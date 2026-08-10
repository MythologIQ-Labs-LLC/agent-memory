# Repo Implementation Map

## Purpose

This map assigns each related repository or system to a canonical role in the agentic memory architecture.

The goal is to prevent repo-specific terminology from fragmenting the doctrine.

A second goal is to prevent implementations from collapsing probabilistic estimation, governance, and committed state mutation into one opaque subsystem.

## System map

| System | Canonical role | Primary responsibility | Governed-uncertainty posture |
|---|---|---|---|
| UOR Framework | Identity substrate | deterministic addressability, exact object resolution, content identity | deterministic substrate; must not infer authority |
| EvolveAI | Memory metabolism prototype | lifecycle orchestration, decay, tier routing, crystallization prototype | probabilistic/heuristic proposals allowed; lifecycle commit remains governed |
| CodeGenome | Code reality graph | code artifact graph, overlays, confidence fusion, provenance, impact traversal | inferred relations must preserve confidence, estimator provenance, and disagreement |
| COREFORGE Vault | Runtime memory container | encrypted local memory, graph recall, context windows, governed storage | probabilistic retrieval may generate candidates; scope and mutation boundaries remain enforced |
| Neurospace | Operational memory space | agent-facing memory traversal and use within COREFORGE | learned ranking may operate only inside recall-time policy |
| PAMA | Mutation authority model | governed promotion, mutation, pruning, adaptation, canonicalization | maps uncertain inputs into deterministic or formally bounded authority outcomes |
| FailSafe | Governance enforcement | evidence capture, approval gates, policy checks, release/session audit | binds policy version, estimator context, permitted action set, and consequence receipt |
| Arbiter | Product policy guardian | authorization, rate limits, audit logging, action boundaries | enforces prohibited and permitted actions independently of model confidence |
| Bicameral | Decision continuity layer | durable decision state, drift detection, team/agent alignment | drift/disagreement may be estimated probabilistically; durable decision changes remain governed |
| Shadow Genome | Negative memory substrate | failure patterns, blocked behaviors, prior harm avoidance | failure inference may be probabilistic; guardrail promotion must preserve evidence and authority |

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
- probabilistic interpretation must not contaminate exact identity semantics

### Governed-uncertainty contract

UOR should provide stable references that probabilistic layers can reason about without changing the identity of the underlying object. Exact reference resolution is a deterministic substrate concern, not a confidence-weighted guess.

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
- transition proposal must remain separate from transition commit
- estimator uncertainty, version, and calibration scope must remain inspectable
- threshold jitter and estimator disagreement require explicit handling

### Governed-uncertainty contract

EvolveAI may use learned or heuristic signals to propose decay, retention, consolidation, or promotion. Those signals must not self-authorize irreversible or canonical state changes.

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
- inferred edges should identify estimator/method version when material to downstream decisions
- confidence fusion should preserve material estimator disagreement rather than averaging it into invisibility

### Governed-uncertainty contract

Exact syntax or content-addressed facts may be deterministic while semantic overlays, entity resolution, impact estimates, and relation confidence remain probabilistic. Consumers must be able to tell which is which.

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
- retrieval ranking occurs before recall-time scope, tenancy, sensitivity, and certification filters
- stochastic strategy selection may occur only among policy-permitted recall or write actions

### Governed-uncertainty contract

High semantic relevance must not override privacy, tenancy, scope, dispute state, or policy. Candidate generation may be probabilistic; admission into active context remains governed.

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
- a fixed policy snapshot and committed input record must yield a reconstructable deterministic or formally bounded authority envelope
- estimator confidence does not resolve missing policy, authority, or scope

### Governed-uncertainty contract

PAMA consumes uncertainty. It does not become uncertainty. Its purpose is to convert estimates into a finite set of permitted, blocked, deferred, or review-required consequences.

## FailSafe / Arbiter

### Canonical owner of

- policy enforcement
- evidence capture
- human approval gates
- audit trails
- action governance

### Should import from this doctrine

- memory mutation must be treated as a governed action
- durable memory changes require evidence and rollback paths
- approval workflows should bind to lifecycle transitions
- receipts should bind estimator versions, policy version, permitted action set, selected action, and before/after state when relevant
- high-consequence actions should fail closed or escalate when required governance state cannot be reconstructed

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
- probabilistic drift detection or disagreement scoring may propose review but must not silently rewrite durable decisions

## Shadow Genome

### Canonical owner of

- negative memory and failure patterns
- recurrence avoidance
- blocked behaviors and learned caution

### Should import from this doctrine

- failure inference must preserve causal evidence and applicability scope
- a high-confidence negative pattern must not become a global prohibition without governed promotion
- guardrails derived from failure memory should retain provenance to the failures that justified them

## Cross-repo control contract

Implementations should identify which responsibilities they own using these control classes:

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

A repo may own more than one class, but it must expose the boundary between them.

## Required implementation evidence

A repo claiming governed-uncertainty alignment should be able to point to:

1. where probabilistic or learned estimates are produced
2. how those estimates identify their method/version and calibration scope
3. where policy converts estimates into authority outcomes
4. where prohibited actions are enforced
5. where the permitted action set is represented, if more than one action can follow
6. where committed state changes are ledgered
7. how estimator drift differs from policy change
8. how the implementation behaves when required authority inputs are missing

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
governed-uncertainty
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
