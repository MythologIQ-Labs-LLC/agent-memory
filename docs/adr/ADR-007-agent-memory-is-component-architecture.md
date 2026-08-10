# ADR-007: Agent Memory Is a Component Architecture

## Status

Accepted

## Context

The Agent Memory doctrine consolidates concepts from UOR, EvolveAI, CodeGenome, COREFORGE Vault / Neurospace, PAMA, FailSafe, Arbiter, Bicameral, and related systems.

These concepts are tightly related, but they do not all belong in the same implementation layer.

If everything is treated as one concept, the architecture becomes vague. If everything is split into unrelated projects, the doctrine fragments.

## Decision

Agent Memory is one overall architecture composed of bounded components.

The doctrine repo owns the shared architecture, vocabulary, contracts, segmentation rules, and conformance expectations.

Individual repos own implementation slices.

Components may contain deterministic, probabilistic, learned, or hybrid internals, but cross-component handoffs must preserve signal semantics, provenance, scope, uncertainty, and authority boundaries.

## Component boundaries

The canonical components include:

1. Identity Substrate
2. Evidence and Provenance Substrate
3. Reality Graphs
4. Lifecycle Engine
5. Saturation and Decay Engine
6. Governance and Mutation Authority
7. Certification and Crystallization Gate
8. Runtime Memory Space
9. Context Assembly Surface
10. Correction and Dispute Surface
11. Conformance and Calibration Harness
12. Product and Agent Integrations

Additional components may be added when they have distinct cross-system interfaces and failure modes.

## Consequences

### Positive

- preserves one coherent architecture
- avoids monolithic implementation pressure
- gives every concept a home
- makes cross-repo adoption easier
- allows conformance to test boundaries rather than repo names
- supports product runtimes without letting them redefine doctrine locally

### Negative

- requires adapter contracts between components
- requires careful documentation discipline
- requires cross-repo backlinks and implementation maps
- creates composition-specific failure modes that must be tested

## Rejected alternatives

### One monolithic memory system

Rejected because identity, inference, scoring, certification, governance, runtime use, privacy, and correction have distinct failure modes.

### Completely separate concepts

Rejected because the concepts participate in governed memory transition/admission and need shared doctrine.

### Product-first definition

Rejected because products should conform to doctrine rather than redefine memory terms locally.

## Acceptance scope

Accepted establishes component architecture as canonical doctrine. It does not freeze the component list forever or require one repository per component.

## Doctrine

Agent Memory is unified by contracts, not repository location.

The system is one architecture, segmented into bounded components, composed through governed handoffs.
