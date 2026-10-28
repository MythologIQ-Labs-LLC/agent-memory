# Agent Memory Benchmarks

Benchmarking is a first-class repository function, not an auxiliary test harness.

Agent Memory keeps benchmark adapters, evaluator-integrity probes, frozen run evidence, normalized manifests, accepted qualification gold, current dashboards, and remediation links alongside the runtime so behavior can be tied to exact revisions and replayed after change.

The governing repository relationship is documented in [`docs/REPOSITORY_OPERATING_MODEL.md`](docs/REPOSITORY_OPERATING_MODEL.md).

**What “Gauntlet” covers:** the externally usable portfolio of benchmark and assessment workloads, benchmark-native evaluators, neutral system adapters, orchestration, evaluator-integrity checks, evidence capture and comparable reporting. This is a **benchmarking laboratory for Agent Memory and third-party memory systems**, not the Agent Memory runtime, not a single score, and not a certification authority. The [repository operating model](docs/REPOSITORY_OPERATING_MODEL.md#component-ownership-exit-criteria-and-active-priority) owns the exact cross-role start/stop/handoff boundaries. [Gauntlet system-adapter contract](docs/GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md) owns the external system interface.

Gauntlet reports preserve each benchmark's native metrics. Cross-system comparisons require compatible workload/revision, selection, protocol, adapter contributions and metric definitions; when those differ, disclose **conditionally comparable** or **not directly comparable** rather than pretending the numbers share a denominator. A submitted run is not an independently reproduced run. A valid harness does not prove a good memory system.

**Development priority:** runtime precision, recall preservation, correctness and calibrated abstention remain the active product objective. Benchmark development should be bounded to measuring, falsifying and replaying those improvements; broadening the portfolio is not automatically higher priority than implementing the runtime.

The canonical current portfolio view is [`reports/benchmarks/dashboard/current.md`](reports/benchmarks/dashboard/current.md). Historical generated scorecards remain revision-bound snapshots and are not the current-state dashboard.

## Start here

| If you are | Go to |
|---|---|
| Inspecting current accepted evidence, deltas, and non-numeric states | [`reports/benchmarks/dashboard/current.md`](reports/benchmarks/dashboard/current.md) (canonical), `current.json` (machine-readable) |
| Checking which memory capabilities are measured, partial, or white space | [`docs/BENCHMARK_COVERAGE_ATLAS.md`](docs/BENCHMARK_COVERAGE_ATLAS.md) |
| Bringing a memory system or a benchmark | [`docs/CONTRIBUTOR_ARCHITECTURE.md`](docs/CONTRIBUTOR_ARCHITECTURE.md), then [`docs/GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md`](docs/GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md) |
| Running controlled same-harness comparisons | [`docs/65-independent-amb-competitive-profile.md`](docs/65-independent-amb-competitive-profile.md), [`docs/69-agentmembench-mesa-formal-baseline.md`](docs/69-agentmembench-mesa-formal-baseline.md), lane files under `reference/agentmem_ref/evaluation/lanes/` |
| Following per-metric leaderboard and evidence-freshness work | issues [#779](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/779), [#789](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/789), [#795](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/795); the console contract is [`docs/benchmark-evidence-console-catalog.md`](docs/benchmark-evidence-console-catalog.md) |
| Reading how findings become bounded remediation | [`docs/56-benchmark-gauntlet-remediation-evidence.md`](docs/56-benchmark-gauntlet-remediation-evidence.md), [`docs/72-benchmark-neutral-remediation-loop.md`](docs/72-benchmark-neutral-remediation-loop.md) |

The dashboard is the **only current numeric benchmark portfolio**. This guide intentionally maintains no copied scores or running RC schedule.

## Governing benchmark rules

```text
benchmark score != authority
benchmark score != truth
retrieval quality != answer-generation quality
retrieval quality != production readiness
harness validation != external benchmark comparability
blocked != 0
not_run != 0
evidence_gap != 0
```

The benchmark program has three jobs:

1. measure the runtime honestly;
2. falsify product/architecture assumptions;
3. prove bounded remediation against the same frozen input when the workload can exercise the mechanism.

There is no universal memory-health aggregate.

## Benchmark coverage and evidence owners

The benchmark portfolio changes as accepted results, competitor reproductions, and blocked evaluations change. Inspect the [canonical dashboard](reports/benchmarks/dashboard/current.md) and its [machine-readable evidence](reports/benchmarks/dashboard/current.json) rather than quoting numbers from this file.

| Workload or evidence family | Interpret or reproduce at its owner |
|---|---|
| LongMemEval_S and LongMemEval_M | Same-harness/adapted retrieval and temporal evidence in the dashboard; do not confuse retrieval scores with model-judged QA |
| AgentMemBench / MESA | [Formal MESA baseline](docs/69-agentmembench-mesa-formal-baseline.md) and dashboard; do not equate source retrieval with final answer quality |
| Natural proposition semantics | [#594 accepted closeout](reports/benchmarks/replays/594-post-550-semantic-qualification/CLOSEOUT.md), with interpretation failure classes preserved |
| SWE-ContextBench Lite | [Comparison harness](docs/50-swe-contextbench-comparison-harness.md) and [coverage atlas](docs/BENCHMARK_COVERAGE_ATLAS.md); synthetic probes are not protocol-comparable external results |
| Temporal and internal conformance | [Orthogonal gauntlets](docs/59-orthogonal-temporal-gauntlet-qualification.md), [temporal/currentness program](docs/60-temporal-currentness-qualification-gauntlet.md), and immutable fixture/evidence records |
| External competitive systems | [AMB independent profile](docs/65-independent-amb-competitive-profile.md), [Gauntlet contestant guide](docs/GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md), and version-pinned same-harness dashboard rows |

A profile's integration-admission status is not its evidence-execution or score-acceptance status. Unavailable, blocked, unsupported, non-comparable, and unexecuted are distinct from a numeric zero. Historical results remain accessible in their own revision-bound artifacts.

## Contributor contracts

Two contributor paths are specified and executable; both are documented in [`docs/CONTRIBUTOR_ARCHITECTURE.md`](docs/CONTRIBUTOR_ARCHITECTURE.md):

```text
system author     adapter manifest -> operation envelopes -> capability negotiation
                  -> Gauntlet profile -> native + normalized evidence
benchmark author  integration descriptor -> benchmark-native runner -> native evidence
                  -> optional common-dimension mappings -> evaluator-integrity controls
                  -> optional Gauntlet profile binding
```

Every benchmark in this portfolio has a committed integration descriptor (`reference/agentmem_ref/evaluation/integrations/`, validated against `schemas/memory-benchmark-integration.schema.json`) that records its exact upstream revision, source rights, input-digest and selection rules, native metrics, runner, system invocation surface, provider requirements, normalization mappings, negative controls, and Gauntlet relationship. `agent-memory benchmark list | inspect | validate-integration` read them without executing anything. The `golden-keyed-retrieval-v1` integration is the executable demonstration of the benchmark-author path; it is `baseline_or_probe` evidence and is deliberately absent from the portfolio above.

## Current dashboard and historical scorecards

Canonical current dashboard:

- [`reports/benchmarks/dashboard/current.md`](reports/benchmarks/dashboard/current.md)
- `reports/benchmarks/dashboard/current.json`

It reports current accepted evidence, previous accepted evidence/deltas where available, exact provenance, evidence class, and non-numeric states.

Historical generated scorecards remain at:

- `reports/benchmarks/scorecards/scorecards.md`
- `reports/benchmarks/scorecards/scorecards.json`

Those artifacts are useful revision-bound history. They are not the current portfolio authority after #591/#594.

## Remediation evidence

Benchmark-driven remediation evidence is preserved in [`docs/56-benchmark-gauntlet-remediation-evidence.md`](docs/56-benchmark-gauntlet-remediation-evidence.md) and `reports/benchmarks/replays/`.

Important completed steps include:

- explicit ranking/currentness policy and admitted-set BM25;
- runtime-owned serialization for shared handles;
- incremental integrity attestation;
- domain/identity candidate prefiltering;
- deterministic BM25 summation (#576);
- typed write-time semantic evidence (#550);
- identity-first candidate materialization performance repair (#591);
- natural semantic qualification (#594).

## Active remediation and evaluation sequence

The live RC/runtime program, completed steps, blockers and implementation owners are maintained in [BACKLOG.md](docs/BACKLOG.md), [SYSTEM_STATE.md](docs/SYSTEM_STATE.md), and [open GitHub issues](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues). Earlier RC dependency chains are preserved in revision-bound evidence, not repeated here as current instructions.

## Rules for benchmark-driven changes

Do not:

- hardcode benchmark dataset IDs, phrases, or question classes into runtime behavior;
- change frozen input or evaluator semantics while claiming a before/after product comparison;
- populate gold/property aliases after inspecting predictions simply to improve a score;
- collapse missing, blocked, not-run, or evidence-gap states into numeric zero;
- treat a benchmark score as recall admission or mutation authority;
- weaken scope, tenant, currentness, deletion, or PAMA boundaries solely to improve recall.

Do:

- preserve exact revision, input digest, sample/selection identity, configuration, and evidence class;
- keep benchmark-native metrics alongside normalized portfolio dimensions;
- report regressions/tradeoffs as visibly as improvements;
- separate product defects from evaluator defects and external blockers;
- keep pre-remediation and pre-gold evidence immutable;
- use Part R and stratified Part S according to their actual statistical meaning.

## Evaluator integrity

Evaluator correctness is its own evidence dimension.

Mutation probes verify that evaluators react to corruption/failure classes they claim to measure. #594 additionally proves that accepted gold cannot be loaded from draft annotations, verifies the accepted source hash before materializing items, and freezes property aliases before scoring.

```text
evaluator-integrity pass != memory efficacy
```

A trustworthy ruler does not imply the thing measured is good. It merely prevents us from congratulating ourselves with a broken ruler, which is already more discipline than software usually volunteers for.
