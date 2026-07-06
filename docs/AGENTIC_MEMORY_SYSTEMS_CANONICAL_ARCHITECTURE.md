# Agentic Memory Systems Canonical Architecture

## Purpose

This document defines the canonical architecture for governed agentic memory systems across UOR, EvolveAI, CodeGenome, COREFORGE Vault / Neurospace, PAMA, and related governance systems.

It consolidates the logic into one doctrine so implementations can stop rediscovering the same boundary decisions under different names.

## Core thesis

Agentic memory is not retrieval.

Agentic memory is governed state transition over addressable artifacts, scored by calibrated relevance, constrained by mutation authority, and confirmed by provenance or certification before becoming durable.

## Canonical pipeline

```text
Raw experience / artifact
        |
        v
UOR identity
What is it? Can it be addressed deterministically?
        |
        v
Evidence layer
Who observed it? What supports it? What confidence applies?
        |
        v
Saturation / PRISM layer
Should it persist, decay, route, recheck, or be proposed for crystallization?
        |
        v
PAMA governance layer
Is the system allowed to promote, mutate, canonize, or prune it?
        |
        v
Certification / crystallization gate
Can it become durable, canonical, or exact-address retrievable?
        |
        v
Neurospace / runtime memory
How does the agent use it operationally?
```

## Layer model

| Layer | Question answered | Canonical responsibility |
|---|---|---|
| UOR identity | What is this object? | Deterministic content address, exact identity, object resolution |
| Evidence | Why do we believe this object or relation exists? | Provenance, witness material, confidence, observation records |
| Saturation / PRISM | How durable or relevant is this object? | Calibrated scoring, routing, decay, tier candidacy |
| Lifecycle | What state is this memory in? | State transitions, decay, dispute, pruning, crystallization candidacy |
| PAMA | Who or what may change this memory? | Mutation authority, adaptation limits, policy-weighted promotion |
| Certification | Can this become durable? | Verification, approval, integrity checks, certificate gates |
| Runtime / Neurospace | How is this memory used? | Local operational memory, context assembly, graph recall, agent access |
| CodeGenome | What is true about code? | Canonical code reality graph, overlays, confidence fusion, impact traversal |

## Governing invariants

1. UOR identity is not memory.
2. Saturation is not truth.
3. Repetition is not durability.
4. Retrieval frequency is not permission to crystallize.
5. Crystallization is a governed transition, not a natural reward.
6. Certification confirms what saturation only proposes.
7. Provenance must survive summarization.
8. A memory that cannot be disputed cannot be trusted.
9. Mutation authority must be explicit and scoped.
10. Runtime usefulness does not imply canonical permanence.

## Memory state machine

```text
Transient
  -> Observed
  -> Linked
  -> Reinforced
  -> Candidate
  -> Pending Verification
  -> Crystallized
  -> Operationally Reused
  -> Stale
  -> Disputed
  -> Corrected
  -> Reconciled
  -> Pruned
```

Not all memories move through every state. The state machine exists to make every durable transition explainable.

## Memory object model

A canonical memory object should carry at least:

```text
id: UOR address or implementation-specific identity pointer
content_ref: pointer to raw or canonical content
type: observation | decision | fact | trace | code_artifact | preference | policy | failure | correction
evidence: list of evidence records
provenance: origin, observer, timestamp, method
confidence: evidence-level confidence
saturation: calibrated lifecycle score
state: lifecycle state
authority: mutation and promotion authority scope
certification: optional confirmation record
decay_profile: half-life, pressure, last access, dispute status
ledger_ref: audit or history pointer
```

## Distinction between confidence, saturation, and certification

| Signal | Means | Does not mean |
|---|---|---|
| Confidence | Evidence suggests this observation or relation is valid | The memory should persist forever |
| Saturation | The memory has lifecycle relevance or persistence pressure | The memory is correct |
| Certification | A verification or approval gate was satisfied | The memory can never be revised |

This distinction is mandatory. Collapsing these signals creates hallucination permanence.

## Crystallization rule

A memory may be crystallized only when all required gates pass:

```text
identity_resolved == true
provenance_present == true
saturation >= calibrated_threshold
trap_class_check == pass
pama_authority == allow
certification_gate == pass
```

A high saturation score may propose crystallization. It must not grant crystallization by itself unless an explicit policy permits that risk.

## Implementation doctrine

The repo ecosystem should map to this architecture as follows:

| System | Role |
|---|---|
| UOR Framework | Identity substrate and addressability model |
| EvolveAI | Memory metabolism prototype and lifecycle engine |
| CodeGenome | Canonical graph substrate for software reality |
| COREFORGE Vault / Neurospace | Product runtime memory container |
| PAMA | Mutation authority and adaptive governance model |
| FailSafe / Arbiter | Governance enforcement, evidence capture, approval gates |
| Bicameral | Decision continuity and drift detection surface |

## Conformance expectation

Any implementation claiming alignment with this doctrine should be able to demonstrate:

1. deterministic identity or stable reference resolution
2. durable provenance for memory creation and mutation
3. calibrated saturation or equivalent lifecycle scoring
4. trap-class resistance against access-spam and confidently-wrong promotion
5. explicit mutation authority
6. dispute and correction pathways
7. audit evidence for crystallization
8. safe pruning behavior for ephemeral or contradicted memory
