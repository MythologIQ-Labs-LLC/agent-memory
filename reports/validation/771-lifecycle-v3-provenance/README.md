# #771 Evaluator: adoption confirmation and R-A2/R-A3 (lifecycle v3)

| | |
|---|---|
| Adopted evaluator | `evaluation/served-memory-quality-first-no-ci` @ `9b7090e8f7fc094c161baa9ba04e77afcc0b584b` (verified) |
| This branch | `evaluation/771-lifecycle-v3-provenance-no-ci` (evaluation-only, from `9b7090e`) |
| **Adoption verdict** | **PASS.** The adopted scripts and tests are byte-identical to the reviewed validation branch, including R-A1 and the seeded properties. Re-executed on the new SHA. |
| **R-A2/R-A3 verdict** | **Implemented here; needs adoption.** Evaluator qualification overall: **PASS once adopted.** |

## Phase 1: re-execution at `9b7090e` (not assumed)

- **Top-level suites:** 55 OK plus 6 expected failures (the runtime-gap reproductions). That includes all **11 provenance** tests, all **6 seeded properties** (300 trials each) and **R-A1**.
- **Integration:** `test_771_served_memory_integration.py` passes 8/8.
- Logs are in `logs/P1_771_*.log`.

## R-A2: declared evaluation instant

**New schema `served-memory-lifecycle-v3`:** v2 plus a **required** `reference_time`.
- **Strict format:** full ISO-8601 with `Z` or `±HH:MM`.
- **Rejected:** naive times, `-00:00` (the RFC 3339 "unknown offset"), lowercase `z`, a missing seconds field, date-only values, impossible dates, `+24:00`, and more than 6 fractional digits.
- **Normalized:** the instant is normalized to UTC in the run manifest.

**v2 is never reinterpreted:**
- A v2 document carrying `reference_time` is still rejected by v2 validation.
- `derive_v3` writes a **new** document.
- v2 digests are unchanged.

**Derived copies:**
- Halcyon v1.1 and Cedarline v1.1 v3 copies at `2026-10-12T12:00:00Z` are in `holdouts/`.
- `DERIVATION.json` pins each source commit, path and sha256: `d41ae86d…` and `eee23441…`, identical to the frozen originals.
- The original evidence is untouched.

**Temporal gold check:** the qualifier now refuses gold that leaves a fact outside its declared window at the reference instant eligible for a current-intent question.

## R-A3: separated provenance (`served-memory-run-v2` manifests)

The manifest records each identity separately; there is no `runtime_revision` field:

| Recorded field | Meaning |
|---|---|
| `provenance.evaluator.{commit, clean}` | the checkout whose scripts ran |
| `provenance.runtime.{commit, clean}` | the checkout whose runtime executed |
| `provenance.runtime.protected_tree` | git tree of `reference/agentmem_ref` at that commit (protected source identity) |
| `provenance.runtime.loaded_module` / `loaded_module_blob` | the `runtime_composition.py` actually imported |
| `input_sha256`, `reference_time`, `reference_time_utc`, `reference_time_applied_to` | execution inputs |

**Runner safeguards:**
- It imports the runtime from `--runtime-root` *before* any evaluator module and refuses if another copy was loaded.
- It refuses a dirty runtime protected tree.
- It also refuses a loaded module whose blob differs from the committed source.

**`qualify_v3` checks:**
- It checks label integrity first, then re-derives tree and blob from `runtime.commit` in a given repository.
- It refuses substitution, unknown commits, unclean checkouts, short hashes, non-canonical module paths, and extra or legacy identity fields.
- Reports carry `gold_sha256` and the provenance block, with `runtime_revision = null`.

**Adversarial tests** (`tests/test_served_memory_v3_provenance.py`, 11 tests) use **real** git objects:
- the evaluator commit recorded in place of the v7 runtime;
- tree and blob substitution from `6e00f42`;
- unknown, unclean or malformed identities;
- equivalent-offset instants with different declarations;
- forged normalized instants;
- ambiguous timestamps.

All 11 pass on a clean tree (`logs/P2_v3_tests_clean_tree.log`).

**Demonstration** (`runs/`): Halcyon and Cedarline v3 were executed against the v7 parent (`9b025f9`, tree `7b87b4db…`, blob `65a39d5e…`) and the #773 head (`6e00f42`, tree `b59b1640…`, blob `86b3bc29…`). Each manifest records evaluator `9249fca` separately. Quality equals the earlier composed-with-instant results: P0 0/0; Halcyon 13/21 answer@1 and 19/21 all-critical; Cedarline 14/20 and 14/20.

**Remaining limitation:** identity is unkeyed. A malicious author can fabricate a consistent manifest for a commit that genuinely has those objects. Independent replay remains the control.
