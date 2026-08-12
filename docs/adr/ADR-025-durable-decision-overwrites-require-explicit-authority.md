# ADR-025: Durable Decision Overwrites Require Explicit Authority

Status: Proposed

Date: 2026-08-12

## Context

Issues #137 and #138 expose a critical boundary in agent memory systems: agents may be able to detect contradiction, propose correction, and identify supersession candidates, but that does not automatically grant authority to overwrite durable decisions.

Durable decisions are different from ordinary observations. They may encode human approval, policy, governance posture, scope boundaries, or operational commitments. Allowing agents to quietly overwrite earlier durable decisions converts memory into an argument engine with a commit bit. That is not governance.

The repository already treats PAMA as the mutation authority boundary and conflict resolution as a separate component. This ADR clarifies that durable decision overwrite is a distinct authority event and must be resolved before commit.

## Decision

The system must distinguish agent-proposed supersession from committed durable decision overwrite.

Agents may propose corrections, supersession links, conflict candidates, replacement records, and supporting evidence. They must not independently overwrite, reverse, retire, or supersede prior durable decisions unless the applicable authority policy explicitly grants that mutation class for the affected scope.

For high-impact decisions or prior human-confirmed decisions, the default posture is human confirmation before overwrite unless a bounded policy explicitly delegates that authority.

Rejected, expired, or unapproved overwrite proposals remain auditable evidence and must not mutate durable decision state.

## Rationale

The useful work agents can do is proposing, gathering evidence, detecting contradiction, and presenting candidate resolutions. The risky work is granting those proposals durable authority without a valid policy basis.

This ADR preserves automation where it is valuable while preventing silent decision reversal. It also keeps the repository aligned with deterministic governance: probabilistic discovery may identify a possible correction, but deterministic authority controls whether durable state changes.

## Consequences

### Positive

- Durable decision overwrite becomes explicit and auditable.
- Human-confirmed decisions cannot be silently displaced by agent consensus.
- Agent proposals remain useful without becoming unauthorized mutation.
- PAMA retains control over mutation authority.
- Conflict resolution has a clear handoff into authority evaluation.

### Negative

- Some overwrites require human review, adding latency.
- Implementations must classify ordinary memory correction separately from durable decision overwrite.
- Delegated authority policies must be precise enough to avoid rubber-stamping.
- User interfaces and APIs must represent pending, approved, rejected, and expired overwrite proposals.

## Implementation notes

A conforming implementation should represent at least:

- proposal identifier;
- proposing actor;
- affected durable decision record;
- proposed replacement or supersession record;
- rationale and evidence basis;
- requested mutation class;
- authority policy used for evaluation;
- approval, rejection, or expiry status;
- approver identity where human confirmation is required;
- final commit receipt only when approved.

The proposal record may be durable evidence. It is not itself an overwrite unless approved under the applicable authority policy.

## Validation and acceptance

This ADR should not advance beyond Proposed until the repository includes evidence for:

- an agent-proposed overwrite that remains pending or rejected without mutating durable decision state;
- a human-confirmed durable decision overwrite that creates append-only supersession evidence;
- an explicitly delegated low-risk overwrite case, if supported, with bounded policy evidence;
- negative-path coverage for unauthorized overwrite, stale evidence, silent decision reversal, and agent-collusion scenarios;
- documentation showing composition with PAMA, conflict resolution, temporal causality, lifecycle state, and audit events.

## Related

- #137
- #138
- #144
- ADR-004: PAMA Controls Mutation Authority
- ADR-010: Conflict Resolution Is a Separate Component
- ADR-011: Temporal Causality Is Required for Memory Evolution
- ADR-017: Memory Observability and Audit Events Are Required
- ADR-020: Probabilistic Discovery, Deterministic Governance
- ADR-023: Corrections Are Supersession, Not Deletion
- ADR-024: Shared Memory Writes Require Pre-Write Claims
