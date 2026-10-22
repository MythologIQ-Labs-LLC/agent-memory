# #774 strict caller-targeted predecessor selector on the integrated #776/#777 head: blind replay

Same-harness replay of the two blind corpora from the independent #774 evaluation
(`validation/774-blind-holdout`: theatre, frozen `af09d61`, gold v1.1 `e560be6`, successor
annotations by a second independent author; vineyard, frozen `45b6d14`, gold v1.1 `6dd042d`), with
the evaluator at `evaluation/served-memory-quality-first-no-ci` @ `9961067d020c4f1a1817f222f5a29af76884b4b2` (v3), the same caller
intents for every runtime, no tuning and no fixture change. `measure_head.py` is the independent
reviewer's `measure_strict.py` with only the runtime roots and plan changed (paths elided).

| Runtime | Mode | Theatre: P0 · top-1 critical · all-critical (of 21) | Vineyard: P0 · top-1 critical · all-critical (of 20) |
|---|---|---|---|
| `ec811f9` (PR #783 head, no #774) | composed | 0 · 9 · 11 | 0 · 9 · 13 |
| `500acfa` (#774 strict on that head) | composed | 0 · 9 · 11 (served lists byte-identical to `ec811f9`) | 0 · 9 · 13 (byte-identical) |
| `500acfa` | strict, annotated successor | **0 · 16 · 17** | **0 · 18 · 19** |
| `500acfa` | strict, no target | 0 · 9 · 11 (byte-identical to composed) | 0 · 9 · 13 (byte-identical) |

For reference, the independent evaluation reported v7 `9b025f9` composed at 9/21 · 11/21 and 9/20 · 13/20,
and the strict selector at `4088823` at 16/21 · 17/21 and 18/20 · 19/20: the integration reproduces
both exactly. Only annotated predecessor questions with a resolvable successor change (theatre
Q01, Q02, Q04, Q14, Q18, Q20, Q22; vineyard Q01–Q11); every unresolved target (theatre Q15–Q17,
vineyard Q12–Q16: deleted, other scope, never changed) is served unchanged. `cases_with_prohibited_exposure`
and `cases_with_stale_exposure` are 0 in every run, including the composed runs, because the
#776 admission repair on this head withholds deleted lineage in plain historical recall as well.

Caveats carried over from the independent evaluation: the gains assume the caller identifies the
successor (here an independent annotator did, which upper-bounds a real caller); natural-language
successor resolution is not promoted; automatic routing is not promoted.
