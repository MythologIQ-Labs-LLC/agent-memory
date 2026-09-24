# Implementation Ownership Map

## Purpose

[`05-repo-implementation-map.md`](05-repo-implementation-map.md) records how related systems contribute implementation ancestry, domain evidence, optional interoperability, verification, or downstream consumption.

This document answers the ownership question directly:

> **Who owns the generic memory capability after useful prior work is harvested?**

The answer is Agent Memory.

```text
implementation ancestry
    !=
permanent runtime ownership

proven mechanism in another first-party repo
    -> inspect / validate / harvest
    -> native Agent Memory implementation
```

This corrects an older transition-state map that treated EvolveAI, CodeGenome, and COREFORGE Vault/Neurospace as candidate end-state implementation owners.

## Ownership vocabulary

```text
native-owned
    Agent Memory owns the generic contract and implementation surface.

ancestry
    same-owner prior work contains useful implementation mechanisms or evidence.

specialized-domain-source
    a system may continue producing domain-specific observations/projections.

optional-peer
    a system may provide identity, verification, evidence, or enforcement without owning memory semantics.

downstream-consumer
    a product consumes Agent Memory while retaining product-specific concerns.

implemented
    native executable Agent Memory implementation exists.

partial
    part of the native capability exists; additional planned capability remains.

declared
    contract/role is defined but the native implementation is not yet complete.
```

Maturity and ownership are separate. Declaring Agent Memory the owner does not promote an incomplete capability.

## Canonical ownership map

| Component | Canonical owner | Implementation ancestry / peers | Continuing specialized consumers or sources | Current posture |
|---|---|---|---|---|
| Identity contract | **Agent Memory** | UOR intellectual lineage; CodeGenome code identity patterns | any runtime or domain module | native-owned; optional exact-identity mechanisms |
| Evidence and provenance | **Agent Memory** | CodeGenome provenance; COREFORGE lineage; FailSafe/Arbiter receipt patterns | all memory types and downstream products | native-owned / implemented across current contracts |
| Semantic / exact / relational retrieval | **Agent Memory** | EvolveAI exact/vector patterns; CodeGenome retrieval patterns | downstream products | native-owned; exact/lexical/relational implemented |
| Semantic/vector retrieval | **Agent Memory** | EvolveAI vector retrieval; CodeGenome embeddings/cosine/kNN | domain sources may supply derived observations | native-owned; active implementation #456 |
| Temporal / graph retrieval | **Agent Memory** | EvolveAI temporal graph; CodeGenome traversal/overlays; Graphiti as external comparator/adapter | CodeGenome may supply code-domain graph observations | native-owned; partial, further native depth planned |
| Reality Graph framework | **Agent Memory** | CodeGenome implementation ancestry | CodeGenome as code-domain observation source | native-owned; CRG package exists, generic expansion ongoing |
| Lifecycle / Cognitive Metabolism | **Agent Memory** | EvolveAI decay, tiering, REM, consolidation, pruning, crystallization; COREFORGE lifecycle mechanics | downstream products consume native lifecycle | native-owned; partial native lifecycle, further absorption planned |
| Saturation / decay / reinforcement | **Agent Memory** | EvolveAI CMHL-style mechanisms and experiments | memory modules | native-owned doctrine; implementation depth varies |
| **PAMA** | **Agent Memory** | FailSafe/Arbiter enforcement lessons may inform adapters | every mutating component | **native-owned and implemented** |
| Certification / review evidence | **Agent Memory contract** | FailSafe/Arbiter/approval systems may act as evidence or enforcement peers | governance consumers | native-owned contract; peer implementations bounded |
| Runtime memory space | **Agent Memory** | COREFORGE Vault/Neurospace product ancestry | COREFORGE, Cortera, TARA, agents | native-owned; canonical runtimes/substrates now exist |
| Context assembly semantics | **Agent Memory** | COREFORGE broker/packet ancestry | downstream product-specific presentation/orchestration | native-owned; retrieval composition implemented, product facade still evolving |
| Correction / dispute / supersession | **Agent Memory** | prior product workflows as ancestry | all consumers | native-owned / implemented in current governed runtime |
| Durable decision memory | **Agent Memory** | product implementations may consume profile | decision-oriented products/agents | native-owned profile |
| Negative / failure memory | **Agent Memory** | Shadow Genome concepts from EvolveAI ancestry | downstream risk/planning consumers | native-owned / implemented through #471 / PR #473; generic standalone owner remains process-local, bounded checkpoint/recovery composition proven |
| Continuous memory evaluation | **Agent Memory** | CodeGenome experiment-loop ancestry | CI/release/benchmark consumers | native-owned; initial retrieval benchmarks exist, broader loop planned |
| Conformance | **Agent Memory** | optional verification peers such as PrismPM may strengthen evidence | every implementation | native-owned / implemented |

## PAMA ownership

PAMA's canonical semantics and runtime implementation are Agent Memory responsibilities.

Canonical sources include:

- [`pama/README.md`](pama/README.md)
- [`04-governance-and-pama.md`](04-governance-and-pama.md)
- [`33-pama-decision-table.md`](33-pama-decision-table.md)
- [`ADR-004`](adr/ADR-004-pama-controls-mutation-authority.md)

A downstream product or enforcement peer may host additional controls, but no external product becomes PAMA's semantic owner.

A PAMA boundary must preserve at least:

```text
M0-M5 target class
lifecycle strength
requested operation
A0-A5 downstream authority
actor and charter
scope and reversibility
evidence and uncertainty
policy version
permitted / prohibited outcomes
selected action
committed consequence receipt
```

PAMA must remain distinguishable from relevance, similarity, confidence, saturation, storage success, or implementation convenience.

## First-party absorption rule

ADR-036 classifies same-owner components as first-party module candidates rather than attributed providers.

The runtime consequence is now explicit:

```text
same-owner component has useful mechanism
    -> Agent Memory may adopt it directly
    -> native Agent Memory module owns the resulting generic capability
    -> originating repo need not remain installed or invoked at runtime
```

Lineage remains valuable. Cross-repository runtime dependency is not the destination by default.

## EvolveAI disposition

EvolveAI remains implementation ancestry and a behavioral/test oracle for capabilities including:

- vector representation and retrieval;
- temporal graph behavior;
- tier routing;
- decay/weakening and reinforcement;
- lifecycle orchestration;
- consolidation and REM-style synthesis;
- pruning pressure;
- crystallization proposals;
- exact recall;
- negative/failure memory concepts;
- restart behavior.

The end-state owner of those generic capabilities is Agent Memory.

Negative/failure memory is now a concrete example of that ownership rule. #471 / PR #473 harvested stable failure identity, typed revision/history, recurrence evidence, currentness, typed recall isolation, and bounded checkpoint/recovery behavior into native Agent Memory code while explicitly rejecting Shadow Genome's direct similarity-to-block authority shape.

An EvolveAI estimator may still be useful in experiments or optional specialized deployments. Its score or proposal cannot become memory authority merely because the mechanism originated in first-party code.

## CodeGenome disposition

CodeGenome has two distinct relationships that must not be collapsed.

### 1. Implementation ancestry

Agent Memory may harvest generic mechanisms such as:

- embedding persistence;
- vector similarity / kNN;
- graph traversal patterns;
- semantic/multi-overlay relationships;
- impact propagation;
- provenance/evidence fusion;
- experiment and performance evaluation loops.

After absorption, those generic mechanisms are Agent Memory implementation.

### 2. Specialized domain evidence source

CodeGenome may continue to produce code-domain observations, structural relationships, impact evidence, or code-specific projections.

```text
CodeGenome observes code reality
    -> Agent Memory ingests/evaluates domain evidence
```

This does not mean Agent Memory must call CodeGenome for generic graph memory, vector retrieval, causal traversal, or evaluation.

## COREFORGE Vault / Neurospace disposition

COREFORGE contains valuable product-level memory ancestry, including historical code for:

- lifecycle storage;
- memory domains;
- source/reference objects;
- context brokers and context packets;
- graph recall;
- RAG/context assembly;
- mutation gating;
- lineage;
- provider composition.

The older map interpreted that code as a candidate owner for Runtime Memory Space and Context Assembly. That was useful during transition, but it is not the desired final dependency direction.

```text
historical:
COREFORGE contains/emulates generic memory machinery

end state:
Agent Memory owns generic memory machinery
COREFORGE consumes Agent Memory
```

COREFORGE may continue to own product-specific concerns such as UI, inference adapters, local application orchestration, encrypted product packaging, or caches. Those concerns do not transfer generic memory ownership back out of Agent Memory.

## UOR disposition

UOR is optional exact-identity/interoperability lineage.

Agent Memory owns the identity boundary and may use UOR-derived or UOR-compatible mechanisms where useful.

```text
UOR/exact reference
    !=
memory lifecycle
    !=
retrieval authority
    !=
PAMA
```

See [`ADR-001`](adr/ADR-001-uor-is-identity-not-memory.md).

## PrismPM disposition

PrismPM is a candidate verification/conformance peer where exact canonical models, replay, state-transition verification, or atomic promotion evidence add value.

Potential uses include:

- canonical memory-state verification;
- replay/conformance checks;
- checkpoint or transition evidence;
- release/conformance integrity.

It is not ordinary recall machinery and does not become a memory semantic owner merely because its verification model is useful.

## Consolidation calls

### Consolidate into Agent Memory

Generic capabilities should converge into native Agent Memory implementations rather than remain fragmented by repository history:

- semantic/vector retrieval;
- temporal/graph traversal;
- lifecycle/metabolism;
- context assembly semantics;
- provenance/currentness/correction/deletion mechanics;
- negative/failure memory;
- continuous memory evaluation.

### Keep specialized boundaries

Some boundaries should remain segmented:

- CodeGenome remains free to specialize in code intelligence and provide code-domain evidence.
- COREFORGE remains free to specialize in product UX, local orchestration, inference adapters, and application packaging.
- Certification/review independence should not collapse into the estimator proposing a mutation.
- UOR remains an optional identity mechanism rather than a memory owner.
- verification peers remain evidence/conformance helpers rather than recall authorities.

## Historical inspection record

**2026-08-11.** EvolveAI, CodeGenome, GG-CORE, and COREFORGE were inspected at pinned revisions. That inspection established real implementation ancestry:

- COREFORGE Vault/Neurospace existed as code with lifecycle storage, mutation gates, context assembly, graph/RAG behavior, references, lineage, and provider seams.
- EvolveAI and CodeGenome were consumed inside COREFORGE through memory-provider interfaces.
- GG-CORE was a compute dependency rather than a memory successor.

Those findings remain valid evidence about the historical implementation state.

They no longer establish end-state ownership.

```text
historical provider seam exists
    !=
Agent Memory should preserve that provider seam forever
```

The inspection now serves as a harvest inventory and migration reference.

## Native implementation evidence rule

Once a mechanism is absorbed, maturity is earned as ordinary Agent Memory implementation evidence rather than same-owner provider qualification.

A native capability should be able to show, as applicable:

1. the Agent Memory contract it implements;
2. source ancestry when materially useful for reconstruction;
3. focused positive and adversarial tests;
4. currentness and correction behavior;
5. deletion/residue behavior;
6. scope/isolation behavior;
7. restart/rebuild behavior;
8. estimator/version bindings where probabilistic representation is involved;
9. authority effect;
10. benchmark/regression evidence appropriate to the capability.

Ownership is not maturity. A native module can still be experimental, partial, or wrong.

## Current execution direction

Issue #470 now owns the exhaustive ancestry/peer harvest closeout. The planned native sequence through semantic/vector retrieval, typed temporal/relational graph retrieval, metabolism, and continuous evaluation has landed, and #471 / PR #473 closed the negative/failure-memory implementation gap exposed by the first harvest-closeout wave.

The current direction is therefore:

```text
completed native slices
  -> evidence-bound harvest matrix
  -> classify remaining ancestry/peer mechanisms
  -> implement only material generic gaps
  -> preserve specialized/interoperability boundaries where appropriate
  -> downstream products delegate generic memory to Agent Memory
```

Remaining #470 work includes the bounded CodeGenome impact/evidence-fusion disposition, COREFORGE Vault/Neurospace and context-packaging inventory, source-rights/NOTICE reconciliation, and other peer reviews already recorded in the harvest matrix. Those audits must not be converted into implementation merely because a source contains a feature.

## Doctrine

Ownership is a governance and architecture fact, not merely a deployment fact.

Agent Memory defines and increasingly implements its generic memory capabilities. A related repository can contribute excellent prior art, specialized observations, or optional peer functionality without remaining the canonical runtime owner.

Code that proves a useful mechanism is valuable ancestry. The destination is a coherent Agent Memory system, not a permanent museum of internal service boundaries.
