<p align="center">
  <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/brand/agent-memory-wiki-cover.png" alt="Agent Memory Wiki cover showing the MythologIQ Labs lineage and the Agent Memory layered memory emblem with a cyan inference spark." width="100%">
</p>

# Agent Memory

**A reference architecture for governed memory in autonomous and agentic systems.**

Agent Memory is about retained state that can influence future behavior without quietly acquiring truth, scope, permanence, or authority it has not earned.

It separates uncertain interpretation from governed consequence, preserves why state changed, and treats correction, isolation, and forgetting as first-class architectural responsibilities rather than cleanup work.

> **Agentic memory is retained state that can alter an agent's future interpretation, reasoning, planning, tool use, action, or adaptation across a meaningful persistence boundary.**

## The architecture in one view

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/agent-memory-flow.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/agent-memory-flow-light.svg">
    <img src="https://raw.githubusercontent.com/MythologIQ-Labs-LLC/agent-memory/main/assets/agent-memory-flow-light.svg" alt="Agent Memory governed memory loop showing interpretation, evidence and proposal, PAMA governance, permitted action selection, retained memory, governed recall, and active agent context" width="100%">
  </picture>
</p>

The loop is intentionally split into responsibilities that many memory systems blur together:

1. **Interpret.** Experience becomes evidence, provenance, uncertainty, and a proposal.
2. **Govern.** PAMA resolves what consequences are permitted under current policy, scope, authority, and state.
3. **Commit.** A permitted consequence becomes explicit retained state with reconstructable evidence.
4. **Recall.** Retrieval creates candidates; governance decides what may enter active context.
5. **Revise or forget.** Correction, supersession, staleness, deletion, and residual derived state remain distinct and auditable.

The governing idea is compact:

> **Probabilistic epistemics. Governed consequences.**  
> **Uncertainty may propose. Authority constrains.**

## Start with what you need

- **New to Agent Memory?** Start with **[Getting Started](Getting-Started)**, then **[Core Concepts](Core-Concepts)** for the vocabulary and invariants the architecture preserves.
- **Want the architecture in pictures?** Open **[Decision Flows and Memory Lifecycle](Decision-Flows-and-Memory-Lifecycle)** for lifecycle, PAMA, recall, correction, deletion, isolation, and evidence flows.
- **Implementing a memory system?** Use the **[Implementation Guide](Implementation-Guide)**, then move into **[PAMA](PAMA)**, **[Lifecycle and Forgetting](Lifecycle-and-Forgetting)**, and **[Canonical and Derived State](Canonical-and-Derived-State)** as needed.
- **Reviewing security or isolation?** Start with **[Security and Privacy](Security-and-Privacy)** for scope, tenancy, isolation domains, sensitivity, leakage, and deletion boundaries.
- **Checking what is actually proven?** Read **[Conformance and Evidence](Conformance-and-Evidence)** first, then **[Runtime Evidence](Runtime-Evidence)** for what has actually executed.
- **Researching the foundations or influences?** Use **[Research and Sources](Research-and-Sources)** and **[Aligned Projects & Intellectual Lineage](Aligned-Projects-and-Intellectual-Lineage)**.

## Why retrieval alone is not enough

A retrieval system can answer **what looks relevant**. A governed memory architecture must also answer:

- Should this state have been retained at all?
- Is it still current, merely historically true, disputed, or superseded?
- Does it belong to this user, task, project, tenant, or shared domain?
- Is the source trustworthy in this scope?
- May the memory enter the current context?
- May an agent change durable or shared state because of it?
- Can the resulting consequence be reconstructed later?
- Can the memory be corrected without destroying history?
- Can a deletion request reach summaries, indexes, caches, graph edges, and other derived state?

That is the boundary Agent Memory is designed to make explicit.

## The separations that matter

The architecture resists convenient equivalences that become expensive failure modes later:

```text
identity       != truth
confidence     != authority
saturation     != truth
relevance      != permission
retrieval      != recall admission
proposal       != commit
same agent     != same memory scope
staleness      != falsity
supersession   != correction
delete action  != forgetting completeness
```

These are not slogans pasted over a storage layer. They determine where evidence, policy, scope, lifecycle, and authority must remain independently inspectable.

## Four jobs that should not collapse into one score

**Epistemics** estimates uncertain properties such as relevance, trust, contradiction, sensitivity, utility, and staleness.

**Governance** determines which consequences are allowed under current authority, policy, scope, and state.

**Commit** applies an explicit state transition and emits evidence sufficient to reconstruct why it happened.

**Recall** admits retained state into active context only when relevance and authorization both permit it.

A model may be highly confident and still be wrong. A memory may be highly reinforced and still be unauthorized. A retrieval result may be highly relevant and still belong to another scope. Agent Memory keeps those possibilities representable instead of averaging them into reassurance.

## Current maturity

Agent Memory separates doctrine maturity from implementation evidence so that one cannot impersonate the other.

| Area | Current state |
|---|---|
| **Canonical doctrine** | ADR-001 through ADR-020 and ADR-022 are **Accepted**. |
| **Portable governance evidence** | ADR-021 remains **Proposed** and independently maturity-gated. |
| **Runtime evidence** | Executable reference paths cover governed mutation, stochastic containment, deletion completeness, concurrency conflict handling, portable evidence correlation, adversarial comparator behavior, and systems characterization. |
| **ADR-020 evidence gate** | Satisfied through the repository's executable P10 acceptance audit. |
| **Reference implementation** | A narrow evidence vehicle, not a claim of universal production readiness or higher cumulative conformance. |
| **Conformance claims** | Governed separately from individual evidence slices. Passing a runtime experiment does not automatically raise a cumulative conformance level. |

See **[Architecture Decisions](Architecture-Decisions)** for doctrine status and **[Runtime Evidence](Runtime-Evidence)** for the executable evidence ledger.

## Explore the architecture

- **[PAMA](PAMA)** for proportional mutation authority and consequence governance
- **[Lifecycle and Forgetting](Lifecycle-and-Forgetting)** for strengthening, correction, dispute, pruning, and forgetting
- **[Canonical and Derived State](Canonical-and-Derived-State)** for staleness, deletion propagation, residue, and rebuild authority
- **[Governed Uncertainty](Governed-Uncertainty)** for deterministic boundaries around probabilistic discovery
- **[Security and Privacy](Security-and-Privacy)** for isolation domains, scope, tenancy, sensitivity, and leakage risks
- **[Decision Flows and Memory Lifecycle](Decision-Flows-and-Memory-Lifecycle)** for the complete visual architecture set
- **[Glossary](Glossary)** when two familiar words turn out to mean inconveniently different things

## Canonical source and contribution path

The Wiki is the reader-facing navigation and explanation layer. Canonical doctrine, schemas, fixtures, evidence, and ADR status live in the repository itself.

- **Canonical repository:** https://github.com/MythologIQ-Labs-LLC/agent-memory
- **Documentation index:** https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/README.md
- **Architecture decisions:** https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/main/docs/adr
- **Runtime evidence program:** https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/main/docs/programs/runtime-evidence
- **Contributing:** **[Contributing](Contributing)**

If a Wiki summary and a canonical repository source ever disagree, the canonical source wins. The useful response is to fix the Wiki, not to hold a committee meeting between two Markdown files.
