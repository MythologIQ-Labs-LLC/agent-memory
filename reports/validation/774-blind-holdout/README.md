# #774 blind holdout: theatre production company (independent author)

| | |
|---|---|
| Author | A separate agent instance given only the v3 corpus format. It was barred from reading the repository, runtime, routing rule, existing corpora and reports, and it states it read none (`holdout/brief.md`). **It is an independent model instance, not a human.** |
| Frozen | `af09d61` (files and sha256 as delivered), **before any execution** |
| Fixture correction | `e560be6`, before any result: no-safe-answer Q17 graded an eligible item 2, which the scorer forbids, so it was regraded 1 (`holdout/FIXTURE-CORRECTION.md`; original kept). Runs use `gold-v1.1.json`. |
| Size | 18 memories, 38 events, 24 questions. 13 are annotated as immediate-predecessor questions, 3 of them about an *older* version and 3 with no safe answer. |
| Harness | `measure_blind.py`, evaluator `9961067` v3, instant `2026-10-12T12:00:00Z` (`results-blind.json`) |

## Results (P0 prohibited/stale · answer@1 · all-critical)
| Runtime / mode | P0 | answer@1 | all-critical |
|---|---|---|---|
| v7 composed | **1**/0 (Q15 serves deleted `fee-900`) | 9/21 | 11/21 |
| #774 `ce1fdfc` declared | 0/0 | 13/21 | 15/21 |
| #774 head `a6745a9` declared | 0/0 | **13/21** | **15/21** |
| #774 head auto (routing 0.2.0) | 0/0 | 10/21 | 13/21 |
| #774 head over-routed (sensitivity) | 0/0 | 10/21 | 15/21 |
| design prototype `b367b76` declared / auto | 0/0 | 13/21 / 10/21 (identical lists to `a6745a9`) | 15/21 / 13/21 |

## Per-question findings
- **Gains confirmed blind (declared):**
  - Q01, Q02, Q04, Q20 and Q22 (latest-change predecessors) reach rank 1.
  - No question loses critical coverage versus v7 in any mode.
- **Incorrect predecessor selection: Q19**, "What did adult tickets cost before the price went up to 28 pounds?"
  - Asks about the predecessor of an *older* version. The answer is `tp-24`.
  - The selector answers relative to the current value and promotes `tp-28`, **losing rank 1 that v7 had**. This happens in declared *and* automatic modes.
  - Q14 and Q18 are the same class: wrong predecessor, but v7 also missed rank 1. This is the B12 limitation, now shown blind to cost answer@1.
- **Wrong-subject anchors** (nothing prohibited served):
  - Q15, about the deleted fee, promotes `bo-11am` (box-office hours).
  - Q16, about the other-project rehearsal, promotes `rr-sail-loft`.
- **Automatic routing:** it misses Q02, Q04 and Q20 (no cue) and routes Q15–Q19. Gains: answer@1 9 → 10 versus declared 13.

## Decision
- **Automatic routing: NOT PROMOTED.**
  - It causes incorrect predecessor selection (Q19, rank-1 loss versus v7).
  - It recovers only 1 of the 4 answer@1 gains that declared routing achieves.
- **Declared selector:** its blind gains are real (+4 answer@1, +4 all-critical), but it must not select relative to the current value when the question names an older version.
  - Require a declared `successor_ref` or as-of instant for older-version questions; otherwise return no predecessor.
  - Then re-measure on a fresh blind set.
- #775 subject identity stays separate. It is not used here.
