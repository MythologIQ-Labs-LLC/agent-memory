# Architecture Decisions

Agent Memory uses Architecture Decision Records (ADRs) to preserve why important doctrine choices exist and when they should be reconsidered.

## Status semantics

ADR status describes **doctrine maturity**, not runtime implementation completeness.

| Status | Meaning |
|---|---|
| Proposed | The decision is under active evaluation and has not yet met its acceptance bar. |
| Accepted | The decision is canonical doctrine for this repository. |
| Superseded | A later decision replaces it while preserving history. |
| Rejected | The proposed direction was considered and intentionally not adopted. |

An Accepted ADR does **not** mean every mapped product implements it. That would be a convenient fiction, but still a fiction.

## Current state

- **ADR-001 through ADR-020:** Accepted
- **ADR-021:** Proposed, portable memory-governance evidence boundary
- **ADR-022:** Accepted, memory isolation domains and controlled boundary crossing
- **ADR-023:** Proposed, correction as supersession rather than deletion
- **ADR-024:** Accepted, pre-write coordination for shared-memory mutation
- **ADR-025:** Proposed, explicit authority for durable decision overwrite
- **ADR-026:** Proposed, origin is provenance rather than evidentiary authority
- **ADR-027:** Proposed, governed re-admission for rejected values
- **ADR-028:** Proposed, language-neutral core with optional implementation/interoperability profiles
- **ADR-029:** Proposed, Governance Context Projection as derived context rather than authority

Each Proposed ADR has its own acceptance evidence. A green implementation slice does not silently accept a doctrine decision whose ADR demands broader evidence.

## Important decision families

Rather than memorizing twenty-nine filenames, think in decision families.

### Identity and provenance

Decisions about exact references, source evidence, derivation, durable traceability, and source-neutral evidence scrutiny.

### Lifecycle and persistence

Decisions about decay, consolidation, retention, correction, supersession, re-admission, forgetting, and inherited state.

### Governance and PAMA

Decisions about mutation authority, consequence classes, certification, and separating learned pressure from permission.

ADR-024 adds the shared-write coordination boundary:

```text
shared write intent
  -> pre-write claim / lease / equivalent coordination
  -> current-state and conflict validation
  -> PAMA authority evaluation
  -> durable mutation or refusal
```

A valid claim gives a writer the bounded opportunity to attempt a shared mutation. It does not grant permission to make that mutation durable. ADR-024 was accepted only after executable valid, conflicting, stale, expired, unauthorized, audit, and PAMA-non-override paths passed the repository evidence gates.

### Composition and security

Decisions about component boundaries, scope, isolation domains, privacy, trust, conflict, and multi-memory behavior.

### Governed uncertainty

ADR-020 establishes the deterministic governance boundary around uncertain or probabilistic discovery.

### Implementation portability

ADR-028 separates normative doctrine from implementation language and optional ecosystem profiles:

```text
normative doctrine / schemas / fixtures
        !=
reference implementation language
        !=
optional implementation or interoperability profile
```

Python, Rust, UOR, AGT, MCP, and future ecosystems may participate without becoming the definition of Agent Memory.

### Interoperability and governance projection

ADR-021 and ADR-029 preserve two different directions across an external-governance boundary:

```text
ADR-029
memory-derived context
  -> external governance decision

ADR-021
Agent Memory decision / execution evidence
  -> external verifier / attestation system
```

ADR-029's core ownership model is:

```text
Agent Memory core
  -> Governance Context Projection
  -> consumer-specific adapter
  -> governance / approval / enforcement system
```

The projection is remembered context, not standing permission or a final policy verdict. ADR-029 complements ADR-028 by keeping the projection vendor-neutral while the normative core remains language-neutral. See **[Governance Projection](Governance-Projection)**.

## When an ADR should change

An accepted decision should be revisited when there is:

- contradictory research with material architectural consequences
- a reproducible implementation failure
- a security or privacy failure mode the decision does not contain
- a semantic incompatibility discovered in schemas or composition
- evidence that a simpler architecture satisfies the same constraints
- new interoperability requirements that invalidate the original boundary

Preference alone is not enough. Neither is “the new framework has a nicer README.”

## Proposing a decision change

A strong proposal states:

1. current decision
2. new evidence or failure mode
3. proposed replacement or clarification
4. affected docs, schemas, fixtures, and implementations
5. compatibility impact
6. falsification/rejection criteria

Use the **Doctrine or architecture proposal** issue form for new ADR work.

## Canonical source

ADR index: https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/main/docs/adr

The canonical ADR files, not this Wiki summary, determine current decision text and status.

## Next

- **[Governed Uncertainty](Governed-Uncertainty)** for deterministic governance around probabilistic discovery
- **[Governance Projection](Governance-Projection)** for ADR-029 and governance-consumer interoperability
- **[Aligned Projects & Intellectual Lineage](Aligned-Projects-and-Intellectual-Lineage)** for current external governance comparators
- **[Contributing](Contributing)** for the change process
