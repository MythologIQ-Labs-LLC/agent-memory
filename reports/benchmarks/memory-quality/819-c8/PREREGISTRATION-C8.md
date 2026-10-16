# #819 C8 preregistration: bounded rank fusion with an explicit cost budget and a restated temporal invariant

Committed before any C8 runtime change, and before C7 or C8 is run on the C8 development set.

## Authority and lineage

**Authorisation.** C7 (RRF fusion, ranking policy 3.5.0) stopped at its preregistered gate (`819-c7/C7-STOP.md`):
- it met every rank-quality criterion, including out of sample;
- it failed I4 because an *incidental* newer-first ordering under unspecified intent reversed (1 of 6, against 2 of 6);
- it failed I5 (cost).

**The program owner chose this successor** (session decision, 2026-10-16):
- re-preregister fusion on a fresh, newly authored development set;
- add an explicit cost budget;
- restate I4 so that it gates only orderings decided by a temporal stage;
- measure incidental newer-first, without gating it.

Engineering did not make that choice after seeing results. C7's record and invariants are unchanged.

| Item | Value |
|---|---|
| Branch | `claude/eager-dirac-bftkfg-819-c8`, from C7's stop head `bbdc71dc` (C7 runtime `d05bf2b1` plus records). C6 `171e67db` and C7 remain untouched |
| Comparators | A `7c06468a`; C4 `bc2be631` (route off, and route on with `ranked_prefix`); C6 `171e67db` (route on, `relevance_sufficient`) |
| Not touched | Security lineage, #821, C1–C7 evidence, evaluator branches and cohorts, the Runtime Baseline register, defaults |

## Hypothesis

**H.** C7's fusion, unchanged in every ranking constant, keeps its rank-depth gain on fresh data. Two cost changes bring it within the latency budget. It reverses no ordering decided by a temporal stage.

## Mechanism

**1. Ranking: identical to C7.** Ranking policy `3.5.0`:
- RRF with k = 60, equal weights, competition ranks;
- lists: admitted-set BM25 > 0, shared-evidence route score, dense similarity rounded to 1e-6;
- the stage order below temporal applicability and exact identity;
- bounded at 512 admitted;
- degrades to 3.4.0;
- sufficiency decided on the 3.4.0 order.

No ranking constant changes.

**2. Cost changes (new).**
- **Reuse the route's similarities.** The semantic route's scan already computes the query's cosine for every memory in its pool, and the admitted set is a subset of that pool. Fusion reuses those exact values, recorded by the retriever for that query, and computes only the missing ones. The values are bit-identical (same function and inputs).
- **One ranking pass under `ranked_prefix`.** The 3.4.0 base order is computed only when relevance-sufficient selection needs it.

## Development data

**`dev/c8-scenarios.json`.** Fresh, self-authored after C7 stopped; it shares no text with earlier sets. Seven stores, 57 queries, 78 needed memories:

| Kind | Queries |
|---|---:|
| multi-evidence | 18 |
| corroboration | 6 |
| distractor | 6 |
| weak lexical overlap | 6 |
| conflict, unspecified intent (newer-first measured only) | 6 |
| conflict with declared validity windows, under caller-declared `current` or `as_of` intent | 9 |
| no-answer | 6 |

The stores also contain question-shaped notes and filler.

**Fixture note** (found while writing the tests, before this commit and before any candidate run): caller-declared `current` intent needs a `reference_time`, otherwise applicability is `no_reference_time` and the tier does not act. The declared-intent queries and test 3 therefore carry `reference_time` 2026-10-16.

**Regression sets** (not development data for C8):
- C7's development set (48 queries; in-sample for C7's design);
- C6's development union (78);
- C6's independently authored reviewer set (55).

## Engineering gate (all required)

### Rank quality on the C8 set (C8 route on, `ranked_prefix`, against C4+sem `ranked_prefix`)

- **R1.** All needed evidence in the top 5: at least C4+sem + 3 queries.
- **R2.** Needed memories in the top 5: at least C4+sem + 6.
- **R3.** All needed evidence in the top 10 and in the top 3: at least C4+sem's.
- **R4.** At most 2 queries lose top-5 coverage that C4+sem had.

### Regression sets

- **R5.** On each regression set, under `ranked_prefix` with the route on:
  - needed recall@10 ≥ C4+sem's;
  - needed memories in the top 5 ≥ C4+sem's − 2.

### Selection (C8 route on, `relevance_sufficient`, against C6+sem; all four sets)

- **S1.** Returned sets equal C6+sem's wherever the budget does not bind.
- **S2.** Strict ≥, extras ≤ and no-answer queries returning something ≤ C6+sem's.

### Invariants

| Criterion | Requirement |
|---|---|
| I1 | Route off: identical to C6/C4 on every query of every set |
| I2 | Governance tests pass; zero safety violations |
| I3 | Deterministic: two full runs (one with a different `PYTHONHASHSEED`) give identical ranked orders |
| **I4′ (restated, owner-authorised)** | On every `conflict_declared` query, C8 ranks the preferred statement first whenever C6+sem does, under both `ranked_prefix` and `relevance_sufficient`. In particular, every pair whose two members have different temporal applicability under C6 keeps C6's order. Incidental newer-first under unspecified intent (`conflict` kind) is reported for C4, C6 and C8, but not gated |
| I5 | Latency and memory, same budget as C7: on the 200-memory probe (default selection), p50 ≤ C6+sem p50 + 10 ms; at 1,000 memories, p50 ≤ 1.15 × C6+sem; peak RSS ≤ 1.10 × C6+sem. Two runs each |

### Stop conditions

- **R1–R5 or I4′ fails: stop.** C8 stops with a negative-result record.
- **S1–S2, I1–I3 or I5 fails:** fix or reject, without changing any ranking constant.
- **Nothing is changed after results** among the constants or thresholds above.

## Fail-first tests (`reference/tests/test_c8_fusion_cost.py`)

**Must fail on C7 `d05bf2b1` and pass on C8:**
1. A route-on recall computes each pool memory's cosine once. The route's scan and fusion share the values, so the count of cosine evaluations equals the pool size, not more.
2. A `ranked_prefix` recall with fusion runs the ranking policy once. A `relevance_sufficient` recall runs it twice (base and fused).

**Must hold on C6, C7 and C8:**

3. Under caller-declared `current` intent, an older statement whose declared validity has ended ranks below the newer one, even when it has the higher BM25 and cosine.
4. The C7 tests (`test_c7_rank_fusion.py`) keep passing unchanged, including the expected failure.

## Review and handoff

- **Independent adversarial review before any freeze.** It covers the C7 list:
  - false-positive semantic matches;
  - query-shaped stuffing;
  - multi-evidence incompleteness;
  - temporal ordering;
  - security boundaries;
  - determinism;
  - provider outage;
  - over- and under-return.

  It also covers the correctness of similarity reuse: stale values across queries or stores.
- **Blocking findings** are fixed without changing thresholds.
- **If the gate is met:** freeze, record configuration, publish the disposition, hand off to the evaluator.
- **No successor declaration** and no register change.

## Known limits (stated in advance)

As in C7:
- semantic-only evidence is not lifted (RRF's single-list penalty);
- discovery losses remain;
- newer-first under unspecified intent is not addressed;
- the gain needs the optional local model.
