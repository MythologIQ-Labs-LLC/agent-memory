# ADR-034: Procedural Memory Is Retained State, Not Execution Authority

## Status

Proposed

## Context

Agent Memory doctrine already states:

```text
memory is not procedure
procedure is not permission
permission is not governance
```

The external memory frontier now makes this boundary operationally urgent.

Modern agent-memory systems increasingly retain reusable procedures, strategies, playbooks, tool-use routines, and “skills” as memory. MemOS, MIRIX, Letta, Acontext, and research on execution-oriented/procedural memory all expose forms of retained know-how that can materially change later agent behavior.

Some skill formats are human-readable Markdown. Others include scripts/resources, learned policies, condensed experience, or routing triggers. The substrate is not the stable architectural question.

The stable question is whether storing or recalling a procedure silently grants the agent authority to activate or execute it.

It must not.

A second frontier has also emerged: systems such as MemSkill and EvolveMem learn **how the memory system itself should remember**, including extraction, consolidation, retrieval, ranking, and forgetting strategies. These “metamemory” procedures are even more consequential because they alter future memory formation and recall.

Existing doctrine covers pieces of this problem:

- ADR-020 separates uncertain/learned proposals from governed consequences;
- ADR-022 governs cross-scope memory movement;
- ADR-025 (Proposed) addresses explicit authority for durable decision overwrite;
- ADR-027 (Proposed) addresses governed re-admission of rejected values;
- ADR-032 governs structural adaptation and forbids probabilistic self-authorization;
- ADR-033 establishes capability-oriented composition and deterministic routing floors;
- PAMA separates memory target class, operation, downstream authority, risk, and review requirements.

The missing doctrine is the lifecycle and authority boundary for retained **procedural/skill memory** itself.

## Decision candidate

Agent Memory SHOULD treat procedural/skill memory as governed retained state with a separate activation and execution boundary.

> **A remembered procedure may influence a plan. It does not, by being remembered, grant permission to perform the procedure's actions.**

The architecture separates at least:

```text
skill retention
  store/version/scope/provenance the procedure

skill retrieval
  produce the procedure as a memory candidate

skill admission / activation
  permit the procedure to influence the current plan/context

skill execution
  perform tools/actions described by the procedure under Runtime/Governance authority
```

No earlier stage implies the later stage.

## Procedural memory unit

A procedural-memory implementation MAY use Markdown, structured JSON, files, database records, code bundles, learned policies, or another representation.

At the Agent Memory semantic boundary, a durable procedural memory SHOULD be able to represent or derive at least:

```text
logical procedure identity
version / currentness
scope / isolation domain
purpose / applicability or trigger conditions
procedure content/reference
provenance/source episodes or authored source
validation/evaluation evidence where available
known constraints / hazards / prerequisites
supersession/correction lineage
sensitivity
activation posture
content/reference integrity
```

Exact field names are an implementation/schema question, not fixed by this ADR.

## Promotion into procedural memory

A procedure may originate from:

- explicit human instruction;
- imported project/user documentation;
- repeated successful agent experience;
- consolidation/synthesis over episodes;
- external skill catalogs;
- another governed memory domain;
- learned skill-generation systems.

Origin establishes provenance, not authority.

Promotion from episodic experience into durable procedural memory is a consequential memory mutation and must pass the normal PAMA/currentness/scope path.

A model's confidence that a procedure is useful does not authorize durable promotion.

## Activation/admission

Procedural recall produces a **candidate skill/procedure**.

Before the procedure may influence the active plan/context, Agent Memory must apply governed recall/admission constraints including as applicable:

- currentness and supersession;
- scope/isolation;
- purpose/applicability;
- sensitivity;
- rejection/readmission state;
- material validation status;
- required authority ceilings;
- source/provenance availability;
- consumer/runtime compatibility.

A high similarity score, trigger match, graph reachability, or learned router choice does not bypass admission.

## Execution remains outside memory authority

Once admitted, a procedural memory may recommend or shape Runtime behavior.

The Runtime and/or Agent Governance system remains responsible for actual action/tool execution authority.

```text
Agent Memory
  recalls/admit procedure
        |
        v
Agent Runtime
  forms plan / proposes action
        |
        v
Agent Governance where applicable
  permits / reviews / blocks action
        |
        v
execution
```

A stored skill containing a shell command, HTTP call, repository mutation, payment step, deployment procedure, or destructive operation does not inherit authority merely because the skill was previously approved for another case.

## Correction and supersession

Procedural memories are versioned knowledge, not immortal scripts.

When a procedure changes:

```text
old current procedure
  -> correction/successor proposal
  -> governance/currentness evaluation
  -> new current procedure
  -> old procedure retained as superseded history where required
```

Superseded procedures MUST NOT be admitted as current merely because a retrieval component ranks them highly.

Historical procedures may remain queryable for reconstruction, incident analysis, or rollback evidence without being current guidance.

## Cross-scope transfer

A useful skill in one project, tenant, environment, or toolchain does not automatically transfer to another.

Cross-scope procedural reuse is a governed boundary crossing under ADR-022.

Transfer may require:

- re-scoping;
- compatibility validation;
- removal/generalization of environment-specific assumptions;
- renewed authority/approval;
- new validation evidence.

The same procedure text in two domains does not imply the same applicability or authority.

## Procedure plus executable artifacts

Some skill systems package instructions with executable scripts/resources.

Agent Memory may retain and retrieve such artifacts as `resource_artifact_memory` associated with `procedural_skill_memory`.

However:

```text
artifact retained
  != artifact trusted
  != artifact executable
  != execution authorized
```

Integrity, provenance, malware/supply-chain checks, runtime sandboxing, and action governance remain separate controls.

## Metamemory is a stricter sub-class

A procedure about performing a user task is ordinary procedural memory.

A procedure about **how Agent Memory itself should form, consolidate, route, retrieve, rank, prune, archive, or forget memory** is a `metamemory_policy` capability.

Metamemory has a higher consequence surface because recalling/applying it changes future memory-system behavior.

The safe path is:

```text
learned metamemory insight
  -> versioned proposed memory-management/profile change
  -> deterministic compatibility + regression analysis
  -> PAMA / ADR-032 structural or policy classification
  -> bounded authorized commit OR explicit human decision
```

A recalled metamemory skill MUST NOT silently modify the active memory profile.

This ADR does not create a separate metamemory authority system. Existing PAMA, ADR-020, ADR-032, configuration compatibility, and normal human-authority boundaries remain controlling.

## Learned and self-evolving skills

Systems may learn skills from successful episodes, hard cases, failure logs, or benchmark feedback.

Agent Memory permits probabilistic/learned systems to:

- propose new procedural memories;
- propose refinements;
- estimate expected utility;
- identify applicability triggers;
- recommend retirement;
- propose metamemory/profile changes.

They do not self-authorize:

- durable promotion;
- cross-scope transfer;
- semantic correction;
- deletion/retirement;
- active profile mutation;
- action execution.

For self-evolving retrieval or metamemory changes, regression evidence and rollback boundaries SHOULD be first-class inputs to the governance decision.

## Evaluation evidence

Procedural memory quality is not adequately measured by retrieval accuracy alone.

A capability profile SHOULD be able to bind a skill/procedure to evidence such as:

- source episodes;
- successful/failed applications;
- environment/tool versions;
- tests or validation runs;
- negative cases;
- last validation time;
- known constraints;
- observed outcome metrics.

This evidence informs currentness and applicability. It does not become standing execution permission.

## First implementation profile

The reference implementation SHOULD deliberately use a simple, inspectable representation before adopting a specialized skill database.

A suitable v0 profile is:

```text
human-readable Markdown/structured skill artifact
  + Agent Memory logical identity/provenance/scope/currentness
  + governed promotion
  + governed recall/admission
  + explicit activation evidence
  + separate Runtime/Governance execution
```

The first proof should not require embeddings, GraphRAG, a learned skill model, or a new first-party repository.

Those capabilities can be composed later without changing the behavioral contract.

## Required acceptance evidence before doctrine promotion

This ADR intentionally remains Proposed until the first vertical slice demonstrates at least:

1. an episodic or human-authored procedure can be proposed without immediate mutation;
2. governed promotion creates durable procedural memory with provenance/scope;
3. a later session retrieves and admits the current procedure;
4. the admitted procedure changes the plan without automatically executing actions;
5. execution still traverses the normal Runtime/Governance boundary;
6. correction creates a superseding procedure and the old procedure is no longer admitted as current;
7. stale procedure/approval replay cannot restore an old procedure as current;
8. cross-project/tenant procedure admission is blocked without governed crossing;
9. deletion/revocation makes derived/index/cache copies non-influential or reports incomplete residue honestly;
10. an attempted metamemory/profile change cannot self-authorize through ordinary skill recall;
11. decision, activation/admission, and execution evidence remain distinct.

## Consequences

### Positive

- makes a major emerging agent-memory capability first-class without giving memory execution authority;
- creates a clean bridge between experience and reusable agent competence;
- supports human-readable, external, learned, or first-party skill stores behind one semantic contract;
- provides a concrete workload for ADR-033 component/capability composition;
- gives metamemory evolution a safe home under existing governance rather than inventing a parallel authority model;
- enables EvolveAI lifecycle and CodeGenome provenance to compose later.

### Negative

- a “skill” requires more lifecycle/evidence than a convenient prompt snippet;
- runtime integrations must preserve an extra activation boundary;
- existing external skill stores may need adapters to express Agent Memory scope/currentness/provenance;
- self-evolving memory systems cannot directly apply every learned optimization.

## Alternatives considered

### Treat skills as ordinary facts

Rejected. Procedures have applicability, activation, validation, and execution consequences that facts do not.

### Treat a recalled skill as already authorized execution

Rejected. This collapses memory, procedure, permission, and governance into one artifact and creates standing-authority replay risk.

### Make one skill format canonical

Rejected. External systems successfully use Markdown, files, structured records, scripts/resources, and learned policies. The representation should remain a capability/profile decision.

### Put procedural memory entirely in Agent Runtime

Rejected. Durable cross-session procedure identity, provenance, scope, correction, supersession, deletion, and recall are memory responsibilities even though execution is not.

### Create a new proprietary skill-memory repository immediately

Rejected for the first slice. Current evidence shows the semantics can be proven with simple artifacts. A new subsystem should be created only if later conformance evidence demonstrates a substrate/capability gap that EvolveAI, CodeGenome, files, ordinary stores, or external adapters cannot satisfy cleanly.

## Relationship to other ADRs

- ADR-020 governs learned/probabilistic skill discovery and proposal.
- ADR-022 governs skill scope and cross-domain transfer.
- ADR-023, if accepted, strengthens correction-as-supersession behavior.
- ADR-025, if accepted, applies when a procedural memory carries durable decision-like authority consequences.
- ADR-027, if accepted, applies to rejected/unsafe procedures that attempt re-entry.
- ADR-028 preserves representation/language portability.
- ADR-030 applies when a derived projection of procedural memory feeds authorization/temporal consumers.
- ADR-032 governs metamemory/structural mutation.
- ADR-033 governs capability declaration, maturity, and deterministic component composition.

This ADR adds no exception to PAMA or existing authority rules.
