# Architecture Decision Records

This directory records architectural decisions for the Agent Memory doctrine.

## Status semantics

ADR status describes **doctrine maturity**, not implementation maturity.

| Status | Meaning |
|---|---|
| Proposed | A decision candidate under active evaluation. Required evidence, follow-up, or doctrine integration is incomplete. |
| Accepted | The decision is canonical Agent Memory doctrine. Implementations may still be conceptual, partial, experimental, or absent. |
| Superseded | A later ADR replaces this decision. Historical rationale remains useful. |
| Rejected | The proposal was evaluated and intentionally not adopted. |

An `Accepted` ADR does **not** claim:

- every related repository implements it
- executable conformance exists
- runtime enforcement is complete
- the decision can never be revised

Implementation maturity is tracked separately through documentation, fixtures, conformance evidence, implementation maps, and runtime evidence.

## Current status policy

A decision may move from Proposed to Accepted when:

1. its architectural boundary is sufficiently defined
2. it is integrated consistently into canonical doctrine
3. known material contradictions have been resolved or documented
4. required foundational documentation exists
5. acceptance does not depend on implementation evidence the ADR itself explicitly requires

If an ADR explicitly requires executable evidence before acceptance, that requirement controls.

## Governed uncertainty

`ADR-020` is intentionally different from many earlier ADRs. It explicitly requires conformance and implementation evidence before acceptance. It remains **Proposed** until those conditions are met.

## Canonical references

- [`../01-layer-model.md`](../01-layer-model.md)
- [`../04-governance-and-pama.md`](../04-governance-and-pama.md)
- [`../06-conformance-test-plan.md`](../06-conformance-test-plan.md)
- [`../11-component-architecture.md`](../11-component-architecture.md)
- [`../24-determinism-probability-and-governed-uncertainty.md`](../24-determinism-probability-and-governed-uncertainty.md)
- [`../25-governed-uncertainty-documentation-conformance-audit.md`](../25-governed-uncertainty-documentation-conformance-audit.md)
