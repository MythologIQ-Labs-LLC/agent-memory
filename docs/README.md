# Agent Memory Documentation

<p align="center">
  <img src="../assets/brand/agent-memory-mark.png" alt="Agent Memory emblem: layered memory stack with connected nodes, an orbit, and a cyan inference spark." width="140">
</p>

This directory is the canonical documentation map for Agent Memory as it exists now: **a canonical architecture/governance corpus, an evaluation/benchmark laboratory, and an executable governed memory runtime**.

The product intent is governed, hierarchical, heterogeneous multi-system memory composition (structured/relational state, lexical and vector retrieval, typed graph and GraphRAG-style context, episodic/temporal/procedural memory, Markdown/file projections) under one governance boundary, specified in [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636). The only qualified canonical persistence profile today is single-host SQLite; see [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md).

## Three entry points

| Entry point | For | Start | Then |
|---|---|---|---|
| **Theory** | researchers studying memory architecture and governance | [`ARCHITECTURE_INDEX.md`](ARCHITECTURE_INDEX.md), the single architecture catalog and filing policy | [`AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md`](AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md) (architectural explanation), [`adr/README.md`](adr/README.md) (accepted decisions), [`pama/README.md`](pama/README.md) |
| **Benchmarks** | evaluators running controlled comparisons, inspecting evidence, or bringing a system or a benchmark | [`../BENCHMARKS.md`](../BENCHMARKS.md) | [`../reports/benchmarks/dashboard/current.md`](../reports/benchmarks/dashboard/current.md), [`BENCHMARK_COVERAGE_ATLAS.md`](BENCHMARK_COVERAGE_ATLAS.md), [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md) |
| **Runtime** | builders integrating governed memory | [`47-developer-facade-and-local-open-path.md`](47-developer-facade-and-local-open-path.md) | [`45-agent-memory-rc1-implementation-profile.md`](45-agent-memory-rc1-implementation-profile.md), [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md), [`future/distributed-runtime-roadmap.md`](future/distributed-runtime-roadmap.md) (proposed, not implemented) |

For the start/stop boundaries among runtime implementation, agent-memory theory and lessons, and external comparative benchmarking through Gauntlet, use the [repository operating model](REPOSITORY_OPERATING_MODEL.md#component-ownership-exit-criteria-and-active-priority). The benchmark portfolio and comparability guidance live in [BENCHMARKS.md](../BENCHMARKS.md); the current development priority remains runtime retrieval quality.

The entry points are the repository's three operational roles. The proposed five-layer project partition has a different purpose, reconciled in [#565](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/565). The owning explanations are [REPOSITORY_OPERATING_MODEL.md](REPOSITORY_OPERATING_MODEL.md) and [AGENT_MEMORY_PROJECT_MODEL.md](AGENT_MEMORY_PROJECT_MODEL.md); this navigation index does not maintain a third summary.

Start with [`REPOSITORY_OPERATING_MODEL.md`](REPOSITORY_OPERATING_MODEL.md) if you are unsure which role a document, issue, or contribution belongs to.

For current state, use the sources that own it: [`BACKLOG.md`](BACKLOG.md) (work queue and owner rulings), [`SYSTEM_STATE.md`](SYSTEM_STATE.md) (revision-bound projection), [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md) (what is qualified), `../reports/runtime/baseline-register.json` (current Runtime Baseline), the code-declared `POLICY_VERSION` and `CONTRACT_VERSION`, and the canonical dashboard at [`../reports/benchmarks/dashboard/current.md`](../reports/benchmarks/dashboard/current.md). [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) is the historical #591/#594 reconciliation.

## Choose your path

| Goal | Start here | Continue with |
|---|---|---|
| Use Agent Memory as a local runtime | [`47-developer-facade-and-local-open-path.md`](47-developer-facade-and-local-open-path.md) | [`45-agent-memory-rc1-implementation-profile.md`](45-agent-memory-rc1-implementation-profile.md), [`46-state-checkpoint-contract.md`](46-state-checkpoint-contract.md), [`43-substrate-inventory-and-maturity.md`](43-substrate-inventory-and-maturity.md) |
| Understand the architecture | [`ARCHITECTURE_INDEX.md`](ARCHITECTURE_INDEX.md) | [`AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md`](AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md), [`01-layer-model.md`](01-layer-model.md), ADR index |
| Understand current RC/governance state | [`BACKLOG.md`](BACKLOG.md), [`SYSTEM_STATE.md`](SYSTEM_STATE.md) | issues #410, #668, #636; current benchmark dashboard; [`64-current-governance-and-benchmark-dashboard.md`](64-current-governance-and-benchmark-dashboard.md) for the historical #594 reconciliation |
| Understand lifecycle/currentness | [`02-lifecycle-state-machine.md`](02-lifecycle-state-machine.md) | [`18-temporal-causality-layer.md`](18-temporal-causality-layer.md), [`60-temporal-currentness-qualification-gauntlet.md`](60-temporal-currentness-qualification-gauntlet.md), [`61-write-time-proposition-semantics.md`](61-write-time-proposition-semantics.md) |
| Understand governance / PAMA | [`pama/README.md`](pama/README.md) | `04`, `17`, `33`, `34`, [`../GOVERNANCE.md`](../GOVERNANCE.md) |
| Evaluate / benchmark Agent Memory | [`../BENCHMARKS.md`](../BENCHMARKS.md) | [`53-memory-evaluation-subsystem.md`](53-memory-evaluation-subsystem.md), [`54-memory-evaluation-cli.md`](54-memory-evaluation-cli.md), [`55-memory-evaluation-scorecards.md`](55-memory-evaluation-scorecards.md) |
| Investigate precision, context quality and regressions | [#819 measured quality outcome](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/819) | [#775 relevance challenges](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/775), [#691 consumer package](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/691), [#782 research](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/782); experiments are not accepted score authority |
| Bring a memory system or a benchmark to the laboratory | [`CONTRIBUTOR_ARCHITECTURE.md`](CONTRIBUTOR_ARCHITECTURE.md) | [`GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md`](GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md), [`GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md`](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md), [`GAUNTLET_ORCHESTRATION.md`](GAUNTLET_ORCHESTRATION.md), [`BENCHMARK_COVERAGE_ATLAS.md`](BENCHMARK_COVERAGE_ATLAS.md) |
| Review current benchmark results | [`../reports/benchmarks/dashboard/current.md`](../reports/benchmarks/dashboard/current.md) | [`../reports/benchmarks/dashboard/current.json`](../reports/benchmarks/dashboard/current.json), #594 closeout |
| Contribute code or evidence | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | [`REPOSITORY_OPERATING_MODEL.md`](REPOSITORY_OPERATING_MODEL.md), [`../GOVERNANCE.md`](../GOVERNANCE.md) |
| Review source rights / intellectual lineage | [`08-source-material-index.md`](08-source-material-index.md) | [`40-aligned-projects-and-intellectual-lineage.md`](40-aligned-projects-and-intellectual-lineage.md), [`SOURCE_RIGHTS_POLICY.md`](SOURCE_RIGHTS_POLICY.md) |
| Control GitHub Actions budget and manual benchmark qualification | [`74-github-actions-cost-and-qualification.md`](74-github-actions-cost-and-qualification.md) | [`plan-662-finops-quiet-staging.md`](plan-662-finops-quiet-staging.md), [#662](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/662) |
| Review protected artifact retention and one-time workflow retirement | [`75-finops-protected-artifacts-and-closeout-review.md`](75-finops-protected-artifacts-and-closeout-review.md) | 43 protected workflows, 50 uncapped upload steps and 6 retirement candidates awaiting evidence review |
| Review security/privacy | [`15-memory-threat-model.md`](15-memory-threat-model.md) | `16`, `19`, `28`, `29`, `41`, [`../SECURITY.md`](../SECURITY.md) |

## Repository roles and project layers

The authoritative operating explanation is [REPOSITORY_OPERATING_MODEL.md](REPOSITORY_OPERATING_MODEL.md); the distinct proposed five-layer partition and its #565 reconciliation are owned by [AGENT_MEMORY_PROJECT_MODEL.md](AGENT_MEMORY_PROJECT_MODEL.md). The [architecture catalog](ARCHITECTURE_INDEX.md) owns filing and decision location. This navigation page does not maintain a competing architecture or maturity summary.

## Product and RC documentation

Audience navigation for the Runtime entry point. The authoritative shelf assignment for each document is [`ARCHITECTURE_INDEX.md`](ARCHITECTURE_INDEX.md) (shelf I); this table only routes.

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

Audience navigation for the Benchmarks entry point. The authoritative shelf assignment is [`ARCHITECTURE_INDEX.md`](ARCHITECTURE_INDEX.md) (shelf E); this table only routes.

| Document | Purpose |
|---|---|
| [`../BENCHMARKS.md`](../BENCHMARKS.md) | Benchmark methodology and authoritative live-dashboard pointers; no duplicate scores |
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

**Status lookup rule:** do not use this navigation page to determine whether an ADR or PR is currently proposed, accepted, draft, held, or merged. Read the live ADR status in [`adr/README.md`](adr/README.md) and the relevant GitHub PR/issue, then verify the exact implementation and accepted evidence before claiming runtime qualification.

## Architecture library

[`ARCHITECTURE_INDEX.md`](ARCHITECTURE_INDEX.md) is the single catalog for the architecture corpus: it files every numbered `docs/NN-*.md` document on exactly one shelf with a named owner, lists the non-numbered entry points and collections, and states the filing rule for new architectural documents. This page does not keep a second copy of that catalog. [`AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md`](AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md) is the governing architectural narrative; individual ADRs, schemas, code, and accepted evidence keep factual authority for their own claims.

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
