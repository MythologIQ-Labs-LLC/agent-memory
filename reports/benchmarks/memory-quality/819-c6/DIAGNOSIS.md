# #819 C6 diagnosis: where low-overlap evidence is lost

**Data.** The data is self-authored synthetic content: `dev/build_diag_set.py`, 7 scenarios and 30 queries, 32 needed memories. Each store holds about 30 memories, most of them irrelevant neighbours. Every query runs through the public facade (`dev/diagnose.py`).

**Not used.** No hidden cohort, no benchmark gold, and no other user's content. Only the querying scope's own synthetic text is read.

## Revisions

| Item | Revision |
|---|---|
| Baseline A (accepted comparison baseline) | `7c06468aae1aed0d2115c42f9588fbbe8417657e`. Its runtime is identical to `1df28f84`, the base of the C lineage (no `reference/` diff). |
| C4 (frozen) | `bc2be6319a3eda96731fdb235f4feba882bcb9be`. The C6 branch starts at C4's evidence head `9942a8a6`, whose runtime tree is identical. |
| C6 branch | `claude/eager-dirac-bftkfg-819-c6` |
| main | `38f6a7dc`. The C lineage is not on main. |
| Security lineage | #805 `28f257c9` → #815 `77c472e6` → #816 `e13d8c58`. The C lineage predates it; integration comes later. |
| Semantic route | Pinned local `multi-qa-MiniLM-L6-cos-v1` ONNX (#669), off by default. Run here with `semantic_retrieval="required"`. |

## Stage attribution (32 needed memories)

| Configuration | Returned | Withheld (admitted, not returned) | Refused by governance | Never discovered | Extra returned | Strict (of 30) |
|---|---:|---:|---:|---:|---:|---:|
| A (`ranked_prefix`, budget 10) | 17 | 5 (budget) | 0 | **10** | 157 | 1 |
| C4 default (`relevance_sufficient`) | 10 | **12** (selection) | 0 | **10** | 7 | 8 |
| C4 with the semantic route on | 20 | 5 | 0 | 7 | 22 | 8 |

- **Undiscovered evidence (10 of 32).** It shares no token with the question, so the lexical route never proposes it. For example, "Which animals live with us?" against "Biscuit, our beagle, …": "our" is not "us". A's ranked prefix cannot return it either. On the independent cohorts, A's paraphrase and aggregation recall came from small stores and incidental function-word overlap. That does not generalise to larger stores.
- **Dense reach of undiscovered evidence.** Its dense rank among all in-scope memories is 1–3 for 6 of the 10 and ≤ 5 for 8. The cosines are low (0.12–0.46). The semantic route's absolute 0.30 floor drops five of them: beagle 0.28, tabby 0.21, antihistamine 0.27, return flight 0.20, eSIM 0.16.
- **Withheld evidence (12 in C4).** It was discovered lexically through function words, but its topical BM25 is zero or below the floor. Most of it is dense rank 1–2 with clear similarity: beagle 0.61, Corolla 0.57, manager 0.48, client 0.45, knee 0.44, GP 0.40. Turning the semantic route on rescues some of it, but the route also returns every neighbour above 0.30 unconditionally (22 extras).
- **Governance never caused a loss.** No needed memory was refused. Other-scope memories are removed by the domain prefilter before any route sees them, and forgotten memories are refused as `tombstoned`.
- **Out of reach for this model.**
  - Some aggregate members are far from the question in embedding space: "new people on my team" against two hires at 0.17 and 0.13; "cause problems" against a risk at 0.05.
  - Fact-to-fact similarity is dominated by surface style, not kind: with the fish fact as anchor, household notes score up to 0.41 and the beagle 0.13. So sibling expansion from an anchor does not work with this model, and it was rejected after this feasibility check.

## What the evidence supports

Two kinds of loss are at work, and one discovery mechanism reaches both: **the semantic route's proposal policy.**

- Today the route proposes the top 16 neighbours above an absolute 0.30 floor, and selection treats each proposal as sufficient. It misses top-ranked evidence below 0.30 and floods the return with neighbours above it.
- A **rank-bounded** proposal policy would be better:
  - propose only the top K in-scope memories, with K set by query shape;
  - include only those within a relative margin of the best match;
  - propose nothing when even the best match is weak.
- This would reach top-ranked low-cosine evidence, rescue withheld top-ranked evidence, and cut the neighbour flood. It leaves selection exactly as in C4.

**Feasibility** (an offline union of C4's returns with dense top-K on this dev data):
- needed memories returned rise from 10 to 17–20, and strict passes from 8 to 12;
- extras rise from 7 to 12–15, against 22 for C4 with the semantic route on;
- 4 of 6 no-answer queries return something, because topically near memories score highly (weather → flight 0.59).

C6 is preregistered on this basis (`PREREGISTRATION-C6.md`).
