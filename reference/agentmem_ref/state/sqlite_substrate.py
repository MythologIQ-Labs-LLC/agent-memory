"""Durable single-host SQLite canonical substrate for Agent Memory RC1.

This module implements the ordinary ``TemporalGraphPort`` contract directly
against SQLite.  The database, not a JSON row dump, is the canonical durable
state.  Governance and authority remain above this layer.

The profile is intentionally modest:

* one local SQLite database file;
* WAL journaling, ``synchronous=FULL`` and foreign-key enforcement;
* deterministic lexical candidate generation and provenance-neighbor lookup;
* durable substrate-scoped identifier progress;
* explicit transaction and integrity seams for the SQLite restart runtime;
* additive native typed-relation storage under its own relation schema version;
* no provider-native score, storage success, or relation creates authority.

SQLite is an embedded transactional store, not a distributed database.  This
module does not claim multi-host leader election, network partition handling,
or horizontal scale.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Iterable

from .substrate import (
    DeterministicIds,
    Episode,
    Fact,
    TYPED_RELATION_SCHEMA_VERSION,
    TypedRelation,
    UNFILTERED,
)


SQLITE_SUBSTRATE_SCHEMA_VERSION = "1.0.0"
SQLITE_SUBSTRATE_PROFILE = "sqlite_single_host_v1"
SQLITE_SOURCE_RIGHTS = "SQLite public domain; Python sqlite3 under the Python license"
# Incremental canonical-state commitment (#522). The digest string is self-describing:
# "sha256:<hex>" is the legacy full-JSON digest, "bmerkle-v1:<hex>" the bucketed Merkle root.
LEGACY_DIGEST_PREFIX = "sha256:"
BUCKETED_DIGEST_SCHEME = "bmerkle-v1"
DIGEST_BUCKETS = 256


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


_OPERATION_TABLES = {
    "add_episode": "episodes",
    "write_fact": "facts",
    "invalidate_fact": "facts",
    "delete_fact": "facts",
    "write_relation": "typed_relations",
    "invalidate_relation": "typed_relations",
    "delete_relation": "typed_relations",
}


def _bucket_of(table: str, key: str) -> int:
    return int(hashlib.sha256(f"{table}\x00{key}".encode("utf-8")).hexdigest()[:8], 16) % DIGEST_BUCKETS


def _row_hash(table: str, payload: dict) -> str:
    return hashlib.sha256(_canonical_bytes({"table": table, "row": payload})).hexdigest()


def _bucket_digest(row_hashes: list[str]) -> str:
    return hashlib.sha256(_canonical_bytes(sorted(row_hashes))).hexdigest()


_EMPTY_BUCKET = _bucket_digest([])


def _tokens(text: str) -> set[str]:
    return {token.strip(".,;:!?").lower() for token in text.split() if token.strip(".,;:!?")}


class SqliteDeterministicIds(DeterministicIds):
    """Durable substrate-scoped id sequence stored in SQLite metadata."""

    def __init__(self, connection: sqlite3.Connection, prefix: str = "ref") -> None:
        super().__init__(prefix)
        self._connection = connection
        self._sqlite_prefix = prefix

    def next(self) -> str:
        self._connection.execute(
            "UPDATE agent_memory_meta SET value = CAST(value AS INTEGER) + 1 WHERE key = 'id_counter'"
        )
        row = self._connection.execute(
            "SELECT value FROM agent_memory_meta WHERE key = 'id_counter'"
        ).fetchone()
        if row is None:
            raise RuntimeError("SQLite substrate identifier metadata is missing")
        return f"{self._sqlite_prefix}-{int(row[0]):04d}"

    def checkpoint_value(self) -> int:
        row = self._connection.execute(
            "SELECT value FROM agent_memory_meta WHERE key = 'id_counter'"
        ).fetchone()
        if row is None:
            raise RuntimeError("SQLite substrate identifier metadata is missing")
        return int(row[0])

    def restore_checkpoint_value(self, value: int) -> None:
        parsed = int(value)
        if parsed < 0:
            raise ValueError("identifier checkpoint cannot be negative")
        current = self.checkpoint_value()
        if parsed > current:
            self._connection.execute(
                "UPDATE agent_memory_meta SET value = ? WHERE key = 'id_counter'",
                (str(parsed),),
            )


class SQLiteTemporalGraph:
    """Production-credible single-host implementation of ``TemporalGraphPort``."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False is safe ONLY because every use of this connection by
        # an Agent Memory handle happens while holding the owning runtime's
        # serialization lock (SQLiteRestartSafeRuntime.serialization_lock, #530).
        # This substrate is not independently thread-safe.
        self._connection = sqlite3.connect(
            str(self.path),
            timeout=30.0,
            isolation_level=None,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._initialize_schema()
        self._ids = SqliteDeterministicIds(self._connection)
        # Canonical rows changed since the digest index was last brought current.
        self._digest_dirty: set[tuple[str, str]] = set()
        # The maintained index is derived data: it is trusted only after this process rebuilt
        # it or verified it row-for-row against the canonical tables.
        self._digest_index_trusted = False

    def _initialize_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS agent_memory_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS episodes (
                uuid TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source_description TEXT NOT NULL,
                valid_at TEXT NOT NULL,
                group_id TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS episodes_group_idx ON episodes(group_id);
            CREATE TABLE IF NOT EXISTS facts (
                uuid TEXT PRIMARY KEY,
                fact_text TEXT NOT NULL,
                group_id TEXT NOT NULL,
                episode_uuids_json TEXT NOT NULL,
                valid_at TEXT,
                invalid_at TEXT,
                created_at TEXT,
                expired_at TEXT,
                attributes_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS facts_group_idx ON facts(group_id);
            CREATE TABLE IF NOT EXISTS typed_relations (
                relation_id TEXT PRIMARY KEY,
                source_uuid TEXT NOT NULL,
                target_uuid TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                group_id TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                retrieval_weight REAL NOT NULL,
                valid_at TEXT,
                invalid_at TEXT,
                created_at TEXT,
                expired_at TEXT,
                attributes_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS typed_relations_source_group_idx
                ON typed_relations(source_uuid, group_id);
            CREATE INDEX IF NOT EXISTS typed_relations_target_group_idx
                ON typed_relations(target_uuid, group_id);
            CREATE INDEX IF NOT EXISTS typed_relations_type_idx
                ON typed_relations(relation_type);
            CREATE TABLE IF NOT EXISTS substrate_write_log (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                operation TEXT NOT NULL,
                reference TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runtime_state (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runtime_journal (
                generation INTEGER PRIMARY KEY,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS digest_rows (
                table_name TEXT NOT NULL,
                row_key TEXT NOT NULL,
                bucket INTEGER NOT NULL,
                row_hash TEXT NOT NULL,
                PRIMARY KEY (table_name, row_key)
            );
            CREATE INDEX IF NOT EXISTS digest_rows_bucket_idx ON digest_rows(bucket);
            CREATE TABLE IF NOT EXISTS digest_buckets (
                bucket INTEGER PRIMARY KEY,
                digest TEXT NOT NULL
            );
            """
        )
        self._connection.execute(
            "INSERT OR IGNORE INTO agent_memory_meta(key, value) VALUES('schema_version', ?)",
            (SQLITE_SUBSTRATE_SCHEMA_VERSION,),
        )
        self._connection.execute(
            "INSERT OR IGNORE INTO agent_memory_meta(key, value) VALUES('relation_schema_version', ?)",
            (TYPED_RELATION_SCHEMA_VERSION,),
        )
        self._connection.execute(
            "INSERT OR IGNORE INTO agent_memory_meta(key, value) VALUES('id_counter', '0')"
        )
        row = self._connection.execute(
            "SELECT value FROM agent_memory_meta WHERE key = 'schema_version'"
        ).fetchone()
        if row is None or row[0] != SQLITE_SUBSTRATE_SCHEMA_VERSION:
            raise RuntimeError("unsupported SQLite substrate schema version")
        relation_row = self._connection.execute(
            "SELECT value FROM agent_memory_meta WHERE key = 'relation_schema_version'"
        ).fetchone()
        if relation_row is None or relation_row[0] != TYPED_RELATION_SCHEMA_VERSION:
            raise RuntimeError("unsupported SQLite typed relation schema version")

    def close(self) -> None:
        self._connection.close()

    @property
    def sqlite_version(self) -> str:
        return sqlite3.sqlite_version

    def operational_identity(self) -> dict[str, str]:
        return {
            "substrate_profile": SQLITE_SUBSTRATE_PROFILE,
            "substrate_schema_version": SQLITE_SUBSTRATE_SCHEMA_VERSION,
            "relation_schema_version": TYPED_RELATION_SCHEMA_VERSION,
            "sqlite_version": self.sqlite_version,
            "source_rights": SQLITE_SOURCE_RIGHTS,
            "journal_mode": str(self._connection.execute("PRAGMA journal_mode").fetchone()[0]).lower(),
            "synchronous": str(self._connection.execute("PRAGMA synchronous").fetchone()[0]),
        }

    def integrity_check(self) -> None:
        row = self._connection.execute("PRAGMA integrity_check").fetchone()
        if row is None or str(row[0]).lower() != "ok":
            raise RuntimeError("SQLite integrity_check failed")

    def identifier_checkpoint(self) -> int:
        return self._ids.checkpoint_value()

    def restore_identifier_checkpoint(self, value: int) -> None:
        self._ids.restore_checkpoint_value(value)

    @contextmanager
    def transaction(self):
        if self._connection.in_transaction:
            raise RuntimeError("nested SQLite substrate transactions are unsupported")
        self._connection.execute("BEGIN IMMEDIATE")
        dirty_before = set(self._digest_dirty)
        trusted_before = self._digest_index_trusted
        try:
            yield
        except Exception:
            self._connection.execute("ROLLBACK")
            # Rows and digest tables roll back together; forget changes that no longer exist.
            self._digest_dirty = dirty_before
            self._digest_index_trusted = trusted_before
            raise
        else:
            self._connection.execute("COMMIT")

    # -- runtime-state ownership used by the SQLite production profile --

    def read_runtime_state(self) -> dict | None:
        row = self._connection.execute(
            "SELECT payload_json FROM runtime_state WHERE singleton = 1"
        ).fetchone()
        if row is None:
            return None
        value = json.loads(row[0])
        if not isinstance(value, dict):
            raise ValueError("SQLite runtime state is malformed")
        return value

    def write_runtime_state(self, payload: dict) -> None:
        self._connection.execute(
            "INSERT INTO runtime_state(singleton, payload_json) VALUES(1, ?) "
            "ON CONFLICT(singleton) DO UPDATE SET payload_json = excluded.payload_json",
            (_canonical_bytes(payload).decode("utf-8"),),
        )

    def read_runtime_journal(self) -> list[dict]:
        rows = self._connection.execute(
            "SELECT payload_json FROM runtime_journal ORDER BY generation"
        ).fetchall()
        result: list[dict] = []
        for row in rows:
            value = json.loads(row[0])
            if not isinstance(value, dict):
                raise ValueError("SQLite runtime journal row is malformed")
            result.append(value)
        return result

    def append_runtime_journal(self, generation: int, payload: dict) -> None:
        self._connection.execute(
            "INSERT INTO runtime_journal(generation, payload_json) VALUES(?, ?)",
            (int(generation), _canonical_bytes(payload).decode("utf-8")),
        )

    def backup_to(self, destination: str | Path) -> None:
        target_path = Path(destination)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target = sqlite3.connect(str(target_path))
        try:
            self._connection.backup(target)
        finally:
            target.close()

    # -- canonical substrate writes --

    def add_episode(self, episode: Episode) -> None:
        self._connection.execute(
            """
            INSERT INTO episodes(uuid, content, source_description, valid_at, group_id)
            VALUES(?, ?, ?, ?, ?)
            ON CONFLICT(uuid) DO UPDATE SET
                content = excluded.content,
                source_description = excluded.source_description,
                valid_at = excluded.valid_at,
                group_id = excluded.group_id
            """,
            (
                episode.uuid,
                episode.content,
                episode.source_description,
                episode.valid_at,
                episode.group_id,
            ),
        )
        self._log("add_episode", episode.uuid)

    def write_fact(self, fact: Fact) -> None:
        existing = self.get_fact(fact.uuid)
        if existing is not None and existing != fact:
            raise ValueError(
                f"refusing to overwrite fact {fact.uuid!r}: identifier collision would destroy a committed fact"
            )
        if existing is None:
            self._connection.execute(
                """
                INSERT INTO facts(
                    uuid, fact_text, group_id, episode_uuids_json,
                    valid_at, invalid_at, created_at, expired_at, attributes_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact.uuid,
                    fact.fact_text,
                    fact.group_id,
                    _canonical_bytes(list(fact.episode_uuids)).decode("utf-8"),
                    fact.valid_at,
                    fact.invalid_at,
                    fact.created_at,
                    fact.expired_at,
                    _canonical_bytes(fact.attributes).decode("utf-8"),
                ),
            )
        self._log("write_fact", fact.uuid)

    def invalidate_fact(self, uuid: str, invalid_at: str, expired_at: str) -> None:
        cursor = self._connection.execute(
            "UPDATE facts SET invalid_at = ?, expired_at = ? WHERE uuid = ?",
            (invalid_at, expired_at, uuid),
        )
        if cursor.rowcount:
            self._log("invalidate_fact", uuid)

    def delete_fact(self, uuid: str) -> None:
        self._connection.execute("DELETE FROM facts WHERE uuid = ?", (uuid,))
        self._log("delete_fact", uuid)

    def write_relation(self, relation: TypedRelation) -> None:
        if self.get_fact(relation.source_uuid) is None or self.get_fact(relation.target_uuid) is None:
            raise ValueError("typed relation endpoints must exist when the relation is written")
        existing = self.get_relation(relation.relation_id)
        if existing is not None and existing != relation:
            raise ValueError(
                f"refusing to overwrite relation {relation.relation_id!r}: "
                "identifier collision would destroy canonical graph state"
            )
        if existing is None:
            self._connection.execute(
                """
                INSERT INTO typed_relations(
                    relation_id, source_uuid, target_uuid, relation_type, group_id,
                    evidence_refs_json, retrieval_weight, valid_at, invalid_at,
                    created_at, expired_at, attributes_json
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relation.relation_id,
                    relation.source_uuid,
                    relation.target_uuid,
                    relation.relation_type,
                    relation.group_id,
                    _canonical_bytes(list(relation.evidence_refs)).decode("utf-8"),
                    relation.retrieval_weight,
                    relation.valid_at,
                    relation.invalid_at,
                    relation.created_at,
                    relation.expired_at,
                    _canonical_bytes(relation.attributes).decode("utf-8"),
                ),
            )
        self._log("write_relation", relation.relation_id)

    def invalidate_relation(
        self,
        relation_id: str,
        invalid_at: str,
        expired_at: str,
    ) -> None:
        cursor = self._connection.execute(
            "UPDATE typed_relations SET invalid_at = ?, expired_at = ? WHERE relation_id = ?",
            (invalid_at, expired_at, relation_id),
        )
        if cursor.rowcount:
            self._log("invalidate_relation", relation_id)

    def delete_relation(self, relation_id: str) -> None:
        self._connection.execute(
            "DELETE FROM typed_relations WHERE relation_id = ?",
            (relation_id,),
        )
        self._log("delete_relation", relation_id)

    def _log(self, operation: str, reference: str) -> None:
        self._connection.execute(
            "INSERT INTO substrate_write_log(operation, reference) VALUES(?, ?)",
            (operation, reference),
        )
        table = _OPERATION_TABLES.get(operation)
        if table is None:
            raise RuntimeError(f"canonical write {operation!r} has no digest table mapping")
        self._digest_dirty.add((table, reference))

    # -- canonical substrate reads --

    def get_episode(self, uuid: str) -> Episode | None:
        row = self._connection.execute(
            "SELECT uuid, content, source_description, valid_at, group_id FROM episodes WHERE uuid = ?",
            (uuid,),
        ).fetchone()
        if row is None:
            return None
        return Episode(**dict(row))

    def get_fact(self, uuid: str) -> Fact | None:
        row = self._connection.execute("SELECT * FROM facts WHERE uuid = ?", (uuid,)).fetchone()
        return None if row is None else self._fact_from_row(row)

    def get_relation(self, relation_id: str) -> TypedRelation | None:
        row = self._connection.execute(
            "SELECT * FROM typed_relations WHERE relation_id = ?",
            (relation_id,),
        ).fetchone()
        return None if row is None else self._relation_from_row(row)

    def all_facts(self) -> Iterable[Fact]:
        rows = self._connection.execute("SELECT * FROM facts ORDER BY uuid").fetchall()
        return tuple(self._fact_from_row(row) for row in rows)

    def all_relations(self) -> Iterable[TypedRelation]:
        rows = self._connection.execute(
            "SELECT * FROM typed_relations ORDER BY relation_id"
        ).fetchall()
        return tuple(self._relation_from_row(row) for row in rows)

    def relations_from(
        self,
        source_uuid: str,
        group_ids: list[str] | None = UNFILTERED,
        relation_types: tuple[str, ...] | None = None,
    ) -> list[TypedRelation]:
        return self._relations_for_endpoint(
            endpoint="source_uuid",
            endpoint_ref=source_uuid,
            group_ids=group_ids,
            relation_types=relation_types,
        )

    def relations_to(
        self,
        target_uuid: str,
        group_ids: list[str] | None = UNFILTERED,
        relation_types: tuple[str, ...] | None = None,
    ) -> list[TypedRelation]:
        return self._relations_for_endpoint(
            endpoint="target_uuid",
            endpoint_ref=target_uuid,
            group_ids=group_ids,
            relation_types=relation_types,
        )

    def _relations_for_endpoint(
        self,
        *,
        endpoint: str,
        endpoint_ref: str,
        group_ids: list[str] | None,
        relation_types: tuple[str, ...] | None,
    ) -> list[TypedRelation]:
        if endpoint not in ("source_uuid", "target_uuid"):
            raise ValueError("unsupported typed relation endpoint selector")
        clauses = [f"{endpoint} = ?"]
        values: list[object] = [endpoint_ref]
        if group_ids is not UNFILTERED:
            if not group_ids:
                return []
            placeholders = ",".join("?" for _ in group_ids)
            clauses.append(f"group_id IN ({placeholders})")
            values.extend(group_ids)
        if relation_types is not None:
            if not relation_types:
                return []
            placeholders = ",".join("?" for _ in relation_types)
            clauses.append(f"relation_type IN ({placeholders})")
            values.extend(relation_types)
        rows = self._connection.execute(
            "SELECT * FROM typed_relations WHERE "
            + " AND ".join(clauses)
            + " ORDER BY retrieval_weight DESC, relation_type, source_uuid, target_uuid, relation_id",
            tuple(values),
        ).fetchall()
        return [self._relation_from_row(row) for row in rows]

    def evidence_neighbors(
        self,
        seed_uuid: str,
        group_ids: list[str] | None = UNFILTERED,
    ) -> list[tuple[Fact, tuple[str, ...], float]]:
        seed = self.get_fact(seed_uuid)
        if seed is None:
            return []
        seed_evidence = set(seed.episode_uuids)
        if not seed_evidence:
            return []
        neighbors: list[tuple[Fact, tuple[str, ...], float]] = []
        for fact in self._facts_for_groups(group_ids):
            if fact.uuid == seed_uuid:
                continue
            candidate_evidence = set(fact.episode_uuids)
            shared = tuple(sorted(seed_evidence.intersection(candidate_evidence)))
            if not shared:
                continue
            union = seed_evidence.union(candidate_evidence)
            score = len(shared) / len(union) if union else 0.0
            neighbors.append((fact, shared, score))
        neighbors.sort(key=lambda item: (-item[2], item[0].uuid))
        return neighbors

    def search(
        self,
        query: str,
        group_ids: list[str] | None = UNFILTERED,
        eligible=None,
    ) -> list[tuple[Fact, float]]:
        """Lexical discovery. ``eligible`` (#548) skips facts before scoring; it is a
        minimisation filter supplied by the governed caller, never permission."""
        terms = _tokens(query)
        scored: list[tuple[Fact, float]] = []
        for fact in self._facts_for_groups(group_ids):
            if eligible is not None and not eligible(fact):
                continue
            overlap = terms & _tokens(fact.fact_text)
            if not overlap:
                continue
            scored.append((fact, len(overlap) / max(len(terms), 1)))
        scored.sort(key=lambda pair: (-pair[1], pair[0].uuid))
        return scored

    def _facts_for_groups(self, group_ids: list[str] | None) -> tuple[Fact, ...]:
        if group_ids is UNFILTERED:
            rows = self._connection.execute("SELECT * FROM facts ORDER BY uuid").fetchall()
        elif not group_ids:
            return ()
        else:
            placeholders = ",".join("?" for _ in group_ids)
            rows = self._connection.execute(
                f"SELECT * FROM facts WHERE group_id IN ({placeholders}) ORDER BY uuid",
                tuple(group_ids),
            ).fetchall()
        return tuple(self._fact_from_row(row) for row in rows)

    @staticmethod
    def _fact_from_row(row: sqlite3.Row) -> Fact:
        episodes = json.loads(row["episode_uuids_json"])
        attributes = json.loads(row["attributes_json"])
        if not isinstance(episodes, list) or not isinstance(attributes, dict):
            raise ValueError("SQLite fact payload is malformed")
        return Fact(
            uuid=row["uuid"],
            fact_text=row["fact_text"],
            group_id=row["group_id"],
            episode_uuids=tuple(str(item) for item in episodes),
            valid_at=row["valid_at"],
            invalid_at=row["invalid_at"],
            created_at=row["created_at"],
            expired_at=row["expired_at"],
            attributes=attributes,
        )

    @staticmethod
    def _relation_from_row(row: sqlite3.Row) -> TypedRelation:
        evidence_refs = json.loads(row["evidence_refs_json"])
        attributes = json.loads(row["attributes_json"])
        if not isinstance(evidence_refs, list) or not isinstance(attributes, dict):
            raise ValueError("SQLite typed relation payload is malformed")
        return TypedRelation(
            relation_id=row["relation_id"],
            source_uuid=row["source_uuid"],
            target_uuid=row["target_uuid"],
            relation_type=row["relation_type"],
            group_id=row["group_id"],
            evidence_refs=tuple(str(item) for item in evidence_refs),
            retrieval_weight=float(row["retrieval_weight"]),
            valid_at=row["valid_at"],
            invalid_at=row["invalid_at"],
            created_at=row["created_at"],
            expired_at=row["expired_at"],
            attributes=attributes,
        )

    def state_digest(self) -> str:
        episodes = [asdict(item) for item in self._all_episodes()]
        facts = [asdict(item) for item in self.all_facts()]
        relations = [asdict(item) for item in self.all_relations()]
        return _digest(
            {
                "schema_version": SQLITE_SUBSTRATE_SCHEMA_VERSION,
                "relation_schema_version": TYPED_RELATION_SCHEMA_VERSION,
                "id_counter": self.identifier_checkpoint(),
                "episodes": episodes,
                "facts": facts,
                "relations": relations,
            }
        )

    # -- incremental canonical-state commitment (#522) --

    def _row_payload(self, table: str, key: str) -> dict | None:
        if table == "episodes":
            value = self.get_episode(key)
        elif table == "facts":
            value = self.get_fact(key)
        elif table == "typed_relations":
            value = self.get_relation(key)
        else:
            raise ValueError(f"unknown digest table {table!r}")
        return None if value is None else asdict(value)

    def _bucketed_root(self, bucket_digests: list[str]) -> str:
        material = {
            "scheme": BUCKETED_DIGEST_SCHEME,
            "schema_version": SQLITE_SUBSTRATE_SCHEMA_VERSION,
            "relation_schema_version": TYPED_RELATION_SCHEMA_VERSION,
            "id_counter": self.identifier_checkpoint(),
            "buckets": bucket_digests,
        }
        return f"{BUCKETED_DIGEST_SCHEME}:" + hashlib.sha256(_canonical_bytes(material)).hexdigest()

    def _canonical_digest_rows(self) -> list[tuple[str, str, int, str]]:
        rows: list[tuple[str, str, int, str]] = []
        for episode in self._all_episodes():
            rows.append(("episodes", episode.uuid, _bucket_of("episodes", episode.uuid), _row_hash("episodes", asdict(episode))))
        for fact in self.all_facts():
            rows.append(("facts", fact.uuid, _bucket_of("facts", fact.uuid), _row_hash("facts", asdict(fact))))
        for relation in self.all_relations():
            rows.append((
                "typed_relations", relation.relation_id,
                _bucket_of("typed_relations", relation.relation_id), _row_hash("typed_relations", asdict(relation)),
            ))
        return rows

    @staticmethod
    def _bucket_digests(rows: list[tuple[str, str, int, str]]) -> list[str]:
        buckets: list[list[str]] = [[] for _ in range(DIGEST_BUCKETS)]
        for _, _, bucket, row_hash in rows:
            buckets[bucket].append(row_hash)
        return [_bucket_digest(values) for values in buckets]

    def recompute_bucketed_digest(self) -> str:
        """Full recomputation from the canonical tables themselves (never from the index)."""

        return self._bucketed_root(self._bucket_digests(self._canonical_digest_rows()))

    def rebuild_digest_index(self) -> str:
        """Rebuild the maintained digest index from canonical rows; return the root."""

        rows = self._canonical_digest_rows()
        digests = self._bucket_digests(rows)
        self._connection.execute("DELETE FROM digest_rows")
        self._connection.execute("DELETE FROM digest_buckets")
        self._connection.executemany(
            "INSERT INTO digest_rows(table_name, row_key, bucket, row_hash) VALUES(?, ?, ?, ?)", rows
        )
        self._connection.executemany(
            "INSERT INTO digest_buckets(bucket, digest) VALUES(?, ?)", list(enumerate(digests))
        )
        self._digest_dirty.clear()
        self._digest_index_trusted = True
        return self._bucketed_root(digests)

    def incremental_state_digest(self) -> str:
        """Bring the digest index current for rows changed since the last call; return the root.

        Cost is O(changed rows + rows in touched buckets + bucket count), independent of
        total store size for bounded buckets. ``recompute_bucketed_digest`` reproduces the
        same root from the canonical tables alone.
        """

        if not self._digest_index_trusted:
            return self.rebuild_digest_index()
        touched: set[int] = set()
        for table, key in sorted(self._digest_dirty):
            bucket = _bucket_of(table, key)
            touched.add(bucket)
            payload = self._row_payload(table, key)
            if payload is None:
                self._connection.execute(
                    "DELETE FROM digest_rows WHERE table_name = ? AND row_key = ?", (table, key)
                )
            else:
                self._connection.execute(
                    "INSERT INTO digest_rows(table_name, row_key, bucket, row_hash) VALUES(?, ?, ?, ?) "
                    "ON CONFLICT(table_name, row_key) DO UPDATE SET bucket = excluded.bucket, "
                    "row_hash = excluded.row_hash",
                    (table, key, bucket, _row_hash(table, payload)),
                )
        for bucket in sorted(touched):
            hashes = [
                row[0]
                for row in self._connection.execute(
                    "SELECT row_hash FROM digest_rows WHERE bucket = ?", (bucket,)
                ).fetchall()
            ]
            self._connection.execute(
                "UPDATE digest_buckets SET digest = ? WHERE bucket = ?", (_bucket_digest(hashes), bucket)
            )
        self._digest_dirty.clear()
        digests = [
            row[0]
            for row in self._connection.execute("SELECT digest FROM digest_buckets ORDER BY bucket").fetchall()
        ]
        return self._bucketed_root(digests)

    def verify_recorded_state_digest(self, recorded: str) -> bool:
        """Recovery-time full verification for either digest scheme, from canonical rows.

        Never consults the maintained index to decide the answer. As a side effect it
        checks the index row-for-row against the canonical rows and trusts it only when
        they match; otherwise the next persist rebuilds it. Nothing is written here.
        """

        if recorded.startswith(f"{BUCKETED_DIGEST_SCHEME}:"):
            rows = self._canonical_digest_rows()
            digests = self._bucket_digests(rows)
            if self._bucketed_root(digests) != recorded:
                return False
            indexed = {
                (row[0], row[1], int(row[2]), row[3])
                for row in self._connection.execute(
                    "SELECT table_name, row_key, bucket, row_hash FROM digest_rows"
                ).fetchall()
            }
            stored = [
                row[0]
                for row in self._connection.execute("SELECT digest FROM digest_buckets ORDER BY bucket").fetchall()
            ]
            self._digest_index_trusted = indexed == set(rows) and stored == digests
            return True
        if recorded.startswith(LEGACY_DIGEST_PREFIX):
            # Legacy full-JSON commitment; the index is rebuilt at the next persist.
            self._digest_index_trusted = False
            return self.state_digest() == recorded
        return False

    # -- light runtime-state reads (#522) --

    def read_runtime_binding(self) -> tuple[int, str | None] | None:
        """(generation, journal_record_digest) without parsing the whole state blob."""

        row = self._connection.execute(
            "SELECT json_extract(payload_json, '$.generation'), "
            "json_extract(payload_json, '$.journal_record_digest') FROM runtime_state WHERE singleton = 1"
        ).fetchone()
        if row is None:
            return None
        return int(row[0] or 0), row[1]

    def read_runtime_journal_tail(self) -> dict | None:
        row = self._connection.execute(
            "SELECT payload_json FROM runtime_journal ORDER BY generation DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        value = json.loads(row[0])
        if not isinstance(value, dict):
            raise ValueError("SQLite runtime journal row is malformed")
        return value

    def _all_episodes(self) -> tuple[Episode, ...]:
        rows = self._connection.execute(
            "SELECT uuid, content, source_description, valid_at, group_id FROM episodes ORDER BY uuid"
        ).fetchall()
        return tuple(Episode(**dict(row)) for row in rows)
