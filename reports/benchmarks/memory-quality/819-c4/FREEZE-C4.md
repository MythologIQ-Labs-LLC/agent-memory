# #819 C4 freeze: candidate `bc2be631`

| Item | Value |
|---|---|
| **C4 runtime candidate (frozen)** | `bc2be6319a3eda96731fdb235f4feba882bcb9be`, branch `claude/eager-dirac-bftkfg-819-c4` |
| Base | C3 evidence head `8549e942` (runtime = C3 `6a2255c0`). C2 `eaf60e4d`, C3 and their evidence branches are untouched. |
| Selection policy | `relevance-sufficient-return-selection` `2.3.0`. The contract number is still the candidate `1.9.0`: **not advanced, no Runtime Baseline successor, unaccepted.** |
| Configuration | Default facade; semantic route off; no paid inference; no new storage or dependencies |
| Preregistration | `PREREGISTRATION-C4.md` (`2c710b72`, before any runtime change), errata 1–3 recorded before the freeze |
| Fresh held-out | v3, sealed `532f39d0…` at `3dc81c8d` before the freeze; authored by a separate agent without runtime access; opened only after the freeze |
| Execution | Local only; 0 hosted Actions; no PR |

## What changed against C3

1. **Uncovered-entity coverage.**
   - An entity mention is covered when a selected fact writes it **as a name** with at least half
     the best admitted relevance to it. Only an uncovered entity adds the admitted fact most about it.
   - "As a name" follows the query interpreter's own orthography: capitalised, not starting a
     sentence or clause unless possessive, and not in all-caps or title-case text; or a
     letter–digit token.
   - So "Mom's new mailing address…" covers Mom, while "mark it urgent", "Mark the form…" and
     "- Mark it urgent" do not cover Mark.
2. **Ranking consistency anchored on the best primary fact.** A below-floor fact is promoted only
   when ranking places it above the highest-ranked primary-evidence fact.
3. **Per-fact diagnostics.** Each admitted fact's record now states `requirement`,
   `query_terms_matched`, `query_terms_added` and `entities_added`.

**Removed before the freeze:** preregistered change 3, term-coverage dominance. Independent review
showed that matching more of the question's words is not answering it: a tool could suppress a
user's answer by restating the question. Its date guard was manipulable, and the mechanism was
quadratic. See erratum 3 and `REVIEW-C4-adversarial.md`.

## Tests

`reference/tests/test_c4_selection_precision.py` (23 test methods) covers:
- fail-first cases;
- every reviewer reproduction, each failing on the reviewed head;
- homograph layouts;
- governance: correction, forgetting, other scope, `ranked_prefix`.

**Full suite at `bc2be631`:** 2654 tests, 36 skipped. The one failure is the Runtime Baseline
equivalence guard, which fails by design for any runtime change until a successor is declared.

## Measured

### Held-out v3 (fresh, independent author, sealed before the freeze, one run each, same runner)

250 queries: 202 single, 17 multi, 31 abstention.

| | A `1df28f84` | C2 `eaf60e4d` | C3 `6a2255c0` | **C4 `bc2be631`** |
|---|---:|---:|---:|---:|
| Strict pass | 52 | **161** | 151 | 153 |
| Mean precision | 0.462 | **0.824** | 0.778 | 0.783 |
| Mean recall | **0.888** | 0.827 | 0.867 | 0.865 |
| Safety violations (forgotten or other-scope returned) | 0 | 0 | 0 | 0 |
| Recall latency p50 / p95 (ms) | 25.9 / 39.2 | 25.0 / 38.5 | 28.0 / 41.7 | 25.7 / 39.8 |

Paired strict pass (exact McNemar; bootstrap 95% CI of the pass-rate difference, 10,000
resamples, seed 819):

| Comparison | Improved / regressed | p | Δ pass rate [95% CI] |
|---|---|---:|---|
| **C4 vs C3** | +2 / −0 (correction 1, multi-evidence 1) | 0.50 | +0.008 [+0.000, +0.020] |
| C4 vs C2 | +11 / −19 | 0.20 | −0.032 [−0.076, +0.012] |
| C3 vs C2 | +10 / −20 | 0.10 | −0.040 [−0.084, +0.000] |
| C4 vs A | +106 / −5 | <0.001 | +0.404 [+0.340, +0.468] |

C4 vs C2 by category (C4 improved / regressed): imperfect_query +6/−1; multi_evidence +3/−3;
entity_redundancy +1/−6; correction +1/−4; currentness 0/−3; abstention 0/−1;
forgetting_and_scope 0/−1.

Strict pass by category:

| Category | A | C2 | C3 | C4 |
|---|---:|---:|---:|---:|
| abstention (30) | 2 | 15 | 14 | 14 |
| correction (34) | 5 | **20** | 16 | 17 |
| currentness (28) | 4 | **16** | 13 | 13 |
| distractor_heavy (32) | 5 | 26 | 26 | 26 |
| entity_redundancy (32) | 1 | **25** | 20 | 20 |
| forgetting_and_scope (34) | 20 | **27** | 26 | 26 |
| imperfect_query (32) | 10 | 20 | **25** | **25** |
| multi_evidence (28) | 5 | **12** | 11 | **12** |

**Acceptance against the preregistration:**
1. **Strict pass over C3:** improved by 2, not statistically significant (p = 0.50).
2. **Recall:** 0.865 against C3's 0.867, inside the 0.02 margin.
3. **Safety:** zero violations.

**Verdict: C4 is a small, safe improvement over C3. It does not recover C2's strict-pass lead.**
C2 remains ahead on correction, currentness, entity redundancy and abstention. C3 and C4 lead on
imperfect queries and recall.

**Why C4 still trails C2 (post-freeze diagnosis, for the next cycle; no tuning on this cohort).**
Of C4's 154 extra returned facts on v3:
- 121 are primary `content_relevance` facts on single-answer questions (C2 has 98);
- 21 are `ranked_above_sufficient` (C2 has 9);
- 7 are entity coverage. That was C3's main defect, now largely removed.

The remaining extras come from the slice 1/2 relevance changes (topical-only relevance and
word-form matching), which admit more near-topical facts against a 0.5 floor. That is the price of
C3's multi-evidence and imperfect-query recall.

### Diagnostic sets (seen during development; not independent evidence)

| | C3 | C4 |
|---|---:|---:|
| LongMemEval-S session trace, recall_all@5 | 0.862 | 0.869 |
| LongMemEval-S session trace, recall_all@10 | 0.905 | 0.907 |
| Pooled precision | 0.381 | 0.458 |
| Mean returned | 4.68 | 3.86 |
| Paired vs C3 | — | +3/−2 |
| AMB 77, strict | 38 | 39 (+1/−0) |
| AMB precision | 0.522 | 0.528 |
| AMB recall | 0.942 | 0.942 |

Native LongMemEval-S at the freeze. This uses the repository runner, `external_frozen`, budget 50, and all 500 questions; 419 have user-turn evidence. It is not pristine, because it was seen in earlier cycles, and nothing was tuned against its labels. Raw outputs and summaries are in `longmemeval/`.

| Plane | Revision | Mean returned | any@1 | all@5 | all@10 | all@50 |
|---|---|---:|---:|---:|---:|---:|
| session | A `1df28f84` | 45.1 | 0.809 | 0.823 | 0.893 | **1.000** |
| session | C2 `eaf60e4d` | — | 0.814 | 0.747 | 0.754 | 0.757 |
| session | C3 `6a2255c0` | 4.7 | 0.831 | 0.862 | 0.905 | 0.916 |
| session | **C4 `bc2be631`** | **3.9** | 0.831 | **0.869** | **0.907** | 0.907 |
| turn | A | 50.0 | 0.573 | 0.601 | 0.723 | **0.859** |
| turn | C2 | — | 0.578 | 0.549 | 0.632 | 0.654 |
| turn | C3 | 12.4 | 0.587 | 0.628 | **0.764** | 0.847 |
| turn | **C4** | **9.6** | 0.587 | **0.632** | 0.759 | 0.816 |

Paired comparisons use exact McNemar:

| Comparison | all@5 | all@10 |
|---|---|---|
| Session, C4 vs C3 | +4/−1, p = 0.38 | +3/−2, p = 1 |
| Session, C4 vs A | +27/−8, p = 0.0019 | +18/−12, p = 0.36 |
| Turn, C4 vs C3 | +7/−5, p = 0.77 | +5/−7, p = 0.77 |
| Turn, C4 vs A | +19/−6, p = 0.015 | +28/−13, p = 0.028 |

`ranked_prefix` at `bc2be631` reproduces A exactly on both planes, with 0 of 500 differing.

**Trade-off.**
- C4 returns 18–22% fewer facts than C3, with no significant change in all@5 or all@10.
- Turn all@50, which is the ceiling a caller gets from everything returned, falls from 0.847 to 0.816, and session all@50 falls from 0.916 to 0.907. C4 trades some long-tail completeness for precision.
- Both are below A's full 50-fact prefix, which remains available as `ranked_prefix`.

### Cost

- **Held-out recall latency:** p50 25.7 ms, against C3's 28.0 ms and C2's 25.0 ms.
- **Synthetic stores of 1,000–3,000 facts:** per-query latency within noise of C3.
- **Facade recall over 8,000 admitted facts:** about 3.0 s, against C3's 3.3 s (reviewer's measurement).
- **No new storage.**

## Independent review

Three passes (`REVIEW-C4-adversarial.md`):
1. **`3caf0c13`:** 2 blocking findings, 5 should-fix, 1 note. Dominance was removed and F5 fixed.
2. **`df1190e9`:** F5 was only partly fixed (capitalised homographs). Fixed.
3. **`6f85868f`:** note layouts (headline case, lists, line breaks, dashes). Fixed.

Accepted residual ambiguity:
- possessive shop names ("Mark's Hardware");
- vocatives after a comma;
- passing mentions;
- plural list questions without an aggregate cue are read as single.

Held across every pass:
- `ranked_prefix` byte-identical to C3;
- determinism;
- isolation, forgetting and reopen;
- no benchmark-specific code.

## Generalisation answers

| Question | Answer |
|---|---|
| Real-world behaviour improved | An answer is no longer padded with "the fact most about" a person it already names. Ordering noise among similar facts is not promoted. Every returned or withheld fact explains itself. |
| Architectural deficiency | C3 judged entity coverage and ranking consistency without asking whether a requirement was already met. |
| Why it should generalise | Both rules are deterministic: orthography plus relative relevance, and ranking position. No dataset vocabulary. The fresh cohort showed no regression against C3 and zero safety violations. |
| Which queries benefit | Single-answer questions about named people or things in name-dense stores; questions where ranking order is noisy. |
| Which regress or stay unsupported | No significant regression against C3. C2 is still better on correction, currentness and entity-redundant single answers. Also unsupported: plural lists without a cue, possessive homographs, zero-overlap paraphrase, multi-hop, untyped state changes. |
| Cost | Within noise; no storage. |
| Survives correction, restart, deletion and scale? | Yes, tested; linear cost. |
| Deterministic or inference-dependent? | Deterministic, no model. |
| Useful without optional providers? | Yes. |

## Integration

See `INTEGRATION-HANDOFF-C4.md`.

## Next slice

Single-answer precision inside primary relevance:
- a stricter relative floor, or a most-specific-term requirement, for `single` questions;
- ranking-consistency promotion only when ranking's advantage comes from a non-lexical stage named
  in its evidence.

Measure on a new sealed cohort; v3 is now spent.
