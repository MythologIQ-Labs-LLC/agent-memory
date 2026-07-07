# ADR-010: Conflict Resolution Is a Separate Component

## Status

Proposed

## Context

The lifecycle state machine includes a `disputed` state. That state identifies a problem, but it does not resolve the problem.

Conflicts can arise between:

- facts
- decisions
- time windows
- policies
- source reliability scores
- user corrections
- implementation states
- code graph evidence

If conflict resolution is embedded ad hoc inside each implementation, the same memory dispute can resolve differently across systems.

## Decision

Conflict resolution must be treated as a separate component.

The component will classify conflict type, rank evidence, determine whether to correct, demote, split scope, escalate, preserve historical minority claims, or prune.

## Consequences

### Positive

- prevents silent overwrite
- gives disputed memory a deterministic path forward
- allows temporal supersession without losing historical context
- supports policy-aware reconciliation

### Negative

- requires conflict taxonomy and rules
- requires implementations to expose enough evidence for resolution
- may require human escalation for high-risk disputes

## Required conflict types

At minimum:

- factual contradiction
- temporal supersession
- scope mismatch
- policy conflict
- source reliability conflict
- user correction conflict
- implementation drift

## Required follow-up

Create and maintain:

```text
docs/17-conflict-resolution-engine.md
```

## Doctrine

Dispute is a state.

Resolution is a component.
