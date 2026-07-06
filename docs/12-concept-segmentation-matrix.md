# Concept Segmentation Matrix

## Purpose

This matrix decides whether a concept belongs as:

1. a canonical doctrine concept
2. a component inside the larger architecture
3. an implementation detail inside a specific repo
4. a product or UX surface
5. a conformance concern

This prevents concept drift by forcing every idea to answer where it belongs before it becomes another half-remembered architecture ghost.

## Placement rules

| Placement | Use when | Example |
|---|---|---|
| Doctrine concept | The idea affects all implementations | saturation is not truth |
| Component | The idea has distinct interfaces and failure modes | PAMA, lifecycle engine, certification gate |
| Implementation detail | The idea is repo-specific | EvolveAI REM synthesis implementation |
| Product surface | The idea affects user interaction | COREFORGE memory correction UI |
| Conformance concern | The idea must be tested across systems | access-spam trap class |

## Segmentation matrix

| Concept | Placement | Component | Canonical owner | Notes |
|---|---|---|---|---|
| UOR address | Component | Identity Substrate | UOR Framework | Stable identity, not memory policy |
| BLAKE3 content identity | Implementation plus component | Identity Substrate | UOR / CodeGenome | Used by multiple systems for deterministic identity |
| Memory unit | Doctrine concept | Lifecycle Engine | agent-memory doctrine | Shared object abstraction |
| Artifact | Doctrine concept | Identity and Evidence | agent-memory doctrine | Raw thing entering memory |
| Observation | Doctrine concept | Evidence and Provenance | agent-memory doctrine | Witnessed artifact or relation |
| Evidence bundle | Component | Evidence and Provenance | FailSafe, CodeGenome, runtime ledgers | Must survive summarization |
| Provenance | Doctrine concept | Evidence and Provenance | agent-memory doctrine | Required for durable transitions |
| Fiber | Doctrine concept | Saturation and Decay | agent-memory doctrine | Durability or relevance dimension |
| Saturation sigma | Component | Saturation and Decay | PRISM-style lifecycle consumer | Routing signal, not truth |
| Decay | Component | Saturation and Decay | EvolveAI / lifecycle runtime | Reduces operational weight |
| CMHL | Implementation detail | Saturation and Decay | EvolveAI | Specific decay implementation |
| MTS | Implementation detail | Lifecycle routing | EvolveAI | Routing heuristic, not universal doctrine |
| Confidence fusion | Component | Reality Graphs / Evidence | CodeGenome | Evidence support, not permanence |
| Noisy-OR fusion | Implementation detail | Reality Graphs | CodeGenome | Specific confidence fusion method |
| Lifecycle state machine | Component | Lifecycle Engine | agent-memory doctrine | Shared state vocabulary |
| Crystallization | Doctrine concept plus component | Certification and Crystallization Gate | agent-memory doctrine | Governed transition to durable state |
| Certification | Component | Certification and Crystallization Gate | governance layer | Confirmation record for durable transition |
| PAMA | Component | Governance and Mutation Authority | agent-memory doctrine / PAMA implementation | Permission to mutate, promote, prune, or canonize |
| Mutation authority | Doctrine concept | Governance and Mutation Authority | PAMA | Capability is not authority |
| Neurospace | Component | Runtime Memory Space | COREFORGE | Operational agent memory space |
| Vault | Implementation plus component | Runtime Memory Space | COREFORGE | Local encrypted memory container |
| CodeGenome | Component | Reality Graphs | CodeGenome | Code reality graph, not general runtime memory |
| Shadow Genome | Component | Correction, Dispute, and Negative Memory | EvolveAI / FailSafe style systems | Stores failure patterns and negative constraints |
| Bicameral decision continuity | Product plus component | Reality Graphs / Durable Decision Memory | Bicameral | High-risk decision memory and drift detection |
| FailSafe evidence capture | Product plus component | Evidence and Governance | FailSafe | Enforcement and audit surface |
| Arbiter | Product component | Governance and Mutation Authority | COREFORGE | Runtime policy guardian |
| Context window assembly | Product surface | Context Assembly Surface | COREFORGE / agent runtime | Operational use, not canonical truth |
| Correction workflow | Product surface plus component | Correction and Dispute Surface | runtime implementation | Must preserve prior state |
| Calibration protocol | Conformance concern | Conformance and Calibration Harness | agent-memory doctrine | Determines threshold validity |
| Trap classes | Conformance concern | Conformance and Calibration Harness | agent-memory doctrine | Access-spam and confidently-wrong cases |

## Decision tree

Use this decision tree for new concepts.

```text
Does it affect every implementation?
  yes -> doctrine concept
  no -> continue

Does it have its own failure mode and interface?
  yes -> component
  no -> continue

Is it specific to one repo or runtime?
  yes -> implementation detail
  no -> continue

Is it visible to users or agents during operation?
  yes -> product surface
  no -> continue

Is it mainly used to prove behavior?
  yes -> conformance concern
  no -> open a doctrine issue before implementing
```

## Boundary examples

### Saturation

Saturation is a component-level concept because it has its own failure modes:

- access-spam inflation
- false permanence
- overfit durability dimensions
- poor threshold calibration

It is also a doctrine concept because every implementation must understand that saturation is routing, not truth.

### PAMA

PAMA is a component because it owns a bounded decision:

```text
Is this memory transition allowed?
```

It should not be embedded as a small helper inside each memory implementation. That would duplicate authority logic and make policy drift inevitable, because humans apparently enjoy creating three versions of the same mistake.

### CodeGenome

CodeGenome is a component inside the larger system, not the whole memory system.

It provides code reality evidence. Agent Memory decides how that evidence becomes operational memory or durable memory.

### Neurospace

Neurospace is runtime memory space.

It should consume canonical doctrine and enforce runtime boundaries, but it should not redefine identity, certification, or PAMA rules locally.

## Segmentation rule

If a concept controls a transition, it should be a component.

If a concept explains a boundary, it should be doctrine.

If a concept proves behavior, it should be conformance.

If a concept only exists inside one repo, keep it there until it proves it deserves promotion.
