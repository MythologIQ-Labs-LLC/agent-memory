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
> Agent Memory is no longer only an architecture-and-documentation project. The repository contains governed semantic, epistemic, procedural, predictive, cognitive-mesh, persistence, correction, deletion, multi-route recall, provider-qualification, and Code Reality Graph execution paths. The reference runtime is restart-safe at its declared boundary and is protected by a large conformance/evidence suite.
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
| Deterministic multi-route recall | Lexical + exact logical-identity candidate routes; per-route provenance, deduplication, one governed admission boundary, admitted-only ranking |
| Correction / supersession | Executable and restart-safe in the reference profile |
| Deletion / tombstones | Executable, evidence-bearing and restart-safe in the reference profile |
| Shared-domain / crossing authority | Governed mutation paths; RC-relevant authority gaps from #364 are closed |
| Code Reality Graph | Agent Memory-owned `crg/` package with CodeGenome profile/integration modules; not a universal graph ontology |
| Capability qualification | Executable provider qualification/substitution framework |
| Hindsight / MemOS | Evidence-proven for bounded `resource_artifact_memory`; **not canonical substrates** |
| Production canonical substrate | **None qualified yet**; tracked by #427 |
| Vector / graph / adaptive recall routes | Not yet promoted into the RC runtime; provider evidence must earn each route |
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

### Deterministic multi-route recall

RC retrieval now separates **candidate discovery** from **recall admission**.

```text
query / recall intent
        |
        +--> lexical candidate route
        |
        +--> exact logical-identity route
                  |
                  v
        dedupe + route provenance
                  |
                  v
        one governed admission boundary
                  |
                  v
        deterministic ranking of admitted candidates only
```

A route score, exact-identity hit, or future model/controller judgment cannot repair a scope, currentness, dispute, tombstone, or isolation refusal. Retrieval decides where to look; governance decides what may influence active cognition.

The current RC route set is intentionally conservative. Vector, temporal, graph, and adaptive/System-One routes can plug into the same boundary later, but they must earn runtime qualification rather than becoming authoritative because they retrieve convincingly.

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
