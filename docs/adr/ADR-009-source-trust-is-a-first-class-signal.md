# ADR-009: Source Trust Is a First-Class Signal

## Status

Proposed

## Context

Evidence and provenance tell the system where memory came from and what supports it. They do not fully answer whether a source remains reliable over time.

A low-quality source can produce high volume. A stale source can remain cited. An agent can recursively cite its own prior claims. A single-source assertion can become over-weighted if the system treats provenance as equivalent to trust.

That is how memory systems develop the confidence of a freshman philosophy major with a search bar. Delightful. Unsafe.

## Decision

Source trust and reputation must be a first-class signal in the architecture.

The system should track source class, reliability, contradiction history, freshness, authority scope, and self-citation risk.

## Consequences

### Positive

- prevents high-volume low-quality sources from dominating saturation
- improves evidence weighting
- supports conflict resolution
- helps detect recursive self-citation
- makes source reliability visible to certification gates

### Negative

- requires source metadata beyond simple provenance
- requires policy for source demotion and rehabilitation
- may complicate conformance fixtures

## Required source classes

At minimum, implementations should distinguish:

- authoritative
- observed
- inferred
- synthetic
- user-provided
- agent-generated
- external
- code-derived
- policy-derived

## Required follow-up

Create and maintain:

```text
docs/16-source-trust-and-reputation.md
```

## Doctrine

Provenance says where memory came from.

Source trust says how much weight that source deserves now.
