# #819 C5: stopped at its preregistered calibration gate (negative result)

**Status: not frozen as a candidate, not handed to the evaluator for qualification.**
- The implementation and every record are preserved on `claude/eager-dirac-bftkfg-819-c5`.
- The independently authored v4 cohort (`HELDOUT-V4-SEAL.md`, sha256 `fe8dc55f…`) was **not opened and not run**. It stays sealed and usable for the next candidate.
- C1–C4, A and all evaluator branches are unchanged.

## What was attempted

The hypothesis (`PREREGISTRATION-C5.md`): an opt-in semantic channel inside return selection (policy 2.4.0) recovers paraphrased and aggregate evidence that C4's lexical floor withholds, without returning unrelated facts. It works over the existing pinned local ONNX route: similarity of the query to each *admitted* fact, absolute and relative floors, a looser set channel for aggregate and plural questions, and route candidates no longer unconditional.

## Why it stopped

1. **First calibration.** On the self-authored dev set it chose τ_abs = τ_set = 0.25 and δ = 0.05. That reached dev 27/48, precision 0.715, recall 0.775, which passed the stop gate (recall ≥ 0.70 at precision ≥ 0.590).
2. **The independent review** (`review/REVIEW-C5-independent.md`; no blocking findings) showed that point was structurally unsound:
   - **F4:** a 0.25 floor sits below the route's own 0.30 discovery floor. Facts the vector route rejected became sufficient whenever the lexical route had proposed them through a shared function word, so outcomes depended on stop-word overlap.
   - **F1:** with set parameters equal to single-answer ones, the aggregate channel could never fire, so the dev gain came only from single-answer queries.
3. **Erratum 3 constraints**, recorded before recalibration: floors ≥ 0.30, and a set margin strictly wider than the single margin. Under them the best grid point is τ_abs 0.30, δ_single 0.05, τ_set 0.30, δ_set 0.10:

   | Dev, 48 queries | Strict | Precision | Recall | Mean returned |
   |---|---:|---:|---:|---:|
   | C4, semantic route off | 16 | 0.537 | 0.263 | 0.56 |
   | C4, semantic route on | 22 | 0.640 | 0.675 | 1.23 |
   | C5 constrained, route on | 27 | 0.733 | **0.675** | 1.02 |
   | C5, route off | 16 | 0.537 | 0.263 | 0.56 (lists identical to C4) |

4. **No constrained point reaches recall 0.70** (maximum 0.675). The preregistered stop condition therefore applies.

**What C5 does do:** it makes the existing semantic route *more precise* (+5 dev strict passes, precision +0.09, about 15 ms extra at p50 on a 200-fact store). It does **not** recover low-overlap evidence beyond what C4 already returns when the route is on.

## Diagnosis: where low-overlap evidence is lost

These are the residual dev failures, from captured selection inputs (`CALIBRATION.md`).

1. **Discovery reach, not selection.** Evidence worded differently from the question is often never *admitted*:
   - "Which animals live with us?" admitted none of three pet facts, and "What technologies are we using?" admitted nothing.
   - The semantic route proposes only facts above 0.30 similarity. The lexical route proposes only facts sharing a token.
   - Selection cannot return what discovery never reached, and lowering selection floors below the discovery floor is unsound (F4).
2. **Similarity is not answerability.** The bi-encoder scores topically near, non-answering facts highly, so semantic evidence cannot ground abstention:
   - weather → the flight note, 0.59;
   - cholesterol → blood pressure, 0.37.
3. **Margins anchored on the best match are manipulable (F2, recorded boundary).** Memory text stuffed toward the question can push the true answer out of a narrow single margin.
4. **Grammar limits.** The plural reading misses irregular plurals and "which of …".

This agrees with the independent evaluator's interim C4 note on #819. That note names reachability, multi-hop bridging and newer-first ordering as distinct defects, not a threshold choice.

## Recommendation: **changes required** (C5 is not qualified, and not even opt-in)

The next candidate needs its own preregistration and the still-sealed v4 cohort. It should target **governed discovery reachability**:
- align the semantic route's discovery floor with the selection floors, measured for admission volume and `ranked_prefix` effects;
- a bounded admitted-set expansion for aggregate and plural questions;
- or a calibrated hybrid sparse/dense candidate route behind governed admission.

Answerability (abstention) needs a signal other than bi-encoder similarity. Newer-first ordering of conflicting statements is a separate defect.

## Preserved

| Item | Commit |
|---|---|
| Preregistration | `3509a48a` |
| Erratum 1 | `e0e1b80c` |
| Errata 2 and 3 | `4f09f2bf` |
| Implementation | `eaed54ee` |
| Latency fix | `a7845438` |
| Constrained state and this record | this commit |

Also preserved: the dev set and harness (`dev/`, including the unconstrained second run, `calibration-run2-unconstrained.json`), the review with its probes, and the fail-first tests (`reference/tests/test_c5_low_overlap_selection.py`, 11 tests; 5 fail on C4 with the route on).
