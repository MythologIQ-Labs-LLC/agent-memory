# ADR-013: Governed Recall Planner Is Required

## Status

Proposed

## Context

Retrieval is not memory.

A governed memory system needs recall planning that respects current state, certification, dispute status, sensitivity, source trust, tenancy, authority, and context boundaries.

Candidate generation may legitimately be probabilistic. Recall admission is a governed decision.

## Decision candidate

Agent Memory should include a governed recall planner or equivalent recall-admission component contract.

The planner should compose exact lookup, graph traversal, evidence search, semantic retrieval, temporal retrieval, procedural recall, and policy constraints without treating relevance as permission.

## Required invariant

```text
candidate_generation may be probabilistic
relevance != permission
prohibited_memory never enters admitted context
```

## Consequences

### Positive

- prevents disputed or wrong-scope memory from entering context as canonical
- distinguishes exact lookup from similarity retrieval
- supports recall explanations and composition checks
- makes context assembly policy-aware

### Negative

- adds a governance step before context assembly
- requires recall metadata and destination context
- may reduce convenient but unsafe recall

## Required follow-up before acceptance

Create and audit:

```text
docs/26-governed-recall-planner.md
```

Then add conformance evidence for:

- high-relevance wrong-tenant memory
- disputed canonical memory
- uncertain sensitivity
- unsafe multi-memory composition
- stochastic candidate ordering under fixed admission policy

## Doctrine candidate

Retrieval finds candidates.

Governed recall decides what may enter context.
