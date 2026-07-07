# ADR-014: Schema Registry and Type Evolution Are Needed

## Status

Proposed

## Context

The repository now contains initial schemas for memory units and conformance reports. As implementations adopt the doctrine, schemas will need to evolve.

Without explicit schema governance, implementation-specific fields can leak into doctrine-level objects, memory units can become incompatible across systems, and migration rules can become oral tradition, which is how software projects summon ghosts.

## Decision

Agent Memory should define a schema registry and type-evolution strategy.

This should remain an architecture component candidate until adapter contracts and implementation ownership are clearer.

## Consequences

### Positive

- prevents schema drift
- supports cross-repo adoption
- enables versioned conformance fixtures
- makes memory-unit migrations explicit

### Negative

- adds governance overhead
- requires compatibility rules
- may slow experimentation if applied too early

## Required follow-up

Create an issue to define:

```text
docs/21-schema-registry-and-type-evolution.md
```

## Doctrine

Schemas are part of memory governance.

A memory object that cannot evolve safely cannot remain canonical across implementations.
