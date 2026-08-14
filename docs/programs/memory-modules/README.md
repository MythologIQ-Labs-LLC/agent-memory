# Memory Component Capability Program

This program turns Agent Memory's representation-neutral doctrine into configurable component/capability contracts, research comparisons, and executable evidence.

## Core model

```text
component identity != capability identity

one component -> many capabilities
one capability -> many candidate implementations
```

Capability roles such as graph, vector, GraphRAG, lifecycle, procedural memory, structural reasoning, storage, exact retrieval, multimodal memory, or learned representation are not mutually exclusive product classes.

## Current research artifacts

- [`first-party-capability-inventory.md`](first-party-capability-inventory.md) — evidence-bounded EvolveAI and CodeGenome capability/maturity map.
- [`capability-vocabulary.md`](capability-vocabulary.md) — representation-neutral vocabulary spanning retained-content, graph/vector/temporal retrieval, procedural/metamemory, lifecycle, latent, multimodal, sharing, and operational capabilities.
- [`external-capability-frontier.md`](external-capability-frontier.md) — external-system mapping and gap classification across the same capability families.
- [`implementation-lane-selection.md`](implementation-lane-selection.md) — selected next vertical slice: governed procedural/skill memory.

## Current doctrine decisions

- ADR-033: capability identity/maturity is independent from component identity and overlapping implementations are composed or selected deterministically.
- ADR-034 (Proposed): procedural/skill memory is governed retained state, not standing execution authority; metamemory is a stricter configuration/policy-change surface.

## Work tracking

- #274 — capability-oriented memory component program
- #275 — adversarial first-party/external capability comparison; remains executable/runtime work
- #280 — component/capability registry and routing fabric
- #284 — first-party capability inventory and subsystem-gap analysis
- #286 — external capability coverage mapping
- #287 — machine-readable capability maturity declarations
- #289 — first-party subsystem-boundary decision
- #290 — capability-based routing and overlap resolution
- #291 — capability vocabulary
- #292 — EvolveAI capability qualification
- #293 — CodeGenome capability qualification

## Current research conclusion

No new proprietary memory subsystem is justified by the current gap analysis.

The strongest genuinely distinct missing generic capability is **procedural/skill memory**, but current external evidence demonstrates that this can be proven with simple human-readable/declarative artifacts rather than a new database or repository.

The first implementation lane therefore is:

```text
#287 capability declarations
  -> #290 deterministic capability resolution
  -> governed procedural/skill memory vertical slice
  -> ADR-034 acceptance evidence
```

EvolveAI and CodeGenome remain broad multi-capability first-party subsystem candidates. Their overlapping graph/vector capabilities should be qualified and composed by capability, not split merely to remove code-level duplication.

## Safeguards

```text
component != authority
capability != authority
declared capability != runtime capability
retrieval score != recall permission
graph reachability != permission
first-party ownership != conformance
procedural memory != execution permission
metamemory proposal != configuration authority
```

New proprietary subsystems should be created only after capability inventory and external comparison establish a real gap that cannot be cleanly satisfied by extending EvolveAI or CodeGenome, composing existing components, implementing generic semantics in Agent Memory core, or adopting/wrapping an external implementation.