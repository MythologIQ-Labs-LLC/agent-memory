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

- **ADR-001 through ADR-019:** Accepted
- **ADR-020:** Proposed

ADR-020 remains Proposed because governed uncertainty still requires real end-to-end runtime proof.

## Important decision families

Rather than memorizing twenty filenames, think in decision families:

### Identity and provenance

Decisions about exact references, source evidence, derivation, and durable traceability.

### Lifecycle and persistence

Decisions about decay, consolidation, retention, correction, forgetting, and inherited state.

### Governance and PAMA

Decisions about mutation authority, consequence classes, certification, and separating learned pressure from permission.

### Composition and security

Decisions about component boundaries, scope, privacy, trust, conflict, and multi-memory behavior.

### Governed uncertainty

The current frontier: preserving probabilistic interpretation while formally bounding consequential actions.

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

- **[Governed Uncertainty](Governed-Uncertainty)** for ADR-020
- **[Contributing](Contributing)** for the change process
