# Hindsight 0.10.2 chunk-only (no LLM): full 500-question LongMemEval-S, both planes (#640, #810)

**Status: candidate.** This is a self-run and has not been independently reviewed or accepted.
It was preregistered before execution (`PREREGISTRATION.md`, `preregistration.json` at
13:15:24Z; the file is byte-identical after the run).

This measures **Hindsight's no-LLM chunk retrieval**, not its LLM fact-extraction or observation
product modes. Configuration:
- `llm_provider=none` and a chunks bank;
- semantic search with local ONNX e5-small, fused by RRF with text search;
- observations, temporal, graph and reranking all off;
- recall `mid`, `max_tokens` 65,536.

## Results

The evaluator's native summaries are `{session,turn}.hindsight_chunks_onnx.summary.json`. All 500
questions completed on both planes, with 419 scored (30 abstention and 51 no-user-target
exclusions). There were 0 runtime failures, 0 ingestion failures and 0 out-of-corpus results.

| Plane | recall_all@5 | recall_all@10 | recall_all@50 | ndcg_any@10 |
|---|---:|---:|---:|---:|
| session | 0.888 | 0.964 | 1.000 | 0.906 |
| turn | 0.706 | 0.835 | 0.957 | 0.759 |

### Paired against the frozen Agent Memory baseline

The baseline is the repeated full-500 controls, which are row-identical to the originals. Both
systems are compared on the same 419 questions. Source: `paired-vs-controls.{plane}.json`.

| Plane, metric | Agent Memory | Hindsight | W / L / T | Exact McNemar | Δ mean, 95% paired bootstrap |
|---|---:|---:|---|---:|---|
| session @5 | 0.823 | 0.888 | 34 / 7 / 378 | 2.5e-5 | +0.064 [+0.036, +0.093] |
| session @10 | 0.893 | 0.964 | 32 / 2 / 385 | 7e-8 | +0.072 [+0.045, +0.098] |
| turn @5 | 0.601 | 0.706 | 57 / 13 / 349 | 1e-7 | +0.105 [+0.067, +0.143] |
| turn @10 | 0.723 | 0.835 | 51 / 4 / 364 | <1e-8 | +0.112 [+0.081, +0.146] |

recall_all@k for the two planes, per question type:

| Question type (n) | Session AM | Session Hindsight | Turn AM | Turn Hindsight |
|---|---:|---:|---:|---:|
| multi-session (121) | 0.810 | 0.942 | 0.537 | 0.711 |
| temporal-reasoning (127) | 0.890 | 0.969 | 0.740 | 0.843 |
| knowledge-update (72) | 0.986 | 1.000 | 0.931 | 1.000 |
| single-session-preference (30) | 0.767 | 0.867 | 0.400 | 0.533 |
| single-session-user (64) | 1.000 | 1.000 | 0.953 | 1.000 |
| single-session-assistant (5) | 1.000 | 1.000 | 0.800 | 1.000 |

The paired script's aggregates match the evaluator's native summaries exactly on both planes.

## Repeatability and ordering

- **Cross-host repeat:** the 50 subset questions on a second host
  (`subset50-vs-full500.session.json`) returned the same sets 50/50 and the same recall@k, but
  the order was permuted on 40/50 and nDCG changed on 1.
- **Cause:** the BM25 arm's score ties have no tie-break, so a fresh ingestion reorders them.
  Recall is unaffected (`determinism-probe/`).
- **Effect on these numbers:** recall_all@k is stable. nDCG is a single-run value and may move by
  small amounts.

## Execution

`hindsight-500.exec.json` covers both planes:

| Item | Value |
|---|---|
| Exit status | 0 |
| Wall time | 25,468 s |
| Peak RSS | 2,915 MiB |
| Run user | `benchrun` |
| Environment | allowlisted, no credentials |
| Host | 4 vCPU, shared with other runs (timings are indicative) |

Finalisation is recorded in `finalize.exec.json`. The #808 v1 manifests are
`{plane}.hindsight_chunks_onnx.manifest.json`. The environment freeze is
`../subset50/hindsight-venv-freeze.txt`, and the bridge is unchanged from the subset run (blob
`a14e2eb9`).
