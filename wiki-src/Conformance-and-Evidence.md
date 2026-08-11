# Conformance and Evidence

Agent Memory deliberately separates **what the architecture says**, **what repository artifacts validate**, and **what a real runtime has actually demonstrated**.

That distinction matters because a perfectly valid JSON fixture can still describe behavior no production system has ever executed.

## Evidence ladder

| Level of evidence | What it establishes |
|---|---|
| **Doctrine** | The architecture states a rule or boundary. |
| **Schema** | A machine-readable contract defines required structure and semantics. |
| **Fixture** | A scenario expresses expected behavior and invariants. |
| **Repository validation** | The declared schemas, fixtures, links, and validators are internally coherent. |
| **Implementation mapping** | A real system exposes surfaces that correspond to the doctrine. |
| **Observed runtime behavior** | A pinned implementation produced a reproducible result. |
| **Conformance evidence** | Repeated positive and negative-path results satisfy a defined evidence bar. |

## Current conformance levels

| Level | Evidence target |
|---|---|
| **0** | Documentation alignment |
| **1** | Identity and provenance |
| **2** | Lifecycle and decay |
| **3** | Calibrated saturation and trap resistance |
| **4** | PAMA or equivalent mutation authority |
| **5** | Certification and audited crystallization |
| **6** | Governed uncertainty across estimator, policy, action-set, and committed-consequence boundaries |

Level 6 does not mean “make the model deterministic.” It means uncertainty can remain adaptive while prohibited consequences stay unreachable.

## What the repository already validates

Agent Memory currently includes:

- 7 JSON Schemas
- 24 conformance fixture definitions
- fixture invariant validation
- schema validation
- source-rights validation
- doctrine-boundary validation
- calibration report consistency checks
- documentation-link validation

## What that does not prove

Repository validation does not by itself prove that a runtime:

- detects poisoning
- blocks cross-tenant recall
- contains a stochastic selector inside a permitted action set
- resolves concurrent mutation correctly
- rejects stale or expired authority
- propagates deletion into derived state
- reconstructs a committed decision from receipts

Those claims require runtime evidence.

## High-value negative paths

A useful implementation should exercise at least:

- high-confidence false promotion
- threshold jitter
- estimator disagreement
- cross-tenant relevance traps
- stochastic retrieval under policy
- unsafe multi-memory composition
- uncertain sensitivity before export
- irreversible deletion under uncertain utility
- policy/estimator version drift
- concurrent mutation
- sleeper poisoning
- authority laundering
- deletion residue
- out-of-calibration-scope scoring
- expired delegation
- stochastic replay reconstruction

## Evidence quality rule

For any consequential claim, preserve:

```text
implementation version
policy version
estimator version
fixture/version
input state
authority context
permitted action set
selected action
before/after state
runtime evidence
known limitations
```

## ADR-020 proof bar

ADR-020 should remain Proposed until at least one real implementation demonstrates the complete chain:

```text
estimate / proposal
  → governance envelope
  → permitted action set
  → selected action
  → committed consequence
```

with repeated stochastic trials, cross-scope admission tests, real concurrency behavior, deletion propagation, and reconstructable decision receipts.

## Canonical sources

- Conformance test plan: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/06-conformance-test-plan.md
- Calibration protocol: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/09-calibration-protocol.md
- Documentation conformance audit: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/25-governed-uncertainty-documentation-conformance-audit.md
- Quality metrics: https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/32-memory-quality-metrics.md
- Schemas: https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/main/schemas
- Fixtures: https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/main/fixtures

## Next

- **[Implementation Guide](Implementation-Guide)** to map a real runtime
- **[Architecture Decisions](Architecture-Decisions)** to understand the accepted/proposed doctrine boundary
