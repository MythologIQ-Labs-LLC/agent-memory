# Mutable Memory Fabric

Agent Memory is the memory system. The graph database, RAG implementation, vector index, JEPA-style representation, Markdown files, lifecycle engine, or complete first-/third-party memory service are **components** used by that system.

Components expose one or more **capabilities**. Those capabilities are composable roles, not exclusive product categories.

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
    +-- component + capability configuration
    +-- capability routing
    +-- governed mutation and recall
    +-- evidence / receipts
    |
    +--> configured components
    |       +--> capabilities[]
    |       +--> maturity/evidence per capability
    |
    v
Agent Governance peer(s)
    DashClaw / AGT / other policy, approval, enforcement systems
```

Agent Governance is a peer. It can tighten consequences or return approval/enforcement evidence, but it does not become the owner of memory semantics.

## Components and capabilities are different things

The fabric uses a many-to-many model:

```text
component identity != capability identity

one component -> many capabilities
one capability -> many possible components
```

That matters for first-party systems in particular.

EvolveAI is not merely a lifecycle module. Its architecture spans temporal graph memory, vector retrieval, exact/content-addressed retrieval, tier routing, decay, consolidation/lifecycle mechanisms, failure memory, persistence/audit, and GraphRAG-oriented design at different maturity levels.

CodeGenome is not merely a graph module. Its architecture spans graph storage/traversal, graph-derived code context, impact analysis, embeddings, vector similarity, confidence/evidence fusion, provenance, multi-language extraction, MCP exposure, and self-evaluation at different maturity levels.

Their differentiators remain useful labels. They are not exclusive capability assignments.

## Capability maturity is explicit

A capability should be described independently as:

- `declared` — documented or intended;
- `implemented` — material code exists;
- `runtime_wired` — reachable through the supported runtime/product path;
- `evidence_proven` — reproducible evidence demonstrates the claim;
- `reference_qualified` — Agent Memory conformance requirements for that capability are satisfied.

This prevents two equally bad mistakes: pretending a documented design is already shipped, and pretending a real capability does not exist because another feature is more distinctive.

The initial EvolveAI/CodeGenome inventory is tracked in the canonical repository documentation under `docs/programs/memory-modules/first-party-capability-inventory.md`.

## Memory technologies expose capability families

A deployment can compose capabilities such as:

- **storage/persistence:** files, SQL/document stores, graph stores, object/event stores, content-addressed vaults;
- **exact retrieval:** deterministic key/content-addressed lookup;
- **vector representation/retrieval:** embedding storage, similarity, vector candidate retrieval;
- **graph:** graph storage, graph query/traversal, graph candidate retrieval;
- **GraphRAG/context assembly:** graph-augmented context construction for downstream reasoning;
- **representation:** summaries, compressed state, JEPA-style learned representations;
- **structural/reasoning:** temporal associations, code reality, impact/blast-radius analysis;
- **lifecycle/maintenance:** decay, consolidation, synthesis, pruning/archival proposals;
- **complete memory systems:** first- or third-party systems exposing several capability families simultaneously.

Graph storage is not automatically GraphRAG. Vector storage is not automatically vector retrieval. Issue #291 owns the precise generic vocabulary.

First-party ownership does not grant authority or reference status. EvolveAI and CodeGenome must satisfy the same provenance, correction, deletion, isolation, currentness, failure, and conformance requirements as external systems for every capability they claim.

## Short, medium, and long term are not technologies

Agent Memory does not define:

```text
short = Markdown
medium = JEPA
long = graph
```

A deployment may choose that profile, but routing should be driven by memory characteristics such as retention horizon, scope, sensitivity, relationship density, exactness, latency/cost, offline requirements, and rebuild cost.

Those characteristics resolve to required **capabilities and maturity/posture constraints**, then to configured component implementations.

The same Agent Memory behavior should survive a change in component/capability composition where the changed implementation does not legitimately alter memory semantics.

## Overlap is allowed

Several components may implement the same capability.

For example, EvolveAI and CodeGenome both have graph and vector-related capabilities, but their domain semantics, maturity, cost, and intended use differ.

The runtime may:

```text
select one implementation
compose several implementations
or reject an ambiguous configuration
```

What it may not do is silently select whichever provider registered first, lower a maturity requirement during fallback, or allow overlapping writable components to create ambiguous canonical authority.

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
8. the same acceptance behavior survives different component/capability compositions;
9. capability maturity and overlap resolution are enforced rather than assumed.

The DashClaw integration is a component of that proof. DashClaw governs the broader action/approval side while Agent Memory owns the memory-specific mutation and recall boundaries.

## Current first-party research

- **#284** inventories EvolveAI and CodeGenome capability-by-capability and identifies real gaps.
- **#286** maps external implementations against the same capability rows.
- **#289** decides whether capability overlap should remain inside current repositories, move to shared components, use external implementations, or justify a new first-party subsystem.
- **#292/#293** qualify EvolveAI and CodeGenome profiles without first-party shortcuts.

The goal is not to manufacture one repository per empty taxonomy cell. The goal is to own differentiated subsystems where ownership materially improves the system and to compose existing technology where it does not.

## Canonical sources

- [Governed Mutable Memory Fabric](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/42-governed-mutable-memory-fabric.md)
- [ADR-032: Governed Mutable Memory Structure](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/adr/ADR-032-governed-mutable-memory-structure.md)
- [RFC-001: Governed Mutable Memory Fabric](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/rfcs/RFC-001-governed-mutable-memory-fabric.md)
- [PRD-001: Configurable Agent Memory Runtime](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/prd/PRD-001-configurable-agent-memory-runtime.md)
- [First-Party Capability Inventory](https://github.com/MythologIQ-Labs-LLC/agent-memory/blob/main/docs/programs/memory-modules/first-party-capability-inventory.md)

The Wiki summarizes. The canonical repository sources govern if the two ever disagree.
