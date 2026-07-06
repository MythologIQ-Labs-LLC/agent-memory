# ADR-006: Neurospace Is Runtime Memory Space

## Status

Proposed

## Context

COREFORGE Vault and Neurospace provide the local product runtime where agents assemble, traverse, retrieve, and use memory.

Runtime memory has different responsibilities from identity, scoring, governance, and certification.

## Decision

Neurospace is the operational runtime memory space.

It consumes identity, evidence, saturation, governance, and certification signals to support agent recall and action. It must not redefine those layers silently.

## Consequences

### Positive

- keeps COREFORGE product behavior aligned with doctrine
- separates user-facing memory use from canonical permanence
- enables correction, dispute, and governance UI flows

### Negative

- requires Neurospace to expose state and authority metadata
- requires runtime memory to distinguish operational use from canonical use

## Runtime rule

```text
operationally_useful != canonical
```

A memory may be useful in a context window without being crystallized.

## Doctrine

Neurospace is where memory is used.

It is not where memory becomes true by convenience.
