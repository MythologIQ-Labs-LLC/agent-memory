# Agent Memory Feature Index

Canonical cross-reference of implemented repository features against their primary source and verification surface. Detailed implementation history belongs in the linked plans and `docs/META_LEDGER.md`; this index stays deliberately compact so its current-state summary can be maintained without duplicating entire audit narratives.

**Feature ledger evidence boundary**: historical feature rows originally verified against `main` `56e44d3cd3cb9c4186596f6a064dd554d14c1940` (2026-09-12).  
**Current-state reconciliation**: 2026-10-13 against `main` `3eebb6d54e2a218c4fd10cf53c52acac8384c3e6`; feature rows were *not* re-executed. This is a bounded historical inventory, **not an exhaustive live feature or release-status ledger**. For current capability maturity see [System State](SYSTEM_STATE.md) and [Substrate Inventory](43-substrate-inventory-and-maturity.md).

## Coverage Summary

- Total feature rows: **26**
- **Verified at original row evidence boundaries**: 26
- **Unverified**: 0
- **N/A**: 0
- **Reserved ID**: FX025, held for the Sprint 4b JS/PAMA slice that did not ship

A `verified` row means the named implementation and verification surface were evidenced at the original feature boundary. It is not an assertion of exact-head tests, complete present-day coverage, or production qualification. This ledger intentionally does not duplicate every subsequent runtime feature.

## Reference Runtime, Governance, and Packaging

| ID | Feature | Primary source | Verification surface | Status |
|----|---------|----------------|----------------------|--------|
| FX001 | Installable wheel resolves canonical schemas and exposes the `agent-memory` console command outside the checkout | `setup.py`, `pyproject.toml`, `reference/agentmem_ref/core/receipts.py` | `.github/workflows/cli-doctor.yml` (`wheel-install`) | verified |
| FX002 | `receipts.schema_dir()` resolves source schemas first, packaged `_schemas/` second, and fails with an install-oriented error when neither exists | `reference/agentmem_ref/core/receipts.py` | `reference/tests/test_receipts_schema_location.py` | verified |
| FX003 | Cedar policy digest pin is line-ending independent | `reference/agentmem_ref/harness/cedar_policy_comparator.py`, `.gitattributes` | `reference/tests/test_cedar_policy_comparator.py` | verified |
| FX004 | Adapters sharing one substrate mint disjoint identifiers across facts, receipts, and events, including restart | `reference/agentmem_ref/state/substrate.py`, `runtime/adapter.py`, `runtime/restart_runtime.py` | `test_substrate_identity.py`, `test_substrate_identity_restart.py` | verified |
| FX005 | PAMA base decision table matches documented operation/risk cells, including ADR-038 `action_execution` | `reference/agentmem_ref/core/policy.py`, `docs/33-pama-decision-table.md` | `reference/tests/test_decision_table_doctrine.py` | verified |
| FX006 | Recall rejects candidates with missing scope metadata as `unknown_scope` | `reference/agentmem_ref/runtime/adapter.py` | `reference/tests/test_recall_unknown_scope.py` | verified |
| FX007 | Governed recall emits an audit event and schema-valid per-candidate admission decision | `reference/agentmem_ref/runtime/adapter.py` | `reference/tests/test_recall_authority_record.py` | verified |
| FX008 | Governed deletion enforces existence, tenant ownership, target binding, and staleness | `reference/agentmem_ref/runtime/adapter.py`, `runtime/restart_runtime.py` | `reference/tests/test_deletion_authority.py` | verified |
| FX009 | Review discharge derives self-approval from identity rather than trusting a caller assertion | `reference/agentmem_ref/core/policy.py` | `reference/tests/test_derived_authority.py` | verified |
| FX010 | Reusable grant evaluation verifies against an independently held ratification record | `reference/agentmem_ref/memory/reusable_grants.py` | `reference/tests/test_ratification_anchor.py` | verified |
| FX011 | External verification is dischargeable through proposal-bound attestation rather than assertion | `reference/agentmem_ref/core/policy.py`, governed mutation callers | `reference/tests/test_verified_discharge.py` | verified |
| FX012 | Refused proposals park with decision, remediation route, and correlation identity | `reference/agentmem_ref/core/pending_verification.py` | `reference/tests/test_pending_verification.py` | verified |
| FX013 | Evidence gets a derived qualification class/binding status and correlated evidence collapses into dependence groups | `reference/agentmem_ref/core/evidence_qualification.py` | `reference/tests/test_evidence_qualification.py` | verified |
| FX014 | Parked proposals are resumed by the evaluator with staleness and separation controls | `reference/agentmem_ref/core/resumption.py`, `pending_verification.py` | `reference/tests/test_governed_resumption.py` | verified |
| FX015 | `require_review` has a qualified-evidence discharge path with risk-sensitive strength requirements | `reference/agentmem_ref/core/policy.py` | `reference/tests/test_qualified_discharge.py` | verified |
| FX016 | Procedural memory, reusable grants, and DashClaw can produce checkable `EvidenceItem`s without self-certifying them | `memory/procedural_memory.py`, `memory/reusable_grants.py`, `memory/dashclaw_external_verdict.py` | `reference/tests/test_evidence_producers.py` | verified |
| FX017 | `require_review` fails closed against arbitrary `review_satisfied` / `approval_refs` assertions | `reference/agentmem_ref/core/policy.py`, `core/verification.py` | `test_fail_closed_review.py`, `test_flip_migration_markers.py` | verified |
| FX018 | Refused governed operations retain a traversable remediation path instead of disappearing | governed operation modules plus pending-verification registry | `reference/tests/test_fail_closed_review.py` | verified |
| FX019 | Ledger SESSION SEAL trees are anchored under `refs/seals/entry-<N>` and remotely verifiable | `scripts/anchor_seal.py`, `scripts/verify_seals.py`, `.github/workflows/seal-anchors.yml` | `reference/tests/test_seal_anchors.py` | verified |
| FX020 | Reference tests avoid package-relative imports so they load under all repository CI discover styles | `reference/tests/test_test_import_convention.py` | same | verified |
| FX021 | An approved medium DashClaw correction parks when it lacks qualifying transition evidence, and CI asserts the park rather than fabricating a commit | `reference/run_dashclaw_external_verdict.py`, `memory/dashclaw_external_verdict.py`, DashClaw workflow | `reference/tests/test_dashclaw_correction_parks.py` | verified |
| FX022 | `agentmem_ref` is organized into enforced layered subpackages with compatibility aliases for former flat imports | `scripts/restructure_package.py`, `reference/agentmem_ref/_paths.py`, layer packages | `reference/tests/test_package_layout.py` | verified |
| FX023 | `runtime_config` and `discovery` use the canonical packaged schema resolver; legacy `data-files` packaging is retired | `runtime/runtime_config.py`, `runtime/discovery.py`, `pyproject.toml` | `reference/tests/test_packaged_schema_resolution.py`, wheel smoke | verified |
| FX024 | Public API contract is schema-backed and versioned; contract 1.4.0 introduced the opt-in post-admission return budget (`returned`, `return_policy`). Subsequent additive changes are documented in the authoritative API contract; the implemented `CONTRACT_VERSION` is declared in `reference/agentmem_ref/api/contract.py`. Historical 1.4.0 feature evidence is not current-contract qualification | `reference/agentmem_ref/api/contract.py`, `api/surface.py`, `schemas/api-*.schema.json` | `test_api_contract.py`, `test_api_surface.py`, `test_api_dod20.py`, `test_developer_facade.py` | verified |
| FX026 | Contract 1.1.0 added read-only `history` and `posture` inspections and corrected additive-minor compatibility direction | `reference/agentmem_ref/api/surface.py`, `api/contract.py` | `reference/tests/test_api_history_posture.py` plus API contract/DoD-20 tests | verified |
| FX027 | Contract 1.2.0 added governed action authorization and execution witnessing bound to PAMA decisions, with single-consumption state surviving checkpointed restart | `reference/agentmem_ref/memory/action_authority.py`, `api/surface.py`, `core/policy.py` | `test_api_action_authority.py`, `test_action_authority.py`, `test_policy_action_execution.py` | verified |

## Reserved Feature ID

**FX025** remains reserved for Sprint 4b JS/PAMA parity. That plan was held after audit determined that porting the Python decision table without a correction discharge route would make the runtime unable to commit any correction. A reserved ID is not a verified feature and is not included in the 26-row total.

## Known Gaps Are Not Hidden Here

A verified historical row may still have a current limitation. For current work use [BACKLOG.md](BACKLOG.md), [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410), [#668](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/668), and [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636), not the closed #363/#364 or deferred #392 as if they were live blockers. Verification of a narrower feature is not closure of its broader product capability.
