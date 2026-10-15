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

| Configuration | Strict (of 78) | Needed-memory recall | Extra returned | No-answer queries that return something (of 8) | Mean precision | Mean returned | Safety violations |
|---|---:|---:|---:|---:|---:|---:|---:|
| A `7c06468a` (semantic off) | 6 | 0.526 | 313 | 6 | 0.195 | 4.58 | 0 |
| C4 `bc2be631` default | 24 | 0.282 | 20 | 3 | 0.570 | 0.56 | 0 |
| C4, semantic route on | 30 | **0.628** | 49 | 7 | 0.595 | 1.30 | 0 |
| **C6, semantic route on** | **40** | 0.551 | **23** | 4 | **0.700** | 0.87 | 0 |
| C6, semantic route off | 24 | 0.282 | 20 | 3 | 0.570 | 0.56 | 0 (lists identical to C4) |

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
