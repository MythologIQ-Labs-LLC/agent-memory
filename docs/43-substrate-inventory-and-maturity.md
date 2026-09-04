# Substrate Inventory and Maturity

**Purpose**: a single answer to "which memory substrates exist, where does each live, and how mature is it" — for first-party substrates and for the external systems people reach for as equivalents.

**Method**: derived from code and from committed qualification artifacts, not from intent. Every maturity value below is either read from a qualification artifact on disk or stated as absent.

---

## 1. The distinction this document exists to make

"Substrate", "capability", "architectural role", and "persistence mechanism" are four different things, and the names people use conversationally cut across all four. Conflating them is how a component acquires maturity it never earned.

| Kind | Definition here | Example |
|---|---|---|
| **Substrate** | A concrete implementation of `TemporalGraphPort` — `add_episode`, `write_fact`, `invalidate_fact`, `get_fact`, `delete_fact`, `search` | `InMemoryTemporalGraph` |
| **Capability** | A named, versioned, qualifiable function a component provides | `resource_artifact_memory v1.0` |
| **Architectural role** | A position in the layer model that some component may be proposed to fill | Code Reality Graph |
| **Persistence mechanism** | Storage technology a substrate or provider may use underneath | Markdown, Postgres, object store |

`docs/42-governed-mutable-memory-fabric.md:131` already states the governing rule: *"A graph database does not become GraphRAG merely because nodes and edges exist."* The same applies in every direction. **Postgres underneath a provider is not a substrate, and a substrate is not a capability.**

---

## 2. First-party substrates — there are exactly two

Verified by enumerating classes implementing the full `TemporalGraphPort` surface.

| Substrate | Location | Maturity | Notes |
|---|---|---|---|
| `InMemoryTemporalGraph` | `reference/agentmem_ref/substrate.py:92` | **reference implementation** — the executable definition, not a qualified component | Deliberately permissive: `write_fact` is documented as "Direct write. No authority check, by design and by observation." Governance lives in the adapter above it. Owns the identifier counter as of ledger entry #12. |
| `GraphitiSubstrate` | `reference/agentmem_ref/graphiti_driver.py:64` | **`declared`** — no qualification artifact exists | Implements the port over `graphiti-core`. **Not a declared dependency**, and targets deprecated Kuzu. Cannot be checkpointed: `JsonRuntimeStateStore` reaches into `InMemoryTemporalGraph` privates (`_episodes`, `_facts`, `write_log`). Tracked as [#363](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/363). |

**No other substrate exists in this repository.** Any additional substrate is prospective work, not an implementation with a location.

### Maturity ladder

Schema-enforced in `schemas/component-capability-qualification.schema.json`:

```
declared -> implemented -> runtime_wired -> evidence_proven -> reference_qualified
```

A component sits at `declared` until evidence moves it. Nothing self-promotes.

---

## 3. Qualified external components

These are **capability providers**, not substrates. They provide a named capability under a qualified contract; neither implements `TemporalGraphPort`.

| Component | Capability | Earned maturity | Authority effect | Artifact |
|---|---|---|---|---|
| `hindsight-v0.9.0` | `resource_artifact_memory v1.0` | **`evidence_proven`** | `none` | `reference/fixtures/component-qualification/hindsight-v0.9.0-resource-artifact-qualified-v12.json` |
| `memos-local-plugin-v2.0.17` | `resource_artifact_memory v1.0` | **`evidence_proven`** | `none` | `.../memos-local-plugin-v2.0.17-resource-artifact-qualified-v12.json` |

Both qualifications are **narrow by construction** and say so. Hindsight carries 5 recorded limitations, MemOS 7. Two worth repeating because they are the kind of thing that gets dropped in summary:

- *"Only chunk-backed `resource_artifact_memory` is qualified; richer LLM-backed Hindsight modes are outside this evidence."*
- *"PostgreSQL underneath Hindsight is not evidence that the Hindsight operation exposed to Agent Memory has a particular atomic or concurrency guarantee."* (`docs/programs/memory-modules/hindsight-v090-qualification.md:149`)

`authority_effect: none` on both: a qualified provider supplies memory, never authority.

---

## 4. Named concepts that are not substrates

Each of these is real and each lives somewhere — just not as a substrate. This section exists so nobody has to rediscover that.

### Code Reality Graph

An **architectural role** in the layer model (`docs/01-layer-model.md:48`, `docs/11-component-architecture.md:41`).

**CodeGenome** is the *proposed* first-party implementation of the role (`docs/11:77`). `docs/01:71` is explicit that the mapping "does not promote any capability maturity and does not make either provider's internal ontology canonical."

**Maturity: role is doctrine-defined; no implementation is qualified in this repository.** There is no CodeGenome code, capability declaration, or qualification artifact here.

External equivalents: code-property-graph and code-knowledge-graph tooling (Sourcegraph SCIP, Glean, CodeQL's database). None is qualified against a capability contract here.

### GraphRAG

A **capability family**, not a store (`docs/42:7,120-131`). The doctrine spends a section distinguishing graph storage from graph-augmented context assembly precisely because the two get conflated.

**Maturity: doctrine-defined; no GraphRAG capability is declared or qualified in this repository.**

External equivalents: Microsoft GraphRAG, LlamaIndex property-graph retrievers, Neo4j GraphRAG. A substrate could underlie any of them; none is one.

### Markdown / files

A **persistence mechanism** (`docs/42:114`, `docs/rfcs/RFC-001:164`). `ADR-034:71` states procedural memory MAY use Markdown, and `:236` states doing so does not make Markdown canonical. `docs/42:209` uses `short-term = Markdown` as an illustration of a lifecycle-to-mechanism mapping, not a specification.

**Maturity: named as an example; no Markdown substrate exists.**

### Postgres / SQLite

A **persistence mechanism** (`RFC-001:164`), and the subject of an explicit anti-inference rule: durability of the storage engine is not evidence about the capability contract above it (`federated-resource-exchange.md:48`, `hindsight-v090-qualification.md:149`).

**Maturity: named as an example; no relational substrate exists.** Hindsight uses PostgreSQL underneath, which is a property of Hindsight, not a Postgres substrate in this repository.

External equivalents: pgvector, Supabase, Timescale for temporal workloads. Any of these could back a future substrate; none is one today.

---

## 5. Summary — what actually exists

| | Count | At what maturity |
|---|---|---|
| First-party substrates | **2** | one reference implementation, one `declared` |
| Qualified external components | **2** | both `evidence_proven`, both `authority_effect: none` |
| Architectural roles with no implementation here | 1 (Code Reality Graph) | doctrine-defined |
| Capability families with no declaration here | 1 (GraphRAG) | doctrine-defined |
| Persistence mechanisms named as examples | 4+ (Markdown, files, Postgres/SQLite, object stores, event logs) | not substrates |

**The gap between what the doctrine names and what the runtime implements is intentional and is the honest state.** The layer model describes an architecture; the reference runtime implements the parts that have been built and proven. This document exists so the difference stays visible rather than being read as a claim.

---

## 6. Maintenance

Update in the same change that adds a substrate, declares a capability, or lands a qualification artifact. A substrate added without a row here is a `docs/GOVERNANCE_INDEX.md` Tier 1 drift bug.
