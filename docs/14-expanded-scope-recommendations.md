# Expanded Scope Recommendations

## Purpose

This document records recommended expansion areas beyond the originally stated scope.

The goal is not to absorb every adjacent idea into Agent Memory. That would recreate the same conceptual sprawl this repo exists to prevent. The goal is to decide which adjacent ideas deserve first-class component treatment, which should remain integrations, and which should stay outside the architecture until they prove necessity.

## Recommendation summary

| Recommendation | Placement | Priority | Rationale |
|---|---|---|---|
| Source trust and reputation | Component candidate | High | Memory depends on evidence quality over time |
| Conflict resolution engine | Component candidate | High | Disputes need deterministic handling beyond simple flags |
| Temporal causality model | Component candidate | High | Memory changes over time and needs causal explanation |
| Privacy and sensitivity classifier | Component candidate | High | Memory systems must classify what can be stored, recalled, or shared |
| Memory economics and budget policy | Component candidate | Medium | Agents need cost-aware retention and context assembly |
| Human correction UX contract | Product plus component | Medium | Durable memory needs user-facing correction pathways |
| Ontology and schema registry | Component candidate | Medium | Shared memory objects need stable schemas and type evolution |
| Query planner and recall strategy | Component candidate | Medium | Retrieval needs policy-aware planning, not raw similarity |
| Multi-agent shared memory protocol | Future subsystem | Medium | Team and org memory require ownership and scope controls |
| Memory threat model | Conformance plus governance | High | Memory poisoning, access-spam, and unauthorized mutation require explicit treatment |
| Policy-as-memory | Doctrine concern | Medium | Policies are durable memory but need stronger authority rules |
| Memory compiler | Future subsystem | Low | Useful later for compiling docs, graphs, traces, and decisions into memory units |
| Interoperability profile | Future standard | Medium | Needed if multiple implementations claim doctrine conformance |
| Domain-specific memory packs | Integration pattern | Low | Should not enter core doctrine unless cross-domain behavior emerges |

## Add now

These should be added to the architecture soon because they are foundational and affect multiple components.

### 1. Source trust and reputation

Memory quality depends on source quality.

The current architecture captures evidence and provenance, but it does not yet define how source reliability changes over time.

Recommended component:

```text
Source Trust and Reputation Layer
```

Responsibilities:

- track source reliability
- weight evidence by source class
- decay or demote sources that produce contradictions
- distinguish authoritative, observed, inferred, synthetic, user-provided, and agent-generated sources
- prevent a noisy source from dominating saturation

Failure modes:

- high-volume low-quality source inflates memory
- stale source remains trusted
- agent-generated memory recursively cites itself
- single-source claims become durable without corroboration

### 2. Conflict resolution engine

Dispute state is necessary but not sufficient.

The system needs a deterministic way to resolve conflicts between memories, sources, policies, and time windows.

Recommended component:

```text
Conflict Resolution Engine
```

Responsibilities:

- rank conflicting evidence
- classify conflict type
- select correction, split-scope, demotion, or escalation
- preserve minority or historical claims when relevant
- prevent silent overwrite

Conflict types:

- factual contradiction
- temporal supersession
- scope mismatch
- policy conflict
- source reliability conflict
- user correction conflict
- implementation drift

### 3. Temporal causality model

Memory systems need to know not only what changed, but why it changed.

Recommended component:

```text
Temporal Causality Layer
```

Responsibilities:

- represent event order
- link decisions to causes and consequences
- distinguish stale from superseded
- support causal recall
- preserve timeline of correction and drift

This is especially important for decision memory, codebase evolution, organizational memory, and agent self-improvement.

### 4. Privacy and sensitivity classifier

A governed memory system must know which memory can be stored, recalled, exported, summarized, shared, or deleted.

Recommended component:

```text
Privacy and Sensitivity Classifier
```

Responsibilities:

- classify memory sensitivity
- apply retention boundaries
- prevent unsafe context assembly
- enforce local-first and encrypted storage expectations
- distinguish personal, organizational, security, financial, health, credential, and public data

This component should influence PAMA, Vault, context assembly, and conformance fixtures.

### 5. Memory threat model

The doctrine already contains trap classes, but it needs a broader threat model.

Recommended document:

```text
docs/15-memory-threat-model.md
```

Threat classes:

- memory poisoning
- access-spam reinforcement
- hallucination permanence
- recursive self-citation
- source spoofing
- provenance stripping
- unauthorized mutation
- stale policy retention
- cross-user leakage
- overbroad context assembly
- malicious correction
- poisoned code graph evidence

## Add soon

These are valuable but should follow the foundational components.

### 6. Memory economics and budget policy

Agent memory has resource costs.

The architecture should model cost, context budget, storage budget, retrieval budget, and cognitive budget.

Recommended placement:

```text
Context Assembly Surface + Saturation and Decay Engine
```

This should not become a standalone component yet unless cost policy becomes complex enough to need one.

### 7. Ontology and schema registry

The architecture now has schemas, but it does not yet define schema evolution.

Recommended component candidate:

```text
Memory Schema Registry
```

Responsibilities:

- maintain memory-unit types
- version schemas
- define compatibility rules
- support migrations
- prevent implementation-specific fields from corrupting doctrine-level objects

### 8. Query planner and recall strategy

Current memory systems often confuse retrieval with memory.

A query planner would decide how recall should work across identity lookup, graph traversal, evidence search, runtime context, and policy constraints.

Recommended component candidate:

```text
Governed Recall Planner
```

Responsibilities:

- choose recall path
- respect certification state
- avoid disputed canonical use
- compose graph, vector, exact-address, and policy-aware retrieval
- produce recall explanations

### 9. Human correction UX contract

Correction is a doctrine concept, but products need a user-facing contract.

Recommended placement:

```text
Correction and Dispute Surface
```

The architecture should define what users must be able to see and change:

- why a memory exists
- why it was recalled
- what evidence supports it
- whether it is certified
- how to dispute it
- how to correct it
- how correction affects future recall

## Watch closely

These are promising but should not enter the core architecture too soon.

### 10. Multi-agent shared memory protocol

Shared memory across agents, teams, or organizations is important, but risky.

It introduces ownership, identity, consent, tenant boundaries, ACLs, role-based recall, and conflicting authority models.

Recommendation:

Keep as a future subsystem until single-agent and product-local memory boundaries are stable.

### 11. Interoperability profile

If multiple systems claim Agent Memory conformance, the repo will need profiles.

Potential profiles:

- Level 1: identity and provenance
- Level 2: lifecycle and decay
- Level 3: calibrated saturation
- Level 4: PAMA authority
- Level 5: certification and crystallization
- Level 6: cross-system interoperability

Recommendation:

Wait until adapter contracts and implementation ownership map exist.

### 12. Memory compiler

A memory compiler could convert docs, traces, issues, PRs, decisions, code graphs, and chat transcripts into memory units.

This is powerful but dangerous if added too early.

Recommendation:

Do not add as a component yet. Track as a future subsystem after source trust, conflict resolution, and certification are stronger.

## Keep outside core for now

These may integrate later but should not define the doctrine.

### Domain-specific memory packs

Examples:

- software-engineering memory pack
- sales memory pack
- personal productivity memory pack
- mental health support memory pack
- compliance memory pack

Recommendation:

Treat these as integration profiles or products, not core doctrine.

### Agent personality memory

Agent personality continuity may use memory, but it should not drive memory doctrine.

Recommendation:

Keep personality memory as a runtime/product concern unless it intersects identity, consent, correction, or governance.

### Prompt-template libraries

Prompt templates may consume memory but should not define memory.

Recommendation:

Keep outside core.

## Highest-value next additions

The next architecture pass should add:

1. `docs/15-memory-threat-model.md`
2. `docs/16-source-trust-and-reputation.md`
3. `docs/17-conflict-resolution-engine.md`
4. `docs/18-temporal-causality-layer.md`
5. `docs/19-privacy-and-sensitivity-classifier.md`

These five expand scope without losing architecture discipline.

## Strategic recommendation

Do not market this as an agent memory library.

Treat it as a reference architecture for governed agent memory systems.

That lets EvolveAI, CodeGenome, COREFORGE, UOR, FailSafe, Bicameral, and future systems remain separate implementations while still aligning to a common doctrine.

The long-term wedge is not memory recall.

The wedge is governed memory state transition across identity, evidence, lifecycle, authority, certification, and runtime use.
