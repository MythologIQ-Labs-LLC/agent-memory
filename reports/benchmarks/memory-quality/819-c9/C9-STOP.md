# #819 C9: corroborated-rank sufficiency stopped at its preregistered gate

**Status:** implemented, tested and measured locally. **Stopped:** P1 and P2 failed, as predicted in the
preregistration. C9 is not frozen, not handed to the evaluator, and not a default candidate. This is a
negative-result record. It locates the defect.

## Identity

| Item | Value |
|---|---|
| Branch | `claude/determined-cray-i3fvsm`, from frozen C8 `24d4dd26` (C8, C6 and C4 untouched) |
| Runtime head measured | `4c64d8267f13b5cf54c003aed669ed4448edfc61` (selection policy 2.4.0) |
| Preregistration | `33bcc9bf`, before any runtime change; erratum 1 and fail-first tests at `12644e77` |
| C9 development set | `51f39ee2`, before any C9 run on it (55 queries, six new topics) |
| Hidden cohorts | None read. e4/e5 per-case data was not used; v4 and e6 were not touched |
| Hosted CI / PR | None. All runs local, 4 vCPU container, Python 3.13.16, pinned model `multi-qa-MiniLM-L6-cos-v1@b207367` (digest-verified fetch) |

## 1. Why the selection stage withholds relevant admitted facts

`AgentMemory._select_returned` passes `base_ranked_admitted` (the 3.4.0 order) to `select_relevance_sufficient`.
Fusion therefore only reorders what 2.3.0 already chose. Every admitted memory that C8's fused top 5 held but
selection withheld was classified with the facade's own `return_selection` record (budget 5, route on, five
earlier development sets, 238 queries; `dev/analyze_withheld.py`):

| Withheld from the fused top 5 | Needed | Allowed | Noise |
|---|---:|---:|---:|
| W1: topical relevance below the floor | 3 | 2 | 32 |
| W2: no topical term match | 34 | 6 | 666 |

- **The withheld needed memories are paraphrases** (34 of 37 share no topical word with the question). They
  are admitted only because the lexical route matched a function word ("my", "is"), the same reason the 666
  noise memories are admitted.
- **Only dense similarity distinguishes them, and it does so poorly.** Dense rank 1 among the admitted gives
  9 needed memories against 45 noise; "at least the highest returned cosine" gives 4 against 15. A
  question-shaped or topical distractor routinely has the highest cosine (0.615 in one C8-set case).
- **The e5 gap to C4+sem is a proposal-policy difference, not a selection one.** C4+sem's route proposes
  every neighbour at cosine 0.30 or above, and route evidence is sufficient. C6/C8 cap proposals (K = 1, or 3
  for set questions; nothing below a best of 0.40). Those memories are then admitted only lexically and
  withheld. Recovering them in selection would make similarity alone sufficient, which this program excludes.

## 2. Candidate (selection policy 2.4.0)

When fusion applied, a `below_relative_floor` memory becomes `corroborated_rank` if:
- the fused order places it above the lowest selected memory, and
- its dense similarity is at least the lowest similarity among the selected primary evidence.

W2 never qualifies. With nothing selected there is no anchor, so the recall still abstains. Time-ordering
intents and route-off recalls are unchanged. Lifecycle closure runs after the step. No constant was added and
no model call was added: similarities come from the fused ranking's own evidence.

Files: `runtime/return_selection.py`, `api/surface.py`, `api/contract.py` (`corroborated_rank_count`), and
`schemas/api-result-envelope.schema.json` (2.4.0 and the count).

## 3. Tests

- `reference/tests/test_c9_corroborated_selection.py`, 9 tests:
  - 2 recovery tests, fail-first: they fail on C8 (`fail-first-on-C8-24d4dd26.log`) and pass on C9.
  - 7 controls that pass on both heads:
    - a top-cosine memory with no topical match stays withheld;
    - a less-similar memory and a memory fused below the selected evidence stay withheld;
    - all-W2 recalls abstain;
    - declared current intent keeps the valid statement first;
    - superseded, forgotten and other-scope text never appears;
    - route off is unchanged.
- C7's `test_fusion_does_not_make_a_below_floor_memory_sufficient` is restated as preregistered
  (`test_fusion_alone_does_not_make_a_memory_sufficient`).
- Focused suites (C4, C6, C7, C8, evidence-set, relevance-sufficient, lifecycle, API contract, API surface,
  developer facade, AMB bridge, LongMemEval runner): 111 + 104 tests, the existing expected failure only.
- Full suite at `4c64d826`: see section 6.

## 4. Gate (budget 5, route on, default selection unless stated; `dev/comparison.json`)

| Criterion | Result | Verdict |
|---|---|---|
| **P1** needed returned on the C9 set ≥ C8 + 2 | 33 against 32 (+1) | **FAIL** |
| **P2** added extras ≤ added needed; strict ≥ C8 | All six sets: +2 needed, +8 extras; strict equal on every set (0 wins, 0 losses) | **FAIL** |
| P3 no-answer queries returning something ≤ C8 | equal on every set | met |
| I1 route off identical to C8 and C4 | identical on every query of all six sets | met |
| I2 `ranked_prefix` identical to C8 (C9 set) | identical on all 55 | met |
| I3 safety violations | 0 on every set and arm | met |
| I4 determinism (`PYTHONHASHSEED` 0, 1, 12345) | identical returned lists and top-5 orders | met |
| I5 cost | no extra model call by construction; see section 6 for latency | see section 6 |

What 2.4.0 changed (6 of 293 queries):

| Set | Query | Added (role) | Strict |
|---|---|---|---|
| C9 | pets-1 | `vet-weight` (needed), `groomer` (noise) | fail → fail |
| C8 | kitchen-3 | `knives` (needed) | fail → fail |
| C8 | school-4 | `cubs`, `nut` (noise); budget displaced a filler | fail → fail |
| C7 | hobby-6 | `climb`, `book-club` (noise) | fail → fail |
| C6 reviewer | 2 queries | 4 noise | unchanged |

## 5. Comparison against C4 and C6 (C9 set; all sets in `dev/comparison.json`)

| C9 set, 55 queries | C4 (off) | C4+sem | C6+sem | C8+sem | **C9+sem** |
|---|---:|---:|---:|---:|---:|
| Strict | 31 | 23 | 35 | 35 | **35** |
| Needed returned (of 45) | 23 | **36** | 32 | 32 | 33 |
| Extras | **21** | 64 | 26 | 26 | 27 |
| Queries with nothing required that still return something (of 17) | **6** | 12 | 7 | 7 | 7 |
| Safety violations | 0 | 0 | 0 | 0 | 0 |

Paired strict, C9+sem against each comparator:

| Set | vs C4 | vs C4+sem | vs C6+sem |
|---|---|---|---|
| C9 | +5/−1 (p 0.22) | +14/−2 (p 0.004) | 0/0 |
| C8 | +1/−0 | +11/−2 (p 0.02) | 0/0 |
| C7 | +2/−1 | +9/−2 (p 0.07) | 0/0 |
| C6 diagnosis | +7/−1 (p 0.07) | +7/−1 (p 0.07) | 0/0 |
| C5 dev | +11/−1 (p 0.006) | +7/−3 (p 0.34) | 0/0 |
| C6 reviewer | +5/−1 (p 0.22) | +10/−1 (p 0.01) | 0/0 |

C9 is C6/C8 to within 2 needed memories. Its strict advantage over C4+sem, and its recall deficit (for example
33 against 36 of 45 on the C9 set), are both C6's.

## 6. LongMemEval-S and cost

LONGMEMEVAL_PLACEHOLDER

## 7. Unresolved defects (stated plainly)

1. **Paraphrase evidence is unrecoverable at selection without trusting similarity alone.** This is the bulk
   of the e5 "51 withheld". The fix belongs to the semantic route's proposal policy (C6's K cap and 0.40
   `min_best`), which the evaluator already asked to replace. That is discovery work, outside this lane.
2. **Similarity does not separate answers from topical neighbours** on any data examined, so a looser
   proposal policy will trade precision for recall (C4+sem: +4 needed, +38 extras on the C9 set). It needs a
   non-dense answerability signal, which does not exist in the runtime today.
3. **Never discovered:** 4 to 31 needed memories per set are never proposed by any route; C9 cannot reach them.
4. Inherited, unchanged: newer-first under unspecified intent, multi-hop bridging, the 512-admitted fusion
   fallback, the Runtime Baseline successor declaration, the security-stack rebase, and the LongMemEval lane
   version.

## Recommendation

**Do not adopt 2.4.0.** It is safe (all invariants met) but does not move user-visible quality. Keep `ranked_prefix`
and C6/C8 status as decided by the evaluator. The next hypothesis should target the proposal stage with a
signal other than cosine alone, preregistered against fresh e6, in the discovery lane.
