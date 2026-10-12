# #775 Relevance qualification: research prototype (evaluation-only)

| | |
|---|---|
| Branch | `validation/775-relevance-qualification-research` (evaluation code only, no runtime change) |
| Collision corpus | Northgate v1, **frozen at `eda9635` before any prototype ran** (16 questions, 11 answerable) |
| Baseline served lists | unchanged v7 parent `9b025f9` composed recall, via the v3 runner with separated provenance; instant `2026-10-12T12:00:00Z` |
| **Verdict** | **CHANGES REQUIRED / not ready for runtime.** No rule is promotable. R1 is the only zero-false-negative rule and its gain is small. Subject anchoring must come from governed typed identity, not capitalization or term frequency. |

All rules only **remove** served items (no backfill), so nothing is broadened beyond governed admission. No rule was tuned on any listed corpus: R1's ½ cut is a majority rule, R2 uses the minimum frequency, R3 is structural.

## Results (legitimate = grade ≥ 2, eligible; a lost legitimate item is a false negative)

| Corpus | Rule | Irrelevant withheld | Context lost | **Legitimate lost** | Critical coverage lost | Answer@1 | No-answer items |
|---|---|---|---|---|---|---|---|
| Northgate (collision) | R1 discriminative-term | 1 | 0 | **0** | – | 8→8/11 | 10→9 |
| | R2 anchored coverage | 6 | 0 | **3** | N01, N02, N14 | 8→7 | 10→9 |
| | R3 entity anchors | 13 | 1 | **1** | N12 | 8→8 | **10→1** |
| Halcyon v1.1 | R1 | 3 | 0 | **0** | – | 13→13/21 | 9→7 |
| | R2 | 29 | 1 | **7** | H01, H02, H08, H10, H13, H22 | 13→11 | 9→4 |
| | R3 | 20 | 1 | **4** | H09, H13, H23 | 13→12 | 9→6 |
| Cedarline v1.1 | R1 | 5 | 0 | **0** | – | 14→14/20 | 8→6 |
| | R2 | 20 | 0 | **9** | C03, C06, C10, C14 | 14→12 | 8→6 |
| | R3 | 10 | 0 | **5** | C03, C05, C12 | 14→12 | 8→5 |

R4 (R1 and R3 together) behaves like R3. Full lists are in `results-775.json`.

## Interpretation

- **R1 (discriminative-term)** is the only rule with **zero false negatives** on all three corpora.
  - It removes 1–5 irrelevant items per corpus and empties one no-answer context (C21).
  - **It does not separate wrong-subject candidates.** Northgate's "Hilltop" vs "Riverside" facts share every discriminative word except the entity name.
- **R2 (anchored coverage) is harmful.** It requires the query's rarest in-scope token, which is often a paraphrase word or the successor in a history question, so it drops answers (e.g. H02 `pgver-15`, H22 `ratelimit`, C06 `owner-integrity`).
- **R3 (capitalized entity anchors) is the overfitting trap the issue warns about.**
  - On Northgate, whose entities are capitalized clinic names, it withholds 13 irrelevant items and empties 4 of 5 no-answer contexts (N06, N07, N09, N13).
  - On the other corpora it drops valid answers because the question capitalizes a word the memory doesn't: "Thursday" (H09), "AWS" (H13), "ALTER TABLE" (H23), "CSV"/"Parquet" (C03), "Cedarline" (C05/C12).
  - It also fails a valid same-for-both-entities fact on Northgate (N12, "Both clinics …").

## Recommended engineering direction

1. **Subject anchoring from governed identity.** Use the typed proposition subject recorded at write time (`typed_proposition.subject`), or caller-declared entity scopes, compared with an entity resolved from the query by a *separately measured* resolver. Missing typed identity yields *uncertainty*, never exclusion (as #775 requires).
2. **R1** may be considered as a necessary condition only after **blind** validation that includes paraphrase strata, with possessive and inflection handling measured separately.
3. **Exact-identity and graph-route evidence must bypass lexical qualification.** None of these rules looked at route provenance, which is a gap to close before any runtime change.
4. Report `no_qualified_evidence` (never "abstained") when a filter empties a context, and keep withheld items available as a separate, non-answer diagnostic channel, as #773's D773-2 did for known-not-current refs.

## Limitations

- Northgate was authored by the same reviewer as the prototype. It was frozen before the prototype ran, but it is not blind.
- Corpora are small (16–24 questions), so differences of one or two items are within noise.
- Rules were applied post hoc to served lists at the frozen budgets. Interactions with backfill or ranking are not measured.
