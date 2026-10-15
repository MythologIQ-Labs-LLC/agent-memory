# Hindsight OSS chunk-only (no LLM) on AMB PrecisionMemBench single-turn, all 77 cases: 9/77

**Status: candidate.** This is self-run and unreviewed. It is not accepted, not an official AMB
entry, and not Hindsight's LLM product mode. It was preregistered before execution
(`PREREGISTRATION.md`, pushed in `89931a8` before the run).

## Result (AMB native scoring, run 1)

| System (same harness, protocol A, no LLM) | Correct | Active | Mean precision | Mean recall | Mean returned | Paired vs Agent Memory (W/L, exact McNemar) |
|---|---:|---:|---:|---:|---:|---|
| Agent Memory (reviewed) | **15/77** | 4/43 | 0.181 | 0.954 | 8.9 | — |
| Mem0 OSS explicit | 10/77 | 0/43 | 0.105 | 1.000 | 8.0 | +1 / −6, p = 0.125 |
| **Hindsight 0.10.2 chunk-only (this run)** | **9/77** | **0/43** | **0.054** | **0.985** | **18.1** | **+0 / −6, p = 0.031** |
| MemPalace 3.11.0 | 9/77 | 0/43 | 0.056 | 1.000 | 18.1 | +0 / −6, p = 0.031 |
| BM25 (AMB built-in) | 8/77 | 0/43 | 0.054 | 0.965 | 18.3 | +0 / −7, p = 0.016 |

Hindsight returns almost the full budget for every case. 68 of its 68 failures include an
unexpected belief. Its per-category passes are identical to MemPalace's:
- Budget eviction and capacity: 3/5
- Design boundary cases: 2/6
- Structural singletons
- Alias resolution and Fuzzy matching: 0

Details are in `paired-vs-cohort.json`. Hindsight's published 66/77 on this dataset used LLM
ingestion and AMB's structured `retrieval_filter`. Neither is used here, so the two numbers
measure different protocols.

## Repeatability: outcomes are stable, but order varies within one host

Run 2 was a fresh full rerun on the same host, with new banks. Everything scored is identical to
run 1: correct 9/77, precision 0.0544, recall 0.985, 0 active passes, and per-case `correct` on
all 77 cases.

The retrieval order is not identical: 27 of 77 cases return the same set in a different order
(`rep1-vs-rep2.outcome-stability.json`; `scripts/compare_amb_runs.py` reports 78 field
differences, all in order-dependent text). In one case the set itself changed:
`budget-ceiling-evicts-relevant-beliefs`, with a budget of 2, swapped one item at the budget
edge. That case failed in both runs.

So Hindsight's ordering variation also occurs on a single host, not only across hosts as in
the LongMemEval repeat. At tight budgets it can change set membership. A same-host determinism
probe that separates ingest-time from query-time variation is prepared
(`reference/hindsight_determinism_probe.py`).

## Identity

| Item | Value |
|---|---|
| Harness | AMB `03c1d0f`; pinned fixtures; guard and wrapper unchanged from `1df28f8`; launched with `AWS_*` unset |
| Product | Hindsight 0.10.2 `5fc4ce2`, `llm_provider=none`, chunks bank (qualified per bank), e5-small ONNX `03415a4` |
| Process layout | In its pinned interpreter, behind `reference/hindsight_amb_worker.py`, as an unprivileged user, with a separate pg0 home |
| Bridge | `reference/amb_hindsight_bridge.py` 0.1.0-candidate |
| Run cost | Wall time 91 s and 79 s; peak RSS 2.3 GiB for the whole CLI plus the worker |
