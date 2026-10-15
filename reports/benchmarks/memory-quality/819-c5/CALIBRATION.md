# C5 calibration on the self-authored development set

**Not evidence.** The development set was written by the implementation agent for calibration (`dev/build_dev_set.py`, 8 scenarios, 48 queries). It was committed with the preregistration, before any C5 runtime change. No LongMemEval, AMB or sealed-cohort label was used.

## Procedure

`dev/calibrate.py` runs each dev scenario once through the public facade with the semantic route set to `required`, using the pinned MiniLM model in its local directory. It captures every recall's selection inputs at the facade's call into `select_relevance_sufficient`, then replays only the selection stage at each grid point.

- **Grid:** τ ∈ {0.20, 0.25, …, 0.50}, δ ∈ {0.05, 0.10, …, 0.30}, with τ_set ≤ τ_abs. That gives 1,008 points.
- **Objective:** maximise dev strict pass.
- **Constraint:** dev precision ≥ C4-semantic-on dev precision − 0.05 = 0.5897.
- **Tie-break (erratum 2):** higher recall, then higher precision, then higher floors and smaller margins.

**Replay check.** The C4-equivalent replay reproduces the separate runner result for C4 with the semantic route on exactly: 22/48, precision 0.6397, recall 0.675.

## Result

| Configuration (dev, 48 queries) | Strict | Precision | Recall | Mean returned |
|---|---:|---:|---:|---:|
| C4, semantic route off | 16 | 0.537 | 0.263 | 0.56 |
| C4, semantic route on (vector neighbours unconditional) | 22 | 0.640 | 0.675 | 1.23 |
| **C5, semantic route on, chosen point** | **27** | **0.715** | **0.775** | 1.21 |
| C5, semantic route off | 16 | 0.537 | 0.263 | 0.56 (lists identical to C4's) |

**Chosen point:** `SEMANTIC_ABSOLUTE_FLOOR = 0.25`, `SEMANTIC_SINGLE_MARGIN = 0.05`, `SEMANTIC_SET_FLOOR = 0.25`, `SEMANTIC_SET_MARGIN = 0.05`.
- Twenty grid points reach 27 passes.
- The set parameters change little on this dev set: δ_set from 0.05 to 0.10 is identical, and 0.15 and above lowers precision to 0.70.
- The full grid is in `dev/calibration.json`.

**Stop condition (preregistered):** dev recall ≥ 0.70 at precision ≥ 0.5897. **Met** (0.775 at 0.715), so implementation continued.

**Erratum 2 (tie-break).** The first calibration run broke ties conservatively first (higher floors). It chose a 27-pass point with recall 0.575, although 27-pass points with recall 0.775 existed. Recall of low-overlap evidence is the hypothesis' target, so ties now go to recall first. Both runs used only the dev set.

## What the remaining dev failures show (21 of 48)

These are diagnosed from the captured inputs. They are expected to recur on unseen data, and they were preregistered as boundaries.

1. **Discovery reach.**
   - "Which animals live with us?" admitted none of the three pet facts, and "What technologies are we using?" admitted nothing.
   - The semantic route proposes candidates only above 0.30 similarity, so these never reach selection.
   - C5 changes selection, not discovery. Lowering the route's discovery floor would change what is admitted, and `ranked_prefix` with the semantic route on, so it is left to a separate, measured change.
2. **Similarity is not answerability.** A bi-encoder scores a topically near but non-answering fact highly:
   - "weather forecast for Osaka?" → the flight note 0.59;
   - "company picnic?" → standup 0.38 and offsite 0.34;
   - "cholesterol?" → blood pressure 0.37.

   With a 0.25 absolute floor, such abstention queries return the nearest fact. That costs abstention strict passes. Any higher floor gives up more paraphrase recall than it saves.
3. **Close calls inside the margin.** "Who is my boss?" → manager 0.31 and employer 0.30, so both are returned.
4. **Aggregate members below the set floor.** Medications 0.45 and 0.16: the second member is out of reach.


## Recalibration under erratum 3 (after the independent review)

**Grid:** τ ∈ {0.30, …, 0.50} (no floor below the route's 0.30 discovery floor), τ_set ≤ τ_abs, δ_set ≥ δ_single + 0.05. That gives 225 points.

**Chosen:** τ_abs 0.30, δ_single 0.05, τ_set 0.30, δ_set 0.10. Dev 27/48, precision 0.733, recall 0.675, mean returned 1.02.

**Stop condition:** recall ≥ 0.70 is **not met** by any constrained point (maximum 0.675), so C5 stops ().

**Run files:**
- : the constrained grid.
- : the second unconstrained run.
- The first run's choice is stated in erratum 2.
