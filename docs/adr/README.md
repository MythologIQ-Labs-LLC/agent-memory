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
ADR-024: Accepted
ADR-025: Proposed
ADR-026: Proposed
ADR-027: Proposed
ADR-028: Accepted
ADR-029: Proposed
ADR-030: Accepted
ADR-031: Accepted
ADR-032: Accepted
```

ADRs 001-020, ADR-022, ADR-024, ADR-028, ADR-030, ADR-031, and ADR-032 have satisfied their respective doctrine-maturity gates. ADR-020 is deliberately stronger than documentation-only acceptance: it required executable end-to-end runtime evidence and adversarial negative paths before acceptance. ADR-024 likewise required executable positive and negative shared-write coordination evidence before promotion.

ADR-021 proposes the interoperability boundary for **portable memory-governance evidence**. It keeps Agent Memory authoritative for memory semantics, PAMA, lifecycle obligations, and canonical decision receipts while allowing external trust systems such as AgenTrust to verify and correlate evidence without redefining those semantics.

ADR-022 establishes **memory isolation domains and controlled boundary crossing** as first-class architecture. It extends ADR-016 by making same-agent cross-project/task separation, shared-memory domains, derived-scope inheritance, and scope crossing explicitly governable rather than leaving them as implied metadata filters.

ADR-023 proposes that durable correction is **append-only supersession rather than destructive deletion**. ADR-024 establishes **pre-write coordination for shared-memory mutation** as accepted doctrine. ADR-025 proposes **explicit authority for overwriting durable decision state**. The #144 implementation slice now supplies executable proposal/authority/PAMA/supersession evidence for ADR-025, but #144 explicitly excludes automatic maturity promotion, so ADR-025 remains Proposed pending a separate doctrine-governance decision.

ADR-026 proposes a source-neutral epistemic boundary: **claim origin establishes provenance, not evidentiary authority**. ADR-027 proposes **governed re-admission for explicitly rejected values** so a corrected value cannot silently return merely by acquiring a fresh identity. Both remain Proposed while their linked evidence programs run.

ADR-028 establishes a **language-neutral normative core with optional implementation and interoperability profiles**. It permits Python-first reference tooling, Rust high-assurance implementations, and UOR/AGT/MCP integrations without allowing any one language or external ecosystem to become the definition of Agent Memory doctrine.

ADR-029 proposes a three-layer governance-consumer boundary: **canonical Agent Memory core -> vendor-neutral Governance Context Projection -> consumer-specific adapter**. The projection is reconstructable derived context, not canonical memory truth, standing permission, or a final external-governance verdict.

ADR-030 establishes that temporal and authorization consumers require a **versioned compatibility/currentness evaluation** before a memory-derived projection can be treated as current policy input. Serialization success is not semantic compatibility, and historical temporal evidence is not current authority.

ADR-031 establishes a **layered temporal-commitment model**. Material temporal claims that determine historical identity belong inside deterministic content commitments, while signer attestation, signer trust, external witnessed time/transparency evidence, currentness, and PAMA authority remain distinct claims.

ADR-032 establishes **governed structural mutability**. Memory shape may adapt, and probabilistic or learned systems may discover and propose structural changes, but canonical structural consequences are committed only through a versioned deterministic authorized envelope or explicit authorized human decision. Authority escalates with semantic impact, blast radius, migration requirements, scope, authority effect, and irreversibility.

## Current status policy

A decision may move from Proposed to Accepted when:

1. its architectural boundary is sufficiently defined
2. it is integrated consistently into canonical doctrine
3. known material contradictions have been resolved or documented
4. required foundational documentation exists
5. any repository-level schema/fixture prerequisites named by the ADR are satisfied
6. acceptance does not depend on runtime evidence the ADR explicitly says is still missing

If an ADR explicitly requires stronger evidence before acceptance, that requirement controls. Satisfying an evidence prerequisite does not silently promote a Proposed ADR when the governing issue or decision process reserves maturity review as a separate action.

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

ADR-032 is a domain-specific strengthening of this boundary for canonical structural mutation: probabilistic systems may propose a structural change, but the authority determination that commits the canonical structural consequence must be deterministic and versioned or explicitly human-authorized.

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

## Shared durable-memory write coordination

[`ADR-024`](ADR-024-shared-memory-writes-require-prewrite-claims.md) is **Accepted**.

Its central boundary is:

```text
shared write intent
  -> bounded pre-write claim / lease / equivalent coordination
  -> current-state and conflict validation
  -> PAMA authority evaluation
  -> durable mutation or refusal
```

A claim grants the bounded opportunity to attempt the shared write. It does not grant the durable consequence.

Acceptance is backed by executable valid, conflicting, stale, expired, and unauthorized claim paths, schema-valid audit evidence for successful and failed claim outcomes, a negative test proving a valid claim cannot override PAMA `block`, and conflict-resolution documentation that settles competing shared-writer authority before commit. The reference lease coordinator is evidence for the contract, not a normative requirement that every implementation use the same primitive.

## Durable decision overwrite authority evidence

[`ADR-025`](ADR-025-durable-decision-overwrites-require-explicit-authority.md) remains **Proposed**.

The #144 reference slice now exercises:

```text
agent proposal
  -> exact overwrite-authority validation
  -> PAMA
  -> append-only supersession or refusal
```

The evidence includes proposal-without-mutation, human-confirmed overwrite, bounded delegated low-risk overwrite, stale proposal, agent-collusion rejection, authority-binding failures, append-only supersession, PAMA non-override, and versioned PAMA `decision_overwrite` representation. This closes implementation questions; it does not itself decide doctrine maturity.

## Candidate durable-mutation and interoperability decisions

The remaining Proposed ADRs intentionally separate several related but non-identical questions:

- [`ADR-021`](ADR-021-portable-memory-governance-evidence-boundary.md): define the portable memory-governance evidence boundary with external trust and attestation systems;
- [`ADR-023`](ADR-023-corrections-are-supersession-not-deletion.md): preserve correction history while removing superseded state from current truth;
- [`ADR-025`](ADR-025-durable-decision-overwrites-require-explicit-authority.md): require explicit authority before overwriting durable decision state;
- [`ADR-026`](ADR-026-origin-is-provenance-not-evidentiary-authority.md): apply the same evidence discipline to claims regardless of origin;
- [`ADR-027`](ADR-027-rejected-values-require-governed-readmission.md): require governed re-admission when a corrected/rejected value later reappears;
- [`ADR-029`](ADR-029-governance-projection-is-derived-context-not-authority.md): expose vendor-neutral governance context as reconstructable derived state without turning consumer semantics into core memory doctrine.

These ADRs must not be collapsed into a single broad "memory safety" or "governance integration" claim. Each has its own acceptance evidence and may be accepted, narrowed, or rejected independently.

## Implementation portability and ecosystem boundaries

[`ADR-028`](ADR-028-language-neutral-core-and-optional-implementation-profiles.md) is **Accepted**.

Its central boundary is:

```text
normative doctrine / schemas / fixtures
        !=
reference implementation language
        !=
optional implementation or interoperability profile
```

Python may remain the practical reference/integration language where it maximizes ecosystem reach. Rust is a first-class implementation language for high-assurance or performance-sensitive components. UOR, AGT, MCP, and other external systems may supply reusable primitives or profiles, but none becomes authoritative for Agent Memory semantics merely through adoption.

Acceptance is backed by the #232 UOR-Addr interoperability slice, including exact cross-language/content-reference compatibility evidence and negative paths proving that content identity does not confer memory authority or make UOR a required runtime dependency.

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

## Versioned temporal-policy projections

[`ADR-030`](ADR-030-temporal-policy-consumers-require-versioned-compatible-projections.md) is **Accepted**.

Its central boundary is:

```text
canonical Agent Memory state
        |
        v
versioned consumer projection
        |
        v
compatibility / currentness evaluation
        |
        v
external temporal or authorization consumer
```

A projection is not current merely because it serialized successfully or matched historical policy context. Compatibility binds source schema/currentness, projection identity/version, consumer/policy schema and capabilities, isolation strategy, and evidence. External policy may tighten consequences but cannot silently widen PAMA authority.

## Cryptographic temporal commitments

[`ADR-031`](ADR-031-temporal-claims-require-deterministic-content-commitments.md) is **Accepted**.

Its central boundary is:

```text
temporal claims + payload/schema/scope/order
        |
        v
deterministic content commitment
        |
        +--> signer attestation
        +--> optional external witness / transparency evidence
        |
        v
separate Agent Memory currentness + PAMA evaluation
```

The commitment provides exact historical identity for material temporal claims. Signer attestation is not signer trust, witnessed time is not event truth, predecessor chaining is not proof of complete or unique history, and cryptographic validity does not create lifecycle currentness or authority. The accepted evidence includes adversarial fork/gap behavior, supersession/currentness separation, witness-binding failures, optional UOR compatibility, and exact-head repository validation.

## Governed mutable memory structure

[`ADR-032`](ADR-032-governed-mutable-memory-structure.md) is **Accepted**.

Its central boundary is:

```text
learned / probabilistic structural discovery
        |
        v
structural proposal
        |
        v
deterministic semantic / migration / dependency / scope analysis
        |
        v
deterministic authorized envelope OR explicit human authority
        |
        v
committed structural consequence
```

The doctrine distinguishes canonical semantic shape, application/domain ontology, and derived/physical representation. Rebuild-only derived changes may be autonomous under deterministic maintenance policy. Bounded additive changes may be autonomous only when a versioned deterministic rule proves the authorized envelope. Semantic migrations and destructive/cross-scope/authority-bearing changes require explicit human authority unless a future accepted doctrine narrows an exact delegated class.

PAMA 1.2 remains conservatively stricter than the new doctrine because it routes all `domain_schema_mutation` outcomes to review or external verification. Issue #281 owns the implementation evidence needed before any narrower autonomous structural path is introduced.

## Canonical references

- [`../01-layer-model.md`](../01-layer-model.md)
- [`../04-governance-and-pama.md`](../04-governance-and-pama.md)
- [`../06-conformance-test-plan.md`](../06-conformance-test-plan.md)
- [`../11-component-architecture.md`](../11-component-architecture.md)
- [`../17-conflict-resolution-engine.md`](../17-conflict-resolution-engine.md)
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
- [`../42-governed-mutable-memory-fabric.md`](../42-governed-mutable-memory-fabric.md)
- [`../profiles/durable-decision-memory-profile.md`](../profiles/durable-decision-memory-profile.md)
- [`../profiles/governance-context-projection-profile.md`](../profiles/governance-context-projection-profile.md)
- [`../profiles/temporal-commitment-evidence-profile.md`](../profiles/temporal-commitment-evidence-profile.md)
