<p align="center">
  <img src="assets/brand/agent-memory-readme-banner.png" alt="Agent Memory: governed memory architecture for AI agents, shown with a layered memory stack, connected nodes, and a cyan inference spark." width="100%">
</p>

<div align="center">

# 01010001 Agent Memory

<p><sub><strong>Q Agent Memory</strong></sub></p>

### Governed persistent cognition for autonomous and agentic systems

Multiple memory forms. Shared identity and evidence. Explicit lifecycle and recall governance. Probabilistic inference without probabilistic authority.

[![Validate Doctrine Evidence](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/workflows/validate-doctrine-evidence.yml/badge.svg)](https://github.com/MythologIQ-Labs-LLC/agent-memory/actions/workflows/validate-doctrine-evidence.yml)
![Architecture](https://img.shields.io/badge/Architecture-Governed%20Cognitive%20Framework-334155)
![Release](https://img.shields.io/badge/Release-Pre--RC-b45309)
[![ADRs](https://img.shields.io/badge/ADRs-Canonical%20Index-2563eb)](docs/adr/README.md)
[![License](https://img.shields.io/badge/License-Apache--2.0-0b7285)](LICENSE)

**[Documentation](docs/README.md)** · **[RC1 profile](docs/45-agent-memory-rc1-implementation-profile.md)** · **[PAMA](docs/pama/README.md)** · **[Architecture decisions](docs/adr/README.md)** · **[Substrate inventory](docs/43-substrate-inventory-and-maturity.md)** · **[Contributing](CONTRIBUTING.md)**

</div>

---

> [!IMPORTANT]
> **Current status: strong executable reference runtime, pre-RC.**
>
> Agent Memory is no longer only an architecture-and-documentation project. The repository contains governed semantic, epistemic, procedural, predictive, cognitive-mesh, persistence, correction, deletion, recall, provider-qualification, and Code Reality Graph execution paths. The reference runtime is restart-safe at its declared boundary and is protected by a large conformance/evidence suite.
>
> It is **not** yet a production 1.0 system and **not** yet RC1. There are currently **zero production-qualified canonical substrates**. Production substrate qualification is tracked by #427; RC composition and release gates are tracked by #410.

## What Agent Memory is

**Agentic memory is retained state that can alter an agent's future interpretation, reasoning, planning, tool use, action, or adaptation across a meaningful persistence boundary.**

That definition is intentionally larger than RAG, vector search, a graph database, a Markdown file, a conversation history, or any single memory subsystem.

Agent Memory is one governed architecture in which specialized memory responsibilities can coexist without being flattened into one universal record type:

```text
experience / observation
        |
        v
+----------------------- Cognitive Plane -----------------------+
| Cognitive Mesh                                               |
| working memory / attention                                   |
| cognitive metabolism                                         |
| consolidation / abstraction                                  |
| epistemic, semantic, procedural and predictive memory        |
+---------------------------------------------------------------+
        |
        +---------------- Reality Plane ------------------------+
        | Reality Graphs: code, task, environment, social, ...  |
        +-------------------------------------------------------+
        |
        +---------------- Authority Plane ----------------------+
          PAMA
          recall admission
          certification / durable commit
          scope / privacy / isolation
          correction / supersession
          deletion / forgetting
          inheritance / crossing

Cross-cutting: identity, evidence, provenance, calibration, conformance
```

The canonical architecture is established by **[ADR-035](docs/adr/ADR-035-agent-memory-is-a-governed-cognitive-framework.md)**. The important consequence is simple:

> A substrate is not the memory system. A retrieval strategy is not the memory system. A graph is not the memory system. They are bounded participants in Agent Memory.

---

## Governing doctrine

The architecture separates uncertain inference from durable consequence:

> **Probabilistic epistemics. Governed consequences.**
>
> **Uncertainty may propose. Authority constrains.**

Two invariants recur throughout the implementation:

```text
selected_action ∈ permitted_action_set
estimator_output != authority
```

A model or controller may estimate relevance, confidence, contradiction, sensitivity, staleness, utility, risk, relation strength, or retrieval value. Those estimates do not create permission.

### Proportional Adaptive Mutation Authority

**PAMA** is Agent Memory's native mutation-authority doctrine.

```text
adaptation != authority
memory != procedure
procedure != permission
permission != governance
```

PAMA evaluates the consequence of a proposed mutation across distinct dimensions rather than collapsing governance into one confidence score:

- target class `M0-M5`
- lifecycle strength
- requested operation
- downstream authority `A0-A5`
- reversibility, evidence, scope, risk, review and verification state

See **[PAMA](docs/pama/README.md)**, **[Governance and PAMA](docs/04-governance-and-pama.md)**, and **[PAMA Decision Table](docs/33-pama-decision-table.md)**.

---

## What is implemented today

The repository is deliberately strict about the difference between **architecture**, **implementation**, **runtime evidence**, and **production maturity**.

| Surface | Current state |
|---|---|
| Canonical semantic memory | Executable governed reference runtime |
| Epistemic belief memory | Executable claims/beliefs/hypotheses with confidence, directional evidence, dispute and retraction lineage |
| Procedural / skill memory | Executable governed procedure/skill lifecycle with action-authority separation |
| Predictive / counterfactual memory | Executable governed predictive memory surface |
| Cognitive Mesh | Executable bounded ADR-035 composition seam |
| Semantic + epistemic composition | Restart-safe RC1 reference slice; shared provenance with distinct memory identities and type-preserving recall |
| Derived projections | Executable freshness, staleness, residue and rebuild governance |
| Governed recall | Scope/tenant/project/currentness admission with decision evidence |
| Correction / supersession | Executable and restart-safe in the reference profile |
| Deletion / tombstones | Executable, evidence-bearing and restart-safe in the reference profile |
| Shared-domain / crossing authority | Governed mutation paths; RC-relevant authority gaps from #364 are closed |
| Code Reality Graph | Agent Memory-owned `crg/` package with CodeGenome profile/integration modules; not a universal graph ontology |
| Capability qualification | Executable provider qualification/substitution framework |
| Hindsight / MemOS | Evidence-proven for bounded `resource_artifact_memory`; **not canonical substrates** |
| Production canonical substrate | **None qualified yet**; tracked by #427 |
| Multi-route recall planner | Architecture defined; RC implementation still open |
| Developer `AgentMemory.open()/remember()/...` facade | RC implementation still open |
| LoCoMo / LongMemEval RC baseline | Planned RC evidence work; not yet the release benchmark package |

### The first composed multi-memory slice

The RC path now composes semantic and epistemic memory through one restart-safe runtime. One source experience/evidence reference may lead to two separately governed consequences:

```text
experience:deploy-observation-001
        |
        +--> semantic memory
        |      release_branch = main
        |
        +--> epistemic memory
               "main is likely safe for staged deployment"
               confidence = 0.8
               status = active | disputed | retracted
```

Those are **not duplicate copies of one string**. They have different identity, semantics, lifecycle and recall behavior. A high-confidence epistemic revision cannot overwrite semantic truth or bypass review. A refused epistemic revision does not roll back an independently committed semantic fact.

This is the architectural point of Agent Memory made executable: multiple memory responsibilities participate in one governed system without pretending they are the same thing.

---

## Restart-safe reference persistence

The reference persistence profile has moved substantially beyond a process-local demo.

The current reference path includes:

- explicit state ownership contracts instead of runtime private-field scraping
- substrate-owned identifier progress
- governed-adapter-owned governance state
- rejection/readmission recovery
- transactional checkpoint generations
- compare-and-commit stale-writer protection
- crash-releasing POSIX advisory locking
- hash-chained generation journal
- fail-closed torn-write / rollback detection within the local checkpoint boundary
- governed schema/profile migration
- crash recovery and governed rollback semantics
- public checkpoint transaction support
- atomic auxiliary-state composition through the same generation boundary
- restart rules for projection declarations, write claims, telemetry, and composed epistemic state

See **[State checkpoint contract](docs/46-state-checkpoint-contract.md)**.

### What this does not mean

`reference_file_checkpoint_v1` is a **reference durability profile**, not a production database qualification.

The in-memory canonical substrate can be checkpointed and recovered correctly under that profile. That proves Agent Memory's persistence semantics. It does not prove that the in-memory substrate is an appropriate production deployment choice.

Likewise:

```text
Postgres underneath a provider != Agent Memory Postgres substrate
SQLite underneath a plugin      != Agent Memory SQLite substrate
Graph database                   != automatically qualified canonical graph memory
```

Production canonical-substrate qualification is intentionally separate and is tracked by **#427**.

---

## Substrates, memory implementations, and providers are different things

This distinction prevents capability maturity from spreading by association, one of software architecture's more persistent communicable diseases.

| Kind | Meaning | Current examples |
|---|---|---|
| **Canonical substrate** | Implements the retained fact/episode `TemporalGraphPort` contract | `InMemoryTemporalGraph`, experimental `GraphitiSubstrate` |
| **Memory implementation** | Governed semantic behavior above the substrate | epistemic, procedural, predictive, semantic memory |
| **Capability provider** | Supplies one versioned capability under a qualification contract | Hindsight, MemOS |
| **Reality module** | Supplies bounded reality evidence/relations | Code Reality Graph / CodeGenome profile |
| **Persistence mechanism** | Storage technology used underneath something else | files, SQLite, Postgres, graph databases, object stores |

Current substrate maturity is maintained in **[docs/43-substrate-inventory-and-maturity.md](docs/43-substrate-inventory-and-maturity.md)**.

The existing `GraphitiSubstrate` is an experimental direct-write adapter over deprecated Kuzu. It is useful evidence, not production qualification. A future Graphiti production profile would need to use an exact supported backend and earn restart, scope, deletion, recovery and operational evidence on that exact profile.

---

## Repository structure

The reference package is no longer the old flat 100+ module namespace. Package placement is enforced by `scripts/restructure_package.py` and tested in CI.

```text
reference/agentmem_ref/
├── core/       PAMA, receipts, evidence, verification, contextual recall
├── state/      canonical substrate, graph driver, projections, residue
├── contracts/  capability declarations, qualification, substitution
├── runtime/    governed adapter, restart, transactions, composition, CLI
├── memory/     epistemic, procedural, predictive, crossing, temporal, etc.
├── api/        versioned public contract and stage surface
├── crg/        Agent Memory Code Reality Graph / CodeGenome profile
└── harness/    conformance, adversarial evidence, comparators, benchmarks
```

Compatibility aliases preserve the historical `agentmem_ref.<module>` import paths while the real modules live in their architecture layers.

---

## Public contract versus developer facade

Agent Memory already has a versioned public contract. **[Public API Contract 1.2](docs/44-public-api-contract.md)** separates stages such as proposal, approval, commit, recall, forgetting, history, posture, action authorization and execution evidence.

What Agent Memory does **not** yet have is the small ergonomic product facade intended for RC1:

```python
# Target RC ergonomics, not a claim that this facade exists on main today.
memory = AgentMemory.open("./agent-state")
memory.remember(...)
memory.recall(...)
memory.correct(...)
memory.forget(...)
memory.history(...)
memory.posture(...)
```

That facade must wrap the canonical contract. It may not become a friendlier bypass around PAMA, recall admission, scope, evidence, or lifecycle rules.

---

## RC1 status

RC1 is tracked by **#410** and **[docs/45-agent-memory-rc1-implementation-profile.md](docs/45-agent-memory-rc1-implementation-profile.md)**.

| RC slice | Status |
|---|---|
| RC-0 Canonical ADR-035 architecture reconciliation | **Complete** |
| RC-1 Restart-safe reference semantics | **Complete at the reference boundary** |
| RC-1 Production canonical substrate qualification | **Open: #427** |
| RC-2 Multi-memory composition | **First restart-safe semantic + epistemic slice implemented** |
| RC-3 Multi-route candidate retrieval + governed recall | **Open** |
| RC-4 Ergonomic developer facade | **Open** |
| RC-5 Recall/crossing authority seams | **Complete** |
| RC-6 End-to-end cognitive-memory release scenario | **Open** |
| RC-7 Release benchmark/evidence package | **Partial** |

**Do not cut RC1 yet.**

The remaining work is now primarily product composition and release evidence rather than architecture invention:

```text
production substrate qualification (#427)
        -> multi-route recall
        -> developer facade
        -> end-to-end RC scenario
        -> reproducible quality/performance/governance benchmark package
        -> RC1
```

Jev-Mem and other external memory systems are useful comparative pressure and benchmark targets. They do not define Agent Memory's architecture, and Jev is not an RC dependency.

A Rust rewrite is also **not** an RC prerequisite. Profile the coherent runtime first; move only evidenced hot/system-critical kernels behind existing contracts if the measurements justify it.

---

## Recall is governed separately from retrieval

Agent Memory treats candidate generation and context admission as different decisions:

```text
query / task
  -> requester + purpose + scope
  -> candidate generation
  -> normalization
  -> governed recall admission
  -> ranking among admitted candidates
  -> composition-risk checks
  -> context assembly
  -> receipt / explanation
```

The rule is:

> **High relevance does not imply authorized recall.**

Candidate generation may be lexical, exact, vector, graph, temporal, procedural, predictive, source-aware, or eventually controlled by a cheap adaptive/System-One planner. None of those mechanisms gains scope, privacy, tenancy or durable-mutation authority by being good at ranking.

See **[Governed Recall Planner](docs/26-governed-recall-planner.md)**.

---

## Lifecycle

The architecture distinguishes proposal from durable consequence and current truth from retained history.

Representative lifecycle states include:

```text
Transient
  -> Observed
  -> Linked
  -> Reinforced
  -> Candidate
  -> Pending Verification
  -> Crystallized
  -> Operationally Reused
  -> Stale
  -> Disputed
  -> Corrected
  -> Reconciled
  -> Pruned
```

A repeated or high-confidence proposal cannot authorize its own transition. Correction preserves history. Deletion/forgetting must account for derived residue rather than merely removing one primary row.

See **[Lifecycle State Machine](docs/02-lifecycle-state-machine.md)** and **[Retention, deletion and tombstones](docs/28-retention-deletion-and-tombstones.md)**.

---

## Security and privacy posture

Agent Memory treats memory as a security boundary because retained state changes future behavior.

The repository has explicit doctrine and executable pressure tests for:

- tenant / project / isolation boundaries
- source and evidence provenance
- unsafe composition
- authority laundering
- stale authorization and replay
- rejected-value readmission
- disputed/superseded currentness
- deletion completeness and derived residue
- shared-domain membership and governed crossing
- sensitivity / destination handling
- provider-native confidence or graph output attempting to become authority

Start with **[Memory Threat Model](docs/15-memory-threat-model.md)**, **[Privacy and Sensitivity](docs/19-privacy-and-sensitivity-classifier.md)**, and **[Isolation Domains and Governed Crossing](docs/41-memory-isolation-domains-and-governed-crossing.md)**.

---

## Run the reference evidence locally

The repository is installable as a Python package and exposes the current CLI/doctor surface:

```bash
python -m pip install .
agent-memory --help
```

For the pinned reference validation environment:

```bash
python -m pip install -r reference/requirements.txt
python scripts/validate_fixtures.py fixtures
python scripts/validate_schemas.py
python scripts/validate_doctrine_boundaries.py
python -m unittest discover -s reference/tests -t reference
```

Passing these checks proves the boundaries the fixtures and tests actually exercise. It does not magically confer production maturity on every declared component. The repository is quite intentionally rude about that distinction.

See **[Configuration](docs/CONFIGURATION.md)** and **[reference/README.md](reference/README.md)** for the executable evidence environment.

---

## Start here

| Goal | Read first |
|---|---|
| Understand the architecture | [Layer model](docs/01-layer-model.md), [Component architecture](docs/11-component-architecture.md), [ADR-035](docs/adr/ADR-035-agent-memory-is-a-governed-cognitive-framework.md) |
| Understand authority | [PAMA](docs/pama/README.md), [Governance and PAMA](docs/04-governance-and-pama.md) |
| Understand recall | [Governed Recall Planner](docs/26-governed-recall-planner.md), [Adapter contracts](docs/34-adapter-contracts.md) |
| Understand persistence | [State checkpoint contract](docs/46-state-checkpoint-contract.md), [Substrate inventory](docs/43-substrate-inventory-and-maturity.md) |
| Understand RC1 | [RC1 implementation profile](docs/45-agent-memory-rc1-implementation-profile.md), issue #410 |
| Review security/privacy | [Threat model](docs/15-memory-threat-model.md), [Privacy](docs/19-privacy-and-sensitivity-classifier.md), [Isolation](docs/41-memory-isolation-domains-and-governed-crossing.md) |
| Evaluate conformance | [Conformance plan](docs/06-conformance-test-plan.md), [Calibration](docs/09-calibration-protocol.md), [Fixtures](fixtures/) |
| Research the field | [Research bibliography](docs/23-research-bibliography.md), [Aligned projects](docs/40-aligned-projects-and-intellectual-lineage.md) |

The full documentation map lives in **[docs/README.md](docs/README.md)**.

---

## Ownership and external components

Agent Memory owns its architectural contracts. Same-owner projects such as CodeGenome and EvolveAI can contribute first-party implementation material without turning their original ontology into Agent Memory doctrine. See **[ADR-036](docs/adr/ADR-036-same-owner-components-are-first-party-modules.md)** and the **[implementation ownership map](docs/39-implementation-ownership-map.md)**.

Third-party systems remain third-party systems. Qualification records what exact capability, version, source-rights posture, state behavior and authority effect was actually proven.

In particular:

- CodeGenome material participates in the Agent Memory-owned **Code Reality Graph** module.
- EvolveAI material informs/implements bounded **Cognitive Metabolism** capabilities where adopted and evidenced.
- Hindsight and MemOS have bounded external capability qualifications with `authority_effect: none`.
- Graphiti remains an external substrate technology; the current Kuzu-backed driver is experimental evidence, not production qualification.

Provider popularity, benchmark quality, or storage durability does not create Agent Memory authority.

---

## What Agent Memory is not claiming

This repository does **not** currently claim:

- production 1.0 readiness
- RC1 readiness
- a production-qualified canonical substrate
- that every architecture module is equally mature
- that one benchmark proves overall memory quality
- that a graph, vector store, RAG pipeline, Markdown corpus, or LLM context window is sufficient memory by itself
- that estimator confidence is authorization
- that a provider's internal ontology becomes Agent Memory's ontology
- that Jev-Mem, Graphiti, Hindsight, MemOS, CodeGenome, EvolveAI, or any other component defines the architecture
- that Rust would automatically make the system better without profiling evidence

The goal is narrower and harder: **make persistent cognition useful without allowing retained state, retrieval scores, learned procedures, or adaptive controllers to quietly manufacture authority.**

---

## Contributing

Contributions are welcome when they preserve the architecture's evidence discipline.

Before adding a memory type, provider, substrate, benchmark, policy engine, or adaptive controller, read:

- **[CONTRIBUTING.md](CONTRIBUTING.md)**
- **[GOVERNANCE.md](GOVERNANCE.md)**
- **[SECURITY.md](SECURITY.md)**
- **[Evidence Promotion Policy](docs/policies/EVIDENCE_PROMOTION.md)**
- **[Source Rights Policy](docs/SOURCE_RIGHTS_POLICY.md)**

Do not promote a component because it is fashionable. Do not promote a benchmark because it is flattering. Do not promote an estimator because it sounds certain. Computers already have enough confidence problems inherited from humans.

## License

Apache License 2.0. See **[LICENSE](LICENSE)**.
