# Implementation Guide

Agent Memory is implementation-neutral. A runtime does not need to copy one storage engine or framework. It needs to preserve the architectural boundaries that make retained state governable.

## Minimal runtime loop

A useful implementation should be able to show this chain explicitly:

```text
observation / request
  → evidence + provenance
  → estimate / proposal
  → PAMA governance decision
  → permitted action set
  → selected action
  → state transition
  → decision receipt
  → retained state
  → governed recall
```

If one opaque model call silently performs all of those jobs, the implementation may still work, but it is difficult to audit, test, constrain, or recover.

## Minimal component responsibilities

| Component | Responsibility |
|---|---|
| Identity | Stable object and reference identity |
| Evidence/provenance | Source, derivation, time, witnesses |
| Lifecycle | Explicit state and legal transitions |
| Estimators | Relevance, trust, contradiction, sensitivity, utility, risk, etc. |
| PAMA/governance | Authority envelope and permitted consequences |
| Commit layer | Explicit mutation + receipt |
| Storage/projections | Canonical and derived retained state |
| Recall planner | Candidate retrieval + governed admission + composition |
| Observability | Transition and decision evidence |
| Recovery | Replay, rollback, compensation |

## Canonical versus derived state

A production implementation should declare which artifacts are authoritative and which are projections.

Possible projections include:

- vector indexes
- graph projections
- summaries
- caches
- compiled knowledge
- search indexes
- model-side derived state

Derived artifacts need dependency metadata if correction, deletion, or replay is expected to propagate reliably.

## Required version bindings

Runtime evidence should bind decisions to the versions that produced them:

```text
memory/state version
schema version
policy version
estimator/model version
calibration context
authority/delegation state
fixture/test version when evaluating conformance
```

Without those bindings, later replay can reproduce syntax while missing the actual decision context.

## Governed recall

Recall is not just nearest-neighbor retrieval.

A robust path is:

```text
candidate retrieval
  → identity/scope checks
  → sensitivity/privacy checks
  → freshness/conflict evaluation
  → policy admission
  → ranking among admitted candidates
  → context composition
```

Stochastic ranking can be perfectly acceptable **after** prohibited candidates are removed from the reachable set.

## Decision receipts

A consequential memory mutation should be reconstructable. Useful receipt fields include:

- request
- state snapshot
- estimator versions/calibration
- uncertainty summary
- policy version
- authority references
- permitted/prohibited actions
- selected action
- selection mode/seed where relevant
- before/after state
- supporting evidence
- receipt hash or integrity reference
- recovery reference

## Start small

A minimal reference adapter should prove the boundaries before becoming a feature-rich memory product.

Recommended first milestone:

1. one canonical memory store
2. one probabilistic estimator
3. one explicit PAMA policy layer
4. one governed recall path
5. decision receipts
6. a handful of adversarial fixtures
7. repeated runs for stochastic behavior

Then add richer graphs, consolidation, portability, and multi-agent features.

## Implementation evidence

When mapping a real system, pin the exact release or commit and document both positive and negative paths. Use the repository's **Implementation or conformance evidence** issue form.

## Canonical sources

- Component architecture: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/11-component-architecture.md
- Composition boundaries: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/13-system-composition-boundaries.md
- Recall planner: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/26-governed-recall-planner.md
- Schema registry: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/27-schema-registry-and-type-evolution.md
- Observability: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/30-memory-observability-and-audit-events.md
- Recovery/replay: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/31-recovery-rollback-and-replay.md

## Next

- **[Conformance and Evidence](Conformance-and-Evidence)** for proving behavior
- **[Security and Privacy](Security-and-Privacy)** for negative paths
