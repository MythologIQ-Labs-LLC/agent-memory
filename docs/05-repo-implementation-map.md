# Repo Implementation Map

## Purpose

This map assigns each related repository or system to a canonical role in the agentic memory architecture.

The goal is to prevent repo-specific terminology from fragmenting the doctrine.

## System map

| System | Canonical role | Primary responsibility |
|---|---|---|
| UOR Framework | Identity substrate | deterministic addressability, exact object resolution, content identity |
| EvolveAI | Memory metabolism prototype | lifecycle orchestration, decay, tier routing, crystallization prototype |
| CodeGenome | Code reality graph | code artifact graph, overlays, confidence fusion, provenance, impact traversal |
| COREFORGE Vault | Runtime memory container | encrypted local memory, graph recall, context windows, governed storage |
| Neurospace | Operational memory space | agent-facing memory traversal and use within COREFORGE |
| PAMA | Mutation authority model | governed promotion, mutation, pruning, adaptation, canonicalization |
| FailSafe | Governance enforcement | evidence capture, approval gates, policy checks, release/session audit |
| Arbiter | Product policy guardian | authorization, rate limits, audit logging, action boundaries |
| Bicameral | Decision continuity layer | durable decision state, drift detection, team/agent alignment |
| Shadow Genome | Negative memory substrate | failure patterns, blocked behaviors, prior harm avoidance |

## UOR Framework

### Canonical owner of

- identity
- deterministic addressability
- exact object resolution
- content-addressed lookup

### Should import from this doctrine

- saturation is not identity
- lifecycle scoring belongs outside the addressing kernel
- crystallization requires certification or policy authority

## EvolveAI

### Canonical owner of

- autopoietic memory theory prototype
- memory metabolism
- L1 / L2 / L3 tier model
- REM synthesis
- CMHL decay engine
- lifecycle orchestration

### Should import from this doctrine

- PAMA authority for promotion and mutation
- calibration protocol for saturation thresholds
- trap-class conformance tests
- certification gate before durable crystallization

## CodeGenome

### Canonical owner of

- code artifact graph
- BLAKE3 node identity for code objects
- observer separation
- confidence fusion
- provenance and evidence bundles
- governed code reality queries

### Should import from this doctrine

- confidence is evidence support, not lifecycle permanence
- code graph nodes can become memory units when consumed by agents
- memory lifecycle state should preserve graph provenance

## COREFORGE Vault / Neurospace

### Canonical owner of

- local-first memory storage
- encrypted Vault memory
- runtime graph recall
- RAG and context windows
- product-level memory UX

### Should import from this doctrine

- memory write boundary must enforce PAMA
- crystallization should be ledgered
- runtime usefulness must not imply permanence
- user-visible correction and dispute flows are required for durable memory

## PAMA

### Canonical owner of

- mutation authority
- promotion authority
- adaptive constraints
- authority scaling by risk and reversibility

### Should import from this doctrine

- saturation proposes transitions but does not authorize them
- certification gates durable memory
- all mutation authority must be scoped and auditable

## FailSafe / Arbiter

### Canonical owner of

- policy enforcement
- evidence capture
- human approval gates
- audit trails
- action governance

### Should import from this doctrine

- memory mutation must be treated as an governed action
- durable memory changes require evidence and rollback paths
- approval workflows should bind to lifecycle transitions

## Bicameral

### Canonical owner of

- decision continuity
- drift detection
- durable decision alignment
- team and agent consensus surfaces

### Should import from this doctrine

- decisions are high-risk memory objects
- decision changes must preserve old state and rationale
- drift should trigger dispute or correction, not silent overwrite

## Source of truth policy

This repo owns the doctrine.

Other repos may own implementations, experiments, and product behavior, but should reference this doctrine for shared terms and boundaries.

## Implementation labels

Suggested labels for cross-repo issues:

```text
agent-memory
memory-doctrine
pama
governed-memory
crystallization
saturation-calibration
neurospace
uor-identity
code-reality-graph
conformance
```

## Required cross-repo backlinks

Each implementation repo should eventually include a short doctrine pointer:

```text
This implementation follows the Agent Memory doctrine in Knapp-Kevin/agent-memory.
```

And should link to the specific docs it conforms to.
