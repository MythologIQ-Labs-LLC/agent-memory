# ADR-011: Temporal Causality Is Required for Memory Evolution

## Status

Proposed

## Context

Memory changes over time. A memory may become stale, superseded, corrected, disputed, or historically relevant.

Time-based decay alone does not explain why a memory changed. It only says that time passed, which is technically true and architecturally lazy.

Decision memory, code evolution, organizational memory, agent learning, and correction flows all need causal explanation.

## Decision

Agent Memory must include a temporal causality layer.

The layer will represent event order, causal links, supersession, correction history, and causal recall requirements.

## Consequences

### Positive

- distinguishes stale from superseded
- supports causal recall
- preserves decision and correction history
- improves code-evolution memory
- helps explain why memory changed

### Negative

- requires event and causal-link modeling
- increases complexity of memory state transitions
- requires careful treatment of historical claims

## Required distinctions

The architecture must distinguish:

- stale memory
- superseded memory
- corrected memory
- disputed memory
- historically relevant memory
- currently canonical memory

## Required follow-up

Create and maintain:

```text
docs/18-temporal-causality-layer.md
```

## Doctrine

Memory does not only decay.

Memory evolves through causes, consequences, corrections, and supersession.
