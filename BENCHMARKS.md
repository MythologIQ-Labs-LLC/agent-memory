# Agent Memory Benchmarks

Benchmarking is now a first-class repository function, not an auxiliary test harness.

Agent Memory keeps benchmark adapters, evaluator-integrity probes, frozen run evidence, normalized manifests, scorecards, and remediation links alongside the runtime so behavior can be reproduced against exact revisions and compared before and after product changes.

The governing repository relationship is documented in [`docs/REPOSITORY_OPERATING_MODEL.md`](docs/REPOSITORY_OPERATING_MODEL.md).

## Why benchmarks live here

The benchmark program has three jobs:

1. **Measure the runtime honestly.** External workloads should expose behavior the repository's own fixtures may have missed.
2. **Falsify architecture assumptions.** Repeated benchmark failures may reveal an implementation defect, a product-contract gap, or a genuine architecture gap.
3. **Prove remediation.** A benchmark-discovered defect should be replayed against the same frozen input after repair when the workload can validly exercise the fix.

The goal is not to optimize one universal score.

```text
benchmark score != authority
benchmark score != truth
retrieval quality != answer-generation quality
retrieval quality != production readiness
harness validation != external benchmark comparability
```

## Current portfolio

### LongMemEval

Profile documentation: [`docs/profiles/longmemeval-retrieval-currentness-profile.md`](docs/profiles/longmemeval-retrieval-currentness-profile.md)

Current status:

- **LongMemEval_S full:** complete frozen external run;
- **LongMemEval_M:** held. It is not run merely because a remediation slice landed. The post-prefilter scale probe in [`docs/56`](docs/56-benchmark-gauntlet-remediation-evidence.md) shows per-commit persistence dominating at 5,000–10,000 facts (#562), so M is promoted only after #562 is bounded;
- **upstream model-judged QA:** not run;
- session and turn retrieval/currentness evidence is committed;
- external run is revision/input bound;
- no runtime, ingestion, out-of-corpus, or unmapped-admission failures occurred in the frozen S run;
- the run exposed currentness/ranking and scaling weaknesses. These were remediated in bounded slices and replayed against the same frozen input; the pre-remediation `f73b872` artifacts stay immutable.

The S run is a retrieval/currentness profile. It must not be presented as the upstream model-judged LongMemEval QA score.

### AgentMemBench / MemDialogue

Current status:

- bounded external MemDialogue v2 operational profile complete;
- deterministic retrieval, conflict/currentness, isolation, deletion, concurrency, and scale phases recorded;
- upstream LLM-judged retrieval is not run;
- M6 LLM portability is not run;
- product defects exposed:
  - #530, remediated;
  - #531 class A, remediated through #538's ranking policy; class B is recorded as an explicit limitation;
  - #522, with Part A (attestation) and Part B (domain-eligibility prefilter, #548) remediated and the remaining scale terms tracked.
- The pre-remediation `03197cd` artifacts stay immutable.

### SWE-ContextBench Lite

Start here: [`docs/50-swe-contextbench-comparison-harness.md`](docs/50-swe-contextbench-comparison-harness.md)

The synthetic smoke harness is executable and revision-bound, but it is deliberately **non-comparable** to the external research result.

The protocol-comparable external 99-query / 100-gold-edge lane remains blocked on the exact frozen research-compatible past-task projection and provenance required by #467.

Do not substitute the synthetic fixture for the external result.

### Internal RC retrieval fixture

The repository also retains deterministic internal fixtures that prove specific architecture behavior, such as multi-route recall recovering relevant memories missed by lexical-only recall while preserving governed admission.

These fixtures are valuable conformance evidence. They are not external efficacy evidence.

### Remediation replays

Every remediation slice under #537 is replayed against the same frozen input. It records improvements, regressions, and tradeoffs side by side, with artifacts under `reports/benchmarks/replays/`. The summary is in [`docs/56-benchmark-gauntlet-remediation-evidence.md`](docs/56-benchmark-gauntlet-remediation-evidence.md).

### Orthogonal temporal gauntlet (qualification only)

LongMemEval_S and AgentMemBench barely exercise validity intervals, as-of, or prospective questions. Candidate gauntlets are qualified in [`docs/59-orthogonal-temporal-gauntlet-qualification.md`](docs/59-orthogonal-temporal-gauntlet-qualification.md):

- **Ground Truth First** is blocked on artifact availability.
- **Microsoft RHELM** is runnable, but cannot falsify the targeted temporal claims.

Any run keeps the protocol-faithful text-only lane separate from the explicit-temporal-metadata conformance lane. The metadata lane is never presented as published-comparable.

## Generated scorecards

Human-readable portfolio and side-by-side scorecards:

- [`reports/benchmarks/scorecards/scorecards.md`](reports/benchmarks/scorecards/scorecards.md)

Machine-readable scorecards:

- `reports/benchmarks/scorecards/scorecards.json`

Normalized common-run evidence:

- `reports/benchmarks/normalized/`

Regeneration and interpretation rules:

- [`docs/55-memory-evaluation-scorecards.md`](docs/55-memory-evaluation-scorecards.md)

The scorecard system does not define an aggregate memory-health score. Retrieval, currentness, reasoning/QA, governance, efficiency, evaluator integrity, and reproducibility remain separate dimensions.

## Benchmark CLI

The Memory Evaluation CLI is documented in [`docs/54-memory-evaluation-cli.md`](docs/54-memory-evaluation-cli.md).

Supported evaluation operations include listing registered benchmark profiles, validating normalized run evidence, and fail-closed comparison of compatible runs.

Comparability depends on exact evidence identity. Two reports do not become comparable merely because their metric names look similar.

## The gauntlet learning loop

A benchmark result should normally flow through:

```text
external workload
    -> measured finding
    -> classify finding
    -> bounded issue / hypothesis
    -> product, architecture, or evaluator remediation
    -> exact frozen replay
    -> before/after evidence
    -> regression test / doctrine update / known limitation
```

Useful finding classes are:

- architecture validated;
- implementation defect;
- architecture gap;
- runtime/product contract gap;
- evaluation defect or gap;
- benchmark mismatch / non-applicable assumption;
- inconclusive.

One benchmark finding is evidence. Independent convergence across different benchmark families is stronger evidence of a general weakness.

The current benchmark-remediation architecture is tracked by #537.

## Rules for benchmark-driven changes

Do not:

- hardcode benchmark dataset IDs, phrases, or question classes into runtime behavior;
- change frozen input or evaluator semantics while claiming a before/after product comparison;
- collapse missing, blocked, or not-run evidence into numeric zero;
- treat a benchmark score as recall admission or mutation authority;
- weaken scope, tenant, currentness, deletion, or PAMA boundaries solely to improve recall;
- close a benchmark-discovered defect only because unit tests pass when the original workload can directly replay the repaired path.

Do:

- preserve exact revision, dataset/input digest, configuration, sample/selection identity, and environment where material;
- keep benchmark-native metrics available alongside normalized dimensions;
- report regressions and tradeoffs as visibly as improvements;
- separate product defects from evaluator defects and external blockers;
- keep pre-remediation evidence immutable.

## Evaluator integrity

The repository treats evaluator correctness as its own evidence dimension.

Mutation probes exist to verify that benchmark evaluators actually react to failures such as stale-over-current ordering, deletion failures, cross-scope leakage, dropped writes, identity corruption, or relevant-result suppression where the benchmark claims to measure those properties.

```text
evaluator-integrity pass != memory efficacy
```

A trustworthy ruler does not imply the thing being measured is good. It merely prevents us from congratulating ourselves with a broken ruler, which is already progress by software standards.
