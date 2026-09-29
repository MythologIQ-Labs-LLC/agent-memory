from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_canonical_json_v2_migration_contract import validate as validate_base_contract


EXPECTED_TRANSACTION_FIELDS = {
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
}
EXPECTED_CLOSEOUT_FIELDS = {"restart_verified", "outcome"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate(path: Path, repo_root: Path) -> dict[str, Any]:
    validate_base_contract(path, repo_root)
    payload = json.loads(path.read_bytes())

    target = payload.get("qualification_target", {})
    _require(target.get("kind") == "disposable_verified_copy", "qualification target must be a disposable verified copy")
    _require(target.get("source_store_read_only") is True, "qualification source store must remain read-only")
    _require(
        target.get("candidate_transaction_applies_only_to_copy") is True,
        "candidate transaction must apply only to the qualification copy",
    )
    _require(target.get("copy_identity_bound_to_source_generation") is True, "qualification copy must bind source generation")
    _require(target.get("production_cutover") is False, "#622 must not define production cutover")

    phases = payload["phases"]
    phase4 = set(map(str, phases[3].get("requires", [])))
    phase5 = set(map(str, phases[4].get("requires", [])))
    _require(
        "candidate_transaction_targets_disposable_verified_copy" in phase4,
        "phase 4 must target only the disposable qualification copy",
    )
    _require(
        "transaction_provenance_marks_pending_restart_verification" in phase4,
        "phase 4 provenance must remain pending restart verification",
    )
    _require(
        "qualification_closeout_records_final_outcome_without_runtime_write" in phase5,
        "phase 5 must record final outcome without a runtime write",
    )

    partition = payload.get("provenance_partition", {})
    durable = partition.get("durable_transaction_record", {})
    closeout = partition.get("post_restart_qualification_closeout", {})

    _require(durable.get("written_in_phase") == 4, "durable transaction provenance must be written in phase 4")
    _require(durable.get("durable_runtime_write") is True, "phase 4 transaction provenance must be durable")
    _require(set(map(str, durable.get("fields", []))) == EXPECTED_TRANSACTION_FIELDS, "transaction provenance field partition changed")
    _require(
        durable.get("transaction_outcome") == "committed_pending_restart_verification",
        "phase 4 may claim only committed_pending_restart_verification",
    )
    _require(
        durable.get("may_claim_final_migration_committed") is False,
        "phase 4 provenance must never claim final migration success",
    )

    _require(closeout.get("produced_in_phase") == 5, "qualification closeout must be produced in phase 5")
    _require(closeout.get("durable_runtime_write") is False, "phase 5 closeout must not mutate runtime state")
    _require(set(map(str, closeout.get("fields", []))) == EXPECTED_CLOSEOUT_FIELDS, "qualification closeout field partition changed")
    _require(closeout.get("committed_outcome") == "committed", "final qualification outcome changed")
    _require(
        closeout.get("committed_requires_restart_verified") is True,
        "final committed outcome must require restart verification",
    )
    _require(closeout.get("authority_effect") == "none", "qualification closeout must not grant authority")

    invariants = set(map(str, payload.get("success_invariants", [])))
    _require(
        "phase4_transaction_provenance_never_claims_final_migration_success" in invariants,
        "transaction/final-outcome separation invariant missing",
    )
    _require(
        "phase5_final_outcome_is_qualification_evidence_not_runtime_mutation" in invariants,
        "phase-5 closeout boundary invariant missing",
    )

    post_commit_failure = next(
        row for row in payload.get("failure_injections", []) if row.get("id") == "fail_post_commit_restart_verification"
    )
    _require(
        post_commit_failure.get("expected")
        == "candidate_copy_is_rejected_and_final_migration_outcome_not_marked_committed",
        "post-commit restart failure must reject the candidate copy without claiming final success",
    )

    return {
        "qualification_target": "disposable_verified_copy",
        "source_store_read_only": True,
        "phase4_transaction_outcome": "committed_pending_restart_verification",
        "phase5_final_outcome": "committed_only_after_restart_verification",
        "phase5_runtime_write": False,
        "production_cutover": False,
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
