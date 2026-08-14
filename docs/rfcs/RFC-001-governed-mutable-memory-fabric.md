# RFC-001: Governed Mutable Memory Fabric

Status: **Proposed**

## Summary

Agent Memory should be implemented as a governed memory fabric between an agent runtime and heterogeneous memory technologies, with external agent-governance systems remaining peer authorities.

The long-term system boundary is:

```text
Agent Runtime
  acts, plans, invokes tools, requests memory
        |
        v
Agent Memory
  owns memory semantics, lifecycle, provenance, scope,
  structural mutability, mutation authority, recall admission,
  module routing, and evidence
        |
        +--> configured memory modules / substrates
        |
        v
Agent Governance peer(s)
  DashClaw / AGT / other approval, policy, enforcement systems
```

Agent Memory is not one graph database, RAG implementation, vector store, JEPA representation, file layout, or first-party product. Those technologies are modules behind Agent Memory contracts.

## Goals

1. make memory representation and persistence configurable without changing Agent Memory doctrine;
2. allow several module types to participate in one deployment simultaneously;
3. allow routing by memory characteristics rather than hard-coding one technology to one retention tier;
4. treat first-party systems such as EvolveAI and CodeGenome as candidate modules, not privileged doctrine;
5. preserve external memory-system adapters as optional modules under the same governance boundary;
6. make structural adaptation possible without giving probabilistic systems authority over canonical memory shape;
7. keep Agent Runtime, Agent Memory, and Agent Governance as separately reasoned system boundaries.

## Non-goals

- selecting one universal storage engine;
- making short-, mid-, or long-term memory synonymous with a specific backend;
- merging every first-party repository into this repository as source code;
- making DashClaw, AGT, EvolveAI, CodeGenome, Graphiti, JEPA, GraphRAG, or any other implementation mandatory;
- allowing module-specific identity, confidence, or ontology to become canonical Agent Memory authority;
- defining a universal physical database schema.

## Architectural model

```text
                         AGENT MEMORY

  Runtime/API boundary
          |
          v
  memory classification + routing
          |
          v
  PAMA / scope / lifecycle / provenance / authority
          |
          v
  canonical memory semantics + logical state
          |
          +-------------------------------+
          |               |               |
          v               v               v
   storage modules   retrieval modules   representation modules
          |               |               |
          +-------+-------+-------+-------+
                  |               |
                  v               v
          reasoning/graph      lifecycle/maintenance
             modules               modules
                  \               /
                   \             /
                    configured composition
                          |
                          v
                governed recall/admission
                          |
                          v
                   Agent Runtime context
```

Modules may implement more than one capability, but their responsibilities must remain typed and inspectable.

## Module taxonomy

A deployment MAY configure modules in one or more of these roles:

### Storage substrate

Examples: files/Markdown, SQLite/Postgres, graph database, object store, event log.

Owns physical persistence mechanics. Does not own memory authority.

### Retrieval/index module

Examples: lexical search, vector search, GraphRAG retrieval, code-graph traversal.

Produces candidates. Candidate rank is not recall permission.

### Representation module

Examples: embeddings, learned latent state, JEPA-style representations, summaries/compression.

Produces a representation or influence surface. Representation quality is not truth or authority.

### Structural/reasoning module

Examples: CodeGenome-style code reality graphs, domain graph traversal, association engines.

May expose observed and inferred relationships with provenance/currentness. Reachability is not permission.

### Lifecycle/maintenance module

Examples: EvolveAI-style decay, weakening, consolidation, synthesis, archive/prune candidacy.

May propose lifecycle consequences. Maintenance signals do not self-authorize durable mutation.

### Complete external memory-system adapter

Wraps a third-party memory service behind the Agent Memory contract. Imported state is not automatically admitted, trusted, or authorized.

### First-party integrated subsystem

A first-party implementation such as EvolveAI or CodeGenome may implement one or more module roles after conformance evidence. First-party ownership changes packaging and maintenance posture, not authority semantics.

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

A profile may then route one memory to one or several modules.

Example deployment profile:

```yaml
working:
  storage: [markdown, local_kv]
  retrieval: [lexical]

episodic:
  storage: [event_store]
  representation: [latent_state]
  retrieval: [vector]

durable_project:
  storage: [canonical_sql]
  structure: [graph]
  retrieval: [graph_rag, lexical]
```

These names are illustrative, not canonical configuration keys.

## Canonical versus derived state

Every configured module MUST declare whether it stores or produces:

- canonical memory state;
- historical evidence;
- derived projection/index state;
- learned/latent influence state;
- cache/ephemeral state.

Derived or physical state MUST remain rebuildable or explicitly non-rebuildable. A module replacement MUST NOT silently change canonical logical identity, provenance, lifecycle, scope, or currentness.

## Structural mutability

ADR-032 governs structural adaptation.

The fabric may discover and propose new memory shapes at runtime. Structural proposals may come from learned systems, domain modules, workload pressure, or deterministic maintenance observations.

Commit authority is separate:

```text
probabilistic / learned discovery
  -> structural proposal
  -> deterministic semantic + dependency + migration analysis
  -> deterministic governance classification
  -> autonomous bounded commit OR explicit human decision
```

No confidence score, embedding similarity, learned utility estimate, or model recommendation can directly authorize canonical structural mutation.

## Configuration contract

A module profile should expose at least:

```text
module_id
module_type / capabilities
implementation_ref
version
configuration_version
canonical_or_derived_posture
supported scopes / isolation behavior
write capabilities
recall-candidate capabilities
currentness / invalidation semantics
correction / supersession behavior
deletion / residue behavior
migration / rebuild behavior
failure / unavailable posture
local / remote deployment posture
dependency + license metadata
observability / evidence hooks
structural mutation requirements
```

Unsupported or incompatible configurations must fail deterministically rather than degrade into guessed behavior.

## Routing contract

Routing itself is not authority.

A router MAY use learned or heuristic signals to recommend candidate modules or representations, but any routing consequence that changes canonical durability, scope, authority, lifecycle, or structural semantics must pass normal governance.

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

## Open design questions

- should module composition be static per deployment, dynamically routed per memory, or both;
- which canonical state surfaces may be shared across several writable modules without introducing dual authority;
- how module migration and shadow/canary operation should work;
- which structural S1 changes deserve an autonomous PAMA envelope;
- how first-party modules are packaged: libraries, processes, sidecars, or remote services;
- how restart-safe governance metadata is reconstructed independently from a physical substrate;
- which conformance levels are required before a module can be called reference-grade.

## Relationship to current work

- #274 owns the modular-memory program.
- #275 evaluates EvolveAI and CodeGenome as first-party candidates.
- #276 currently finds no need for a new universal logical-state algebra in the tested scenarios.
- #279 proves the Agent Memory <-> Agent Governance peer seam against DashClaw.
- ADR-032 defines structural mutation authority and schema lifecycle.

## Proposed implementation sequence

1. freeze module/configuration contracts;
2. build the minimal configurable Agent Memory instance around existing reference components;
3. prove the DashClaw governed durable-memory scenario;
4. make governance metadata restart-safe;
5. implement at least two materially different module profiles;
6. run replacement/removal and mixed-module conformance;
7. qualify first-party EvolveAI/CodeGenome responsibilities only after executable evidence.
