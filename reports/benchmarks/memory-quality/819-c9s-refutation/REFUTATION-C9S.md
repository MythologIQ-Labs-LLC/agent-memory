# #819 C9-S: decoupled semantic sufficiency is refuted before implementation

**Decision: no runtime change (owner choice after this feasibility check).**

The C9-D handoff proposed decoupling the semantic route's two roles:
- **Discovery:** the dense top-r enters admission regardless of the 0.30 floor.
- **Sufficiency:** credited only above the floor, or with lexical corroboration.

An offline feasibility check on the development data shows that this design cannot reach the memories it was meant to reach. No rule in the family Pareto-improves C4+sem.

## Data and method

**Data.** Seven development sets: C6 diag, C5 dev, C6 reviewer gen, C7 dev, C8 dev, and the C9-D longitudinal and merged sets. That is 298 queries and 384 needed memories. No e4, e5 or e6, and no hidden gold.

**Features.** `tools/features.py` records one row per query and in-scope current memory (9,587 rows, `evidence/features.jsonl.gz`):
- dense cosine and dense rank among the scope's memories, with the pinned MiniLM `sha256:74477054…`;
- cosine relative to the query's best;
- whether a topical query term matches (admitted-set BM25 > 0);
- C4's selection basis, taken from a C9-D+sem run (`ba955a70`).

**Simulator.** `tools/simulate.py` reproduces C4+sem from these features exactly on strict passes (56/298) and on returned needed memories (241/384). Its extras come out at 558 against 616 observed, because it ignores budget truncation and `may_include` handling.

## Findings

1. **No corroboration exists for the misses.** C4+sem misses 143 needed memories (`evidence/misses.txt`):
   - all 143 have cosine ≤ 0.30;
   - **none shares a topical term with the query**;
   - 8 are dense rank 1, 20 are rank 2–3, and 115 rank lower.

   "Below the floor, with lexical corroboration" therefore admits nothing new: `C4 | (topical & rank ≤ 3)` returns 241 needed memories, the same as C4+sem, with +1 extra.
2. **Sufficiency restrictions above the floor trade reach for precision.** Requiring cosine ≥ t × the best match:

   | t | Strict (C4+sem: 56) | Needed returned (C4+sem: 241) | Extras (C4+sem: 558) |
   |---:|---:|---:|---:|
   | 0.5 | 68 | 233 | 467 |
   | 0.6 | 76 | 231 | 412 |
   | 0.7 | 90 | 219 | 343 |
   | 0.8 | 95 | 202 | 302 |

   Rank-capped variants, which are C6's shape, reach strict 94–99 but return only 188–196 needed memories. Every variant with more strict passes returns fewer needed memories.
3. **Below-floor reach costs abstention.** As measured for C9-D, guaranteeing the dense top-1 past the floor gains 8 needed memories, adds 23 extras, and makes 10 no-answer queries return something.

## Consequence

On this data, the semantic route cannot raise end-to-end recall above C4+sem without a precision or abstention cost. This holds for any rule over cosine, dense rank, relative cosine and topical match. The 143 misses carry no lexical evidence, and their dense evidence is indistinguishable from neighbours in the same range.

Reaching them needs signal this pipeline does not have. Two examples are a different representation (the model's ceiling, which C6's diagnosis already noted) and caller-declared structure. The C9-D handoff recommendation (RESULTS-C9D.md §5) is withdrawn.
