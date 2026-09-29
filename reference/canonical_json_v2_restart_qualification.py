from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import tempfile

from agentmem_ref.restart_runtime import RuntimeRecoveryError
from agentmem_ref.sqlite_runtime import SQLiteRestartSafeRuntime

from canonical_json_v2_sqlite_preflight import (
    SQLiteMigrationPreflightResult,
    _profile_from_state,
)
from canonical_json_v2_transaction_qualification import (
    CandidateMigrationError,
    CandidateRestartQualification,
    qualify_candidate_v2_restart as _qualify_candidate_v2_restart,
)
from canonical_scheme_registry_candidate import CandidateSchemeRegistry


# The only refusal that proves ordinary production recovery excludes the
# qualification-only envelope. A missing file, profile mismatch, corrupted database
# or unrelated integrity failure is not that proof.
EXPECTED_PRODUCTION_REFUSAL_REASON = "unsupported SQLite runtime state schema"

@dataclass(frozen=True)
class ProductionRecoveryRefusalEvidence:
    source_candidate_database: str
    tested_database_kind: str
    production_recovery_refused: bool
    refusal_type: str
    refusal_reason: str


def _read_candidate_state(path: Path) -> dict:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
    try:
        connection.execute("PRAGMA query_only = ON")
        row = connection.execute("SELECT payload_json FROM runtime_state WHERE singleton = 1").fetchone()
    finally:
        connection.close()
    if row is None:
        raise CandidateMigrationError("candidate_runtime_state_missing")
    try:
        state = json.loads(row[0])
    except (TypeError, json.JSONDecodeError) as exc:
        raise CandidateMigrationError("candidate_runtime_state_invalid") from exc
    if not isinstance(state, dict):
        raise CandidateMigrationError("candidate_runtime_state_invalid")
    return state


def _backup_read_only(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
    destination_connection = sqlite3.connect(str(destination), isolation_level=None)
    try:
        source_connection.execute("PRAGMA query_only = ON")
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def prove_production_runtime_refusal(
    preflight: SQLiteMigrationPreflightResult,
) -> ProductionRecoveryRefusalEvidence:
    """Prove ordinary production recovery refuses the candidate on a throwaway copy.

    Production recovery owns writable runtime initialization, so it must never be
    pointed at the qualification evidence database merely to prove that it refuses
    the qualification-only schema. The proof therefore operates on a second SQLite
    backup and discards it immediately afterward.
    """

    candidate_db = Path(preflight.evidence.snapshot_database)
    candidate_state = _read_candidate_state(candidate_db)
    profile = _profile_from_state(candidate_state)

    with tempfile.TemporaryDirectory(prefix="agent-memory-v2-production-refusal-") as temp:
        refusal_root = Path(temp)
        refusal_db = refusal_root / "agent-memory.sqlite3"
        _backup_read_only(candidate_db, refusal_db)
        try:
            runtime = SQLiteRestartSafeRuntime.recover(refusal_root, profile=profile)
        except RuntimeRecoveryError as exc:
            if str(exc) != EXPECTED_PRODUCTION_REFUSAL_REASON:
                raise CandidateMigrationError("production_recovery_refused_for_unexpected_reason", str(exc)) from exc
            return ProductionRecoveryRefusalEvidence(
                source_candidate_database=str(candidate_db),
                tested_database_kind="disposable_backup",
                production_recovery_refused=True,
                refusal_type=type(exc).__name__,
                refusal_reason=str(exc),
            )
        else:
            runtime.close()
            raise CandidateMigrationError("production_recovery_accepted_qualification_envelope")


def qualify_candidate_v2_restart(
    preflight: SQLiteMigrationPreflightResult,
    *,
    fault: str | None = None,
    registry: CandidateSchemeRegistry | None = None,
    prove_production_refusal: bool = True,
) -> CandidateRestartQualification:
    """Run phase-5 qualification without ever giving production runtime the candidate.

    The independent candidate verifier always uses a read-only SQLite connection.
    When the production-refusal proof is requested, that proof is executed against
    an additional disposable backup after candidate verification succeeds.
    """

    qualification = _qualify_candidate_v2_restart(preflight, fault=fault, registry=registry)
    if prove_production_refusal:
        evidence = prove_production_runtime_refusal(preflight)
        if not evidence.production_recovery_refused or evidence.refusal_reason != EXPECTED_PRODUCTION_REFUSAL_REASON:
            raise CandidateMigrationError("production_recovery_refused_for_unexpected_reason")
    return qualification
