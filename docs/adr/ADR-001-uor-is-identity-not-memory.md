# ADR-001: UOR Is Identity, Not Memory

## Status

Proposed

## Context

The memory architecture uses UOR concepts for deterministic addressability and exact object resolution. A recurring risk is treating UOR identity as if it were the full memory system.

That collapses two different responsibilities:

- identity: what object is this?
- lifecycle: should this object persist, decay, route, or crystallize?

## Decision

UOR is the identity substrate.

UOR must own deterministic object identity and exact addressability. It must not own memory lifecycle policy, saturation scoring, mutation authority, or certification.

## Consequences

### Positive

- preserves clean kernel semantics
- prevents lifecycle policy from corrupting identity
- allows multiple memory runtimes to consume the same identity substrate
- keeps crystallization as a governed transition rather than an address side effect

### Negative

- requires a separate lifecycle layer
- requires implementers to respect the boundary between object identity and memory use

## Doctrine

UOR answers what the object is.

The memory system answers what should happen to it.
