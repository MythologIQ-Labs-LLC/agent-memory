# ADR-003: Crystallization Requires Certification

## Status

Proposed

## Context

Crystallization moves memory into a durable or exact-address retrievable state. That transition can create long-lived agent behavior, so it cannot be granted by repetition, retrieval frequency, or saturation alone.

## Decision

Crystallization requires certification or an explicitly scoped policy exception.

Certification may include human approval, test evidence, cryptographic verification, corroboration, policy approval, or a ledgered gate specific to the memory type.

## Consequences

### Positive

- prevents accidental permanence
- creates an audit point for durable memory
- preserves correction and dispute pathways
- aligns memory permanence with governance

### Negative

- adds friction to promotion
- requires implementation-specific certification mechanisms

## Required gate

```text
can_crystallize =
  identity_resolved
  and provenance_present
  and saturation >= calibrated_threshold
  and pama_authority == allow
  and certification_gate == pass
  and dispute_status == clear
```

## Doctrine

Crystallization is a governed transition.

It is not a reward for being repeated often enough.
