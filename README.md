<div align="center">

# Agent Memory

### A reference architecture for governed memory in autonomous and agentic systems

From working memory to inherited state. From biological theory to executable conformance. From probabilistic inference to bounded authority.

[![Validate Doctrine Evidence](https://github.com/Knapp-Kevin/agent-memory/actions/workflows/validate-doctrine-evidence.yml/badge.svg)](https://github.com/Knapp-Kevin/agent-memory/actions/workflows/validate-doctrine-evidence.yml)
![Architecture](https://img.shields.io/badge/Architecture-Reference%20Architecture-334155)
![ADRs](https://img.shields.io/badge/ADRs-19%20Accepted%20%7C%201%20Proposed-2563eb)
![Conformance](https://img.shields.io/badge/Conformance-Level%206%20Spec-7c3aed)
![Fixtures](https://img.shields.io/badge/Fixtures-24%20Validated-0f766e)
![Research](https://img.shields.io/badge/Research-Open%20Evidence-b45309)
[![License](https://img.shields.io/badge/License-Apache--2.0-0b7285)](LICENSE)

**[Documentation](docs/README.md)** · **[PAMA](docs/pama/README.md)** · **[Architecture decisions](docs/adr/README.md)** · **[Research map](docs/23-research-bibliography.md)** · **[Conformance](docs/06-conformance-test-plan.md)** · **[Contributing](CONTRIBUTING.md)** · **[Governance](GOVERNANCE.md)** · **[Security](SECURITY.md)**

</div>

---

> [!IMPORTANT]
> **Current maturity:** the doctrine, schemas, and 24 conformance fixture definitions are repository-validated. ADR-001 through ADR-019 are accepted architecture decisions. **ADR-020 remains Proposed** because governed uncertainty still requires real runtime evidence end to end. Passing fixture validation is not the same thing as proving a production memory system behaves correctly.

## The thesis

**Agentic memory is retained state that can alter an agent's future interpretation, reasoning, planning, tool use, action, or adaptation across a meaningful persistence boundary.**

That makes memory much larger than retrieval.

A serious memory system must decide:

- what deserves to be encoded
- what should remain ephemeral
- what becomes durable
- what should be consolidated or generalized
- what must remain exact and historical
- what can be trusted, disputed, corrected, shared, or inherited
- what should be forgotten
- what uncertainty must remain visible
- what an agent is actually authorized to change

The core governed-uncertainty model is deliberately simple:

> **Probabilistic epistemics. Governed consequences.**
>
> **Uncertainty may propose. Authority constrains.**

The architecture does **not** require all memory behavior to be deterministic. It requires uncertain inference to remain separate from the authority to create durable consequences.

---

## Start here

You do not need to read the repository front to back. Human working memory has suffered enough.

| If you are... | Start with | Then read |
|---|---|---|
| **Researching memory theory** | [Memory foundations across scales](docs/20-memory-foundations-across-scales.md) | [Forgetting & consolidation](docs/21-forgetting-consolidation-and-memory-metabolism.md), [Research bibliography](docs/23-research-bibliography.md), [Governed uncertainty](docs/24-determinism-probability-and-governed-uncertainty.md) |
| **Designing an agent architecture** | [Layer model](docs/01-layer-model.md) | [Component architecture](docs/11-component-architecture.md), [Composition boundaries](docs/13-system-composition-boundaries.md), [Agentic memory theory](docs/22-agentic-memory-theory-and-development.md) |
| **Designing adaptive authority** | [PAMA foundation](docs/pama/README.md) | [Governance & PAMA](docs/04-governance-and-pama.md), [PAMA decision table](docs/33-pama-decision-table.md), [ADR-004](docs/adr/ADR-004-pama-controls-mutation-authority.md) |
| **Implementing a memory system** | [Agentic memory theory](docs/22-agentic-memory-theory-and-development.md) | [Lifecycle](docs/02-lifecycle-state-machine.md), [PAMA](docs/04-governance-and-pama.md), [Recall planner](docs/26-governed-recall-planner.md), [Schemas](schemas/) |
| **Reviewing security or privacy** | [Memory threat model](docs/15-memory-threat-model.md) | [Source trust](docs/16-source-trust-and-reputation.md), [Privacy](docs/19-privacy-and-sensitivity-classifier.md), [Retention & deletion](docs/28-retention-deletion-and-tombstones.md), [Scope & tenancy](docs/29-actor-scope-consent-and-tenancy.md) |
| **Evaluating conformance** | [Conformance test plan](docs/06-conformance-test-plan.md) | [Calibration](docs/09-calibration-protocol.md), [Audit rubric](docs/25-governed-uncertainty-documentation-conformance-audit.md), [Fixtures](fixtures/) |
| **Reviewing architecture decisions** | [ADR index](docs/adr/README.md) | ADR-001 through ADR-020 |
| **Contributing evidence or challenges** | [CONTRIBUTING.md](CONTRIBUTING.md) | [Source material index](docs/08-source-material-index.md), [Research bibliography](docs/23-research-bibliography.md) |

The complete document map is in **[docs/README.md](docs/README.md)**.

---

## Why this repository exists

Most AI-memory implementations begin with:

> How do we retrieve old context?

That is useful. It is also much too small.

Retrieval does not answer:

- whether the memory should have been stored
- whether it is current or merely historically true
- whether it came from observation, inference, inheritance, or synthesis
- whether the source is trustworthy within this scope
- whether the memory belongs to this user or tenant
- whether it conflicts with stronger evidence
- whether it should be generalized into semantic or procedural memory
- whether a model is confident but wrong
- whether the memory is safe to place into the current context
- whether a deletion request propagated into derived state
- whether a learned policy is proposing an action or granting itself authority

**Agent Memory exists to make those questions architectural rather than accidental.**

---

## Native doctrine: Proportional Adaptive Mutation Authority

**Proportional Adaptive Mutation Authority (PAMA) is native Agent Memory doctrine authored by Kevin R. Knapp.** It is not an external dependency, related-product import, or source-registry item.

Its systems-agnostic rule is:

> **Adaptation should be broadly available to authorized agents. Authority to make a mutation durable, influential, shared, or action-enabling should increase in proportion to the mutation's consequence.**

PAMA preserves four separations:

```text
adaptation != authority
memory != procedure
procedure != permission
permission != governance
```

And it separates four dimensions that are easy to muddle when governance is reduced to a single score:

```text
M0-M5 target class
lifecycle strength
requested operation
A0-A5 downstream authority
```

A validated procedure can become a trusted capability without gaining permission to execute externally. A highly reinforced memory can remain barred from governance effects. Low-risk reversible learning can proceed without turning a human into the bottleneck for every observation.

See **[PAMA](docs/pama/README.md)**, **[Governance and PAMA](docs/04-governance-and-pama.md)**, and **[PAMA Decision Table](docs/33-pama-decision-table.md)**.

---

## The system at a glance

<p align="center">
  <img src="assets/agent-memory-flow.svg" alt="Agent Memory governed memory loop: experience becomes evidence and an estimate, PAMA constrains the permitted actions, a consequence is committed with a receipt, retained state is recalled through policy, and memory influences future context." width="100%" />
</p>

The critical invariant is:

```text
selected_action ∈ permitted_action_set
```

And the equally important one:

```text
estimator_output != authority
```

A model may estimate relevance, trust, contradiction, sensitivity, staleness, utility, or risk. Those estimates can shape the decision. They do not create permission by themselves.

See **[Determinism, Probability, and Governed Uncertainty](docs/24-determinism-probability-and-governed-uncertainty.md)**.

---

## Where determinism belongs, and where it does not

The useful boundary is not "deterministic memory versus probabilistic memory."

| Responsibility | Typical control character | Why |
|---|---|---|
| Exact identity and references | **Deterministic** | Ambiguous identity corrupts every later decision |
| Schema and transition validity | **Deterministic** | Invalid states should not depend on model confidence |
| Provenance and policy version | **Deterministic records** | Consequence must be reconstructable |
| Semantic relevance | **Probabilistic / learned / heuristic** | Relevance is contextual and uncertain |
| Source trust | **Probabilistic / evidence-driven** | Reliability is scoped and evolves over time |
| Contradiction and causal interpretation | **Probabilistic / hybrid** | Evidence may support multiple hypotheses |
| Sensitivity classification | **Deterministic when exact; probabilistic when inferred** | Uncertainty must remain visible |
| Lifecycle candidacy | **Probabilistic / calibrated / heuristic** | Persistence pressure is not truth |
| Mutation authority | **Deterministic or formally bounded** | Permission must not emerge from confidence |
| Recall admission | **Governed** | Relevance does not override tenant, sensitivity, or policy |
| Choice among permitted actions | **May be stochastic** | Exploration is acceptable inside the safe envelope |
| Durable state transition | **Governed and auditable** | Consequence must bind to policy, state, and authority |

A deterministic rule can be perfectly reproducible and perfectly wrong.

A probabilistic component can be useful and safe when it operates inside an explicit authority envelope.

---

## The seven functions of memory

A mature memory architecture must do more than store and search.

```text
ENCODE -> RETAIN -> CONSOLIDATE -> RETRIEVE -> REVISE -> FORGET -> INHERIT
```

| Function | Architectural question |
|---|---|
| **Encode** | What experience becomes a memory candidate? |
| **Retain** | What crosses the relevant persistence boundary? |
| **Consolidate** | What can be generalized, summarized, proceduralized, or modeled? |
| **Retrieve** | What retained state is relevant now? |
| **Revise** | How do correction, contradiction, supersession, and disagreement change memory? |
| **Forget** | What should decay, suppress, archive, redact, tombstone, or delete? |
| **Inherit** | What state may pass to a successor agent, team, or generation? |

See **[Agentic Memory Theory and Development](docs/22-agentic-memory-theory-and-development.md)**.

---

## Memory across scales

This repository deliberately studies memory beyond software architecture.

| Scale | What persists | Useful questions for agent design |
|---|---|---|
| **Neural / cognitive** | active state, plasticity, distributed representations | working memory, episodic/semantic distinction, uncertainty, interference |
| **Cellular** | altered future response | persistence without autobiographical record |
| **Immune** | changed response to later exposure | adaptation, specificity, inherited response state |
| **Individual agent** | state across steps, tasks, or sessions | preferences, episodes, procedures, corrections |
| **Multi-agent / institutional** | shared state beyond one actor | policy, ownership, consensus, provenance, tenancy |
| **Inherited / evolutionary-scale** | state survives the originating individual/process | priors, weights, seed doctrine, inherited constraints |

> [!NOTE]
> These are **functional comparisons**, not claims of substrate equivalence. An embedding index is not a hippocampus. A system prompt is not a genome. A cache eviction policy is not human forgetting. Analogy becomes useful after the poetry stops impersonating mechanism.

See **[Memory Foundations Across Scales](docs/20-memory-foundations-across-scales.md)**.

---

## Memory horizons and types are separate dimensions

### Persistence horizons

```text
Immediate -> Working -> Session -> Episodic -> Long-term -> Remote -> Inherited
```

A horizon says **how far state persists**, not what kind of memory it is.

### Content types

The canonical taxonomy includes:

- observation
- episodic
- semantic
- procedural
- prospective
- preference
- relationship
- policy
- failure
- correction
- decision
- evidence
- compact environment/model state
- inherited memory

A procedural memory can be session-local or remote. An episodic record can become permanent evidence. A semantic claim can remain provisional. Treating "long-term memory" as one storage bucket hides those differences.

---

## Forgetting is a first-class capability

A memory system that remembers everything is not maximally intelligent. It is a database with boundary problems.

Agent Memory distinguishes:

- decay
- suppression
- interference management
- deprioritization
- pruning
- archival
- compression
- semanticization
- supersession
- redaction
- tombstoning
- cryptographic deletion
- full-pipeline purge
- specialized model unlearning

These operations have different consequences and authority requirements.

```text
predicted low utility -> forgetting candidate
predicted low utility != irreversible deletion authority
```

Deletion must also account for derived memory such as summaries, indexes, graph edges, caches, exported copies, and consolidated state where the system controls them.

See **[Forgetting, Consolidation, and Memory Metabolism](docs/21-forgetting-consolidation-and-memory-metabolism.md)** and **[Retention, Deletion, and Tombstones](docs/28-retention-deletion-and-tombstones.md)**.

---

## Canonical architecture

Agent Memory is **one reference architecture composed of bounded components**, not one monolithic library.

| Component | Owns | Must not silently own |
|---|---|---|
| **Identity substrate** | stable identity, exact addressing | lifecycle policy, truth |
| **Evidence & provenance** | source records, derivation, witnesses | permanence |
| **Source trust** | scoped reliability evidence | authority |
| **Reality graphs** | domain structure and relations | canonical memory status |
| **Lifecycle engine** | explicit memory states and transitions | identity semantics |
| **Saturation & decay** | persistence pressure and routing signals | truth, certification |
| **Conflict resolution** | disagreement and resolution proposals | ungoverned overwrite |
| **Temporal causality** | chronology, valid time, causal hypotheses | certainty from sequence alone |
| **Governance / PAMA** | M0-M5 target classes, A0-A5 authority ceilings, mutation and consequence authority | factual truth, raw scoring |
| **Privacy & sensitivity** | handling classification and disclosure constraints | optimistic scope guessing |
| **Certification** | durable transition confirmation | eternal immutability |
| **Runtime memory** | operational use and graph traversal | doctrine ownership |
| **Governed recall** | context admission | relevance-as-permission |
| **Correction & dispute** | revision without history destruction | silent overwrite |
| **Durable decision memory** | decisions, rationale, supersession, drift | product ownership by adjacency |
| **Observability** | decision and transition evidence | sensitive shadow copies |
| **Recovery** | rollback, compensation, replay | rewriting history to hide errors |
| **Conformance** | fixtures, schemas, calibration, quality metrics | claims of runtime proof without runtime evidence |

See **[Component Architecture](docs/11-component-architecture.md)** and **[System Composition Boundaries](docs/13-system-composition-boundaries.md)**.

---

## Signals that must remain separate

One universal memory score is appealing for the same reason one permissions role named `admin-ish` is appealing: fewer fields, more regret.

| Signal | Means | Does **not** mean |
|---|---|---|
| Identity | exact object/reference | truth or usefulness |
| Confidence | support for an estimate/claim | authority |
| Probability | modeled uncertainty with defined semantics | generic score |
| Similarity | representational closeness | correctness |
| Source trust | expected reliability in scope | permission |
| Relevance | usefulness to current task | recall authorization |
| Saturation | lifecycle persistence pressure | truth |
| Sensitivity | handling/privacy risk | low utility |
| Scope | where memory is valid/visible | global truth |
| Authority | permission for a consequence | evidence quality |
| Certification | required confirmation passed | immutability |
| Contradiction | retained state conflicts | automatic winner selection |

---

## Lifecycle

Memory has history. The architecture should be able to explain it.

| Formation | Durability | Use & drift | Repair & forgetting |
|---|---|---|---|
| `Transient -> Observed -> Linked -> Reinforced` | `Candidate -> Pending verification -> Crystallized` | `Operationally reused -> Stale / Disputed` | `Corrected -> Reconciled -> Archived / Pruned -> Tombstoned` |

This is intentionally a compact README view rather than the complete transition graph. Not every memory follows every transition, and several states have governed branches that do not fit honestly into one tiny horizontal picture.

The invariant is that consequential transitions remain explicit, scoped, authorized, and auditable.

See **[Lifecycle State Machine](docs/02-lifecycle-state-machine.md)** for the canonical state machine.

---

## Security and privacy are lifecycle concerns

Persistent memory creates attack surfaces that do not exist in a stateless exchange.

The threat model includes:

- direct and sleeper memory poisoning
- hallucination permanence
- recursive self-citation
- authority laundering through summaries or trusted tools
- provenance stripping
- cross-tenant leakage
- sensitive-memory extraction
- unsafe multi-memory composition
- stale authorization
- stochastic policy bypass
- estimator manipulation and calibration drift
- malicious correction
- irreversible deletion abuse
- deletion residue in derived memory

Write-time safety is not lifetime safety.

A memory can appear benign when stored and become unsafe later when another context retrieves, combines, or acts on it.

See **[Memory Threat Model](docs/15-memory-threat-model.md)** and **[Privacy and Sensitivity](docs/19-privacy-and-sensitivity-classifier.md)**.

---

## Conflict, time, and correction

A mature memory system must preserve more than one kind of disagreement.

```text
factual contradiction
!= temporal supersession
!= scope mismatch
!= source disagreement
!= policy conflict
!= estimator disagreement
```

Likewise:

```text
historically true != currently true
stale != false
superseded != corrected
chronology != causality
```

Conflict interpretation may be probabilistic. Resolution consequences remain governed.

See **[Conflict Resolution](docs/17-conflict-resolution-engine.md)** and **[Temporal Causality](docs/18-temporal-causality-layer.md)**.

---

## Conformance and executable evidence

The repository now contains machine-readable doctrine evidence, not just prose.

### Schemas

- [`memory-unit.schema.json`](schemas/memory-unit.schema.json)
- [`conformance-report.schema.json`](schemas/conformance-report.schema.json)
- [`decision-receipt.schema.json`](schemas/decision-receipt.schema.json)
- [`memory-audit-event.schema.json`](schemas/memory-audit-event.schema.json)
- [`calibration-results.schema.json`](schemas/calibration-results.schema.json)
- [`source-record.schema.json`](schemas/source-record.schema.json)
- [`pama-decision.schema.json`](schemas/pama-decision.schema.json)

### Fixtures

The [`fixtures/`](fixtures/) directory contains **24 validated fixture definitions**, including:

- valuable persistent memory
- ephemeral memory
- access-spam junk
- confidently wrong memory
- contradiction
- certified durable memory
- unauthorized mutation
- audit-preserving pruning
- high-confidence false promotion
- threshold jitter
- estimator disagreement
- cross-tenant relevance
- stochastic retrieval inside policy
- unsafe multi-memory composition
- uncertain sensitivity
- irreversible deletion under uncertain utility
- policy/estimator drift
- concurrent mutation
- sleeper poisoning
- authority laundering
- deletion residue
- out-of-calibration-scope scoring
- expired delegation
- stochastic replay reconstruction

### Validate locally

```bash
python -m pip install jsonschema
python scripts/validate_fixtures.py fixtures
python scripts/validate_schemas.py
python scripts/validate_doctrine_boundaries.py
```

The **[Validate Doctrine Evidence](.github/workflows/validate-doctrine-evidence.yml)** workflow runs the same checks on pushes and pull requests.

> [!WARNING]
> These checks prove schema and fixture coherence. They do **not** prove a runtime implementation detects poisoning, enforces tenancy, contains a stochastic planner, resolves concurrency, or propagates deletion correctly. Structural evidence is a prerequisite for runtime evidence, not a substitute for it.

See **[Conformance Test Plan](docs/06-conformance-test-plan.md)**.

---

## Conformance levels

| Level | Evidence target |
|---|---|
| **0** | documentation alignment |
| **1** | identity and provenance |
| **2** | lifecycle and decay |
| **3** | calibrated saturation and trap resistance |
| **4** | PAMA or equivalent mutation authority |
| **5** | certification and audited crystallization |
| **6** | governed uncertainty across estimator, policy, action-set, and committed-consequence boundaries |

Level 6 does not mean "make the model deterministic."

It means uncertainty can remain adaptive while prohibited consequences stay outside the reachable action space.

---

## Architecture decisions and current maturity

See **[docs/adr/README.md](docs/adr/README.md)** for status semantics.

| Area | Current state |
|---|---|
| Core doctrine | **Canonical and extensively documented** |
| Native PAMA doctrine | **Canonical; authored by Kevin R. Knapp** |
| ADR-001 through ADR-019 | **Accepted** |
| ADR-020 governed uncertainty | **Proposed** |
| Documentation conformance audit | **Recorded piece by piece** |
| JSON Schemas | **7 validated schemas** |
| Conformance fixture definitions | **24 validated fixtures** |
| Repository validation workflow | **Active** |
| Runtime reference implementation | **Not yet the evidence basis of this repo** |
| ADR-020 runtime proof | **Incomplete by design** |
| Research evidence | **Living, open-evidence-preferred, challengeable** |

### Why ADR-020 is still Proposed

The repository already has the theory, contracts, schemas, receipts, fixtures, and validation machinery.

What it intentionally does **not** yet claim is that a real implementation has demonstrated, end to end:

```text
estimate / proposal
    -> governance envelope
    -> permitted action set
    -> selected action
    -> committed consequence
```

with repeated stochastic trials, cross-scope admission tests, actual concurrency behavior, deletion propagation, and reconstructable runtime receipts.

That missing evidence is a feature of the governance process, not an embarrassing footnote to hide below the fold.

---

## Research posture

This repository uses research to **learn and challenge**, not to decorate architecture with citation density.

Preferred evidence sources, when practical, include:

- open-access journals
- PubMed Central and comparable public archives
- lawful preprints
- open conference proceedings
- public technical reports
- open datasets and benchmark repositories
- standards and government publications

For consequential claims, the goal is to preserve:

```text
supporting evidence
challenging evidence
boundary conditions
implementation evidence
conformance evidence
known uncertainty
```

When transferring an idea from biological or cognitive memory into software, classify it as:

```text
MECHANISM
FUNCTIONAL ANALOGY
ENGINEERING PRESCRIPTION
OPEN HYPOTHESIS
```

The repository should be willing to revise a favorite theory when better evidence shows up. Otherwise this is not a research architecture; it is a belief system with Markdown.

See **[Research Bibliography](docs/23-research-bibliography.md)** and **[Source Material Index](docs/08-source-material-index.md)**.

---

## Related implementation systems

The doctrine currently maps several systems into bounded implementation roles where they add specific value:

| System | Role |
|---|---|
| **UOR Framework** | exact identity and deterministic addressability |
| **EvolveAI** | memory metabolism and lifecycle prototype |
| **CodeGenome** | code-reality graph, evidence, provenance, inferred relations |
| **COREFORGE Vault / Neurospace** | local-first runtime memory and agent-facing recall |
| **FailSafe / Arbiter** | governance enforcement, evidence, approval boundaries |

**PAMA is intentionally not in this external implementation table.** It is native Agent Memory doctrine. A runtime may implement PAMA inside any conforming codebase while preserving its authority boundary.

**Durable decision memory is also defined internally**, through the [Durable Decision Memory Profile](docs/profiles/durable-decision-memory-profile.md). A product earns an implementation mapping by demonstrating evidence against that profile, not by being conceptually nearby.

The map defines architectural implementation roles. It does not claim every related repository already conforms to every current contract.

See **[Repo Implementation Map](docs/05-repo-implementation-map.md)**.

---

## Repository map

```text
agent-memory/
├── README.md                       # front door and architecture overview
├── LICENSE                         # Apache License 2.0
├── NOTICE                          # authorship, attribution, rights boundary
├── CITATION.cff                    # citation metadata
├── CONTRIBUTING.md                 # evidence and contribution standard
├── GOVERNANCE.md                   # repository decision and doctrine governance
├── SECURITY.md                     # vulnerability reporting policy
├── CODE_OF_CONDUCT.md              # contributor conduct expectations
├── assets/                         # stable README presentation graphics
├── docs/
│   ├── README.md                   # full documentation index
│   ├── pama/                       # native PAMA foundation
│   ├── 00-10                       # architecture spine
│   ├── 11-19                       # composition, security, trust, time, privacy
│   ├── 20-25                       # interdisciplinary theory and governed uncertainty
│   ├── 26-39                       # operational and executable contracts
│   ├── profiles/                   # doctrine profiles for memory classes
│   ├── adr/                        # architecture decision records
│   └── audits/                     # preserved audit history
├── sources/                        # external/material source-rights registry
├── schemas/                        # doctrine-level JSON Schemas
├── fixtures/                       # 24 conformance fixture definitions
├── scripts/                        # fixture, schema, link, and doctrine-boundary validators
└── .github/
    ├── CODEOWNERS
    ├── ISSUE_TEMPLATE/
    └── workflows/
        └── validate-doctrine-evidence.yml
```

---

## Core invariants

These are the shortest route to the doctrine:

1. **Identity is not memory.**
2. **Retrieval is not memory.**
3. **Confidence is not authority.**
4. **Trust is not authority.**
5. **Relevance is not permission.**
6. **Saturation is not truth.**
7. **Reflection is not evidence.**
8. **A deterministic threshold is not certainty.**
9. **A probabilistic component is not inherently ungovernable.**
10. **Proposal is not commit.**
11. **Historical truth is not current truth.**
12. **Chronology is not causality.**
13. **Uncertain sensitivity is not non-sensitive.**
14. **Utility is not deletion authority.**
15. **Provenance must survive transformation.**
16. **A blocked action must remain blocked downstream.**
17. **Stochastic choice may occur only inside a permitted action set.**
18. **Memory must remain correctable after becoming durable.**
19. **Forgetting is a governed family of operations.**
20. **Memory quality is measured by future behavior, not recall alone.**
21. **Adaptation is not authority.**
22. **Memory is not procedure.**
23. **Procedure is not permission.**
24. **Permission is not governance.**
25. **Validated capability does not imply autonomous execution authority.**

---

## What this repository is not

It is **not**:

- a claim that brains are databases
- a neuroscience simulation
- one universal memory algorithm
- a vector-store wrapper presented as complete memory architecture
- a benchmark leaderboard
- a production-runtime certification program
- proof that every mapped implementation already conforms
- a requirement that uncertain cognition become deterministic
- an architecture whose validity depends on keeping every adjacent product name in the doctrine

It **is** a place to define, challenge, test, and eventually implement the contracts required for memory that persists without becoming ungoverned state.

---

## Contributing

Read **[CONTRIBUTING.md](CONTRIBUTING.md)** before proposing architecture, research, schema, or conformance changes. Repository decision rights and doctrine-change expectations are in **[GOVERNANCE.md](GOVERNANCE.md)**, and security-sensitive findings should follow **[SECURITY.md](SECURITY.md)**.

The most valuable contributions are not limited to confirming the current doctrine. Strong counterexamples, contradictory research, adversarial fixtures, implementation failures, and evidence that an accepted decision should be revised are all first-class contributions.

When a doctrine claim changes, preserve the reason it changed.

When a probabilistic system fails, preserve the uncertainty and evidence.

When a deterministic policy fails, resist the temptation to congratulate it for failing reproducibly.

---

## License, citation, and attribution

Agent Memory is licensed under the **[Apache License 2.0](LICENSE)**. The license applies to original material distributed as part of this repository unless a file or section states otherwise.

Authorship and attribution notices are recorded in **[NOTICE](NOTICE)**. Citation metadata is available in **[CITATION.cff](CITATION.cff)**.

Third-party research, repositories, issue comments, linked documents, and other referenced material remain subject to their own rights and licenses. A citation or public link does not relicense that material under Apache-2.0. See **[Source Rights Policy](docs/SOURCE_RIGHTS_POLICY.md)** and the **[source registry](sources/source-registry.json)** for the repository's reuse discipline.

---

## The long-term objective

The wedge is not remembering more.

It is building memory systems that can explain:

- **why something was remembered**
- **why it was trusted**
- **what uncertainty remained**
- **why it entered the current context**
- **what the agent was allowed to change**
- **why a state transition occurred**
- **how the decision can be reconstructed**
- **how the memory can be corrected**
- **when and how it should be forgotten**

**The objective is not persistent recall. It is governed memory state across time.**
