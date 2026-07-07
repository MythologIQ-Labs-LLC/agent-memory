# ADR-018: Recovery, Rollback, and Replay Are Required

## Status

Proposed

## Context

Governed memory systems will make mistakes.

A memory may be incorrectly promoted, wrongly corrected, over-pruned, recalled into unsafe context, or mutated under insufficient authority.

If the system cannot recover from these events, governance becomes performative. Performative governance is just theater with YAML.

## Decision

Agent Memory must define recovery, rollback, and replay semantics.

Implementations should be able to reconstruct memory state transitions, roll back unsafe mutations when policy allows, replay decision paths for audit, and preserve evidence for incident review.

## Consequences

### Positive

- makes unsafe memory transitions recoverable
- supports incident review and conformance debugging
- improves trust in correction workflows
- enables replay-based validation of PAMA and certification decisions

### Negative

- requires ledger integrity
- requires event ordering and replay semantics
- may conflict with deletion requirements unless retention policy is explicit

## Required recovery capabilities

At minimum:

- replay memory state transition history
- identify unsafe transition source
- roll back unauthorized mutation
- demote incorrectly crystallized memory
- restore mistakenly pruned memory when retention allows
- revoke certification
- preserve incident evidence

## Required follow-up

Create and maintain:

```text
docs/26-recovery-rollback-and-replay.md
```

## Doctrine

A governed memory system must be able to recover from its own mistakes.
