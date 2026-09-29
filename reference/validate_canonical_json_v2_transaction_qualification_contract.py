from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EXPECTED_SUBSTRATE_JSON = {
    "facts.episode_uuids_json",
    "facts.attributes_json",
    "typed_relations.evidence_refs_json",
    "typed_relations.attributes_json",
}
EXPECTED_GOVERNANCE_JSON = {
    "governance_entries.value_json",
    "governance_log.value_json",
    "governance_residual.value_json",
}
EXPECTED_TRANSITION_JSON = {
    "canonicalization_migration.payload_json",
    "runtime_state.payload_json",
    "runtime_journal.payload_json[candidate_generation]",
}
EXPECTED_DERIVED = {
    "digest_rows",
    "digest_buckets",
    "governance_entries.entry_hash",
    "governance_buckets",
    "governance_log.chain",
}
EXPECTED_FAILURES = {
    "before_transaction",
    "after_persisted_byte_rewrite",
    "after_derived_integrity_rebuild",
    "after_provenance_write",
    "before_envelope_and_journal",
    "after_envelope_before_journal",
    "before_commit",
    "during_phase5_restart_verification",
}
EXPECTED_REFUSALS = {
    "legacy_scheme_with_v2_bytes",
    "v2_scheme_with_legacy_bytes",
    "mixed_legacy_v2_derived_indexes",
    "candidate_envelope_with_legacy_rows",
    "candidate_rows_with_legacy_envelope",
    "candidate_commitment_tamper",
    "migration_provenance_tamper",
    "provenance_present_but_commitment_invalid",
    "mixed_source_candidate_generation",
    "broken_candidate_journal_provenance_binding",
    "logical_state_mismatch_with_self_consistent_provenance",
}
EXPECTED_INVARIANTS = {
    "original_source_store_never_mutated",
    "no_durable_write_before_phase4_transaction",
    "all_phase4_changes_commit_or_roll_back_together",
    "candidate_json_bytes_are_exact_v2_bytes_not_merely_parse_equivalent",
    "candidate_commitments_match_phase3_preflight_exactly",
    "pre_and_post_logical_state_digest_are_identical",
    "candidate_generation_is_exactly_source_generation_plus_one",
    "durable_provenance_is_integrity_bound_but_not_verification_authority",
    "ordinary_production_recovery_refuses_qualification_envelope",
    "phase5_final_outcome_requires_independent_restart_verification",
    "phase5_performs_no_runtime_write",
}
EXPECTED_DURABLE_PROVENANCE_FIELDS = {
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
    "transaction_outcome",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _set(value: Any) -> set[str]:
    return {str(item) for item in value or []}


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_bytes())
    if not isinstance(payload, dict):
        raise ValueError(f"expected object fixture: {path}")
    return payload


def validate(path: Path, repo_root: Path) -> dict[str, Any]:
    payload = _load(path)
    _require(payload.get("fixture_id") == "agent-memory-canonical-json-v2-transaction-qualification-v1", "fixture id changed")
    _require(payload.get("status") == "FROZEN_PREIMPLEMENTATION_TRANSACTION_QUALIFICATION_CONTRACT", "fixture status changed")
    _require(payload.get("owner_issue") == 625 and payload.get("parent_issue") == 622, "issue ownership changed")
    _require(payload.get("qualification_only") is True, "contract must remain qualification-only")
    _require(payload.get("production_activation") is False, "contract must not activate production v2")
    _require(payload.get("production_recovery_support") is False, "contract must not add production recovery support")

    target = payload.get("target", {})
    _require(target.get("kind") == "disposable_verified_copy", "phase 4 must target only the disposable verified copy")
    _require(target.get("source_store_read_only") is True, "source store must remain read-only")
    _require(target.get("transaction_protocol") == "single_sqlite_begin_immediate", "transaction protocol changed")
    _require(target.get("transaction_generation_delta") == 1, "migration must advance exactly one generation")
    _require(target.get("phase5_runtime_write") is False, "phase 5 must perform no runtime write")

    candidate = payload.get("candidate_identity", {})
    _require(candidate.get("canonicalizer") == "agent-memory-canonical-json-v2", "candidate canonicalizer changed")
    _require(candidate.get("substrate_scheme") == "bmerkle-v2", "candidate substrate scheme changed")
    _require(candidate.get("governance_scheme") == "gsect-v2", "candidate governance scheme changed")
    _require(candidate.get("runtime_state_schema") == "1.2.0-canonical-v2-qualification", "candidate runtime schema changed")
    _require(candidate.get("journal_schema") == "1.1.0-canonical-v2-qualification", "candidate journal schema changed")
    _require(candidate.get("registry_operation") == "inspect", "candidate registry operation must remain inspect-only")

    surfaces = payload.get("persisted_json_byte_surfaces", {})
    _require(_set(surfaces.get("substrate")) == EXPECTED_SUBSTRATE_JSON, "substrate JSON byte surface changed")
    _require(_set(surfaces.get("governance")) == EXPECTED_GOVERNANCE_JSON, "governance JSON byte surface changed")
    _require(_set(surfaces.get("transition")) == EXPECTED_TRANSITION_JSON, "transition JSON byte surface changed")
    _require(_set(payload.get("derived_integrity_rebuild")) == EXPECTED_DERIVED, "derived integrity rebuild surface changed")

    provenance = payload.get("provenance", {})
    _require(provenance.get("table") == "canonicalization_migration", "provenance table changed")
    _require(provenance.get("row_identity") == "singleton=1", "provenance row identity changed")
    _require(provenance.get("payload_encoding") == "agent-memory-canonical-json-v2", "provenance encoding changed")
    _require(_set(provenance.get("durable_fields")) == EXPECTED_DURABLE_PROVENANCE_FIELDS, "durable provenance field set changed")
    _require(provenance.get("transaction_outcome") == "committed_pending_restart_verification", "phase-4 outcome changed")
    _require(provenance.get("final_outcome_forbidden_in_runtime_state") is True, "runtime must not claim final migration success")
    _require(
        _set(provenance.get("bound_by"))
        == {"candidate_journal.migration_provenance_digest", "candidate_runtime_state.migration_provenance_digest"},
        "provenance integrity binding changed",
    )

    journal = payload.get("candidate_journal", {})
    _require(journal.get("rewrites_historical_rows") is False, "historical journal bytes must not be rewritten")
    _require(journal.get("record_digest_encoding") == "agent-memory-canonical-json-v2", "candidate journal digest encoding changed")
    _require("migration_provenance_digest" in _set(journal.get("record_digest_material_fields")), "journal must bind provenance digest")

    state = payload.get("candidate_runtime_state", {})
    _require(state.get("ordinary_runtime_recovery_must_refuse") is True, "production recovery refusal boundary changed")
    _require(state.get("encoding") == "agent-memory-canonical-json-v2", "candidate runtime-state encoding changed")
    _require(state.get("durability_profile") == "sqlite_transactional_runtime_v1", "durability profile changed")
    _require("migration_provenance_digest" in _set(state.get("required_fields")), "runtime state must bind provenance digest")

    closeout = payload.get("phase5_closeout", {})
    _require(_set(closeout.get("fields")) == {"restart_verified", "outcome"}, "phase-5 closeout fields changed")
    _require(closeout.get("restart_verified") is True and closeout.get("outcome") == "committed", "phase-5 success semantics changed")
    _require(closeout.get("durable_runtime_write") is False, "phase-5 closeout must not mutate runtime")
    _require(closeout.get("authority_effect") == "none", "phase-5 closeout must not grant authority")

    _require(_set(payload.get("failure_injections")) == EXPECTED_FAILURES, "failure-injection boundary changed")
    _require(_set(payload.get("adversarial_refusals")) == EXPECTED_REFUSALS, "adversarial refusal set changed")
    _require(_set(payload.get("success_invariants")) == EXPECTED_INVARIANTS, "success invariant set changed")

    migration_contract = _load(repo_root / str(payload["preflight_contract"]))
    _require(migration_contract.get("qualification_target", {}).get("source_store_read_only") is True, "#623 source-read-only boundary drifted")
    _require(migration_contract.get("phases", [])[4].get("durable_writes_allowed") is False, "#623 phase-5 write boundary drifted")

    registry = _load(repo_root / str(payload["scheme_registry_source"]))
    bindings = {str(item.get("binding_id")): item for item in registry.get("bindings", [])}
    for binding_id in ("substrate-bmerkle-v2-candidate", "governance-gsect-v2-candidate"):
        binding = bindings.get(binding_id)
        _require(binding is not None, f"missing frozen candidate registry binding {binding_id}")
        _require(binding.get("runtime_state_schemas") == [], f"{binding_id} unexpectedly gained production runtime schema")
        _require(binding.get("activation") == "candidate_not_emittable", f"{binding_id} unexpectedly became emittable")
        _require(
            binding.get("envelope_requirement") == "new_runtime_state_schema_required_before_activation",
            f"{binding_id} candidate envelope requirement changed",
        )

    cases = {str(item.get("id")): item for item in registry.get("cases", [])}
    emission_case = cases.get("candidate-bmerkle-v2-emission-refuses")
    _require(emission_case is not None, "candidate emission refusal case disappeared")
    _require(emission_case.get("expected_refusal") == "candidate_activation_forbidden", "candidate emission refusal changed")

    sqlite_source = (repo_root / "reference/agentmem_ref/state/sqlite_substrate.py").read_text(encoding="utf-8")
    for column in ("episode_uuids_json", "attributes_json", "evidence_refs_json", "value_json", "entry_hash", "chain"):
        _require(column in sqlite_source, f"frozen persistence column disappeared: {column}")
    for table in ("digest_rows", "digest_buckets", "governance_entries", "governance_buckets", "governance_log", "governance_residual"):
        _require(table in sqlite_source, f"frozen derived table disappeared: {table}")

    runtime_source = (repo_root / "reference/agentmem_ref/runtime/sqlite_runtime.py").read_text(encoding="utf-8")
    _require(candidate["runtime_state_schema"] not in runtime_source, "qualification runtime schema leaked into production recovery")
    _require(candidate["journal_schema"] not in runtime_source, "qualification journal schema leaked into production runtime")

    return {
        "fixture_id": payload["fixture_id"],
        "qualification_only": True,
        "source_store_read_only": True,
        "phase4_transaction": "single_sqlite_begin_immediate",
        "phase5_runtime_write": False,
        "production_recovery_support": False,
        "candidate_registry_operation": "inspect",
        "candidate_registry_activation": "candidate_not_emittable",
        "persisted_json_surfaces": len(EXPECTED_SUBSTRATE_JSON | EXPECTED_GOVERNANCE_JSON | EXPECTED_TRANSITION_JSON),
        "failure_injections": len(EXPECTED_FAILURES),
        "adversarial_refusals": len(EXPECTED_REFUSALS),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        type=Path,
        default=Path("reference/fixtures/runtime/canonical-json-v2-transaction-qualification-v1.json"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    report = validate(args.fixture, args.repo_root.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
