# Component Architecture

## Purpose

This document defines Agent Memory as a larger system composed of bounded components.

The doctrine should not collapse every concept into one mega-concept. A real system needs a shared spine and segmented responsibilities.

Component boundaries must preserve the difference between uncertain inference and governed consequence. A probabilistic output crossing a component boundary must not quietly become authority because the receiving component forgot what kind of signal it was.

They must also preserve the difference between **implementation ancestry** and **runtime ownership**.

## Core decision

Agent Memory is one overall architecture made of multiple governed components.

It is not one monolithic product, library, database, score, graph, vault, protocol, or model.

PAMA is a native governance component of this architecture, not an external product dependency.

Agent Memory also owns its generic memory machinery. Same-owner prior systems may donate proven mechanisms or continue as specialized domain producers, but they are not the intended permanent owners of generic Agent Memory retrieval, lifecycle, graph, context, or evaluation capabilities.

See [`05-repo-implementation-map.md`](05-repo-implementation-map.md), [`39-implementation-ownership-map.md`](39-implementation-ownership-map.md), and [ADR-036](adr/ADR-036-same-owner-components-are-first-party-modules.md).

## Accepted cognitive-framework architecture

> **Status:** Accepted by [ADR-035](adr/ADR-035-agent-memory-is-a-governed-cognitive-framework.md). This section describes the canonical system topology. Existing Accepted ADR boundaries remain controlling within that composition.

The accepted top-level architecture is:

```text
Agent Memory
|
+-- Cognitive Plane
|   +-- Cognitive Mesh
|   +-- Working Memory & Attention
|   +-- Cognitive Metabolism
|   +-- Consolidation & Abstraction
|   +-- Procedural Memory & Skills
|   +-- Predictive / World Modeling
|   +-- Metacognitive Signals
|
+-- Reality Plane
|   +-- Reality Graphs
|       +-- Code Reality Graph
|       +-- Environment Reality Graph
|       +-- Task Reality Graph
|       +-- Social Reality Graph
|       +-- Organizational Reality Graph
|
+-- Authority Plane
    +-- PAMA
    +-- Governed Recall Admission
    +-- Certification & Durable Commit
    +-- Scope / Privacy / Isolation
    +-- Correction / Supersession
    +-- Deletion / Forgetting Authority
    +-- Inheritance / Multi-Agent Crossing

Cross-cutting:
  Identity & Continuity
  Evidence & Provenance
  Conformance / Calibration / Evaluation
```

The planes are logical responsibility groupings, not exclusive component categories or deployment boundaries.

ADR-033 remains controlling for composition:

```text
module identity != component identity
component identity != capability identity

one component -> many capabilities
one capability -> many implementation strategies over time
```

## First-party ancestry within the accepted architecture

EvolveAI, CodeGenome, and COREFORGE contain substantial prior implementation work that materially informs the accepted architecture. Under ADR-036 they are first-party implementation ancestry, not attributed external providers.

The intended migration rule is:

```text
first-party mechanism
    -> inspect / validate / harvest
    -> native Agent Memory capability
```

Specifically:

- **EvolveAI** is implementation ancestry and a behavioral test oracle for Cognitive Metabolism, vector retrieval, temporal graph behavior, tier routing, decay, consolidation, pruning, crystallization, restart, and failure-memory mechanisms.
- **CodeGenome** is implementation ancestry for generic graph/vector/provenance/evaluation mechanisms and may continue as a **specialized code-domain observation source**.
- **COREFORGE Vault / Neurospace** is product/runtime ancestry for context brokerage, memory domains, references, graph recall, mutation boundaries, and lineage. The desired end-state direction is for COREFORGE to consume Agent Memory for generic memory capabilities.
- **Agent Memory core/runtime** owns the Cognitive Mesh contract, generic memory machinery, cross-module semantics, governance boundaries, and conformance requirements.

This mapping is architecture and ownership, not capability promotion. First-party ancestry does not confer production maturity.

## Cognitive Mesh

The Cognitive Mesh is the shared substrate through which persistent cognitive objects and typed relationships can participate in multiple bounded modules without losing semantic type, provenance, uncertainty, scope, lifecycle, currentness, or authority posture.

Candidate object classes include:

```text
Experience
Observation
Episode
Concept
Fact
Preference
Relationship
Procedure
Skill
Goal
Task
Prediction
Failure
Decision
Policy
Person
CodeArtifact
EnvironmentState
Correction
Evidence
DerivedState
```

Candidate typed relationships include:

```text
supports
contradicts
derived_from
supersedes
associated_with
caused_by
part_of
depends_on
predicts
performed_by
applies_to
learned_from
similar_to
evidenced_by
invalidates
```

The mesh must not collapse unlike semantics:

```text
common mesh != common behavior
relationship != truth
activation != authority
confidence != permission
persistence != correctness
```

## Module responsibilities

| Module | Responsibility | Native owner / ancestry | Must not silently own |
|---|---|---|---|
| Cognitive Mesh | shared cognitive identity and typed relation substrate | **Agent Memory** | universal truth, mutation authority |
| Cognitive Metabolism | salience, decay, reinforcement, persistence pressure, consolidation candidacy, adaptive restructuring proposals | **Agent Memory**; EvolveAI ancestry | truth, deletion authority, crystallization authority |
| Working Memory & Attention | active admitted cognitive state | **Agent Memory** | bypass of recall admission |
| Consolidation & Abstraction | candidate semantic/procedural/generalized structures | **Agent Memory**; EvolveAI and other mechanisms may inform implementation | canonicality from repetition alone |
| Predictive / World Modeling | expectations about future or latent state | **Agent Memory contract**, pluggable estimators | factual truth or action authority |
| Procedural Memory & Skills | retained reusable procedures | **Agent Memory** procedural-memory profile | execution permission |
| Reality Graphs | domain-specific external/operational reality | **Agent Memory framework** with specialized domain sources | memory permanence or downstream authority |
| Code Reality Graph | code-domain identity, structure, evidence, freshness, impact | **Agent Memory CRG boundary**; CodeGenome may supply code-domain observations and ancestry | universal Cognitive Mesh ontology |
| Retrieval | exact, lexical, relational, vector, temporal, graph candidate discovery | **Agent Memory**; EvolveAI/CodeGenome ancestry where useful | recall permission or truth |
| Runtime Memory / Context Assembly | operational recall and governed context | **Agent Memory**; COREFORGE ancestry, downstream consumers | canonical truth from utility |
| PAMA | mutation/consequence authority | **Agent Memory native** | factual truth |
| Conformance / Evaluation | module and composition evidence | **Agent Memory**; CodeGenome experiment-loop ancestry; optional verification peers | product claims without evidence |

## Accepted system shape

```text
Agent Memory System
├── Identity Substrate
├── Evidence and Provenance Substrate
├── Reality Graphs
├── Retrieval Machinery
├── Lifecycle Engine
├── Saturation and Decay Engine
├── Governance and Mutation Authority (PAMA)
├── Certification and Crystallization Gate
├── Runtime Memory Space
├── Context Assembly Surface
├── Correction and Dispute Surface
├── Durable Decision Memory
├── Governance Context Projection
├── Conformance and Calibration Harness
└── Product and Agent Integrations
```

ADR-035 establishes the system-level composition of these responsibilities. It does not erase their distinct failure modes.

## Component map

| Component | Canonical role | Owns | Must not own | Typical control character |
|---|---|---|---|---|
| Identity Substrate | stable object identity | Agent Memory identity contract; exact-address mechanism | lifecycle policy, truth, promotion | deterministic substrate |
| Evidence and Provenance Substrate | why something is believed | source records, observations, witnesses, evidence bundles, estimator provenance | permanence decisions by itself | deterministic records + uncertain evidence |
| Reality Graphs | domain-specific structured reality | Agent Memory graph contracts/projections | runtime memory authority | deterministic identity + probabilistic relations |
| Retrieval Machinery | candidate discovery | exact, lexical, relational, semantic/vector, temporal, graph routes as implemented | recall admission, truth, mutation authority | deterministic / probabilistic / hybrid by route |
| Lifecycle Engine | memory state transitions | transient, observed, linked, candidate, disputed, pruned, crystallized | identity semantics | governed state machine |
| Saturation and Decay Engine | persistence pressure | calibrated saturation, decay, reinforcement, routing candidacy | correctness, certification | probabilistic / heuristic / learned estimates |
| Governance and Mutation Authority | permission to change memory or downstream authority | native PAMA outcomes, M0-M5 target classes, A0-A5 authority ceilings, risk, reversibility | raw scoring, factual truth | deterministic or formally bounded governance envelope |
| Certification and Crystallization Gate | durable transition approval | verification, approval, certificate, scope | ongoing truth forever | governed consequence |
| Runtime Memory Space | operational memory use | governed recall, currentness, history, persistence/restart posture | canonical doctrine ownership by downstream product | hybrid retrieval + enforced scope |
| Context Assembly Surface | what the agent sees now | admitted memory/context, active constraints, representation | memory mutation without authority | ranking/assembly after governed admission |
| Correction and Dispute Surface | how memory changes safely | user correction, contradiction, reconciliation | silent overwrite | mixed inference + governed commit |
| Durable Decision Memory | decision continuity and rationale | durable decisions, supersession, drift evidence, rationale preservation | product-specific ownership | governed memory profile |
| Governance Context Projection | vendor-neutral governance-facing view | derived precedent/context, material conditions, polarity, validity, derivation metadata | canonical memory truth, standing permission, consumer verdicts | deterministic projection first; estimator-mediated retrieval only as typed evidence |
| Conformance and Calibration Harness | system validation | fixtures, reports, trap classes, threshold calibration, benchmark manifests | product UX | measurement and falsification |
| Product and Agent Integrations | adoption surfaces | consumer-specific adapters and product behavior | redefining canonical Agent Memory terms locally | implementation-specific within doctrine |

## Component interaction pipeline

```text
Artifact or experience
  -> Identity Substrate
  -> Evidence and Provenance Substrate
  -> Reality Graph and/or Memory Unit
  -> deterministic / probabilistic candidate processing
  -> Lifecycle and Saturation proposal
  -> Governance and Mutation Authority (PAMA)
  -> permitted action set
  -> Certification and Crystallization Gate when required
  -> committed state transition
  -> native Runtime Memory Space
  -> candidate retrieval
  -> governed recall admission
  -> Context Assembly Surface
```

Corrections and disputes can re-enter at Evidence, Lifecycle, Governance, or Certification depending on severity.

The pipeline describes responsibility and authority flow, not necessarily one synchronous execution order.

ADR-035 generalizes the same boundary into a cognitive loop:

```text
experience / observation
  -> stable cognitive identity + evidence
  -> Cognitive Mesh
  -> Cognitive Metabolism and/or Reality Graph processing
  -> candidate cognitive change
  -> PAMA authority evaluation
  -> governed durable commit or refusal
  -> candidate retrieval
  -> governed recall
  -> Working Memory & Attention
  -> active cognition
```

A learned signal, graph score, vector similarity, prediction, or domain-native verdict remains a proposal/evidence signal unless existing authority doctrine says otherwise.

Governance Context Projection is an optional derived branch from canonical memory and governed recall, not a replacement stage in the canonical write/read path:

```text
canonical memory + evidence + scope + outcome
  -> governed retrieval / selection
  -> Governance Context Projection
  -> consumer-specific adapter
  -> external governance / approval / enforcement decision
```

Returned approval or execution evidence may become new Agent Memory input only through normal identity, evidence, lifecycle, and authority boundaries.

## Uncertainty must survive handoff

When a component produces an estimate, the receiver must be able to distinguish:

```text
value
semantic meaning
estimator or method
estimator version
calibration scope when relevant
uncertainty representation
source evidence
validity scope
```

For example, a CodeGenome relation with confidence `0.82` must not arrive at PAMA as a naked `0.82` with no indication that it is an inferred semantic edge.

Likewise, a sensitivity classifier that reports uncertainty must not be converted into `non_sensitive=true` merely because an API wanted a boolean.

A Cognitive Metabolism signal such as high reinforcement, low predicted utility, or crystallization candidacy must remain typed as a metabolic/lifecycle proposal. It must not arrive downstream disguised as truth, deletion authority, or permission to become canonical.

A vector similarity score must remain candidate relevance evidence. It cannot become recall permission or currentness.

A Governance Context Projection selected through semantic similarity must preserve the estimator and uncertainty that selected the precedent. The consumer may receive candidate relevance; it must not receive probabilistic similarity disguised as permission.

## Proposal, authority, selection, commit

Composition preserves four logical stages:

```text
PROPOSAL
what an estimator, model, rule, or planner suggests

AUTHORITY ENVELOPE
what PAMA policy permits, blocks, defers, or requires review for

SELECTION
which permitted action is chosen, deterministically or stochastically

COMMIT
what state actually changes and what receipt is emitted
```

A component may implement multiple stages, but it must not make them indistinguishable.

For external governance consumers, Governance Context Projection sits before their equivalent authority/selection/commit stages. It supplies remembered context, not a substitute authority envelope.

## Segmentation principle

A concept belongs in a separate component when it has a distinct failure mode.

Examples:

- cognitive-mesh failure means identity, type, or relationship semantics are corrupted across modules;
- identity failure means the wrong object is addressed;
- evidence failure means the object lacks support;
- estimator failure means confidence, relevance, sensitivity, persistence, or prediction is miscalibrated or out of scope;
- metabolic failure means the system reinforces, consolidates, retains, or forgets poorly;
- retrieval failure means useful evidence is not discovered, stale evidence is over-ranked, or route provenance is lost;
- reality-graph failure means domain state or relationships are wrong, stale, or insufficiently evidenced;
- governance failure means the system changes memory or authority without permission;
- certification failure means an unverified memory becomes durable;
- runtime failure means the agent uses memory incorrectly;
- durable-decision failure means rationale, supersession, or current decision state is lost or silently rewritten;
- governance-projection failure means derived context loses provenance/scope, erases negative precedent, or becomes consumer authority;
- composition failure means individually valid components combine into unsafe behavior;
- conformance failure means the implementation cannot prove its behavior.

If two concepts fail differently, segment them or expose the internal boundary clearly.

## Composition failure is first-class

Safe components do not automatically create a safe system.

Examples:

```text
safe retriever + missing tenant filter -> cross-tenant leakage
accurate sensitivity classifier + stale policy -> unsafe sharing
calibrated utility estimator + overbroad deletion authority -> irreversible loss
high reinforcement + bad evidence -> durable false belief candidate
accurate reality graph + stale currentness -> incorrect active cognition
high vector similarity + superseded memory -> stale active context
useful prediction + authority collapse -> unauthorized action
valid individual memories + unsafe composition -> poisoned context
valid PAMA outcome + stale state snapshot -> incorrect commit
valid precedent + consumer-specific overgeneralization -> approval laundering
```

Therefore conformance must test handoffs and composition, not only isolated component behavior.

## Unification principle

A concept belongs under Agent Memory when it participates in governed memory state transition, persistent cognition, native retrieval/context assembly, or a governed projection of remembered state whose semantics must remain reconstructable.

Examples:

- UOR may participate through optional exact identity;
- CodeGenome may participate as a code-domain evidence producer and as implementation ancestry for generic mechanisms now owned by Agent Memory;
- EvolveAI participates as implementation ancestry/test oracle for Cognitive Metabolism and retrieval mechanisms now owned by Agent Memory;
- PAMA participates as native authority machinery;
- COREFORGE Vault/Neurospace contributes product/runtime ancestry and should increasingly consume Agent Memory downstream;
- FailSafe and Arbiter may participate as enforcement/evidence peers;
- durable decision memory participates through Agent Memory's own decision-memory profile;
- Governance Context Projection participates by exposing bounded, consumer-neutral context without owning the downstream governance decision.

An adjacent product name is not itself an architectural role.

## Boundary rules

1. Shared doctrine, segmented native implementation.
2. The shared Cognitive Mesh under ADR-035 does not erase component or capability boundaries.
3. Components may depend on each other, but must not redefine each other.
4. Every durable memory transition crosses identity, evidence, authority, and certification boundaries; scoring may propose but not authorize.
5. Runtime memory may use uncertified memory only with scope and warning semantics.
6. Domain reality graphs may provide evidence, but do not own permanence or generic memory machinery.
7. Cognitive Metabolism may propose reinforcement, decay, consolidation, or restructuring, but does not own truth or consequence authority.
8. PAMA may authorize mutation, but does not determine factual truth.
9. Certification may confirm durability, but does not block later correction.
10. Probabilistic outputs must preserve semantic type, provenance, and uncertainty across handoffs.
11. A blocked action remains blocked even when another component assigns high confidence, utility, reinforcement, similarity, or predicted value.
12. Stochastic selection may occur only inside a policy-permitted action set.
13. Commit boundaries bind to the state and policy snapshot under which authority was granted.
14. Composition-specific failure modes require composition-specific tests.
15. PAMA target class, lifecycle strength, requested operation, and downstream authority remain separate dimensions.
16. Module identity, component identity, and capability identity remain distinct.
17. Implementation ancestry does not imply permanent cross-repository runtime ownership.
18. A specialized domain producer does not become the owner of Agent Memory's generic graph/vector/retrieval machinery.
19. Derived Governance Context Projection is reconstructable context, never an alternate canonical memory store or final policy authority.
20. Consumer-specific fields belong in consumer adapters unless they expose a genuinely general missing Agent Memory primitive.
21. Returned external approval or execution evidence re-enters through normal evidence/governance boundaries; an integration callback is not a privileged write path.

## Cross-component handoff contract

A consequential handoff should preserve, where applicable:

```text
memory_id
source_component
target_component
handoff_reason
state_snapshot
pama_target_class
lifecycle_strength
requested_operation
requested_downstream_authority
estimate_type
estimate_value
estimator_ref
estimator_version
calibration_ref
uncertainty_summary
evidence_refs
policy_refs
policy_version
authority_refs
permitted_action_set
certification_refs
ledger_ref
timestamp
```

For Cognitive Mesh participation, additional typed metadata may be required to preserve object class, relationship semantics, activation posture, canonical/derived posture, and currentness. ADR-035 requires that this be defined without forcing one implementation-specific universal ontology.

Not all fields apply to every handoff. Omitted authority-critical fields must not be guessed downstream.

Governance Context Projection has a separate minimized schema because it is a consumer-facing derived view rather than a canonical component mutation handoff. It still preserves source-memory references, scope, derivation, validity, and uncertainty sufficient for reconstruction.

## Component maturity levels

| Level | Meaning |
|---|---|
| Conceptual | the component is defined in doctrine only |
| Documented | interfaces and failure modes are documented |
| Handoff-documented | input/output semantics and uncertainty/authority boundaries are documented |
| Fixture-tested | component behavior appears in conformance fixtures |
| Composition-tested | handoffs and multi-component failure modes are tested |
| Implemented | Agent Memory has a native implementation of the bounded component/capability |
| Enforced | the component blocks unsafe behavior at runtime |
| Consumer-adopted | downstream products consume the Agent Memory boundary rather than independently redefining it |

These architectural maturity descriptions do not replace ADR-033 capability maturity (`declared`, `implemented`, `runtime_wired`, `evidence_proven`, `reference_qualified`). Capability qualification remains independently version- and evidence-scoped.

## Architecture decision

This repository owns the overall Agent Memory architecture, generic memory capability contracts, native governance including PAMA, and the vendor-neutral Governance Context Projection profile.

Under ADR-035, Agent Memory owns the canonical Cognitive Mesh contract and module-level topology of the governed cognitive framework. Under ADR-036 and #455, useful same-owner mechanisms may be absorbed into this runtime rather than preserved as mandatory cross-repository provider boundaries.

Specialized systems may remain independent where specialization is real. CodeGenome may continue to observe code reality. COREFORGE may continue to own product UX and orchestration. Optional identity, verification, and enforcement peers may remain separate.

The shared architecture should stabilize concepts, boundaries, handoff semantics, implementation ownership, and conformance expectations. It should not force every product into one repository, but it also should not recreate generic Agent Memory functionality as a permanent federation of historical internal services.