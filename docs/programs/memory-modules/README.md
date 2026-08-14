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
- [`implementation-lane-selection.md`](implementation-lane-selection.md) — why governed procedural/skill memory was selected as the first product-shaped fabric proof.
- [`../runtime-evidence/procedural-memory.md`](../runtime-evidence/procedural-memory.md) — executable #295 evidence for capability routing, governed skill lifecycle, action-authority separation, and metamemory refusal.

## Current doctrine decisions

- **ADR-033 Accepted:** capability identity/maturity is independent from component identity and overlapping implementations are composed or selected deterministically.
- **ADR-034 Accepted:** procedural/skill memory is governed retained state, not standing execution authority; exact approval binds the exact procedure/state, and metamemory is a stricter configuration/policy-change surface.

## Executable capability fabric

The first reference slice implements the minimum reusable #287/#290 surfaces required by #295:

```text
machine-readable component capability declaration
        |
        v
minimum maturity + posture requirement
        |
        v
deterministic provider resolution
        |
        +-- no eligible provider -> explicit failure
        +-- ambiguous providers -> explicit failure
        +-- configured eligible preference -> deterministic selection
        |
        v
selected implementation
        |
        v
normal Agent Memory PAMA / recall authority remains controlling
```

The capability registry never turns provider selection into memory mutation or recall permission. Fallback cannot silently lower minimum maturity or required scope posture.

The checked-in EvolveAI and CodeGenome declarations are evidence-bounded examples. They preserve known limitations and do not promote either subsystem to `reference_qualified` merely because MythologIQ owns them.

## Governed procedural-memory reference slice

The first concrete workload is:

```text
procedure proposal
  -> PAMA-governed promotion
  -> durable scoped/versioned skill
  -> later-session retrieval candidate
  -> governed admission/activation
  -> plan influence
  -> separate runtime action proposal
  -> separate action governance
  -> separate execution evidence
```

The slice also proves correction/supersession, exact-content approval binding, stale replay refusal, cross-project admission refusal, revocation/residue honesty, and metamemory self-authorization refusal.

It deliberately uses a simple inspectable reference artifact and the existing `GovernedMemoryAdapter`. A new proprietary skill database/repository was not required to prove the semantics.

## Work tracking

- #274 — capability-oriented memory component program
- #275 — adversarial first-party/external capability comparison; remains executable/runtime comparator work
- #280 — broader component/capability registry and routing fabric program
- #284 — first-party capability inventory and subsystem-gap analysis, completed
- #286 — external capability coverage mapping, completed
- #287 — machine-readable capability maturity declarations, implemented by the #295 reference slice
- #289 — first-party subsystem-boundary decision, completed
- #290 — capability-based routing and overlap resolution, implemented by the #295 reference slice
- #291 — capability vocabulary, completed
- #292 — EvolveAI capability qualification, remains open
- #293 — CodeGenome capability qualification, remains open
- #295 — governed procedural/skill memory reference vertical slice

## Current portfolio conclusion

No new proprietary memory subsystem is justified by the current gap analysis.

EvolveAI and CodeGenome remain broad multi-capability first-party subsystem candidates. Their overlapping graph/vector capabilities should be qualified and composed by capability, not split merely to remove implementation overlap.

Procedural/skill memory was a genuinely distinct generic gap, but the reference implementation demonstrates that its stable value is semantic and governance-oriented rather than tied to a new storage product.

## Safeguards

```text
component != authority
capability != authority
declared capability != runtime capability
retrieval score != recall permission
graph reachability != permission
first-party ownership != conformance
procedural memory != execution permission
approval for X != approval for modified Y
metamemory proposal != configuration authority
```

New proprietary subsystems should be created only after capability inventory and external comparison establish a real gap that cannot be cleanly satisfied by extending EvolveAI or CodeGenome, composing existing components, implementing generic semantics in Agent Memory core, or adopting/wrapping an external implementation.
