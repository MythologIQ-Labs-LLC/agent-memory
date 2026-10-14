"""Derived, rebuildable vector store for the semantic vector route (#669).

Vectors are derived state: never canonical memory, never authority. They are keyed
by ``(fact_uuid, sha256(fact_text))`` and bound to one representation
``config_digest``. Deleting the store changes no recall result, only latency, because
every vector is recomputed deterministically from canonical facts on demand.

Integrity: the store lives inside the durable root's trust boundary (the same as the
canonical SQLite file) and is created with mode 0600. Each row carries
``row_sha256 = sha256(config_digest | fact_uuid | content_sha256 | vector bytes)``. A
row that fails its checksum is treated as a miss, recomputed and rewritten, and is
counted. ``verify`` recomputes every row against the provider. A ``meta`` row binds
the full ``config_digest``; any mismatch discards the file and starts over.
"""

from __future__ import annotations

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


def _invalid_store(connection: sqlite3.Connection, bare_digest: str) -> str | None:
    """Why this file is not a derived store of ours, or None when its identity checks out."""
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if not {"meta", "vectors"} <= tables:
        return "missing meta or vectors table"
    meta = dict(connection.execute("SELECT key, value FROM meta"))
    digest = str(meta.get("config_digest", "")).split(":", 1)[-1]
    columns = {row[1] for row in connection.execute("PRAGMA table_info(vectors)")}
    if meta.get("format") != STORE_FORMAT:
        return "unknown store format"
    if not digest.startswith(bare_digest):
        return "config_digest does not match the file name"
    if not str(meta.get("dimensions", "")).isdigit():
        return "invalid dimensions"
    if not _REQUIRED_COLUMNS <= columns:
        return "vectors schema is incomplete"
    return None


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
    * ``stores_discarded``: regular files under our name pattern that are not readable
      derived stores (corrupt, foreign schema, wrong identity). They are unlinked, the
      same disposition ``DerivedVectorStore`` applies to its own damaged file, because
      an unreadable store cannot be reconciled and discarding it is the only way to
      remove whatever residue it holds;
    * ``unsafe``: entries never touched or followed (symlinks, non-regular files, a
      ``derived`` path that is not a directory);
    * ``failed``: stores that could not be reconciled (locked, read-only, I/O error);
    * ``status``: ``"complete"`` when nothing is unsafe or failed, else ``"incomplete"``.

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
                    "stores_discarded": [], "unsafe": [], "failed": []}
    directory = Path(root) / "derived"
    if not directory.exists():
        return report
    if not directory.is_dir():
        report["unsafe"].append(str(directory))
        report["status"] = "incomplete"
        return report
    allowed = {
        (str(uuid), _content_sha256(text))
        for uuid, text in canonical_texts.items()
    }
    for path in sorted(directory.glob("vectors-*.sqlite")):
        match = _VECTOR_FILE.fullmatch(path.name)
        if match is None:
            continue  # not a store of ours; never touched
        try:
            status = os.lstat(path)
        except OSError as exc:
            report["failed"].append([str(path), f"{type(exc).__name__}: {exc}"])
            continue
        if stat.S_ISLNK(status.st_mode) or not stat.S_ISREG(status.st_mode):
            report["unsafe"].append(str(path))
            continue
        try:
            # ``mode=rw`` never creates a file; the absolute (not resolved) path keeps a
            # symlink swapped in after the lstat from being followed by name resolution.
            connection = sqlite3.connect(path.absolute().as_uri() + "?mode=rw", uri=True, timeout=5.0)
        except sqlite3.Error as exc:
            report["failed"].append([str(path), f"{type(exc).__name__}: {exc}"])
            continue
        try:
            try:
                reason = _invalid_store(connection, match.group(1))
            except sqlite3.DatabaseError as exc:
                if isinstance(exc, sqlite3.OperationalError):
                    raise  # locked, I/O, permissions: a valid store we cannot read right now
                reason = f"unreadable: {exc}"
            if reason is not None:
                connection.close()
                path.unlink()
                report["stores_discarded"].append([str(path), reason])
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
    if report["unsafe"] or report["failed"]:
        report["status"] = "incomplete"
    return report


class DerivedVectorStore:
    """SQLite sidecar of float32 vectors for one representation identity."""

    def __init__(self, root: str | Path, config_digest: str, dimensions: int) -> None:
        if not config_digest or dimensions < 1:
            raise ValueError("a derived vector store needs a config_digest and positive dimensions")
        self.config_digest = config_digest
        self.dimensions = dimensions
        directory = Path(root) / "derived"
        directory.mkdir(parents=True, exist_ok=True)
        bare = config_digest.split(":", 1)[-1]
        self.path = directory / f"vectors-{bare[:16]}.sqlite"
        self.checksum_failures = 0
        self.rows_written = 0
        self._connection = self._open()

    # lifecycle ------------------------------------------------------------------

    def _open(self) -> sqlite3.Connection:
        if self.path.is_symlink():
            raise ValueError(f"refusing a symlinked derived vector store: {self.path}")
        existed = self.path.exists()
        if not existed:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        os.chmod(self.path, 0o600)
        connection = sqlite3.connect(self.path, check_same_thread=False)
        try:
            # Freed cells (replaced rows, purged orphans) are zeroed inside the file (#802).
            connection.execute("PRAGMA secure_delete=ON")
            connection.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS vectors (fact_uuid TEXT NOT NULL, content_sha256 TEXT NOT NULL, "
                "vector BLOB NOT NULL, row_sha256 TEXT NOT NULL, PRIMARY KEY (fact_uuid, content_sha256))"
            )
            meta = dict(connection.execute("SELECT key, value FROM meta").fetchall())
        except sqlite3.DatabaseError:
            connection.close()
            return self._discard_and_reopen()
        expected = {"format": STORE_FORMAT, "config_digest": self.config_digest, "dimensions": str(self.dimensions)}
        if meta and meta != expected:
            connection.close()
            return self._discard_and_reopen()
        if not meta:
            connection.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", sorted(expected.items()))
            connection.commit()
        return connection

    def _discard_and_reopen(self) -> sqlite3.Connection:
        self.path.unlink(missing_ok=True)
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


__all__ = ["DerivedVectorStore", "STORE_FORMAT", "float32_canonical", "reconcile_derived_vector_stores", "DerivedCacheReconciliationError"]
