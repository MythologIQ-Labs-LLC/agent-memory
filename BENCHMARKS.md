# Agent Memory benchmarks

This repository keeps benchmark code, fixtures, and evidence boundaries alongside the implementation so results can be reproduced against exact revisions.

## SWE-ContextBench Lite comparison harness

Start here: [`docs/50-swe-contextbench-comparison-harness.md`](docs/50-swe-contextbench-comparison-harness.md)

After installing the reference package dependencies:

```bash
python -m pip install -e .
python reference/run_swe_context_bench_harness.py --output artifacts/swe-contextbench-smoke.json
```

The default run is credential-free and uses the repository's synthetic smoke fixture. It compares:

- no memory;
- deterministic lexical overlap;
- governed Agent Memory retrieval.

It is deliberately labeled **non-comparable** to the external SWE-ContextBench Lite result. The external 99-query / 100-gold-edge evidence lane remains governed by issue #467 and requires the exact frozen input/provenance contract before a comparable result can be claimed.

The harness also accepts frozen schema `1.0.0` and batched/multi-gold schema `2.0.0` manifests. See the full guide for invocation, report fields, comparability rules, and backend-extension boundaries.

## Evidence rule

Benchmark dimensions remain separate. Retrieval quality, performance, consistency, governance, recovery, and downstream task outcomes must not be collapsed into one universal memory-health score.

```text
benchmark score != authority
retrieval quality != production readiness
harness validation != external benchmark comparability
```
