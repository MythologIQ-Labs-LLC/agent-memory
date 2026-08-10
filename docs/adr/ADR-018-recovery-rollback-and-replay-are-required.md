# ADR-018: Recovery, Rollback, and Replay Are Required

## Status

Proposed

## Context

Governed memory systems will make mistakes.

A memory may be incorrectly promoted, wrongly corrected, over-pruned, recalled into unsafe context, mutated under insufficient authority, or committed from stale authorization.

If the system cannot recover from these events, governance becomes performative. Performative governance is just theater with YAML.

## Decision candidate

Agent Memory must define recovery, rollback, and replay semantics.

Implementations should be able to reconstruct consequential decision paths, restore or compensate for unsafe mutations when policy allows, demote incorrectly durable memory, revoke certification, and preserve incident evidence.

Exact replay of stochastic cognition is not always required or possible.

The required invariant is reconstruction of:

```text
what was observed/estimated
which policy and authority applied
what actions were permitted/prohibited
what action was selected
what state changed
what recovery path exists
```

## Consequences

### Positive

- makes unsafe transitions recoverable
- supports incident review and conformance debugging
- improves correction and certification trust
- preserves accountability even when model outputs are stochastic

### Negative

- requires ledger integrity and ordering
- requires state/version binding
- may conflict with privacy/deletion requirements unless retention is explicit

## Required recovery capabilities

- reconstruct memory transition history
- identify unsafe transition source
- reject stale authorization at commit
- roll back or compensate for unauthorized mutation
- demote incorrectly crystallized memory
- restore mistakenly pruned memory when retention allows
- revoke certification
- preserve incident evidence within privacy constraints

## Required follow-up before acceptance

Create and audit:

```text
docs/31-recovery-rollback-and-replay.md
```

Then add replay cases for stochastic estimators, policy drift, concurrent mutation, and deletion constraints.

## Doctrine candidate

A governed memory system must recover from its own mistakes without pretending stochastic cognition has to be byte-for-byte replayable.
