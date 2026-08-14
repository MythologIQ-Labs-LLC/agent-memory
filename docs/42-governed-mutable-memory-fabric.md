# Governed Mutable Memory Fabric

## Purpose

Agent Memory is the memory system. Storage engines, retrieval systems, graph technologies, learned representations, lifecycle engines, and complete external memory products are implementation modules inside or behind that system.

The primary long-term boundaries are:

```text
Agent Runtime
  plans, reasons, acts, invokes tools
        |
        v
Agent Memory
  memory semantics, lifecycle, provenance, scope,
  structural mutability, PAMA authority, routing,
  mutation, recall admission, evidence
        |
        +--> configurable memory modules / substrates
        |
        v
Agent Governance peer(s)
  policy / approval / enforcement systems such as
  DashClaw, AGT, or other external governance runtimes
```

Agent Governance is a peer authority surface. It is not a memory substrate. A DashClaw or AGT adapter can tighten consequences or return approval/enforcement evidence, but Agent Memory remains responsible for memory-specific semantics and revalidation at commit and recall.

## Agent Memory owns the fabric

Agent Memory MUST remain authoritative for the general memory contract even when most physical work is delegated to modules.

It owns at least:

- logical memory identity and currentness;
- provenance/evidence boundaries;
- scope, tenancy, and isolation;
- lifecycle and supersession semantics;
- PAMA mutation authority;
- structural-mutation authority;
- canonical-versus-derived state classification;
- routing policy and module compatibility;
- governed recall admission;
- correction/deletion obligations;
- evidence sufficient to reconstruct consequential changes.

A module can implement several capabilities, but it does not inherit these authorities by installation.

## Configurable module roles

### Storage

Files/Markdown, relational/document stores, graph stores, object stores, event logs, and other persistence mechanisms.

### Retrieval and indexing

Lexical indexes, vector retrieval, GraphRAG-style traversal, code-graph queries, and other candidate-generation mechanisms.

### Representation

Embeddings, summaries, compressed state, JEPA-style or other learned latent representations.

### Structural and reasoning memory

Domain graphs, code-reality graphs, temporal associations, relationship traversal, and other structured evidence surfaces.

CodeGenome is a first-party candidate for a code-domain structural-memory role. It does not become the canonical graph ontology or logical identity system merely because it is first-party.

### Lifecycle and maintenance

Decay, weakening, consolidation, synthesis, archival, pruning candidacy, and other memory-metabolism capabilities.

EvolveAI is a first-party candidate for adaptive/lifecycle roles. Its learned or heuristic signals may propose consequences but do not acquire mutation authority.

### Complete external memory-system adapter

A third-party memory service may be wrapped as one or more module roles. Imported or retrieved state remains subject to Agent Memory provenance, scope, currentness, lifecycle, and admission rules.

## Memory horizon is not backend identity

The architecture does not define fixed mappings such as:

```text
short-term = Markdown
mid-term = JEPA
long-term = knowledge graph
```

Those may be reasonable deployment choices, but they are configuration, not doctrine.

Instead the system evaluates memory characteristics such as:

```text
retention horizon
scope and isolation
sensitivity
semantic/relationship density
exactness and audit requirements
lifecycle state
reversibility
latency and cost budget
local/offline requirements
rebuild cost
provenance requirements
```

A deployment profile then routes the memory to one or several compatible modules.

This permits different instances to use different combinations while preserving the same Agent Memory behavior and conformance boundaries.

## Mutable shape, governed authority

Agent Memory allows memory structures to evolve because useful domain shape is not always knowable at design time.

The system distinguishes:

```text
canonical semantic shape
application / domain ontology
derived / physical representation
```

Changing a vector index is not necessarily changing memory meaning. Adding a project-local entity type is more consequential. Reinterpreting existing durable memory or changing isolation/authority semantics is more consequential still.

ADR-032 establishes the safeguard:

> **Memory shape may adapt. Authority over canonical structural mutation may not be probabilistic.**

Learned, heuristic, or probabilistic systems may discover pressure and propose a new structure. A canonical structural consequence is committed only by:

- a versioned deterministic policy proving the change falls inside an explicitly authorized bounded envelope; or
- an explicitly authorized human decision.

## Structural consequence classes

| Class | Typical change | Default authority posture |
|---|---|---|
| **S0** | rebuild-only derived/index/representation change | autonomous under deterministic maintenance policy |
| **S1** | bounded additive local extension with preserved meaning and rollback | autonomous only when deterministic policy proves the bounded envelope |
| **S2** | semantic reinterpretation or migration-bearing change | user-visible proposal and authorized human decision |
| **S3** | destructive, cross-scope, isolation-, policy-, or authority-bearing change | explicit authorized human decision; stricter PAMA rules may block |

The class is determined by impact, not by how confident the proposing model sounds.

## Schema has lifecycle

Once durable state depends on a shape, that shape cannot be removed casually.

```text
active version
  -> successor proposed
  -> semantic / compatibility / dependency analysis
  -> authority decision
  -> successor activated
  -> migration / rebuild
  -> validation / residue check
  -> old version superseded
  -> retirement only after live dependencies are resolved
```

Historical interpretation should remain reconstructable where it matters. Structural supersession is preferred to pretending the previous model never existed.

## Probabilistic discovery remains useful

The safeguard is not a ban on adaptive discovery.

A model or learned module may observe:

```text
"these memories repeatedly need a release_channel relationship"
```

and produce:

- a candidate entity/relation definition;
- supporting examples and source roots;
- a migration proposal;
- expected retrieval benefit;
- uncertainty and alternatives.

Agent Memory then performs deterministic compatibility, dependency, scope, reversibility, and authority classification before any structural consequence is committed.

```text
probabilistic discovery
  -> candidate structural change
  -> deterministic impact analysis
  -> deterministic governance classification
  -> autonomous bounded commit OR human decision
```

## Three-system responsibility model

### Agent Runtime

Uses memory. It may propose memory operations but does not become memory authority simply because it is the consumer.

### Agent Memory

Owns retained-state semantics and the configured module fabric. It decides what memory is current, admissible, correctable, forgettable, and structurally mutable under PAMA and related doctrine.

### Agent Governance

Owns broader policy, approval, and enforcement concerns outside the memory-specific authority boundary. It may tighten a memory consequence or supply approval/evidence through an adapter without redefining memory semantics.

The interfaces among these systems may evolve. Their responsibilities should remain explicit so an integration does not collapse decision, approval, execution, and memory state into one ambiguous token.

## First implementation target

The first product-shaped acceptance test is deliberately concrete:

1. an agent learns a project-specific release-branch fact;
2. Agent Memory governs and commits it;
3. another session recalls it and changes behavior because of it;
4. new evidence corrects the fact;
5. DashClaw supplies the external governance/approval portion where required;
6. Agent Memory revalidates and supersedes the old current value;
7. another session uses the corrected value;
8. stale approval, authority widening, and cross-scope recall fail;
9. process restart eventually preserves currentness and governance state;
10. the same behavioral contract is rerun with different module compositions.

This is the difference between proving an adapter and proving a memory system.

## Related architecture work

- [`adr/ADR-032-governed-mutable-memory-structure.md`](adr/ADR-032-governed-mutable-memory-structure.md)
- [`rfcs/RFC-001-governed-mutable-memory-fabric.md`](rfcs/RFC-001-governed-mutable-memory-fabric.md)
- [`prd/PRD-001-configurable-agent-memory-runtime.md`](prd/PRD-001-configurable-agent-memory-runtime.md)
- [`explorations/memory-architectures/progressive-domain-schema-discovery.md`](explorations/memory-architectures/progressive-domain-schema-discovery.md)
- [`profiles/pama-1-2-domain-schema-compatibility.md`](profiles/pama-1-2-domain-schema-compatibility.md)
- issue #274: modular memory profiles program
- issue #275: EvolveAI / CodeGenome adversarial module comparison
- issue #279: DashClaw external-verdict integration
- issue #280: module/configuration and routing implementation
- issue #281: deterministic structural-mutation classification and schema lifecycle
- issue #282: restart-safe runtime and acceptance harness
