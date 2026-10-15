# Hindsight 0.10.2 (chunks, no LLM): LongMemEval-S subset50, independent repetition 2

This is candidate evidence. It is not reviewed or accepted.

**Run 1** is on `claude/817-jev-mem-execution-no-ci` at `05f5a38`, as `reports/benchmarks/runs/640-hindsight/subset50/hindsight-50.json`. It ran from 06:00 UTC on 2026-10-15. This **repetition 2** ran from 18:27 UTC with:

- the identical argv
- the identical bridge and runner (the last change to either was commit `e4e2a4be`, 24 s before run 1 started, with none since)
- the identical Hindsight environment (the `uv pip freeze` output is byte-identical)
- the same pinned server, ONNX model and bank configuration
- the same input `d6f21ea9…` and selection `5266568e…7339`

The host was more heavily shared during this run. The exec record shows wall time and RSS.

| Plane, metric (43 scored) | Rep 1 | Rep 2 | Questions whose verdict changed |
| --- | ---: | ---: | ---: |
| Session recall_all@5 | 0.930233 | 0.930233 | 0 |
| Session recall_all@10 | 0.953488 | 0.953488 | 0 |
| Session recall_all@50 | | | 0 |
| Turn recall_all@5 | 0.767442 | 0.767442 | 0 |
| Turn recall_all@10 | 0.837209 | 0.837209 | 0 |
| Turn recall_all@50 | 0.976744 | 0.976744 | 0 |
| Failures (runtime, ingestion, out-of-corpus) | 0 | 0 | |

**Not bit-identical.** The order of tied results differs:

- **Session:** 46 of 50 questions have some order difference, but the returned sets are identical.
- **Turn:** all 50 questions have some order difference, and 15 have a different returned set beyond the recall depth.
- **nDCG:** shifts by at most 0.005 (session ndcg_any@10 is 0.929 vs 0.926).

The same tie-order behaviour appears in the AMB repetitions. Every recall verdict reproduces exactly.
