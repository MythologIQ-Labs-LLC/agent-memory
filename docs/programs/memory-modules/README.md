# Memory Component Capability Program

This program turns Agent Memory's representation-neutral doctrine into configurable component/capability contracts, research comparisons, executable adapters, and version-bound qualification evidence.

## Core model

```text
component identity != capability identity

one component -> many capabilities
one capability -> many candidate implementations

configured capability != qualified capability
qualified old version != qualified new version
```

Capability roles such as graph, vector, GraphRAG, lifecycle, procedural memory, structural reasoning, storage, exact retrieval, multimodal memory, or learned representation are not mutually exclusive product classes.

## Current research artifacts

- [`first-party-capability-inventory.md`](first-party-capability-inventory.md) — evidence-bounded EvolveAI and CodeGenome capability/maturity map.
- [`capability-vocabulary.md`](capability-vocabulary.md) — representation-neutral vocabulary spanning retained-content, graph/vector/temporal retrieval, procedural/metamemory, lifecycle, latent, multimodal, sharing, and operational capabilities.
- [`external-capability-frontier.md`](external-capability-frontier.md) — historical external-system mapping and gap classification.
- [`external-capability-frontier-refresh-2026-08-14.md`](external-capability-frontier-refresh-2026-08-14.md) — fast-moving current release/license/capability refresh for the next qualification wave.
- [`implementation-lane-selection.md`](implementation-lane-selection.md) — why governed procedural/skill memory was selected as the first product-shaped fabric proof.
- [`component-adapter-qualification-contract.md`](component-adapter-qualification-contract.md) — #298 research conclusion defining install/declaration vs adapter invocation vs earned qualification evidence.
- [`../runtime-evidence/procedural-memory.md`](../runtime-evidence/procedural-memory.md) — executable #295 evidence for capability routing, governed skill lifecycle, action-authority separation, and metamemory refusal.

## Current doctrine decisions

- **ADR-033 Accepted:** capability identity/maturity is independent from component identity and overlapping implementations are composed or selected deterministically.
- **ADR-034 Accepted:** procedural/skill memory is governed retained state, not standing execution authority; exact approval binds the exact procedure/state, and metamemory is a stricter configuration/policy-change surface.
- **No new ADR currently required for #298:** version-bound adapter/qualification evidence is an implementation/conformance specialization of existing doctrine unless executable adapters expose a genuine doctrine-level contradiction.

## Executable capability fabric already earned

PR #297 implemented the reusable #287/#290 surfaces required by #295:

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
```

The capability registry never turns provider selection into memory mutation or recall permission. Fallback cannot silently lower minimum maturity or required scope posture.

The checked-in EvolveAI and CodeGenome declarations are evidence-bounded examples. They preserve known limitations and do not promote either subsystem to `reference_qualified` merely because MythologIQ owns them.

## Missing executable layer

Selection is not yet the complete #280 component contract.

The next layer is:

```text
capability requirement
  -> deterministic provider resolution
  -> versioned adapter invocation
  -> raw provider result + evidence
  -> provider-neutral normalization
  -> Agent Memory currentness/scope/lifecycle evaluation
  -> PAMA or governed recall admission
  -> commit/admit/refuse
  -> version-bound qualification evidence
```

#298 defines the common adapter and qualification record before #292/#293 are allowed to become provider-specific certification exercises.

The key separations are:

```text
selected component != authorized consequence
component result != canonical Agent Memory state
component success != capability conformance
maturity claim != executable proof
adapter normalization != evidence laundering
```

## Governed procedural-memory reference slice

The first concrete workload is already merged:

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

## Next deterministic portability proof

The first common adapter/qualification harness should use two real local code-graph providers:

```text
CodeGenome
Graphify
```

Reasons:

- deterministic local execution;
- no model/API variability required for the matched facts;
- materially different implementations;
- useful stale/currentness/update pressure;
- Graphify's active project line is now Apache-2.0;
- draft PR #278 already contains a small adversarial fixture and raw-output-preserving comparator design that can be harvested against current `main`.

The result must remain a factual capability qualification, not a scalar product ranking.

## Work tracking

- #274 — capability-oriented memory component program
- #275 — initial adversarial first-party/external capability comparison, completed
- #280 — broader component/capability runtime contract and routing fabric, open
- #287 — machine-readable capability maturity declarations, completed by PR #297
- #290 — capability-based routing and overlap resolution, completed by PR #297
- #292 — EvolveAI capability qualification, open and gated by #298
- #293 — CodeGenome capability qualification, open and gated by #298
- #295 — governed procedural/skill memory reference vertical slice, completed by PR #297
- #298 — executable component adapter and version-bound capability qualification contract, active research/next implementation gate
- #282 — restart-safe runtime and end-to-end acceptance harness

## Current first-party pressure

### EvolveAI

Current planning pin:

`7cd42412ceed2ab638249a1517b2a6dac46f1312`

Open EvolveAI #19 means L3 live removal currently lacks an explicit delete/tombstone operation in the hash-chain ledger. Until repaired and re-qualified:

```text
live L3 removal
!= reconstructable audited delete
!= complete Agent Memory forgetting
```

This caps strong deletion/audit/persistence qualification claims.

### CodeGenome

Current planning pin:

`d2578729a46d495369bd7613845002d50cf20f4c`

The #275 file-identity and traversal-direction defects were repaired before this pin. Those fixes become permanent regression requirements for #293 rather than being forgotten after the bug tracker turns green.

## Current portfolio conclusion

No new proprietary memory subsystem is justified by the current gap analysis.

EvolveAI and CodeGenome remain broad multi-capability first-party subsystem candidates. Their overlapping graph/vector capabilities should be qualified and composed by capability, not split merely to remove implementation overlap.

The external frontier is increasingly diverse: deterministic graphs, hybrid complete memory systems, file/skill memory, self-evolving skills, and hypergraph systems. That diversity strengthens the need for a shared adapter/qualification boundary rather than one shared storage ontology.

## Safeguards

```text
component != authority
capability != authority
declared capability != runtime capability
configured capability != qualified capability
provider success != Agent Memory conformance
retrieval score != recall permission
graph reachability != permission
first-party ownership != conformance
procedural memory != execution permission
approval for X != approval for modified Y
metamemory proposal != configuration authority
old qualification != new-version qualification
```

New proprietary subsystems should be created only after capability inventory and executable external comparison establish a real gap that cannot be cleanly satisfied by extending EvolveAI or CodeGenome, composing existing components, implementing generic semantics in Agent Memory core, or adopting/wrapping an external implementation.