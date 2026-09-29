from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Sequence

from agentmem_ref.restart_runtime import CapabilityBinding, RuntimeProfile, RuntimeRecoveryError
from agentmem_ref.sqlite_runtime import SQLiteRestartSafeRuntime
from agentmem_ref.sqlite_substrate import (
    SQLITE_SUBSTRATE_SCHEMA_VERSION,
)
from agentmem_ref.substrate import TYPED_RELATION_SCHEMA_VERSION

from canonical_json_v2_candidate import CanonicalJsonV2Error, canonical_bytes_v2
from canonical_json_v2_migration_preflight import (
    CandidateCommitments,
    MigrationPreflightError,
    compute_candidate_commitments,
)
from canonical_scheme_registry_candidate import (
    CandidateSchemeRegistry,
    SchemeBinding,
    SchemeRegistryError,
)


LEGACY_CANONICALIZER = "legacy-python-sorted-json-v1"
CANDIDATE_CANONICALIZER = "agent-memory-canonical-json-v2"
SOURCE_ROOT_CONTRACTS = {
    ("substrate_state", "sha256:"): "substrate-full-json-sha256-v1",
    ("substrate_state", "bmerkle-v1:"): "substrate-bucketed-merkle-sha256-v1",
    ("governance_state", "sha256:"): "governance-full-json-sha256-v1",
    ("governance_state", "gsect-v1:"): "governance-sections-sha256-v1",
}
TARGET_ROOT_CONTRACTS = {
    "substrate_state": "substrate-bucketed-merkle-sha256-v2-candidate",
    "governance_state": "governance-sections-sha256-v2-candidate",
}
# Phase-3 external anchor domains (#625). Each digest is SHA-256 over a length-framed
# domain tag followed by length-framed material, so no two distinct inputs share a
# preimage and no anchor can be replayed as another.
HISTORICAL_JOURNAL_ANCHOR_DOMAIN = "agent-memory/v2-qualification/historical-runtime-journal/v1"
RUNTIME_PROFILE_ANCHOR_DOMAIN = "agent-memory/v2-qualification/runtime-profile/v1"
SUBSTRATE_IDENTITY_ANCHOR_DOMAIN = "agent-memory/v2-qualification/substrate-identity/v1"


@dataclass(frozen=True)
class SQLiteMigrationPreflightEvidence:
    source_runtime_generation: int
    source_runtime_state_schema: str
    source_substrate_binding_id: str
    source_substrate_commitment: str
    source_governance_binding_id: str
    source_governance_commitment: str
    target_substrate_binding_id: str
    target_substrate_commitment: str
    target_governance_binding_id: str
    target_governance_commitment: str
    pre_migration_logical_state_digest: str
    source_journal_tail_record_digest: str
    historical_journal_row_count: int
    historical_journal_digest: str
    source_runtime_profile_digest: str
    source_interpretation_digest: str
    source_substrate_identity_digest: str
    snapshot_database: str
    source_open_mode: str = "sqlite_mode_ro"
    source_store_read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SQLiteMigrationPreflightResult:
    evidence: SQLiteMigrationPreflightEvidence
    candidate: CandidateCommitments


def _source_uri(path: Path) -> str:
    return path.resolve().as_uri() + "?mode=ro"


def _open_source_read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise MigrationPreflightError("source_database_missing", f"SQLite source does not exist: {path}")
    try:
        connection = sqlite3.connect(_source_uri(path), uri=True, isolation_level=None, timeout=30.0)
    except sqlite3.Error as exc:
        raise MigrationPreflightError("source_database_open_failed", str(exc)) from exc
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _integrity_check(connection: sqlite3.Connection) -> None:
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as exc:
        raise MigrationPreflightError("source_sqlite_integrity_failed", str(exc)) from exc
    if row is None or str(row[0]).lower() != "ok":
        raise MigrationPreflightError("source_sqlite_integrity_failed")


def _runtime_state(connection: sqlite3.Connection) -> dict[str, Any]:
    try:
        row = connection.execute(
            "SELECT payload_json FROM runtime_state WHERE singleton = 1"
        ).fetchone()
    except sqlite3.Error as exc:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", str(exc)) from exc
    if row is None:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "runtime state is missing")
    try:
        state = json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as exc:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "runtime state is malformed") from exc
    if not isinstance(state, dict):
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "runtime state is malformed")
    return state


def _binding_material(state: Mapping[str, Any]) -> tuple[int, str, str, str, str]:
    try:
        generation = int(state["generation"])
        state_schema = str(state["schema_version"])
        substrate = str(state["substrate_digest"])
        governance = str(state["governance_digest"])
        journal = str(state["journal_record_digest"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "runtime binding is incomplete") from exc
    if generation < 1 or not state_schema or not substrate or not governance or not journal:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "runtime binding is incomplete")
    return generation, state_schema, substrate, governance, journal


def _frame(hasher: "hashlib._Hash", data: bytes) -> None:
    hasher.update(len(data).to_bytes(8, "big"))
    hasher.update(data)


def _anchor_hasher(domain: str) -> "hashlib._Hash":
    hasher = hashlib.sha256()
    _frame(hasher, domain.encode("utf-8"))
    return hasher


def historical_journal_anchor_digest(rows: Sequence[tuple[int, bytes]]) -> str:
    """Digest ordered ``runtime_journal`` rows as (SQL generation, raw payload bytes).

    The payload is hashed exactly as stored, never parsed and re-serialized, so an
    equal-value reserialization of any historical record changes the digest.
    """

    hasher = _anchor_hasher(HISTORICAL_JOURNAL_ANCHOR_DOMAIN)
    hasher.update(len(rows).to_bytes(8, "big"))
    for generation, payload in rows:
        if type(generation) is not int or not isinstance(payload, bytes):
            raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "journal row is malformed")
        hasher.update(generation.to_bytes(8, "big", signed=True))
        _frame(hasher, payload)
    return "sha256:" + hasher.hexdigest()


def structured_anchor_digest(domain: str, value: Any) -> str:
    """Deterministic digest of a structured envelope value under a named domain."""

    try:
        encoded = canonical_bytes_v2(value)
    except CanonicalJsonV2Error as exc:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", exc.reason) from exc
    hasher = _anchor_hasher(domain)
    _frame(hasher, encoded)
    return "sha256:" + hasher.hexdigest()


def read_raw_runtime_journal(connection: sqlite3.Connection) -> list[tuple[int, bytes, dict[str, Any]]]:
    """Read journal rows with exact stored payload bytes and the decoded record.

    Requires an INTEGER SQL generation, a TEXT payload holding a JSON object, and the
    SQL generation column to equal the payload's own ``generation`` field.
    """

    rows: list[tuple[int, bytes, dict[str, Any]]] = []
    for row in connection.execute(
        "SELECT typeof(generation), generation, typeof(payload_json), CAST(payload_json AS BLOB) "
        "FROM runtime_journal ORDER BY generation"
    ).fetchall():
        generation_type, generation, payload_type, payload = row[0], row[1], row[2], row[3]
        if generation_type != "integer" or payload_type != "text" or not isinstance(payload, bytes):
            raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "journal row type is malformed")
        try:
            value = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "journal row is malformed") from exc
        if not isinstance(value, dict):
            raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "journal row is malformed")
        payload_generation = value.get("generation")
        if type(payload_generation) is not int or payload_generation != generation:
            raise MigrationPreflightError(
                "journal_sql_generation_payload_mismatch",
                f"runtime_journal generation {generation} does not equal its payload generation",
            )
        rows.append((int(generation), bytes(payload), value))
    return rows


@dataclass(frozen=True)
class SourceIdentityAnchor:
    source_journal_tail_record_digest: str
    historical_journal_row_count: int
    historical_journal_digest: str
    source_runtime_profile_digest: str
    source_interpretation_digest: str
    source_substrate_identity_digest: str


def compute_source_identity_anchor(connection: sqlite3.Connection, state: Mapping[str, Any]) -> SourceIdentityAnchor:
    """Anchor the verified source journal and preserved runtime-envelope identity."""

    generation, _, _, _, bound_tail = _binding_material(state)
    rows = read_raw_runtime_journal(connection)
    if [item[0] for item in rows] != list(range(1, len(rows) + 1)) or len(rows) != generation:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "journal is not contiguous to generation")
    tail = rows[-1][2]
    if tail.get("record_digest") != bound_tail:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "runtime state does not bind journal tail")
    profile = state.get("profile")
    interpretation = state.get("interpretation_digest")
    substrate_identity = state.get("substrate_identity")
    if not isinstance(profile, dict) or not isinstance(substrate_identity, dict):
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "runtime identity is missing")
    if not isinstance(interpretation, str) or not interpretation:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "interpretation digest is missing")
    return SourceIdentityAnchor(
        source_journal_tail_record_digest=bound_tail,
        historical_journal_row_count=len(rows),
        historical_journal_digest=historical_journal_anchor_digest([(g, p) for g, p, _ in rows]),
        source_runtime_profile_digest=structured_anchor_digest(RUNTIME_PROFILE_ANCHOR_DOMAIN, profile),
        source_interpretation_digest=interpretation,
        source_substrate_identity_digest=structured_anchor_digest(SUBSTRATE_IDENTITY_ANCHOR_DOMAIN, substrate_identity),
    )


def _read_snapshot_anchor(snapshot_db: Path, source_state: Mapping[str, Any]) -> SourceIdentityAnchor:
    connection = _open_source_read_only(snapshot_db)
    try:
        state = _runtime_state(connection)
        if state != dict(source_state):
            raise MigrationPreflightError(
                "source_generation_changed_during_snapshot",
                "verified snapshot runtime envelope differs from the source envelope",
            )
        return compute_source_identity_anchor(connection, state)
    except sqlite3.Error as exc:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", str(exc)) from exc
    finally:
        connection.close()


def _profile_from_state(state: Mapping[str, Any]) -> RuntimeProfile:
    raw = state.get("profile")
    if not isinstance(raw, dict):
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "runtime profile is missing")
    try:
        return RuntimeProfile(
            runtime_version=str(raw["runtime_version"]),
            profile_id=str(raw["profile_id"]),
            profile_version=str(raw["profile_version"]),
            bindings=tuple(CapabilityBinding(**binding) for binding in raw.get("bindings", ())),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MigrationPreflightError("source_journal_or_envelope_verification_failed", "runtime profile is malformed") from exc


def _source_root_contract(domain: str, commitment: str) -> str:
    for (candidate_domain, prefix), contract in SOURCE_ROOT_CONTRACTS.items():
        if domain == candidate_domain and commitment.startswith(prefix):
            return contract
    raise MigrationPreflightError("source_scheme_binding_failed", f"unsupported source scheme for {domain}")


def _resolve_source_binding(
    registry: CandidateSchemeRegistry,
    *,
    domain: str,
    runtime_state_schema: str,
    commitment: str,
) -> SchemeBinding:
    try:
        return registry.resolve(
            operation="verify",
            domain=domain,
            recorded_commitment=commitment,
            requested_canonicalizer=LEGACY_CANONICALIZER,
            requested_root_contract=_source_root_contract(domain, commitment),
            runtime_state_schema=runtime_state_schema,
        )
    except (SchemeRegistryError, MigrationPreflightError) as exc:
        detail = exc.reason if isinstance(exc, SchemeRegistryError) else str(exc)
        raise MigrationPreflightError("source_scheme_binding_failed", detail) from exc


def _resolve_target_binding(
    registry: CandidateSchemeRegistry,
    *,
    domain: str,
    commitment: str,
) -> SchemeBinding:
    try:
        return registry.resolve(
            operation="inspect",
            domain=domain,
            recorded_commitment=commitment,
            requested_canonicalizer=CANDIDATE_CANONICALIZER,
            requested_root_contract=TARGET_ROOT_CONTRACTS[domain],
            runtime_state_schema=None,
        )
    except SchemeRegistryError as exc:
        raise MigrationPreflightError("candidate_scheme_binding_failed", exc.reason) from exc


def _copy_consistent_snapshot(
    source_db: Path,
    snapshot_db: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if snapshot_db.exists():
        raise MigrationPreflightError("snapshot_destination_exists", f"refusing to overwrite {snapshot_db}")
    snapshot_db.parent.mkdir(parents=True, exist_ok=True)

    source = _open_source_read_only(source_db)
    target: sqlite3.Connection | None = None
    try:
        _integrity_check(source)
        before = _runtime_state(source)
        before_binding = _binding_material(before)
        target = sqlite3.connect(str(snapshot_db), isolation_level=None, timeout=30.0)
        source.backup(target)
        after = _runtime_state(source)
        after_binding = _binding_material(after)
        if before_binding != after_binding:
            raise MigrationPreflightError(
                "source_generation_changed_during_snapshot",
                "source runtime binding changed while the qualification snapshot was created",
            )
        return before, after
    except sqlite3.Error as exc:
        raise MigrationPreflightError("source_snapshot_failed", str(exc)) from exc
    finally:
        if target is not None:
            target.close()
        source.close()


def _logical_candidate_state(runtime: SQLiteRestartSafeRuntime) -> tuple[dict, dict, dict, dict]:
    substrate = runtime.substrate
    substrate_state = {
        "schema_version": SQLITE_SUBSTRATE_SCHEMA_VERSION,
        "relation_schema_version": TYPED_RELATION_SCHEMA_VERSION,
        "id_counter": substrate.identifier_checkpoint(),
        "episodes": [asdict(item) for item in substrate._all_episodes()],
        "facts": [asdict(item) for item in substrate.all_facts()],
        "relations": [asdict(item) for item in substrate.all_relations()],
    }
    maps, logs = runtime.adapter.export_governance_sections()
    residual = runtime._governance_residual()
    return substrate_state, maps, logs, residual


def _classify_recovery_failure(exc: Exception) -> MigrationPreflightError:
    message = str(exc)
    lowered = message.lower()
    if "canonical substrate digest" in lowered:
        return MigrationPreflightError("source_substrate_verification_failed", message)
    if "governance" in lowered and ("digest" in lowered or "integrity" in lowered or "malformed" in lowered):
        return MigrationPreflightError("source_governance_verification_failed", message)
    if "journal" in lowered or "runtime state" in lowered or "generation" in lowered:
        return MigrationPreflightError("source_journal_or_envelope_verification_failed", message)
    return MigrationPreflightError("source_recovery_verification_failed", message)


def qualify_sqlite_migration_preflight(
    *,
    source_database: str | Path,
    snapshot_root: str | Path,
    registry: CandidateSchemeRegistry | None = None,
) -> SQLiteMigrationPreflightResult:
    """Verify a source store without opening it through a writable runtime handle.

    The source database is opened with SQLite ``mode=ro`` and used only as the source
    of SQLite's online backup API. Full Agent Memory recovery verification runs on the
    resulting disposable snapshot. Candidate v2 commitments are then computed entirely
    in memory from the recovered logical state. No runtime or canonicalization change is
    written to the source database.
    """

    source_db = Path(source_database)
    snapshot_root_path = Path(snapshot_root)
    snapshot_db = snapshot_root_path / "agent-memory.sqlite3"
    active_registry = registry or CandidateSchemeRegistry.from_frozen_fixture()

    source_state, _ = _copy_consistent_snapshot(source_db, snapshot_db)
    generation, state_schema, source_substrate, source_governance, _ = _binding_material(source_state)
    source_substrate_binding = _resolve_source_binding(
        active_registry,
        domain="substrate_state",
        runtime_state_schema=state_schema,
        commitment=source_substrate,
    )
    source_governance_binding = _resolve_source_binding(
        active_registry,
        domain="governance_state",
        runtime_state_schema=state_schema,
        commitment=source_governance,
    )
    profile = _profile_from_state(source_state)

    runtime: SQLiteRestartSafeRuntime | None = None
    try:
        runtime = SQLiteRestartSafeRuntime.recover(snapshot_root_path, profile=profile)
        recovered = runtime.recovery_evidence
        if recovered is None:
            raise MigrationPreflightError("source_recovery_verification_failed", "recovery evidence is missing")
        if (
            recovered.generation != generation
            or recovered.substrate_digest != source_substrate
            or recovered.governance_digest != source_governance
        ):
            raise MigrationPreflightError(
                "source_generation_changed_during_snapshot",
                "verified snapshot does not bind the source runtime generation and commitments",
            )

        substrate_state, maps, logs, residual = _logical_candidate_state(runtime)
        candidate = compute_candidate_commitments(
            substrate_state=substrate_state,
            governance_maps=maps,
            governance_logs=logs,
            governance_residual=residual,
        )
    except MigrationPreflightError:
        raise
    except (RuntimeRecoveryError, RuntimeError, ValueError, TypeError) as exc:
        raise _classify_recovery_failure(exc) from exc
    finally:
        if runtime is not None:
            runtime.close()

    # Anchored only after full recovery verification succeeded on the snapshot.
    anchor = _read_snapshot_anchor(snapshot_db, source_state)

    target_substrate_binding = _resolve_target_binding(
        active_registry,
        domain="substrate_state",
        commitment=candidate.substrate_commitment,
    )
    target_governance_binding = _resolve_target_binding(
        active_registry,
        domain="governance_state",
        commitment=candidate.governance_commitment,
    )

    evidence = SQLiteMigrationPreflightEvidence(
        source_runtime_generation=generation,
        source_runtime_state_schema=state_schema,
        source_substrate_binding_id=source_substrate_binding.binding_id,
        source_substrate_commitment=source_substrate,
        source_governance_binding_id=source_governance_binding.binding_id,
        source_governance_commitment=source_governance,
        target_substrate_binding_id=target_substrate_binding.binding_id,
        target_substrate_commitment=candidate.substrate_commitment,
        target_governance_binding_id=target_governance_binding.binding_id,
        target_governance_commitment=candidate.governance_commitment,
        pre_migration_logical_state_digest=candidate.logical_state_digest,
        **asdict(anchor),
        snapshot_database=str(snapshot_db),
    )
    return SQLiteMigrationPreflightResult(evidence=evidence, candidate=candidate)
