# #819 C9 preregistration: corroborated-rank sufficiency (selection policy 2.4.0)

Committed before any C9 runtime change and before any C9 candidate is run on the C9 development set.
The diagnosis it rests on is committed beside it (`dev/diag/`, `dev/analyze_withheld.py`).

## Authority and lineage

| Item | Value |
|---|---|
| Branch | `claude/determined-cray-i3fvsm` (the "selection engineer" lane of the 2026-10-17 coordination note), from frozen C8 `24d4dd26`. C8, C6 and C4 stay untouched |
| Comparators | C4 `bc2be631` (route off, and route on with default selection = "C4+sem"); C6 `171e67db` (route on, default); C8 `24d4dd26` (route on, default and `ranked_prefix`) |
| Not touched | Frozen comparators, evaluator branches and cohorts (e4, e5 spent; v4 and e6 unseen), the Runtime Baseline register, defaults, contract numbering, LongMemEval lane files |
| Not used | e5 per-case data. Only the published e5 aggregates motivate the question |

## The question (from the C8 independent review)

C8 ranks needed memories into its fused top 5 and then withholds them: 51 on e5, against 11 for C4+sem.
Sufficiency is decided on the 3.4.0 order (`AgentMemory._select_returned` passes
`base_ranked_admitted` to `select_relevance_sufficient`). Is a selection-stage change able to return
those memories without returning noise, and without similarity alone deciding sufficiency?

## Diagnosis (C8+sem, default selection, budget 5; five earlier development sets, 238 queries)

The facade's own `return_selection` record classifies every admitted memory that the fused top 5 holds
but selection withheld:

| Class | Needed (`must`) | Allowed (`may`) | Neither (noise) |
|---|---:|---:|---:|
| W1: topical relevance positive but below the floor (`below_relative_floor`) | 3 | 2 | 32 |
| W2: no topical term match (`no_informative_term_match`) | 34 | 6 | 666 |
| Total withheld in the fused top 5 | 37 | 8 | 700 |

- **92% of the withheld needed memories are W2.** They share no topical word with the query (paraphrase),
  so the only evidence for them is dense similarity. 95% of the withheld noise is also W2.
- Simple separators were tallied (diagnostic, not a candidate): dense rank 1 among admitted gives 9 needed
  against 45 noise; at least the highest returned cosine gives 4 against 15. **Every rule that recovers W2
  does so on similarity alone**, which this program excludes as evidence of sufficiency, and none of them
  separates evidence from noise.
- **Selection-only ceiling without dense-alone evidence: 3 of 37** (the W1 needed memories).
- C8 and C6 return identical sets on all five sets, as the evaluator found on e5. C4+sem returns more needed
  memories (226 against 143 in total) and more extras (367 against 179), with fewer strict passes (48 against 83).

So the e5 gap to C4+sem is a *dense-only sufficiency* difference (C4+sem's route proposes every neighbour
at cosine 0.30 or above, and route evidence is sufficient), which belongs to the discovery and proposal
policy, not to a selection rule that must not trust similarity alone.

## Hypothesis

**H9.** Within the selection stage, a withheld admitted memory that carries *both* positive topical lexical
evidence *and* dense agreement with evidence selection already returns is useful evidence more often than
noise. Crediting it recovers some needed memories while adding at most as many extras.

**Prediction stated in advance.** In-sample on the five earlier sets, the mechanism below adds 1 needed
memory and 3 extras. **C9 is expected to stop at its gate.** It is preregistered anyway: it is the safest
form of "selection credits what fusion ranks" that respects the no-dense-alone rule, and a measured stop
locates the defect in discovery and proposal, not selection.

## Mechanism (selection policy 2.4.0; one new step, no new constant)

After entity coverage and before lifecycle closure, when the recall's ranking applied fusion (the optional
provider is on, the intent does not order by time, at most 512 admitted), a memory whose basis is
`below_relative_floor` becomes sufficient with basis `corroborated_rank` if and only if all of:

1. **Lexical evidence (non-dense):** its topical content relevance is positive, which is implied by
   `below_relative_floor`. W2 memories (`no_informative_term_match`) never qualify, so dense similarity
   is never the only signal.
2. **Fused rank:** the fused order places it above the lowest-placed memory already selected.
3. **Relative dense agreement:** its dense similarity is at least the lowest dense similarity among the
   selected primary-evidence memories (`exact_identity`, `non_lexical_route_evidence`, `content_relevance`).
   Similarity is compared only with evidence already justified on other grounds, never with an absolute
   threshold.

Consequences, all by construction:
- With nothing selected, there is no anchor and the recall still abstains.
- Under time-ordering intents, fusion is skipped and 2.4.0 equals 2.3.0.
- With the route off, there are no dense scores and 2.4.0 equals 2.3.0.
- Lifecycle closure runs after the new step, so a recovered memory brings the admitted later states that
  change it.
- Admission, refusals, candidates, `admitted`, the ranked order and `ranked_prefix` are unchanged.
  Selection only ever chooses among admitted memories, so superseded, forgotten, disputed, other-scope and
  other-tenant memories cannot be returned.
- Dense similarities are read from the fused ranking's own evidence (`ranking_evidence[...]["fusion"]["dense_similarity"]`),
  so there are no extra model calls.

**Preregistered test change.** C7's `test_fusion_does_not_make_a_below_floor_memory_sufficient` encodes the
C7/C8 invariant that H9 deliberately relaxes: its `memory:serviced` is W1, fused above the only selected
memory, and more similar than it. C9 restates that test as two tests: the corroborated case is now
returned with basis `corroborated_rank`, and the same memory with a cosine below the anchor stays withheld.

## Fail-first tests (`reference/tests/test_c9_corroborated_selection.py`)

Fail on C8 `24d4dd26`, pass on C9:
1. A W1 memory fused above the selected memory and at least as similar as it is returned (`corroborated_rank`).
2. A recovered memory's lifecycle successor joins it.

Hold on C8 and C9 (false-positive and safety controls):

3. A W2 memory with the highest cosine and fused rank 1 stays withheld.
4. A W1 memory less similar than the selected evidence stays withheld.
5. A W1 memory fused below the lowest selected memory stays withheld.
6. A recall whose admitted memories are all W2 still abstains, whatever their cosines.
7. Under a caller-declared `current` intent, selection is identical to 2.3.0; an ended-window statement is
   not returned.
8. Route off: returned lists and records equal 2.3.0.
9. Superseded, forgotten and other-scope memories with W1 text and high cosine are never returned or
   leaked as text.

## Engineering gate

Primary set: `dev/c9-scenarios.json` (55 queries, fresh, committed at `51f39ee2` before any C9 run).
Regression sets: C8 dev (57), C7 dev (48), C6 diagnosis (30), C5 dev (48), C6 reviewer (55).
Budget 5, default selection, route on, unless stated. Comparator: C8+sem default.

| Criterion | Requirement |
|---|---|
| **P1 (recovery)** | On the C9 set, needed memories returned ≥ C8 + 2 |
| **P2 (precision)** | On the C9 set and on the union of regression sets: added extras ≤ added needed memories; strict ≥ C8 |
| **P3 (abstention)** | No-answer queries returning something ≤ C8, on every set |
| **I1** | Route off: identical returned lists to C8 (and C4) on every query of every set |
| **I2** | `ranked_prefix`: identical to C8 on every query of the C9 set |
| **I3** | Zero safety violations (superseded, forgotten, other scope, ended window under current intent) on every set; governance tests pass |
| **I4** | Determinism: two runs, one with a different `PYTHONHASHSEED`, give identical returned lists on the C9 set |
| **I5** | Cost: no additional model call; p50 on the C9 set ≤ C8 p50 + 2 ms |
| **L1 (LongMemEval, secondary)** | If the pinned LongMemEval-S input can be fetched locally: a bounded semantic-on comparison (C8 against C9, default selection, a fixed first-N question subset declared before the run, both planes if runtime allows), reported as paired wins and losses at @3, @5 and @10. Not gating unless complete at 500; a significant loss at any depth is reported as a defect |

**Stop rule.** If P1 or P2 fails, C9 stops with a negative-result record. No constant or rule changes after
results. If an invariant fails, fix or reject without changing the rule.

## Not claimed in advance

- No discovery change. The 21 to 31 needed memories per set that are never discovered stay so.
- No paraphrase recovery: W2 is excluded by design.
- No newer-first change under unspecified intent.
- No claim on e6. The independent evaluator owns it.
