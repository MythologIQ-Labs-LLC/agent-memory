# Agent Memory Feature Index

Single canonical cross-reference of every user-touchable feature in Agent Memory against documentation, source code, and test surface. Updated per the Phase 73 FEATURE_INDEX update obligation in every `/qor-implement` cycle (see `/qor-implement` Step 12.5).

**Generated**: 2026-09-01 by `qor-bootstrap`
**Sources**: declared by `/qor-plan` `Feature Inventory Touches` table per cycle.

## Coverage Summary

- Total entries: **3**
- **Verified**: 3
- **Unverified**: 0
- **N/A (operator-justified)**: 0

---

## Section: Reference Runtime and CLI

| ID | Name | Source-of-truth | Doc citation | Test path | Verification status | Surface | Notes |
|---|---|---|---|---|---|---|---|
| FX001 | Installable wheel resolves canonical schemas and exposes the `agent-memory` console command from outside the checkout | `setup.py:13-27`; `pyproject.toml` package-data; `reference/agentmem_ref/receipts.py:31-46` | `docs/CONFIGURATION.md`; `docs/plan-sprint1-install-correctness.md` | `.github/workflows/cli-doctor.yml` (job `wheel-install`) | verified | cli | Smoke exits 0 only on a schema ValueError, 1 on FileNotFoundError; local fresh-venv reproduction 2026-09-02: exit 0, 58 schemas in wheel |
| FX002 | `receipts.schema_dir()` resolves the source tree first and the packaged `_schemas/` copy second, raising with an install hint when neither exists | `reference/agentmem_ref/receipts.py:31-46` | `docs/plan-sprint1-install-correctness.md` LD1, LD2 | `reference/tests/test_receipts_schema_location.py` | verified | api | 4 tests, seams patched |
| FX003 | Cedar policy digest pin is line-ending independent | `reference/agentmem_ref/cedar_policy_comparator.py:140-142`; `.gitattributes` | `docs/plan-sprint1-install-correctness.md` LD4, LD5 | `reference/tests/test_cedar_policy_comparator.py` | verified | api | `test_policy_digest_is_eol_independent`, `test_policy_digest_is_pinned`; pin unchanged (`a369c142...`) |

---

## Gaps Surfaced

<!-- Reality without Promise / Promise without Reality entries land here. -->
