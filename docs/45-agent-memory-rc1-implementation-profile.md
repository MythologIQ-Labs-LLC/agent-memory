# Agent Memory RC1 Implementation Profile

**Status:** implementation profile; tracked by issue #410

**Architectural authority:** Accepted ADR-035

**Public contract baseline:** Agent Memory API contract `1.2.0`

## Purpose

This profile defines the smallest release-candidate implementation that can truthfully present Agent Memory as one usable governed memory system.

It does **not** introduce a new architecture.

ADR-035 already establishes the system shape: bounded cognitive, reality, and authority modules participate in one governed persistent-cognition framework through the Cognitive Mesh. RC1 operationalizes that accepted architecture by composing implementation slices that already exist and closing only the gaps necessary for a usable runtime.

The release-candidate question is:

> Can a developer use one Agent Memory runtime in which multiple specialized memory forms and retrieval mechanisms cooperate without losing identity, provenance, lifecycle, scope, currentness, uncertainty, or authority semantics?

## Architectural invariants

RC1 inherits the existing invariants without weakening them for convenience:

```text
one Agent Memory architecture
    != one undifferentiated memory representation

shared Cognitive Mesh
    != universal truth store

memory representation
    != memory truth

candidate retrieval
    != recall admission

activation
    != authority

confidence / relevance / reinforcement
    != permission

retained procedure
    != execution authority

provider capability
    != Agent Memory consequence authority
```

A single experience or logical cognitive object may participate in more than one specialized memory responsibility. Those representations are not independent copies merely because their mechanisms differ. They must remain reconstructably related through Agent Memory identity, evidence, lifecycle, scope, and relationship semantics.

## Current implementation baseline

RC1 starts from existing executable work rather than rebuilding it.

| Responsibility | Current executable evidence | RC1 posture |
|---|---|---|
| Public governed stages | `reference/agentmem_ref/api/surface.py`, contract `1.2.0` | preserve; wrap ergonomically |
| Canonical semantic memory | `GovernedMemoryAdapter`, runtime composition | compose |
| Exact identity retrieval | current configured composition | compose |
| Cognitive Mesh | `reference/agentmem_ref/memory/cognitive_mesh.py` | compose |
| Epistemic belief memory | `reference/agentmem_ref/memory/epistemic_memory.py` | compose without truth collapse |
| Procedural / skill memory | `reference/agentmem_ref/memory/procedural_memory.py` | compose without execution-authority collapse |
| Predictive / counterfactual memory | `reference/agentmem_ref/memory/predictive_memory.py` | compose without observed-history collapse |
| Derived state / projection rebuild | `reference/agentmem_ref/runtime/runtime_composition.py` | preserve and generalize composition |
| Vector candidate retrieval | EvolveAI profile: bounded evidence-proven mock-backed route | eligible only within proven boundary |
| Temporal graph | EvolveAI profile: evidence proven | eligible within proven boundary |
| Graph traversal | EvolveAI direct-neighbor path; Code Reality Graph evidence separately exists | compose only where applicability is current |
| Consolidation / metabolism | EvolveAI REM-synthesis/lifecycle evidence | proposal-only consequence posture preserved |
| Negative / failure memory | EvolveAI evidence-proven provider capability | risk candidate only; no autonomous block |
| Governed recall admission | canonical adapter/contextual recall | preserve as authority boundary |
| Correction / supersession | governed adapter and specialized memory slices | make restart-safe and product-usable |
| Forgetting / tombstones | governed deletion path | make restart-safe and product-usable |
| History / receipts | public API and adapter evidence | expose through facade |
| Durable general runtime state | incomplete; issue #363 | RC blocker |
| Recall/crossing authority seam | incomplete; issue #364 | RC blocker |
| Developer-level unified facade | no general `AgentMemory` product facade | implement |
| Multi-route unified recall request | capability pieces exist; no general composed planner/fusion path | implement |
| End-to-end multi-memory product scenario | separate slices exist; no single RC proof | implement |

The matrix intentionally distinguishes implementation existence from usable composition. A capability does not become RC-ready merely because source code or a qualification record exists somewhere in the repository.

## RC1 system boundary

RC1 is a local/embeddable Agent Memory runtime with one supported initialization path and a small developer surface.

Conceptually:

```python
memory = AgentMemory.open(path, ...)

memory.remember(...)
memory.recall(...)
memory.correct(...)
memory.forget(...)
memory.history(...)
memory.posture(...)
```

Names remain implementation-level decisions until the surface lands. The contract requirements do not depend on those exact method names.

The facade sits **over** the public Agent Memory contract. It must not create a privileged path around proposal/decision/approval/commit, governed recall, forgetting, history, or PAMA.

For ordinary low-risk local use, the facade should provide explicit safe defaults so a caller does not need to construct internal policy dataclasses manually. Every consequential result remains inspectable as a governed result/receipt rather than collapsing to an opaque boolean.

## RC1 composition model

The release candidate must make the accepted architecture observable in one execution path.

```text
experience / observation
        |
        v
stable logical identity + evidence
        |
        v
Cognitive Mesh
        |
        +--> semantic/canonical representation
        +--> epistemic representation when applicable
        +--> procedural representation when applicable
        +--> predictive representation when applicable
        +--> Reality Graph relationships when applicable
        +--> metabolic/consolidation/failure signals when applicable
        |
        v
PAMA-governed consequential transitions
        |
        v
restart-safe durable state
        |
        v
multi-route candidate generation
        |
        v
governed recall admission
        |
        v
active context
```

No single event is required to create every representation. Classification/projection must be evidence-driven and type-preserving rather than a ritual of duplicating each input across every subsystem.

## Required slices

### 1. Durable state profile

Issue #363 is an RC blocker.

The RC state boundary must persist governance-relevant state through process loss without making private implementation attributes the storage contract.

Required restart proofs:

```text
retain -> stop -> restart -> governed recall
correct -> stop -> restart -> corrected currentness preserved
forget -> stop -> restart -> tombstone/deletion posture preserved
history -> stop -> restart -> lineage/receipts reconstructable
scope/isolation bindings -> stop -> restart -> preserved
```

Storage selection is an implementation decision. No storage engine becomes Agent Memory doctrine by being used for RC1.

### 2. Multi-memory composition

Extend the current narrow configured composition beyond semantic fact memory + exact retrieval + rebuild projection.

At least one RC fixture must show one logical experience/object participating in two or more **materially different** memory responsibilities while preserving typed semantics.

A valid fixture could, for example, retain an observed event as historical evidence, derive a governed semantic/current statement, bind a relationship in a Reality Graph, and later produce a procedural or predictive candidate where the evidence supports it.

The test must prove that these are related representations of one cognitive history rather than unrelated duplicated strings.

### 3. Multi-route candidate retrieval

One recall request must be able to obtain candidates through more than one eligible route.

Possible routes include exact identity, vector candidate retrieval, temporal relationships, graph traversal, procedural lookup, and other capability-vocabulary routes as their implementation/evidence maturity permits.

RC1 requires:

```text
query/context
  -> route selection
  -> per-route candidates + provenance
  -> optional bounded fusion/ranking
  -> governed recall admission
  -> context assembly
```

Route provenance must survive fusion/ranking.

Ranking, similarity, graph confidence, recency, or route count never grants recall permission.

A deterministic or heuristic planner is sufficient for RC1. Learned/adaptive routing is not required.

### 4. Developer facade

Provide one supported embedding surface that can initialize the runtime, perform the core lifecycle, and expose evidence.

The facade must support:

- retain/remember;
- recall;
- correction/supersession;
- forgetting/tombstoning;
- history/provenance;
- runtime posture/health.

It must preserve contract versioning, governed refusals, review requirements, receipts, and advanced evidence/attestation inputs.

### 5. Recall and crossing authority closure

Resolve the RC-relevant open seams in #364.

The RC must not ship a composed memory system in which:

- a caller-asserted principal is silently treated as authenticated identity;
- shared-domain membership is an unguarded authority setter;
- scope crossing is governed in one stage and widened ungoverned in another.

Where identity authentication remains a host responsibility, that trust boundary must be explicit in the runtime contract and evidence.

### 6. End-to-end RC scenario

Create one product-level scenario that crosses the complete RC boundary:

```text
experience
 -> typed memory consequences
 -> durable governed commit
 -> restart
 -> multi-route candidate generation
 -> governed admission
 -> active result
 -> correction/supersession
 -> restart
 -> corrected current result + historical predecessor
 -> forgetting/tombstone
 -> restart
 -> no forbidden current influence + reconstructable history
```

Include negative controls for:

- wrong scope/tenant/isolation;
- superseded or disputed candidate;
- high-confidence/high-relevance candidate with insufficient authority;
- stale state/authorization;
- unsafe or conflicting multi-memory composition where applicable.

## Retrieval-controller boundary

External work such as Jev-Mem demonstrates that lightweight adaptive control of typing, relation judgment, routing, budgets, ranking, evidence sufficiency, and stopping can be valuable.

RC1 does not adopt that architecture and does not require Jev.

The Agent Memory boundary is provider-neutral:

```text
controller may estimate/propose
    memory type
    relationship likelihood
    retrieval routes
    search budget
    candidate score/rank
    evidence sufficiency
    expected value of continued search
    stop recommendation

controller may not own
    tenant/scope authority
    recall admission
    PAMA outcome
    certification
    durable commit
    deletion/tombstone authority
    inheritance/cross-agent permission
```

A future learned/System-One/Jev-style controller can implement the estimator side of this boundary without changing Agent Memory architecture.

## Benchmark and evidence baseline

Do not optimize based on competitive anecdotes before measuring the RC.

### Memory/retrieval quality

Measure where applicable:

- recall@k;
- precision@k;
- first relevant rank / MRR;
- relation-recall contribution;
- temporal/currentness correctness;
- supersession filtering;
- answer/task quality on reproducible public memory benchmarks such as LoCoMo and LongMemEval.

### Performance

Record:

- construction/ingestion time;
- query latency distribution, not only mean;
- process memory footprint;
- durable storage growth;
- token/model/controller calls;
- route counts and expansion work.

### Governance

Keep hard invariants and failure rates separate from quality/performance:

- wrong tenant/scope/isolation admitted;
- superseded/disputed state represented as current;
- tombstoned/deleted state regains current influence;
- stale authorization accepted;
- sensitive memory disclosed to an ineligible destination/controller;
- unsafe composition admitted;
- estimator/relevance/graph confidence becomes authority;
- provenance required for reconstruction is absent.

No single scalar combines these strata.

Every benchmark claim must bind dataset/evaluator version, Agent Memory revision, runtime configuration, provider/controller identity, and relevant caches/model versions.

## Rust decision boundary

RC1 is not a Rust rewrite program.

The first requirement is a coherent measurable runtime. After RC evidence exists, profiling may justify moving bounded hot or security-sensitive kernels behind existing contracts.

A language change is earned by measured latency, memory, concurrency, deployment, or safety requirements. It is not accepted as a substitute for composing the existing architecture.

## Jev-Mem competitive boundary

Jev-Mem changes urgency and supplies useful comparative evidence. It does not redefine Agent Memory.

RC1 must not:

- rename Agent Memory concepts after Jev-Mem;
- depend on Jev/Jev-Mem to operate;
- adopt retain-every-valid-observation as lifecycle doctrine;
- let a controller's memory-management decision become consequence authority;
- redesign Cognitive Mesh identity or relationship semantics around Jev-Mem internals.

Comparative evaluation is encouraged once Agent Memory has a coherent RC baseline.

## Acceptance gates

RC1 requires all of the following:

- [ ] canonical architecture documents agree that ADR-035 is Accepted and controlling
- [ ] one supported install/open path creates a usable Agent Memory runtime
- [ ] retain -> restart -> governed recall succeeds
- [ ] correction -> restart -> corrected current state succeeds
- [ ] forget/tombstone -> restart -> stale/deleted current influence remains blocked
- [ ] history/provenance remains reconstructable after restart
- [ ] one runtime composes at least two materially different memory responsibilities
- [ ] one recall request exercises multiple eligible candidate-generation routes
- [ ] route provenance survives candidate fusion/ranking
- [ ] governed recall admission remains a separate consequential stage
- [ ] wrong-scope/tenant/isolation negative path fails safely
- [ ] superseded/disputed state is not silently returned as current
- [ ] confidence/relevance/graph scores cannot grant authority
- [ ] developer facade preserves the canonical public contract and receipts
- [ ] one full cognitive-memory scenario crosses retain, restart, recall, correction and forgetting
- [ ] benchmark/evidence manifest is reproducible
- [ ] quality, performance and governance results are reported separately
- [ ] known failures and limitations are included in the RC evidence

## Explicit non-goals

RC1 does not require:

- a new architecture or ADR;
- a universal cognitive ontology;
- every declared capability to reach production maturity;
- a Jev or Jev-Mem dependency;
- a Rust rewrite;
- branding/name resolution;
- automatic capability-maturity promotion from architectural association;
- production 1.0 claims.

## Completion definition

RC1 is complete when Agent Memory can be installed and evaluated as **one coherent governed memory system** whose specialized memory forms and retrieval mechanisms compose through the accepted ADR-035 architecture, rather than only as a collection of individually correct reference and qualification slices.