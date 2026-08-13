# Quality Peers and Useful Projects

Agent Memory should make excellent independent work easier to discover.

This page highlights products, repositories, platforms, specifications, and technical systems that contribute real value to the agent, governance, trust, security, and memory ecosystem. Some directly influence Agent Memory. Some are interoperability targets. Some are comparators. Some simply do something well enough that practitioners should know they exist.

> **Good work should be visible. Credit should be generous. Boundaries should remain precise.**

The canonical recognition policy is [`docs/ecosystem/quality-peer-recognition.md`](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/ecosystem/quality-peer-recognition.md). Intellectual-lineage and licensing details remain in **[Aligned Projects & Intellectual Lineage](Aligned-Projects-and-Intellectual-Lineage)**.

## What recognition means

```text
quality recognition
!= dependency
!= endorsement
!= sponsorship
!= formal partnership
!= conformance
!= architectural authority
```

A project can be excellent without Agent Memory adopting it. An interoperability target can be useful without either project controlling the other. A comparator can expose architectural value without becoming a normative dependency.

## Current highlights

| Project | Why it stands out | Current relationship |
|---|---|---|
| **UOR Foundation / UOR Framework** | Deterministic object reference, exact identity, resolution state, formally described object spaces | quality peer / intellectual lineage |
| **DashClaw** | Serious treatment of pre-execution governance, approvals, enforcement posture, liveness, and evidence | enforcement peer / interoperability target / comparator |
| **Microsoft Agent Governance Toolkit** | Broad open governance surface around policy, identity, audit, and runtime controls | policy/enforcement peer / interoperability target |
| **AgentTrust / TRACE** | Cryptographically bound governance evidence, attestation, verification, and conformance surfaces | evidence/attestation peer / comparator |
| **Open Policy Agent** | Mature general-purpose policy engine with a strong deterministic external-decision surface | validated real policy comparator |
| **Cedar** | Purpose-built authorization model with principal/action/resource/context and permit/forbid semantics | active second policy comparator |
| **Cedarling** | Embedded/local Cedar PDP with identity, policy-store, logging, bindings, OPA and AuthZen deployment surfaces | quality peer / active research candidate |

---

## UOR Foundation / UOR Framework

UOR is particularly useful for thinking precisely about identity. Agent Memory's main architectural takeaway is the distinction between exact object identity and the separate question of what that object is permitted to become or influence as memory.

**Repository:** https://github.com/UOR-Foundation/UOR-Framework

See **[Aligned Projects & Intellectual Lineage](Aligned-Projects-and-Intellectual-Lineage)** for the fuller lineage record.

---

## DashClaw

DashClaw is an independent governance runtime focused on the seam immediately before agent actions execute. Its emphasis on interception, risk/policy decisions, approval, evidence, and enforcement liveness makes it a useful parallel system rather than a competing memory implementation.

**Repository:** https://github.com/ucsandman/DashClaw

The particularly useful architectural lesson is simple:

```text
policy decision
!= approval evidence
!= enforcement point reached
!= action outcome
```

Agent Memory should be able to provide governed context to systems like DashClaw without absorbing their product-specific vocabulary into canonical memory semantics.

---

## Microsoft Agent Governance Toolkit

Microsoft Agent Governance Toolkit is a substantial open-source governance system covering deterministic policy, identity verification, audit, and runtime controls.

**Repository:** https://github.com/microsoft/agent-governance-toolkit

Its strongest value here is as a peer for testing responsibility separation:

```text
memory-specific governance
!= general agent policy
!= runtime enforcement
```

Agent Memory remains the semantic owner of memory lifecycle and PAMA consequences. A broader governance runtime may further constrain execution but should never silently widen a memory consequence Agent Memory denied.

---

## AgentTrust / TRACE

TRACE provides an open specification and tooling ecosystem for cryptographically bound AI-agent governance evidence.

**Repository:** https://github.com/agentrust-io/trace-spec

Current public material describes TRACE v0.2 as a developer-preview specification with a conformance test suite. Trust Records bind facts such as runtime, policy, environment, data class, and tool usage into verifiable evidence.

That is valuable precisely because Agent Memory keeps a strict boundary:

```text
verified identity != memory authority
valid attestation != semantic correctness
runtime evidence != lifecycle satisfaction
```

Agent Memory already uses a pinned TRACE package as a bounded evidence comparator.

---

## Open Policy Agent

OPA is a mature general-purpose policy engine and a strong example of policy-as-code that does not need to become Agent Memory's policy model in order to be useful.

**Repository:** https://github.com/open-policy-agent/opa

Agent Memory has executed its generic monotonic external-policy contract against pinned OPA v1.19.0. The surviving rule is:

```text
Agent Memory allow + OPA deny -> deny
Agent Memory deny + OPA allow -> still deny
policy result -> not execution evidence
```

That makes OPA both a useful product in its own right and a validated architectural comparator.

---

## Cedar

Cedar is a purpose-built authorization language and engine centered on explicit principal, action, resource, context, permit, and forbid semantics.

**Repository:** https://github.com/cedar-policy/cedar

Agent Memory is currently proving the same generic external-policy seam against Cedar v4.12.0 as the required second deterministic policy host after OPA.

Cedar is especially valuable for this test because its authorization result is structurally different from OPA. The adapter must bind the result to the exact request and policy artifact rather than relying on an arbitrary result object that echoes Agent Memory metadata.

Until issue #216 completes, Cedar is an active comparator target rather than a validated Agent Memory integration.

---

## Cedarling

Cedarling is maintained inside the Janssen Project and builds a practical local authorization layer around Cedar.

**Repository:** https://github.com/JanssenProject/jans/tree/main/jans-cedarling

Current source describes a high-performance local authorization service powered by Cedar and exposes a Rust core plus multiple bindings and deployment surfaces. Particularly useful capabilities include:

- embedded/local policy decision;
- policy-store/bootstrap configuration;
- JWT and multi-issuer authorization;
- decision logging;
- Python, Go, WASM, C/UniFFI and other bindings;
- sidecar/gateway-oriented integration patterns;
- an OPA plugin that performs Cedar-based authorization in OPA workflows;
- AuthZen access-evaluation endpoints through that OPA/Cedarling integration.

That last point is unusually interesting for Agent Memory. OPA is already a validated comparator, Cedar is the active second policy host, and Cedarling provides an independent bridge between the two policy ecosystems.

Current Janssen `main` declares Cedarling against `cedar-policy = 4.11.2`. Agent Memory's direct Cedar comparator targets v4.12.0. Those are separate evidence lines and should remain visibly separate.

Issue #217 is evaluating Cedarling as an embedded policy, identity, and deployment peer. It is **not** an adopted Agent Memory dependency.

---

## How projects earn a place here

A project should be highlighted only when current primary evidence supports a real reason:

1. it is unusually useful or technically strong for practitioners;
2. it materially shaped an Agent Memory distinction;
3. it has served as a real comparator or reference substrate;
4. it exposes a useful interoperability, policy, enforcement, evidence, identity, observability, framework, or security boundary;
5. it contributed a falsifiable challenge that improved the architecture.

This is intentionally not an exhaustive software directory. There are already enough lists on the internet whose primary qualification is that somebody remembered a URL.

Entries should evolve as projects evolve. Strong work can earn greater prominence. Stale or materially changed projects can be reclassified. Recognition follows evidence.

## Source rights and independence

The default pattern is link + attribution + independent synthesis. Agent Memory does not copy logos, screenshots, code, diagrams, schemas, or marketing assets merely to make recognition look official.

See **[Aligned Projects & Intellectual Lineage](Aligned-Projects-and-Intellectual-Lineage)** and the canonical [Source Rights and Reuse Policy](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/SOURCE_RIGHTS_POLICY.md).
