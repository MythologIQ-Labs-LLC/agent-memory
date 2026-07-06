# Source Material Index

## Purpose

This index records the conceptual sources that fed the doctrine.

It is not a complete bibliography. It is a working map of where the ideas currently live so they can be reconciled without treating every repo as its own little kingdom.

## Primary source systems

| Source | Relevant doctrine area |
|---|---|
| UOR Framework issue 2 | saturation-derived decay, crystallization, O(1) exact-address transition |
| UOR issue comment by maurathat | decay calibration protocol, saturation as routing, certification distinction |
| EvolveAI | autopoietic memory, L1/L2/L3 tiers, CMHL, REM synthesis, Shadow Genome |
| CodeGenome | content-addressed code reality graph, overlays, confidence fusion, provenance |
| COREFORGE | local-first product runtime, Vault, Neurospace, governed agent modules |
| PAMA logic | mutation authority, adaptive guardrails, promotion and pruning policy |
| FailSafe / Arbiter | evidence capture, policy gates, approval boundaries, audit trails |
| Bicameral | decision continuity, drift detection, durable decisions |

## UOR Framework

Relevant ideas:

- UOR identity as deterministic addressability
- saturation-derived decay
- crystallization as durable memory transition
- exact-address lookup after crystallization
- distinction between kernel identity and PRISM-style routing consumer

Doctrine placement:

- `docs/01-layer-model.md`
- `docs/03-scoring-and-decay.md`
- `docs/adr/ADR-001-uor-is-identity-not-memory.md`
- `docs/adr/ADR-002-saturation-is-routing-not-truth.md`

## EvolveAI

Relevant ideas:

- autopoietic memory system
- 5-phase metabolic lifecycle
- L1 transient cache, L2 temporal graph, L3 UOR vault
- memory tier score
- cryptographic memory half-life
- Shadow Genome

Doctrine placement:

- `docs/02-lifecycle-state-machine.md`
- `docs/03-scoring-and-decay.md`
- `docs/06-conformance-test-plan.md`

## CodeGenome

Relevant ideas:

- canonical code reality graph
- BLAKE3 graph node identity
- observer separation
- provenance
- confidence fusion
- governance and evidence bundles

Doctrine placement:

- `docs/01-layer-model.md`
- `docs/05-repo-implementation-map.md`
- `docs/adr/ADR-005-codegenome-is-code-reality-substrate.md`

## COREFORGE Vault / Neurospace

Relevant ideas:

- local-first memory runtime
- encrypted Vault storage
- knowledge graph and RAG recall
- context window assembly
- governed autonomy
- agent-facing runtime memory

Doctrine placement:

- `docs/01-layer-model.md`
- `docs/04-governance-and-pama.md`
- `docs/adr/ADR-006-neurospace-is-runtime-memory-space.md`

## PAMA

Relevant ideas:

- proportional adaptive mutation authority
- promotion authority
- adaptive mutation constraints
- governance by risk, scope, reversibility, and evidence

Doctrine placement:

- `docs/04-governance-and-pama.md`
- `docs/adr/ADR-004-pama-controls-mutation-authority.md`

## Open consolidation questions

1. Should saturation be represented as one scalar or a vector of durability dimensions?
2. Should PAMA authority be evaluated before or after saturation reaches candidate threshold?
3. How should certification expire or be renewed?
4. How should Neurospace expose disputed memory to agents without allowing canonical misuse?
5. Which memory types require human approval before crystallization?
6. What is the minimum viable conformance fixture schema?
7. How should CodeGenome graph confidence flow into general agent memory saturation?

## Maintenance rule

When a new memory-system idea appears, place it in one of these categories before adding implementation work:

```text
identity
evidence
saturation
lifecycle
governance
certification
runtime
conformance
```

If it does not fit, create an issue before creating a new concept.
