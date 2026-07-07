# ADR-017: Memory Observability and Audit Events Are Required

## Status

Proposed

## Context

The doctrine defines lifecycle states, PAMA outcomes, certification gates, conformance fixtures, and component handoffs. It does not yet define a common observability and audit event model.

Without shared audit events, implementations can claim governance while emitting incompatible or incomplete traces. That is how observability turns into decorative logging, nature's most boring confetti.

## Decision

Agent Memory must define a memory observability and audit event model.

Every meaningful memory transition, handoff, recall, mutation, certification, dispute, correction, deletion, and policy decision should emit a structured event.

## Consequences

### Positive

- enables cross-component traceability
- supports conformance testing
- improves incident review
- allows runtime memory behavior to be replayed or audited
- gives FailSafe, Arbiter, Vault, and product surfaces a common event language

### Negative

- requires event schemas
- increases implementation burden
- requires careful handling of sensitive event content

## Required event classes

At minimum:

- memory_created
- memory_linked
- memory_scored
- memory_state_changed
- memory_recalled
- memory_mutation_requested
- pama_decision
- certification_requested
- certification_completed
- dispute_opened
- correction_applied
- memory_pruned
- memory_tombstoned
- memory_deleted
- component_handoff
- conformance_fixture_run

## Required follow-up

Create and maintain:

```text
docs/25-memory-observability-and-audit-events.md
schemas/memory-audit-event.schema.json
```

## Doctrine

If a memory transition cannot be observed, it cannot be governed.
