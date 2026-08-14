# RFC-001: Governed Mutable Memory Fabric

Status: **Proposed**

## Summary

Agent Memory should be implemented as a governed memory fabric between an agent runtime and heterogeneous memory technologies, with external agent-governance systems remaining peer authorities.

Memory technologies participate as **components** that expose one or more independently described **capabilities**. Component identity and capability identity are distinct.

The long-term system boundary is:

```text
Agent Runtime
  acts, plans, invokes tools, requests memory
        |
        v
Agent Memory
  owns memory semantics, lifecycle, provenance, scope,
  structural mutability, mutation authority, recall admission,
  capability routing, and evidence
        |
        +--> configured components
        |       +--> capabilities[]
        |       +--> maturity/evidence per capability
        |
        v
Agent Governance peer(s)
  DashClaw / AGT / other approval, policy, enforcement systems
```

Agent Memory is not one graph database, RAG implementation, vector store, JEPA representation, file layout, or first-party product. Those technologies implement capabilities behind Agent Memory contracts.

## Goals

1. make memory representation and persistence configurable without changing Agent Memory doctrine;
2. allow several components and capability families to participate in one deployment simultaneously;
3. allow one component to expose many capabilities and one capability to have many candidate implementations;
4. allow routing by memory characteristics and capability requirements rather than hard-coding one technology to one retention tier;
5. treat first-party systems such as EvolveAI and CodeGenome as multi-capability candidate components, not privileged doctrine;
6. preserve external memory-system integrations under the same capability/governance boundary;
7. make structural adaptation possible without giving probabilistic systems authority over canonical memory shape;
8. keep Agent Runtime, Agent Memory, and Agent Governance as separately reasoned system boundaries.

## Non-goals

- selecting one universal storage engine;
- making short-, mid-, or long-term memory synonymous with a specific backend;
- forcing each component into one exclusive module type;
- merging every first-party repository into this repository as source code;
- making DashClaw, AGT, EvolveAI, CodeGenome, Graphiti, JEPA, GraphRAG, or any other implementation mandatory;
- allowing component-specific identity, confidence, ontology, or retrieval score to become canonical Agent Memory authority;
- defining a universal physical database schema;
- treating a declared capability as runtime-available merely because documentation mentions it.

## Architectural model

```text
                         AGENT MEMORY

  Runtime/API boundary
          |
          v
  memory classification + capability requirements
          |
          v
  PAMA / scope / lifecycle / provenance / authority
          |
          v
  canonical memory semantics + logical state
          |
          v
  deterministic component/capability resolution
          |
          +-------------------------------------+
          |                  |                  |
          v                  v                  v
     component A        component B        component C
      caps [x,y]         caps [y,z]         caps [w]
          |                  |                  |
          +------------------+------------------+
                             |
                             v
                   configured composition
                             |
                             v
                   governed recall/admission
                             |
                             v
                      Agent Runtime context
```

A component may implement several capabilities. A capability may be available from several components. Responsibilities, maturity, and provenance remain typed and inspectable.

## Component/capability model

The core invariant is:

```text
component identity != capability identity
```

A component declaration identifies the deployable implementation boundary. Capability declarations identify what that component claims to provide.

A component may expose, for example:

```text
EvolveAI
  temporal_graph
  vector_candidate_retrieval
  exact_retrieval
  lifecycle_decay
  consolidation

CodeGenome
  code_graph
  graph_traversal
  impact_analysis
  embedding_storage
  vector_similarity
```

The exact capability vocabulary is defined separately. Issue #291 owns the graph/vector/GraphRAG/hybrid terminology.

## Capability maturity model

Each capability declaration should carry an independent maturity state. Initial vocabulary:

```text
declared
implemented
runtime_wired
evidence_proven
reference_qualified
```

Meaning:

- `declared`: documented/intended architecture;
- `implemented`: material code exists;
- `runtime_wired`: reachable through a supported runtime/product path;
- `evidence_proven`: reproducible evidence demonstrates the claimed behavior;
- `reference_qualified`: applicable Agent Memory conformance profile is satisfied.

A component-wide release/version must not silently imply that every capability has the same maturity.

## Capability families

Capability families are composable roles, not exclusive product classes.

### Storage and persistence

Examples: files/Markdown, SQLite/Postgres, graph database, object store, event log, content-addressed vault.

Owns physical persistence mechanics. Does not own memory authority.

### Exact retrieval

Examples: content-addressed lookup, key-addressed lookup, deterministic indexed lookup.

Exact identity retrieval is distinct from semantic similarity.

### Vector representation and retrieval

Distinguish at least:

```text
vector representation/storage
vector similarity
vector candidate retrieval
```

Embeddings or cosine similarity alone do not prove a supported vector-retrieval product path.

### Graph and GraphRAG

Distinguish at least:

```text
graph storage
graph query/traversal
graph candidate retrieval
graph-augmented context assembly / GraphRAG
```

Graph existence does not prove end-to-end GraphRAG. GraphRAG also does not cease to be a valid component capability merely because the same component implements lifecycle, code analysis, or vector retrieval.

### Representation

Examples: embeddings, learned latent state, JEPA-style representations, summaries/compression.

Produces a representation or influence surface. Representation quality is not truth or authority.

### Structural/reasoning capability

Examples: code reality graphs, domain graph traversal, association engines, impact/blast-radius analysis.

May expose observed and inferred relationships with provenance/currentness. Reachability is not permission.

### Lifecycle/maintenance capability

Examples: decay, weakening, reinforcement signals, consolidation, synthesis, archive/prune candidacy.

May propose lifecycle consequences. Maintenance signals do not self-authorize durable mutation.

### Complete memory-system integration

A first- or third-party memory service may expose several capability families simultaneously. Imported state is not automatically admitted, trusted, or authorized.

## First-party integrated subsystems

EvolveAI and CodeGenome are first-party candidate components. Neither should be reduced to one exclusive module category.

At the initial #284 inventory boundary:

```text
EvolveAI
  spans temporal graph, vector retrieval, exact retrieval,
  tiering, lifecycle/decay, consolidation, failure memory,
  persistence/audit, and GraphRAG-oriented design

CodeGenome
  spans graph storage/traversal, graph-derived code context,
  impact analysis, embedding storage, vector similarity,
  confidence/evidence fusion, provenance, MCP exposure,
  and experiment/evaluation
```

Capabilities are at different maturity levels. The pinned inventory is:

`docs/programs/memory-modules/first-party-capability-inventory.md`

First-party ownership changes packaging and maintenance posture, not authority semantics or maturity.

## Memory tiers are policy characteristics, not backends

The architecture MUST NOT define:

```text
short-term = Markdown
mid-term = JEPA
long-term = graph
```

Instead routing evaluates memory characteristics such as:

```text
retention horizon
scope / tenant / isolation domain
sensitivity
current lifecycle state
reversibility
retrieval pattern
relationship density
exactness requirements
latency / cost budget
availability / offline constraints
rebuild cost
provenance requirements
```

These characteristics produce **capability requirements**, not product names.

A profile may then resolve required capabilities to one or several configured components.

Illustrative profile:

```yaml
working:
  requires:
    - capability: ephemeral_storage
    - capability: lexical_retrieval

episodic:
  requires:
    - capability: event_storage
    - capability: vector_candidate_retrieval

durable_project:
  requires:
    - capability: canonical_persistence
    - capability: graph_candidate_retrieval
    - capability: exact_retrieval
```

These names are illustrative, not canonical configuration keys.

## Canonical versus derived state

Every capability instance MUST declare whether it stores or produces:

- canonical memory state;
- historical evidence;
- derived projection/index state;
- learned/latent influence state;
- cache/ephemeral state.

A single component may have different postures for different capabilities.

Derived or physical state MUST remain rebuildable or explicitly non-rebuildable. Component replacement MUST NOT silently change canonical logical identity, provenance, lifecycle, scope, or currentness.

## Structural mutability

ADR-032 governs structural adaptation.

The fabric may discover and propose new memory shapes at runtime. Structural proposals may come from learned systems, domain components, workload pressure, or deterministic maintenance observations.

Commit authority is separate:

```text
probabilistic / learned discovery
  -> structural proposal
  -> deterministic semantic + dependency + migration analysis
  -> deterministic governance classification
  -> autonomous bounded commit OR explicit human decision
```

No confidence score, embedding similarity, learned utility estimate, or model recommendation can directly authorize canonical structural mutation.

## Component declaration contract

A component profile should expose at least:

```text
component_id
implementation_ref
component_version
configuration_version
deployment posture
failure / unavailable posture
dependency + license metadata
observability / evidence hooks
capabilities[]
```

Each capability declaration should expose at least:

```text
capability_id
capability_version
maturity
maturity_evidence_refs
canonical_or_derived_posture
supported scopes / isolation behavior
read / write / candidate behavior
currentness / invalidation semantics
correction / supersession behavior
deletion / residue behavior
migration / rebuild behavior
failure behavior when capability-specific
structural mutation requirements
```

Unsupported or incompatible configurations must fail deterministically rather than degrade into guessed behavior.

## Capability resolution and routing contract

Routing itself is not authority.

A route should conceptually resolve:

```text
memory characteristics
  -> required capabilities
  -> minimum maturity + posture constraints
  -> matching configured component capability instances
  -> deterministic selection/composition
```

A router MAY use learned or heuristic signals to recommend candidate capabilities or implementations, but any routing consequence that changes canonical durability, scope, authority, lifecycle, or structural semantics must pass normal governance.

When several components provide the same capability, configuration MUST define precedence, composition, or an explicit ambiguity failure. Hidden registration order or first-match behavior is unacceptable.

Fallback MUST NOT silently lower required maturity, scope/isolation guarantees, or canonical/derived requirements.

Low-impact placement or derived-projection choices may be automatic when a versioned deterministic profile explicitly allows them.

## Agent Governance boundary

Agent governance remains a peer system, not a memory substrate.

```text
Agent Memory
  -> memory-specific proposal/verdict/context evidence
  -> governance adapter
  -> DashClaw / AGT / other governance peer
```

External governance may tighten a consequence or supply approval/enforcement evidence. It does not redefine Agent Memory semantics, and returned approval does not become reusable standing memory authority.

The DashClaw #219/#279 integration is the first concrete proof of this peer boundary.

## Acceptance scenario

The first minimal fabric should prove a cross-session project-memory workload:

1. Agent Runtime learns a project fact.
2. Agent Memory classifies and proposes durable promotion.
3. DashClaw governs the consequential mutation through the external-verdict seam.
4. Agent Memory independently revalidates and commits through its governed mutation path.
5. A later session recalls the memory and changes behavior because of it.
6. A correction is proposed, reviewed, approved, committed, and supersedes the old current value.
7. A later session uses the corrected value.
8. stale approval, scope widening, and cross-tenant recall fail.
9. evidence distinguishes decision, approval, mutation, lifecycle, and recall.
10. the report states whether process-restart durability was proven or only cross-session reuse.
11. the same behavioral contract can be rerun with a different component/capability composition.

## Open design questions

- should capability composition be static per deployment, dynamically resolved per memory, or both;
- which canonical state surfaces may be shared across several writable capability implementations without introducing dual authority;
- how component migration and shadow/canary operation should work;
- which structural S1 changes deserve an autonomous PAMA envelope;
- how first-party components are packaged: libraries, processes, sidecars, or remote services;
- how restart-safe governance metadata is reconstructed independently from a physical substrate;
- which conformance levels are required before a capability can be called reference-qualified;
- when overlap between EvolveAI and CodeGenome should remain domain-specialized versus move to a shared component;
- whether any uncovered capability family justifies a new first-party subsystem after #284/#286.

## Relationship to current work

- #274 owns the modular-memory program.
- #275 evaluates first-party capabilities against external peers.
- #276 currently finds no need for a new universal logical-state algebra in the tested scenarios.
- #279 proves the Agent Memory <-> Agent Governance peer seam against DashClaw.
- #280 implements the common component/capability contract and routing fabric.
- #284 inventories EvolveAI/CodeGenome capability coverage and gaps.
- #285 corrects the architecture taxonomy to capability-oriented composition.
- #286 maps external capability coverage.
- #287 implements capability maturity declarations.
- #289 decides first-party subsystem boundaries after overlap analysis.
- #290 implements capability-based selection and overlap resolution.
- #291 defines precise graph/vector/GraphRAG/hybrid capability vocabulary.
- #292 and #293 qualify EvolveAI and CodeGenome capabilities respectively.
- ADR-032 defines structural mutation authority and schema lifecycle.

## Proposed implementation sequence

1. freeze capability vocabulary and component/capability declaration contracts;
2. implement machine-readable capability maturity and deterministic overlap resolution;
3. build the minimal configurable Agent Memory instance around existing reference components;
4. prove the DashClaw governed durable-memory scenario;
5. make governance metadata restart-safe;
6. qualify at least two materially different capability compositions under the same acceptance contract;
7. qualify EvolveAI and CodeGenome capability-by-capability;
8. compare external alternatives against the same capability matrix;
9. decide whether any missing capability justifies extending an existing subsystem, adopting an external implementation, extracting a shared component, or creating a new first-party subsystem.
