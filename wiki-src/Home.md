# Agent Memory

**A field guide to governed memory for autonomous and agentic systems.**

Agent Memory asks a larger question than _“how do we retrieve old context?”_ It defines the architecture around what becomes memory, what remains uncertain, what may influence future behavior, who may change durable state, and how memory can be corrected or forgotten.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/agent-memory-flow.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/agent-memory-flow-light.svg">
    <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/agent-memory-flow-light.svg" alt="Agent Memory governed memory loop" width="100%">
  </picture>
</p>

> **Agentic memory is retained state that can alter an agent's future interpretation, reasoning, planning, tool use, action, or adaptation across a meaningful persistence boundary.**

## Choose your path

| I want to... | Start here |
|---|---|
| Understand the architecture quickly | **[Getting Started](Getting-Started)** |
| Learn the core vocabulary and invariants | **[Core Concepts](Core-Concepts)** |
| Understand adaptive authority | **[PAMA](PAMA)** |
| Design retention, consolidation, and forgetting | **[Lifecycle and Forgetting](Lifecycle-and-Forgetting)** |
| Separate probabilistic inference from consequential authority | **[Governed Uncertainty](Governed-Uncertainty)** |
| Review threat, privacy, and deletion risks | **[Security and Privacy](Security-and-Privacy)** |
| Evaluate evidence or runtime claims | **[Conformance and Evidence](Conformance-and-Evidence)** |
| See what has actually been executed | **[Runtime Evidence](Runtime-Evidence)** |
| Contribute research or challenge doctrine | **[Research and Sources](Research-and-Sources)** |
| Map a real memory system into the architecture | **[Implementation Guide](Implementation-Guide)** |
| Contribute to the project | **[Contributing](Contributing)** |

## The architecture in one minute

Agent Memory separates four jobs that are often collapsed into one opaque score:

| Layer | Job |
|---|---|
| **Epistemics** | Estimate relevance, trust, contradiction, sensitivity, utility, staleness, and other uncertain properties. |
| **Governance** | Determine which consequences are allowed under current policy, scope, authority, and state. |
| **Commit** | Apply an explicit state transition and emit reconstructable evidence. |
| **Recall** | Admit retained state into active context only when relevance and authorization both permit it. |

The governing rule is simple:

> **Probabilistic epistemics. Governed consequences.**  
> **Uncertainty may propose. Authority constrains.**

## What makes Agent Memory different

Agent Memory treats all of these as first-class architectural concerns:

- provenance and source trust
- short-, medium-, long-, remote-, and inherited persistence
- episodic, semantic, procedural, preference, policy, decision, and evidence memory
- contradiction, correction, supersession, and causality
- forgetting, deletion, redaction, tombstones, and deletion residue
- privacy, sensitivity, scope, tenancy, and consent
- adaptive mutation authority through **PAMA**
- receipts, replay, rollback, observability, and conformance evidence

## Current maturity

| Surface | State |
|---|---|
| Core doctrine | Canonical and extensively documented |
| PAMA | Native doctrine authored by Kevin R. Knapp |
| ADRs | ADR-001 through ADR-019 Accepted; ADR-020 Proposed |
| Schemas | 7 validated JSON Schemas |
| Conformance fixtures | 25 validated definitions |
| Runtime evidence | Reference adapter executed against a real substrate; broader ADR-020 proof remains incomplete |
| License | Apache-2.0 |

> **Important:** repository validation proves the declared schemas, fixtures, links, and doctrine boundaries are coherent. It does **not** magically prove a production runtime enforces them. Reality remains stubbornly outside the jurisdiction of JSON Schema.

## Canonical source

The Wiki is the readable navigation layer. The repository documentation is authoritative.

**Canonical repository:** https://github.com/MythologIQ-Labs-LLC/agent-memory  
**Documentation index:** https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/README.md  
**Architecture decisions:** https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/main/docs/adr
