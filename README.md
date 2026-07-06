# Agent Memory

Canonical architecture, doctrine, and implementation map for governed agentic memory systems.

This repository consolidates memory-system logic distributed across UOR, EvolveAI, CodeGenome, COREFORGE Vault / Neurospace, PAMA, and related governance work.

The goal is not to create another memory implementation. The goal is to define the shared doctrine that implementations can conform to.

## Core thesis

Agentic memory is not retrieval.

Agentic memory is governed state transition over addressable artifacts, scored by calibrated relevance, constrained by mutation authority, and confirmed by provenance or certification before becoming durable.

## Repository structure

```text
.
├── README.md
├── docs/
│   ├── AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md
│   ├── 00-glossary.md
│   ├── 01-layer-model.md
│   ├── 02-lifecycle-state-machine.md
│   ├── 03-scoring-and-decay.md
│   ├── 04-governance-and-pama.md
│   ├── 05-repo-implementation-map.md
│   ├── 06-conformance-test-plan.md
│   ├── 07-integration-roadmap.md
│   ├── 08-source-material-index.md
│   ├── 09-calibration-protocol.md
│   ├── 10-memory-unit-examples.md
│   └── adr/
│       ├── ADR-001-uor-is-identity-not-memory.md
│       ├── ADR-002-saturation-is-routing-not-truth.md
│       ├── ADR-003-crystallization-requires-certification.md
│       ├── ADR-004-pama-controls-mutation-authority.md
│       ├── ADR-005-codegenome-is-code-reality-substrate.md
│       └── ADR-006-neurospace-is-runtime-memory-space.md
├── fixtures/
│   ├── access-spam-junk.json
│   ├── certified-durable-memory.json
│   ├── confidently-wrong-memory.json
│   ├── contradicted-memory.json
│   ├── ephemeral-memory.json
│   ├── pruning-with-audit-preservation.json
│   ├── unauthorized-mutation-attempt.json
│   └── valuable-persistent-memory.json
├── schemas/
│   ├── conformance-report.schema.json
│   └── memory-unit.schema.json
├── scripts/
│   └── validate_fixtures.py
└── .github/
    └── ISSUE_TEMPLATE/
        └── doctrine-consolidation-task.md
```

## Layer summary

| Layer | Responsibility |
|---|---|
| UOR | Identity, deterministic addressability, exact object resolution |
| Evidence | Observations, provenance, confidence, witness material |
| Saturation / PRISM | Relevance scoring, lifecycle routing, decay pressure |
| Lifecycle | Memory state transitions from transient to crystallized or pruned |
| PAMA | Mutation authority, promotion authority, adaptive guardrails |
| Certification | Confirmation, integrity, authorization, and permanence gates |
| Neurospace / Vault | Local runtime memory space used by agents and products |
| CodeGenome | Canonical code reality graph and evidence substrate for software artifacts |

## Start here

Read these first:

1. `docs/AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md`
2. `docs/00-glossary.md`
3. `docs/01-layer-model.md`
4. `docs/06-conformance-test-plan.md`
5. `docs/09-calibration-protocol.md`

Then use the ADRs to anchor implementation decisions.

## Fixture validation

Run the fixture validator from the repository root:

```bash
python scripts/validate_fixtures.py
```

The validator uses only the Python standard library.

## Non-goals

This repo is not:

- a vector database
- a chatbot memory prompt pack
- a replacement for UOR, EvolveAI, CodeGenome, or COREFORGE
- a dumping ground for every interesting memory idea ever conceived by a human avoiding sleep

It is the canonical spine for organizing those ideas.
