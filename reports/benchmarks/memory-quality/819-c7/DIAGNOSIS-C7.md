# #819 C7 diagnosis: where multi-evidence recall is lost, and whether ranking is the dominant stage

**Data.** Self-authored synthetic content from `dev/build_c7_set.py`:
- 6 life-domain stores of 36–45 memories each;
- 48 queries needing 76 memories.

Query kinds:
- 17 multi-evidence questions (2–4 needed memories, worded differently from the question and from each other);
- 7 corroboration questions;
- 6 single-answer questions with topical distractors;
- 6 single-answer questions with weak lexical overlap;
- 6 newer-against-older conflict questions (both remembered, no correction);
- 6 no-answer questions.

Every store also holds a question-shaped note, allowed but never needed, and ordinary filler.

**Harness.** Every query runs through the public facade (`dev/diagnose_c7.py`).

**Not used.** No benchmark data, gold or wording; no hidden cohort; no other user's content. The competitive evidence at `8887bbe` (branch `claude/810-external-exec-no-ci`) motivated where to look. Nothing in it is a target here.

## Revisions

| Item | Revision | Relation |
|---|---|---|
| main | `38f6a7dc` | Base of everything below |
| A (accepted baseline) | `7c06468a` (runtime equals `1df28f84`) | Descends from main |
| C4 (frozen) | `bc2be631` | Descends from A |
| C6 (frozen, under independent evaluation) | `171e67db` | Descends from C4. `reference/` equals `fab09130` |
| Security lineage | #805 `28f257c9` → #815 `77c472e6` → #816 `e13d8c58` | Descends from main. **Not** in the C lineage |
| Competitive evidence | `8887bbe` | Descends from main. No runtime change, only bridges and reports. Its LongMemEval rows measured `e4e2a4be` (main lineage, pre-C) with the route off, `ranked_prefix`, top_k 50 |
| **C7 development base** | **C6 `171e67db`**, branch `claude/eager-dirac-bftkfg-819-c7` | See the reasoning below |

**Why C6 as the base.**
- Under `ranked_prefix`, C6's semantic discovery is C4's, so C7 against C4+sem isolates the ranking change.
- Under relevance-sufficient selection, C7 against C6+sem isolates it too.

**Consequences of this choice.**
- **If C6 is rejected:** C7's commits must be rebased onto C4.
- **Security stack:** it is not merged into C7. Release qualification needs it, as for C6.

## Stage attribution (76 needed memories)

| Configuration | Returned | Withheld (admitted, not returned) | Refused | Never discovered | Admitted needed at rank ≤5 / 6–10 / >10 | All needed evidence in the top 5 (of 42) | Extras | Strict |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| A | 38 | 6 | 0 | 32 | 30 / 8 / 6 | 17 | 383 | 0 |
| C4 default (route off, `relevance_sufficient`) | 24 | 21 | 0 | 31 | 31 / 8 / 6 | 17 | 39 | 10 |
| C4+sem, `ranked_prefix` (= C6+sem `ranked_prefix`) | 44 | 16 | 0 | 16 | **33 / 11 / 16** | 19 | 393 | 0 |
| C4+sem, `relevance_sufficient` | 50 | 10 | 0 | 16 | 33 / 11 / 16 | 19 | 117 | 4 |
| C6+sem, `relevance_sufficient` | 32 | 17 | 0 | 27 | 32 / 9 / 8 | 18 | 45 | 11 |

### Two regimes

- **Route off: discovery dominates.** 32 of 76 needed memories are never discovered. These short facts share no word with the question. That is C5/C6 territory, and without a provider C7 changes nothing by design.
- **Route on: ranking dominates.** 60 of 76 are admitted, but only 33 rank in the top 5 and 16 rank below 10.

  Ordering the same admitted list by the pinned model's cosine alone would put 52 of the 60 in the top 5. This is diagnostic, never fed back to the runtime.

### Why admitted evidence ranks low (C4+sem, `ranked_prefix`; 27 needed memories below rank 5)

Of these 27, 22 are in the top 5 by cosine. They fall into two groups.

| Group | Count | Cause |
|---|---:|---|
| Found only by the semantic route | 14 | Ranking policy 3.2.0/3.4.0 orders `route_corroboration_count` first and treats the semantic route as *subordinate*: it orders only after every relevance and temporal stage. A semantic-only memory therefore ranks below **every** lexically found memory, filler included. Example: "Drove up to the Highlands for a long weekend in August." is rank 12 for "Which trips did I take this year?" (cosine rank 2), behind filler that shares only "I" or "did" |
| Found lexically, with weak BM25 | 13 | Function-word or partial overlap. Topical non-answers and filler outrank them on BM25, and the dense signal only breaks exact ties |

The stage order is lexicographic, so a second signal can only break ties below the first. This is the defect #673 describes.

### Multi-evidence questions specifically (45 needed memories, route on)

| Fate | Count |
|---|---:|
| Never discovered | 16 |
| Ranked >10 | 13 |
| Ranked 6–10 | 7 |
| Ranked ≤5 | 9 |

All the evidence is in the top 5 for 1 of 17 queries.

Ranking is the larger loss (20 of 45), but discovery (16) is not small. A ranking change cannot reach the 16, and they are left for a separately preregistered hypothesis.

### Newer against older conflicts

The newer statement ranks first in 2 of 6 under every configuration. Unspecified intent does not order temporally, so this is the separate newer-first deficit (docs/76). It is not addressed by C7, and C7 must not make it worse.

## Offline feasibility (`dev/fusion_feasibility.py`, recorded scores, no runtime change)

Inputs: C4+sem `ranked_prefix` admitted lists. Each order is scored on all needed evidence in the top 3, 5 or 10 (out of 42 queries) and on needed memories in the top 5 (out of 76).

| Order | All needed @3 | @5 | @10 | Needed in top 5 |
|---|---:|---:|---:|---:|
| Current (3.4.0) | 14 | 19 | 24 | 33 |
| Reciprocal-rank fusion, k = 60, of BM25 (> 0), shared-evidence and cosine ranks | 18 | 23 | 27 | 41 |
| Cosine only | 24 | 26 | 28 | 52 |

- **Insensitive to k.** At k = 10 and k = 30 the fusion results are the same, ±1.
- **By kind,** current → fusion:
  - multi: all needed evidence in the top 5 rises from 1 to 3 of 17, and needed memories in the top 5 from 9 to 15 of 45;
  - weak lexical overlap: 2 → 4 of 6;
  - corroboration, distractor and conflict: unchanged.
- **Why not cosine only, although it scores higher here.**
  - It lets similarity alone decide order, which exposes ranking to topical non-answers and to query-shaped text (C6 review, finding 2).
  - The external evidence does not support it: in `8887bbe`, a pure-vector store did not beat Agent Memory, while the two hybrid stores did.
  - This set's facts are short and lexically sparse, which flatters a dense ranker.

  Fusion keeps lexical relevance as an equal voice.

## Conclusion

With the optional provider present, the dominant loss of admitted multi-evidence is **ranking**. Specifically:
- the lexicographic stage order puts route corroboration and BM25 strictly above a subordinate semantic tie-break;
- semantic-only evidence is ordered last.

A bounded fusion of the existing signals over the admitted set is the smallest mechanism that targets this. Discovery losses (16 of 45 multi-evidence memories) and newer-first ordering remain, and are out of C7's scope.
