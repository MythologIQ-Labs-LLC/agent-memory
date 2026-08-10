# ADR-019: Memory Quality Metrics Are Required

## Status

Proposed

## Context

Conformance fixtures test defined cases, but implementations can still degrade over time through stale recall, poor correction, over-retention, under-retention, unsafe context assembly, calibration drift, or authority-boundary failures.

Ongoing metrics are required to distinguish a memory system that passed yesterday's fixture from one that remains healthy today.

## Decision candidate

Agent Memory must define ongoing memory-quality metrics across retention, forgetting, retrieval, uncertainty, correction, governance, security, privacy, and agent outcomes.

Metrics should be segmented by memory class and consequence class where aggregate numbers would hide risk.

## Required metric families

At minimum:

- false permanence rate
- valuable-memory loss / false evaporation
- stale recall rate
- disputed canonical use rate
- correction latency and propagation
- provenance retention rate
- source-trust calibration/degradation
- unsafe recall and overbroad context rate
- cross-scope leakage rate
- deletion completeness/residue
- successful rollback or recovery rate
- certification failure catch rate
- boundary instability rate
- abstention rate and quality
- estimator disagreement rate
- out-of-calibration-scope rate
- blocked-action escape rate
- stochastic action-set violation rate
- memory-guided task success
- repeated-failure avoidance

## Consequences

### Positive

- supports continuous evaluation beyond fixture snapshots
- detects drift and degradation
- gives implementations comparable outcome families
- makes optimization tradeoffs visible

### Negative

- requires telemetry, workloads, and reporting
- metrics can be gamed if detached from adversarial fixtures and evidence
- some metrics require domain-specific interpretation

## Required follow-up before acceptance

Create and audit:

```text
docs/32-memory-quality-metrics.md
```

Then map the metrics into conformance-report schema and implementation evidence.

## Doctrine candidate

Conformance shows a system can satisfy defined invariants under test.

Quality metrics show whether it continues to do so under real memory pressure and drift.
