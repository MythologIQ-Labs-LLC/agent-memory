# Memory Component Capability Program

This program turns Agent Memory's representation-neutral doctrine into configurable component/capability contracts and evidence.

## Core model

```text
component identity != capability identity

one component -> many capabilities
one capability -> many candidate implementations
```

Capability roles such as graph, vector, GraphRAG, lifecycle, structural reasoning, storage, exact retrieval, or learned representation are not mutually exclusive product classes.

## Current first-party inventory

- [`first-party-capability-inventory.md`](first-party-capability-inventory.md) — evidence-bounded EvolveAI and CodeGenome capability/maturity map.

## Work tracking

- #274 — capability-oriented memory component program
- #275 — adversarial first-party/external capability comparison
- #280 — component/capability registry and routing fabric
- #284 — first-party capability inventory and subsystem-gap analysis
- #285 — capability-oriented taxonomy correction
- #286 — external capability coverage mapping
- #287 — machine-readable capability maturity declarations
- #289 — first-party subsystem-boundary decision
- #290 — capability-based routing and overlap resolution
- #291 — graph/vector/GraphRAG/hybrid vocabulary
- #292 — EvolveAI capability qualification
- #293 — CodeGenome capability qualification

## Safeguards

```text
component != authority
capability != authority
declared capability != runtime capability
retrieval score != recall permission
graph reachability != permission
first-party ownership != conformance
```

New proprietary subsystems should be created only after capability inventory and external comparison establish a real gap that cannot be cleanly satisfied by extending EvolveAI or CodeGenome, composing existing components, implementing generic semantics in Agent Memory core, or adopting/wrapping an external implementation.
