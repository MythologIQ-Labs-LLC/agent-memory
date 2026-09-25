# Memory Evaluation Subsystem

Status: common-contract implementation under #524 / #525, with blocked-input honesty clarified by #529.

## Purpose

Agent Memory now has two deliberately separate repository responsibilities:

```text
Agent Memory
├── Memory Runtime
│   └── remember / retrieve / govern / correct / forget / recover
└── Memory Evaluation
    └── benchmark adapters / system adapters / evidence / comparison / evaluator integrity
```

The evaluation subsystem exists so Agent Memory, simple baselines, and future external memory systems can be measured under one reconstructable evidence shape. It is not another memory runtime and it does not acquire memory authority.

```text
benchmark score != truth
benchmark score != recall admission
benchmark score != mutation authority
evaluator-integrity pass != memory efficacy
```

Every common result therefore carries:

```text
authority_effect: none
```

## Common run contract

The canonical schema is:

```text
schemas/memory-benchmark-run.schema.json
```

The reusable Python utilities are:

```text
reference/agentmem_ref/evaluation/
```

A benchmark run binds four categories of evidence.

### Benchmark identity

At minimum:

```text
benchmark.id
benchmark.source_revision
benchmark.input_sha256
```

For an executed `complete` or `partial` run, `benchmark.input_sha256` must be the exact 64-hex digest of the frozen input.

For a `blocked` or `not_run` record, `benchmark.input_sha256` may be `null` when the blocker is precisely that the input has not been obtained or materialized. A null value means **input identity unavailable**. It is not a wildcard, a placeholder digest, or evidence of comparability.

```text
complete / partial -> exact input SHA-256 required
blocked / not_run  -> input SHA-256 may be null
null input digest  -> comparison forbidden
```

Where available the benchmark identity also records dataset identity/revision and a task profile. An adapter must not invent a dataset revision or digest when the upstream source does not expose one.

### System identity

At minimum:

```text
system.id
system.kind
system.revision
```

Configuration digest and adapter identity/revision are recorded when available. `system.kind` is intentionally broad enough to represent no-memory, lexical, vector, Agent Memory, external memory, and other bounded systems without promoting any one implementation into the benchmark ontology.

### Execution identity

Comparison binds:

```text
execution.selection_id
execution.selection_method
execution.sample_count
```

Environment, elapsed time, and seed may be recorded when actually measured. Missing execution evidence must not be fabricated merely to make a result look complete.

### Evidence dimensions

The first common vocabulary is:

```text
retrieval
currentness
reasoning
governance
efficiency
evaluator_integrity
reproducibility
```

These are reporting dimensions, not components of an aggregate score. Every run declares the status of every dimension explicitly:

```text
measured
partial
not_measured
not_applicable
blocked
```

Metrics inside a dimension separately declare:

```text
measured
not_measured
not_applicable
blocked
```

A measured numeric zero is therefore not interchangeable with a missing measurement.

## Metric semantics

A common metric observation may carry:

```text
metric_id
state
value               # measured only
direction           # higher_better / lower_better / zero_target / descriptive
denominator
unit
population
note
```

The contract does not claim that two metrics are semantically identical merely because their names resemble each other. Benchmark-native outputs are retained under `native_results` as opaque JSON so an adapter can preserve upstream evidence without laundering it into a supposedly universal metric.

For example, an upstream model-judged QA score can remain a native result even if the common `reasoning` dimension is not populated because the adapter cannot establish a stable cross-system mapping.

## Fail-closed comparison

`compare_runs()` accepts only executed `complete` or `partial` runs with exact frozen input identity. `blocked` and `not_run` records are valuable evidence about why a result does not exist, but they are never comparison evidence.

For executed runs, the frozen comparison identity includes:

```text
benchmark id
benchmark source revision
dataset id/revision when present
exact input SHA-256
task profile when present
selection id
selection method
sample count
```

This prevents the common failure mode where two result files both contain `recall@10` but were computed over different datasets or denominators and are nevertheless presented as a delta.

Even after run-level compatibility is established, a metric receives a numeric delta only when both observations are measured and these semantics match:

```text
direction
unit
denominator
population
```

Otherwise the comparison records why the metric-level delta was refused.

There is intentionally no `overall_score` in the comparison result.

## Native benchmark adapters

Existing and future adapters remain responsible for their actual benchmark semantics.

For example:

- SWE-ContextBench owns its gold-edge and ranking protocol.
- LongMemEval owns its session/turn recall and nDCG semantics.
- A currentness/forgetting benchmark may own stale-memory and update semantics.
- An agent task benchmark may own end-task success.

The common contract gives those results one evidence envelope. It does not rewrite their scoring rules.

## Evaluator integrity

Evaluator integrity stays separate from efficacy.

A mutation probe may prove that removing a relevant item harms recall or that injecting noise harms precision. That establishes sensitivity of the evaluator to that controlled defect.

It does not establish that:

- Agent Memory has high retrieval quality;
- a third-party memory system is safe;
- the benchmark is externally comparable;
- a memory result has authority.

The current common vocabulary therefore gives `evaluator_integrity` its own dimension rather than folding mutation-probe results into retrieval.

## Runtime independence

The evaluation package is not imported by ordinary Agent Memory runtime startup.

Benchmark adapters may invoke the public `AgentMemory` facade when Agent Memory is the system under test. The reverse dependency is forbidden: Agent Memory runtime behavior must not depend on benchmark adapters, benchmark datasets, or benchmark scores.

```text
Memory Evaluation -> may observe Agent Memory
Agent Memory Runtime -> does not depend on Memory Evaluation
```

## Intended next steps

Under #524, later slices should:

1. normalize at least two existing benchmark adapters into this common evidence contract;
2. add profile discovery and lightweight CLI validation/comparison;
3. define a minimal system-adapter contract for no-memory, simple retrieval, Agent Memory, and external systems;
4. expand the benchmark portfolio only where a benchmark adds distinct pressure such as currentness/forgetting, implicit recall, dynamic state, or real agent task completion;
5. keep benchmark-native results, common dimensions, governance, performance, and evaluator-integrity evidence separate.

The goal is a reusable memory-evaluation lab, not a leaderboard whose most important feature is that its author happens to win it.
