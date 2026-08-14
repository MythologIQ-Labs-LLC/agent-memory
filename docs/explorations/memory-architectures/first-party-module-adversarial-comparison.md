# First-Party Module Adversarial Comparison

Status: **active exploratory research** for #275. This document is not canonical doctrine and does not grant reference-module status to any implementation.

## Decision boundary

The purpose of this work is to test whether the strongest first-party Agent Memory implementation candidates deserve a defined module responsibility after comparison with materially relevant external peers.

The governing rule is deliberately unfriendly to portfolio favoritism:

```text
first-party ownership
!= architectural superiority
!= Agent Memory conformance
!= reference-module status
!= canonical doctrine
```

A first-party implementation must survive the same source pinning, falsification, currentness, correction, deletion, scope, authority, failure, and evidence requirements applied to an external implementation.

## Exact evidence pins for the first comparison slice

| System | Role in this research | Exact source pin | License posture | Evidence status |
|---|---|---|---|---|
| EvolveAI | first-party adaptive/autopoietic-memory candidate | `MythologIQ-Labs-LLC/EvolveAI@7cd42412ceed2ab638249a1517b2a6dac46f1312` | Apache-2.0 | implementation observed from source/docs; executable Agent Memory conformance not yet established |
| CodeGenome | first-party code-domain structural-memory candidate | `MythologIQ-Labs-LLC/CodeGenome@b498b80959f52a2eb37724e5b1c56ddcf68d3c7f` | MIT | implementation observed from source/docs; executable Agent Memory conformance not yet established |
| Hindsight | EvolveAI comparator | `vectorize-io/hindsight@41b292e5747c8e87040c65bc0e32429cb5e6ba21` | MIT | implementation observed from source/docs; vendor benchmark claims are not accepted as reproduced evidence here |
| MemOS | EvolveAI comparator | `MemTensor/MemOS@f4db521214c29337164ec788bafede7eab236c25` | Apache-2.0 | implementation observed from source/docs; benchmark claims remain separate until reproduced |
| GitNexus | CodeGenome comparator | `abhigyanpatwari/GitNexus@28187bb3a70840998cbe760f8bef3655c113156c` | **PolyForm Noncommercial 1.0.0** | implementation observed from source/docs; comparator-only unless rights analysis supports a narrower use |
| Graphify | CodeGenome comparator | `Graphify-Labs/graphify@7fe58b0b0f3873be9a21c30106b8b8527c353aa6` | Apache-2.0 at root `LICENSE` | implementation observed from source/docs; benchmark claims remain separate until reproduced |

The pins above establish what was reviewed. They do not freeze later executable comparison work to these exact heads if a newer release is selected deliberately and recorded before execution.

## Lane A: EvolveAI

### Current first-party shape

At the pinned revision, EvolveAI describes itself as an autopoietic memory system implemented primarily in Rust. The active core exposes:

- a thermodynamic/decay-oriented memory model;
- a hash-chained audit ledger;
- a persistent CLI state path;
- lifecycle phases `GROUNDING -> SEMANTIC_PAUSE -> ACTIVE_FLOW -> DETACHMENT -> REM_SYNTHESIS`;
- L1 transient, L2 temporal-graph, and L3 vault tiers;
- CMHL lazy decay;
- a Memory Tier Score (MTS);
- Shadow Genome failure-pattern matching;
- explicit Agent Memory alignment with implementation maturity still labeled `declared` and no conformance evidence yet.

That last point matters. The repository itself already states the correct maturity boundary, so #275 must measure rather than upgrade the claim by enthusiasm.

### Immediate architectural strengths

**1. Memory metabolism is first-class rather than bolted onto retrieval.**

Decay, tier movement, detachment, REM-style synthesis, dispute, feedback, and crystallization are explicit operational concepts. This gives EvolveAI a genuinely different comparison surface from a simple vector memory wrapper.

**2. Local-first operation is architecturally serious.**

The system is not designed around a mandatory hosted memory service. That makes it a useful deployment-profile comparator for Agent Memory local/single-user and offline-first goals.

**3. Negative/failure memory has an explicit implementation surface.**

Shadow Genome gives EvolveAI a concrete place to model remembered failure patterns rather than allowing positive successful history to dominate the memory model by default.

**4. Auditability is part of the product thesis.**

The hash-chained ledger and explicit lifecycle operations give #275 something concrete to test against Agent Memory evidence and maintenance-run requirements.

### Immediate pressure points

#### E1. `L3 = immortal` conflicts with Agent Memory forgetting doctrine if interpreted literally

EvolveAI currently describes the L3 vault with zero decay and an `immortal` characteristic. That can be a storage/retention policy, but it cannot become a semantic guarantee that L3 state is exempt from correction, revocation, scope change, user-directed deletion, or lifecycle invalidation.

Required test:

```text
memory reaches L3
-> source later corrected / revoked / deletion-authorized
-> physical durability may remain historically evidenced
-> current influence and forgetting obligations still change
```

If EvolveAI cannot express that distinction, the tier model needs revision before reference-module promotion.

#### E2. MTS may be mixing placement inputs with governance-significant inputs

The documented Memory Tier Score uses sensitivity, accuracy requirement, privilege level, and compute constraint to choose L1/L2/L3 placement.

That is potentially useful as a placement estimator, but the following must remain false:

```text
high sensitivity / privilege score
-> stronger epistemic status
-> stronger authority
-> automatic crystallization
```

Sensitivity and privilege may justify stricter handling. They cannot make content more true or more authorized.

#### E3. CMHL access-sensitive decay creates a feedback-loop risk

Decay based on time since access can make frequently retrieved material persist longer. That is operationally plausible but governance-sensitive because retrieval frequency can be manipulated or recursively self-reinforced.

Required adversarial case:

```text
stale or wrong memory
-> repeatedly retrieved by the agent itself
-> effective retention pressure increases
```

Expected Agent Memory boundary:

```text
access frequency != independent corroboration
access frequency != truth
access frequency != authority
```

#### E4. Shadow Genome cannot own `PASS/BLOCK` authority solely from semantic similarity

The pinned README describes cosine-similarity matching against failure traces and a `PASS` / `BLOCK` verdict surface. EvolveAI's own backlog identifies a deterministic policy gate as future work.

For Agent Memory alignment, the safe shape is:

```text
failure-pattern similarity
-> risk / precedent evidence
-> deterministic policy / PAMA consequence
-> permitted action set
```

not:

```text
cosine similarity
-> authoritative block/allow
```

A high-quality negative-memory estimator is valuable. An estimator that silently becomes the authority boundary is not.

### Comparator: Hindsight

At the pinned revision Hindsight exposes a materially different but overlapping memory model:

- memory banks;
- `retain`, `recall`, and `reflect` operations;
- explicit separation among world facts, experiences, and mental models;
- entity/relationship/time-series representations combined with sparse/dense retrieval;
- metadata-based memory isolation/filtering;
- reflection that derives new observations/insights from retained material;
- server, client, and embedded deployment paths.

#### What Hindsight pressures in EvolveAI

1. **Mental-model derivation vs REM synthesis.** Both systems derive higher-order memory from lower-level experience. #275 should compare lineage, correction propagation, negative evidence retention, and derived-state currentness rather than merely comparing output quality.
2. **Experience/world distinction vs tier distinction.** Hindsight separates memory by semantic role; EvolveAI emphasizes lifecycle/storage tiers. These are orthogonal dimensions. EvolveAI may need semantic memory classes without conflating them with persistence tier.
3. **Bank isolation vs Agent Memory isolation domains.** Hindsight offers a practical isolation mechanism that can pressure-test whether EvolveAI scope is currently explicit enough.
4. **Reflect vs authority.** Hindsight reflection is a strong comparator for REM synthesis because derived mental models must remain derived evidence, not self-certifying truth.

Hindsight's benchmark and production claims are useful leads, not imported evidence. Reproduction remains a separate step.

### Comparator: MemOS

At the pinned revision MemOS exposes an especially direct architectural challenge:

- one API for add/retrieve/edit/delete memory;
- graph-structured inspectable memory;
- multi-modal memory;
- multiple composable memory cubes for isolation and sharing;
- asynchronous memory scheduling;
- natural-language feedback/correction;
- local and hosted deployment profiles;
- local-plugin work describing L1 traces, L2 policies, L3 world models, and crystallized skills;
- hybrid FTS/vector retrieval in local-plugin paths.

#### What MemOS pressures in EvolveAI

1. **Tier vocabulary collision.** MemOS also uses L1/L2/L3-style structures, but with different meanings. Agent Memory must not normalize either product's tier labels into canonical semantics.
2. **Skill memory.** MemOS treats crystallized skills as a first-class memory outcome. EvolveAI needs evidence that REM synthesis can preserve procedural/skill-like state distinctly from ordinary facts and summaries if it wants the same operational territory.
3. **Memory-cube isolation.** MemOS has an explicit user/project/agent composition story. EvolveAI's module promotion should require an equally explicit isolation contract rather than relying on local process boundaries.
4. **Correction as a product operation.** MemOS exposes correction/update as a first-class user surface. EvolveAI should demonstrate correction/supersession semantics independently from decay and dispute.
5. **Scheduler vs autonomous metabolism.** MemOS scheduling pressures EvolveAI's autonomous maintenance posture. The deciding question is not which scheduler is richer, but whether background maintenance remains transactional, currentness-aware, and non-self-authorizing.

### Preliminary EvolveAI verdict

Current recommendation: **retain as a first-party module candidate; do not promote beyond `declared` yet.**

The distinctive value is real: explicit metabolism, local-first operation, decay, lifecycle phases, and failure-memory handling are not redundant with simple retrieval systems. The strongest risks are also real: immortal-tier semantics, access-feedback reinforcement, placement/governance signal mixing, and estimator-shaped block/allow behavior.

The first executable EvolveAI slice should therefore test lifecycle correctness, not generic recall accuracy.

## Lane B: CodeGenome

### Current first-party shape

At the pinned revision CodeGenome describes a content-addressed multi-layer program-analysis graph with:

- BLAKE3-based node addressing;
- syntax, semantic, control/data-flow, process, PDG, runtime, SCIP, and LSP overlay concepts;
- confidence-bearing edges;
- Noisy-OR confidence fusion;
- impact/staleness propagation;
- Rust, TypeScript, and Python language extraction at the pinned first-party revision;
- an adaptive experiment engine;
- MCP access;
- explicit research-prototype status;
- Agent Memory alignment as code-domain evidence/graph structure rather than general memory authority.

### Immediate architectural strengths

**1. Observer separation is explicit.**

Tree-sitter, runtime traces, compiler indexes, semantic resolution, and other mechanisms contribute observations rather than each becoming the truth model. This fits Agent Memory's source-neutral evidence posture well.

**2. Provenance and evidence are core product concerns.**

CodeGenome's claim that capabilities must trace to retained experimental evidence is unusually aligned with Agent Memory's evidence discipline.

**3. Program-analysis depth is more than code search.**

Control/data flow, PDG, process traces, runtime overlays, and impact propagation provide a richer structural-memory surface than lexical or embedding retrieval alone.

**4. The experiment engine creates falsifiable self-improvement evidence.**

The system has an explicit mechanism for measuring structural changes rather than relying only on subjective developer impressions.

### Immediate pressure points

#### C1. Content address cannot become logical code-memory identity

CodeGenome describes graph nodes as identified by BLAKE3 content. That is useful for immutable content identity, but Agent Memory already preserves:

```text
content identity != logical memory identity
```

A symbol can retain logical continuity while its content changes; two identical code fragments can have different repository/scope/semantic identities. #275 must test whether CodeGenome can preserve logical lineage above content-addressed snapshots.

#### C2. `the graph is canonical` is too broad for Agent Memory module promotion

For CodeGenome itself, a canonical code-reality graph may be a coherent product choice. Within Agent Memory, however, graph state can contain both observed and inferred relationships and must remain domain-specific.

The safe integration boundary is closer to:

```text
CodeGenome graph
= canonical CodeGenome domain state
= Agent Memory evidence / derived structural-memory module
!= canonical ontology for all Agent Memory
```

#### C3. Noisy-OR requires explicit dependence handling

CodeGenome fuses edge confidence via Noisy-OR. The mechanism is useful only when its independence assumptions are honest enough for the evidence being fused.

The existing Agent Memory autonomous-maintenance research already establishes:

```text
confidence fusion != truth
repeated / correlated evidence != independent corroboration
```

#275 must check whether CodeGenome tracks shared evidence roots strongly enough to avoid confidence inflation from correlated observers.

#### C4. First-party language breadth is currently a competitive weakness

The pinned first-party README states three language families. Both external comparator lanes now cover broader language surfaces. Language count is not a doctrine metric, but it directly affects usefulness as a code-domain structural-memory module.

### Comparator: GitNexus

At the pinned revision GitNexus exposes a broad code-intelligence implementation with:

- tree-sitter-based indexing;
- a persistent knowledge graph;
- dependency, call-chain, cluster, and execution-flow analysis;
- MCP tools for context, impact, traces, change detection, structural checks, raw graph queries, API impact, PDG queries, and taint findings;
- hybrid BM25/semantic retrieval where enabled;
- incremental branch/worktree indexing;
- explicit staleness surfaces;
- significant multi-language import-resolution work;
- a current **PolyForm Noncommercial 1.0.0** license.

#### What GitNexus pressures in CodeGenome

1. **Language and ecosystem breadth.** GitNexus currently demonstrates that broad code-graph coverage and sophisticated resolution are no longer hypothetical differentiators.
2. **Impact tooling.** GitNexus exposes blast-radius and pre-change analysis directly to agents, overlapping CodeGenome's impact thesis.
3. **PDG / taint / structural checks.** CodeGenome cannot claim unique program-analysis depth merely because it has control/data-flow overlays; GitNexus has moved into adjacent territory.
4. **Import correctness as graph integrity.** GitNexus's recent work explicitly treats fabricated import edges as a correctness defect. This is an excellent adversarial standard for CodeGenome: false high-confidence structural edges are memory poisoning, not harmless recall noise.

### Licensing stop line for GitNexus

GitNexus is valuable as a comparator, but its PolyForm Noncommercial license makes it a poor candidate for copied implementation or an embedded dependency in a commercial first-party product without separate rights analysis.

For #275:

```text
observe / execute where legally permitted
compare behavior and architecture
cite primary source
!= copy implementation
!= import code into Apache-2.0 Agent Memory
!= assume commercial redistribution rights
```

### Comparator: Graphify

At the pinned revision Graphify exposes:

- local deterministic tree-sitter parsing for code;
- a persisted queryable knowledge graph;
- explicit `EXTRACTED` vs `INFERRED` edge classification;
- cross-file calls/imports/inheritance across a broad language set;
- graph query/path/explain workflows;
- rationale and ADR/RFC references as first-class graph nodes;
- incremental update behavior;
- code-local operation without a mandatory vector store;
- an Apache-2.0 root license.

#### What Graphify pressures in CodeGenome

1. **Observed vs inferred edge semantics.** Graphify's simple explicit distinction is a useful baseline. CodeGenome's confidence model must prove it adds value beyond classification without obscuring provenance.
2. **Language breadth with simpler architecture.** If Graphify can satisfy common agent code-understanding tasks with deterministic AST graphs across many languages, CodeGenome's extra overlays must justify their complexity through matched outcomes.
3. **Rationale nodes.** Treating architectural rationale/ADR references as graph state is a strong code-memory capability that CodeGenome should compare directly.
4. **No-vector baseline.** Graphify offers a useful control for testing whether embeddings or richer fusion actually improve the code-domain tasks under study.

### Preliminary CodeGenome verdict

Current recommendation: **retain as a first-party code-domain structural-memory candidate; do not treat current graph identity or graph ontology as Agent Memory canonical state.**

CodeGenome's strongest differentiators are not language count or generic graph retrieval. They are the evidence-generating experiment engine, explicit observer/fusion model, runtime/program-analysis overlays, and the possibility of binding structural conclusions to retained evidence.

Its largest competitive problem is that GitNexus and Graphify now cover substantial portions of the code-graph/query/impact surface. #275 therefore needs to prove that CodeGenome's additional complexity produces better structural correctness, provenance, update behavior, or agent task outcomes rather than merely more overlay names.

## Cross-lane findings that already matter to #276

This first comparison slice produces an important state-model result.

The competing systems disagree heavily about physical representation and product ontology:

```text
EvolveAI    -> lifecycle tiers + temporal graph + vault
Hindsight   -> world + experiences + mental models in memory banks
MemOS       -> graph memory + cubes + scheduler + retrieval + skills
CodeGenome  -> content-addressed multi-overlay code graph
GitNexus    -> persistent code knowledge graph + precomputed intelligence
Graphify    -> deterministic extracted/inferred knowledge graph
```

Yet the governance questions repeat almost unchanged:

```text
what is the stable logical identity?
what is observed vs derived?
what is current after correction?
what survives deletion?
what scope may influence recall?
what evidence supports a derived state?
what does an estimator merely propose?
what authority permits a durable consequence?
```

That repetition is evidence **for a shared logical contract**, but not yet evidence that Agent Memory needs a new storage engine or new state algebra. #276 should test whether existing Agent Memory primitives already cover the repeated questions before adding another abstraction.

## Next executable comparison slice

The next #275 work should use matched fixtures rather than product-native demos.

### EvolveAI/Hindsight/MemOS

Run equivalent cases for:

1. correction after derived mental-model/summary state exists;
2. source revocation while derived state remains useful;
3. repeated access to a stale memory;
4. cross-user/project high-relevance recall;
5. autonomous consolidation with one required invariant lost;
6. deletion with one residual index/graph/summary representation.

### CodeGenome/GitNexus/Graphify

Run equivalent cases for:

1. symbol content changes while logical symbol continuity should survive;
2. false import/call edge generated by ambiguous resolution;
3. corrected source leaves stale inferred edge/path;
4. two correlated observers inflate one relationship;
5. cross-repository/scope collision or contamination;
6. changed-file impact query with known ground-truth downstream dependents.

## Promotion rule

No implementation is promoted beyond `declared` from this document alone.

A stronger status requires executable evidence that survives the matched negative paths and then maps cleanly to the #274 module/profile contract without importing product-specific ontology into Agent Memory core.
