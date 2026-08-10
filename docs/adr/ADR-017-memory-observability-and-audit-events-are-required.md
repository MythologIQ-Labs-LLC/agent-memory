# ADR-017: Memory Observability and Audit Events Are Required

## Status

Proposed

## Context

The doctrine defines lifecycle states, PAMA outcomes, certification gates, conformance fixtures, component handoffs, probabilistic estimators, and bounded action sets.

Without a common audit-event model, implementations can claim governance while emitting incompatible or incomplete traces. Decorative logging remains logging's favorite hobby.

## Decision candidate

Agent Memory must define a common memory observability and audit-event model.

Consequential memory transitions, handoffs, recalls, mutations, certification, disputes, corrections, deletion, policy decisions, and conformance runs should emit structured events appropriate to their risk and privacy constraints.

Events affecting governed uncertainty should preserve where material:

- estimator/model ID and version
- calibration reference
- uncertainty/disagreement summary
- policy version
- authority reference
- permitted action set
- selected action and selection mode
- before/after state
- rollback/recovery reference

## Required event classes

At minimum:

- memory_created
- memory_linked
- memory_scored
- memory_state_changed
- memory_recalled
- recall_admission_decided
- memory_mutation_requested
- pama_decision
- action_selected
- certification_requested
- certification_completed
- dispute_opened
- correction_applied
- memory_archived
- memory_pruned
- memory_tombstoned
- memory_deleted
- component_handoff
- conformance_fixture_run

## Required follow-up before acceptance

Create and audit:

```text
docs/30-memory-observability-and-audit-events.md
schemas/memory-audit-event.schema.json
```

## Doctrine candidate

If a consequential memory transition cannot be reconstructed from evidence, policy, authority, and state, its governance is incomplete.
