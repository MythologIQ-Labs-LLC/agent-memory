# ADR-013: Governed Recall Planner Is Required

## Status

Proposed

## Context

Retrieval is not memory.

Agentic systems often treat retrieval as the whole memory problem: search something, stuff it into context, and hope the model behaves. This is convenient in the same way that removing the brakes makes a car simpler.

A governed memory system needs recall planning that respects state, certification, dispute status, sensitivity, source trust, authority, and context boundaries.

## Decision

Agent Memory must include a governed recall planner.

The planner decides how to retrieve memory across exact lookup, graph traversal, evidence search, vector retrieval, policy recall, runtime context recall, and certification-aware recall.

## Consequences

### Positive

- prevents disputed memory from being used as canonical
- avoids unsafe recall of sensitive memory
- distinguishes exact lookup from similarity retrieval
- supports recall explanations
- makes context assembly policy-aware

### Negative

- adds another planning step before context assembly
- requires recall metadata from memory units
- may block convenient but unsafe retrieval

## Required recall paths

At minimum:

- exact identity lookup
- graph traversal
- evidence search
- vector or similarity retrieval
- policy recall
- runtime context recall
- certified memory recall
- disputed memory recall with warning semantics

## Required follow-up

Create and maintain:

```text
docs/20-governed-recall-planner.md
```

## Doctrine

Retrieval finds candidates.

Governed recall decides what may enter context and under what warning, scope, or authority.
