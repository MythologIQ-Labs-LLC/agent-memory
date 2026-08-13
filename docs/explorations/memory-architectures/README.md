# Governed Memory Across Architecture Families

Status: **active exploratory research** under #67. This directory is not canonical doctrine.

## Purpose

Agent Memory is intended to govern retained state without assuming that memory must be represented as files, vectors, graphs, rows, events, latent state, or any single combination of them.

This program asks a harder question than “which backend is best?”:

> **Which governance obligations remain invariant, and which implementation/evidence techniques change, when memory is represented and retrieved through fundamentally different architecture families?**

The program became active after its original sequencing prerequisites were completed:

- #46 runtime-evidence program
- #63 portable governance evidence / AgenTrust interoperability
- #68 memory isolation domains and governed boundary crossing

Those programs now provide evidence and vocabulary that this exploration can pressure-test across architecture families.

## Strategic scope intent

Agent Memory's early emphasis on governance, provenance, lifecycle, correction, forgetting, isolation, and authority was a **sequencing decision**, not a permanent product boundary.

Those surfaces were the best place to start because they establish the control plane needed before adding more powerful and less inspectable memory mechanisms. The long-term scope is broader: Agent Memory should be capable of encompassing explicit durable memory, lexical/vector retrieval, graph memory, event/log memory, consolidation and tiering, learned or latent predictive state, world-model memory, planning context, and hybrid compositions where evidence shows they improve the system.

The intended direction is therefore not:

```text
governance/provenance around somebody else's memory system
```

It is closer to:

```text
Agent Memory
  = governed memory substrate(s)
  + provenance / evidence
  + lifecycle / correction / forgetting
  + recall / context assembly
  + learned and explicit representations
  + predictive / world-state memory where justified
  + isolation / authority / PAMA
  + reconstructable runtime evidence
```

No current representation is protected by historical sequencing. If comparative evidence shows that a learned predictive representation, graph, retrieval architecture, or hybrid should become a first-class operational memory layer, the architecture should evolve accordingly while preserving only the governance invariants that survive pressure-testing.

## Research products

This foundation slice is tracked by #224.

- [`taxonomy.md`](taxonomy.md) — architecture-family vocabulary and boundaries
- [`analysis-contract.md`](analysis-contract.md) — common questions every family must answer
- [`governance-comparison-matrix.md`](governance-comparison-matrix.md) — bounded cross-family comparison with explicit evidence status
- [`hybrid-composition-patterns.md`](hybrid-composition-patterns.md) — governance of multi-stage memory compositions
- [`adversarial-scenarios.md`](adversarial-scenarios.md) — equivalent pressure tests for later representative substrates
- [`opaque-latent-predictive-state.md`](opaque-latent-predictive-state.md) — #137 JEPA/latent predictive-state study and comparative architecture hypotheses

Follow-on family studies should eventually include file/note memory, lexical/vector RAG, knowledge graphs, GraphRAG, event logs, relational/document stores, hierarchical memory, shared/distributed memory, and opaque learned/latent state.

## Evidence status

Every architecture claim must carry one of these evidence states:

```text
architectural_deduction
primary_research_supported
implementation_observed
benchmark_or_conformance_evidence
cross_architecture_reproduced
open_hypothesis
contradicted
not_yet_evaluated
```

A claim may carry supporting and challenging evidence simultaneously. Do not average them into a confidence score.

The source-neutral rule from the repository evidence-promotion policy remains controlling:

```text
origin / provenance
!= evidence strength
!= promotion authority
```

A paper, implementation, maintainer statement, benchmark, community report, local experiment, or architectural argument may all produce useful evidence. None becomes doctrine because of who or what produced it.

## Common architecture-neutral invariants under test

The following are **hypotheses to pressure-test**, not conclusions this research is required to preserve:

```text
retrieval relevance != recall permission
probabilistic discovery != durable write authority
canonical state != derived projection
correction != silent overwrite
historical evidence != current truth
successful deletion operation != forgetting proof
representation compression != scope erasure
predictive quality != action authority
external/runtime evidence != lifecycle satisfaction
```

A cross-architecture counterexample is valuable. A no-change result where the current doctrine survives a materially different architecture is also valuable.

## Relationship to #137 and #138

#137 tests the representation-agnostic hypothesis against opaque learned/JEPA-style predictive state. It should be treated as an adversarial architecture family and a serious candidate operational memory architecture, not an exotic footnote or a mechanism that must remain merely external to Agent Memory.

#138 supplies recurring field claims, benchmark failures, context-assembly questions, long-horizon degradation hypotheses, and evaluation-contamination risks. It is a research feed into this program, not a source of doctrine by itself.

## Research sequence

```text
Phase A0  taxonomy + common analysis contract
Phase A1  architecture-family studies
Phase A2  hybrid-composition studies
Phase A3  select representative substrates
Phase A4  equivalent cross-architecture experiments
Phase A5  adversarial review and promotion decisions
```

Do not choose representative products before the family taxonomy is stable enough to prevent one implementation from defining the category.

## Promotion boundary

Research findings may move into numbered doctrine, ADRs, schemas, profiles, fixtures, or conformance only when the evidence-promotion policy is satisfied.

This directory should preserve rejected hypotheses and doctrine-survives results instead of silently deleting them. The goal is a reconstructable research record, not a persuasive essay that remembers only successful arguments.
