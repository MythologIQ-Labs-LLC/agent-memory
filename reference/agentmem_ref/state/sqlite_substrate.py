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


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


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
        self._connection = sqlite3.connect(
            str(self.path),
            timeout=30.0,
            isolation_level=None,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._initialize_schema()
        self._ids = SqliteDeterministicIds(self._connection)

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
        try:
            yield
        except Exception:
            self._connection.execute("ROLLBACK")
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
    ) -> list[tuple[Fact, float]]:
        terms = _tokens(query)
        scored: list[tuple[Fact, float]] = []
        for fact in self._facts_for_groups(group_ids):
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

    def _all_episodes(self) -> tuple[Episode, ...]:
        rows = self._connection.execute(
            "SELECT uuid, content, source_description, valid_at, group_id FROM episodes ORDER BY uuid"
        ).fetchall()
        return tuple(Episode(**dict(row)) for row in rows)
