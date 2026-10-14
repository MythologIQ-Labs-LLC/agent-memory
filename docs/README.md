# Agent Memory Documentation

<p align="center">
  <img src="../assets/brand/agent-memory-mark.png" alt="Agent Memory emblem: layered memory stack with connected nodes, an orbit, and a cyan inference spark." width="140">
</p>

This directory is the canonical documentation map for Agent Memory as it exists now: **a canonical architecture/governance corpus, an evaluation/benchmark laboratory, and an executable governed memory runtime**.

The product intent is governed, hierarchical, heterogeneous multi-system memory composition (structured/relational state, lexical and vector retrieval, typed graph and GraphRAG-style context, episodic/temporal/procedural memory, Markdown/file projections) under one governance boundary, specified in [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636). The only qualified canonical persistence profile today is single-host SQLite; see [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md).

## Three entry points

| Entry point | For | Start | Then |
|---|---|---|---|
| **Theory** | researchers studying memory architecture and governance | [`01-layer-model.md`](01-layer-model.md) | [`adr/README.md`](adr/README.md) (canonical doctrine-status ledger), [`pama/README.md`](pama/README.md), [`24-determinism-probability-and-governed-uncertainty.md`](24-determinism-probability-and-governed-uncertainty.md) |
| **Benchmarks** | evaluators running controlled comparisons, inspecting evidence, or bringing a system or a benchmark | [`../BENCHMARKS.md`](../BENCHMARKS.md) | [`../reports/benchmarks/dashboard/current.md`](../reports/benchmarks/dashboard/current.md), [`BENCHMARK_COVERAGE_ATLAS.md`](BENCHMARK_COVERAGE_ATLAS.md), [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md) |
| **Runtime** | builders integrating governed memory | [`47-developer-facade-and-local-open-path.md`](47-developer-facade-and-local-open-path.md) | [`45-agent-memory-rc1-implementation-profile.md`](45-agent-memory-rc1-implementation-profile.md), [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md), [`future/distributed-runtime-roadmap.md`](future/distributed-runtime-roadmap.md) (proposed, not implemented) |

The entry points are the repository's three operational roles. The project is also partitioned into a five-layer model; the two are reconciled in [#565](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/565) and summarised under "Repository operating model" below.

Start with [`REPOSITORY_OPERATING_MODEL.md`](REPOSITORY_OPERATING_MODEL.md) if you are unsure which role a document, issue, or contribution belongs to.

For current state, use the sources that own it: [`BACKLOG.md`](BACKLOG.md) (work queue and owner rulings), [`SYSTEM_STATE.md`](SYSTEM_STATE.md) (revision-bound projection), [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md) (what is qualified), `../reports/runtime/baseline-register.json` (current Runtime Baseline), the code-declared `POLICY_VERSION` and `CONTRACT_VERSION`, and the canonical dashboard at [`../reports/benchmarks/dashboard/current.md`](../reports/benchmarks/dashboard/current.md). [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) is the historical #591/#594 reconciliation.

## Choose your path

| Goal | Start here | Continue with |
|---|---|---|
| Use Agent Memory as a local runtime | [`47-developer-facade-and-local-open-path.md`](47-developer-facade-and-local-open-path.md) | [`45-agent-memory-rc1-implementation-profile.md`](45-agent-memory-rc1-implementation-profile.md), [`46-state-checkpoint-contract.md`](46-state-checkpoint-contract.md), [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md) |
| Understand the architecture | [`01-layer-model.md`](01-layer-model.md) | `11`, `13`, `18`, `22`, `24`, `42`, ADR index |
| Understand current RC/governance state | [`BACKLOG.md`](BACKLOG.md), [`SYSTEM_STATE.md`](SYSTEM_STATE.md) | issues #410, #668, #636; current benchmark dashboard; [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) for the historical #594 reconciliation |
| Understand lifecycle/currentness | [`02-lifecycle-state-machine.md`](02-lifecycle-state-machine.md) | [`18-temporal-causality-layer.md`](18-temporal-causality-layer.md), [`60-temporal-currentness-qualification-gauntlet.md`](60-temporal-currentness-qualification-gauntlet.md), [`61-write-time-proposition-semantics.md`](61-write-time-proposition-semantics.md) |
| Understand governance / PAMA | [`pama/README.md`](pama/README.md) | `04`, `17`, `33`, `34`, [`../GOVERNANCE.md`](../GOVERNANCE.md) |
| Evaluate / benchmark Agent Memory | [`../BENCHMARKS.md`](../BENCHMARKS.md) | [`53-memory-evaluation-subsystem.md`](53-memory-evaluation-subsystem.md), [`54-memory-evaluation-cli.md`](54-memory-evaluation-cli.md), [`55-memory-evaluation-scorecards.md`](55-memory-evaluation-scorecards.md) |
| Bring a memory system or a benchmark to the laboratory | [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md) | [`GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md`](GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md), [`GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md`](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md), [`GAUNTLET_ORCHESTRATION.md`](GAUNTLET_ORCHESTRATION.md), [`BENCHMARK_COVERAGE_ATLAS.md`](BENCHMARK_COVERAGE_ATLAS.md) |
| Review current benchmark results | [`../reports/benchmarks/dashboard/current.md`](../reports/benchmarks/dashboard/current.md) | [`../reports/benchmarks/dashboard/current.json`](../reports/benchmarks/dashboard/current.json), #594 closeout |
| Contribute code or evidence | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | [`REPOSITORY_OPERATING_MODEL.md`](REPOSITORY_OPERATING_MODEL.md), [`../GOVERNANCE.md`](../GOVERNANCE.md) |
| Review source rights / intellectual lineage | [`08-source-material-index.md`](08-source-material-index.md) | [`40-aligned-projects-and-intellectual-lineage.md`](40-aligned-projects-and-intellectual-lineage.md), [`SOURCE_RIGHTS_POLICY.md`](SOURCE_RIGHTS_POLICY.md) |
| Review UOR/PrismPM/TRACE/AGT lessons for cross-write proposition identity | [`research/cryptographic-proposition-identity-ancestry-2026-10-08.md`](research/cryptographic-proposition-identity-ancestry-2026-10-08.md) | [#757](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/757), [`52-harvest-closeout-final.md`](52-harvest-closeout-final.md) |
| Examine non-authoritative cross-write identity link safety | [`plan-757-proposition-link-falsification.md`](plan-757-proposition-link-falsification.md) | [#757](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/757); evaluation-only structural adversarial tests |
| Qualify append-only, unsigned proposition-link evidence replay | [`plan-757-link-evidence-journal.md`](plan-757-link-evidence-journal.md) | [#757](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/757); evaluation-only replay, no semantic or authority claims |
| Qualify independently pinned Ed25519 evidence-journal checkpoints | [`plan-757-signed-journal-checkpoints.md`](plan-757-signed-journal-checkpoints.md) | [#757](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/757); evaluation only, no issuer/semantic trust |
| Qualify explicit schema-backed cross-write property identity | [`plan-757-property-registry.md`](plan-757-property-registry.md) | [#757](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/757); evaluation-only candidate, no semantic authority |
| Review security/privacy | [`15-memory-threat-model.md`](15-memory-threat-model.md) | `16`, `19`, `28`, `29`, `41`, [`../SECURITY.md`](../SECURITY.md) |

## Repository operating model

Agent Memory has three first-class operational roles:

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

### Three roles and the five-layer project model

[`AGENT_MEMORY_PROJECT_MODEL.md`](AGENT_MEMORY_PROJECT_MODEL.md) partitions the wider project into five layers:

```text
1. Architecture / Doctrine / Research Commons
2. Memory Evaluation
3. Agent Memory Gauntlet
4. Reference / Conformance Implementation
5. future Distinct Production Runtime Product
```

Per the ruling in [#565](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/565), the three roles describe what the repository *does* operationally today, and the five layers describe how the project is *partitioned* for community, evaluation, qualification, reference implementation, and future product/licensing boundaries. Layer 1 is the architecture/governance role; layers 2 and 3 refine the evaluation role into measurement machinery plus the public Gauntlet; layers 4 and 5 refine the product/runtime role into the reference/conformance implementation that exists now plus a future distinct runtime whose identity and licensing are owned by [#556](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/556). Neither formulation supersedes the other.

Gauntlet and project-model documents:

| Document | Purpose |
|---|---|
| [`AGENT_MEMORY_PROJECT_MODEL.md`](AGENT_MEMORY_PROJECT_MODEL.md) | Five-layer project/product model (proposed under #554 / #556) |
| [`GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md`](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md) | System adapter contract for entering the Gauntlet |
| [`GAUNTLET_ORCHESTRATION.md`](GAUNTLET_ORCHESTRATION.md) | Gauntlet orchestration and failure attribution |
| [`GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md`](GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md) | Shortest supported external-contestant path |
| [`GOVERNANCE_GAUNTLET_SPECIFICATION.md`](GOVERNANCE_GAUNTLET_SPECIFICATION.md) | Governance Gauntlet specification |
| [`GOVERNANCE_GAUNTLET_ALPHA.md`](GOVERNANCE_GAUNTLET_ALPHA.md) | Governance Gauntlet alpha evidence |
| [`GAUNTLET_EXECUTION_ROADMAP.md`](GAUNTLET_EXECUTION_ROADMAP.md) | Proposed Gauntlet execution/staging plan |
| [`GAUNTLET_EXTERNAL_BENCHMARK_QUALIFICATION_2026-09-26.md`](GAUNTLET_EXTERNAL_BENCHMARK_QUALIFICATION_2026-09-26.md) | First-pass external benchmark qualification record (#560) |
| [`BENCHMARK_COVERAGE_ATLAS.md`](BENCHMARK_COVERAGE_ATLAS.md) | Capability-coverage map and benchmark admission vocabulary |
| [`RUNTIME_IDENTITY_NAMING_BRIEF.md`](RUNTIME_IDENTITY_NAMING_BRIEF.md) | Naming brief for the future distinct runtime (#556) |

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
| [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) | Historical RC dependency/governance reconciliation at the #591/#594 boundary (`691251c`); not refreshed |
| [`66-pre-1.0-maturity-and-runtime-qualification.md`](66-pre-1.0-maturity-and-runtime-qualification.md) | Pre-1.0 maturity program as reconciled at the #600-#602 boundary (`b50d6d1`): competitive comparators (#601) and runtime qualification (#602) |
| [`66-rust-runtime-qualification-current-state.md`](66-rust-runtime-qualification-current-state.md) | Rust shadow-kernel state; Python remains the qualified runtime |
| [`67-runtime-baseline-succession.md`](67-runtime-baseline-succession.md) | How a runtime change passes the Runtime Baseline mechanism (`reports/runtime/baseline-register.json`) |
| [`68-baseline-first-complete-architecture-execution.md`](68-baseline-first-complete-architecture-execution.md) | Owner execution posture: formal external baseline first, then complete runtime architecture |
| [`CONFIGURATION.md`](CONFIGURATION.md) | Runtime configuration contract and extension surfaces |
| [`47-transactional-checkpoint-generations.md`](47-transactional-checkpoint-generations.md) | Transaction semantics around the reference checkpoint profile (#414); distinct from `47-developer-facade…` |
| [`52-governed-cognitive-classification.md`](52-governed-cognitive-classification.md) | Governed classification-provider contract (#490/#500); distinct from `52-harvest-closeout-final` |
| [`future/distributed-runtime-roadmap.md`](future/distributed-runtime-roadmap.md) | **Proposed, not implemented**: staged path from single-host SQLite toward multi-substrate and distributed profiles |

A working runtime is not production 1.0. The qualified persistence posture remains deliberately bounded to single-host SQLite; the distributed roadmap above is a proposal, not a capability. Historical status lines inside older documents (for example public contract `1.2.0` in [`45-agent-memory-rc1-implementation-profile.md`](45-agent-memory-rc1-implementation-profile.md)) record the state at their publication; the current contract version is declared by `reference/agentmem_ref/api/contract.py` and summarised in [`44-public-api-contract.md`](44-public-api-contract.md).

## Evaluation and benchmark documentation

| Document | Purpose |
|---|---|
| [`../BENCHMARKS.md`](../BENCHMARKS.md) | Current benchmark portfolio, evidence classes and learning-loop rules |
| [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md) | Canonical contributor contract: Runtime vs Memory Evaluation vs Gauntlet, system-author and benchmark-author paths, state decision tree |
| [`50-swe-contextbench-comparison-harness.md`](50-swe-contextbench-comparison-harness.md) | SWE-ContextBench comparison harness and comparability boundary |
| [`50-keyed-rebinding-currentness-benchmark.md`](50-keyed-rebinding-currentness-benchmark.md) | Keyed rebinding / stale-value resistance benchmark (#483); distinct from `50-swe-contextbench…` |
| [`53-memory-evaluation-subsystem.md`](53-memory-evaluation-subsystem.md) | Benchmark-neutral evaluation architecture |
| [`54-memory-evaluation-cli.md`](54-memory-evaluation-cli.md) | Benchmark registry, validation and comparison CLI |
| [`55-memory-evaluation-scorecards.md`](55-memory-evaluation-scorecards.md) | Historical deterministic normalized scorecard machinery |
| [`56-benchmark-gauntlet-remediation-evidence.md`](56-benchmark-gauntlet-remediation-evidence.md) | Before/after replay evidence for benchmark-driven remediation |
| [`57-query-conditioned-applicability.md`](57-query-conditioned-applicability.md) | Query-conditioned applicability reference profile (ADR-039 Proposed) |
| [`59-orthogonal-temporal-gauntlet-qualification.md`](59-orthogonal-temporal-gauntlet-qualification.md) | Which temporal gauntlets can/cannot falsify ADR-039 claims |
| [`60-temporal-currentness-qualification-gauntlet.md`](60-temporal-currentness-qualification-gauntlet.md) | Frozen repository-owned temporal/currentness gauntlet |
| [`62-lessons-learned-evidence-and-currentness.md`](62-lessons-learned-evidence-and-currentness.md) | Lessons from the temporal/currentness arc |
| [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) | Dashboard interpretation and RC sequencing as of #594 (historical) |
| [`65-independent-amb-competitive-profile.md`](65-independent-amb-competitive-profile.md) | Independent AgentMemBench same-harness profile (#601/#640); its status line is historical, the dashboard carries accepted rows |
| [`69-agentmembench-mesa-formal-baseline.md`](69-agentmembench-mesa-formal-baseline.md) | Formal AgentMemBench/MESA baseline protocol and results (#694) |
| [`72-benchmark-neutral-remediation-loop.md`](72-benchmark-neutral-remediation-loop.md) | Benchmark-neutral evidence-to-remediation loop and read-only deficit audit (#722) |
| [`73-failure-memory-recall-shadow.md`](73-failure-memory-recall-shadow.md) | Failure-memory recall shadow qualification (#690, evaluation only) |
| [`benchmark-evidence-console-catalog.md`](benchmark-evidence-console-catalog.md) | Read-only benchmark console catalog contract (#698, PRD-002) |
| [`prd/README.md`](prd/README.md) | Product requirement documents, including the benchmark evidence console (PRD-002) |

Current generated evidence:

- `../reports/benchmarks/dashboard/current.md` is the canonical current human-readable portfolio;
- `../reports/benchmarks/dashboard/current.json` is its machine-readable form;
- `../reports/benchmarks/normalized/` contains common run manifests;
- `../reports/benchmarks/scorecards/` remains historical generated scorecard evidence;
- benchmark-specific frozen evidence remains under `../reports/benchmarks/`.

The repository intentionally does **not** define a universal memory-health score.

## Current semantic/temporal state

This index does not restate the active policy version, RC sequence, or follow-on issue list; they move faster than a navigation page. Read them in order from:

1. `reference/agentmem_ref/runtime/temporal_order_constraints.py` (`POLICY_VERSION`) and `reference/agentmem_ref/api/contract.py` (`CONTRACT_VERSION`) for the versions the code actually declares;
2. [`BACKLOG.md`](BACKLOG.md) for the current work queue and owner rulings, and [`SYSTEM_STATE.md`](SYSTEM_STATE.md) for the revision-bound projection;
3. [`61-write-time-proposition-semantics.md`](61-write-time-proposition-semantics.md) and [`63-post-550-architecture-reconciliation.md`](63-post-550-architecture-reconciliation.md) for the semantic contract;
4. [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) only for the historical #591/#594 reconciliation and its invariant list as of that boundary.

ADR-039 stays Proposed, and PR #587 / #583 stays DRAFT/HOLD, until the ADR index or the owning issue says otherwise.

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

The full series runs `00` through `42`. [`10-memory-unit-examples.md`](10-memory-unit-examples.md) and [`12-concept-segmentation-matrix.md`](12-concept-segmentation-matrix.md) are reference material; [`07-integration-roadmap.md`](07-integration-roadmap.md) and [`14-expanded-scope-recommendations.md`](14-expanded-scope-recommendations.md) are early-phase roadmap material, and the current execution posture is [`68-baseline-first-complete-architecture-execution.md`](68-baseline-first-complete-architecture-execution.md) plus [`BACKLOG.md`](BACKLOG.md).

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

## Plans, research briefs, and audits

`docs/` also carries dated working artifacts. They are evidence of how decisions were reached, not current-state authority:

| Family | Pattern | Status convention |
|---|---|---|
| Sprint and issue plans | `plan-sprint*.md`, `plan-<issue>-*.md` | Historical once their work merged; the live queue is [`BACKLOG.md`](BACKLOG.md) and GitHub issues |
| Research briefs | `research-brief-*.md`, [`RESEARCH_BRIEF.md`](RESEARCH_BRIEF.md), [`research/`](research/) | Research / ancestry evidence; never doctrine |
| Audits | [`audits/`](audits/) | Point-in-time reviews with their own evidence boundary; the #797 documentation inventory is [`audits/797-repository-discoverability-inventory.md`](audits/797-repository-discoverability-inventory.md) and its engineering companion is [`audits/797-engineering-cleanup-candidates.md`](audits/797-engineering-cleanup-candidates.md) |
| Programs | [`programs/runtime-evidence/README.md`](programs/runtime-evidence/README.md), [`programs/memory-modules/`](programs/memory-modules/), [`programs/atlas-research/README.md`](programs/atlas-research/README.md), [`programs/hermes-integration/README.md`](programs/hermes-integration/README.md) | Evidence programs with their own closeouts |
| Explorations | [`explorations/memory-architectures/README.md`](explorations/memory-architectures/README.md), [`explorations/field-claims/README.md`](explorations/field-claims/README.md) | Comparative/adversarial exploration; hypothesis class |
| Future subsystems | [`future/memory-compiler.md`](future/memory-compiler.md), [`future/multi-agent-shared-memory-protocol.md`](future/multi-agent-shared-memory-protocol.md), [`future/distributed-runtime-roadmap.md`](future/distributed-runtime-roadmap.md) | Proposed only; promotion needs an ADR and conformance surface |
| RFCs and PRDs | [`rfcs/README.md`](rfcs/README.md), [`prd/README.md`](prd/README.md) | Implementation-facing proposals subordinate to Accepted ADRs |
| Maintenance ledgers | [`GOVERNANCE_INDEX.md`](GOVERNANCE_INDEX.md), [`SYSTEM_STATE.md`](SYSTEM_STATE.md), [`FEATURE_INDEX.md`](FEATURE_INDEX.md), [`META_LEDGER.md`](META_LEDGER.md), [`SHADOW_GENOME.md`](SHADOW_GENOME.md) | Qor-logic development-time ledgers; each carries its own "last reconciled" boundary, which may lag `main` |

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
