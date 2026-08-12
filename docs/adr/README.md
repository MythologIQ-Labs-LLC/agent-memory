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
ADR-001 through ADR-020: Accepted
ADR-021: Proposed
ADR-022: Accepted
ADR-023: Proposed
ADR-024: Proposed
ADR-025: Proposed
ADR-026: Proposed
ADR-027: Proposed
ADR-028: Proposed
ADR-029: Proposed
```

ADRs 001-020 and ADR-022 have satisfied their respective doctrine-maturity gates. ADR-020 is deliberately stronger than documentation-only acceptance: it required executable end-to-end runtime evidence and adversarial negative paths before acceptance.

ADR-021 proposes the interoperability boundary for **portable memory-governance evidence**. It keeps Agent Memory authoritative for memory semantics, PAMA, lifecycle obligations, and canonical decision receipts while allowing external trust systems such as AgenTrust to verify and correlate evidence without redefining those semantics.

ADR-022 establishes **memory isolation domains and controlled boundary crossing** as first-class architecture. It extends ADR-016 by making same-agent cross-project/task separation, shared-memory domains, derived-scope inheritance, and scope crossing explicitly governable rather than leaving them as implied metadata filters.

ADR-023 proposes that durable correction is **append-only supersession rather than destructive deletion**. ADR-024 proposes **pre-write coordination for shared-memory mutation**. ADR-025 proposes **explicit authority for overwriting durable decision memory**. All remain Proposed until their named evidence gates are satisfied.

ADR-026 proposes a source-neutral epistemic boundary: **claim origin establishes provenance, not evidentiary authority**. ADR-027 proposes **governed re-admission for explicitly rejected values** so a corrected value cannot silently return merely by acquiring a fresh identity. Both remain Proposed while their linked evidence programs run.

ADR-028 proposes a **language-neutral normative core with optional implementation and interoperability profiles**. It permits Python-first reference tooling, Rust high-assurance implementations, and UOR/AGT/MCP integrations without allowing any one language or external ecosystem to become the definition of Agent Memory doctrine.

ADR-029 proposes a three-layer governance-consumer boundary: **canonical Agent Memory core -> vendor-neutral Governance Context Projection -> consumer-specific adapter**. The projection is reconstructable derived context, not canonical memory truth, standing permission, or a final external-governance verdict.

## Current status policy

A decision may move from Proposed to Accepted when:

1. its architectural boundary is sufficiently defined
2. it is integrated consistently into canonical doctrine
3. known material contradictions have been resolved or documented
4. required foundational documentation exists
5. any repository-level schema/fixture prerequisites named by the ADR are satisfied
6. acceptance does not depend on runtime evidence the ADR explicitly says is still missing

If an ADR explicitly requires stronger evidence before acceptance, that requirement controls.

The evidence policy is source-neutral. Native authorship, maintainer status, external publication, implementation popularity, AI generation, or prior acceptance do not make a claim immune to challenge. See [`../policies/EVIDENCE_PROMOTION.md`](../policies/EVIDENCE_PROMOTION.md).

## Governed uncertainty

[`ADR-020`](ADR-020-probabilistic-discovery-deterministic-governance.md) is **Accepted**.

Its acceptance required at least one real implementation mapped and tested end to end across:

```text
estimate / proposal
  -> governance envelope
  -> permitted action set
  -> selected action
  -> committed consequence
```

The repository now has executable evidence for stochastic containment, cross-scope recall, concurrency conflict handling, deletion residue and transitive deletion behavior, reconstructable receipts, adversarial boundary enforcement, and a pinned real-substrate path. The P10 acceptance audit maps all fourteen ADR-020 gates to current evidence.

Acceptance does not upgrade the narrow reference adapter to a higher cumulative conformance level. Doctrine maturity and implementation conformance remain separate claims.

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

[`ADR-022`](ADR-022-memory-isolation-domains-and-controlled-boundary-crossing.md) is **Accepted**.

Its central boundary is:

```text
same agent / same store
        !=
same authorized memory domain
```

It treats project, task, workspace, session, purpose, tenant, and shared-memory boundaries as logical authority domains rather than assuming storage layout or agent identity provides sufficient isolation.

Boundary crossing, including sharing, exporting, copying, deriving, inheriting, or broadening scope, is treated as a governed consequence. Derived state must not silently gain broader scope than its sources.

Acceptance is backed by the canonical isolation-domain contract, additive schema/receipt representation, governed-recall enforcement, same-agent cross-project/task fixtures, derived-scope propagation, unauthorized scope-promotion tests, shared-space member/non-member recall tests, executable crossing receipts, and reconciliation with the future multi-agent shared-memory protocol. This is a doctrine-maturity statement, not universal production-runtime conformance.

## Candidate durable-mutation and interoperability decisions

The current Proposed ADRs intentionally separate several related but non-identical questions:

- [`ADR-023`](ADR-023-corrections-are-supersession-not-deletion.md): preserve correction history while removing superseded state from current truth;
- [`ADR-024`](ADR-024-shared-memory-writes-require-prewrite-claims.md): coordinate shared durable writes before commit;
- [`ADR-025`](ADR-025-durable-decision-overwrites-require-explicit-authority.md): require explicit authority before overwriting durable decision state;
- [`ADR-026`](ADR-026-origin-is-provenance-not-evidentiary-authority.md): apply the same evidence discipline to claims regardless of origin;
- [`ADR-027`](ADR-027-rejected-values-require-governed-readmission.md): require governed re-admission when a corrected/rejected value later reappears;
- [`ADR-028`](ADR-028-language-neutral-core-and-optional-implementation-profiles.md): preserve a language-neutral normative core while allowing optional implementation/interoperability profiles;
- [`ADR-029`](ADR-029-governance-projection-is-derived-context-not-authority.md): expose vendor-neutral governance context as reconstructable derived state without turning consumer semantics into core memory doctrine.

These ADRs must not be collapsed into a single broad "memory safety" or "governance integration" claim. Each has its own acceptance evidence and may be accepted, narrowed, or rejected independently.

## Implementation portability and ecosystem boundaries

[`ADR-028`](ADR-028-language-neutral-core-and-optional-implementation-profiles.md) is **Proposed**.

Its central boundary is:

```text
normative doctrine / schemas / fixtures
        !=
reference implementation language
        !=
optional implementation or interoperability profile
```

Python may remain the practical reference/integration language where it maximizes ecosystem reach. Rust is a first-class implementation language for high-assurance or performance-sensitive components. UOR, AGT, MCP, and other external systems may supply reusable primitives or profiles, but none becomes authoritative for Agent Memory semantics merely through adoption.

ADR-028 acceptance requires cross-language conformance evidence and a negative path demonstrating that content-address verification does not confer memory authority.

## Governance Context Projection

[`ADR-029`](ADR-029-governance-projection-is-derived-context-not-authority.md) is intentionally **Proposed**.

Its central boundary is:

```text
canonical Agent Memory primitives
        |
        v
Governance Context Projection
  evidence / precedent / material conditions
        |
        v
consumer-specific adapter
  policy vocabulary / risk / approval / enforcement
```

The projection does not emit a final consumer verdict or standing permission. It is designed so consumers can use remembered rationale, conditions, negative precedent, validity, and outcomes without requiring Agent Memory core to mirror a DashClaw-, AGT/ACS-, or other vendor-specific data model.

ADR-029 complements ADR-028: the normative core remains language-neutral, the governance projection remains vendor-neutral, and concrete consumers stay behind optional adapters.

ADR-029 acceptance requires a reconstructable reference builder, adversarial near-match coverage, provenance/scope preservation, privacy/minimization evidence, and at least one consumer integration that demonstrates value without pushing consumer-specific fields into the canonical memory-unit schema.

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
- [`../34-adapter-contracts.md`](../34-adapter-contracts.md)
- [`../41-memory-isolation-domains-and-governed-crossing.md`](../41-memory-isolation-domains-and-governed-crossing.md)
- [`../profiles/governance-context-projection-profile.md`](../profiles/governance-context-projection-profile.md)
