"""Derived, rebuildable vector store for the semantic vector route (#669).

Vectors are derived state: never canonical memory, never authority. They are keyed
by ``(fact_uuid, sha256(fact_text))`` and bound to one representation
``config_digest``. Deleting the store changes no recall result, only latency, because
every vector is recomputed deterministically from canonical facts on demand.

Integrity: the store lives inside the durable root's trust boundary (the same as the
canonical SQLite file) and is created with mode 0600 inside a ``derived`` directory the
runtime creates with mode 0700. Every open pins the directory and the file by descriptor
(``O_NOFOLLOW``, ``openat``, ``fchmod``) and then verifies, through the process descriptor
table where the platform exposes one, that the file SQLite opened is that pinned inode:
SQLite resolves paths by name and offers no no-follow open through this binding, so the
verification, not the open, is what keeps a swapped-in link from being acted on. The
trust assumptions this needs are stated on ``_pin_entry``. Each row carries
``row_sha256 = sha256(config_digest | fact_uuid | content_sha256 | vector bytes)``. A
row that fails its checksum is treated as a miss, recomputed and rewritten, and is
counted. ``verify`` recomputes every row against the provider. A ``meta`` row binds
the full ``config_digest``; a store of this format whose identity does not match is
discarded and started over (our own rebuildable state), while a readable database of
another format or version at our path is refused and never touched (``ForeignDerivedStore``).
"""

from __future__ import annotations

import errno
import hashlib
import math
import os
import re
import sqlite3
import stat
import struct
from pathlib import Path
from typing import Callable, Mapping

STORE_FORMAT = "agent-memory-derived-vectors/1.0.0"


def float32_canonical(values) -> tuple[float, ...]:
    """Round to IEEE float32 so cached and freshly computed vectors are identical."""

    vector = tuple(float(value) for value in values)
    packed = struct.pack(f"<{len(vector)}f", *vector)
    return struct.unpack(f"<{len(vector)}f", packed)


def _pack(vector: tuple[float, ...]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def _unpack(blob: bytes) -> tuple[float, ...]:
    return struct.unpack(f"<{len(blob) // 4}f", blob)


def _content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()



_VECTOR_FILE = re.compile(r"^vectors-([0-9a-f]{16})\.sqlite$")
_REQUIRED_COLUMNS = frozenset({"fact_uuid", "content_sha256", "vector", "row_sha256"})
_STORE_FAMILY = STORE_FORMAT.rsplit("/", 1)[0] + "/"
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_O_CLOEXEC = getattr(os, "O_CLOEXEC", 0)
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
#: Where this process can enumerate its own open descriptors (Linux, macOS, the BSDs).
_DESCRIPTOR_TABLE = next((p for p in ("/proc/self/fd", "/dev/fd") if os.path.isdir(p)), None)
_OPENAT = os.open in getattr(os, "supports_dir_fd", set())


class UnsafeDerivedEntry(ValueError):
    """A derived cache directory or file that must not be opened, read, written or unlinked.

    Raised before any I/O through the entry: the directory or file is a symbolic link,
    not a directory or regular file, owned by another user, or SQLite demonstrably opened
    a different inode than the one pinned by descriptor.
    """


class ForeignDerivedStore(ValueError):
    """A readable SQLite database under our name that is not a store of this format.

    Another ``agent-memory-derived-vectors`` version, an unknown format or a foreign
    schema. It is never initialised, reconciled or discarded by this runtime: it may be
    another version's data, so the disposition is the owner's, and it is reported.
    """


def _descriptors_matching(identity: tuple[int, int]) -> set[int] | None:
    """The descriptors of this process open on ``(st_dev, st_ino)``; None without a table."""
    if _DESCRIPTOR_TABLE is None:
        return None
    matching: set[int] = set()
    try:
        names = os.listdir(_DESCRIPTOR_TABLE)
    except OSError:
        return None
    for name in names:
        try:
            number = int(name)
            status = os.fstat(number)
        except (ValueError, OSError):
            continue
        if (status.st_dev, status.st_ino) == identity:
            matching.add(number)
    return matching


def _pin_directory(directory: Path, *, create: bool) -> int:
    """Open ``derived`` itself without following a link, and check it is ours.

    Trust assumptions, stated rather than closed: the runtime root is the trust
    boundary (the canonical SQLite file lives beside this directory). A principal who
    can write to the root can swap ``derived`` for a link to a directory they own; the
    ownership check below refuses a directory owned by another user, and the
    descriptor-table verification in ``_connect_pinned`` refuses a file SQLite opened
    that is not the pinned inode. Only a swap to a directory and file owned by the
    runtime user itself, inside the root, remains indistinguishable from the real
    cache, and that principal already owns the canonical database.
    """
    if directory.is_symlink():
        raise UnsafeDerivedEntry(f"refusing symlinked derived vector cache directory: {directory}")
    if create and not directory.exists():
        try:
            os.mkdir(directory, 0o700)
        except FileExistsError:
            pass
    flags = os.O_RDONLY | _O_NOFOLLOW | _O_DIRECTORY | _O_CLOEXEC
    try:
        dir_fd = os.open(directory, flags)
    except OSError as exc:
        raise UnsafeDerivedEntry(f"refusing derived vector cache directory {directory}: {exc.strerror or exc}") from exc
    try:
        status = os.fstat(dir_fd)
        if not stat.S_ISDIR(status.st_mode):
            raise UnsafeDerivedEntry(f"refusing derived vector cache directory {directory}: not a directory")
        if hasattr(os, "geteuid") and status.st_uid != os.geteuid():
            raise UnsafeDerivedEntry(
                f"refusing derived vector cache directory {directory}: owned by uid {status.st_uid}, "
                f"not the runtime user {os.geteuid()}"
            )
        if stat.S_IMODE(status.st_mode) & 0o022 and hasattr(os, "fchmod"):
            os.fchmod(dir_fd, 0o700)  # ours, and writable by others: tighten
    except BaseException:
        os.close(dir_fd)
        raise
    return dir_fd


def _pin_entry(directory: Path, name: str, *, create: bool) -> tuple[int, os.stat_result]:
    """Open ``directory/name`` as a regular file by descriptor, never through a link.

    The directory is pinned first (``_pin_directory``) and the file is opened relative
    to that descriptor with ``O_NOFOLLOW`` (``openat``), so neither component may be a
    link at the moment of the open. With ``create`` the file is created ``0600`` and,
    whether new or not, ``fchmod``-ed to ``0600`` through the descriptor (never through
    the path). Returns the descriptor, which pins the inode against reuse, and its
    ``fstat``.
    """
    dir_fd = _pin_directory(directory, create=create)
    try:
        flags = os.O_RDWR | _O_NOFOLLOW | _O_CLOEXEC | (os.O_CREAT if create else 0)
        try:
            if _OPENAT:
                fd = os.open(name, flags, 0o600, dir_fd=dir_fd)
            else:
                fd = os.open(directory / name, flags, 0o600)
        except OSError as exc:
            if exc.errno in (getattr(errno, "ELOOP", None), getattr(errno, "EMLINK", None)):
                raise UnsafeDerivedEntry(f"refusing a symlinked derived vector store: {directory / name}") from exc
            raise
    finally:
        os.close(dir_fd)
    try:
        status = os.fstat(fd)
        if not stat.S_ISREG(status.st_mode):
            raise UnsafeDerivedEntry(f"refusing a derived vector store that is not a regular file: {directory / name}")
        if create and hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
    except BaseException:
        os.close(fd)
        raise
    return fd, status


def _connect_pinned(path: Path, status: os.stat_result, **connect_kwargs) -> sqlite3.Connection:
    """Connect SQLite to ``path`` and verify it opened the pinned inode, before any I/O.

    SQLite resolves the path by name. Where the process can enumerate its descriptors,
    the connection is accepted only if a descriptor on the pinned ``(st_dev, st_ino)``
    appeared during the connect: a link swapped in before the open, even one swapped
    back out immediately after, leaves SQLite on another inode and is refused with the
    connection closed and nothing read or written. Without a descriptor table the
    fallback is the directory entry after the open: that detects a link still in place
    but not one swapped in and back out, which is then covered only by the trust
    assumptions on ``_pin_directory``. (A second thread of this process opening the
    same store during the same instant could mask the check; both are this runtime.)
    """
    identity = (status.st_dev, status.st_ino)
    before = _descriptors_matching(identity)
    connection = sqlite3.connect(**connect_kwargs)
    if before is not None:
        after = _descriptors_matching(identity)
        if after is not None and after - before:
            return connection
        if after is not None:
            connection.close()
            raise UnsafeDerivedEntry(f"SQLite opened a different file than the pinned derived store: {path}")
    try:
        entry = os.lstat(path)
    except OSError as exc:
        connection.close()
        raise UnsafeDerivedEntry(f"derived store entry vanished during the open: {path}") from exc
    if stat.S_ISLNK(entry.st_mode) or not stat.S_ISREG(entry.st_mode) or (entry.st_dev, entry.st_ino) != identity:
        connection.close()
        raise UnsafeDerivedEntry(f"derived store entry changed during the open: {path}")
    return connection


def _same_entry(path: Path, status: os.stat_result) -> bool:
    try:
        entry = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISREG(entry.st_mode) and (entry.st_dev, entry.st_ino) == (status.st_dev, status.st_ino)


class DerivedCacheReconciliationError(RuntimeError):
    """Derived sidecar cleanup is incomplete after the canonical operation already committed.

    ``canonical_committed`` is True when a permanent deletion committed canonically and
    residue may remain in a derived store; ``report`` is the reconciliation report and
    ``result`` the canonical commit result, so neither the receipt nor the disposition is
    lost to the caller. Reopening the root retries the reconciliation deterministically.
    """

    def __init__(self, message: str, *, fact_uuid: str | None = None, report: dict | None = None,
                 result: dict | None = None) -> None:
        super().__init__(message)
        self.canonical_committed = fact_uuid is not None
        self.fact_uuid = fact_uuid
        self.report = report
        self.result = result


def _classify_store(connection: sqlite3.Connection, bare_digest: str) -> tuple[str, str | None]:
    """``("ours", None)``, ``("discard", why)`` or ``("foreign", why)`` for an open database.

    Reads only ``sqlite_master``, ``meta`` and ``PRAGMA table_info``; writes nothing.
    ``discard`` is a damaged store of this format (or an empty, never initialised file):
    rebuildable derived state of ours. ``foreign`` is a readable database that
    identifies itself as something else: another ``agent-memory-derived-vectors``
    version, an unknown format, or a schema without our tables. Foreign data is never
    initialised, reconciled or unlinked by this runtime.
    """
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if not tables:
        return "discard", "empty database"
    if not {"meta", "vectors"} <= tables:
        return "foreign", "schema without meta and vectors tables"
    columns = {row[1] for row in connection.execute("PRAGMA table_info(meta)")}
    if not {"key", "value"} <= columns:
        return "foreign", "meta schema is not ours"
    meta = dict(connection.execute("SELECT key, value FROM meta"))
    fmt = str(meta.get("format", ""))
    if fmt != STORE_FORMAT:
        if fmt.startswith(_STORE_FAMILY):
            return "foreign", f"store format {fmt!r} of another runtime version"
        return "foreign", f"unknown store format {fmt!r}"
    digest = str(meta.get("config_digest", "")).split(":", 1)[-1]
    if not digest.startswith(bare_digest):
        return "discard", "config_digest does not match the file name"
    if not str(meta.get("dimensions", "")).isdigit():
        return "discard", "invalid dimensions"
    columns = {row[1] for row in connection.execute("PRAGMA table_info(vectors)")}
    if not _REQUIRED_COLUMNS <= columns:
        return "discard", "vectors schema is incomplete"
    return "ours", None


def reconcile_derived_vector_stores(
    root: str | Path, canonical_texts: Mapping[str, str], *,
    deleted_fact_uuid: str | None = None,
) -> dict:
    """Remove rows no canonical fact accounts for, across every persistent sidecar, with no provider.

    Derived stores are rebuildable and never authority, so this is a cleanup of what
    canonical state no longer physically retains: a row survives only when its
    ``(fact_uuid, sha256(text))`` matches a canonical fact in ``canonical_texts``.
    Pruned (tombstoned) and superseded facts are still canonical rows, so their vectors
    stay; a permanently deleted lineage is gone from both.

    The function never raises for the state of an individual sidecar; it reports:

    * ``stores_checked`` / ``rows_purged``: valid stores reconciled and rows removed;
    * ``stores_discarded``: regular files under our name pattern that are damaged
      stores of this format or not readable as a database at all (corrupt, empty,
      wrong identity). They are unlinked, the same disposition ``DerivedVectorStore``
      applies to its own damaged file, because such a store cannot be reconciled and
      discarding it is the only way to remove whatever residue it holds;
    * ``foreign``: readable databases under our name pattern that identify themselves
      as something else (another ``agent-memory-derived-vectors`` version, an unknown
      format, a schema without our tables). They are never initialised, reconciled or
      unlinked: the data may be another version's, so the disposition is the owner's.
      Residue cannot be ruled out there, so the status is ``"incomplete"``;
    * ``unsafe``: entries never touched or followed (symlinks, non-regular files, a
      ``derived`` path that is not a directory or not owned by the runtime user, a
      file SQLite demonstrably opened other than the pinned one);
    * ``failed``: stores that could not be reconciled (locked, read-only, I/O error);
    * ``status``: ``"complete"`` when nothing is unsafe, foreign or failed, else
      ``"incomplete"``.

    Callers decide the disposition: authorized permanent deletion treats anything but
    ``"complete"`` as residue to report, recovery records it and keeps the canonical
    runtime available. The caller holds the canonical runtime serialization lock.
    SQLite row deletion (with ``secure_delete``) is not a forensic erasure claim about
    rollback journals, backups, snapshots or the filesystem.
    """
    if deleted_fact_uuid is not None and (
        not isinstance(deleted_fact_uuid, str) or not deleted_fact_uuid
    ):
        raise ValueError("deleted_fact_uuid must be a non-empty string or None")
    report: dict = {"status": "complete", "stores_checked": 0, "rows_purged": 0,
                    "stores_discarded": [], "foreign": [], "unsafe": [], "failed": []}
    directory = Path(root) / "derived"
    # An existing link to an external directory is not an Agent Memory cache root.
    # Check before exists(): dangling symlinks would otherwise look like no cache.
    if directory.is_symlink():
        report["unsafe"].append(str(directory))
        report["status"] = "incomplete"
        return report
    if not directory.exists():
        return report
    try:
        dir_fd = _pin_directory(directory, create=False)
    except UnsafeDerivedEntry:
        report["unsafe"].append(str(directory))
        report["status"] = "incomplete"
        return report
    try:
        names = sorted(os.listdir(dir_fd) if os.listdir in os.supports_fd else os.listdir(directory))
    finally:
        os.close(dir_fd)
    allowed = {
        (str(uuid), _content_sha256(text))
        for uuid, text in canonical_texts.items()
    }
    for name in names:
        match = _VECTOR_FILE.fullmatch(name)
        if match is None:
            continue  # not a store of ours; never touched
        path = directory / name
        try:
            fd, status = _pin_entry(directory, name, create=False)
        except UnsafeDerivedEntry:
            report["unsafe"].append(str(path))
            continue
        except OSError as exc:
            report["failed"].append([str(path), f"{type(exc).__name__}: {exc}"])
            continue
        try:
            try:
                # ``mode=rw`` only keeps SQLite from creating a file; it does not stop the
                # open from following a link. ``_connect_pinned`` verifies the inode.
                connection = _connect_pinned(
                    path, status,
                    database=path.absolute().as_uri() + "?mode=rw", uri=True, timeout=5.0,
                )
            except UnsafeDerivedEntry:
                report["unsafe"].append(str(path))
                continue
            except sqlite3.Error as exc:
                report["failed"].append([str(path), f"{type(exc).__name__}: {exc}"])
                continue
            try:
                try:
                    disposition, reason = _classify_store(connection, match.group(1))
                except sqlite3.DatabaseError as exc:
                    if isinstance(exc, sqlite3.OperationalError):
                        raise  # locked, I/O, permissions: a valid store we cannot read right now
                    disposition, reason = "discard", f"unreadable: {exc}"
                if disposition == "foreign":
                    report["foreign"].append([str(path), reason])
                    continue
                if disposition == "discard":
                    connection.close()
                    if _same_entry(path, status):
                        path.unlink()
                        report["stores_discarded"].append([str(path), reason])
                    else:
                        report["unsafe"].append(str(path))
                    continue
                connection.execute("PRAGMA secure_delete=ON")
                rows = connection.execute("SELECT fact_uuid, content_sha256 FROM vectors").fetchall()
                stale = [
                    (uuid, digest)
                    for uuid, digest in rows
                    if (uuid, digest) not in allowed or uuid == deleted_fact_uuid
                ]
                if stale:
                    connection.executemany(
                        "DELETE FROM vectors WHERE fact_uuid = ? AND content_sha256 = ?",
                        stale,
                    )
                    connection.commit()
                report["stores_checked"] += 1
                report["rows_purged"] += len(stale)
            except (sqlite3.Error, OSError) as exc:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
                report["failed"].append([str(path), f"{type(exc).__name__}: {exc}"])
            finally:
                connection.close()
        finally:
            os.close(fd)
    if report["unsafe"] or report["foreign"] or report["failed"]:
        report["status"] = "incomplete"
    return report


class DerivedVectorStore:
    """SQLite sidecar of float32 vectors for one representation identity."""

    def __init__(self, root: str | Path, config_digest: str, dimensions: int) -> None:
        if not config_digest or dimensions < 1:
            raise ValueError("a derived vector store needs a config_digest and positive dimensions")
        self.config_digest = config_digest
        self.dimensions = dimensions
        self.directory = Path(root) / "derived"
        bare = config_digest.split(":", 1)[-1]
        self.path = self.directory / f"vectors-{bare[:16]}.sqlite"
        self.checksum_failures = 0
        self.rows_written = 0
        self._connection = self._open()

    # lifecycle ------------------------------------------------------------------

    def _open(self) -> sqlite3.Connection:
        """Open or create the store by pinned descriptor; never initialise foreign data.

        Raises ``UnsafeDerivedEntry`` (the directory or file is a link, not ours, or
        SQLite opened another inode) and ``ForeignDerivedStore`` (a readable database of
        another format at our path) before any write. Both are ``ValueError``; the
        facade degrades the semantic route in ``auto`` mode and refuses in ``required``.
        """
        fd, status = _pin_entry(self.directory, self.path.name, create=True)
        try:
            connection = _connect_pinned(self.path, status, database=str(self.path), check_same_thread=False)
        finally:
            os.close(fd)
        try:
            try:
                disposition, reason = _classify_store(connection, self.path.name[len("vectors-"):-len(".sqlite")])
            except sqlite3.DatabaseError as exc:
                if isinstance(exc, sqlite3.OperationalError):
                    raise
                disposition, reason = "discard", f"unreadable: {exc}"
            if disposition == "foreign":
                raise ForeignDerivedStore(f"refusing to touch a foreign derived store at {self.path}: {reason}")
            if disposition == "discard" and reason != "empty database":
                connection.close()
                return self._discard_and_reopen(status)
            if disposition == "ours":
                meta = dict(connection.execute("SELECT key, value FROM meta").fetchall())
                expected = {"format": STORE_FORMAT, "config_digest": self.config_digest,
                            "dimensions": str(self.dimensions)}
                if meta != expected:
                    connection.close()
                    return self._discard_and_reopen(status)
            else:  # an empty, never initialised file of ours
                # Freed cells (replaced rows, purged orphans) are zeroed inside the file (#802).
                connection.execute("PRAGMA secure_delete=ON")
                connection.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                connection.execute(
                    "CREATE TABLE vectors (fact_uuid TEXT NOT NULL, content_sha256 TEXT NOT NULL, "
                    "vector BLOB NOT NULL, row_sha256 TEXT NOT NULL, PRIMARY KEY (fact_uuid, content_sha256))"
                )
                connection.executemany(
                    "INSERT INTO meta (key, value) VALUES (?, ?)",
                    sorted({"format": STORE_FORMAT, "config_digest": self.config_digest,
                            "dimensions": str(self.dimensions)}.items()),
                )
                connection.commit()
            connection.execute("PRAGMA secure_delete=ON")
        except BaseException:
            connection.close()
            raise
        return connection

    def _discard_and_reopen(self, status: os.stat_result) -> sqlite3.Connection:
        """Unlink our own damaged store (only while the entry is still that inode) and recreate it."""
        if _same_entry(self.path, status):
            self.path.unlink(missing_ok=True)
        else:
            raise UnsafeDerivedEntry(f"derived store entry changed during the open: {self.path}")
        return self._open()

    def close(self) -> None:
        self._connection.close()

    # rows -------------------------------------------------------------------------

    def _row_sha256(self, fact_uuid: str, content_sha256: str, blob: bytes) -> str:
        digest = hashlib.sha256()
        for part in (self.config_digest, fact_uuid, content_sha256):
            digest.update(part.encode("utf-8"))
            digest.update(b"\x00")
        digest.update(blob)
        return digest.hexdigest()

    def _valid(self, vector: tuple[float, ...]) -> bool:
        return len(vector) == self.dimensions and all(math.isfinite(value) for value in vector)

    def vector_for(self, fact_uuid: str, text: str, embed: Callable[[str], tuple[float, ...]]) -> tuple[float, ...]:
        content = _content_sha256(text)
        row = self._connection.execute(
            "SELECT vector, row_sha256 FROM vectors WHERE fact_uuid = ? AND content_sha256 = ?",
            (fact_uuid, content),
        ).fetchone()
        if row is not None:
            blob, checksum = row
            if checksum == self._row_sha256(fact_uuid, content, blob):
                vector = _unpack(blob)
                if self._valid(vector):
                    return vector
            self.checksum_failures += 1
        vector = float32_canonical(embed(text))
        if not self._valid(vector):
            raise ValueError("representation returned an invalid vector")
        blob = _pack(vector)
        self._connection.execute(
            "INSERT OR REPLACE INTO vectors (fact_uuid, content_sha256, vector, row_sha256) VALUES (?, ?, ?, ?)",
            (fact_uuid, content, blob, self._row_sha256(fact_uuid, content, blob)),
        )
        self._connection.commit()
        self.rows_written += 1
        return vector


    def purge_fact(self, fact_uuid: str) -> int:
        """Delete every cached representation row for a fact, with no model call.

        This is a *derived-store primitive*, not a governance decision or a
        complete permanent-deletion guarantee. The authorized caller owns the
        decision, recovery journal and disposition of other sidecar identities.
        Never use this to infer that canonical data or filesystem remnants have
        been securely erased. It is intentionally idempotent.
        """
        if not isinstance(fact_uuid, str) or not fact_uuid:
            raise ValueError("fact_uuid must be a non-empty string")
        cursor = self._connection.execute(
            "DELETE FROM vectors WHERE fact_uuid = ?", (fact_uuid,)
        )
        self._connection.commit()
        return int(cursor.rowcount)

    def row_count(self) -> int:
        return int(self._connection.execute("SELECT COUNT(*) FROM vectors").fetchone()[0])

    def verify(self, texts: dict[str, str], embed: Callable[[str], tuple[float, ...]], *,
               rebuild: bool = False) -> dict:
        """Recompute every stored row whose fact text is known; report (and optionally fix) mismatches.

        ``texts`` maps fact uuid to canonical text. Rows for unknown facts are orphans
        (for example tombstoned or never-current facts); they are reported, and removed
        on rebuild.
        """

        mismatched, orphans, checked = [], [], 0
        rows = self._connection.execute("SELECT fact_uuid, content_sha256, vector, row_sha256 FROM vectors").fetchall()
        for fact_uuid, content, blob, checksum in rows:
            text = texts.get(fact_uuid)
            if text is None or _content_sha256(text) != content:
                orphans.append(fact_uuid)
                continue
            checked += 1
            expected = _pack(float32_canonical(embed(text)))
            if blob != expected or checksum != self._row_sha256(fact_uuid, content, blob):
                mismatched.append(fact_uuid)
        if rebuild:
            for fact_uuid in mismatched:
                text = texts[fact_uuid]
                self._connection.execute(
                    "DELETE FROM vectors WHERE fact_uuid = ? AND content_sha256 = ?",
                    (fact_uuid, _content_sha256(text)),
                )
                self.vector_for(fact_uuid, text, embed)
            for fact_uuid in orphans:
                self._connection.execute("DELETE FROM vectors WHERE fact_uuid = ?", (fact_uuid,))
            self._connection.commit()
        return {
            "store": str(self.path),
            "rows": len(rows),
            "checked": checked,
            "mismatched": sorted(mismatched),
            "orphans": sorted(orphans),
            "rebuilt": rebuild,
            "authority_effect": "none",
        }

    def posture(self) -> dict:
        return {
            "path": str(self.path),
            "format": STORE_FORMAT,
            "config_digest": self.config_digest,
            "rows": self.row_count(),
            "rows_written_since_open": self.rows_written,
            "checksum_failures_since_open": self.checksum_failures,
            "authority_effect": "none",
        }


__all__ = ["DerivedVectorStore", "STORE_FORMAT", "float32_canonical", "reconcile_derived_vector_stores",
           "DerivedCacheReconciliationError", "UnsafeDerivedEntry", "ForeignDerivedStore"]
