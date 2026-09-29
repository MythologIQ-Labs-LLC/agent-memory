from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_FIXTURE_ID = "agent-memory-canonical-json-v2-migration-v1"
EXPECTED_STATUS = "FROZEN_PREIMPLEMENTATION_MIGRATION_CONTRACT"
EXPECTED_PHASES = [
    "verify_source",
    "reconstruct_and_validate",
    "compute_candidate_commitments",
    "transactional_recommit",
    "post_commit_restart_verification",
]
EXPECTED_REFUSALS = {
    "tampered_substrate_row",
    "tampered_substrate_commitment",
    "tampered_governance_state",
    "tampered_governance_commitment",
    "broken_journal_or_envelope_binding",
    "unknown_or_mixed_scheme_binding",
    "nonfinite_fact_attribute",
    "nonfinite_relation_attribute",
    "nonfinite_extension_state",
    "invalid_unicode_scalar_or_object_key",
    "source_generation_changed_before_transaction",
    "legacy_scheme_with_v2_bytes",
    "v2_scheme_with_legacy_bytes",
    "rollback_envelope_with_incompatible_rows",
    "mixed_candidate_and_legacy_generation",
    "provenance_present_but_commitment_invalid",
}
EXPECTED_FAILURE_INJECTIONS = {
    "fail_before_transaction",
    "fail_after_candidate_state_write",
    "fail_before_envelope_and_journal",
    "fail_before_commit",
    "fail_post_commit_restart_verification",
}
REQUIRED_PROVENANCE_FIELDS = {
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
    "accepted_canonical_vector_source",
    "scheme_registry_source",
    "migration_implementation_id",
    "migration_transaction_generation",
    "pre_migration_logical_state_digest",
    "post_migration_logical_state_digest",
    "restart_verified",
    "outcome",
}
REQUIRED_SUCCESS_INVARIANTS = {
    "source_verified_before_candidate_computation",
    "candidate_value_domain_validated_before_transaction",
    "no_durable_writes_before_transaction",
    "single_transaction_for_scheme_transition_state_provenance_envelope_and_journal",
    "source_generation_checked_again_inside_transaction",
    "post_migration_logical_state_equals_pre_migration_logical_state",
    "restart_verification_required_before_committed_outcome",
    "migration_provenance_is_evidence_not_verification",
}
SUBSTRATE_SOURCE_MARKERS = {
    'def _row_hash(table: str, payload: dict) -> str:',
    'def _bucket_digest(row_hashes: list[str]) -> str:',
    'def _bucketed_root(self, bucket_digests: list[str]) -> str:',
    '"scheme": BUCKETED_DIGEST_SCHEME,',
    'return f"{BUCKETED_DIGEST_SCHEME}:" + hashlib.sha256(_canonical_bytes(material)).hexdigest()',
}
GOVERNANCE_SOURCE_MARKERS = {
    'def _governance_entry_hash(section: str, key: str, value_json: str) -> str:',
    'def _governance_chain(section: str, seq: int, previous: str, value_json: str) -> str:',
    'def _governance_map_root(section: str, bucket_digests: list[str]) -> str:',
    'def _governance_root(map_roots: dict[str, str], logs: dict[str, dict], residual_digest: str) -> str:',
    '"scheme": GOVERNANCE_SCHEME,',
    'return f"{GOVERNANCE_SCHEME}:" + hashlib.sha256(_canonical_bytes(material)).hexdigest()',
}


def _ids(rows: list[dict[str, Any]]) -> set[str]:
    return {str(row["id"]) for row in rows}


def _require_source_markers(source: str, markers: set[str], label: str) -> None:
    missing = sorted(marker for marker in markers if marker not in source)
    if missing:
        raise ValueError(f"{label} commitment construction drifted; re-qualify before migration: {missing}")


def validate(path: Path, repo_root: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    payload = json.loads(raw)

    if payload.get("fixture_id") != EXPECTED_FIXTURE_ID:
        raise ValueError("unexpected migration fixture id")
    if payload.get("status") != EXPECTED_STATUS:
        raise ValueError("migration contract status changed")
    if payload.get("authority_effect") != "none":
        raise ValueError("migration qualification must not grant authority")
    if payload.get("automatic_recovery_migration") is not False:
        raise ValueError("automatic recovery migration must remain forbidden")
    if payload.get("production_activation") is not False:
        raise ValueError("production activation must remain forbidden")

    phases = payload.get("phases")
    if not isinstance(phases, list) or [row.get("id") for row in phases] != EXPECTED_PHASES:
        raise ValueError("migration phases or order changed")
    if [row.get("phase") for row in phases] != [1, 2, 3, 4, 5]:
        raise ValueError("migration phase numbers changed")
    if any(row.get("durable_writes_allowed") is not False for row in phases[:3]):
        raise ValueError("durable writes became possible before transactional phase")
    if phases[3].get("durable_writes_allowed") is not True:
        raise ValueError("transactional recommit is not the sole durable-write phase")
    if phases[3].get("transaction") != "single_sqlite_begin_immediate":
        raise ValueError("migration transaction contract changed")
    if phases[4].get("durable_writes_allowed") is not False:
        raise ValueError("post-commit verification must not introduce durable writes")

    phase4_requires = set(map(str, phases[3].get("requires", [])))
    for required in (
        "all_prior_phases_passed",
        "source_generation_still_current",
        "candidate_commitments_reverified_before_commit",
        "candidate_state_and_provenance_written_in_same_transaction",
        "candidate_runtime_envelope_and_journal_written_in_same_transaction",
    ):
        if required not in phase4_requires:
            raise ValueError(f"transactional guard missing: {required}")

    phase5_requires = set(map(str, phases[4].get("requires", [])))
    for required in (
        "database_closed",
        "database_reopened",
        "candidate_substrate_commitment_verified",
        "candidate_governance_commitment_verified",
        "candidate_journal_chain_verified",
        "logical_state_matches_pre_migration_snapshot",
    ):
        if required not in phase5_requires:
            raise ValueError(f"restart verification guard missing: {required}")

    contracts = payload.get("candidate_commitment_contracts")
    if not isinstance(contracts, dict):
        raise ValueError("candidate commitment contracts missing")
    substrate = contracts.get("bmerkle_v2_candidate", {})
    governance = contracts.get("gsect_v2_candidate", {})
    for name, contract in (("bmerkle_v2_candidate", substrate), ("gsect_v2_candidate", governance)):
        if contract.get("canonicalizer") != "agent-memory-canonical-json-v2":
            raise ValueError(f"{name} canonicalizer changed")
        if contract.get("must_version_entire_commitment_construction") is not True:
            raise ValueError(f"{name} no longer versions full commitment construction")
        if contract.get("must_not_relabel_v1_root") is not True:
            raise ValueError(f"{name} allows relabeling v1 root")

    substrate_layers = set(map(str, substrate.get("canonicalized_layers", [])))
    if substrate_layers != {
        "row_material",
        "sorted_row_hash_lists_for_bucket_digest",
        "final_bucket_root_material",
    }:
        raise ValueError("candidate bmerkle-v2 layer coverage changed")
    governance_layers = set(map(str, governance.get("canonicalized_layers", [])))
    if governance_layers != {
        "map_entry_values",
        "entry_hash_material",
        "log_entry_values",
        "log_chain_material",
        "map_root_material",
        "residual_material",
        "final_governance_root_material",
    }:
        raise ValueError("candidate gsect-v2 layer coverage changed")

    sqlite_source_path = repo_root / "reference" / "agentmem_ref" / "state" / "sqlite_substrate.py"
    sqlite_source = sqlite_source_path.read_text(encoding="utf-8")
    _require_source_markers(sqlite_source, SUBSTRATE_SOURCE_MARKERS, "substrate v1")
    _require_source_markers(sqlite_source, GOVERNANCE_SOURCE_MARKERS, "governance v1")

    if set(map(str, payload.get("provenance_required_fields", []))) != REQUIRED_PROVENANCE_FIELDS:
        raise ValueError("migration provenance fields changed")
    if set(map(str, payload.get("success_invariants", []))) != REQUIRED_SUCCESS_INVARIANTS:
        raise ValueError("migration success invariants changed")

    refusals = payload.get("refusal_cases")
    if not isinstance(refusals, list) or _ids(refusals) != EXPECTED_REFUSALS:
        raise ValueError("migration refusal coverage changed")
    for row in refusals:
        phase = int(row["stop_before_phase"])
        if phase < 2 or phase > 5:
            raise ValueError(f"invalid refusal stop phase for {row['id']}")
        if not str(row.get("expected_refusal", "")):
            raise ValueError(f"missing refusal reason for {row['id']}")

    injections = payload.get("failure_injections")
    if not isinstance(injections, list) or _ids(injections) != EXPECTED_FAILURE_INJECTIONS:
        raise ValueError("failure-injection coverage changed")
    for row in injections:
        if int(row["phase"]) not in {3, 4, 5}:
            raise ValueError(f"failure injection moved to unsupported phase: {row['id']}")

    for key in ("accepted_canonical_vector_source", "scheme_registry_source"):
        source = repo_root / str(payload[key])
        if not source.is_file():
            raise ValueError(f"referenced accepted source missing: {source}")

    non_goals = set(map(str, payload.get("semantic_non_goals", [])))
    for required in (
        "authority_change",
        "automatic_migration_on_recovery",
        "default_v2_scheme_activation",
        "legacy_verifier_removal",
        "rust_runtime_promotion",
        "adr_040_acceptance",
    ):
        if required not in non_goals:
            raise ValueError(f"migration stop line weakened: {required}")

    return {
        "fixture_id": payload["fixture_id"],
        "source_main_sha": payload["source_main_sha"],
        "phase_count": len(phases),
        "refusal_case_count": len(refusals),
        "failure_injection_count": len(injections),
        "durable_write_phase": 4,
        "v1_commitment_construction_tethered": True,
        "automatic_recovery_migration": False,
        "production_activation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("reference/fixtures/runtime/canonical-json-v2-migration-v1.json"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = validate(args.fixture, args.repo_root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
