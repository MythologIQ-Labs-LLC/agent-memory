# Memory Evaluation Subsystem

Status: implemented common result contract (#524 slices A–D) plus the benchmark integration contract (#652); blocked-input honesty from #529  
Canonical contributor entry point: [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md)

## Purpose

Agent Memory has three deliberately separate repository responsibilities:

```text
Agent Memory
├── Memory Runtime
│   └── remember / recall / govern / correct / forget / recover
├── Memory Evaluation
│   └── benchmark integrations / common evidence / validation / comparison / evaluator integrity
└── Agent Memory Gauntlet
    └── system adapters / capability negotiation / qualification profiles / orchestration
```

The evaluation subsystem exists so Agent Memory, simple baselines, and external memory systems can be measured under one reconstructable evidence shape. It is not another memory runtime and it does not acquire memory authority.

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

## Two contracts, two schemas

| Contract | Schema | Describes | Loader |
| --- | --- | --- | --- |
| benchmark **integration** | `schemas/memory-benchmark-integration.schema.json` | how a benchmark enters the laboratory: identity, rights, input rules, native protocol, system invocation surface, mappings, integrity controls, Gauntlet relationship | `agentmem_ref.evaluation.benchmark_integration` |
| benchmark **run** | `schemas/memory-benchmark-run.schema.json` | one executed (or blocked / not-run) result for one system | `agentmem_ref.evaluation.contract` |

This document covers the run contract. The integration contract, the descriptor-backed registry, and the contributor paths are specified in [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md).

## Common run contract

The reusable Python utilities live in:

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

Where available the benchmark identity also records dataset identity/revision and a task profile. An adapter must not invent a dataset revision or digest when the upstream source does not expose one. The benchmark integration descriptor records *how* each benchmark computes these identities (`input_contract.input_digest_rule`, `selection.identity_rule`), so a result can be checked against the rule its benchmark declares.

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

The common vocabulary is:

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

A measured numeric zero is therefore not interchangeable with a missing measurement. The full decision tree, including `unsupported` and `failed` at the Gauntlet boundary, is in [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md#6-state-decision-tree).

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

## Normalization is mapping, never invention

A benchmark integration descriptor lists every mapping into a common dimension together with the native evidence path that supplies it, and lists every unmapped dimension with a reason. `mapped_metric_observations()` turns a mapping whose native evidence is absent into a `not_measured` observation; it never produces a value, and never a zero. Normalizers for the repository-owned integrations (`normalize.py` for LongMemEval and AgentMemBench, the golden runner for `golden-keyed-retrieval-v1`) keep the whole native report under `native_results`; a test asserts the native report is byte-for-byte unchanged by normalization.

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

## Native benchmark integrations

Each integration remains responsible for its actual benchmark semantics:

- SWE-ContextBench owns its gold-edge and ranking protocol (external evidence blocked, #467).
- LongMemEval owns its session/turn recall and nDCG semantics and its upstream exclusions.
- AgentMemBench / MemDialogue owns its operational phases and upstream adapter protocol.
- The golden keyed-retrieval integration owns a tiny exact-id protocol and exists to prove the contributor contract.
- Gauntlet-native suites (governance, durability) own their claim-driven case semantics and are never external evidence.

The common contract gives those results one evidence envelope. It does not rewrite their scoring rules, and the descriptor for each one records which runner, invocation surface, provider requirements, and evidence class apply.

## Evaluator integrity

Evaluator integrity stays separate from efficacy.

A mutation probe may prove that removing a relevant item harms recall or that injecting noise harms precision. That establishes sensitivity of the evaluator to that controlled defect.

It does not establish that:

- Agent Memory has high retrieval quality;
- a third-party memory system is safe;
- the benchmark is externally comparable;
- a memory result has authority.

The common vocabulary therefore gives `evaluator_integrity` its own dimension rather than folding mutation-probe results into retrieval. Each integration descriptor declares its negative controls and the runner that executes them (`reference/run_benchmark_integrity_mutants.py` for the external profiles, `reference/run_golden_benchmark_integrity.py` for the golden path). A control that cannot fail is not a control.

## Runtime independence

The evaluation package is not imported by ordinary Agent Memory runtime startup.

Benchmark adapters may invoke the public `AgentMemory` facade when Agent Memory is the system under test. The reverse dependency is forbidden: Agent Memory runtime behavior must not depend on benchmark adapters, benchmark datasets, or benchmark scores.

```text
Memory Evaluation -> may observe Agent Memory
Agent Memory Runtime -> does not depend on Memory Evaluation
```

The Runtime Baseline v1 source boundary (`reports/runtime/baseline-v1-source-boundary.json`) encodes the same rule for CI: the evaluation package is the only subtree excluded from frozen-runtime equivalence checks, and evaluation changes must keep `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` green.

## Current state against #524

Implemented and tested on `main`:

1. the versioned run contract with explicit missingness and no aggregate score;
2. validation, canonical persistence, digesting, and fail-closed comparison;
3. normalization of LongMemEval and AgentMemBench into the common contract with native results preserved;
4. the separate `evaluator_integrity` dimension and the integrity-control runners;
5. descriptor-backed profile discovery and the `benchmark` CLI (`list`, `inspect`, `validate-integration`, `validate`, `compare`);
6. the system-adapter contract and the Gauntlet orchestration built on it;
7. the benchmark integration contract that binds the two.

Not implemented, by design: a universal execution command across heterogeneous benchmarks. Benchmark-native runners keep their own protocols; the descriptor says which one applies.

The goal is a reusable memory-evaluation lab, not a leaderboard whose most important feature is that its author happens to win it.
