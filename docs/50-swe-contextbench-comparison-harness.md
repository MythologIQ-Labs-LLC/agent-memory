# SWE-ContextBench Lite comparison harness

Issue: #492  
External-evidence lane: #467  
Existing Agent Memory runners: `reference/run_swe_context_bench.py`, `reference/run_swe_context_bench_real_100.py`

## Purpose

Agent Memory includes a repository-native comparison harness for SWE-ContextBench Lite retrieval/context-selection experiments.

The harness is deliberately smaller than a coding-agent evaluation system. It answers:

> Given the same frozen prior experiences and related-task queries, what prior experience does each memory/retrieval backend surface?

The initial comparison arms are:

| Backend | Purpose | Network/API required |
|---|---|---:|
| `no_memory` | Zero-memory retrieval floor | No |
| `lexical_overlap` | Deterministic simple retrieval baseline | No |
| `agent_memory` | Existing governed Agent Memory SWE-ContextBench runner | No |

The Agent Memory arm delegates to the existing benchmark runner. The harness does not implement a second Agent Memory retrieval path.

## Quick start

Requirements:

- Python 3.11+
- a local clone of this repository

Install the reference package dependencies:

```bash
python -m pip install -e .
```

Run the credential-free repository smoke fixture:

```bash
python reference/run_swe_context_bench_harness.py --output artifacts/swe-contextbench-smoke.json
```

The script resolves the current Git revision automatically when executed from a normal clone. To bind another revision explicitly:

```bash
python reference/run_swe_context_bench_harness.py \
  --agent-memory-revision <commit-sha> \
  --output artifacts/swe-contextbench-smoke.json
```

The default fixture is intentionally tiny and synthetic. It proves that the harness, scoring, baseline comparison, and Agent Memory integration execute. It is **not** a publishable SWE-ContextBench result.

## What the report contains

One JSON report contains separate records for all three arms:

```text
backends.no_memory
backends.lexical_overlap
backends.agent_memory
```

Quality is reported with the same core retrieval dimensions where applicable:

- candidate recall;
- final admitted recall;
- final admitted precision;
- final admitted F1;
- false admissions;
- false refusals;
- nDCG@1;
- nDCG@3.

The report also binds:

- Agent Memory revision;
- benchmark manifest digest;
- runtime-configuration digest;
- evidence-profile digest;
- every experience/query input digest;
- declared upstream repository/revision;
- corpus class;
- baseline configuration;
- Agent Memory governance/performance/consistency evidence;
- external-comparability status.

No aggregate memory-health score is defined.

## Baseline semantics

### No memory

`no_memory` returns no prior experience. It is a retrieval floor, not a model-without-memory end-to-end coding score.

### Lexical overlap

`lexical_overlap` is intentionally boring and deterministic:

1. project each prior experience using the same public/redacted projection used by the Agent Memory runner;
2. lowercase and tokenize alphanumeric/underscore terms longer than one character;
3. compare only experiences visible to the query's same-repository corpus/batch;
4. rank by token-overlap count;
5. break ties by Jaccard similarity and then stable instance ID;
6. return the top `K` results.

Default `K` is `3`. Override it with:

```bash
python reference/run_swe_context_bench_harness.py --lexical-top-k 1
```

This baseline is not intended to be sophisticated. Its job is to establish whether Agent Memory earns complexity over a transparent retrieval floor.

## Using a frozen external manifest

The harness supports both existing Agent Memory SWE-ContextBench manifest contracts:

### Schema `1.0.0`

Single-gold ordinary/synthetic manifest used by `run_swe_context_bench.py`.

```bash
python reference/run_swe_context_bench_harness.py \
  --manifest /path/to/manifest.json \
  --benchmark-root /path/to/frozen/corpus \
  --output artifacts/swe-contextbench-comparison.json
```

### Schema `2.0.0`

Batched/multi-gold manifest used by `run_swe_context_bench_real_100.py`, including the 99-query / 100-gold-edge public-Lite shape.

The lexical baseline obeys the manifest's frozen batch visibility. The Agent Memory arm delegates to the real-100 wrapper, including its multi-gold scoring and provenance/comparability checks.

```bash
python reference/run_swe_context_bench_harness.py \
  --manifest /path/to/real-100-manifest.json \
  --benchmark-root /path/to/frozen/corpus \
  --output artifacts/swe-contextbench-real-comparison.json
```

## External-comparability rule

A successful local run does not automatically become an official or paper-comparable result.

The repository currently distinguishes:

```text
harness executes correctly
!=
protocol-compatible shape
!=
exact externally comparable frozen corpus/provenance
```

For the external 99-query / 100-edge lane, #467 remains controlling. A report is externally comparable only when the canonical Agent Memory runner reports that the exact required frozen input provenance and selection provenance are bound.

The vendored synthetic fixture always reports a non-comparable status.

Do not reconstruct unavailable external experience projections from weaker public fields and then label the result comparable. Changing the corpus projection changes the experiment.

## Adding another comparison backend

A new benchmark backend should be added only when it answers a distinct evaluation question.

The harness-level contract is intentionally narrow:

```text
frozen visible prior experiences
        + query
        -> ordered candidate/retrieved experience IDs
        -> common scoring
```

A comparison backend does **not** gain Agent Memory authority merely by being present in the harness.

Preserve:

```text
benchmark score != truth
retrieval score != recall permission
backend identity != canonical Agent Memory semantics
```

Agent Memory governance evidence must continue to come from the canonical Agent Memory runner rather than being simulated by a baseline adapter.

Useful future arms could include a vector-only baseline, BM25, an optional hosted decision/retrieval provider, or an architecture-specific comparator. Each should expose its configuration and dependency/egress posture explicitly.

## What this harness does not measure

This slice does not execute a coding agent inside SWE task containers. It therefore does not measure:

- patch correctness;
- SWE-bench task resolution;
- answer-generation quality;
- end-to-end coding-agent token cost;
- whether retrieved context actually improves a generated patch.

Those require a separate solver/execution layer with the coding model, prompts, tools, budgets, container image, timeout, and evaluator held constant while the memory backend changes.

That later experiment can consume the retrieval outputs from this harness, but should not be conflated with them.

## Reproducibility checklist

Before comparing two reports, verify:

1. identical benchmark manifest digest;
2. identical input file digests;
3. identical corpus class and upstream revision;
4. identical baseline/backend settings;
5. exact Agent Memory revisions are recorded;
6. the same Agent Memory runtime configuration/evidence profile is used where required;
7. external-comparability status matches;
8. quality, performance, consistency, and governance remain separate dimensions.

A higher retrieval score is evidence. It is not permission to weaken scope, currentness, provenance, deletion, or PAMA boundaries.
