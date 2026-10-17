# LongMemEval-S parity (P4): met

**Setup.**
- Unchanged runner `reference/run_longmemeval.py` on each head.
- `--corpus-class external_frozen --subset-size 40` (default subset seed), `--granularity turn --backend agent_memory --agent-memory-semantic-retrieval required`.
- Input `longmemeval_s_cleaned.json`, sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.

**Result.**
- The whole `planes` object of C4+sem `bc2be631` and C9-D+sem `ca590e8` is identical once timing fields are removed. That covers every per-question ranked list, the metrics, the governance counts and the semantic-route summary.
- `refused_candidate_count_total` = 0 in both runs, which is the structural reason: the runner only `remember`s unique refs, so nothing is refusable.

| Arm | Evaluated | recall_all@5 | recall_all@10 | recall_all@50 |
|---|---:|---:|---:|---:|
| C4+sem | 33 | 0.6667 | 0.7879 | 0.8788 |
| C9-D+sem | 33 | 0.6667 | 0.7879 | 0.8788 |

The full 500-question run and the session plane were not run (local cost). The identity argument covers them by construction. Reports are in `lme/`.
