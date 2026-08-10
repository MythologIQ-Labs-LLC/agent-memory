# ADR-016: Actor Scope, Consent, and Tenancy Are Required

## Status

Proposed

## Context

Agent Memory may operate across users, agents, organizations, projects, repositories, tools, and products.

Without explicit actor scope, delegation, consent, and tenancy boundaries, a memory may be valid in one context and unsafe in another.

Examples:

- a user preference must not silently become organization policy
- a project decision must not leak into another tenant
- an agent must not inherit authority merely by reading another agent's memory
- shared memory must not bypass consent, role, or purpose boundaries

## Decision candidate

Agent Memory must define actor scope, consent, delegation, and tenancy as first-class governance concerns.

Memory units and decision receipts should carry enough metadata to determine who may store, mutate, recall, export, share, correct, or delete them.

Relevance, trust, or inherited access must not create broader authority.

## Required dimensions

- actor identity
- agent identity
- user/principal identity
- organization or tenant
- project/repository scope
- role or capability
- consent state
- purpose limitation
- delegation scope
- expiry/revocation state
- re-sharing rights

## Consequences

### Positive

- prevents cross-user and cross-tenant leakage
- supports multi-agent and organizational memory safely
- improves PAMA and recall-admission decisions
- clarifies shared-memory ownership

### Negative

- requires richer scope metadata
- complicates shared-memory protocols and inheritance
- requires consent/revocation propagation

## Required follow-up before acceptance

Create and audit:

```text
docs/29-actor-scope-consent-and-tenancy.md
```

Then add conformance cases for scope laundering, delegated-authority expiry, and cross-tenant retrieval.

## Doctrine candidate

Memory authority is scoped.

A memory that is useful or valid for one actor, tenant, or purpose is not automatically usable everywhere else.
