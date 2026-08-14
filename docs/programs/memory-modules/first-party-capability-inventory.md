# First-Party Memory Capability Inventory

Status: **initial evidence-bounded inventory**

Program issues: #284, #285, #286, #287, #288, #290, #291, #292, #293

## Purpose

Agent Memory must not classify a first-party subsystem by one convenient headline capability.

EvolveAI and CodeGenome are both **multi-capability memory subsystems**. Their differentiators remain useful, but those differentiators are not mutually exclusive module types.

The governing relationship is:

```text
component identity
!= capability identity

one component -> many capabilities
one capability -> many possible components
```

Agent Memory should compose against explicit capability contracts while preserving the identity, version, provenance, failure posture, and maturity of the component implementing each capability.

## Evidence boundary

This inventory is pinned to:

- **EvolveAI:** `7cd42412ceed2ab638249a1517b2a6dac46f1312`
- **CodeGenome:** `d2578729a46d495369bd7613845002d50cf20f4c`

The inventory is intentionally conservative. It distinguishes documentation/design intent from code existence, supported runtime reachability, and Agent Memory conformance.

## Maturity vocabulary

| Maturity | Meaning |
|---|---|
| `declared` | The repository documents or designs the capability. Runtime implementation is not established by this label. |
| `implemented` | Material implementation code exists at the pinned revision. This does not prove the capability is reachable through the supported runtime/product path. |
| `runtime_wired` | The capability is reachable through a supported runtime/product path at the pinned revision, subject to the listed limitations. |
| `evidence_proven` | Reproducible evidence demonstrates the claimed behavior against an explicit fixture or acceptance contract. |
| `reference_qualified` | The capability has satisfied the applicable Agent Memory component/capability conformance profile. |

Maturity is attached to a **capability**, not inherited from a repository-wide product status.

## Capability vocabulary posture

The names below are working capability-family labels for inventory purposes. Issue #291 owns the canonical vocabulary.

In particular:

```text
graph storage
!= graph traversal
!= graph candidate retrieval
!= GraphRAG / graph-augmented context assembly

vector storage
!= vector similarity
!= vector candidate retrieval
```

This avoids both common errors: calling every graph-backed system GraphRAG, and pretending a system has no GraphRAG architecture merely because graph retrieval is one capability among many.

## EvolveAI inventory

Pinned source: https://github.com/MythologIQ-Labs-LLC/EvolveAI/tree/7cd42412ceed2ab638249a1517b2a6dac46f1312

EvolveAI's current README describes a tri-layer system with L1 transient cache, L2 temporal graph, and L3 UOR vault. Its Autopoietic Memory Theory explicitly describes L2 as a **GraphRAG knowledge graph with vector embeddings**. The active Rust rewrite contains an L2 weighted temporal graph and a query path that performs exact L3 content-addressed lookup or vector scan across L1/L2/L3.

The repository review also records important implementation-maturity gaps: the default reachable embedding engine is mock-based, real embeddings are not yet wired into the supported product path, lifecycle/Shadow Genome subsystems are implemented but not integrated into normal runtime execution, and automatic consolidation/pruning/persistence behavior remains incomplete.

| Capability family | Maturity | Evidence / current posture | Agent Memory note |
|---|---|---|---|
| transient/cache memory | `runtime_wired` | L1 transient cache is part of the active Rust tri-layer runtime. | Candidate storage/cache capability, not authority. |
| temporal graph storage | `runtime_wired` | `crates/evolve-core/src/tiers/l2_graph.rs` stores memory nodes and weighted timestamped edges. | Strong candidate temporal/associative graph capability. |
| graph traversal / association | `implemented` | Active L2 graph exposes neighbor/edge traversal primitives. The supported query path does not currently use graph traversal as its main retrieval assembly path. | Do not claim end-to-end GraphRAG from graph storage alone. |
| GraphRAG / graph-augmented context assembly | `declared` | The theory explicitly specifies an L2 GraphRAG knowledge graph with vector embeddings and GraphRAG Top-K retrieval. Current Rust query code instead performs vector scan across tier candidates; a complete graph-augmented assembly path is not established by this inventory. | Foundational design capability requiring runtime qualification under #292. |
| vector representation | `runtime_wired` with material limitation | The active query path encodes query/content representations, but the repository review states the reachable default engine is `MockEngine`; real embedding support is not yet wired through the supported product path. | Capability exists, semantic retrieval quality is not yet production-grade evidence. |
| vector candidate retrieval | `runtime_wired` with material limitation | `crates/evolve-core/src/processor/query.rs` performs a vector scan across tier candidates and decoder scoring. Default embeddings remain mock-derived. | Agent Memory must record engine/version and must not equate similarity with admission. |
| exact/content-addressed retrieval | `runtime_wired` | Active query helper performs O(1) L3 exact match using UOR-derived content address. | Useful exact retrieval capability distinct from vector/graph retrieval. |
| tier routing | `runtime_wired` | L1/L2/L3 routing exists in the active memory pipeline; repository review notes MTS inputs remain simplistic in places. | Routing evidence must be separated from Agent Memory mutation authority. |
| temporal decay / weakening | `runtime_wired` | Decay-aware scoring/filtering participates in query behavior; repository review notes decay does not yet drive a complete GC/consolidation loop. | Good candidate lifecycle signal, not truth/authority. |
| consolidation / REM-style synthesis | `declared` / partial implementation | Central to the theory and lifecycle design; repository review says the active Rust runtime does not yet drive the complete lifecycle/consolidation loop. | Requires explicit runtime and provenance qualification. |
| lifecycle orchestration | `implemented` | Lifecycle orchestrator exists and is tested, but repository review says normal CLI/Tauri paths do not drive it. | Candidate capability below `runtime_wired`. |
| failure / negative memory (Shadow Genome) | `implemented` | Shadow Genome exists and is tested, but repository review says supported runtime paths do not meaningfully populate/use it yet. | May become failure-memory capability; must remain distinct from governance authority. |
| persistent snapshot/state | `runtime_wired` with limitation | Persistent state exists; repository review identifies snapshot-on-demand, missing robust auto-persistence/WAL, and migration/concurrency gaps. | Restart semantics require stronger evidence before Agent Memory can rely on it. |
| deletion / forget operation | `runtime_wired` | CLI exposes `forget`; L2 graph implementation supports node/edge removal. Derived-residue completeness remains a separate question. | Successful local deletion does not equal Agent Memory forgetting completeness. |
| learned/predictive representation | `declared` / partial | Representation engines and future real-embedding work exist; no reference-qualified predictive/world-model capability is established here. | Reuse prior JEPA/predictive-state evidence rather than inventing authority. |
| provenance / audit | `implemented` | Hash-chained ledger and accountable operation concepts are substantial parts of the repository. | Must be mapped to Agent Memory evidence contracts rather than assumed equivalent. |

### EvolveAI conclusion

The earlier label **"adaptive/lifecycle module"** describes a differentiator, not the subsystem's complete capability surface.

A more accurate summary is:

```text
EvolveAI
  transient/cache memory
  temporal graph memory
  graph/associative primitives
  GraphRAG-oriented architecture
  vector representation + retrieval
  exact content-addressed retrieval
  tier routing
  temporal decay
  lifecycle / consolidation mechanisms
  failure / negative memory
  persistence + audit mechanisms
```

The next task is to qualify each capability independently rather than promoting or demoting the repository as one indivisible unit.

## CodeGenome inventory

Pinned source: https://github.com/MythologIQ-Labs-LLC/CodeGenome/tree/d2578729a46d495369bd7613845002d50cf20f4c

CodeGenome describes itself as a **Unified Code Reality Graph**: a content-addressed multi-layer program-analysis graph merging syntax, semantics, control/data flow, process traces, runtime observations, and other overlays into one queryable substrate. The active workspace contains graph query/traversal, confidence fusion, signal propagation, MCP exposure, and experiment/evaluation capabilities.

It also contains embedding persistence plus cosine-similarity k-nearest-neighbor retrieval. That vector surface is real implementation, but the current evidence inspected here does not show it as the primary integrated product query path. CodeGenome should therefore not be reduced to "graph only," nor should its embedding helper be overstated as a mature general vector-RAG product path.

| Capability family | Maturity | Evidence / current posture | Agent Memory note |
|---|---|---|---|
| content-addressed code identity | `runtime_wired` | Core graph nodes use BLAKE3/UOR-style content identity across supported code evidence. | Domain identity can inform Agent Memory without becoming universal core identity doctrine. |
| multi-overlay graph storage | `runtime_wired` | Syntax, semantic, flow, process, PDG, runtime, SCIP and related overlays compose into the code reality graph. | Strong code-domain graph capability. |
| graph query / traversal | `runtime_wired` | Query/traversal and impact propagation are first-class product functions; current main includes directional impact traversal semantics. | Strong graph candidate/structural context capability. |
| graph-derived context / GraphRAG readiness | `implemented` / `runtime_wired` at graph-query substrate level | Graph traversal is operational and exposed to agents through query/MCP surfaces. A separately specified end-to-end GraphRAG generation/context-assembly contract is not established by this inventory. | Treat graph retrieval as real; qualify the exact GraphRAG/context-assembly claim under #293/#291. |
| embedding storage | `implemented` | `codegenome-substrate/src/embedding/store.rs` ingests, persists, and loads embedding vectors bound to addresses/models/timestamps. | Real vector representation storage capability. |
| vector similarity | `implemented` | `codegenome-substrate/src/embedding/similarity.rs` implements cosine similarity and k-nearest neighbors with tests. | Similarity is candidate evidence, not recall authority. |
| vector candidate retrieval product path | `implemented`, not established `runtime_wired` | k-NN exists in substrate/tests, but the inspected primary README/query surface centers graph query/traversal rather than integrated vector retrieval. | #293 should prove supported runtime exposure before stronger claim. |
| confidence/evidence fusion | `runtime_wired` | Multi-observer edge confidence fusion using noisy-OR is core architecture/product behavior. | Confidence must remain evidentiary, never canonical truth or mutation authority. |
| impact / blast-radius propagation | `runtime_wired` | Signal propagation and directional impact traversal are active product capabilities. | Strong code-domain reasoning/structural capability. |
| provenance / observer separation | `runtime_wired` | Graph artifacts retain observation/provenance distinctions; independent observers contribute evidence without individually becoming canonical. | Align with Agent Memory provenance/currentness contracts. |
| freshness / staleness modeling | `runtime_wired` | Freshness/staleness and propagation are explicit product concepts and roadmap evidence. | Useful derived-currentness evidence; Agent Memory remains admission authority. |
| multi-language extraction | `runtime_wired` | Rust, TypeScript/TSX, and Python share language-neutral extraction IR at pinned revision. | Domain capability, not Agent Memory core ontology. |
| MCP/agent exposure | `runtime_wired` | CodeGenome MCP server exposes governed read/write tools. | Candidate integration surface; MCP exposure itself is not Agent Memory conformance. |
| experiment / self-evaluation engine | `runtime_wired` | Product retains experiment engine, fitness functions, raw run records, and adaptive research loop. | Evaluation capability can improve implementation without self-authorizing memory mutations. |
| deletion / rebuild | `implemented` / evidence incomplete | Store/index lifecycle mechanics exist, but this inventory has not yet established Agent Memory-grade deletion-residue and rebuild conformance. | Must be tested explicitly under #293. |

### CodeGenome conclusion

The earlier label **"code-domain structural-memory module"** also describes a differentiator rather than the complete capability surface.

A more accurate summary is:

```text
CodeGenome
  content-addressed code identity
  multi-overlay graph storage
  graph query / traversal
  graph-derived context substrate
  embedding persistence
  vector similarity / k-nearest retrieval
  confidence/evidence fusion
  impact propagation
  freshness / provenance
  multi-language extraction
  MCP exposure
  experiment / self-evaluation
```

## Overlap is expected, not a defect

EvolveAI and CodeGenome overlap in several capability families:

| Capability family | EvolveAI | CodeGenome | Interpretation |
|---|---|---|---|
| graph state | temporal/associative memory graph | code-reality multi-overlay graph | Same broad capability family, materially different domain semantics. |
| graph retrieval/traversal | primitives implemented; full GraphRAG path not yet runtime-qualified | graph query/traversal is core runtime behavior | Do not force one implementation to replace the other merely because both use graphs. |
| vector representation | active but default mock engine limits semantic quality | embedding storage implemented | Both can legitimately expose representation capability at different maturity. |
| vector retrieval | active vector-scan path with mock-default limitation | k-NN implemented but not shown as primary product path | Overlap should be modeled explicitly, then selected by profile/routing policy. |
| content identity | UOR-backed exact durable memory | content-addressed code artifacts | Related exact-identity mechanisms at different semantic layers. |
| provenance/evidence | ledger/accountability orientation | multi-observer graph evidence | Both useful, neither automatically replaces Agent Memory provenance semantics. |
| self-adaptation/evaluation | lifecycle/autopoietic adaptation | adaptive experiment engine | Both may propose changes; neither gets Agent Memory authority from adaptation quality. |

The correct architecture therefore permits:

```text
same capability family
  -> several implementations
  -> different domains / costs / strengths / maturity
  -> deterministic profile selects one or composes several
```

Overlap is only a problem when canonical ownership, write authority, precedence, or currentness becomes ambiguous.

## Initial capability gaps to investigate

This first pass does **not** conclude that new first-party subsystems are required. It identifies capability families that should be tested for meaningful gaps under #284/#286:

- procedural / skill memory;
- multimodal memory;
- shared/federated memory across agents or organizations;
- learned latent / predictive / world-model memory beyond embeddings;
- explicit episodic/event history if current components do not satisfy the generic contract cleanly;
- archival/cold memory and long-retention economics;
- causal memory / explicit intervention models;
- specialized privacy-preserving or confidential-memory substrates;
- additional capability families exposed by external comparators.

For each gap, decide:

```text
extend EvolveAI
extend CodeGenome
implement generic semantics in Agent Memory core
compose existing components
adopt/wrap external implementation
create new first-party subsystem
defer
```

A blank matrix cell is not an argument for a new repository.

## Contract implication

RFC-001/#280 should evolve from an exclusive module-type model toward:

```text
component
  identity
  version
  deployment/failure metadata
  capabilities[]
      capability identity/version
      maturity
      canonical/derived posture
      scope/isolation posture
      read/write behavior
      evidence refs
      migration/rebuild/deletion behavior
```

Routing should request **capabilities with minimum maturity/posture requirements**, then deterministically choose or compose configured component implementations.

## Next work

- #285 corrects RFC/PRD/public architecture terminology.
- #287 defines machine-readable capability maturity declarations.
- #290 implements capability-based routing and overlap resolution.
- #291 establishes precise graph/vector/GraphRAG/hybrid vocabulary.
- #292 qualifies the EvolveAI capability profile.
- #293 qualifies the CodeGenome capability profile.
- #286 maps external implementations against the same capability rows.
- #289 decides whether existing first-party subsystem boundaries should be retained, shared, split, or complemented after evidence exists.
