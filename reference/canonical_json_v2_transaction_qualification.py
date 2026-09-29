from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Mapping

from agentmem_ref.restart_runtime import RuntimeRecoveryError
from agentmem_ref.sqlite_runtime import (
    SQLITE_DURABILITY_PROFILE,
    SQLITE_TRANSACTION_PROTOCOL,
    _validate_journal,
)
from agentmem_ref.sqlite_substrate import SQLITE_SUBSTRATE_SCHEMA_VERSION
from agentmem_ref.substrate import TYPED_RELATION_SCHEMA_VERSION

from canonical_json_v2_candidate import (
    CanonicalJsonV2Error,
    canonical_bytes_v2,
    canonicalize_json_text_v2,
)
from canonical_json_v2_migration_preflight import (
    DIGEST_BUCKETS,
    GOVERNANCE_BUCKETS,
    GOVERNANCE_LOG_SECTIONS,
    GOVERNANCE_MAP_SECTIONS,
    MigrationPreflightError,
    _bucket_digest,
    _governance_bucket,
    _governance_chain,
    _governance_entry_hash,
    _substrate_bucket,
    _substrate_row_hash,
    compute_candidate_commitments,
)
from canonical_json_v2_sqlite_preflight import (
    RUNTIME_PROFILE_ANCHOR_DOMAIN,
    SUBSTRATE_IDENTITY_ANCHOR_DOMAIN,
    SQLiteMigrationPreflightResult,
    _resolve_target_binding,
    compute_source_identity_anchor,
    historical_journal_anchor_digest,
    qualify_sqlite_migration_preflight,
    read_raw_runtime_journal,
    structured_anchor_digest,
)
from canonical_scheme_registry_candidate import CandidateSchemeRegistry


QUALIFICATION_RUNTIME_STATE_SCHEMA = "1.2.0-canonical-v2-qualification"
QUALIFICATION_JOURNAL_SCHEMA = "1.1.0-canonical-v2-qualification"
MIGRATION_IMPLEMENTATION_ID = "agent-memory-canonical-v2-qualification-migration-v1"
ACCEPTED_VECTOR_SOURCE = "reference/fixtures/runtime/canonical-json-v2-vectors-accepted-v1.json"
SCHEME_REGISTRY_SOURCE = "reference/fixtures/runtime/canonicalization-scheme-registry-v1.json"
TRANSACTION_OUTCOME = "committed_pending_restart_verification"
PROVENANCE_TABLE = "canonicalization_migration"
# Exact key sets. Verification rejects missing and unexpected keys alike, so no extra
# field can acquire significance by having integrity material rebuilt around it.
CANDIDATE_RUNTIME_STATE_FIELDS = frozenset(
    {
        "schema_version",
        "durability_profile",
        "transaction_protocol",
        "generation",
        "profile",
        "interpretation_digest",
        "substrate_scheme",
        "substrate_digest",
        "governance_scheme",
        "governance_digest",
        "substrate_identity",
        "migration_provenance_digest",
        "journal_record_digest",
    }
)
CANDIDATE_JOURNAL_MATERIAL_FIELDS = (
    "schema_version",
    "transaction_protocol",
    "generation",
    "substrate_digest",
    "governance_digest",
    "interpretation_digest",
    "previous_record_digest",
    "migration_provenance_digest",
)
CANDIDATE_JOURNAL_FIELDS = frozenset({*CANDIDATE_JOURNAL_MATERIAL_FIELDS, "record_digest"})
ANCHOR_FIELDS = (
    "source_journal_tail_record_digest",
    "historical_journal_row_count",
    "historical_journal_digest",
    "source_runtime_profile_digest",
    "source_interpretation_digest",
    "source_substrate_identity_digest",
)


class CandidateMigrationError(ValueError):
    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


class InjectedMigrationFailure(RuntimeError):
    def __init__(self, point: str) -> None:
        self.point = point
        super().__init__(f"injected migration failure: {point}")


@dataclass(frozen=True)
class CandidateTransactionEvidence:
    database: str
    source_generation: int
    migration_generation: int
    substrate_commitment: str
    governance_commitment: str
    logical_state_digest: str
    migration_provenance_digest: str
    transaction_outcome: str = TRANSACTION_OUTCOME

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateRestartQualification:
    database: str
    generation: int
    substrate_commitment: str
    governance_commitment: str
    logical_state_digest: str
    migration_provenance_digest: str
    restart_verified: bool = True
    outcome: str = "committed"
    authority_effect: str = "none"
    durable_runtime_write: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_prefixed(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _canonical_text(value: Any) -> str:
    try:
        return canonical_bytes_v2(value).decode("utf-8")
    except CanonicalJsonV2Error as exc:
        raise CandidateMigrationError("candidate_value_domain_invalid", exc.reason) from exc


def _canonical_digest(value: Any) -> str:
    return _sha256_prefixed(_canonical_text(value).encode("utf-8"))


def _strict_json(text: str, *, exact_v2: bool, surface: str) -> Any:
    try:
        canonical = canonicalize_json_text_v2(text)
        value = json.loads(text)
    except (CanonicalJsonV2Error, json.JSONDecodeError, UnicodeError) as exc:
        reason = exc.reason if isinstance(exc, CanonicalJsonV2Error) else "invalid_json_text"
        raise CandidateMigrationError("candidate_persisted_json_invalid", f"{surface}: {reason}") from exc
    if exact_v2 and canonical.decode("utf-8") != text:
        raise CandidateMigrationError("candidate_persisted_bytes_not_v2", surface)
    return value


def _inject(requested: str | None, point: str) -> None:
    if requested == point:
        raise InjectedMigrationFailure(point)


def _connect(path: Path, *, read_only: bool) -> sqlite3.Connection:
    if read_only:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None, timeout=30.0)
        connection.execute("PRAGMA query_only = ON")
    else:
        connection = sqlite3.connect(str(path), isolation_level=None, timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _integrity_check(connection: sqlite3.Connection) -> None:
    row = connection.execute("PRAGMA integrity_check").fetchone()
    if row is None or str(row[0]).lower() != "ok":
        raise CandidateMigrationError("candidate_sqlite_integrity_failed")


def _read_runtime_state_raw(connection: sqlite3.Connection) -> tuple[str, dict[str, Any]]:
    row = connection.execute("SELECT payload_json FROM runtime_state WHERE singleton = 1").fetchone()
    if row is None:
        raise CandidateMigrationError("candidate_runtime_state_missing")
    text = str(row[0])
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CandidateMigrationError("candidate_runtime_state_invalid") from exc
    if not isinstance(value, dict):
        raise CandidateMigrationError("candidate_runtime_state_invalid")
    return text, value


def _meta(connection: sqlite3.Connection, key: str) -> str:
    row = connection.execute("SELECT value FROM agent_memory_meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        raise CandidateMigrationError("candidate_substrate_metadata_missing", key)
    return str(row[0])


def _read_logical_state(
    connection: sqlite3.Connection,
    *,
    require_exact_v2: bool,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], dict[str, list[Any]], dict[str, Any]]:
    episodes = [
        {
            "uuid": str(row["uuid"]),
            "content": str(row["content"]),
            "source_description": str(row["source_description"]),
            "valid_at": str(row["valid_at"]),
            "group_id": str(row["group_id"]),
        }
        for row in connection.execute(
            "SELECT uuid, content, source_description, valid_at, group_id FROM episodes ORDER BY uuid"
        )
    ]

    facts: list[dict[str, Any]] = []
    for row in connection.execute(
        "SELECT uuid, fact_text, group_id, episode_uuids_json, valid_at, invalid_at, created_at, expired_at, attributes_json "
        "FROM facts ORDER BY uuid"
    ):
        episodes_value = _strict_json(
            str(row["episode_uuids_json"]), exact_v2=require_exact_v2, surface=f"facts[{row['uuid']}].episode_uuids_json"
        )
        attributes = _strict_json(
            str(row["attributes_json"]), exact_v2=require_exact_v2, surface=f"facts[{row['uuid']}].attributes_json"
        )
        if not isinstance(episodes_value, list) or not isinstance(attributes, dict):
            raise CandidateMigrationError("candidate_substrate_shape_invalid", str(row["uuid"]))
        facts.append(
            {
                "uuid": str(row["uuid"]),
                "fact_text": str(row["fact_text"]),
                "group_id": str(row["group_id"]),
                "episode_uuids": tuple(str(item) for item in episodes_value),
                "valid_at": row["valid_at"],
                "invalid_at": row["invalid_at"],
                "created_at": row["created_at"],
                "expired_at": row["expired_at"],
                "attributes": attributes,
            }
        )

    relations: list[dict[str, Any]] = []
    for row in connection.execute(
        "SELECT relation_id, source_uuid, target_uuid, relation_type, group_id, evidence_refs_json, retrieval_weight, "
        "valid_at, invalid_at, created_at, expired_at, attributes_json FROM typed_relations ORDER BY relation_id"
    ):
        refs = _strict_json(
            str(row["evidence_refs_json"]), exact_v2=require_exact_v2, surface=f"relations[{row['relation_id']}].evidence_refs_json"
        )
        attributes = _strict_json(
            str(row["attributes_json"]), exact_v2=require_exact_v2, surface=f"relations[{row['relation_id']}].attributes_json"
        )
        if not isinstance(refs, list) or not isinstance(attributes, dict):
            raise CandidateMigrationError("candidate_substrate_shape_invalid", str(row["relation_id"]))
        relations.append(
            {
                "relation_id": str(row["relation_id"]),
                "source_uuid": str(row["source_uuid"]),
                "target_uuid": str(row["target_uuid"]),
                "relation_type": str(row["relation_type"]),
                "group_id": str(row["group_id"]),
                "evidence_refs": tuple(str(item) for item in refs),
                "retrieval_weight": float(row["retrieval_weight"]),
                "valid_at": row["valid_at"],
                "invalid_at": row["invalid_at"],
                "created_at": row["created_at"],
                "expired_at": row["expired_at"],
                "attributes": attributes,
            }
        )

    maps: dict[str, dict[str, Any]] = {section: {} for section in GOVERNANCE_MAP_SECTIONS}
    for row in connection.execute(
        "SELECT section, entry_key, value_json FROM governance_entries ORDER BY section, entry_key"
    ):
        section = str(row["section"])
        if section not in maps:
            raise CandidateMigrationError("candidate_governance_shape_invalid", f"unknown map section {section}")
        maps[section][str(row["entry_key"])] = _strict_json(
            str(row["value_json"]),
            exact_v2=require_exact_v2,
            surface=f"governance_entries[{section},{row['entry_key']}].value_json",
        )

    logs: dict[str, list[Any]] = {section: [] for section in GOVERNANCE_LOG_SECTIONS}
    expected_seq = {section: 1 for section in GOVERNANCE_LOG_SECTIONS}
    for row in connection.execute("SELECT section, seq, value_json FROM governance_log ORDER BY section, seq"):
        section = str(row["section"])
        if section not in logs:
            raise CandidateMigrationError("candidate_governance_shape_invalid", f"unknown log section {section}")
        seq = int(row["seq"])
        if seq != expected_seq[section]:
            raise CandidateMigrationError("candidate_governance_shape_invalid", f"non-contiguous {section} log")
        logs[section].append(
            _strict_json(
                str(row["value_json"]),
                exact_v2=require_exact_v2,
                surface=f"governance_log[{section},{seq}].value_json",
            )
        )
        expected_seq[section] += 1

    residual_row = connection.execute("SELECT value_json FROM governance_residual WHERE singleton = 1").fetchone()
    if residual_row is None:
        raise CandidateMigrationError("candidate_governance_shape_invalid", "missing residual")
    residual = _strict_json(
        str(residual_row["value_json"]), exact_v2=require_exact_v2, surface="governance_residual.value_json"
    )
    if not isinstance(residual, dict):
        raise CandidateMigrationError("candidate_governance_shape_invalid", "residual must be object")

    substrate = {
        "schema_version": _meta(connection, "schema_version"),
        "relation_schema_version": _meta(connection, "relation_schema_version"),
        "id_counter": int(_meta(connection, "id_counter")),
        "episodes": episodes,
        "facts": facts,
        "relations": relations,
    }
    if substrate["schema_version"] != SQLITE_SUBSTRATE_SCHEMA_VERSION:
        raise CandidateMigrationError("candidate_substrate_schema_changed")
    if substrate["relation_schema_version"] != TYPED_RELATION_SCHEMA_VERSION:
        raise CandidateMigrationError("candidate_relation_schema_changed")
    return substrate, maps, logs, residual


def _rewrite_persisted_json_bytes(connection: sqlite3.Connection) -> None:
    for row in connection.execute("SELECT uuid, episode_uuids_json, attributes_json FROM facts ORDER BY uuid").fetchall():
        connection.execute(
            "UPDATE facts SET episode_uuids_json = ?, attributes_json = ? WHERE uuid = ?",
            (
                canonicalize_json_text_v2(str(row["episode_uuids_json"])).decode("utf-8"),
                canonicalize_json_text_v2(str(row["attributes_json"])).decode("utf-8"),
                str(row["uuid"]),
            ),
        )
    for row in connection.execute(
        "SELECT relation_id, evidence_refs_json, attributes_json FROM typed_relations ORDER BY relation_id"
    ).fetchall():
        connection.execute(
            "UPDATE typed_relations SET evidence_refs_json = ?, attributes_json = ? WHERE relation_id = ?",
            (
                canonicalize_json_text_v2(str(row["evidence_refs_json"])).decode("utf-8"),
                canonicalize_json_text_v2(str(row["attributes_json"])).decode("utf-8"),
                str(row["relation_id"]),
            ),
        )
    for row in connection.execute("SELECT section, entry_key, value_json FROM governance_entries").fetchall():
        connection.execute(
            "UPDATE governance_entries SET value_json = ? WHERE section = ? AND entry_key = ?",
            (
                canonicalize_json_text_v2(str(row["value_json"])).decode("utf-8"),
                str(row["section"]),
                str(row["entry_key"]),
            ),
        )
    for row in connection.execute("SELECT section, seq, value_json FROM governance_log").fetchall():
        connection.execute(
            "UPDATE governance_log SET value_json = ? WHERE section = ? AND seq = ?",
            (
                canonicalize_json_text_v2(str(row["value_json"])).decode("utf-8"),
                str(row["section"]),
                int(row["seq"]),
            ),
        )
    row = connection.execute("SELECT value_json FROM governance_residual WHERE singleton = 1").fetchone()
    if row is None:
        raise CandidateMigrationError("candidate_governance_shape_invalid", "missing residual")
    connection.execute(
        "UPDATE governance_residual SET value_json = ? WHERE singleton = 1",
        (canonicalize_json_text_v2(str(row["value_json"])).decode("utf-8"),),
    )


def _expected_substrate_index(substrate: Mapping[str, Any]) -> tuple[dict[tuple[str, str], tuple[int, str]], list[str]]:
    rows: dict[tuple[str, str], tuple[int, str]] = {}
    buckets: list[list[str]] = [[] for _ in range(DIGEST_BUCKETS)]
    for table, values, key_name in (
        ("episodes", substrate["episodes"], "uuid"),
        ("facts", substrate["facts"], "uuid"),
        ("typed_relations", substrate["relations"], "relation_id"),
    ):
        for payload in values:
            key = str(payload[key_name])
            bucket = _substrate_bucket(table, key)
            row_hash = _substrate_row_hash(table, payload)
            rows[(table, key)] = (bucket, row_hash)
            buckets[bucket].append(row_hash)
    return rows, [_bucket_digest(values) for values in buckets]


def _rebuild_substrate_index(connection: sqlite3.Connection, substrate: Mapping[str, Any]) -> None:
    expected_rows, expected_buckets = _expected_substrate_index(substrate)
    connection.execute("DELETE FROM digest_rows")
    connection.execute("DELETE FROM digest_buckets")
    connection.executemany(
        "INSERT INTO digest_rows(table_name, row_key, bucket, row_hash) VALUES(?, ?, ?, ?)",
        [(table, key, bucket, row_hash) for (table, key), (bucket, row_hash) in sorted(expected_rows.items())],
    )
    connection.executemany(
        "INSERT INTO digest_buckets(bucket, digest) VALUES(?, ?)",
        [(index, digest) for index, digest in enumerate(expected_buckets)],
    )


def _expected_governance_index(
    maps: Mapping[str, Mapping[str, Any]],
    logs: Mapping[str, list[Any]],
    residual: Mapping[str, Any],
) -> tuple[dict[tuple[str, str], tuple[int, str, str]], dict[tuple[str, int], str], dict[tuple[str, int], tuple[str, str]], str]:
    entries: dict[tuple[str, str], tuple[int, str, str]] = {}
    buckets_out: dict[tuple[str, int], str] = {}
    for section in GOVERNANCE_MAP_SECTIONS:
        per_bucket: list[list[str]] = [[] for _ in range(GOVERNANCE_BUCKETS)]
        for raw_key, value in maps[section].items():
            key = str(raw_key)
            value_json = _canonical_text(value)
            bucket = _governance_bucket(section, key)
            entry_hash = _governance_entry_hash(section, key, value_json)
            entries[(section, key)] = (bucket, value_json, entry_hash)
            per_bucket[bucket].append(entry_hash)
        for index, values in enumerate(per_bucket):
            buckets_out[(section, index)] = _bucket_digest(values)

    log_rows: dict[tuple[str, int], tuple[str, str]] = {}
    for section in GOVERNANCE_LOG_SECTIONS:
        head = ""
        for seq, value in enumerate(logs[section], start=1):
            value_json = _canonical_text(value)
            head = _governance_chain(section, seq, head, value_json)
            log_rows[(section, seq)] = (value_json, head)
    return entries, buckets_out, log_rows, _canonical_text(dict(residual))


def _rebuild_governance_index(
    connection: sqlite3.Connection,
    maps: Mapping[str, Mapping[str, Any]],
    logs: Mapping[str, list[Any]],
    residual: Mapping[str, Any],
) -> None:
    entries, buckets, log_rows, residual_json = _expected_governance_index(maps, logs, residual)
    for (section, key), (bucket, value_json, entry_hash) in entries.items():
        connection.execute(
            "UPDATE governance_entries SET bucket = ?, value_json = ?, entry_hash = ? WHERE section = ? AND entry_key = ?",
            (bucket, value_json, entry_hash, section, key),
        )
    connection.execute("DELETE FROM governance_buckets")
    connection.executemany(
        "INSERT INTO governance_buckets(section, bucket, digest) VALUES(?, ?, ?)",
        [(section, bucket, digest) for (section, bucket), digest in sorted(buckets.items())],
    )
    for (section, seq), (value_json, chain) in log_rows.items():
        connection.execute(
            "UPDATE governance_log SET value_json = ?, chain = ? WHERE section = ? AND seq = ?",
            (value_json, chain, section, seq),
        )
    connection.execute(
        "UPDATE governance_residual SET value_json = ? WHERE singleton = 1",
        (residual_json,),
    )


def _verify_derived_indexes(
    connection: sqlite3.Connection,
    substrate: Mapping[str, Any],
    maps: Mapping[str, Mapping[str, Any]],
    logs: Mapping[str, list[Any]],
    residual: Mapping[str, Any],
) -> None:
    expected_rows, expected_buckets = _expected_substrate_index(substrate)
    observed_rows = {
        (str(row["table_name"]), str(row["row_key"])): (int(row["bucket"]), str(row["row_hash"]))
        for row in connection.execute("SELECT table_name, row_key, bucket, row_hash FROM digest_rows")
    }
    if observed_rows != expected_rows:
        raise CandidateMigrationError("candidate_substrate_index_mismatch")
    observed_buckets = {
        int(row["bucket"]): str(row["digest"])
        for row in connection.execute("SELECT bucket, digest FROM digest_buckets")
    }
    if observed_buckets != {index: digest for index, digest in enumerate(expected_buckets)}:
        raise CandidateMigrationError("candidate_substrate_index_mismatch")

    expected_entries, expected_governance_buckets, expected_logs, expected_residual = _expected_governance_index(
        maps, logs, residual
    )
    observed_entries = {
        (str(row["section"]), str(row["entry_key"])): (int(row["bucket"]), str(row["value_json"]), str(row["entry_hash"]))
        for row in connection.execute("SELECT section, entry_key, bucket, value_json, entry_hash FROM governance_entries")
    }
    if observed_entries != expected_entries:
        raise CandidateMigrationError("candidate_governance_index_mismatch")
    observed_governance_buckets = {
        (str(row["section"]), int(row["bucket"])): str(row["digest"])
        for row in connection.execute("SELECT section, bucket, digest FROM governance_buckets")
    }
    if observed_governance_buckets != expected_governance_buckets:
        raise CandidateMigrationError("candidate_governance_index_mismatch")
    observed_logs = {
        (str(row["section"]), int(row["seq"])): (str(row["value_json"]), str(row["chain"]))
        for row in connection.execute("SELECT section, seq, value_json, chain FROM governance_log")
    }
    if observed_logs != expected_logs:
        raise CandidateMigrationError("candidate_governance_index_mismatch")
    row = connection.execute("SELECT value_json FROM governance_residual WHERE singleton = 1").fetchone()
    if row is None or str(row["value_json"]) != expected_residual:
        raise CandidateMigrationError("candidate_governance_index_mismatch")


def _provenance_payload(preflight: SQLiteMigrationPreflightResult, post_logical_digest: str) -> dict[str, Any]:
    evidence = preflight.evidence
    return {
        "source_runtime_generation": evidence.source_runtime_generation,
        "source_runtime_state_schema": evidence.source_runtime_state_schema,
        "source_substrate_binding_id": evidence.source_substrate_binding_id,
        "source_substrate_commitment": evidence.source_substrate_commitment,
        "source_governance_binding_id": evidence.source_governance_binding_id,
        "source_governance_commitment": evidence.source_governance_commitment,
        "target_substrate_binding_id": evidence.target_substrate_binding_id,
        "target_substrate_commitment": evidence.target_substrate_commitment,
        "target_governance_binding_id": evidence.target_governance_binding_id,
        "target_governance_commitment": evidence.target_governance_commitment,
        "accepted_canonical_vector_source": ACCEPTED_VECTOR_SOURCE,
        "scheme_registry_source": SCHEME_REGISTRY_SOURCE,
        "migration_implementation_id": MIGRATION_IMPLEMENTATION_ID,
        "migration_transaction_generation": evidence.source_runtime_generation + 1,
        "pre_migration_logical_state_digest": evidence.pre_migration_logical_state_digest,
        "post_migration_logical_state_digest": post_logical_digest,
        "transaction_outcome": TRANSACTION_OUTCOME,
    }


def _candidate_journal_record(
    *,
    generation: int,
    substrate_digest: str,
    governance_digest: str,
    interpretation_digest: str,
    previous_record_digest: str,
    migration_provenance_digest: str,
) -> dict[str, Any]:
    material = {
        "schema_version": QUALIFICATION_JOURNAL_SCHEMA,
        "transaction_protocol": SQLITE_TRANSACTION_PROTOCOL,
        "generation": generation,
        "substrate_digest": substrate_digest,
        "governance_digest": governance_digest,
        "interpretation_digest": interpretation_digest,
        "previous_record_digest": previous_record_digest,
        "migration_provenance_digest": migration_provenance_digest,
    }
    return {**material, "record_digest": _canonical_digest(material)}


def _raw_journal(connection: sqlite3.Connection) -> list[tuple[int, bytes, dict[str, Any]]]:
    try:
        return read_raw_runtime_journal(connection)
    except MigrationPreflightError as exc:
        if exc.reason == "journal_sql_generation_payload_mismatch":
            raise CandidateMigrationError("candidate_journal_generation_column_mismatch", str(exc)) from exc
        raise CandidateMigrationError("candidate_journal_invalid", str(exc)) from exc


def _verify_candidate_journal(
    connection: sqlite3.Connection,
    state: Mapping[str, Any],
    provenance_digest: str,
    preflight: SQLiteMigrationPreflightResult,
) -> None:
    evidence = preflight.evidence
    rows = _raw_journal(connection)
    if not rows:
        raise CandidateMigrationError("candidate_journal_missing")
    historical = rows[:-1]

    # History is established against the external phase-3 anchor, never against
    # values derived only from the candidate database.
    if len(historical) != evidence.historical_journal_row_count:
        raise CandidateMigrationError("candidate_historical_journal_anchor_mismatch")
    if historical_journal_anchor_digest([(g, p) for g, p, _ in historical]) != evidence.historical_journal_digest:
        raise CandidateMigrationError("candidate_historical_journal_anchor_mismatch")
    try:
        latest_legacy = _validate_journal([value for _, _, value in historical])
    except RuntimeRecoveryError as exc:
        raise CandidateMigrationError("candidate_historical_journal_invalid", str(exc)) from exc
    if latest_legacy is None or latest_legacy.get("record_digest") != evidence.source_journal_tail_record_digest:
        raise CandidateMigrationError("candidate_historical_journal_anchor_mismatch")

    final_generation, final_bytes, _ = rows[-1]
    final = _strict_json(
        final_bytes.decode("utf-8"), exact_v2=True, surface="runtime_journal.payload_json[candidate_generation]"
    )
    if not isinstance(final, dict) or set(final) != CANDIDATE_JOURNAL_FIELDS:
        raise CandidateMigrationError("candidate_journal_shape_invalid")
    if final["schema_version"] != QUALIFICATION_JOURNAL_SCHEMA:
        raise CandidateMigrationError("candidate_journal_schema_mismatch")
    if final["transaction_protocol"] != SQLITE_TRANSACTION_PROTOCOL:
        raise CandidateMigrationError("candidate_journal_protocol_mismatch")
    if final_generation != evidence.source_runtime_generation + 1 or final["generation"] != state.get("generation"):
        raise CandidateMigrationError("candidate_generation_mismatch")
    if final["previous_record_digest"] != evidence.source_journal_tail_record_digest:
        raise CandidateMigrationError("candidate_journal_chain_broken")
    if final["interpretation_digest"] != evidence.source_interpretation_digest:
        raise CandidateMigrationError("candidate_interpretation_digest_mismatch")
    if final["migration_provenance_digest"] != provenance_digest:
        raise CandidateMigrationError("candidate_journal_provenance_binding_broken")
    material = {key: final[key] for key in CANDIDATE_JOURNAL_MATERIAL_FIELDS}
    if final["record_digest"] != _canonical_digest(material):
        raise CandidateMigrationError("candidate_journal_digest_mismatch")
    if final["record_digest"] != state.get("journal_record_digest"):
        raise CandidateMigrationError("candidate_runtime_journal_binding_broken")
    for field in ("substrate_digest", "governance_digest", "interpretation_digest"):
        if final[field] != state.get(field):
            raise CandidateMigrationError("candidate_runtime_journal_binding_broken")


def _verify_preserved_envelope_identity(
    state: Mapping[str, Any],
    preflight: SQLiteMigrationPreflightResult,
    *,
    reason_prefix: str,
) -> None:
    evidence = preflight.evidence
    if structured_anchor_digest(RUNTIME_PROFILE_ANCHOR_DOMAIN, state.get("profile")) != evidence.source_runtime_profile_digest:
        raise CandidateMigrationError(f"{reason_prefix}_runtime_profile_identity_mismatch")
    if state.get("interpretation_digest") != evidence.source_interpretation_digest:
        raise CandidateMigrationError(f"{reason_prefix}_interpretation_digest_mismatch")
    if (
        structured_anchor_digest(SUBSTRATE_IDENTITY_ANCHOR_DOMAIN, state.get("substrate_identity"))
        != evidence.source_substrate_identity_digest
    ):
        raise CandidateMigrationError(f"{reason_prefix}_substrate_identity_mismatch")


def _read_and_verify_provenance(
    connection: sqlite3.Connection,
    preflight: SQLiteMigrationPreflightResult,
) -> tuple[dict[str, Any], str]:
    try:
        row = connection.execute(f"SELECT payload_json FROM {PROVENANCE_TABLE} WHERE singleton = 1").fetchone()
    except sqlite3.Error as exc:
        raise CandidateMigrationError("candidate_migration_provenance_missing") from exc
    if row is None:
        raise CandidateMigrationError("candidate_migration_provenance_missing")
    text = str(row["payload_json"])
    value = _strict_json(text, exact_v2=True, surface="canonicalization_migration.payload_json")
    if not isinstance(value, dict):
        raise CandidateMigrationError("candidate_migration_provenance_invalid")
    expected = _provenance_payload(preflight, preflight.evidence.pre_migration_logical_state_digest)
    if value != expected:
        raise CandidateMigrationError("candidate_migration_provenance_mismatch")
    return value, _canonical_digest(value)


def _verify_candidate_connection(
    connection: sqlite3.Connection,
    preflight: SQLiteMigrationPreflightResult,
    *,
    registry: CandidateSchemeRegistry,
) -> tuple[dict[str, Any], str]:
    _integrity_check(connection)
    state_text, state = _read_runtime_state_raw(connection)
    _strict_json(state_text, exact_v2=True, surface="runtime_state.payload_json")
    evidence = preflight.evidence
    if set(state) != CANDIDATE_RUNTIME_STATE_FIELDS:
        raise CandidateMigrationError("candidate_runtime_state_shape_invalid")
    if state.get("schema_version") != QUALIFICATION_RUNTIME_STATE_SCHEMA:
        raise CandidateMigrationError("candidate_runtime_schema_mismatch")
    if state.get("durability_profile") != SQLITE_DURABILITY_PROFILE:
        raise CandidateMigrationError("candidate_durability_profile_mismatch")
    if state.get("transaction_protocol") != SQLITE_TRANSACTION_PROTOCOL:
        raise CandidateMigrationError("candidate_transaction_protocol_mismatch")
    if int(state.get("generation", 0)) != evidence.source_runtime_generation + 1:
        raise CandidateMigrationError("candidate_generation_mismatch")
    if state.get("substrate_scheme") != "bmerkle-v2" or state.get("governance_scheme") != "gsect-v2":
        raise CandidateMigrationError("candidate_scheme_binding_failed")
    if state.get("substrate_digest") != evidence.target_substrate_commitment:
        raise CandidateMigrationError("candidate_substrate_commitment_mismatch")
    if state.get("governance_digest") != evidence.target_governance_commitment:
        raise CandidateMigrationError("candidate_governance_commitment_mismatch")
    try:
        _verify_preserved_envelope_identity(state, preflight, reason_prefix="candidate")
    except MigrationPreflightError as exc:
        raise CandidateMigrationError("candidate_runtime_profile_identity_mismatch", str(exc)) from exc

    substrate_binding = _resolve_target_binding(
        registry,
        domain="substrate_state",
        commitment=str(state["substrate_digest"]),
    )
    governance_binding = _resolve_target_binding(
        registry,
        domain="governance_state",
        commitment=str(state["governance_digest"]),
    )
    if substrate_binding.binding_id != evidence.target_substrate_binding_id:
        raise CandidateMigrationError("candidate_scheme_binding_failed")
    if governance_binding.binding_id != evidence.target_governance_binding_id:
        raise CandidateMigrationError("candidate_scheme_binding_failed")

    provenance, provenance_digest = _read_and_verify_provenance(connection, preflight)
    if state.get("migration_provenance_digest") != provenance_digest:
        raise CandidateMigrationError("candidate_runtime_provenance_binding_broken")

    substrate, maps, logs, residual = _read_logical_state(connection, require_exact_v2=True)
    candidate = compute_candidate_commitments(
        substrate_state=substrate,
        governance_maps=maps,
        governance_logs=logs,
        governance_residual=residual,
    )
    if candidate.substrate_commitment != evidence.target_substrate_commitment:
        raise CandidateMigrationError("candidate_substrate_commitment_mismatch")
    if candidate.governance_commitment != evidence.target_governance_commitment:
        raise CandidateMigrationError("candidate_governance_commitment_mismatch")
    if candidate.logical_state_digest != evidence.pre_migration_logical_state_digest:
        raise CandidateMigrationError("candidate_logical_state_mismatch")
    if provenance["post_migration_logical_state_digest"] != candidate.logical_state_digest:
        raise CandidateMigrationError("candidate_migration_provenance_mismatch")

    _verify_derived_indexes(connection, substrate, maps, logs, residual)
    _verify_candidate_journal(connection, state, provenance_digest, preflight)
    return state, provenance_digest


def _reverify_old_copy(preflight: SQLiteMigrationPreflightResult) -> None:
    snapshot_db = Path(preflight.evidence.snapshot_database)
    with tempfile.TemporaryDirectory(prefix="agent-memory-v2-phase4-reverify-") as temp:
        repeated = qualify_sqlite_migration_preflight(
            source_database=snapshot_db,
            snapshot_root=Path(temp),
        )
    a = preflight.evidence
    b = repeated.evidence
    fields = (
        "source_runtime_generation",
        "source_runtime_state_schema",
        "source_substrate_binding_id",
        "source_substrate_commitment",
        "source_governance_binding_id",
        "source_governance_commitment",
        "target_substrate_binding_id",
        "target_substrate_commitment",
        "target_governance_binding_id",
        "target_governance_commitment",
        "pre_migration_logical_state_digest",
    )
    if any(getattr(a, field) != getattr(b, field) for field in fields):
        raise CandidateMigrationError("source_generation_changed_before_transaction")
    if any(getattr(a, field) != getattr(b, field) for field in ANCHOR_FIELDS):
        raise CandidateMigrationError("source_identity_anchor_changed_before_transaction")


def _recheck_source_anchor_in_transaction(
    connection: sqlite3.Connection,
    old_state: Mapping[str, Any],
    preflight: SQLiteMigrationPreflightResult,
) -> None:
    """Inside BEGIN IMMEDIATE: the copy must still carry the phase-3 anchored identity."""

    try:
        observed = compute_source_identity_anchor(connection, old_state)
    except MigrationPreflightError as exc:
        raise CandidateMigrationError("source_journal_or_envelope_verification_failed", str(exc)) from exc
    evidence = preflight.evidence
    if (
        observed.source_journal_tail_record_digest != evidence.source_journal_tail_record_digest
        or observed.historical_journal_row_count != evidence.historical_journal_row_count
        or observed.historical_journal_digest != evidence.historical_journal_digest
    ):
        raise CandidateMigrationError("source_historical_journal_anchor_mismatch")
    if observed.source_runtime_profile_digest != evidence.source_runtime_profile_digest:
        raise CandidateMigrationError("source_runtime_profile_identity_mismatch")
    if observed.source_interpretation_digest != evidence.source_interpretation_digest:
        raise CandidateMigrationError("source_interpretation_digest_mismatch")
    if observed.source_substrate_identity_digest != evidence.source_substrate_identity_digest:
        raise CandidateMigrationError("source_substrate_identity_mismatch")


def transactional_recommit_candidate_v2(
    preflight: SQLiteMigrationPreflightResult,
    *,
    fault: str | None = None,
    registry: CandidateSchemeRegistry | None = None,
) -> CandidateTransactionEvidence:
    """Apply the qualification-only v2 transition to the disposable verified copy.

    The source database used to create ``preflight`` is not opened here. The only
    mutable target is ``preflight.evidence.snapshot_database``. All candidate byte,
    derived-integrity, provenance, runtime-envelope and journal changes live inside
    one explicit SQLite ``BEGIN IMMEDIATE`` transaction.
    """

    _reverify_old_copy(preflight)
    _inject(fault, "before_transaction")

    path = Path(preflight.evidence.snapshot_database)
    active_registry = registry or CandidateSchemeRegistry.from_frozen_fixture()
    connection = _connect(path, read_only=False)
    try:
        connection.execute("BEGIN IMMEDIATE")
        try:
            _, old_state = _read_runtime_state_raw(connection)
            evidence = preflight.evidence
            if (
                int(old_state.get("generation", 0)) != evidence.source_runtime_generation
                or old_state.get("schema_version") != evidence.source_runtime_state_schema
                or old_state.get("substrate_digest") != evidence.source_substrate_commitment
                or old_state.get("governance_digest") != evidence.source_governance_commitment
            ):
                raise CandidateMigrationError("source_generation_changed_before_transaction")
            _recheck_source_anchor_in_transaction(connection, old_state, preflight)

            _rewrite_persisted_json_bytes(connection)
            _inject(fault, "after_persisted_byte_rewrite")

            substrate, maps, logs, residual = _read_logical_state(connection, require_exact_v2=True)
            _rebuild_substrate_index(connection, substrate)
            _rebuild_governance_index(connection, maps, logs, residual)
            _inject(fault, "after_derived_integrity_rebuild")

            candidate = compute_candidate_commitments(
                substrate_state=substrate,
                governance_maps=maps,
                governance_logs=logs,
                governance_residual=residual,
            )
            if candidate.substrate_commitment != evidence.target_substrate_commitment:
                raise CandidateMigrationError("candidate_substrate_commitment_mismatch")
            if candidate.governance_commitment != evidence.target_governance_commitment:
                raise CandidateMigrationError("candidate_governance_commitment_mismatch")
            if candidate.logical_state_digest != evidence.pre_migration_logical_state_digest:
                raise CandidateMigrationError("candidate_logical_state_mismatch")

            provenance = _provenance_payload(preflight, candidate.logical_state_digest)
            provenance_text = _canonical_text(provenance)
            provenance_digest = _canonical_digest(provenance)
            connection.execute(
                f"CREATE TABLE {PROVENANCE_TABLE} (singleton INTEGER PRIMARY KEY CHECK(singleton = 1), payload_json TEXT NOT NULL)"
            )
            connection.execute(
                f"INSERT INTO {PROVENANCE_TABLE}(singleton, payload_json) VALUES(1, ?)",
                (provenance_text,),
            )
            _inject(fault, "after_provenance_write")
            _inject(fault, "before_envelope_and_journal")

            generation = evidence.source_runtime_generation + 1
            journal = _candidate_journal_record(
                generation=generation,
                substrate_digest=candidate.substrate_commitment,
                governance_digest=candidate.governance_commitment,
                interpretation_digest=evidence.source_interpretation_digest,
                previous_record_digest=evidence.source_journal_tail_record_digest,
                migration_provenance_digest=provenance_digest,
            )
            candidate_state = {
                "schema_version": QUALIFICATION_RUNTIME_STATE_SCHEMA,
                "durability_profile": SQLITE_DURABILITY_PROFILE,
                "transaction_protocol": SQLITE_TRANSACTION_PROTOCOL,
                "generation": generation,
                "profile": old_state["profile"],
                "interpretation_digest": old_state["interpretation_digest"],
                "substrate_scheme": "bmerkle-v2",
                "substrate_digest": candidate.substrate_commitment,
                "governance_scheme": "gsect-v2",
                "governance_digest": candidate.governance_commitment,
                "substrate_identity": old_state["substrate_identity"],
                "migration_provenance_digest": provenance_digest,
                "journal_record_digest": journal["record_digest"],
            }
            connection.execute(
                "UPDATE runtime_state SET payload_json = ? WHERE singleton = 1",
                (_canonical_text(candidate_state),),
            )
            _inject(fault, "after_envelope_before_journal")
            connection.execute(
                "INSERT INTO runtime_journal(generation, payload_json) VALUES(?, ?)",
                (generation, _canonical_text(journal)),
            )

            _verify_candidate_connection(connection, preflight, registry=active_registry)
            _inject(fault, "before_commit")
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
    finally:
        connection.close()

    return CandidateTransactionEvidence(
        database=str(path),
        source_generation=preflight.evidence.source_runtime_generation,
        migration_generation=preflight.evidence.source_runtime_generation + 1,
        substrate_commitment=preflight.evidence.target_substrate_commitment,
        governance_commitment=preflight.evidence.target_governance_commitment,
        logical_state_digest=preflight.evidence.pre_migration_logical_state_digest,
        migration_provenance_digest=provenance_digest,
    )


def qualify_candidate_v2_restart(
    preflight: SQLiteMigrationPreflightResult,
    *,
    fault: str | None = None,
    registry: CandidateSchemeRegistry | None = None,
) -> CandidateRestartQualification:
    """Independently verify the committed qualification copy without mutating it.

    This is a read-only candidate verifier only. It never hands the candidate to
    production recovery; the production-refusal proof lives in
    ``canonical_json_v2_restart_qualification.prove_production_runtime_refusal`` and
    runs on a second disposable backup.
    """

    path = Path(preflight.evidence.snapshot_database)
    active_registry = registry or CandidateSchemeRegistry.from_frozen_fixture()
    connection = _connect(path, read_only=True)
    try:
        _integrity_check(connection)
        _inject(fault, "during_phase5_restart_verification")
        state, provenance_digest = _verify_candidate_connection(
            connection,
            preflight,
            registry=active_registry,
        )
    finally:
        connection.close()

    return CandidateRestartQualification(
        database=str(path),
        generation=int(state["generation"]),
        substrate_commitment=str(state["substrate_digest"]),
        governance_commitment=str(state["governance_digest"]),
        logical_state_digest=preflight.evidence.pre_migration_logical_state_digest,
        migration_provenance_digest=provenance_digest,
    )
