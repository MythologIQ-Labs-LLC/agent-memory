# ADR-019: Memory Quality Metrics Are Required

## Status

Proposed

## Context

The doctrine defines conformance fixtures and calibration reporting, but it does not yet define ongoing memory quality metrics.

An implementation may pass fixtures and still degrade over time through stale recall, poor correction handling, over-retention, under-retention, unsafe context assembly, or excessive false permanence.

Because apparently even memory systems need performance reviews. Horrifying, but useful.

## Decision

Agent Memory must define ongoing memory quality metrics.

These metrics should evaluate how well an implementation remembers, forgets, corrects, recalls, protects, and explains memory over time.

## Consequences

### Positive

- supports continuous evaluation beyond fixture snapshots
- detects degradation over time
- gives implementation repos comparable quality targets
- helps tune saturation, decay, recall, and certification policies

### Negative

- requires telemetry and reporting
- may require workload-specific benchmarks
- quality metrics can be gamed if not tied to trap classes and audit evidence

## Required metric families

At minimum:

- false permanence rate
- false evaporation rate
- unsafe recall rate
- disputed canonical use rate
- correction latency
- provenance retention rate
- source trust degradation rate
- overbroad context assembly rate
- successful rollback rate
- certification failure catch rate
- stale memory recall rate

## Required follow-up

Create and maintain:

```text
docs/27-memory-quality-metrics.md
```

## Doctrine

Conformance proves a system can behave correctly under defined tests.

Quality metrics show whether it keeps behaving correctly over time.
