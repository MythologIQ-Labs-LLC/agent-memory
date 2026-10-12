# #771 evaluator v3 adoption check: `9961067`

| | |
|---|---|
| Adopted head | `evaluation/served-memory-quality-first-no-ci` @ `9961067d020c4f1a1817f222f5a29af76884b4b2` (verified) |
| Reviewed source | `evaluation/771-lifecycle-v3-provenance-no-ci` @ `7bfcd25b85c6bc9ddaaf2ab694666406bd9143b5` |
| Verdict | **PASS. Adoption is faithful, and the evaluator's v3 provenance qualifies.** |

## Blob identity
- **Two files added:** the adoption commit (`9b7090e..9961067`) adds exactly `scripts/served_memory_v3.py` and `tests/test_served_memory_v3_provenance.py`.
- **Byte-identical to `7bfcd25`:**
  - `served_memory_v3.py` = `3b6f7cf23c5d4c49d8ef33880c03c8d92f479e97`
  - `test_served_memory_v3_provenance.py` = `b0339599383bf14935d0962822d9a5416587f3df`
- **Nothing else differs:** the only other differences from `7bfcd25` are that branch's report artifacts, which were not adopted.
- **Frozen evidence untouched:** `reference/fixtures/` and `reports/validation/771-cloud-qualification/` are unchanged since `9b7090e`. Halcyon and Cedarline evidence was not modified.

## Re-execution at `9961067` (clean tree)
| Suite | Result |
|---|---|
| top-level `tests/` | 84 run, OK, 6 expected failures (runtime-gap reproductions) |
| `test_served_memory_v3_provenance.py` | 11/11 |
| `reference/tests/test_771_served_memory_integration.py` | 8/8 |

## Independent identity representation (live run)

Halcyon v1.1 v3 (input sha256 `b46348d9…`) was run against the v7 runtime with this evaluator. The manifest (`runs/`) records each identity in its own field:

| Identity | Recorded value |
|---|---|
| Reference time | `2026-10-12T12:00:00Z` (UTC-normalized), plus the list of questions it was applied to |
| Evaluator | `9961067…`, clean |
| Runtime | `9b025f9…`, clean |
| Protected source | tree `7b87b4db…`, loaded module blob `65a39d5e…` |
| Input digest | `1a09066b…` (canonical) |
| Gold digest | `ca51c992…` (in the qualified report) |

`runtime_revision` is null. The qualified report equals the reviewed `7bfcd25` run in every key except `lane_id` and `provenance.evaluator.commit` (`9249fca` → `9961067`). So the evaluator commit is represented separately and changes nothing else.

Limitation (unchanged): identity is unkeyed. Independent replay remains the control.
