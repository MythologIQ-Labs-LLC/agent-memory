# #774 strict caller-targeted predecessor contract: implementation and blind evaluation

| | |
|---|---|
| Contract | `evaluation/774-strict-predecessor-target-contract-no-ci` @ `f2d451dd4a0484307cbfc5d98b8e28f7766325eb` (verified; base #774 `a6745a9`) |
| Implementation | `implementation/774-strict-predecessor-target-no-ci`: independent tests `fd41b2e` (fail) → **`4088823`** (`runtime_composition.py` `5acaf31b…`, `adapter.py` `2e50d85c…`) |
| Blind evidence | theatre corpus (author 1, frozen `af09d61`; gold v1.1 `e560be6`) plus independent **successor annotations** (author 2) and a new **vineyard** corpus (author 2, frozen `45b6d14`; gold v1.1 `6dd042d`). Both authors are separate agent instances with no repository access, not humans. |
| Harness | `measure_strict.py`, evaluator `9961067` v3, same caller intents for every runtime (`results-strict.json`) |
| Verdict | **Strict contract: PASS on the blind evidence, CHANGES REQUIRED before promotion** (successor declaration; no #776 combination yet). **Automatic routing: not promoted.** |

## Contract tests at `f2d451d`
- 2 of 4 fail as intended: implicit anchoring on the current head, and lexical-cue promotion.
- The explicit older-successor and current-successor tests pass (`logs/contract_tests_at_f2d451d.log`).

## The strict contract (selection policy 0.2.0, routing policy 0.3.0)
- **When a predecessor is asserted:** only for a successor the **caller identifies**. That is either `successor_ref` (an authorized, visible fact; unknown, hidden, deleted and corrected-as-false refs raise the identical `ValueError`), or `AsOfTarget(memory_ref, instant)`, which resolves the version of that named memory in effect at the instant under canonical admission.
- **Unresolved targets:** with no resolvable target the result is `target_resolution: "unresolved"`. No predecessor is asserted and historical ranking is unchanged. **This never states that no predecessor existed.** `"resolved"` with no predecessor means the identified successor has no governed state-change predecessor.
- **No inference:** implicit anchoring (current head or top-ranked lineage) is removed. Lexical cues (`predecessor_routing`) still classify, but **never promote**. `routed_historical_context` routes only a caller-historical question whose declared target resolves.
- **Explicit current successor preserved:** the original "latest predecessor" tests are kept by declaring the current successor explicitly. They were migrated, not deleted.
- **Tests:** 38/38 #774 tests pass, plus the 1 pre-existing expected failure: the 4 contract tests, 11 independent strict tests (as-of resolution, before-existence, unknown/other-project/deleted targets indistinguishable, conflicting or malformed targets, error-corrected successor, duplicate text across memories, out-of-budget promotion, routing only with a resolved target) and the migrated originals.
- **Full suite:** 2748 run, 5 failures = 4 freeze guards plus the pre-existing durability failure.

## Blind results (P0 · answer@1 · all-critical)
| Corpus | v7 composed | legacy #774 declared (implicit) | **strict, annotated target** | strict, no target |
|---|---|---|---|---|
| Theatre (24 q, 13 predecessor) | 1 · 9/21 · 11/21 | 0 · 13/21 · 15/21 | **0 · 16/21 · 17/21** | 0 · 9/21 · 11/21 |
| Vineyard (25 q, 16 predecessor, 5 older-version) | 1 · 9/20 · 13/20 | 0 · 14/20 · 16/20 | **0 · 18/20 · 19/20** | 0 · 9/20 · 13/20 |

**Per question:**
- **No rank-1 or critical-coverage loss** versus v7 or legacy in any question.
- **Q19 is fixed**: the predecessor of the older £28 version is `tp-24`. Older-version questions now succeed: theatre Q14 and Q18; vineyard Q05, Q06, Q07 and Q10.
- **Wrong-subject anchors are gone.** Theatre Q15/Q16/Q17 and vineyard Q12–Q16 (deleted, other project or tenant, never changed) are `unresolved` and served unchanged.
- **Untargeted strict calls equal v7** except where v7 served deleted content (theatre Q15 `fee-900`, vineyard Q12 `cf-600`). The selector withholds versions of deleted memories; plain recall on this branch does not, because that is #776.

## Caveats
- The gains assume the caller can identify the successor. Here an independent annotator supplied it from the stored texts, which upper-bounds a real caller. Resolving a successor from natural language is a separate capability, and must be qualified separately before any automatic use.
- **Fixture corrections, both made before results:** theatre Q17 (no-safe-answer grade) and vineyard Q09 (error-corrected value graded 2 → 1, rule R-A1). Originals are kept.
- **Not combined** with #776 or #773. The #774 × #776 fact-level lineage design (`validation/774-776-integration-contract-review`) still applies, and this branch keeps #774's memory-level deletion checks.
