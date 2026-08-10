# Component Architecture

## Purpose

This document defines Agent Memory as a larger system composed of bounded components.

The doctrine should not collapse every concept into one mega-concept. That would make the architecture sound unified while making implementation worse. A real system needs a shared spine and segmented responsibilities.

Component boundaries must also preserve the difference between uncertain inference and governed consequence. A probabilistic output crossing a component boundary must not quietly become authority because the receiving component forgot what kind of signal it was.

## Core decision

Agent Memory is one overall architecture made of multiple governed components.

It is not one monolithic product, library, database, score, graph, vault, protocol, or model.

## System shape

```text
Agent Memory System
├── Identity Substrate
├── Evidence and Provenance Substrate
├── Reality Graphs
├── Lifecycle Engine
├── Saturation and Decay Engine
├── Governance and Mutation Authority
├── Certification and Crystallization Gate
├── Runtime Memory Space
├── Context Assembly Surface
├── Correction and Dispute Surface
├── Conformance and Calibration Harness
└── Product and Agent Integrations
```

## Component map

| Component | Canonical role | Owns | Must not own | Typical control character |
|---|---|---|---|---|
| Identity Substrate | Stable object identity | UOR address, deterministic resolution, exact lookup identity | lifecycle policy, truth, promotion | deterministic substrate |
| Evidence and Provenance Substrate | Why something is believed | source records, observations, witnesses, evidence bundles, estimator provenance | permanence decisions by itself | deterministic records + uncertain evidence |
| Reality Graphs | Domain-specific structured reality | code graph, decision graph, task graph, relation graph | runtime memory authority | deterministic identity + probabilistic relations |
| Lifecycle Engine | Memory state transitions | transient, observed, linked, candidate, disputed, pruned, crystallized | identity semantics | governed state machine |
| Saturation and Decay Engine | Persistence pressure | calibrated sigma, decay, pressure, routing candidacy | correctness, certification | probabilistic / heuristic / learned estimates |
| Governance and Mutation Authority | Permission to change memory | PAMA outcomes, risk, reversibility, authority | raw scoring | deterministic or formally bounded governance envelope |
| Certification and Crystallization Gate | Durable transition approval | verification, approval, certificate, scope | ongoing truth forever | governed consequence |
| Runtime Memory Space | Operational use | Vault, Neurospace, context recall, graph traversal | canonical doctrine ownership | hybrid retrieval + enforced scope |
| Context Assembly Surface | What the agent sees now | prompt context, retrieved memories, active constraints | memory mutation without authority | probabilistic ranking inside governed admission |
| Correction and Dispute Surface | How memory changes safely | user correction, contradiction, reconciliation | silent overwrite | mixed inference + governed commit |
| Conformance and Calibration Harness | System validation | fixtures, reports, trap classes, threshold calibration | product UX | measurement and falsification |
| Product and Agent Integrations | Adoption surfaces | COREFORGE, EvolveAI, CodeGenome, FailSafe, Bicameral | redefining canonical terms locally | implementation-specific within doctrine |

## Component interaction pipeline

```text
Artifact or experience
  -> Identity Substrate
  -> Evidence and Provenance Substrate
  -> Reality Graph or Memory Unit
  -> probabilistic / heuristic interpretation
  -> Lifecycle and Saturation proposal
  -> Governance and Mutation Authority
  -> permitted action set
  -> Certification and Crystallization Gate when required
  -> committed state transition
  -> Runtime Memory Space
  -> recall-time governance
  -> Context Assembly Surface
```

Corrections and disputes can re-enter the pipeline at Evidence, Lifecycle, Governance, or Certification depending on severity.

The pipeline describes responsibility and authority flow, not necessarily one synchronous execution order.

## Uncertainty must survive handoff

When a component produces an estimate, the receiving component must be able to distinguish:

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

## Proposal, authority, selection, commit

Composition should preserve four different logical stages:

```text
PROPOSAL
what an estimator, model, rule, or planner suggests

AUTHORITY ENVELOPE
what policy permits, blocks, defers, or requires review for

SELECTION
which permitted action is chosen, deterministically or stochastically

COMMIT
what state actually changes and what receipt is emitted
```

A component may implement multiple stages, but it must not make them indistinguishable.

## Segmentation principle

A concept belongs in a separate component when it has a distinct failure mode.

Examples:

- identity failure means the wrong object is addressed
- evidence failure means the object lacks support
- estimator failure means a confidence, relevance, sensitivity, or persistence estimate is miscalibrated or out of scope
- saturation failure means the system remembers or forgets poorly
- governance failure means the system changes memory without authority
- certification failure means an unverified memory becomes durable
- runtime failure means the agent uses memory incorrectly
- composition failure means individually valid components combine into unsafe behavior
- conformance failure means the implementation cannot prove its behavior

If two concepts fail differently, segment them or expose the internal boundary clearly.

## Composition failure is first-class

Safe components do not automatically create a safe system.

Examples:

```text
safe retriever + missing tenant filter -> cross-tenant leakage
accurate sensitivity classifier + stale policy -> unsafe sharing
calibrated utility estimator + overbroad deletion authority -> irreversible loss
valid individual memories + unsafe composition -> poisoned context
valid PAMA outcome + stale state snapshot -> incorrect commit
```

Therefore conformance must test handoffs and composition, not only isolated component behavior.

## Unification principle

A concept belongs under the same overall architecture when it participates in governed memory state transition.

Examples:

- UOR participates by providing stable identity
- CodeGenome participates by providing domain evidence and graph relations
- EvolveAI participates by modeling lifecycle and decay
- PAMA participates by controlling mutation authority
- COREFORGE Vault and Neurospace participate by operationalizing memory
- FailSafe and Arbiter participate by enforcing policy and audit
- Bicameral participates by preserving decision continuity

## Boundary rules

1. Shared doctrine, segmented implementation.
2. Components may depend on each other, but must not redefine each other.
3. Every durable memory transition must cross identity, evidence, authority, and certification boundaries; scoring may propose but not authorize.
4. Runtime memory may use uncertified memory only with scope and warning semantics.
5. Domain reality graphs may provide evidence, but do not own permanence.
6. PAMA may authorize mutation, but does not determine factual truth.
7. Certification may confirm durability, but does not block later correction.
8. Probabilistic outputs must preserve semantic type, provenance, and uncertainty across handoffs.
9. A blocked action must remain blocked even when another component assigns it high confidence or utility.
10. Stochastic selection may occur only inside a policy-permitted action set.
11. Commit boundaries must bind to the state and policy snapshot under which authority was granted.
12. Composition-specific failure modes require composition-specific tests.

## Cross-component handoff contract

A consequential handoff should preserve, where applicable:

```text
memory_id
source_component
target_component
handoff_reason
state_snapshot
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

Not all fields apply to every handoff. Omitted authority-critical fields must not be guessed downstream.

## Component maturity levels

| Level | Meaning |
|---|---|
| Conceptual | The component is defined in doctrine only |
| Documented | Interfaces and failure modes are documented |
| Handoff-documented | Input/output semantics and uncertainty/authority boundaries are documented |
| Fixture-tested | Component behavior appears in conformance fixtures |
| Composition-tested | Handoffs and multi-component failure modes are tested |
| Implemented | One repo implements the component |
| Enforced | The component blocks unsafe behavior at runtime |
| Cross-repo adopted | Multiple repos conform to the same boundary |

## Architecture decision

This repo owns the overall architecture.

Individual repos own implementation slices.

The shared architecture should stabilize concepts, boundaries, handoff semantics, and conformance expectations. It should not force every implementation into one repository or one runtime.
