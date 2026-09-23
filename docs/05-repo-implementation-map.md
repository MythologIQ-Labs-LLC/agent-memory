# Repo Implementation Map

## Purpose

This map records how related repositories and systems contribute to Agent Memory without confusing **implementation ancestry**, **domain evidence**, **optional interoperability**, and **canonical runtime ownership**.

The controlling rule is:

> **Agent Memory is the memory system. Related projects may donate proven mechanisms, provide domain observations, supply optional interoperability primitives, or act as evidence/test peers. They do not permanently own Agent Memory's generic memory machinery.**

The intended direction is:

```text
EvolveAI
CodeGenome
COREFORGE Vault / Neurospace
UOR-derived mechanisms
other useful prior work
        |
        v
inspect / validate / harvest proven mechanisms
        |
        v
native Agent Memory implementations
        |
        v
Agent Memory canonical memory subsystem
        |
        +--> COREFORGE
        +--> Cortera
        +--> TARA
        +--> agents
        +--> other products
```

This replaces an older transition-state interpretation in which EvolveAI, CodeGenome, or COREFORGE could be read as permanent runtime owners of Agent Memory capabilities.

**Agent Memory owns the architecture, memory semantics, and generic runtime capability contracts. PAMA is native Agent Memory doctrine and runtime authority machinery.**

See also:

- [`ADR-035`](adr/ADR-035-agent-memory-is-a-governed-cognitive-framework.md)
- [`ADR-036`](adr/ADR-036-same-owner-components-are-first-party-modules.md)
- [`39-implementation-ownership-map.md`](39-implementation-ownership-map.md)
- [`40-aligned-projects-and-intellectual-lineage.md`](40-aligned-projects-and-intellectual-lineage.md)

## Relationship vocabulary

| Relationship | Meaning | Runtime consequence |
|---|---|---|
| **Native Agent Memory capability** | Agent Memory owns the contract and implementation surface | ordinary Agent Memory operation does not require an ancestor repository |
| **First-party implementation ancestry** | same-owner prior work contains useful mechanisms, tests, algorithms, or implementation lessons | inspect, validate, harvest, and absorb useful behavior into native Agent Memory modules |
| **Domain evidence source** | a specialized system produces observations or projections in its own domain | Agent Memory may ingest the observations without outsourcing generic memory machinery |
| **Optional interoperability mechanism** | a separate system supplies a bounded identity, evidence, or exchange primitive | optional profile, never implicit ownership of memory semantics |
| **Verification / conformance peer** | a system can strengthen exact-state, replay, or evidence verification | optional verification path, not ordinary recall or lifecycle ownership |
| **Downstream consumer** | a product or agent uses Agent Memory | product-specific UX/orchestration may remain local while generic memory delegates to Agent Memory |

The categories may overlap. CodeGenome, for example, is both first-party implementation ancestry and a valid code-domain evidence source.

## Canonical native ownership

Agent Memory owns generic memory capabilities including:

- memory identity and reference contracts;
- semantic, lexical, exact, relational, temporal, graph, and vector retrieval machinery;
- memory lifecycle and metabolism machinery;
- decay, reinforcement, consolidation, pruning, and crystallization semantics;
- provenance, currentness, correction, supersession, dispute, and forgetting semantics;
- context assembly semantics;
- memory-type composition;
- PAMA mutation authority and governed recall admission;
- restart/durability contracts;
- continuous memory-quality, regression, and conformance evaluation.

A specialized implementation may be better at one domain or mechanism. That does not transfer canonical ownership of the generic capability.

## Native doctrine component: PAMA

**Proportional Adaptive Mutation Authority (PAMA)** is native Agent Memory governance doctrine authored by Kevin R. Knapp.

Canonical doctrine:

- [`pama/README.md`](pama/README.md)
- [`04-governance-and-pama.md`](04-governance-and-pama.md)
- [`33-pama-decision-table.md`](33-pama-decision-table.md)
- [`ADR-004`](adr/ADR-004-pama-controls-mutation-authority.md)

PAMA owns authority semantics, not a separate external repository role. An implementation must preserve at least:

- M0-M5 mutation target classes;
- lifecycle strength separately from authority;
- A0-A5 downstream authority ceilings;
- explicit operation classification;
- consequence-proportional handling;
- no self-approved privilege expansion;
- evidence and charter binding;
- bounded authority envelopes;
- receipts reconstructing permitted, prohibited, selected, and committed consequences.

Probabilistic estimators may propose consequences. They do not mint authority.

## Aligned foundation: UOR

**Relationship:** intellectual lineage + optional exact-identity/interoperability mechanism.

Work from the [UOR Foundation](https://github.com/UOR-Foundation/UOR-Framework) materially informed Agent Memory's separation between deterministic object identity and memory lifecycle/governance.

Agent Memory adopts the boundary, not a compulsory runtime dependency:

```text
exact identity
    !=
lifecycle state
    !=
relevance
    !=
authority
```

When UOR is used, it may provide deterministic addressability, exact object resolution, and content identity. A conforming Agent Memory implementation may use another exact identity mechanism if it preserves the same boundary.

UOR does not own Agent Memory lifecycle, retrieval, metabolism, governance, persistence, deletion, or certification.

See [`ADR-001`](adr/ADR-001-uor-is-identity-not-memory.md).

## First-party implementation ancestry map

| System | Relationship to Agent Memory | Mechanisms / evidence worth harvesting | End-state boundary |
|---|---|---|---|
| **EvolveAI** | first-party implementation ancestry + behavioral/test oracle | vector representation, vector retrieval, decay-aware scoring, temporal graph behavior, tier routing, CMHL-style decay, REM-style synthesis, consolidation, pruning pressure, crystallization proposals, exact recall, restart behavior, Shadow Genome concepts | useful behavior becomes native Agent Memory retrieval/metabolism/lifecycle; no required EvolveAI runtime client |
| **CodeGenome** | first-party implementation ancestry + code-domain evidence source | embedding persistence, cosine/k-nearest retrieval, semantic/multi-overlay traversal, typed relationships, impact propagation, provenance, experiment/evaluation loops | may continue to provide code observations; generic graph/vector/retrieval/evaluation machinery belongs to Agent Memory |
| **COREFORGE Vault / Neurospace** | first-party product/runtime ancestry + downstream consumer target | memory domains, references, context broker/packets, graph recall, decay-ranked retrieval, mutation boundaries, lineage, local-first product lessons | COREFORGE should consume Agent Memory for generic memory; product-specific UX, encryption, caching, and orchestration may remain local |
| **FailSafe / Arbiter** | first-party governance/evidence ancestry or peer depending on the bounded surface | approval gates, evidence capture, action governance, audit patterns | may constrain or evidence consequences; cannot redefine Agent Memory memory semantics or PAMA authority |
| **GG-CORE** | compute substrate only, not a memory owner | local model execution / inference runtime lessons | may provide compute used by a product; owns no Agent Memory memory capability |

Same-owner adoption is governed by [`ADR-036`](adr/ADR-036-same-owner-components-are-first-party-modules.md). Adoption does not imply that the originating repository remains an installed runtime component.

## EvolveAI ancestry

### Useful mechanisms

EvolveAI contains or has contained useful implementation evidence around:

- vector representations and candidate retrieval;
- exact/content-addressed recall;
- temporal graph behavior;
- multi-tier memory routing;
- decay/weakening and reinforcement;
- lifecycle orchestration;
- consolidation and REM-style synthesis;
- pruning pressure;
- crystallization proposals;
- negative/failure memory through Shadow Genome concepts;
- restart and persistence behavior.

### Agent Memory-owned destination

Those generic mechanisms should be evaluated and, where they survive falsification, implemented natively under Agent Memory contracts.

```text
EvolveAI behavior
  -> test oracle / ancestry
  -> Agent Memory native retrieval + metabolism + lifecycle
```

EvolveAI tier names or internal ontology do not become Agent Memory doctrine merely because useful code originated there.

### Governance boundary

Decay, retention, consolidation, ranking, or promotion signals remain estimators/proposals. They cannot self-authorize canonical, irreversible, scope-widening, or otherwise governed mutation.

## CodeGenome ancestry and domain boundary

### Useful mechanisms

CodeGenome contains or has contained useful implementation evidence around:

- content-addressed code identity;
- graph/overlay construction;
- semantic overlays and multi-overlay traversal;
- embedding persistence;
- cosine and k-nearest retrieval;
- entity relationships;
- impact/blast-radius propagation;
- provenance and evidence fusion;
- continuous experiment and performance measurement.

### Agent Memory-owned destination

Generic graph, vector, relational, causal, provenance, and retrieval machinery should be implemented natively in Agent Memory where the behavior is broadly useful.

### Valid continuing CodeGenome role

CodeGenome may remain an excellent **code-domain observation producer**.

```text
CodeGenome code-domain observations
  -> Agent Memory evidence / reality projection
```

That is different from:

```text
Agent Memory generic graph/vector memory
  -> call CodeGenome to function
```

The first is valid specialization. The second is not the intended end state.

Exact syntax facts may be deterministic while semantic overlays, entity resolution, impact estimates, and inferred relationships remain evidential/probabilistic. Agent Memory preserves that distinction.

## COREFORGE Vault / Neurospace ancestry and reversal

Direct inspection of historical COREFORGE code showed real memory mechanics including a lifecycle store, mutation gate, Neurospace assembler/inspector/mutator, context broker/engine/packet, knowledge graph, UOR-style references, memory domains, lineage, RAG behavior, and provider composition.

That historical evidence remains useful. Its architectural interpretation changes.

### Historical transition state

```text
COREFORGE contains/emulates generic memory machinery
COREFORGE composes EvolveAI / CodeGenome-derived providers
```

### Desired direction

```text
Agent Memory owns generic memory machinery
COREFORGE consumes Agent Memory
```

COREFORGE may still own product-specific concerns such as:

- local-first application UX;
- encrypted-at-rest product packaging;
- product-specific caches;
- offline orchestration;
- UI-level context presentation;
- inference adapter selection.

It should not remain the canonical owner of generic memory lifecycle, graph recall, semantic/vector retrieval, context-assembly semantics, or memory governance once Agent Memory provides those capabilities.

Historical inspections prove implementation ancestry and existence, not end-state ownership or current conformance.

## Verification peer: PrismPM

PrismPM may be valuable where its exact-state and replay mechanics can strengthen:

- canonical memory-state verification;
- deterministic replay;
- transition verification;
- atomic promotion/conformance evidence;
- release or checkpoint integrity.

That is a verification role. It is not a reason to put PrismPM in the ordinary recall path or make it an owner of memory semantics.

## FailSafe / Arbiter boundary

FailSafe or Arbiter may provide useful enforcement/evidence mechanics such as:

- policy enforcement;
- evidence capture;
- human approval gates;
- audit trails;
- action governance.

They may further constrain a consequence or attest to enforcement. They do not become the origin of PAMA or the owner of memory lifecycle, recall, correction, or forgetting.

## Negative / failure memory

Shadow Genome concepts are treated as implementation ancestry for Agent Memory negative/failure memory rather than a permanent standalone owner.

Useful principles include:

- preserve causal evidence and applicability scope;
- do not convert a high-confidence failure pattern into a global prohibition automatically;
- retain provenance from promoted guardrails to the failures/evidence that justified them.

## Durable decision memory

Decision continuity, drift, rationale preservation, supersession, and durable decision recall are **Agent Memory capabilities**.

See [`profiles/durable-decision-memory-profile.md`](profiles/durable-decision-memory-profile.md).

A product may implement or consume the profile without becoming its doctrine owner.

## Cross-component control contract

Native modules, domain sources, and optional peers should preserve these control classes:

```text
DETERMINISTIC_SUBSTRATE
exact identity, schema, authorization primitives, state validity, committed receipts

PROBABILISTIC_EPISTEMICS
confidence, relevance, trust, contradiction, semantic similarity, staleness, risk estimates

GOVERNANCE_ENVELOPE
policy-defined permitted / prohibited / review-required outcomes

BOUNDED_ACTION_SELECTION
optional deterministic or stochastic choice among already-permitted actions

COMMITTED_CONSEQUENCE
state mutation, ledger record, scope change, certification, deletion, or other durable effect
```

A module may participate in more than one class, but it must expose the boundary between them.

## Harvest evidence rule

A same-owner ancestor should be harvested only when the mechanism has enough evidence to justify adoption.

For each mechanism record, as applicable:

1. exact source revision or historical implementation boundary;
2. behavior being harvested;
3. tests or fixtures proving the useful behavior;
4. failure modes and limitations;
5. which Agent Memory contract it implements;
6. how currentness/correction/deletion/scope behave;
7. whether any estimator output is involved;
8. authority effect, which must remain explicit;
9. native Agent Memory regression evidence after absorption.

The objective is not to preserve repository topology. It is to preserve useful behavior and evidence while simplifying the runtime boundary.

## Source of truth policy

Agent Memory owns its generic memory architecture and runtime contracts.

Related repositories may:

- contribute implementation ancestry;
- supply specialized domain evidence;
- expose optional interoperability or verification primitives;
- consume Agent Memory downstream.

They do not need to remain runtime dependencies for Agent Memory doctrine or generic memory capabilities to be legitimate or functional.

## Current implementation priority

Issue #455 tracks the ownership reconciliation.

Issue #456 begins the first native-harvest implementation slice:

```text
EvolveAI / CodeGenome vector behavior
  -> Agent Memory native semantic/vector candidate retrieval
  -> existing governed recall admission
```

The planned direction after that is native temporal/graph retrieval, native metabolism, and a continuous memory-evaluation loop, all without recreating permanent cross-repository runtime ownership.