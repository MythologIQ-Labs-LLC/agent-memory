# #819 C3 freeze: candidate `6a2255c0`

| Item | Value |
|---|---|
| **C3 runtime candidate (frozen)** | `6a2255c0f46daa1d546758daa93f4402fed14108`, branch `claude/eager-dirac-bftkfg-819-evidence-sets` |
| Previous candidate (kept immutable) | C2 `eaf60e4dd001c02ce00bb36f15f800996bf77da3`, evidence head `3179ffa5` (branch `claude/eager-dirac-bftkfg-819`, untouched) |
| Baseline A | `1df28f84` (runtime identical to `main` `38f6a7d`, per the independent evaluator) |
| Selection policy | `relevance-sufficient-return-selection` `2.2.0`, normalization `1.1.0`, interpreter `1.0.0` |
| Contract | Candidate `1.9.0`, unchanged since C1. **Not advanced, no Runtime Baseline successor declared, unaccepted.** |
| Configuration | Default facade. Semantic route off, recall control off, no paid inference, no extractor |
| Status | Local evaluation only, 0 hosted CI, no PR. The leaderboard and the public feed are untouched |

## Problem addressed

C2 made return selection precise but lost corroborating evidence (LongMemEval-S session
recall_all@5 0.823 → 0.747). Every fact faced one floor relative to the best match, frame words
("how *many*", "*total*", "*months*") counted as topic, and exact-token matching missed inflections
and typos. C2 also returned a changed state without the later state that changes it.

## What changed (each slice has a verification record)

1. **Evidence sets** (`SLICE-1-evidence-sets.md`):
   - deterministic query interpretation separating topic from frame;
   - the information requirement (single, aggregate or relational) and entity mentions;
   - a set floor for multi-evidence questions;
   - the fact most about each named entity;
   - abstention when the topic matches nothing.
2. **Word forms and typos** (`SLICE-2-lexical-robustness.md`):
   - Porter step-1 inflectional normal forms;
   - one-edit typo tolerance, only for short queries whose topic matched nothing;
   - discovery expansion from the vocabulary of admissible facts only;
   - ranking consistency anchored on primary evidence.
3. **Lifecycle closure** (`SLICE-3-lifecycle-closure.md`): a returned state brings the admitted
   later state that a guarded, **typed** write-time relation links to it.
4. **Review repairs** (`REVIEW-C3-adversarial.md`): two blocking and five should-fix findings
   repaired and pinned by tests (details below).
5. **Rejected:** entity bridging for multi-hop (`SLICE-4-entity-bridging-REJECTED.md`). Blind
   evidence did not support it, so it is kept only as a patch.

## Tests

| File | Tests |
|---|---:|
| `test_evidence_set_selection.py` | 14 |
| `test_lexical_normalization.py` | 12 |
| `test_lifecycle_closure.py` | 12 |
| `test_c3_review_regressions.py` (7 fail on the pre-review head) | 10 |

Each file includes adversarial cases: keyword stuffing, frame-only matches, forgotten,
superseded, other-scope and disputed text, self-claim laundering, crafted "supersedes" text and
quadratic inputs.

**Full suite at `6a2255c0`:** 2633 tests, 36 skipped, 1 failure. The failure is
`test_evaluation_only_change_keeps_runtime_baseline_equivalence`, the repository's Runtime
Baseline guard, which fails for any runtime change until a successor is declared (see
qualification requirements).

## Results

### Independently authored held-out v2

The cohort was sealed before C3's first slice (sha256 `31ae2f22…`, 44 scenarios, 194 queries,
written by a separate agent). It was opened only after the freeze; one run per system.

| | A | C2 | **C3** |
|---|---:|---:|---:|
| Strict pass | 49 | **99** | 94 |
| Mean precision | 0.468 | **0.752** | 0.728 |
| Mean recall | **0.874** | 0.690 | 0.780 |
| Safety violations (superseded / forgotten / other scope returned) | 0 | 0 | 0 |
| Recall latency p50 / p95 (ms) | 31.5 / 49.3 | 32.9 / 47.0 | 31.0 / 49.4 |

- **Paired:** C3 vs A +53/−8 (p < 0.001); C3 vs C2 +14/−19 (p = 0.49, no significant difference).
- **By category** (C2 → C3 strict):

  | Change | Categories |
  |---|---|
  | Improved | scope-boundary 14 → 16, entity-ambiguity 10 → 11, evolving-preference 7 → 9, forgetting 8 → 9, low-overlap 1 → 3 |
  | Equal | historical-vs-current 7, imperfect-query 10 |
  | Worse | **correction 10 → 3**, abstention 15 → 12, distractor-heavy 10 → 8, multi-evidence 7 → 6 |

- **Why C3 loses strict cases to C2.** 16 of its 19 losses return every required fact plus an
  extra. The extras come from:
  - entity coverage adding "the fact most about" a kinship-name entity ("Mom") that a selected
    fact already covers, 13 times;
  - ranking consistency, 18 times against C2's 8.

  In correction scenarios, recall is equal (0.96) and precision falls (0.78 → 0.59).

### LongMemEval-S 500, native runner (`reference/run_longmemeval.py`), frozen input `d6f21ea9…`, budget 50

Session plane (419 scored):

| | A | C2 | **C3** | C3 `ranked_prefix` |
|---|---:|---:|---:|---:|
| recall_any@1 | 0.809 | 0.814 | **0.831** | 0.809 |
| recall_all@5 | 0.823 | 0.747 | **0.862** | 0.823 |
| recall_all@10 | 0.893 | 0.754 | **0.905** | 0.893 |
| recall_all@50 | **1.000** | 0.757 | 0.916 | 1.000 |
| Mean items returned | 45.1 | 3.0 | 4.7 | 45.1 |

- **Paired session plane:**
  - C3 vs A: all@5 +23/−7 (p = 0.005); all@10 +16/−11 (p = 0.44).
  - C3 vs C2: all@5 +50/−2; all@10 +65/−2.
- **By type, all@10, A → C3:** multi-session 0.827 → 0.865, temporal 0.895 → 0.910,
  knowledge-update 0.987 → 0.974, single-session-user 1.000 → 0.986.
- **`ranked_prefix` reproduces A exactly:** 0 of 500 lists differ.
- **Recall@50 is below A by construction.** C3 returns about 5 items, A about 45.

| Turn plane | A | C2 (independent evaluator) | **C3** | C3 `ranked_prefix` |
|---|---:|---:|---:|---:|
| recall_any@1 | 0.573 | — | **0.587** | 0.573 |
| recall_all@5 | 0.601 | — | **0.628** | 0.601 |
| recall_all@10 | 0.723 | 0.632 | **0.764** | 0.723 |
| recall_all@50 | **0.859** | 0.654 | 0.847 | 0.859 |
| Mean items returned | 50.0 | — | 12.3 | 50.0 |

- **Paired turn plane:**
  - C3 vs A: all@10 +24/−7 (p = 0.003); all@50 +16/−22 (p = 0.42).
  - C3 vs C2: all@10 +59/−4.
- **`ranked_prefix` reproduces A exactly** (0 of 500 lists differ).
- Reports and summaries: `longmemeval/`.

### AMB PrecisionMemBench, 77 cases (native scorer, AMB `03c1d0f`)

| | A | C2 | **C3** |
|---|---:|---:|---:|
| Strict | 15 | **39** | 38 |
| Precision | 0.18 | **0.541** | 0.522 |
| Recall | **0.954** | 0.878 | 0.942 |

C3 vs C2: 3 fixed, 4 broken, p = 1.0. The four broken cases are threshold effects of inflection
matching.

### Other evidence

| Cohort | A | C2 | C3 |
|---|---|---|---|
| Blind multi-hop cohort (`blind-multihop/`, sealed `6acef4bf…`; seen once during slice 4, so not clean holdout evidence for `6a2255c0`) | 2/32 | **15/32** | 12/32 |
| Typed-lifecycle fixture (engineer-authored), typed changes | 6/8 | 1/8 | **6/8** |
| Typed-lifecycle fixture, untyped controls | **3/3** | 0/3 | 0/3 |

In the blind cohort, multi-hop is 0 to 1 of 12 for every system.

## Qualitative examples

| Query | Before (C2) | After (C3) |
|---|---|---|
| "How many charity events did I take part in in total?" | The strongest charity fact only | All three charity facts (set evidence); "I had *many* meetings" withheld (frame word) |
| "How many weddings have I attended this year?" | Nothing in the store says "weddings" | Facts that say "wedding" (normal forms) |
| "typsecript compilation config" | Nothing | The TypeScript fact (one-edit correction, short query, topic unmatched) |
| "Who is my manager?" | "My manager is Priya." alone | Plus "Priya left; my team now reports to Daniel." (typed change; lifecycle closure) |
| "How should React error handling work with MongoDB?" | One fact | The fact most about each named entity |
| "what is a good way to grade an old penny without sending it away?" in a store with "Monthly spending on groceries" | — | Abstains; "sending" is not "corrected" to "spending" |

## Multi-evidence completeness and precision

- **Completeness.**
  - LongMemEval multi-session all@10: C2 0.595 → C3 0.865 (A 0.827).
  - Held-out recall: 0.690 → 0.780.
  - The remaining multi-evidence losses are mostly zero-overlap evidence (no shared topical term),
    which needs semantic matching.
- **Precision falls with every recall gain:**
  - LongMemEval pooled precision of returned sessions: C2 0.510 → C3 0.381;
  - held-out precision: 0.752 → 0.728;
  - blind cohort: 0.756 → 0.680.
- **This is C3's main cost.** It is why C3 does not beat C2 on strict pass in the independent
  cohorts.

## Security, scope, correction and deletion

- **Held-out v2, blind cohort and AMB:** zero superseded, forgotten or other-scope returns.
- **Hard boundaries.** Selection only removes admitted facts, apart from closure and coverage,
  which add only already-admitted facts. The ranked-subsequence contract is enforced. Discovery
  vocabulary uses current-state admission's identity checks.
- **Review-found defects, all fixed and tested:**
  - **Blocking:** the #583 anti-laundering mask was bypassable by inflection.
  - **Should-fix:** refused text shaped discovery; closure followed text-derived relations.
- **Merge dependency:** this branch's base still accepts a cross-project write via `overrides`.
  That is the #786 defect, fixed on the #783 security stack. **C3 must be integrated with that
  stack before any adoption.**

## Performance and resources

- **Held-out recall latency p50:** 31.0 ms (C2 32.9, A 31.5).
- **Synthetic stress at equal candidate counts:** +12–20% over slice 1. A store of 3,000 facts
  with no candidates costs +18 ms for the vocabulary scan. A recall that newly finds its
  memories costs what admitting them costs.
- **Interpretation is linear:** a 16,000-word query takes 0.05 s.
- **Peak RSS** at 2,000 facts: 81 MB (A and C2: 77 MB).
- **No new storage, no new dependencies.**

## Generalisation answers

| Question | Answer |
|---|---|
| What real-world behaviour improved? | Counting, totals and comparisons across many memories; word-form and typo mismatch; named-entity questions; a changed state returned with its change (typed); abstention when the topic is absent. |
| Architectural deficiency | Selection judged each fact alone by surface-token overlap against one floor, with frame words treated as topic; it had no notion of the information requirement or of lifecycle relations. |
| Why it should generalise | It is built from closed-class English vocabularies, orthography, Porter step 1 and the runtime's own governed lifecycle evidence. It has no dataset identifiers or answer rules. It holds up on two cohorts authored blind to the code: recall rises, and safety stays at zero. |
| Which queries benefit | Aggregate and relational questions; inflected or misspelled single topics; questions naming entities; current-state questions with typed history. |
| Which regress or stay unsupported | Single-answer questions in stores with near-duplicates (extras: correction scenarios, distractor-heavy); multi-hop bridging; zero-overlap paraphrase; untyped state changes (C2's regression remains: 0/3 vs A 3/3); non-English. |
| Cost | About 15% more CPU per recall at equal candidates; an in-memory token memo per handle; no storage. |
| Survives correction, restart, deletion and scale? | Yes for correction, deletion and restart: tests cover each, including the memo after forget, and outputs are identical across reopen and hash seeds. For scale, linear interpretation and bounded entity coverage; the vocabulary scan is O(current facts) per recall. |
| Deterministic or inference-dependent? | Deterministic. No model, no paid inference, no randomness. |
| Useful without optional providers? | Yes. Everything runs with the semantic route and the extractor off. |

## Independent review and outstanding qualification

**Review.** Two blocking and five should-fix findings were repaired. The notes are accepted and
recorded, including the disclosure that the 2.1.0 anchoring change was diagnosed on LongMemEval
gold traces.

**Outstanding before this could become a default** (none of these were done here):
1. **Hidden holdout.** The independent evaluator's verdict on `6a2255c0`.
2. **Runtime Baseline successor and contract numbering.** A governance decision is needed to
   declare a successor and to number 1.9.0 against the v8 stack's 1.7.0/1.8.0.
3. **Integration with #783.** Needed for #786 write authority, and for re-running the full
   ladder on the integrated head.
4. **LongMemEval lane version.** The default return changes the runner's scored list (the
   evaluator's recommendation 2). That decision belongs to the benchmarking owners.
5. **Product decision.** Whether relevance-sufficient selection should be the default or opt-in.
   The independent cohorts show C3 at parity with C2 on strict pass, with higher recall and lower
   precision.

## Remaining gaps and next slice

1. **Precision of returned sets (highest value).**
   - Entity coverage should add a fact only for an entity no selected fact covers.
   - Ranking consistency should not pull in near-duplicates.
   - It must be measured on a *fresh* blind cohort, since held-out v2 and the multi-hop cohort
     have now been seen.
2. **Untyped state changes.** C2's regression remains. Options: the #732 extractor path, or a
   governed text relation under #671.
3. **Multi-hop.** Governed second-hop discovery, not selection-side bridging.
4. **Zero-overlap evidence.** Calibrate the local semantic route inside selection.
