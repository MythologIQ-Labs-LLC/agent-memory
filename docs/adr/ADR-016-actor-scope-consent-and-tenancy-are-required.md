# ADR-016: Actor Scope, Consent, and Tenancy Are Required

## Status

Proposed

## Context

Agent Memory may operate across users, agents, organizations, projects, repositories, tools, and products.

Without explicit actor scope and consent boundaries, a memory may be valid in one context and unsafe in another.

Examples:

- a user preference should not silently become an organization policy
- a project decision should not leak into another tenant
- an agent should not inherit authority from another agent by reading its memory
- a shared memory should not bypass consent or role boundaries

## Decision

Agent Memory must define actor scope, consent, and tenancy boundaries as first-class governance concerns.

Memory units should carry enough scope metadata to determine who may store, mutate, recall, export, correct, or delete them.

## Consequences

### Positive

- prevents cross-user leakage
- supports multi-agent and organizational memory safely
- improves PAMA risk classification
- enables role-aware recall and mutation
- clarifies product integration boundaries

### Negative

- requires actor and tenant metadata
- complicates shared memory protocols
- may reduce convenience for broad context assembly

## Required scope dimensions

At minimum:

- actor identity
- agent identity
- user identity
- organization or tenant
- project or repository
- role or permission level
- consent state
- delegation scope
- expiration or revocation status

## Required follow-up

Create and maintain:

```text
docs/24-actor-scope-consent-and-tenancy.md
```

## Doctrine

Memory authority is scoped.

A memory that is valid for one actor, tenant, or purpose is not automatically valid everywhere else.
