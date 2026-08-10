# Architecture Decision Records

This directory records architectural decisions for the Agent Memory doctrine.

## Status semantics

ADR status describes **doctrine maturity**, not implementation maturity.

| Status | Meaning |
|---|---|
| Proposed | A decision candidate under active evaluation. Required evidence, follow-up, or doctrine integration is incomplete. |
| Accepted | The decision is canonical Agent Memory doctrine. Implementations may still be conceptual, partial, experimental, or absent. |
| Superseded | A later ADR replaces this decision. Historical rationale remains useful. |
| Rejected | The proposal was evaluated and intentionally not adopted. |

An `Accepted` ADR does **not** claim:

- every related repository implements it
- runtime enforcement is complete
- all behavioral conformance cases pass in production
- the decision can never be revised

Implementation maturity is tracked separately through documentation, fixtures, conformance evidence, implementation maps, quality metrics, and runtime evidence.

## Current doctrine state

```text
ADR-001 through ADR-019: Accepted
ADR-020: Proposed
```

ADRs 001-019 now have their required canonical doctrine contracts and, where specified, repository-level schema/fixture evidence.

ADR-020 remains deliberately different. It requires **runtime end-to-end evidence**, not merely documentation or fixture structure.

## Current status policy

A decision may move from Proposed to Accepted when:

1. its architectural boundary is sufficiently defined
2. it is integrated consistently into canonical doctrine
3. known material contradictions have been resolved or documented
4. required foundational documentation exists
5. any repository-level schema/fixture prerequisites named by the ADR are satisfied
6. acceptance does not depend on runtime evidence the ADR explicitly says is still missing

If an ADR explicitly requires stronger evidence before acceptance, that requirement controls.

## Governed uncertainty

[`ADR-020`](ADR-020-probabilistic-discovery-deterministic-governance.md) is intentionally still **Proposed**.

Its acceptance requires at least one real implementation mapped and tested end to end across:

```text
estimate / proposal
  -> governance envelope
  -> permitted action set
  -> selected action
  -> committed consequence
```

It also requires repeated behavioral evidence for stochastic containment, cross-scope recall, concurrency, deletion residue, and related adversarial cases.

The repository now has machine-readable schemas and fixture definitions for those cases, but fixture validity is not runtime proof.

## Canonical references

- [`../01-layer-model.md`](../01-layer-model.md)
- [`../04-governance-and-pama.md`](../04-governance-and-pama.md)
- [`../06-conformance-test-plan.md`](../06-conformance-test-plan.md)
- [`../11-component-architecture.md`](../11-component-architecture.md)
- [`../24-determinism-probability-and-governed-uncertainty.md`](../24-determinism-probability-and-governed-uncertainty.md)
- [`../25-governed-uncertainty-documentation-conformance-audit.md`](../25-governed-uncertainty-documentation-conformance-audit.md)
- [`../26-governed-recall-planner.md`](../26-governed-recall-planner.md)
- [`../27-schema-registry-and-type-evolution.md`](../27-schema-registry-and-type-evolution.md)
- [`../28-retention-deletion-and-tombstones.md`](../28-retention-deletion-and-tombstones.md)
- [`../29-actor-scope-consent-and-tenancy.md`](../29-actor-scope-consent-and-tenancy.md)
- [`../30-memory-observability-and-audit-events.md`](../30-memory-observability-and-audit-events.md)
- [`../31-recovery-rollback-and-replay.md`](../31-recovery-rollback-and-replay.md)
- [`../32-memory-quality-metrics.md`](../32-memory-quality-metrics.md)
