# Mutable Memory Fabric

Agent Memory is the memory system. The graph database, RAG implementation, vector index, JEPA-style representation, Markdown files, lifecycle engine, or complete external memory service are modules used by that system.

The long-term boundary is:

```text
Agent Runtime
    |
    v
Agent Memory
    |
    +-- memory semantics
    +-- provenance / scope / lifecycle
    +-- PAMA / structural mutation authority
    +-- module configuration and routing
    +-- governed mutation and recall
    +-- evidence / receipts
    |
    +--> storage / retrieval / graph / learned / lifecycle modules
    |
    v
Agent Governance peer(s)
    DashClaw / AGT / other policy, approval, enforcement systems
```

Agent Governance is a peer. It can tighten consequences or return approval/enforcement evidence, but it does not become the owner of memory semantics.

## Memory technologies are configurable modules

A deployment can compose different module roles:

- **storage:** files, SQL/document stores, graph stores, object/event stores;
- **retrieval:** lexical, vector, GraphRAG, code-graph traversal;
- **representation:** embeddings, summaries, compressed state, JEPA-style learned representations;
- **structural/reasoning:** domain graphs, temporal relationships, CodeGenome-style code reality;
- **lifecycle/maintenance:** decay, consolidation, synthesis, pruning/archival proposals, EvolveAI-style adaptive memory;
- **external memory adapters:** complete third-party memory systems wrapped behind Agent Memory contracts.

First-party ownership does not grant authority or reference status. EvolveAI and CodeGenome are candidate first-party modules and must satisfy the same provenance, correction, deletion, isolation, currentness, failure, and conformance requirements as external systems.

## Short, medium, and long term are not technologies

Agent Memory does not define:

```text
short = Markdown
medium = JEPA
long = graph
```

A deployment may choose that profile, but routing should be driven by memory characteristics such as retention horizon, scope, sensitivity, relationship density, exactness, latency/cost, offline requirements, and rebuild cost.

The same Agent Memory behavior should survive a change in module composition where the modules do not legitimately change memory semantics.

## Mutable shape with a deterministic authority boundary

Memory structure can evolve after deployment. A system may discover a useful entity, relation, field, projection, or representation that was not known on day one.

The architecture distinguishes:

```text
canonical semantic shape
application / domain ontology
derived / physical representation
```

A model may propose a new structure. It does not get to commit canonical structure because it is confident.

The safeguard from ADR-032 is:

> **Memory shape may adapt. Authority over canonical structural mutation may not be probabilistic.**

The path is:

```text
learned / probabilistic discovery
    -> structural proposal
    -> deterministic impact analysis
    -> deterministic governance classification
    -> bounded autonomous commit OR human decision
```

Small rebuild-only or tightly bounded additive changes can be automatic under versioned deterministic policy. Semantic migrations, destructive changes, scope widening, isolation changes, or authority-bearing structures require explicit human authority.

## Why removal is harder than addition

Once durable memory depends on a structure, the structure has lifecycle too.

```text
active schema
  -> successor proposal
  -> compatibility + dependency analysis
  -> governance decision
  -> migration / rebuild
  -> validation / residue check
  -> superseded old version
  -> retirement only after live dependencies are resolved
```

The old shape should not simply vanish if doing so destroys historical interpretation or rollback.

## What the first real system must prove

The first product-shaped Agent Memory instance should prove more than an API response:

1. one agent session creates governed durable memory;
2. another session recalls it and changes behavior because of it;
3. correction requires the appropriate authority and supersedes the old current value;
4. a later session uses the correction;
5. stale approvals and unsafe scope expansion fail;
6. cross-scope recall fails;
7. process restart eventually preserves governance/currentness state;
8. the same acceptance behavior survives different module compositions.

The DashClaw integration is a component of that proof. DashClaw governs the broader action/approval side while Agent Memory owns the memory-specific mutation and recall boundaries.

## Canonical sources

- [Governed Mutable Memory Fabric](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/42-governed-mutable-memory-fabric.md)
- [ADR-032: Governed Mutable Memory Structure](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/adr/ADR-032-governed-mutable-memory-structure.md)
- [RFC-001: Governed Mutable Memory Fabric](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/rfcs/RFC-001-governed-mutable-memory-fabric.md)
- [PRD-001: Configurable Agent Memory Runtime](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/prd/PRD-001-configurable-agent-memory-runtime.md)

The Wiki summarizes. The canonical repository sources govern if the two ever disagree.
