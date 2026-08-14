# Memory-Native Logical State Algebra Pressure Test

Status: **active exploratory research** for #276. This document is not canonical doctrine and does not authorize a new storage engine, schema, or ADR.

## Research question

Does Agent Memory need a new memory-native logical state-transition algebra above replaceable physical persistence, or do the existing lifecycle, derivation, currentness, isolation, PAMA, maintenance, and evidence contracts already supply the required logical layer?

The working default is deliberately conservative:

```text
new abstraction
must prove missing reusable semantics
not merely rename existing operations
```

The burden of proof is on a new algebra.

## Evidence boundary

This pressure test starts from the completed cross-architecture research rather than from a blank-sheet design exercise.

That work already reproduced the same governance distinctions across file/document, linked-note, lexical, vector, knowledge-graph, temporal-graph, GraphRAG, event-log, relational/document, hierarchical, shared/distributed, opaque learned/latent, and hybrid families.

The durable findings include:

```text
identity != truth
retrieval != recall admission
relevance / reachability != permission
derived state != canonical authority
historical integrity != current truth
storage placement != authority
shared membership != mutation authority
delete operation != forgetting completeness
probabilistic / learned influence != durable write authority
```

A new logical algebra therefore has to improve portability, correctness, or implementation simplicity beyond those already-shared contracts.

## Existing primitive inventory

Before inventing any new operation vocabulary, map the proposed responsibilities to existing Agent Memory surfaces.

| Candidate logical responsibility | Existing Agent Memory surface | Current assessment |
|---|---|---|
| stable logical identity | memory-unit identity, source/evidence identity, optional content-reference profiles | already represented; content address intentionally remains distinct from logical identity |
| source provenance / derivation | provenance doctrine, derivation evidence, output-custody profile | already represented |
| derived-state currentness | derivation-currentness profile | already represented |
| correction / dispute / supersession | lifecycle, temporal-causality, correction/supersession doctrine | already represented |
| reinforcement / weakening | scoring/decay and governed-estimator doctrine | already represented as evidence/estimation, intentionally not authority |
| promotion / crystallization | lifecycle + PAMA | already represented |
| consolidation / summarization / semanticization | derived-state doctrine + maintenance-run evidence | already represented at the governance/evidence layer |
| projection rebuild / invalidation | derivation currentness + maintenance evidence | already represented |
| deletion / forgetting / purge | lifecycle/deletion doctrine + derived-residue evidence | already represented |
| scope / isolation | isolation-domain doctrine and crossing rules | already represented |
| concurrent/conflicting mutation | conflict/concurrency evidence + PAMA consequence boundary | represented; backend-specific transaction mechanics remain implementation-specific |
| autonomous maintenance transaction | maintenance-run evidence profile | already represented |
| learned / predictive influence | conditional-memory influence profile + governed uncertainty | already represented |
| mutation/action authority | PAMA | already represented and must remain separate from operation naming |
| portable execution / governance evidence | receipt/evidence profiles | already represented |
| implementation/module optionality | language-neutral core / optional implementation profiles and #274 | already represented conceptually; module packaging is current work |

### First finding

The candidate verbs from #276 mostly map cleanly to existing contracts:

```text
observe / ingest
  -> identity + provenance + proposal/commit evidence

link / derive
  -> derivation + currentness + custody

revise / correct / challenge / supersede
  -> lifecycle + temporal causality

reinforce / weaken
  -> estimator/scoring evidence, no authority effect by itself

consolidate / summarize / semanticize
  -> derived state + maintenance transaction + validation

promote / crystallize
  -> lifecycle transition + PAMA

invalidate / mark stale
  -> lifecycle/currentness

rebuild projection
  -> derivation currentness + maintenance transaction

forget / delete / purge
  -> deletion consequence + transitive residue/lifecycle satisfaction

predict / influence
  -> conditional-memory influence gate

re-evidence / revalidate
  -> currentness/evidence transition
```

This strongly argues **against** creating a second parallel lifecycle model merely to collect the verbs under one namespace.

## What could still be missing

The remaining candidate gap is narrower than a database engine or a new memory ontology.

Different module adapters may repeatedly need to package the same transition evidence:

```text
requested logical transition
+ target logical identity
+ source/currentness basis
+ scope/isolation basis
+ estimator evidence, if any
+ PAMA decision
+ backend transaction result
+ post-write validation result
+ lifecycle result
+ reconstructable receipt
```

If multiple materially different modules independently re-create this envelope with incompatible semantics, a **narrow transition contract** may be justified.

That would be an orchestration/evidence contract, not a physical persistence engine and not a replacement for PAMA or lifecycle doctrine.

## Cross-substrate mapping

Use one correction scenario to test whether the same logical semantics survive physically different stores.

### Scenario

```text
source S1 is current
-> derived state D1 is built from S1
-> S1 is corrected to S2
-> D1 remains physically present
```

The required logical result is:

```text
S1 remains historical evidence where policy permits
S2 becomes the current source version
D1 becomes stale / rebuild-required
D1 physical presence does not imply currentness
D1 may not regain authority from retrieval usefulness
rebuild produces a new derived identity/evidence chain
```

### Relational/document mapping

Representative physical implementation:

```text
canonical row/version table
+ transactional update
+ materialized/indexed derived view
```

Physical strengths:

- strong transaction boundaries;
- explicit version columns/foreign keys where designed;
- familiar concurrency controls;
- direct current-state queries.

Physical mismatch that the logical layer must expose:

- transaction success updates canonical state but does not automatically invalidate every external embedding/cache/summary;
- last-write-wins mechanics may be available but are not an acceptable universal contradiction semantic;
- physical row identity is not automatically stable logical memory identity across migrations or backend replacement.

Existing Agent Memory contracts already express the required correction/currentness/residue distinctions.

### Knowledge/temporal-graph mapping

Representative physical implementation:

```text
source/entity nodes
+ asserted/inferred edges
+ temporal validity
+ cached traversal/path or graph-derived summary
```

Physical strengths:

- explicit relationship structure;
- derivation edges can make lineage inspectable;
- temporal validity can preserve historical relationships naturally.

Physical mismatch that the logical layer must expose:

- an inferred edge/path can remain physically reachable after its basis changes;
- reachability does not establish currentness or permission;
- graph deletion may leave caches, summaries, embeddings, or external indexes;
- traversal authorization is a separate concern from graph connectivity.

Existing Agent Memory derivation/currentness/isolation contracts already express these distinctions.

### Event-log / ledger mapping

Representative physical implementation:

```text
append S1
append correction/supersession S2
materialize current view
```

Physical strengths:

- historical mutation sequence is naturally preserved;
- replay can reconstruct prior states;
- append-only integrity can be evidenced independently.

Physical mismatch that the logical layer must expose:

- historical integrity does not decide which event is current truth;
- tombstone/delete events do not prove derived information was forgotten;
- a valid append-only checkpoint advance does not prove retrieval behavior remained semantically acceptable.

Again, existing temporal/currentness/deletion doctrine already handles the logical distinction.

## External pressure signal: Agent Manifest checkpoint assessment

`agentrust-io/agent-manifest#298` provides a useful independent counterexample to treating state-transition integrity as semantic correctness.

The issue observes that an append-only, sequence-valid, fresh, in-budget memory checkpoint advance can still produce undesirable retrieval behavior, including correction-precedence failure, anchor displacement, cross-scope retrieval, or state collapse.

For #276 this supports the separation:

```text
state-transition integrity
!= semantic/retrieval behavior
!= lifecycle correctness
!= downstream authority
```

It does **not** establish that Agent Memory needs a new algebra or that Agent Manifest's proposed assessment artifact should be adopted.

## Interaction with #275

The first #275 comparison slice strengthens the same conclusion.

The reviewed implementations use substantially different product ontologies:

```text
EvolveAI
  lifecycle tiers + temporal graph + vault + synthesis

Hindsight
  world facts + experiences + mental models + banks

MemOS
  graph memory + cubes + scheduler + retrieval + skills

CodeGenome
  content-addressed multi-overlay code graph

GitNexus
  persistent code knowledge graph + precomputed structural intelligence

Graphify
  extracted/inferred knowledge graph
```

Despite that variation, they repeatedly raise the same questions:

- what is stable logical identity when bytes/physical IDs change?
- what is observed versus derived?
- what becomes stale after correction or revocation?
- what residue survives deletion?
- what scope may influence recall/traversal?
- what evidence supports a derived state?
- when is estimator output merely a proposal?
- what authority permits a durable consequence?

This is evidence that Agent Memory's **shared logical contract is real**.

It is not yet evidence that the shared contract needs to be replaced or wrapped in another algebra.

## Decision options

### A. `no_new_algebra`

Use the existing lifecycle, derivation/currentness, isolation, PAMA, maintenance, and evidence contracts directly through the #274 module contract.

Choose this if module implementations do not show recurring incompatible transition glue.

### B. `narrow_transition_contract`

Add a minimal representation-neutral transition envelope that references existing canonical contracts without redefining them.

Choose this only if at least two materially different module families repeatedly need the same orchestration/evidence binding and currently implement it inconsistently.

### C. `profile_specific`

Keep transition contracts inside module families where their physical semantics differ too much for one useful common transition envelope.

Choose this if a universal contract would mostly contain optional/unknown fields or hide important backend capability differences.

### D. `stronger_engine`

Create a broader memory-native logical runtime/state engine.

This requires the strongest evidence because it creates new durable architecture and implementation burden.

At this stage there is **no evidence sufficient to select D**.

## Preliminary disposition

Current evidence ranking, without pretending a research judgment is a scalar benchmark:

```text
leading hypothesis:        no_new_algebra
plausible if repetition emerges: narrow_transition_contract
plausible for irreducible backend differences: profile_specific
not currently justified:  stronger_engine
```

The leading hypothesis is falsifiable. #274 implementation work can overturn it if real adapters repeatedly duplicate missing transition semantics.

## What would justify a new generic contract

A new representation-neutral transition contract should be proposed only if all of these occur:

1. at least two materially different module/substrate families implement the same logical transition;
2. existing contracts leave a concrete ambiguity or incompatibility;
3. the ambiguity causes a correctness, interoperability, recovery, or evidence problem rather than merely verbose adapter code;
4. the proposed contract removes that ambiguity without hiding backend capability differences;
5. PAMA remains the authority boundary;
6. lifecycle/currentness remains authoritative for semantic state;
7. physical storage remains replaceable.

## What would justify a stronger engine

A stronger memory-native logical engine requires evidence beyond a repeated envelope.

At minimum it would need to prove that existing module + profile composition cannot faithfully provide one or more of:

- cross-module atomic logical transitions;
- durable conflict/reconciliation semantics independent of backend behavior;
- recovery/replay semantics that must be uniform for correctness;
- shared logical versioning that cannot safely remain adapter-owned;
- lifecycle closure spanning several physical modules in one governed transaction;
- another recurring cross-substrate requirement demonstrated by implementation rather than intuition.

No such gap is established yet.

## Next evidence stage

The next #276 stage should run the matched scenarios in `logical-state-algebra-scenarios.json` against existing reference harnesses and the first #274 module implementations.

The primary question is not whether each backend can perform CRUD. It is:

> Where, if anywhere, does the existing Agent Memory contract fail to express the same logical consequence without backend-specific semantic leakage?

## ADR promotion gate

Do not create a canonical ADR while `no_new_algebra` remains sufficient.

An ADR is justified only after a generic missing primitive survives cross-substrate execution and adversarial review. A no-new-ADR result is a successful research result, not an unfinished one.
