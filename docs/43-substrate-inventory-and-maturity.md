# Substrate Inventory and Maturity

**Purpose:** provide one current answer to which Agent Memory substrates exist, where they live, what durability they have earned, and which similarly named things are not substrates.

**Method:** derive status from current Agent Memory code, accepted architecture, committed qualification evidence, and exact persistence behavior. Intent does not promote maturity.

## 1. Keep the categories separate

"Substrate", "memory implementation", "capability provider", "implementation ancestry", "domain evidence source", and "persistence mechanism" are different things.

| Kind | Definition here | Example |
|---|---|---|
| **Substrate** | concrete implementation of the Agent Memory temporal/canonical state surface | `InMemoryTemporalGraph`, `SQLiteTemporalGraph` |
| **Memory implementation** | governed Agent Memory behavior above a substrate | epistemic belief memory |
| **External capability provider** | third-party component qualified for a bounded capability | Hindsight resource memory |
| **Implementation ancestry** | prior first-party code from which Agent Memory may harvest mechanisms | EvolveAI, CodeGenome, COREFORGE Vault/Neurospace |
| **Domain evidence source** | specialized system that may continue producing observations | CodeGenome code-domain reality |
| **Persistence mechanism** | storage technology beneath an implementation | SQLite, Postgres, object storage |

The anti-inference rule remains:

```text
storage technology != substrate
substrate != capability
capability != authority
persistence != correctness proof
implementation ancestry != permanent runtime ownership
```

A database underneath a component does not prove Agent Memory restart, concurrency, deletion, scope, or authority semantics. Conversely, an Agent Memory-native substrate that has been qualified against those semantics may earn a bounded production profile.

## 2. First-party temporal/canonical substrates

Agent Memory currently has three first-party substrate implementations of materially different maturity.

| Substrate | Location | Current maturity | Durability posture |
|---|---|---|---|
| `InMemoryTemporalGraph` | `reference/agentmem_ref/state/substrate.py` | **reference implementation** | restart/checkpoint behavior proven through the reference checkpoint profile; not itself a production persistent database |
| `SQLiteTemporalGraph` | `reference/agentmem_ref/state/sqlite_substrate.py` | **RC-qualified production-credible single-host canonical substrate** | SQLite database is canonical durable state; WAL, `synchronous=FULL`, foreign keys, durable identifier progress, transactional runtime state/journal, integrity and backup seams |
| `GraphitiSubstrate` | `reference/agentmem_ref/state/graphiti_driver.py` | **declared / experimental adapter** | does not implement the qualified canonical restart profile; current probe uses a deprecated Kuzu path and is not production canonical evidence |

### 2.1 `InMemoryTemporalGraph`

`InMemoryTemporalGraph` remains the executable reference substrate. It is intentionally permissive below governance: direct substrate writes do not acquire authority merely because they succeed.

The #363 remediation program established a reference persistence contract including:

- component-owned checkpoint export/restore;
- substrate-owned identifier progress;
- serialized generation publication and compare-and-commit conflict detection;
- generation journal integrity;
- explicit schema/profile migration and governed rollback;
- public checkpoint transaction support;
- owner-level auxiliary state restart contracts;
- atomic composition of declared auxiliary owners into a committed generation.

That evidence remains valuable as the reference correctness model. It does not turn an in-memory object graph into a production persistence recommendation.

### 2.2 `SQLiteTemporalGraph`

`SQLiteTemporalGraph` is the first Agent Memory-native production-credible canonical substrate qualified for the RC profile under #427 / PR #452.

The implementation declares profile:

```text
sqlite_single_host_v1
```

The SQLite database, not a JSON dump or an external provider's private state, is canonical durable state for that profile.

Current implementation characteristics include:

- one local SQLite database file;
- WAL journaling;
- `synchronous=FULL`;
- foreign-key enforcement;
- canonical episodes and facts stored directly in SQLite;
- deterministic lexical candidate generation and provenance-neighbor lookup on the native substrate;
- durable substrate-scoped identifier progress;
- explicit transactions using `BEGIN IMMEDIATE`;
- runtime-state and generation-journal storage;
- integrity checking;
- SQLite backup support;
- no authority effect from storage success, native relations, or retrieval scores.

The production claim is deliberately bounded:

```text
production-credible single-host RC substrate
    !=
distributed database
    !=
multi-host consensus
    !=
network-partition tolerance
    !=
horizontal scale guarantee
```

The implementation itself explicitly does not claim leader election, network partition handling, or distributed horizontal scale.

### 2.3 `GraphitiSubstrate`

`GraphitiSubstrate` remains useful as an interoperability/governance pressure adapter, but its maturity is narrow.

Current facts:

- it implements the Agent Memory temporal graph surface over `graphiti-core`;
- the current adapter directly targets Graphiti's Kuzu driver path;
- that path is deprecated upstream;
- the adapter has simplified graph/search behavior suited to the probe;
- it does not inherit SQLite or reference-checkpoint qualification by association.

Therefore:

```text
Graphiti adapter exists
    !=
Graphiti is Agent Memory's qualified production canonical substrate
```

A future Graphiti production profile would require fresh exact-version/backend qualification.

## 3. First-party memory implementations above the substrate

These are Agent Memory implementations, not external substrate owners.

| Implementation | Location | Role |
|---|---|---|
| Epistemic belief memory | `reference/agentmem_ref/memory/epistemic_memory.py` | governed epistemic belief surface |
| Procedural / skill memory | `reference/agentmem_ref/memory/procedural_memory.py` | bounded procedure/skill memory |
| Predictive / counterfactual memory | `reference/agentmem_ref/memory/predictive_memory.py` | governed predictive/counterfactual memory |
| Conditional memory influence | `reference/agentmem_ref/memory/conditional_memory_influence.py` | admission evidence for model-internal conditional memory |
| Code Reality Graph package | `reference/agentmem_ref/crg/` | Agent Memory code-reality boundary and code-domain evidence normalization |
| Multi-route / controlled recall | `reference/agentmem_ref/runtime/` | native candidate retrieval composition and one governed admission boundary |

The capability maturity ladder remains:

```text
declared -> implemented -> runtime_wired -> evidence_proven -> reference_qualified
```

Nothing self-promotes because a lower layer became durable or because useful code existed in another first-party repository.

## 4. External capability providers are not canonical substrates

Third-party providers such as Hindsight or MemOS may earn bounded capability qualification without becoming Agent Memory's canonical substrate.

Their underlying storage choices do not promote those databases into Agent Memory substrates.

```text
Hindsight using PostgreSQL
    !=
Agent Memory PostgreSQL substrate qualification

MemOS plugin using SQLite
    !=
Agent Memory SQLite substrate qualification
```

The second statement remains important even though Agent Memory now has its **own** `SQLiteTemporalGraph`. The native qualification was earned by the Agent Memory implementation and its exact profile, not inherited from another product merely because both use SQLite.

## 5. First-party ancestry is not provider ownership

ADR-036 and #455 clarify the relationship to EvolveAI, CodeGenome, and COREFORGE.

### EvolveAI

EvolveAI is implementation ancestry/test-oracle material for vector retrieval, temporal graph behavior, lifecycle/metabolism, decay, consolidation, pruning, crystallization, restart, and failure-memory concepts.

Useful behavior should be harvested into native Agent Memory modules. EvolveAI is not the required runtime substrate for Agent Memory.

### CodeGenome

CodeGenome is implementation ancestry for graph/vector/provenance/evaluation mechanisms and may continue as a specialized code-domain observation source.

The continuing valid shape is:

```text
CodeGenome code-domain evidence
    -> Agent Memory CRG / memory machinery
```

not:

```text
Agent Memory generic graph/vector memory
    -> requires CodeGenome runtime
```

### COREFORGE Vault / Neurospace

COREFORGE contains valuable product/runtime ancestry around memory domains, context brokerage, graph recall, references, mutation boundaries, and lineage.

The desired end-state direction is for COREFORGE to consume Agent Memory for generic memory capabilities rather than remain the canonical memory container for Agent Memory.

## 6. Code Reality Graph status

Agent Memory has an explicit package boundary:

```text
reference/agentmem_ref/crg/
```

The package contains Agent Memory's Code Reality Graph surface and code-domain normalization/profile logic.

The ownership distinction is:

| Statement | Current state |
|---|---|
| Agent Memory owns the CRG contract/framework | **decided** |
| CRG has a named package boundary | **implemented** |
| CodeGenome-derived/profile modules exist as ancestry/evidence normalization | **implemented** |
| CodeGenome must run for Agent Memory's generic graph/vector memory to function | **no** |
| CodeGenome may continue to supply code-domain observations | **yes** |
| CRG is itself the canonical temporal substrate | **no** |
| provider-native graph/relevance outputs gain authority | **no** |

## 7. Package architecture

The package uses an enforced layered topology through `scripts/restructure_package.py`:

```text
core
state
contracts
runtime
memory
api
crg
harness
```

Compatibility aliases may remain at the package root for older imports.

Current native retrieval work is already composed through the runtime layer. Issue #456 may add or prepare a dedicated retrieval package if the package-layout contract can support it without gratuitous churn.

The ownership requirement is semantic, not decorative: a file does not become native merely because it moved directories. Native ownership requires Agent Memory code, tests, lifecycle/currentness behavior, and evidence.

## 8. Persistence mechanisms that are still not substrates by default

### Graph databases

Neo4j, FalkorDB, Neptune, Kuzu, and similar systems are storage technologies until an Agent Memory adapter/profile is built and qualified against the canonical substrate contract.

### Postgres

Postgres remains a persistence technology in this repository until a native Agent Memory substrate/profile is implemented and qualified.

### SQLite

SQLite now has two different meanings that must not be confused:

1. **SQLite as a generic storage technology** used by arbitrary products or plugins. This alone proves nothing about Agent Memory.
2. **`SQLiteTemporalGraph` under `sqlite_single_host_v1`**, which is an Agent Memory-native implementation with RC qualification evidence.

### Files / Markdown / object stores / event logs

These may be appropriate representations or supporting stores for bounded memory artifacts, backup, evidence, or derived state. Their presence does not establish canonical currentness, migration, deletion, tenancy, or authority semantics.

## 9. Persistence program status

The original #363 audit bundled several reference-persistence correctness defects. Those were remediated through the #413-#425 series and reconciled in #426.

The successor #427 production qualification gate is now complete for the bounded SQLite single-host profile through PR #452.

Therefore the current posture is:

```text
reference checkpoint correctness
    -> proven

one native production-credible single-host canonical substrate
    -> qualified for RC profile

distributed / multi-host production substrate
    -> not claimed
```

Do not reopen completed reference persistence work merely because future deployments may require a stronger topology.

## 10. Production substrate qualification rule

Any additional candidate still has to earn the role through executable evidence. At minimum qualification should cover, as applicable:

- the Agent Memory temporal/canonical state behavioral surface;
- exact identity/version/profile of the backend;
- restart reconstruction without losing currentness, scope, tombstone, or identifier semantics;
- transaction/generation behavior compatible with the active runtime profile;
- stale/concurrent writer behavior;
- crash/interrupted recovery behavior;
- migration and rollback semantics;
- deletion and residue behavior;
- tenant/scope isolation at the Agent Memory boundary;
- deterministic reconstruction of required governance interpretation;
- evidence that provider-native ranking, inference, graph relations, confidence, or storage success do not acquire authority;
- source-rights and operational deployment posture;
- explicit limitations rather than inferred maturity.

A stronger native transaction model need not imitate the reference file checkpoint mechanics. It must satisfy the same correctness obligations for the profile it claims.

## 11. Summary

| Category | Current state |
|---|---|
| First-party temporal/canonical substrates | **3**: in-memory reference, SQLite RC-qualified single-host, Graphiti experimental adapter |
| Restart-safe reference substrate | `InMemoryTemporalGraph` under reference checkpoint profile |
| Production-credible RC-qualified canonical substrate | **1**: `SQLiteTemporalGraph` / `sqlite_single_host_v1` |
| Distributed/multi-host production substrate | **0 claimed** |
| First-party governed memory implementations | multiple native Agent Memory modules above substrate layer |
| External qualified capability providers | bounded providers only; not canonical substrates |
| CRG package boundary | implemented |
| Native multi-route/controlled recall | implemented |
| Native semantic/vector route | active under #456 |
| First-party ancestry relationship | clarified by ADR-036 / #455; ancestry is not permanent runtime ownership |

## 12. Maintenance rule

Update this inventory in the same change that:

- adds/removes a canonical substrate implementation;
- changes a substrate's restart/transaction capability;
- adds a canonical-substrate qualification artifact/profile;
- changes CRG/module ownership or package structure;
- changes an external provider's earned qualification status;
- changes the first-party ancestry/runtime ownership boundary;
- materially changes production durability posture.

A substrate or durability change that leaves this inventory stale is a governance drift defect.