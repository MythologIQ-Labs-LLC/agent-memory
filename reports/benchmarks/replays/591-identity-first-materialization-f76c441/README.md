# #591 identity-first candidate materialization: evidence at `f76c441`

Candidate runtime: `f76c441608e4ee189f410aaf6d7b29d3a0a3d902`, clean tree. The regression baseline is post-#550 `main` `273722e` (its runtime equals the accepted #550 evidence `eb44c34`). Pre-#550 `550abf0` appears for context only. ADR-039 remains **Proposed**. This is performance and equivalence evidence, not a semantic change.

## Root cause

SQLite lexical discovery (`SQLiteTemporalGraph.search`) built a full `Fact` for **every tenant fact** on every search, decoding `episode_uuids_json` and `attributes_json`, and only then applied the caller's #548 `eligible(fact)` predicate. That predicate reads only the fact's `uuid` and `group_id`; scope comes from the adapter's canonical `_fact_scope`. #550 made every decoded `attributes_json` non-trivial, which exposed the waste.

## Change

* `GovernedMemoryAdapter.domain_eligible_identity(uuid, group_id, context)` is the same #548 prefilter on a fact identity. `_domain_eligibility_refusal(fact)` now delegates to `_domain_identity_refusal(uuid, group_id)`, so the two cannot diverge. No authority state is copied anywhere.
* The SQLite substrate declares `supports_identity_prefilter`. Given the identity predicate, it:
  1. projects only `uuid, group_id, fact_text`;
  2. applies the identity predicate and the unchanged lexical overlap;
  3. fully materializes only the survivors, in batches;
  4. re-applies `eligible(fact)` to each;
  5. sorts exactly as before (score desc, uuid).
* There is no new table, index, cache, schema change, digest change, or attestation change. #550 write semantics stay with the fact.

## Materialization (`materialization-counts-agentmembench-300-searches.json`, `materialization_counts.py`)

AgentMemBench retrieval workload, 1,000 facts across 100 user scopes, 300 searches:

| per search | `main` `273722e` | #591 `f76c441` |
| --- | ---: | ---: |
| `_fact_from_row` (full Fact materialization) | 1,020.0 | **30.0** |
| JSON `raw_decode` calls | 2,041.0 | **60.9** |
| `raw_decode` CPU, 300 searches | 1.576 s | **0.050 s** |
| eligible candidates (report governance: 9,937 / 1,000 recalls) | 9.94 | 9.94 |

The remaining 30 materializations per search are about 10 candidates, each materialized three times: discovery, admission, and ranking lookup. That multiplier is pre-existing and outside this slice.

## Idle paired timing (`timing/`, alternated, clean trees)

| AgentMemBench, median | `550abf0` (pre-#550) | `273722e` (`main`) | `f76c441` (#591) | vs `main` |
| --- | ---: | ---: | ---: | ---: |
| total wall | 47.81 s | 54.62 s | **38.63 s** | -29% |
| retrieval read p50 | 14.87 ms | 17.91 ms | **7.68 ms** | -57% |
| retrieval read p95 | 25.78 ms | 31.37 ms | **11.87 ms** | -62% |
| retrieval write p50 | 4.99 ms | 5.56 ms | 5.51 ms | 0% |
| retrieval phase wall | 21.48 s | 25.58 s | 14.09 s | -45% |

The #550 regression is not only recovered: the candidate read path is faster than pre-#550, because the eager materialization predated #550. Write cost is unchanged. The #550 interpretation cost on writes remains, by design.

## Semantic equivalence

* **AgentMemBench** (verified sha256 `33632710…ca2a6` @ `186c9a54`), seeds 0 and 1: `compare-agentmembench-f76c441-seed{0,1}-vs-{eb44c34,8bd6c91}.json` are all **IDENTICAL**. There are 0 non-timing differences in every dimension and governance tally, including candidate, admitted, and refusal counts. The per-search traces (`agentmembench-traces/`) match both the post-#550 and the canonical 3.0.1 traces: all 2,051 ordered results and every BM25 score bit.
* **LongMemEval_S** (verified sha256 `d6f21ea9…a442` @ `98d7416c`): `compare-lme-s-f76c441-vs-{eb44c34,8bd6c91}.json` are both **IDENTICAL**. All 53 checks pass; 3,000/3,000 rows are identical with 0 rank differences. Currentness, governance, and failures are unchanged. Wall time is 976 s against 997 s (#550): each question is a single-scope store, so there is little to skip.
* **LongMemEval_M:** not required. No drift of any kind occurred, and the change's effect scales with tenant-versus-scope fan-out, which AgentMemBench exercises directly.
