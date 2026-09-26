# Memory Evaluation Scorecards

Status: #534 under #524 / #537.

## What is generated

`scripts/build_benchmark_scorecards.py` reads the committed benchmark-native evidence and produces:

| output | content |
| --- | --- |
| `reports/benchmarks/normalized/*.json` | one common run manifest (`schemas/memory-benchmark-run.schema.json`) per system and task profile |
| `reports/benchmarks/scorecards/scorecards.json` | portfolio status plus side-by-side benchmark scorecards (machine-readable) |
| `reports/benchmarks/scorecards/scorecards.md` | the same, as Markdown tables for docs and issue comments |

Regenerate with:

```bash
python scripts/build_benchmark_scorecards.py
python scripts/build_benchmark_scorecards.py --check   # CI/test: fail if committed outputs are stale
```

The output is byte-deterministic. A test runs `--check`, so committed scorecards cannot drift from the evidence they are derived from. The script reads frozen reports (such as the `f73b872` LongMemEval_S evidence) and never rewrites them.

## Normalization rules (`agentmem_ref/evaluation/normalize.py`)

- LongMemEval produces one manifest per (plane, backend), because session and turn retrieval are different task profiles. AgentMemBench produces one manifest per backend.
- Benchmark-native results are preserved verbatim under `native_results`.
- Only observations with stable meaning inside one frozen input are mapped into dimensions:
  - **retrieval**: headline recall/nDCG, and exact-source recall;
  - **currentness**: knowledge-update metrics, `latest_gold_ranked_first`, and new-fact/staleness rates;
  - **governance**: admission and refusal counts, leak rate, audited deletion;
  - **efficiency**: wall, ingest, recall, and latency figures, scale, concurrency, and peak RSS where attributable;
  - **reproducibility**: input binding, clean tree, and execution failure counts.
- Anything not measured is declared, never zeroed. Examples:
  - `reasoning` is `not_measured`, because no QA or LLM judge ran;
  - `evaluator_integrity` is `not_measured` per run, because the #518 probes run separately;
  - baselines have `governance: not_applicable`;
  - LongMemEval peak RSS is `not_measured` per backend, because it was measured for the whole process;
  - `store_size_bytes` is `not_measured`.

## Scorecard rules (`agentmem_ref/evaluation/scorecard.py`)

- Systems share a card only when their comparison identity matches exactly: benchmark, source revision, dataset revision, input SHA-256, task profile, selection, and sample count.
- Δ columns come from the fail-closed `compare_runs` contract, against the lexical baseline where present. A Δ applies one metric's own direction. It is not a verdict on the system.
- Missing metrics render as `absent`, and unmeasured ones by their state. Comparisons that cannot produce a delta show their `comparison_state`.
- The portfolio card lists every registered profile with per-variant `complete / partial / blocked / not_run` status, systems run, dimensions measured and not measured, and linked product findings.
- There is no aggregate or weighted score (`aggregate_score: not_defined`), and `authority_effect` is always `none`.
