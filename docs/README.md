# Agent Memory Documentation

<p align="center">
  <img src="../assets/brand/agent-memory-mark.png" alt="Agent Memory emblem: layered memory stack with connected nodes, an orbit, and a cyan inference spark." width="140">
</p>

This directory is the canonical documentation map for Agent Memory as it exists now: **an executable governed memory runtime, a canonical architecture/governance corpus, and an evaluation/benchmark laboratory**.

Start with [`56-repository-operating-model.md`](56-repository-operating-model.md) if you are unsure which role a document, issue, or contribution belongs to.

## Choose your path

| Goal | Start here | Continue with |
|---|---|---|
| Use Agent Memory as a local runtime | [`47-developer-facade-and-local-open-path.md`](47-developer-facade-and-local-open-path.md) | [`45-agent-memory-rc1-implementation-profile.md`](45-agent-memory-rc1-implementation-profile.md), [`46-state-checkpoint-contract.md`](46-state-checkpoint-contract.md), [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md) |
| Understand the architecture | [`01-layer-model.md`](01-layer-model.md) | `11`, `13`, `18`, `22`, `24`, `42`, ADR index |
| Understand lifecycle/currentness | [`02-lifecycle-state-machine.md`](02-lifecycle-state-machine.md) | [`03-scoring-and-decay.md`](03-scoring-and-decay.md), [`18-temporal-causality-layer.md`](18-temporal-causality-layer.md), [`21-forgetting-consolidation-and-memory-metabolism.md`](21-forgetting-consolidation-and-memory-metabolism.md) |
| Understand governance / PAMA | [`pama/README.md`](pama/README.md) | `04`, `17`, `33`, `34`, [`../GOVERNANCE.md`](../GOVERNANCE.md) |
| Evaluate / benchmark Agent Memory | [`../BENCHMARKS.md`](../BENCHMARKS.md) | [`53-memory-evaluation-subsystem.md`](53-memory-evaluation-subsystem.md), [`54-memory-evaluation-cli.md`](54-memory-evaluation-cli.md), [`55-memory-evaluation-scorecards.md`](55-memory-evaluation-scorecards.md) |
| Review benchmark results | [`../reports/benchmarks/scorecards/scorecards.md`](../reports/benchmarks/scorecards/scorecards.md) | normalized manifests in `../reports/benchmarks/normalized/` |
| Contribute code or evidence | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | [`56-repository-operating-model.md`](56-repository-operating-model.md), [`../GOVERNANCE.md`](../GOVERNANCE.md) |
| Review source rights / intellectual lineage | [`08-source-material-index.md`](08-source-material-index.md) | [`40-aligned-projects-and-intellectual-lineage.md`](40-aligned-projects-and-intellectual-lineage.md), [`SOURCE_RIGHTS_POLICY.md`](SOURCE_RIGHTS_POLICY.md) |
| Review security/privacy | [`15-memory-threat-model.md`](15-memory-threat-model.md) | `16`, `19`, `28`, `29`, `41`, [`../SECURITY.md`](../SECURITY.md) |

## Repository operating model

Agent Memory now has three first-class roles:

```text
product / runtime
architecture / governance laboratory
evaluation / benchmark laboratory
```

The roles are deliberately connected but authority-separated.

- Product execution makes architecture falsifiable.
- Architecture gives product behavior principled boundaries.
- Evaluation pressures both with external and adversarial evidence.
- Governance prevents benchmark scores, model outputs, implementation shortcuts, or research ancestry from silently granting themselves authority.

Full guidance: [`56-repository-operating-model.md`](56-repository-operating-model.md).

## Product and RC documentation

The repository has moved beyond a theory-only reference implementation.

| Document | Purpose |
|---|---|
| [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md) | Substrate inventory, qualification and maturity boundaries |
| [`44-public-api-contract.md`](44-public-api-contract.md) | Versioned public consumer contract |
| [`45-agent-memory-rc1-implementation-profile.md`](45-agent-memory-rc1-implementation-profile.md) | RC1 implementation profile and bounded release posture |
| [`46-state-checkpoint-contract.md`](46-state-checkpoint-contract.md) | Restart, integrity, checkpoint and recovery contract |
| [`47-developer-facade-and-local-open-path.md`](47-developer-facade-and-local-open-path.md) | Installed `AgentMemory` developer facade and local qualified open path |
| [`48-rc-cognitive-memory-lifecycle-evidence.md`](48-rc-cognitive-memory-lifecycle-evidence.md) | End-to-end cognitive-memory lifecycle evidence |
| [`49-rc1-evidence-closeout.md`](49-rc1-evidence-closeout.md) | RC evidence closeout and claim boundaries |

A working runtime is not the same thing as production 1.0. The qualified persistence posture remains deliberately bounded, especially around single-host SQLite versus distributed deployment.

## Evaluation and benchmark documentation

Evaluation is a first-class subsystem rather than a collection of one-off scripts.

| Document | Purpose |
|---|---|
| [`../BENCHMARKS.md`](../BENCHMARKS.md) | Human entry point to the benchmark portfolio and gauntlet-learning rules |
| [`50-swe-contextbench-comparison-harness.md`](50-swe-contextbench-comparison-harness.md) | SWE-ContextBench comparison harness and comparability boundary |
| [`53-memory-evaluation-subsystem.md`](53-memory-evaluation-subsystem.md) | Benchmark-neutral evaluation architecture and runtime/evaluation separation |
| [`54-memory-evaluation-cli.md`](54-memory-evaluation-cli.md) | Benchmark registry, validation and comparison CLI |
| [`55-memory-evaluation-scorecards.md`](55-memory-evaluation-scorecards.md) | Deterministic normalized scorecards and portfolio reporting |
| [`56-repository-operating-model.md`](56-repository-operating-model.md) | How benchmark evidence can drive product or architecture changes without becoming authority |

Generated evidence:

- `../reports/benchmarks/normalized/` contains common run manifests;
- `../reports/benchmarks/scorecards/scorecards.md` is the human-readable portfolio;
- `../reports/benchmarks/scorecards/scorecards.json` is the machine-readable portfolio;
- benchmark-specific frozen evidence remains under `../reports/benchmarks/`.

The repository intentionally does **not** define a universal memory-health score.

## 00-10: Canonical architecture spine

| # | Document | Purpose |
|---|---|---|
| 00 | [`00-glossary.md`](00-glossary.md) | Canonical vocabulary and term boundaries |
| 01 | [`01-layer-model.md`](01-layer-model.md) | Layer ownership, deterministic substrate, probabilistic epistemics, governance boundaries |
| 02 | [`02-lifecycle-state-machine.md`](02-lifecycle-state-machine.md) | Memory states, proposal-versus-commit, promotion, dispute, correction, pruning |
| 03 | [`03-scoring-and-decay.md`](03-scoring-and-decay.md) | Saturation, decay, uncertainty, calibration, drift and threshold stability |
| 04 | [`04-governance-and-pama.md`](04-governance-and-pama.md) | Native PAMA specialization and bounded consequence |
| 05 | [`05-repo-implementation-map.md`](05-repo-implementation-map.md) | Implementation ancestry and ownership mapping |
| 06 | [`06-conformance-test-plan.md`](06-conformance-test-plan.md) | Conformance levels and adversarial fixture requirements |
| 07 | [`07-integration-roadmap.md`](07-integration-roadmap.md) | Doctrine-to-implementation roadmap |
| 08 | [`08-source-material-index.md`](08-source-material-index.md) | Source provenance, rights posture and evidence domains |
| 09 | [`09-calibration-protocol.md`](09-calibration-protocol.md) | Calibration, abstention, hysteresis, disagreement and drift |
| 10 | [`10-memory-unit-examples.md`](10-memory-unit-examples.md) | Concrete memory, uncertainty, authority, receipt and scope examples |

## 11-19: Composition, trust, time and privacy

| # | Document | Purpose |
|---|---|---|
| 11 | [`11-component-architecture.md`](11-component-architecture.md) | Component boundaries and ownership |
| 12 | [`12-concept-segmentation-matrix.md`](12-concept-segmentation-matrix.md) | Concept placement and doctrine-promotion criteria |
| 13 | [`13-system-composition-boundaries.md`](13-system-composition-boundaries.md) | Typed handoffs and composition failure modes |
| 14 | [`14-expanded-scope-recommendations.md`](14-expanded-scope-recommendations.md) | Controlled expansion candidates |
| 15 | [`15-memory-threat-model.md`](15-memory-threat-model.md) | Poisoning, leakage, authority laundering and lifecycle attacks |
| 16 | [`16-source-trust-and-reputation.md`](16-source-trust-and-reputation.md) | Source trust, independence and reputation scope |
| 17 | [`17-conflict-resolution-engine.md`](17-conflict-resolution-engine.md) | Conflict interpretation and governed consequences |
| 18 | [`18-temporal-causality-layer.md`](18-temporal-causality-layer.md) | Event time, valid time, supersession and causal uncertainty |
| 19 | [`19-privacy-and-sensitivity-classifier.md`](19-privacy-and-sensitivity-classifier.md) | Sensitivity, privacy, minimization and deletion fidelity |

## 20-25: Theory and governed uncertainty

| # | Document | Purpose |
|---|---|---|
| 20 | [`20-memory-foundations-across-scales.md`](20-memory-foundations-across-scales.md) | Biological, cognitive, agentic and collective memory foundations |
| 21 | [`21-forgetting-consolidation-and-memory-metabolism.md`](21-forgetting-consolidation-and-memory-metabolism.md) | Forgetting, consolidation, semanticization and metabolism |
| 22 | [`22-agentic-memory-theory-and-development.md`](22-agentic-memory-theory-and-development.md) | Engineering doctrine and development sequence |
| 23 | [`23-research-bibliography.md`](23-research-bibliography.md) | Evidence map across memory science and agent-memory research |
| 24 | [`24-determinism-probability-and-governed-uncertainty.md`](24-determinism-probability-and-governed-uncertainty.md) | Deterministic/probabilistic boundary and governed uncertainty |
| 25 | [`25-governed-uncertainty-documentation-conformance-audit.md`](25-governed-uncertainty-documentation-conformance-audit.md) | Documentation-conformance rubric |

## 26-42: Operational and executable contracts

The `26` through `42` series turns the architecture into explicit operational contracts, including governed recall, schema evolution, deletion/tombstones, tenancy, observability, recovery, quality metrics, PAMA decision tables, adapter/interoperability contracts, policy-as-memory, budgets, correction UX, ownership, isolation domains, and the governed mutable memory fabric.

Key entries:

- [`26-governed-recall-planner.md`](26-governed-recall-planner.md)
- [`28-retention-deletion-and-tombstones.md`](28-retention-deletion-and-tombstones.md)
- [`29-actor-scope-consent-and-tenancy.md`](29-actor-scope-consent-and-tenancy.md)
- [`31-recovery-rollback-and-replay.md`](31-recovery-rollback-and-replay.md)
- [`32-memory-quality-metrics.md`](32-memory-quality-metrics.md)
- [`33-pama-decision-table.md`](33-pama-decision-table.md)
- [`39-implementation-ownership-map.md`](39-implementation-ownership-map.md)
- [`41-memory-isolation-domains-and-governed-crossing.md`](41-memory-isolation-domains-and-governed-crossing.md)
- [`42-governed-mutable-memory-fabric.md`](42-governed-mutable-memory-fabric.md)

## Architecture Decision Records

See [`adr/README.md`](adr/README.md).

The ADR index is the canonical doctrine-status ledger. Implementation or benchmark evidence does not silently promote, supersede, or reject an ADR.

## PAMA

**Proportional Adaptive Mutation Authority (PAMA)** is native Agent Memory doctrine authored by **Kevin R. Knapp**.

Start with [`pama/README.md`](pama/README.md), then use [`04-governance-and-pama.md`](04-governance-and-pama.md) and [`33-pama-decision-table.md`](33-pama-decision-table.md) for the Agent Memory specialization.

Core separation:

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

Those labels exist to prevent maturity and authority from spreading by association. A benchmark result can challenge doctrine. A passing fixture can validate a contract. Neither one becomes something else merely because it is convenient to describe it that way.
