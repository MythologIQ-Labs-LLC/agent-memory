# C6 calibration and development results

**This is in-sample development evidence only, not held-out evidence.**
- **Data:** self-authored. `dev/diag-scenarios.json` (30 queries) plus `dev/c5-dev-scenarios.json` (48 queries), 78 queries in all.
- **Same data for calibration and gate.** The constants were calibrated, and the gate measured, on this same union.
- **Not used:** no hidden cohort or benchmark gold. The sealed v4 cohort was not opened.

## Calibration (`dev/calibrate.py`, `dev/calibration.json`, `dev/calibration.log`)

- **Grid:** 176 points over K_single ∈ {1, 2, 3}, K_set ∈ {2, 3, 4, 6} with K_set ≥ K_single, margin ∈ {0.05, …, 0.20} and min_best ∈ {0.30, …, 0.45}.
- **Objective (preregistered):** maximise strict pass. Ties go to recall, then fewer extras, then the more conservative point.
- **Chosen:** `PROPOSAL_MIN_BEST = 0.40`, `PROPOSAL_MARGIN = 0.20`, `PROPOSAL_K_SINGLE = 1`, `PROPOSAL_K_SET = 3`.
- **Reference:** the harness's C4-semantic reference (no policy) matches the separate C4 runner run exactly: strict 30.

## Comparison: full facade, fresh stores, same runner file and interpreter, budget 10 (`dev/runs/`, `dev/comparison.json`)

| Configuration | Strict (of 78) | Needed-memory recall | Extra returned | No-answer queries that return something (of 14)¹ | Mean precision | Mean returned | Safety violations |
|---|---:|---:|---:|---:|---:|---:|---:|
| A `7c06468a` (semantic off) | 6 | 0.526 | 313 | 13¹ | 0.195 | 4.58 | 0 |
| C4 `bc2be631` default | 24 | 0.282 | 20 | 3 | 0.570 | 0.56 | 0 |
| C4, semantic route on | 30 | **0.628** | 49 | 7 | 0.595 | 1.30 | 0 |
| **C6, semantic route on** | **40** | 0.551 | **23** | 4 | **0.700** | 0.87 | 0 |
| C6, semantic route off | 24 | 0.282 | 20 | 3 | 0.570 | 0.56 | 0 (lists identical to C4) |

¹ Erratum, corrected at `fab09130`: the first version of this table said "(of 8)" and gave A 6. `comparison.json` has always held 13, and the union has 14 no-answer queries. No other cell changed.

**Gate (preregistered): all met.**

| Criterion | Result | Bound |
|---|---|---|
| G1: needed recall | 0.551 | ≥ 0.482 |
| G2: strict | 40 | ≥ 33 |
| G3: extra returned | 23 | ≤ 36.75 |
| G4: no-answer queries returning something | 4 | ≤ 7 |
| G5: safety violations | 0 | 0 |
| G6: C6 off equals C4 | identical on all 78 | identical |
| G7: recall p50 on a 200-memory store, two runs | C6 69.4 / 68.9 ms against C4 with the semantic route 69.9 / 66.3 ms | ≤ C4 + 10 ms |

**Paired strict pass (exact McNemar):**

| Comparison | Improved / regressed | p | Regressions |
|---|---|---:|---|
| C6 vs A | +35 / −1 | < 0.001 | — |
| C6 vs C4 default | +18 / −2 | 0.0004 | c5-dev:tr-2, diag:pets-5 |
| C6 vs C4 with the semantic route | +14 / −4 | 0.031 | c5-dev:co-1, c5-dev:tr-2, c5-dev:wk-2, diag:work-4 |

**Strict by kind (diagnosis set):**

| Kind | n | C4 | C4 + sem | C6 |
|---|---:|---:|---:|---:|
| paraphrase | 13 | 1 | 4 | 5 |
| aggregate | 5 | 0 | 0 | 1 |
| distractor | 2 | 1 | 0 | 2 |
| abstention | 3 | 2 | 0 | 1 |
| governance | 5 | 3 | 3 | 4 |

## Trade-offs, stated plainly

- **Recall is lower than C4 with the semantic route on** (0.551 against 0.628). K_single = 1 and the min_best guard give up some reach for precision: extras 23 against 49, precision 0.70 against 0.60.
- **Against C4 default the gain is large:** recall +0.27 and strict +16.
- **Aggregate questions are still weak:** 1 of 5 diagnosis aggregates pass. Members far from the question in embedding space stay out of reach.
- **Abstention is worse than C4 default** (4 no-answer queries return something, against C4's 3) but better than C4 with the semantic route (7).
- **Every number here is in-sample.** Independent qualification on unseen data is required before any claim.

## Errata (recorded after review, before freeze)

- **No-answer column.** The denominator is 14, not 8, and A's value is 13, not 6 (see the table footnote). The gate (G4) used `comparison.json`, which was always correct.
- **Grid size.** The preregistration said 192 points. `calibrate.py` ran 176, skipping the 16 combinations with K_set < K_single. This was not stated in advance. The skipped points were never evaluated. Each would give plural questions fewer proposals than single-answer ones, which contradicts the policy's definition.
- **G4 is a weak bound.** C4 with the semantic route answers 7 of 14 no-answer queries. Against C4 default, C6 is worse on this measure (4 against 3).
- **Failed preregistered expectation.** The preregistration expected that "against C4 with the semantic route on, recall stays the same or rises". It fell, from 0.628 to 0.551. This is a failed prediction, not just a trade-off.

## Review outcome and fixes (`review/REVIEW-C6.md`, `review/DISPOSITION.md`)

**The independent adversarial review of `80c797d0` found one blocking defect.** In explicit historical and as-of recall, a memory that historical admission refuses could take the single slot. The fix is in `fab09130`: the bounded pool is filtered with the mode-aware admission refusal, and the policy applies only under relevance-sufficient selection, so `ranked_prefix` is C4's route again.

**The policy constants are unchanged.**

**Re-measured at `fab09130`:**
- **C6 runs** (route on and off, both sets): returned lists are identical to the earlier runs on all 78 queries, so `comparison.json`, the gate and the paired tests are unchanged.
- **G7 latency** (`review/after-fixes/c6-latency-fab09130.txt`, 200-memory store, two runs): C6 62.3 / 66.4 ms p50, against C4 with the semantic route 69.3 / 68.1 ms.

### What C6 is, restated after review

The reviewer split each strict win into two cases: the win reached a needed memory, or the win only stopped returning extras.

| Data | Needed memories C6 reaches that C4+sem does not | Needed memories C4+sem reaches that C6 does not | Strict wins over C4+sem | Wins with identical needed coverage |
|---|---:|---:|---:|---:|
| Development union (in-sample) | 2 | 8 | 14 | 13 |
| Reviewer's set (55 queries, unseen) | 0 | 9 | 11 | 11 |

**C6 is therefore not a discovery gain over C4 with the semantic route on.** It is a bounding control on that route.
- **Against C4 with the route on:** C6 trades recall for precision. On the reviewer's set recall falls from 0.655 to 0.500, extras fall from 120 to 61, and strict rises from 6 to 16.
- **Against C4 default (route off):** C6 adds reach through the existing route. On the reviewer's set recall rises from 0.276 to 0.500, strict from 11 to 16, and extras from 53 to 61.
- **Where the route stands now:** on unseen data, turning the route on under C4 lowered strict from 11 to 6. With C6 it raises strict from 11 to 16.

**Known limits** (review findings 2, 5, 6 and 9). None was changed after seeing results:
- **Slot capture by question-shaped memory text.** On the reviewer's stuffing store C6 returns 0 of 6 needed memories, the same as C4 default; C4 with the route returns 3 of 6.
- **The plural reading misses common list questions.**
- **Answers at 0.32–0.40 are not proposed.**
- **A query-time provider failure is not degraded in `auto` mode.** This was already true before C6.
