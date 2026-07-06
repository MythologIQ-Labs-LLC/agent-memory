# ADR-002: Saturation Is Routing, Not Truth

## Status

Proposed

## Context

Saturation is useful for deciding whether memory should persist, decay, route, or become a crystallization candidate. However, high saturation can be produced by flawed signals such as access-spam, repeated incorrect claims, or narrow fiber definitions.

A fully pinned object can still be wrong.

## Decision

Saturation is a calibrated lifecycle routing score.

It must not be treated as correctness, integrity, identity, or certification.

## Consequences

### Positive

- prevents hallucination permanence
- allows saturation to support routing without overclaiming truth
- makes trap-class testing mandatory
- preserves the role of certification and provenance

### Negative

- requires more than one signal to promote memory
- requires calibration before thresholds can be trusted

## Required rule

```text
high_saturation != true
high_saturation != certified
high_saturation == candidate_for_routing_or_review
```

## Doctrine

Saturation can propose. Certification must confirm.
