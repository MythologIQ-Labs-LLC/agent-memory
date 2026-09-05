# Agent Memory Feature Index

Single canonical cross-reference of every user-touchable feature in Agent Memory against documentation, source code, and test surface. Updated per the Phase 73 FEATURE_INDEX update obligation in every `/qor-implement` cycle (see `/qor-implement` Step 12.5).

**Generated**: 2026-09-01 by `qor-bootstrap`
**Sources**: declared by `/qor-plan` `Feature Inventory Touches` table per cycle.

## Coverage Summary

- Total entries: **5**
- **Verified**: 5
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

---

## Gaps Surfaced

<!-- Reality without Promise / Promise without Reality entries land here. -->
