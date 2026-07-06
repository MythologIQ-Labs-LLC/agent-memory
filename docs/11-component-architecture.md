# Component Architecture

## Purpose

This document defines Agent Memory as a larger system composed of bounded components.

The doctrine should not collapse every concept into one mega-concept. That would make the architecture sound unified while making implementation worse. A real system needs a shared spine and segmented responsibilities.

## Core decision

Agent Memory is one overall architecture made of multiple governed components.

It is not one monolithic product, library, database, score, graph, vault, or protocol.

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

| Component | Canonical role | Owns | Must not own |
|---|---|---|---|
| Identity Substrate | Stable object identity | UOR address, deterministic resolution, exact lookup identity | lifecycle policy, truth, promotion |
| Evidence and Provenance Substrate | Why something is believed | source records, observations, witnesses, evidence bundles | permanence decisions by itself |
| Reality Graphs | Domain-specific structured truth | code graph, decision graph, task graph, relation graph | runtime memory authority |
| Lifecycle Engine | Memory state transitions | transient, observed, linked, candidate, disputed, pruned, crystallized | identity semantics |
| Saturation and Decay Engine | Persistence pressure | calibrated sigma, decay, pressure, routing candidacy | correctness, certification |
| Governance and Mutation Authority | Permission to change memory | PAMA outcomes, risk, reversibility, authority | raw scoring |
| Certification and Crystallization Gate | Durable transition approval | verification, approval, certificate, scope | ongoing truth forever |
| Runtime Memory Space | Operational use | Vault, Neurospace, context recall, graph traversal | canonical doctrine ownership |
| Context Assembly Surface | What the agent sees now | prompt context, retrieved memories, active constraints | memory mutation without authority |
| Correction and Dispute Surface | How memory changes safely | user correction, contradiction, reconciliation | silent overwrite |
| Conformance and Calibration Harness | System validation | fixtures, reports, trap classes, threshold calibration | product UX |
| Product and Agent Integrations | Adoption surfaces | COREFORGE, EvolveAI, CodeGenome, FailSafe, Bicameral | redefining canonical terms locally |

## Component interaction pipeline

```text
Artifact or experience
  -> Identity Substrate
  -> Evidence and Provenance Substrate
  -> Reality Graph or Memory Unit
  -> Lifecycle Engine
  -> Saturation and Decay Engine
  -> Governance and Mutation Authority
  -> Certification and Crystallization Gate
  -> Runtime Memory Space
  -> Context Assembly Surface
```

Corrections and disputes can re-enter the pipeline at Evidence, Lifecycle, Governance, or Certification depending on severity.

## Segmentation principle

A concept belongs in a separate component when it has a distinct failure mode.

Examples:

- identity failure means the wrong object is addressed
- evidence failure means the object lacks support
- saturation failure means the system remembers or forgets poorly
- governance failure means the system changes memory without authority
- certification failure means an unverified memory becomes durable
- runtime failure means the agent uses memory incorrectly
- conformance failure means the implementation cannot prove its behavior

If two concepts fail differently, segment them.

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
3. Every durable memory transition must cross identity, evidence, saturation, authority, and certification boundaries.
4. Runtime memory may use uncertified memory only with scope and warning semantics.
5. Domain reality graphs may provide evidence, but do not own permanence.
6. PAMA may authorize mutation, but does not determine factual truth.
7. Certification may confirm durability, but does not block later correction.

## Component maturity levels

| Level | Meaning |
|---|---|
| Conceptual | The component is defined in doctrine only |
| Documented | Interfaces and failure modes are documented |
| Fixture-tested | Component behavior appears in conformance fixtures |
| Implemented | One repo implements the component |
| Enforced | The component blocks unsafe behavior at runtime |
| Cross-repo adopted | Multiple repos conform to the same boundary |

## Architecture decision

This repo owns the overall architecture.

Individual repos own implementation slices.

The shared architecture should stabilize concepts, boundaries, and conformance expectations. It should not force every implementation into one repository or one runtime.
