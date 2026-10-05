# Agent Memory Documentation

<p align="center">
  <img src="../assets/brand/agent-memory-mark.png" alt="Agent Memory emblem: layered memory stack with connected nodes, an orbit, and a cyan inference spark." width="140">
</p>

This directory is the canonical documentation map for Agent Memory as it exists now: **an executable governed memory runtime, a canonical architecture/governance corpus, and an evaluation/benchmark laboratory**.

Start with [`REPOSITORY_OPERATING_MODEL.md`](REPOSITORY_OPERATING_MODEL.md) if you are unsure which role a document, issue, or contribution belongs to.

For the current RC/evidence boundary after #591/#594, start with [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) and the canonical dashboard at [`../reports/benchmarks/dashboard/current.md`](../reports/benchmarks/dashboard/current.md).

## Choose your path

| Goal | Start here | Continue with |
|---|---|---|
| Use Agent Memory as a local runtime | [`47-developer-facade-and-local-open-path.md`](47-developer-facade-and-local-open-path.md) | [`45-agent-memory-rc1-implementation-profile.md`](45-agent-memory-rc1-implementation-profile.md), [`46-state-checkpoint-contract.md`](46-state-checkpoint-contract.md), [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md) |
| Understand the architecture | [`01-layer-model.md`](01-layer-model.md) | `11`, `13`, `18`, `22`, `24`, `42`, ADR index |
| Understand current RC/governance state | [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) | issue #410, current benchmark dashboard |
| Understand lifecycle/currentness | [`02-lifecycle-state-machine.md`](02-lifecycle-state-machine.md) | [`18-temporal-causality-layer.md`](18-temporal-causality-layer.md), [`60-temporal-currentness-qualification-gauntlet.md`](60-temporal-currentness-qualification-gauntlet.md), [`61-write-time-proposition-semantics.md`](61-write-time-proposition-semantics.md) |
| Understand governance / PAMA | [`pama/README.md`](pama/README.md) | `04`, `17`, `33`, `34`, [`../GOVERNANCE.md`](../GOVERNANCE.md) |
| Evaluate / benchmark Agent Memory | [`../BENCHMARKS.md`](../BENCHMARKS.md) | [`53-memory-evaluation-subsystem.md`](53-memory-evaluation-subsystem.md), [`54-memory-evaluation-cli.md`](54-memory-evaluation-cli.md), [`55-memory-evaluation-scorecards.md`](55-memory-evaluation-scorecards.md) |
| Bring a memory system or a benchmark to the laboratory | [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md) | [`GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md`](GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md), [`GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md`](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md), [`GAUNTLET_ORCHESTRATION.md`](GAUNTLET_ORCHESTRATION.md), [`BENCHMARK_COVERAGE_ATLAS.md`](BENCHMARK_COVERAGE_ATLAS.md) |
| Review current benchmark results | [`../reports/benchmarks/dashboard/current.md`](../reports/benchmarks/dashboard/current.md) | [`../reports/benchmarks/dashboard/current.json`](../reports/benchmarks/dashboard/current.json), #594 closeout |
| Contribute code or evidence | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | [`REPOSITORY_OPERATING_MODEL.md`](REPOSITORY_OPERATING_MODEL.md), [`../GOVERNANCE.md`](../GOVERNANCE.md) |
| Review source rights / intellectual lineage | [`08-source-material-index.md`](08-source-material-index.md) | [`40-aligned-projects-and-intellectual-lineage.md`](40-aligned-projects-and-intellectual-lineage.md), [`SOURCE_RIGHTS_POLICY.md`](SOURCE_RIGHTS_POLICY.md) |
| Review security/privacy | [`15-memory-threat-model.md`](15-memory-threat-model.md) | `16`, `19`, `28`, `29`, `41`, [`../SECURITY.md`](../SECURITY.md) |

## Repository operating model

Agent Memory has three first-class roles:

```text
product / runtime
architecture / governance laboratory
evaluation / benchmark laboratory
```

The roles are connected but authority-separated.

- Product execution makes architecture falsifiable.
- Architecture gives product behavior principled boundaries.
- Evaluation pressures both with external and adversarial evidence.
- Governance prevents benchmark scores, model outputs, implementation shortcuts, or research ancestry from silently granting themselves authority.

Full guidance: [`REPOSITORY_OPERATING_MODEL.md`](REPOSITORY_OPERATING_MODEL.md).

## Product and RC documentation

| Document | Purpose |
|---|---|
| [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md) | Substrate inventory, qualification and maturity boundaries |
| [`44-public-api-contract.md`](44-public-api-contract.md) | Versioned public consumer contract |
| [`45-agent-memory-rc1-implementation-profile.md`](45-agent-memory-rc1-implementation-profile.md) | RC1 implementation profile and bounded release posture |
| [`46-state-checkpoint-contract.md`](46-state-checkpoint-contract.md) | Restart, integrity, checkpoint and recovery contract |
| [`47-developer-facade-and-local-open-path.md`](47-developer-facade-and-local-open-path.md) | Installed `AgentMemory` developer facade and local qualified open path |
| [`48-rc-cognitive-memory-lifecycle-evidence.md`](48-rc-cognitive-memory-lifecycle-evidence.md) | End-to-end cognitive-memory lifecycle evidence |
| [`49-rc1-evidence-closeout.md`](49-rc1-evidence-closeout.md) | Earlier RC evidence closeout and claim boundaries |
| [`58-historical-evidence-admission.md`](58-historical-evidence-admission.md) | Current-state vs explicit historical-evidence admission |
| [`61-write-time-proposition-semantics.md`](61-write-time-proposition-semantics.md) | Current #550 semantics contract plus #591/#594 qualification results |
| [`63-post-550-architecture-reconciliation.md`](63-post-550-architecture-reconciliation.md) | Post-#550 architecture reconciliation |
| [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) | Canonical current RC dependency/governance state after #594 |

A working runtime is not production 1.0. The qualified persistence posture remains deliberately bounded, especially around single-host SQLite versus distributed deployment.

## Evaluation and benchmark documentation

| Document | Purpose |
|---|---|
| [`../BENCHMARKS.md`](../BENCHMARKS.md) | Current benchmark portfolio, evidence classes and learning-loop rules |
| [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md) | Canonical contributor contract: Runtime vs Memory Evaluation vs Gauntlet, system-author and benchmark-author paths, state decision tree |
| [`50-swe-contextbench-comparison-harness.md`](50-swe-contextbench-comparison-harness.md) | SWE-ContextBench comparison harness and comparability boundary |
| [`53-memory-evaluation-subsystem.md`](53-memory-evaluation-subsystem.md) | Benchmark-neutral evaluation architecture |
| [`54-memory-evaluation-cli.md`](54-memory-evaluation-cli.md) | Benchmark registry, validation and comparison CLI |
| [`55-memory-evaluation-scorecards.md`](55-memory-evaluation-scorecards.md) | Historical deterministic normalized scorecard machinery |
| [`56-benchmark-gauntlet-remediation-evidence.md`](56-benchmark-gauntlet-remediation-evidence.md) | Before/after replay evidence for benchmark-driven remediation |
| [`57-query-conditioned-applicability.md`](57-query-conditioned-applicability.md) | Query-conditioned applicability reference profile (ADR-039 Proposed) |
| [`59-orthogonal-temporal-gauntlet-qualification.md`](59-orthogonal-temporal-gauntlet-qualification.md) | Which temporal gauntlets can/cannot falsify ADR-039 claims |
| [`60-temporal-currentness-qualification-gauntlet.md`](60-temporal-currentness-qualification-gauntlet.md) | Frozen repository-owned temporal/currentness gauntlet |
| [`62-lessons-learned-evidence-and-currentness.md`](62-lessons-learned-evidence-and-currentness.md) | Lessons from the temporal/currentness arc |
| [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) | Current dashboard interpretation and RC sequencing |

Current generated evidence:

- `../reports/benchmarks/dashboard/current.md` is the canonical current human-readable portfolio;
- `../reports/benchmarks/dashboard/current.json` is its machine-readable form;
- `../reports/benchmarks/normalized/` contains common run manifests;
- `../reports/benchmarks/scorecards/` remains historical generated scorecard evidence;
- benchmark-specific frozen evidence remains under `../reports/benchmarks/`.

The repository intentionally does **not** define a universal memory-health score.

## Current semantic/temporal state

#550's deterministic write-time semantic carrier is implemented and policy 3.1.0 is active. #591 repaired candidate-materialization overhead without changing semantic/retrieval results. #594 is **QUALIFIED** with:

- defensible adapted external evidence for source-anchored LongMemEval_S, but an explicit self-validity-demotion efficacy **EVIDENCE GAP**;
- independently accepted 268-turn proposition-semantics gold;
- first deterministic natural-data interpreter score;
- follow-ons #596, #597 and #598.

#598 is now on the temporal dependency path before redesigned #583. #585 remains the separate query-side intent calibration. PR #587 / #583 stays DRAFT/HOLD. ADR-039 stays Proposed.

## Canonical architecture spine

The `00` through `42` series contains the canonical architecture and operational-contract corpus. Key starting points:

- [`00-glossary.md`](00-glossary.md)
- [`01-layer-model.md`](01-layer-model.md)
- [`02-lifecycle-state-machine.md`](02-lifecycle-state-machine.md)
- [`04-governance-and-pama.md`](04-governance-and-pama.md)
- [`05-repo-implementation-map.md`](05-repo-implementation-map.md)
- [`13-system-composition-boundaries.md`](13-system-composition-boundaries.md)
- [`15-memory-threat-model.md`](15-memory-threat-model.md)
- [`18-temporal-causality-layer.md`](18-temporal-causality-layer.md)
- [`21-forgetting-consolidation-and-memory-metabolism.md`](21-forgetting-consolidation-and-memory-metabolism.md)
- [`24-determinism-probability-and-governed-uncertainty.md`](24-determinism-probability-and-governed-uncertainty.md)
- [`26-governed-recall-planner.md`](26-governed-recall-planner.md)
- [`33-pama-decision-table.md`](33-pama-decision-table.md)
- [`41-memory-isolation-domains-and-governed-crossing.md`](41-memory-isolation-domains-and-governed-crossing.md)
- [`42-governed-mutable-memory-fabric.md`](42-governed-mutable-memory-fabric.md)

## Architecture Decision Records

See [`adr/README.md`](adr/README.md).

The ADR index is the canonical doctrine-status ledger. Implementation or benchmark evidence does not silently promote, supersede, or reject an ADR.

## PAMA

**Proportional Adaptive Mutation Authority (PAMA)** is native Agent Memory doctrine authored by **Kevin R. Knapp**.

Start with [`pama/README.md`](pama/README.md), then use [`04-governance-and-pama.md`](04-governance-and-pama.md) and [`33-pama-decision-table.md`](33-pama-decision-table.md).

```text
adaptation != authority
memory != procedure
procedure != permission
permission != governance
```

## Source rights and aligned projects

- [`40-aligned-projects-and-intellectual-lineage.md`](40-aligned-projects-and-intellectual-lineage.md) records typed relationships to aligned and ancestral projects.
- [`SOURCE_RIGHTS_POLICY.md`](SOURCE_RIGHTS_POLICY.md) defines citation, synthesis, author-originated and licensed reuse modes.
- `../sources/source-registry.json` records material source posture.
- `../schemas/source-record.schema.json` makes those records machine-checkable.

Public readability is not treated as an open license. Implementation ancestry is evidence and provenance, not automatic runtime ownership.

## Evidence discipline

Every material claim should be understandable as one or more of:

```text
doctrine
product contract
implementation
conformance evidence
benchmark evidence
field evidence
research / ancestry
hypothesis
```

Those labels prevent maturity and authority from spreading by association. A benchmark result can challenge doctrine. A passing fixture can validate a contract. Neither becomes something else merely because it is convenient to describe it that way.
