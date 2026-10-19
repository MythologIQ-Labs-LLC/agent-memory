# Agent Memory Architecture Library Index

**Role:** the **single authoritative architectural catalog and filing/routing rule** for this repository.  
**Boundary:** a navigation and ownership contract, **not** an ADR, product requirement, implementation, status dashboard, acceptance ruling or replacement architecture.  
**Inventory baseline:** `main` `3eebb6d54e2a218c4fd10cf53c52acac8384c3e6` (2026-10-14). The links are stable locations; maturity and issue status must be read from their owners.

> **Start here for every architectural lookup or architectural-document change.** Determine the shelf and the source that owns the *specific claim* before reading or writing. Do not create a new "canonical summary" to repair an older summary.

## 1. One front door, one owner per claim

| Question | Authoritative home for the **answer** | Index's responsibility |
|---|---|---|
| What are we building and why? | [Product objective](CONCEPT.md), [original multi-system composition contract](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636), [North Star](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/668) | Locate intent, do not rephrase it as a competing specification |
| How does Agent Memory reason about memory? | [Canonical architecture thesis](AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md), [component model](11-component-architecture.md) and [composition boundaries](13-system-composition-boundaries.md) | Assign architectural topics to shelves |
| Which architectural decisions are accepted? | The **individual** [ADR](adr/README.md) and its status; the ADR directory index routes to it | Never award acceptance in this catalog |
| What is this repository versus future products? | [Repository operating model](REPOSITORY_OPERATING_MODEL.md), [five-layer project model](AGENT_MEMORY_PROJECT_MODEL.md), [#565 ruling](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/565) | Preserve three operational roles versus five project layers |
| What must a consumer/runtime implement? | [Public contract](44-public-api-contract.md), [schemas](../schemas/), exact [source code](../reference/agentmem_ref/), accepted ADRs | Never treat design intent as shipped behavior |
| Which storage/representation is actually qualified? | [Substrate inventory](43-substrate-inventory-and-maturity.md) and exact accepted evidence | Never turn a prototype or module into a qualified substrate |
| Where is the current release and implementation state? | Live [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410) for release decisions, the [baseline register](../reports/runtime/baseline-register.json) for runtime identity, [Backlog](BACKLOG.md); [System State](SYSTEM_STATE.md) is a pinned snapshot pointing to them | No replicated version strings, readiness flags or active issue table |
| What do benchmarks prove? | [Benchmarks](../BENCHMARKS.md), [generated dashboard](../reports/benchmarks/dashboard/current.md), exact run artifacts | No copied scores or cross-harness comparisons |
| How did a decision or failure evolve? | [Meta Ledger](META_LEDGER.md), [Shadow Genome](SHADOW_GENOME.md), [Process Shadow Genome](PROCESS_SHADOW_GENOME.md), archived plans and pinned evidence | Discover lineage without granting old notes current authority |

**Precedence by subject, not by filename:** an Accepted ADR governs *doctrine*, but does not make code qualified; a versioned schema governs the interface at its declared version; code and independently accepted evidence decide *implemented versus qualified*; a live issue owns the unfinished task. When those disagree, report a drift defect and reconcile the owning surface through its normal decision/qualification process. An impressive filename containing `CANONICAL` is not a universal override.

## 2. Architecture shelf catalog

These letter IDs are **virtual library shelves**, not additional filesystem directories, ADR numbers or runtime layers. Every numbered `docs/NN-*.md` file at the pinned baseline is assigned exactly **one** shelf below. Reused numbers (47, 50, 52 and 66) remain distinct paths; do not rename files just to make numbering prettier.

### F · Foundations, theory and architecture

**Content owner(s):** [Canonical architecture thesis](AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md) and [component architecture](11-component-architecture.md); accepted decisions in [ADRs](adr/README.md).

**Numbered-document register (11):** [00-glossary](00-glossary.md) · [01-layer-model](01-layer-model.md) · [10-memory-unit-examples](10-memory-unit-examples.md) · [11-component-architecture](11-component-architecture.md) · [12-concept-segmentation-matrix](12-concept-segmentation-matrix.md) · [13-system-composition-boundaries](13-system-composition-boundaries.md) · [20-memory-foundations-across-scales](20-memory-foundations-across-scales.md) · [22-agentic-memory-theory-and-development](22-agentic-memory-theory-and-development.md) · [24-determinism-probability-and-governed-uncertainty](24-determinism-probability-and-governed-uncertainty.md) · [42-governed-mutable-memory-fabric](42-governed-mutable-memory-fabric.md) · [52-governed-cognitive-classification](52-governed-cognitive-classification.md).

### G · Governance, evidence and decision authority

**Content owner(s):** [PAMA doctrine](pama/README.md), [PAMA decision table](33-pama-decision-table.md), [accepted ADRs](adr/README.md).

**Numbered-document register (8):** [04-governance-and-pama](04-governance-and-pama.md) · [16-source-trust-and-reputation](16-source-trust-and-reputation.md) · [17-conflict-resolution-engine](17-conflict-resolution-engine.md) · [25-governed-uncertainty-documentation-conformance-audit](25-governed-uncertainty-documentation-conformance-audit.md) · [33-pama-decision-table](33-pama-decision-table.md) · [36-policy-as-memory](36-policy-as-memory.md) · [38-human-correction-ux-contract](38-human-correction-ux-contract.md) · [62-lessons-learned-evidence-and-currentness](62-lessons-learned-evidence-and-currentness.md).

### L · Memory lifecycle, revision and time

**Content owner(s):** [Lifecycle state model](02-lifecycle-state-machine.md), [forgetting contract](28-retention-deletion-and-tombstones.md), accepted ADRs.

**Numbered-document register (10):** [02-lifecycle-state-machine](02-lifecycle-state-machine.md) · [03-scoring-and-decay](03-scoring-and-decay.md) · [18-temporal-causality-layer](18-temporal-causality-layer.md) · [21-forgetting-consolidation-and-memory-metabolism](21-forgetting-consolidation-and-memory-metabolism.md) · [27-schema-registry-and-type-evolution](27-schema-registry-and-type-evolution.md) · [28-retention-deletion-and-tombstones](28-retention-deletion-and-tombstones.md) · [31-recovery-rollback-and-replay](31-recovery-rollback-and-replay.md) · [57-query-conditioned-applicability](57-query-conditioned-applicability.md) · [58-historical-evidence-admission](58-historical-evidence-admission.md) · [61-write-time-proposition-semantics](61-write-time-proposition-semantics.md).

### R · Retrieval, cognition and context use

**Content owner(s):** [Recall planner](26-governed-recall-planner.md), [public API contract](44-public-api-contract.md), and implementation under `reference/agentmem_ref/`.

**Numbered-document register (4):** [09-calibration-protocol](09-calibration-protocol.md) · [26-governed-recall-planner](26-governed-recall-planner.md) · [50-keyed-rebinding-currentness-benchmark](50-keyed-rebinding-currentness-benchmark.md) · [73-failure-memory-recall-shadow](73-failure-memory-recall-shadow.md).

### S · Security, privacy, scope and auditability

**Content owner(s):** [Threat model](15-memory-threat-model.md), [scope rules](29-actor-scope-consent-and-tenancy.md), [isolation](41-memory-isolation-domains-and-governed-crossing.md), accepted ADRs.

**Numbered-document register (5):** [15-memory-threat-model](15-memory-threat-model.md) · [19-privacy-and-sensitivity-classifier](19-privacy-and-sensitivity-classifier.md) · [29-actor-scope-consent-and-tenancy](29-actor-scope-consent-and-tenancy.md) · [30-memory-observability-and-audit-events](30-memory-observability-and-audit-events.md) · [41-memory-isolation-domains-and-governed-crossing](41-memory-isolation-domains-and-governed-crossing.md).

### I · Runtime composition, persistence and API

**Content owner(s):** [Substrate maturity](43-substrate-inventory-and-maturity.md), [public API contract](44-public-api-contract.md), implementation + `schemas/`; [baseline register](../reports/runtime/baseline-register.json).

**Numbered-document register (15):** [14 retired scope proposals (historical)](14-expanded-scope-recommendations.md) · [39-implementation-ownership-map](39-implementation-ownership-map.md) · [43-substrate-inventory-and-maturity](43-substrate-inventory-and-maturity.md) · [44-public-api-contract](44-public-api-contract.md) · [45-agent-memory-rc1-implementation-profile](45-agent-memory-rc1-implementation-profile.md) · [46-state-checkpoint-contract](46-state-checkpoint-contract.md) · [47-developer-facade-and-local-open-path](47-developer-facade-and-local-open-path.md) · [47-transactional-checkpoint-generations](47-transactional-checkpoint-generations.md) · [48-rc-cognitive-memory-lifecycle-evidence](48-rc-cognitive-memory-lifecycle-evidence.md) · [49-rc1-evidence-closeout](49-rc1-evidence-closeout.md) · [52-harvest-closeout-final](52-harvest-closeout-final.md) · [63-post-550-architecture-reconciliation](63-post-550-architecture-reconciliation.md) · [66 Rust-shadow snapshot (revision-bound)](66-rust-runtime-qualification-current-state.md) · [67-runtime-baseline-succession](67-runtime-baseline-succession.md) · [68-baseline-first-complete-architecture-execution](68-baseline-first-complete-architecture-execution.md).

### E · Evaluation, qualifications and benchmark interpretation

**Content owner(s):** [Benchmark entry](../BENCHMARKS.md), [canonical generated dashboard](../reports/benchmarks/dashboard/current.md), frozen manifests and [Gauntlet contract](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md).

**Numbered-document register (15):** [06-conformance-test-plan](06-conformance-test-plan.md) · [32-memory-quality-metrics](32-memory-quality-metrics.md) · [50-swe-contextbench-comparison-harness](50-swe-contextbench-comparison-harness.md) · [51-benchmark-integrity-mutation-probes](51-benchmark-integrity-mutation-probes.md) · [53-memory-evaluation-subsystem](53-memory-evaluation-subsystem.md) · [54-memory-evaluation-cli](54-memory-evaluation-cli.md) · [55-memory-evaluation-scorecards](55-memory-evaluation-scorecards.md) · [56-benchmark-gauntlet-remediation-evidence](56-benchmark-gauntlet-remediation-evidence.md) · [59-orthogonal-temporal-gauntlet-qualification](59-orthogonal-temporal-gauntlet-qualification.md) · [60-temporal-currentness-qualification-gauntlet](60-temporal-currentness-qualification-gauntlet.md) · [64 governance reconciliation (historical)](64-current-governance-and-benchmark-dashboard.md) · [65 AMB profile (revision-bound)](65-independent-amb-competitive-profile.md) · [66 pre-1.0 snapshot (historical)](66-pre-1.0-maturity-and-runtime-qualification.md) · [69-agentmembench-mesa-formal-baseline](69-agentmembench-mesa-formal-baseline.md) · [72-benchmark-neutral-remediation-loop](72-benchmark-neutral-remediation-loop.md).

### X · Interoperability, intellectual lineage and system economics

**Content owner(s):** [Implementation ancestry map](05-repo-implementation-map.md), [ownership map](39-implementation-ownership-map.md), [source rights](SOURCE_RIGHTS_POLICY.md).

**Numbered-document register (10):** [05-repo-implementation-map](05-repo-implementation-map.md) · [07 retired integration roadmap (historical)](07-integration-roadmap.md) · [08-source-material-index](08-source-material-index.md) · [23-research-bibliography](23-research-bibliography.md) · [34-adapter-contracts](34-adapter-contracts.md) · [35-interoperability-profiles](35-interoperability-profiles.md) · [37-memory-economics-and-budget-policy](37-memory-economics-and-budget-policy.md) · [40-aligned-projects-and-intellectual-lineage](40-aligned-projects-and-intellectual-lineage.md) · [74-github-actions-cost-and-qualification](74-github-actions-cost-and-qualification.md) · [75-finops-protected-artifacts-and-closeout-review](75-finops-protected-artifacts-and-closeout-review.md).

## 3. Other architectural collections and their boundaries

| Collection | Use it for | Authority/retention rule |
|---|---|---|
| [ADR index](adr/README.md) / `docs/adr/ADR-*.md` | Decision proposals, accepted doctrine and supersession | Individual ADR status governs; proposed != accepted; historical ADRs stay addressable |
| [PRD index](prd/README.md) / `docs/prd/` | Product requirements and acceptance intent | Draft requirements never establish runtime qualification |
| [RFC index](rfcs/README.md) / `docs/rfcs/` | Contested alternatives, experiments and large implementation proposals | An RFC never silently amends an accepted ADR |
| [PAMA doctrine](pama/README.md) / `docs/pama/` | Mutation authority and its required guards | PAMA's accepted ADRs and executable policy are the respective doctrine/implementation owners |
| `docs/policies/` and `docs/profiles/` | Bounded policies, qualified profiles and declared exceptions | Each policy/profile states its own scope and maturity |
| [Memory-architecture explorations](explorations/memory-architectures/README.md), [field claims](explorations/field-claims/README.md) | Research, external influences, alternative mechanisms | Evidence and hypotheses, not active doctrine by default |
| `docs/programs/`, `docs/audits/`, `docs/research/`, `docs/ecosystem/` | Programs, audit trails, research and ecosystem material | Revision-bound evidence, not an automatically live architecture source |
| `docs/future/` and `docs/templates/` | Future-roadmap proposals and document templates | Neither grants an acceptance nor a present-day feature claim |
| `docs/plan-*.md`, `docs/research-brief-*.md` | Historical or explicitly active *issue-bound* implementation planning | Check the live issue/PR before following; do not rewrite frozen plans to update today |
| `reference/`, `schemas/`, `fixtures/`, `reports/` | Executable behavior, machine contracts, tests and independent results | These are **not** narrative architecture shelves. Preserve exact revisions and evidence |
| `.qor/roadmaps/`, `docs/META_LEDGER.md`, `docs/SHADOW_GENOME.md` | Governed development history and learned failure modes | Protect immutable/append-only historical state; no bulk reorganizations |

### Non-numbered entry points and special-purpose documents

| Kind | Registered location | How to use it |
|---|---|---|
| Product objective | [CONCEPT](CONCEPT.md) | Definition of intended product, not a release ledger |
| Governing architectural narrative | [Canonical Architecture](AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md) | Explain design; ADRs own accepted individual decisions |
| Three operational repository functions | [Repository Operating Model](REPOSITORY_OPERATING_MODEL.md) | Repository role and change classification |
| Five-layer project/product model | [Project Model](AGENT_MEMORY_PROJECT_MODEL.md) | Project partition and future product boundary, subject to #565 |
| Historical genesis plan | [Architecture Plan](ARCHITECTURE_PLAN.md) | **Historical blueprint**; tree/version claims are not current |
| Current navigation (public audiences) | [Documentation README](README.md) | Public entry navigation should link *here*, not duplicate this catalog |
| Repository implementation state | [System State](SYSTEM_STATE.md), [Feature Index](FEATURE_INDEX.md) | Revision-bound snapshots; source and accepted qualification take precedence |
| Governance/progress navigation | [Governance Index](GOVERNANCE_INDEX.md), [Backlog](BACKLOG.md) | Governance tiers and work queue only; no separate architecture catalog |
| Runtime consumer guidance | [Configuration](CONFIGURATION.md), [Contributor Architecture](CONTRIBUTOR_ARCHITECTURE.md) | Operating instructions / contributor conventions |
| Benchmark/evidence navigation | [Coverage Atlas](BENCHMARK_COVERAGE_ATLAS.md), [Evidence Console Catalog](benchmark-evidence-console-catalog.md) | Coverage or console design, not numeric score truth |
| Gauntlet contracts and guidance | [System Adapter Contract](GAUNTLET_SYSTEM_ADAPTER_CONTRACT.md), [Orchestration](GAUNTLET_ORCHESTRATION.md), [Governance Specification](GOVERNANCE_GAUNTLET_SPECIFICATION.md), [Governance Alpha](GOVERNANCE_GAUNTLET_ALPHA.md), [External Contestant Quickstart](GAUNTLET_EXTERNAL_CONTESTANT_QUICKSTART.md) | Independent evaluator/adapter contracts; no memory runtime authority |
| Execution and external qualification history | [Retired Gauntlet staging plan](GAUNTLET_EXECUTION_ROADMAP.md), [External Qualification](GAUNTLET_EXTERNAL_BENCHMARK_QUALIFICATION_2026-09-26.md) | Revision-bound plans/evidence, not automatic active work |
| Supporting decision history | [Source Rights](SOURCE_RIGHTS_POLICY.md), [Runtime Identity Brief](RUNTIME_IDENTITY_NAMING_BRIEF.md), [Research Brief](RESEARCH_BRIEF.md) | Respective licensing, proposed identity and research context |
| Persistent failure lessons | [Meta Ledger](META_LEDGER.md), [Shadow Genome](SHADOW_GENOME.md), [Process Shadow Genome](PROCESS_SHADOW_GENOME.md) | Never rewrite evidence merely to reorganize docs |

## 4. Filing and editing protocol

1. **Locate the shelf here.** Name the exact existing question and owning document. If one exists, edit it or open its governing issue; **do not publish a second document answering the same question**.
2. **Classify the proposed change:** doctrine/ADR; product requirement/PRD; RFC/hypothesis; contract/schema; implementation; qualification/evidence; reference explanation; or historical plan. Do not promote by renaming.
3. **State the delta at its owner.** New doctrines require a versioned ADR decision; new runtime behavior requires code, tests and qualification. A README, summary, dashboard or this index cannot approve either.
4. **Register new architectural documents in this index in the same changeset**, with exactly one shelf and the stable linked path. If no owner exists, explicitly nominate one before creating a new file; cross-links may point to it, but copied normative text must not.
5. **On a move or supersession**, preserve old paths through an approved redirect/stub or auditable link map, update incoming references, and keep frozen evidence bytes unmodified. QOR Organize approval is required for moves.
6. **On conflicting claims**, log the two source paths, the subject area and exact revisions; decide which owner controls that claim. Repair the subordinate/stale text with a pointer. Do **not** resolve disagreement by creating yet another reconciliation summary.
7. **Verify before merge** with the repository's local Markdown/path validators and an independent five-question cold-start exercise. No hosted CI is required for this editorial test, and tests not run must be labeled NOT RUN.

### Claim ownership declarations (curated, not a second status register)

The IDs below identify **questions and their sole normative owner**, not the answers at today's revision. A derived page may cite the owner but must not become a second source of acceptance. The validator reads only rows between the markers. It checks unique IDs, known classes and tracked Markdown/JSON owners or collections (a trailing `/` names a collection whose members each own their entry). Only delivery claims may name an issue, they must, and the only accepted issue is #410. It pins the owner-ruled claims (release integration to #410, runtime identity to the baseline register, benchmark admission to the descriptors). It refuses the navigation, planning, projection and history surfaces filed in §3, and any owner whose title, leading Status/Purpose clause or `Authority effect: none` line demotes it. It does **not** guess semantic contradictions from arbitrary prose.

<!-- BEGIN CLAIM OWNERS -->
| Claim ID | Class | Primary owner |
|---|---|---|
| public-api-contract | contract | docs/44-public-api-contract.md |
| canonical-substrate-maturity | qualification | docs/43-substrate-inventory-and-maturity.md |
| runtime-baseline-identity | baseline | reports/runtime/baseline-register.json |
| benchmark-admission | qualification | reference/agentmem_ref/evaluation/integrations/ |
| benchmark-measured-outcomes | evidence | reports/benchmarks/dashboard/current.md |
| architectural-decision-status | doctrine | docs/adr/ |
| roadmap-work-queue | roadmap | docs/BACKLOG.md |
| release-integration-status | delivery | #410 |
<!-- END CLAIM OWNERS -->

**Release-integration-status is owned by live [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410)**; [System State](SYSTEM_STATE.md) is only a revision-bound pointer to it, verified against exact code and baseline evidence. Each ADR file owns its own status; the [ADR index](adr/README.md) routes to them. Benchmark admission is owned by the committed integration descriptors and their validator, not by the dashboard or the [Atlas](BENCHMARK_COVERAGE_ATLAS.md). On disputed ownership, record both sources in the governing issue and leave the declaration unchanged until the owner rules; do not crown the newer document. Before any supersession, record the old owner/revision, new owner/revision, effective acceptance event, and subordinate backlinks.

## 5. Cold-start path for agents

From [this catalog](ARCHITECTURE_INDEX.md), an agent should be able to answer, with primary-source pointers:

1. Product objective and original **hierarchical, heterogeneous, multi-system memory** scope? → [CONCEPT](CONCEPT.md), [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636).
2. Which doctrine and consequences are permitted? → [ADR index](adr/README.md), [PAMA](pama/README.md), [system boundaries](13-system-composition-boundaries.md).
3. What can I run **today**? → [System State](SYSTEM_STATE.md), [API](44-public-api-contract.md), [substrate inventory](43-substrate-inventory-and-maturity.md), exact code/evidence.
4. What is not implemented/qualified? → [substrate inventory](43-substrate-inventory-and-maturity.md), [#410](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/410), [#636](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/636).
5. What should be changed next, and where? → [Backlog](BACKLOG.md), live issue/PR owner, the shelf and owning contract above.

**Maintenance metric:** this index is healthy when newly created architecture documents have an assigned shelf, no two *current* documents claim ownership of the same rule, and no mutable fact (version, acceptance, issue state, benchmark score) is maintained here. The objective is **fewer competing truths**, not more indexed prose.
