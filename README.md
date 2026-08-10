# Agent Memory

### An interdisciplinary reference architecture for how intelligent systems encode, retain, consolidate, retrieve, revise, forget, and inherit information.

Agent Memory is a doctrine, architecture, research map, and conformance framework for **governed agentic memory systems**.

It connects ideas from biological and cognitive memory with practical agent engineering while keeping the boundary between inspiration and implementation explicit. It covers short-term and long-term memory, episodic and semantic memory, procedural and prospective memory, consolidation, forgetting, inherited and collective memory, provenance, trust, mutation authority, privacy, security, evaluation, and the uncomfortable fact that remembering everything is usually a design failure wearing a storage bill.

> **Core thesis:** Agentic memory is not retrieval. It is governed state transition over retained information that can alter future agent behavior.

---

## Why this repository exists

Most "AI memory" systems begin with one question:

> How do we retrieve old context?

That is necessary, but much too small.

A serious memory architecture must also ask:

- What deserves to be encoded at all?
- What should remain only in working memory?
- What crosses a session boundary?
- What becomes durable?
- What should be generalized from repeated experience?
- What should remain an exact episodic record?
- How does a procedure differ from a fact?
- How does an agent remember a future obligation?
- When does old information become stale rather than false?
- What happens when two memories conflict?
- What can the agent revise by itself?
- What requires verification or human authority?
- What should be forgotten?
- How does deletion propagate into summaries, graphs, indexes, and caches?
- What knowledge may be inherited by a successor agent?
- How is inherited knowledge distinguished from direct experience?
- How do we know memory improves action rather than merely recall scores?

This repository exists to make those questions architectural rather than accidental.

---

## What Agent Memory is

Agent Memory is a **reference architecture**, not a single memory library.

It consolidates memory-system logic distributed across UOR, EvolveAI, CodeGenome, COREFORGE Vault / Neurospace, PAMA, FailSafe / Arbiter, Bicameral, and related governance work into shared doctrine and testable contracts.

It now also provides an interdisciplinary framework spanning:

```text
biological memory
      |
cognitive memory
      |
individual agent memory
      |
shared / institutional memory
      |
inherited / evolutionary-scale memory
```

The goal is not to pretend those systems are equivalent.

The goal is to identify reusable **functions, constraints, tradeoffs, and failure modes** without importing biological metaphors as fake implementation facts.

---

## The seven functions of memory

A mature memory system must do more than store and search.

```text
             ┌──────────┐
             │  ENCODE  │
             └────┬─────┘
                  │
                  v
             ┌──────────┐
             │  RETAIN  │
             └────┬─────┘
                  │
                  v
          ┌───────────────┐
          │  CONSOLIDATE  │
          └───────┬───────┘
                  │
                  v
            ┌────────────┐
            │  RETRIEVE  │
            └─────┬──────┘
                  │
          ┌───────┴────────┐
          v                v
     ┌─────────┐      ┌─────────┐
     │ REVISE  │      │ FORGET  │
     └────┬────┘      └────┬────┘
          │                │
          └───────┬────────┘
                  v
             ┌─────────┐
             │ INHERIT │
             └─────────┘
```

### Encode

Turn observations, actions, outcomes, decisions, corrections, and evidence into candidate memory.

### Retain

Preserve selected state across the boundary where it becomes useful.

### Consolidate

Transform experience into more durable or reusable representations such as facts, summaries, procedures, models, or abstractions.

### Retrieve

Select retained information appropriate to the current task, time, scope, and authority boundary.

### Revise

Correct, refine, supersede, dispute, reconcile, or split memory when reality changes or new evidence arrives.

### Forget

Decay, suppress, archive, delete, abstract, or otherwise reduce memory influence according to policy.

### Inherit

Allow a new agent, process, team, or generation to begin with retained information it did not personally experience.

---

## Memory across scales

Memory appears in many substrates, and the word means different things in each.

| Scale | What persists | Example |
|---|---|---|
| Neural / cognitive | activity, plasticity, distributed representations | working, episodic, semantic, procedural memory |
| Cellular | altered future response | transcriptional or epigenetic memory |
| Immune | altered response to later exposure | adaptive and trained immune memory |
| Individual agent | retained state across reasoning or session boundaries | preferences, episodes, procedures, corrections |
| Multi-agent / institutional | shared state beyond one actor | policies, runbooks, repositories, ledgers |
| Inherited / evolutionary | information survives the originating individual/process | genes, inherited priors, model weights, seed doctrine |

**Important:** this table describes functional parallels, not substrate equivalence.

An embedding index is not a hippocampus. A system prompt is not a genome. A cache eviction policy is not human forgetting. The comparison becomes useful only after the poetry is removed.

See [`docs/20-memory-foundations-across-scales.md`](docs/20-memory-foundations-across-scales.md).

---

## Memory horizons

"Short-term" and "long-term" are incomplete specifications. The meaningful question is: **which persistence boundary does the memory cross?**

| Horizon | Agentic meaning | Typical examples |
|---|---|---|
| Immediate | current inference step | intermediate tool output |
| Working | active reasoning context | scratch state, current plan |
| Session | current task or conversation | local entities, temporary decisions |
| Episodic | survives prior sessions | interaction or trajectory records |
| Long-term | durable reusable state | preferences, facts, procedures |
| Remote | deeply consolidated and rarely changing | mature policies, stable domain knowledge |
| Inherited | predates current agent experience | model priors, organization rules, runbooks |

Persistence horizon and memory type are separate dimensions.

A procedural memory can be session-local or remote. A semantic fact can be provisional or certified. An episodic record can be permanent evidence even when it is rarely retrieved.

---

## Memory types

The canonical taxonomy includes more than facts and chat history.

| Memory type | Question it answers | Agent examples |
|---|---|---|
| Observation | What did I perceive? | message, page state, sensor input |
| Episodic | What happened, when, and in what context? | interaction, task trajectory, incident |
| Semantic | What is generally true? | facts, concepts, entity knowledge |
| Procedural | How do I do this? | runbook, tool sequence, recovery workflow |
| Prospective | What must happen later? | follow-up, deadline, deferred obligation |
| Preference | What does this actor prefer? | output style, product choice |
| Relationship | How are entities connected? | ownership, dependencies, trust |
| Policy | What is authoritative or prohibited? | retention, approval, access rules |
| Failure | What failed and why? | environment gotcha, known bad path |
| Correction | What changed because earlier memory was wrong? | user correction, revised fact |
| Decision | What was chosen and why? | architecture decision, approval |
| Evidence | What supports another memory or claim? | logs, artifacts, source records |
| Model | What compact representation predicts the environment? | topology, causal graph, workflow model |

See [`docs/22-agentic-memory-theory-and-development.md`](docs/22-agentic-memory-theory-and-development.md).

---

## Forgetting is a feature

The architecture treats forgetting as a first-class capability.

Forgetting may mean:

- passive decay
- retrieval suppression
- interference control
- pruning
- archival
- compression
- semanticization
- supersession
- scope restriction
- deletion
- cryptographic erasure
- tombstoning
- specialized model unlearning

Those are not interchangeable operations.

A memory system needs to know whether it intends to:

```text
make something harder to recall
make something unavailable to normal recall
preserve it only as history
replace details with abstraction
remove active copies
remove derived copies
or make recovery intentionally impossible
```

Forgetting matters because memory creates costs and risks:

- stale beliefs
- interference
- context pollution
- privacy exposure
- poisoning persistence
- storage and retrieval cost
- outdated policy influence
- contradictory state

A memory architecture with no forgetting policy eventually becomes a historical landfill with semantic search.

See [`docs/21-forgetting-consolidation-and-memory-metabolism.md`](docs/21-forgetting-consolidation-and-memory-metabolism.md).

---

## The canonical governed-memory pipeline

```text
Raw experience / artifact
        |
        v
┌──────────────────────────────┐
│ Identity / exact reference   │
│ What is this object?         │
└──────────────┬───────────────┘
               v
┌──────────────────────────────┐
│ Evidence + provenance        │
│ Why should we believe it?    │
└──────────────┬───────────────┘
               v
┌──────────────────────────────┐
│ Admission + classification   │
│ Should it become memory?     │
└──────────────┬───────────────┘
               v
┌──────────────────────────────┐
│ Saturation / lifecycle       │
│ Persist, decay, verify?      │
└──────────────┬───────────────┘
               v
┌──────────────────────────────┐
│ PAMA / mutation authority    │
│ Is this transition allowed?  │
└──────────────┬───────────────┘
               v
┌──────────────────────────────┐
│ Certification / promotion    │
│ Can it become durable?       │
└──────────────┬───────────────┘
               v
┌──────────────────────────────┐
│ Runtime memory space         │
│ How may agents use it?       │
└──────────────┬───────────────┘
               v
┌──────────────────────────────┐
│ Governed recall planner      │
│ Should it enter context now? │
└──────────────┬───────────────┘
               v
            Agent action
```

Memory is governed on both the **write path** and the **read path**.

That distinction matters because persistent memory can become a durable control channel. A semantically relevant memory can still be stale, malicious, cross-tenant, superseded, over-sensitive, or inappropriate to the current task.

---

## The canonical architecture

Agent Memory is one architecture composed of bounded responsibilities.

| Layer / component | Responsibility |
|---|---|
| Identity substrate | stable object identity and exact addressability |
| Evidence and provenance | source support, witness material, origin |
| Source trust | reliability of sources over time |
| Admission | decide whether observations may become memory |
| Saturation and decay | persistence pressure and lifecycle routing |
| Lifecycle engine | explicit state transitions |
| Conflict resolution | contradiction, supersession, scope mismatch |
| Temporal causality | what changed, when, and why |
| Governance / PAMA | mutation, promotion, pruning, and sharing authority |
| Privacy and sensitivity | what may be stored, recalled, shared, retained, or deleted |
| Certification | durable transition confirmation |
| Runtime memory space | operational memory used by agents |
| Recall planner | exact, semantic, temporal, graph, and procedural recall |
| Context assembly | bounded memory supplied to active reasoning |
| Correction and dispute | safe revision and reconciliation |
| Observability and audit | explain memory creation, mutation, recall, deletion |
| Conformance harness | fixtures, calibration, traps, and metrics |

### Existing implementation mapping

| System | Role in the doctrine |
|---|---|
| UOR Framework | identity substrate and deterministic addressability |
| EvolveAI | memory metabolism and lifecycle prototype |
| CodeGenome | code-reality graph, confidence, evidence, provenance |
| COREFORGE Vault / Neurospace | local-first runtime memory surface |
| PAMA | proportional mutation and promotion authority |
| FailSafe / Arbiter | governance enforcement and approval boundaries |
| Bicameral | decision continuity, evidence, and drift detection |

---

## Governing invariants

These are architectural rules, not implementation suggestions.

1. **Identity is not memory.**
2. **Retrieval is not memory.**
3. **Relevance is not truth.**
4. **Saturation is not truth.**
5. **Repetition is not durability.**
6. **Reflection is not evidence.**
7. **High confidence is not permission to become permanent.**
8. **Runtime usefulness is not canonical authority.**
9. **Newer is not automatically more authoritative.**
10. **Old is not automatically false.**
11. **A memory that cannot be disputed cannot be trusted.**
12. **A durable mutation must be explainable.**
13. **Provenance must survive summarization and consolidation.**
14. **Sensitive memory remains governed at recall time, not only write time.**
15. **Forgetting is a governed transition.**
16. **Deletion must account for derived state.**
17. **Inherited memory must not masquerade as direct observation.**
18. **Memory quality must be evaluated by behavior, not recall alone.**

---

## The signals that must remain separate

A recurring design failure is compressing many dimensions into one score.

Agent Memory keeps these distinct:

| Signal | Meaning | Does not mean |
|---|---|---|
| Identity | exact object/reference resolution | truth or usefulness |
| Confidence | evidence support for content | permanence |
| Source trust | expected source reliability | current relevance |
| Relevance | usefulness to current task | correctness |
| Saturation | persistence/lifecycle pressure | truth |
| Authority | permission to perform transition | evidence quality |
| Certification | required confirmation passed | immutability |
| Sensitivity | privacy/security classification | low utility |
| Scope | where memory is valid or visible | global truth |
| Contradiction | conflict with other retained state | which side is wrong |

A single universal "memory score" is convenient in the same way one giant permissions role called `admin-ish` is convenient.

---

## Lifecycle state machine

A durable memory should have an explainable history.

```text
Transient
   |
Observed
   |
Linked
   |
Reinforced
   |
Candidate
   |
Pending Verification
   |
Crystallized
   |
Operationally Reused
   |
   +-----------> Stale
   |                |
   |                v
   +-----------> Disputed
                    |
                    v
                 Corrected
                    |
                    v
                 Reconciled
                    |
              ┌─────┴─────┐
              v           v
           Archived     Pruned
```

Not every memory traverses every state.

The requirement is that consequential transitions be explicit, authorized, and auditable.

---

## Crystallization

Crystallization is the transition from provisional memory into durable, strongly trusted memory within a defined scope.

A canonical promotion gate may look like:

```text
identity_resolved == true
provenance_present == true
source_trust >= required_floor
saturation >= calibrated_candidate_threshold
trap_class_check == pass
contradiction_state == acceptable
pama_authority == allow
certification_gate == pass
```

A score may nominate memory for promotion.

A score must not silently grant permanence unless an explicit policy accepts that risk.

---

## Memory consolidation

Consolidation is not "move row from short-term table to long-term table."

A system may transform retained experience:

```text
raw episodes
   |
   +--> semantic facts
   +--> generalized patterns
   +--> procedures / runbooks
   +--> failure guardrails
   +--> entity or world models
   +--> compact summaries
```

Derived memory should preserve links back to supporting evidence.

This lets the runtime use compact abstractions without sacrificing auditability and correction.

---

## Prospective memory

Agents need to remember the future as well as the past.

Prospective memory represents:

- commitments
- deadlines
- pending reviews
- follow-ups
- conditions to recheck
- deferred decisions
- unresolved dependencies

This is memory of an obligation or intended action.

It is not necessarily the scheduler that executes it.

---

## Procedural and failure memory

A capable agent should not merely remember what happened. It should retain **how to succeed** and **how not to fail the same way again**.

Procedural memory stores reusable action knowledge.

Failure memory should preserve:

```text
attempt
context
expected outcome
actual outcome
root cause
correction
verification
applicability
expiry / recheck condition
```

This is especially important for coding agents, browser agents, operations agents, and long-running autonomous systems.

---

## Collective and inherited memory

Shared memory is not simply a database with multiple API keys.

Collective memory introduces:

- ownership
- authorship
- tenancy
- roles
- source reputation
- write authority
- read authority
- dispute authority
- versioning
- succession

Inherited memory introduces another distinction:

```text
observed     -> this agent experienced it
inferred     -> this agent derived it
taught       -> another authority provided it
imported     -> brought from an external system
inherited    -> existed before this agent instance
generated    -> synthesized by a model/process
```

That provenance prevents agents from presenting inherited or synthetic state as firsthand experience.

---

## Security model

Memory is a security boundary because retained information can change future behavior.

Threat classes include:

- memory poisoning
- prompt-injection persistence
- access-spam reinforcement
- hallucination permanence
- recursive self-citation
- source spoofing
- provenance stripping
- unauthorized mutation
- stale policy retention
- cross-user or cross-tenant leakage
- malicious correction
- overbroad context assembly
- sensitive-data persistence
- poisoned procedural memory

A trustworthy system governs:

```text
write admission
source trust
scope
retrieval admission
mutation authority
promotion
sharing
expiry
correction
revocation
deletion
audit
```

---

## Evaluation: recall is only level one

A memory system should be evaluated at four levels.

### Level 1: Recall

Can it retrieve a past fact or event?

### Level 2: Temporal and update reasoning

Can it distinguish current, historical, contradicted, and superseded state?

### Level 3: Memory-guided action

Does retained experience improve later planning and execution?

### Level 4: Governed memory

Can it improve behavior while preserving provenance, privacy, authority, correction, deletion, and scope?

Recent benchmarks increasingly expose the gap between simple recall and memory-guided agent performance. The doctrine therefore treats **task outcome, avoided repeated failure, stale-memory contamination, false permanence, and governance compliance** as first-class memory metrics.

Recommended evaluation dimensions:

| Stage | Metrics |
|---|---|
| Encoding | useful-memory precision/recall, sensitive-data rejection, unsupported-inference admission |
| Retrieval | relevant recall, temporal correctness, stale recall, contradiction contamination, abstention |
| Consolidation | abstraction accuracy, transfer utility, provenance completeness, exception preservation |
| Revision | correction propagation, supersession accuracy, rollback integrity |
| Forgetting | false permanence, valuable-memory loss, deletion completeness, interference reduction |
| Agent behavior | task success, avoided repeated failure, tool-call quality, latency, token cost |
| Security | poisoning success, leakage, unauthorized mutation, memory-induced jailbreaks |

See the current research map in [`docs/23-research-bibliography.md`](docs/23-research-bibliography.md).

---

## Development guide

For a new memory implementation, build in this order.

### 1. Define contracts

Establish:

- memory unit schema
- stable identity
- provenance
- scope
- lifecycle state
- mutation events

### 2. Build write admission

Implement:

- candidate extraction
- sensitivity classification
- source classification
- deduplication
- contradiction detection
- admission policy

### 3. Build multiple recall paths

Support appropriate combinations of:

- exact address
- semantic similarity
- graph traversal
- temporal retrieval
- procedural retrieval

Then govern what may actually enter context.

### 4. Build correction before clever reflection

Implement:

- dispute
- supersession
- reconciliation
- mutation history
- rollback

A system that can synthesize insights but cannot reliably correct itself has prioritized the cinematic feature.

### 5. Build forgetting

Implement intentionally distinct modes:

- decay
- suppression
- archive
- prune
- delete
- tombstone

### 6. Build consolidation

Add:

- summarization
- semantic extraction
- procedure induction
- generalization
- reflection with provenance

### 7. Add governance

Enforce:

- mutation authority
- certification
- privacy
- tenancy
- sharing boundaries
- audit

### 8. Evaluate the lifecycle

Use adversarial fixtures and multi-session action tasks, not just retrieval QA.

---

## Repository map

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
│   ├── 20-memory-foundations-across-scales.md
│   ├── 21-forgetting-consolidation-and-memory-metabolism.md
│   ├── 22-agentic-memory-theory-and-development.md
│   ├── 23-research-bibliography.md
│   └── adr/
│       ├── ADR-001-uor-is-identity-not-memory.md
│       ├── ADR-002-saturation-is-routing-not-truth.md
│       ├── ADR-003-crystallization-requires-certification.md
│       ├── ADR-004-pama-controls-mutation-authority.md
│       ├── ADR-005-codegenome-is-code-reality-substrate.md
│       ├── ADR-006-neurospace-is-runtime-memory-space.md
│       ├── ADR-007-agent-memory-is-component-architecture.md
│       ├── ADR-008-memory-threat-model-is-required.md
│       ├── ADR-009-source-trust-is-a-first-class-signal.md
│       ├── ADR-010-conflict-resolution-is-a-separate-component.md
│       ├── ADR-011-temporal-causality-is-required-for-memory-evolution.md
│       ├── ADR-012-privacy-and-sensitivity-classification-is-required.md
│       ├── ADR-013-governed-recall-planner-is-required.md
│       ├── ADR-014-schema-registry-and-type-evolution-are-needed.md
│       ├── ADR-015-retention-deletion-and-tombstones-are-required.md
│       ├── ADR-016-actor-scope-consent-and-tenancy-are-required.md
│       ├── ADR-017-memory-observability-and-audit-events-are-required.md
│       ├── ADR-018-recovery-rollback-and-replay-are-required.md
│       └── ADR-019-memory-quality-metrics-are-required.md
├── fixtures/
├── schemas/
├── scripts/
│   └── validate_fixtures.py
└── .github/
```

Numbers 15-19 remain intentionally available for the foundational architecture additions already specified in `14-expanded-scope-recommendations.md`.

---

## Reading paths

### If you are new to agent memory

1. [`20-memory-foundations-across-scales.md`](docs/20-memory-foundations-across-scales.md)
2. [`22-agentic-memory-theory-and-development.md`](docs/22-agentic-memory-theory-and-development.md)
3. [`AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md`](docs/AGENTIC_MEMORY_SYSTEMS_CANONICAL_ARCHITECTURE.md)
4. [`00-glossary.md`](docs/00-glossary.md)

### If you are implementing a system

1. [`11-component-architecture.md`](docs/11-component-architecture.md)
2. [`02-lifecycle-state-machine.md`](docs/02-lifecycle-state-machine.md)
3. [`03-scoring-and-decay.md`](docs/03-scoring-and-decay.md)
4. [`04-governance-and-pama.md`](docs/04-governance-and-pama.md)
5. [`06-conformance-test-plan.md`](docs/06-conformance-test-plan.md)
6. [`09-calibration-protocol.md`](docs/09-calibration-protocol.md)
7. [`10-memory-unit-examples.md`](docs/10-memory-unit-examples.md)

### If you care about forgetting, retention, and deletion

1. [`21-forgetting-consolidation-and-memory-metabolism.md`](docs/21-forgetting-consolidation-and-memory-metabolism.md)
2. [`03-scoring-and-decay.md`](docs/03-scoring-and-decay.md)
3. `ADR-015-retention-deletion-and-tombstones-are-required.md`

### If you are researching the field

1. [`23-research-bibliography.md`](docs/23-research-bibliography.md)
2. [`20-memory-foundations-across-scales.md`](docs/20-memory-foundations-across-scales.md)
3. [`08-source-material-index.md`](docs/08-source-material-index.md)
4. [`12-concept-segmentation-matrix.md`](docs/12-concept-segmentation-matrix.md)

### If you are integrating another repository

1. [`05-repo-implementation-map.md`](docs/05-repo-implementation-map.md)
2. [`13-system-composition-boundaries.md`](docs/13-system-composition-boundaries.md)
3. [`07-integration-roadmap.md`](docs/07-integration-roadmap.md)

---

## Fixture validation

Run from the repository root:

```bash
python scripts/validate_fixtures.py
```

The validator uses only the Python standard library.

Existing fixtures test cases including:

- certified durable memory
- confidently wrong memory
- contradicted memory
- ephemeral memory
- access-spam junk
- unauthorized mutation
- pruning with audit preservation
- valuable persistent memory

The conformance suite should continue expanding toward:

- stale-but-historically-valid memory
- semantic abstraction with preserved evidence
- prospective memory completion
- procedural memory version drift
- inherited-memory provenance
- deletion propagation
- cross-tenant recall denial
- memory poisoning
- conflict reconciliation
- retrieval interference

---

## Research discipline

Agent Memory deliberately combines architecture and interdisciplinary research, so source discipline matters.

When importing a concept, label it as one of:

```text
MECHANISM
Demonstrated in the source substrate.

FUNCTIONAL ANALOGY
A similar problem or function appears elsewhere.

ENGINEERING PRESCRIPTION
A requirement justified by agent-system evidence or governance.

OPEN HYPOTHESIS
Promising, but not doctrine yet.
```

Biological analogy must not be used as implementation evidence by itself.

A paper saying the hippocampus does something does not create a Jira ticket requiring a `HippocampusService`.

See [`docs/23-research-bibliography.md`](docs/23-research-bibliography.md).

---

## Non-goals

This repository is not:

- a vector database
- a RAG wrapper
- a chatbot prompt pack
- a universal cognitive model
- a claim that LLM agents think like humans
- a replacement for UOR, EvolveAI, CodeGenome, COREFORGE, PAMA, FailSafe, or Bicameral
- an excuse to put every vaguely memory-shaped idea into one mega-framework

It is the canonical spine for organizing memory theory, architecture, governance, implementation, and evidence.

---

## Conformance challenge

Before calling a system an Agent Memory implementation, it should be able to answer:

1. What exactly is a memory unit?
2. What persistence boundary does each memory class cross?
3. What is raw evidence versus derived memory?
4. How are episodic, semantic, procedural, and prospective memory distinguished?
5. Who may create, mutate, promote, share, or delete memory?
6. How are source trust and provenance represented?
7. How are stale, historical, disputed, and superseded states distinguished?
8. How does forgetting work?
9. How does user deletion propagate into derived state?
10. How does retrieval enforce scope and sensitivity?
11. How is poisoning contained?
12. How are corrections propagated?
13. How are failures converted into reusable learning without overgeneralization?
14. How is inherited memory distinguished from direct experience?
15. What evidence shows memory improves later agent action?

If the answers reduce to "we embed previous messages and retrieve the top five," the system has useful retrieval. It does not yet have a memory architecture.

---

## Direction

The long-term goal is to make this repository the **quintessential reference for Agentic Memory theory, function, governance, and development**:

```text
memory science
   +
agent architecture
   +
security and governance
   +
implementation contracts
   +
conformance tests
   +
evaluation benchmarks
   =
Agent Memory
```

The wedge is not remembering more.

The wedge is **remembering, transforming, using, correcting, and forgetting the right information under the right authority at the right time**.
