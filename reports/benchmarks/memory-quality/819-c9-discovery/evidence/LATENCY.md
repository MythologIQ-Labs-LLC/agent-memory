# C9-D cost (P6)

**Setup.**
- Merged longitudinal store: 180 facts in the query scope's tenant (90 superseded, 12 forgotten), plus 18 in another scope.
- 30 queries, semantic route required, `relevance_sufficient`, budget 10.
- 3 rounds, alternating C4+sem `bc2be631` and C9-D+sem `ca590e8` sequentially in the same process conditions.
- Elapsed time per query covers `AgentMemory.open` plus `recall`, with the verified provider loaded once per process.
- Two LongMemEval processes were running on the other 2 of 4 cores, so absolute values are noisy. The comparison is paired by round.

| Arm | n | p50 ms | p95 ms | Per-round p50 |
|---|---:|---:|---:|---|
| C4+sem | 90 | 75.7 | 170.1 | 76.5, 71.3, 97.8 |
| C9-D+sem | 90 | 71.3 | 124.5 | 68.0, 69.5, 75.9 |

**Result.** P6 (≤ C4+sem + 10 ms) is met.

**Why.** The added refusal check is a few set and dict reads per fact. It removes refused facts before their derived vector is looked up and before they are scored. Per-query JSON is in `latency/`.
