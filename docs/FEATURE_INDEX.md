# Agent Memory Feature Index

Single canonical cross-reference of every user-touchable feature in Agent Memory against documentation, source code, and test surface. Updated per the Phase 73 FEATURE_INDEX update obligation in every `/qor-implement` cycle (see `/qor-implement` Step 12.5).

**Generated**: 2026-09-01 by `qor-bootstrap`
**Sources**: declared by `/qor-plan` `Feature Inventory Touches` table per cycle.

## Coverage Summary

- Total entries: **10**
- **Verified**: 10
- **Unverified**: 0
- **N/A (operator-justified)**: 0

---

## Section: Reference Runtime and CLI

| ID | Name | Source-of-truth | Doc citation | Test path | Verification status | Surface | Notes |
|---|---|---|---|---|---|---|---|
| FX001 | Installable wheel resolves canonical schemas and exposes the `agent-memory` console command from outside the checkout | `setup.py:13-27`; `pyproject.toml` package-data; `reference/agentmem_ref/receipts.py:31-46` | `docs/CONFIGURATION.md`; `docs/plan-sprint1-install-correctness.md` | `.github/workflows/cli-doctor.yml` (job `wheel-install`) | verified | cli | Smoke exits 0 only on a schema ValueError, 1 on FileNotFoundError; local fresh-venv reproduction 2026-09-02: exit 0, 58 schemas in wheel |
| FX002 | `receipts.schema_dir()` resolves the source tree first and the packaged `_schemas/` copy second, raising with an install hint when neither exists | `reference/agentmem_ref/receipts.py:31-46` | `docs/plan-sprint1-install-correctness.md` LD1, LD2 | `reference/tests/test_receipts_schema_location.py` | verified | api | 4 tests, seams patched |
| FX003 | Cedar policy digest pin is line-ending independent | `reference/agentmem_ref/cedar_policy_comparator.py:140-142`; `.gitattributes` | `docs/plan-sprint1-install-correctness.md` LD4, LD5 | `reference/tests/test_cedar_policy_comparator.py` | verified | api | `test_policy_digest_is_eol_independent`, `test_policy_digest_is_pinned`; pin unchanged (`a369c142...`) |
| FX004 | Two adapters sharing one substrate mint disjoint identifiers across facts, receipts, and events | `reference/agentmem_ref/substrate.py` (`next_id`, `write_fact` guard); `reference/agentmem_ref/adapter.py` (counter binding); `reference/agentmem_ref/restart_runtime.py` (LD6) | `docs/plan-sprint2a-identity-and-decision-table.md` LD1, LD2, LD6; `docs/15-memory-threat-model.md` | `reference/tests/test_substrate_identity.py`; `reference/tests/test_substrate_identity_restart.py` | verified | api | GAP-SEC-08. 12 tests. Single-adapter sequence pinned bit-identical (`ref-0001`-`ref-0007`) |
| FX005 | PAMA base decision table resolves every documented operation/risk cell as `docs/33` specifies | `reference/agentmem_ref/policy.py:53-107` | `docs/33-pama-decision-table.md` | `reference/tests/test_decision_table_doctrine.py` | verified | api | GAP-ARCH-09. 52 cells asserted; closes `score_adjustment/critical` (was require_review, doctrine `block`) and `link_deletion/critical` (was require_review, doctrine `require_external_verification`) |
| FX006 | Recall refuses candidates with no scope metadata as `unknown_scope`, matching the JS runtime | `reference/agentmem_ref/adapter.py` `_admission_refusal` | `docs/34-adapter-contracts.md`:139; `docs/plan-sprint2b-recall-authority-record.md` LD1 | `reference/tests/test_recall_unknown_scope.py` | verified | api | GAP-ARCH-18. Closes a Python/JS divergence; parity source `integrations/agent-memory-runtime/src/index.mjs:114`. Refusal ordering asserted so the blast-radius shield is pinned |
| FX007 | Every governed recall emits an audit event and a schema-valid per-candidate admission decision | `reference/agentmem_ref/adapter.py` `governed_recall`, `_recall_decision`, `_recall_event` | `docs/34-adapter-contracts.md`:136; `docs/plan-sprint2b-recall-authority-record.md` LD3, LD4, LD6 | `reference/tests/test_recall_authority_record.py` | verified | api | GAP-SEC-02 record leg only -- gap remains OPEN. `signal_type: recall_admission`; `policy.status` pinned `unavailable`, never `evaluated` |
| FX008 | Governed deletion enforces existence, tenant ownership, target binding, and staleness | `reference/agentmem_ref/adapter.py` `_delete_refusal`, `governed_delete`; `restart_runtime.py` `fact_memory` | `docs/plan-sprint2c-deletion-authority.md` LD1-LD5 | `reference/tests/test_deletion_authority.py` | verified | api | GAP-SEC-03. 11 tests. Closes a cross-tenant physical delete and a falsified tombstone; guard ordering and restart survival asserted |
| FX009 | Review discharge derives self-approval from identity and records what the discharge rested on | `reference/agentmem_ref/policy.py` `_apply_modifiers`, `evaluate_with_base_outcome`; `Decision.review_discharge` | `docs/plan-sprint2d-derived-authority.md` LD1-LD4 | `reference/tests/test_derived_authority.py` | verified | api | GAP-ARCH-04 self-approval leg only -- gap remains OPEN. Generalizes `decision_overwrite.py:171` and `enforcement_evidence.py:61-80`. Reaches `crossing.py` via `policy.evaluate` |
| FX010 | Reusable grant evaluation verifies against an independently-held ratification record | `reference/agentmem_ref/reusable_grants.py` `RatificationRegistry`, `grant_body_digest`, `evaluate_reusable_grant` | `docs/plan-sprint2e-ratification-anchor.md` LD1-LD5 | `reference/tests/test_ratification_anchor.py` | verified | api | GAP-SEC-04 grant path. Implements the operator's option-C decision; option D retained as a labelled profile. Defeats the recompute attack that beat a digest-only fix. No schema modified |

---

## Gaps Surfaced

<!-- Reality without Promise / Promise without Reality entries land here. -->
