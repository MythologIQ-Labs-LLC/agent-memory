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
ADR-021: Proposed
ADR-022: Proposed
```

ADRs 001-019 now have their required canonical doctrine contracts and, where specified, repository-level schema/fixture evidence.

ADR-020 remains deliberately different. It requires **runtime end-to-end evidence**, not merely documentation or fixture structure.

ADR-021 proposes the interoperability boundary for **portable memory-governance evidence**. It keeps Agent Memory authoritative for memory semantics, PAMA, lifecycle obligations, and canonical decision receipts while allowing external trust systems such as AgenTrust to verify and correlate evidence without redefining those semantics.

ADR-022 proposes **memory isolation domains and controlled boundary crossing** as first-class architecture. It extends ADR-016 by making same-agent cross-project/task separation, shared-memory domains, derived-scope inheritance, and scope crossing explicitly governable rather than leaving them as implied metadata filters.

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

## Portable memory-governance evidence

[`ADR-021`](ADR-021-portable-memory-governance-evidence-boundary.md) is intentionally **Proposed**.

Its central boundary is:

```text
Agent Memory
  owns memory semantics, PAMA, lifecycle, and canonical receipts
        |
        v
portable evidence projection
        |
        v
external trust / attestation system
  verifies binding, integrity, and execution correlation
```

The external trust system does not acquire authority to redefine memory-specific permission or infer lifecycle satisfaction from cryptographic integrity alone.

ADR-021 acceptance requires an executable interoperability proof, including negative paths and at least one deletion-completeness scenario that distinguishes a valid memory mutation/checkpoint from successful semantic forgetting.

## Memory isolation domains

[`ADR-022`](ADR-022-memory-isolation-domains-and-controlled-boundary-crossing.md) is intentionally **Proposed**.

Its central boundary is:

```text
same agent / same store
        !=
same authorized memory domain
```

It treats project, task, workspace, session, purpose, tenant, and shared-memory boundaries as logical authority domains rather than assuming storage layout or agent identity provides sufficient isolation.

Boundary crossing, including sharing, exporting, copying, deriving, inheriting, or broadening scope, is treated as a governed consequence. Derived state must not silently gain broader scope than its sources.

ADR-022 acceptance requires a canonical isolation-domain contract, schema/receipt representation, recall integration, critical same-agent cross-project/task fixtures, unauthorized scope-promotion tests, and reconciliation with the future multi-agent shared-memory protocol.

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
