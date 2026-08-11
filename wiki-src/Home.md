# Agent Memory

**A field guide to governed memory for autonomous and agentic systems.**

Agent Memory is about more than retrieving old context. It defines what becomes memory, what remains uncertain, what may influence future behavior, who may change durable state, and how retained state can be corrected or forgotten.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/agent-memory-flow.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/agent-memory-flow-light.svg">
    <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/agent-memory-flow-light.svg" alt="Agent Memory governed memory loop showing interpretation, evidence and proposal, PAMA governance, permitted action selection, retained memory, governed recall, and active agent context" width="100%">
  </picture>
</p>

> **Agentic memory is retained state that can alter an agent's future interpretation, reasoning, planning, tool use, action, or adaptation across a meaningful persistence boundary.**

## Start with the question you have

**I want the architecture in pictures.**  
Start with **[Decision Flows and Memory Lifecycle](Decision-Flows-and-Memory-Lifecycle)**. It is the visual map for lifecycle, strength/stability, PAMA, recall, temporal correction, deletion completeness, executable scenarios, and evidence boundaries.

**I am new to Agent Memory.**  
Read **[Getting Started](Getting-Started)**, then **[Core Concepts](Core-Concepts)** for the vocabulary and invariants that the diagrams preserve.

**I am implementing a memory system.**  
Use the **[Implementation Guide](Implementation-Guide)**, then **[PAMA](PAMA)**, **[Lifecycle and Forgetting](Lifecycle-and-Forgetting)**, and **[Canonical and Derived State](Canonical-and-Derived-State)** for the consequential boundaries.

**I am evaluating whether a claim is actually proven.**  
Use **[Conformance and Evidence](Conformance-and-Evidence)** for the evidence ladder and **[Runtime Evidence](Runtime-Evidence)** for what has actually executed.

## Follow the architecture

1. **Observe and estimate.** Experience becomes evidence, provenance, uncertainty, and a proposal. See **[Core Concepts](Core-Concepts)**.
2. **Govern consequences.** PAMA resolves what actions are permitted. Evidence may strengthen a proposal; it does not manufacture authority. See **[PAMA](PAMA)**.
3. **Commit explicit state.** A permitted consequence becomes retained state with reconstructable evidence. See **[Lifecycle and Forgetting](Lifecycle-and-Forgetting)**.
4. **Recall through admission.** Retrieval creates candidates; governance decides what may enter active context. See **[Decision Flows and Memory Lifecycle](Decision-Flows-and-Memory-Lifecycle#4-governed-recall-pipeline)**.
5. **Correct, supersede, or forget.** Historical truth, correction, staleness, supersession, deletion, and residue remain distinct. See **[Lifecycle and Forgetting](Lifecycle-and-Forgetting)** and **[Canonical and Derived State](Canonical-and-Derived-State)**.
6. **Verify without inflating claims.** Runtime and portable evidence can prove specific relationships and outcomes without becoming semantic authority. See **[Runtime Evidence](Runtime-Evidence)**.

The core separations are deliberately simple to state and expensive to violate:

```text
confidence != truth
saturation != authority
relevance != permission
proposal != commit
retrieval != recall admission
staleness != falsity
delete operation != forgetting completeness
```

For the complete visual set and nearby canonical-source links, use **[Decision Flows and Memory Lifecycle](Decision-Flows-and-Memory-Lifecycle)**.

## What makes the architecture different

Agent Memory separates four jobs that are often collapsed into one opaque score:

- **Epistemics** estimates relevance, trust, contradiction, sensitivity, utility, staleness, and other uncertain properties.
- **Governance** determines which consequences are allowed under current policy, scope, authority, and state.
- **Commit** applies an explicit state transition and emits reconstructable evidence.
- **Recall** admits retained state into active context only when relevance and authorization both permit it.

> **Probabilistic epistemics. Governed consequences.**  
> **Uncertainty may propose. Authority constrains.**

## Current maturity

- **Canonical doctrine:** ADR-001 through ADR-019 are Accepted.
- **Emerging decisions:** ADR-020, ADR-021, and ADR-022 remain Proposed and keep their own evidence gates.
- **Executed evidence:** the repository exercises a governed reference adapter, P4 deletion-completeness paths, and the P4.5 portable-governance-evidence chain with adversarial negative cases.
- **Claim boundary:** those executions do not automatically raise a conformance level or accept an ADR.

See **[Architecture Decisions](Architecture-Decisions)** for doctrine maturity and **[Runtime Evidence](Runtime-Evidence)** for the executable evidence ledger.

## Explore the rest

- **[Governed Uncertainty](Governed-Uncertainty)** for deterministic governance around probabilistic discovery
- **[Security and Privacy](Security-and-Privacy)** for scope, deletion, and leakage risks
- **[Research and Sources](Research-and-Sources)** for supporting and challenging research
- **[Aligned Projects & Intellectual Lineage](Aligned-Projects-and-Intellectual-Lineage)** for external influences and architectural relationships
- **[Contributing](Contributing)** for contribution rules

## Canonical source

The Wiki is the readable navigation and explanation layer. The numbered repository documentation remains authoritative.

**Canonical repository:** https://github.com/MythologIQ-Labs-LLC/agent-memory  
**Documentation index:** https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/README.md  
**Architecture decisions:** https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/main/docs/adr
