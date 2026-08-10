# ADR-014: Schema Registry and Type Evolution Are Needed

## Status

Proposed

## Context

The repository contains initial schemas for memory units and conformance reports. As implementations adopt the doctrine, those schemas will evolve.

Without explicit schema governance, implementation-specific fields can leak into doctrine-level objects, uncertainty semantics can be lost across adapters, and migrations can become oral tradition, which is how software projects summon ghosts.

## Decision candidate

Agent Memory should define a schema registry and type-evolution strategy.

The registry should govern doctrine-level types while allowing implementation-specific extension under explicit compatibility rules.

It should define representations for at least:

- memory unit identity and lifecycle state
- provenance and acquisition mode
- estimator provenance and uncertainty
- policy and authority references
- permitted-action sets
- decision receipts
- deletion/tombstone state
- schema version and migration metadata

## Consequences

### Positive

- prevents schema drift and semantic type erasure
- supports cross-repo adoption
- enables versioned conformance fixtures
- makes migrations explicit

### Negative

- adds governance overhead
- requires compatibility and migration rules
- can slow experimentation if extension mechanisms are too rigid

## Required follow-up before acceptance

Create and audit:

```text
docs/27-schema-registry-and-type-evolution.md
```

Then reconcile the existing schemas and fixtures against the registry.

## Doctrine candidate

Schemas are part of memory governance.

A memory object that cannot evolve without losing semantic meaning cannot remain canonical across implementations.
