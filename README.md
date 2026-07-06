# Agent Memory

Canonical architecture, doctrine, and implementation map for governed agentic memory systems.

This repository consolidates memory-system logic distributed across UOR, EvolveAI, CodeGenome, COREFORGE Vault / Neurospace, PAMA, and related governance work.

The goal is not to create another memory implementation. The goal is to define the shared doctrine that implementations can conform to.

## Core thesis

Agentic memory is not retrieval.

Agentic memory is governed state transition over addressable artifacts, scored by calibrated relevance, constrained by mutation authority, and confirmed by provenance or certification before becoming durable.

## Architecture posture

Agent Memory is one overall architecture composed of bounded components.

It is unified by shared contracts, vocabulary, and conformance expectations. It is segmented by responsibility so identity, evidence, scoring, lifecycle, governance, certification, runtime use, and conformance do not collapse into one vague mega-layer.

It should be treated as a reference architecture for governed agent memory systems, not as a single memory library.

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
│   ├── 11-component-architecture.md
│   ├── 12-concept-segmentation-matrix.md
│   ├── 13-system-composition-boundaries.md
│   ├── 14-expanded-scope-recommendations.md
│   └── adr/
│       ├── ADR-001-uor-is-identity-not-memory.md
│       ├── ADR-002-saturation-is-routing-not-truth.md
│       ├── ADR-003-crystallization-requires-certification.md
│       ├── ADR-004-pama-controls-mutation-authority.md
│       ├── ADR-005-codegenome-is-code-reality-substrate.md
│       ├── ADR-006-neurospace-is-runtime-memory-space.md
│       └── ADR-007-agent-memory-is-component-architecture.md
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

## Component summary

| Component | Role |
|---|---|
| Identity Substrate | stable object identity |
| Evidence and Provenance Substrate | source support and witness material |
| Reality Graphs | structured domain truth with confidence and provenance |
| Lifecycle Engine | governed memory state transitions |
| Saturation and Decay Engine | calibrated persistence pressure |
| Governance and Mutation Authority | permission to mutate, promote, prune, or canonize |
| Certification and Crystallization Gate | durable transition confirmation |
| Runtime Memory Space | operational agent memory use |
| Context Assembly Surface | scoped recall into agent context |
| Correction and Dispute Surface | safe revision, demotion, and reconciliation |
| Conformance and Calibration Harness | fixtures, trap classes, reports, and thresholds |
| Product and Agent Integrations | implementation adoption surfaces |

## Expansion candidates

The highest-value expansion areas are:

1. source trust and reputation
2. conflict resolution
3. temporal causality
4. privacy and sensitivity classification
5. memory threat modeling
6. query planning and governed recall
7. schema registry and type evolution
8. multi-agent shared memory protocol

See `docs/14-expanded-scope-recommendations.md`.

## Start here

Read these first:

1. `docs/AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md`
2. `docs/11-component-architecture.md`
3. `docs/12-concept-segmentation-matrix.md`
4. `docs/13-system-composition-boundaries.md`
5. `docs/14-expanded-scope-recommendations.md`
6. `docs/00-glossary.md`
7. `docs/01-layer-model.md`
8. `docs/06-conformance-test-plan.md`
9. `docs/09-calibration-protocol.md`

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
