# Decision Flows and Memory Lifecycle

This page is a **visual map of existing Agent Memory doctrine**. It is not a new doctrine source, decision table, runtime guarantee, or substitute for the canonical numbered documentation.

Use each diagram to answer one architectural question, then follow the canonical source link when implementation or conformance depends on the exact contract.

| Principal question | Visual | Canonical source |
|---|---|---|
| How can retained state strengthen, weaken, be disputed, corrected, reconciled, or pruned? | [Lifecycle state map](#1-memory-lifecycle-state-map) | [`docs/02-lifecycle-state-machine.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/02-lifecycle-state-machine.md) |
| Which signals strengthen or weaken persistence without creating authority? | [Strength and stability](#2-strength-and-stability-dynamics) | [`docs/03-scoring-and-decay.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/03-scoring-and-decay.md) |
| What authority outcome is allowed for a proposed mutation? | [PAMA decision flow](#3-pama-mutation-authority-decision-flow) | [`docs/pama/README.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/pama/README.md) |
| Which retrieved candidates may enter active context, and under what treatment? | [Governed recall](#4-governed-recall-pipeline) | [`docs/26-governed-recall-planner.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/26-governed-recall-planner.md) |
| How should readers distinguish supersession, correction, dispute, and staleness across time? | [Temporal change](#5-temporal-change-correction-and-supersession) | [`docs/18-temporal-causality-layer.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/18-temporal-causality-layer.md) |

## Reading rule

The diagrams deliberately preserve distinctions that are easy to destroy through visual simplification:

```text
confidence != truth
saturation != confidence
saturation != authority
relevance != permission
certification != permanence forever
staleness != falsity
supersession != correction
delete operation != forgetting completeness
retrieval != recall admission
same agent != same memory scope
proposal != commit
```

When a visual and a canonical document appear to differ, **the canonical document governs**. Open an issue rather than treating the picture as an independent policy source.

## 1. Memory lifecycle state map

**Question:** How can retained state strengthen, weaken, be disputed, corrected, reconciled, or pruned?

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/lifecycle-flow.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/lifecycle-flow-light.svg">
    <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/lifecycle-flow-light.svg" alt="Agent Memory lifecycle state map showing strengthening and promotion, demotion, dispute, correction, reconciliation, pruning, and the separation between transition proposal and committed state" width="100%">
  </picture>
</p>

Not every memory traverses every state. `Crystallized` is durable under current evidence and policy, not eternal. `Pruned` removes memory from active recall or durable lifecycle consideration according to policy and does not necessarily mean physical deletion.

**Readable Wiki context:** [Lifecycle and Forgetting](Lifecycle-and-Forgetting)  
**Canonical contract:** [`docs/02-lifecycle-state-machine.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/02-lifecycle-state-machine.md)

## 2. Strength and stability dynamics

**Question:** Which signals strengthen or weaken a memory's case for persistence without creating authority?

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/strength-stability-flow.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/strength-stability-flow-light.svg">
    <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/strength-stability-flow-light.svg" alt="Agent Memory strength and stability map separating evidence confidence, source trust, saturation, contradiction pressure, certification, lifecycle stability, and PAMA authority" width="100%">
  </picture>
</p>

Evidence, verification, corroboration, meaningful reuse, and stable provenance can strengthen the case for persistence. Contradiction, expiry, invalidation, uncertainty, and drift can weaken it. Neither direction grants authority to promote, share, execute, or delete. Exact operating thresholds remain calibrated implementation choices rather than doctrine.

**Readable Wiki context:** [Core Concepts](Core-Concepts)  
**Canonical contracts:** [`docs/03-scoring-and-decay.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/03-scoring-and-decay.md) · [`docs/16-source-trust-and-reputation.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/16-source-trust-and-reputation.md) · [`docs/04-governance-and-pama.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/04-governance-and-pama.md)

## 3. PAMA mutation-authority decision flow

**Question:** What authority outcome is allowed for a proposed mutation?

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/pama-decision-flow.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/pama-decision-flow-light.svg">
    <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/pama-decision-flow-light.svg" alt="PAMA mutation authority decision flow showing proposal classification, authority floors, policy modifiers, outcome resolution, permitted action set construction, and commit or deferral with evidence" width="100%">
  </picture>
</p>

PAMA is multidimensional governance, not a single memory-quality score. Target class, lifecycle strength, requested operation, downstream authority, consequence, actor, evidence, uncertainty, and policy remain distinct. Confidence or saturation can contribute evidence but cannot expand an otherwise prohibited authority envelope.

**Readable Wiki context:** [PAMA](PAMA)  
**Canonical contracts:** [`docs/pama/README.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/pama/README.md) · [`docs/33-pama-decision-table.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/33-pama-decision-table.md) · [ADR-004](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/adr/ADR-004-pama-controls-mutation-authority.md)

## 4. Governed recall pipeline

**Question:** Which retrieved candidates may enter active context, and under what treatment?

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/governed-recall-flow.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/governed-recall-flow-light.svg">
    <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/governed-recall-flow-light.svg" alt="Governed recall pipeline showing request resolution, candidate generation and normalization, recall admission, ranking only among admitted candidates, composition risk, context budgeting, governed assembly, and recall explanation" width="100%">
  </picture>
</p>

Candidate generation may be probabilistic. Admission is governed. Ranking occurs only among admitted candidates, composition has its own policy boundary, and context budgeting cannot discard required governance state. A stronger retrieval score never reopens a blocked candidate.

**Readable Wiki context:** [Implementation Guide](Implementation-Guide)  
**Canonical contract:** [`docs/26-governed-recall-planner.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/26-governed-recall-planner.md) · [ADR-013](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/adr/ADR-013-governed-recall-planner-is-required.md)

## 5. Temporal change, correction, and supersession

**Question:** How should readers distinguish supersession, correction, dispute, and staleness across time?

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/temporal-correction-flow.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/temporal-correction-flow-light.svg">
    <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/diagrams/temporal-correction-flow-light.svg" alt="Temporal change diagram distinguishing historically true state that is later superseded, wrong or incomplete state that is corrected, uncertain state that is disputed, and old but historically valid state that is stale for current-state recall" width="100%">
  </picture>
</p>

Supersession preserves a previously valid state while a newer state becomes current. Correction records that an earlier claim was wrong or materially incomplete within its claimed scope or time. Dispute preserves unresolved uncertainty. Staleness can reduce current-state usefulness without converting historical truth into falsity. Exact chronology does not establish causality, and inferred causal links must not rewrite the historical event log.

**Readable Wiki context:** [Lifecycle and Forgetting](Lifecycle-and-Forgetting)  
**Canonical contract:** [`docs/18-temporal-causality-layer.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/18-temporal-causality-layer.md) · [ADR-011](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/adr/ADR-011-temporal-causality-is-required-for-memory-evolution.md)

## What comes next

The remaining stable V2 visual work under issue #73 covers deletion completeness/derived-state propagation and the first scenario walkthroughs.

[ADR-021](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/adr/ADR-021-portable-memory-governance-evidence-boundary.md) and [ADR-022](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/adr/ADR-022-memory-isolation-domains-and-controlled-boundary-crossing.md) remain **Proposed**. This visual guide does not contain a visual that finalizes either boundary. Isolation-domain visuals must follow ADR-022's doctrine maturity, and portable-evidence visuals must follow ADR-021's executable interoperability evidence rather than inventing a wire model visually. A diagram does not raise an ADR status, conformance level, or runtime-evidence claim.

This page will remain an index into stable visual explanations as they land.
