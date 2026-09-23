# Substrate Inventory and Maturity

**Purpose**: provide one current answer to "which memory substrates exist, where do they live, what durability have they earned, and which similarly named things are not substrates?"

**Method**: derive status from current code, accepted architecture, committed qualification artifacts, and exact persistence evidence. Intent does not promote maturity.

---

## 1. Keep the categories separate

"Substrate", "memory implementation", "capability provider", "architectural role", and "persistence mechanism" are different things.

| Kind | Definition here | Example |
| --- | --- | --- |
| **Substrate** | A concrete implementation of `TemporalGraphPort` | `InMemoryTemporalGraph` |
| **Memory implementation** | A governed memory surface above the substrate | epistemic belief memory |
| **Capability provider** | A versioned component qualified for a bounded capability | Hindsight resource memory |
| **Architectural role** | A position in the Agent Memory architecture | Code Reality Graph |
| **Persistence mechanism** | Storage technology used underneath some implementation | Postgres, SQLite, object storage |

The anti-inference rule is unchanged:

```text
storage technology != substrate
substrate != capability
capability != authority
persistence != correctness proof
```

A durable database underneath a component does not prove the component's restart, concurrency, deletion, or authority semantics.

---

## 2. First-party temporal substrates

There are currently two first-party implementations of the `TemporalGraphPort` surface.

| Substrate | Location | Current maturity | Durability posture |
| --- | --- | --- | --- |
| `InMemoryTemporalGraph` | `reference/agentmem_ref/state/substrate.py` | **reference implementation** | Implements the reference checkpoint capability used by `RestartSafeRuntime`; owner-defined export/restore and identifier progress are covered by the #363 remediation evidence. |
| `GraphitiSubstrate` | `reference/agentmem_ref/state/graphiti_driver.py` | **declared / experimental adapter** | Does **not** implement the reference checkpoint capability and is therefore not a restart-safe canonical substrate. The current adapter directly imports Graphiti's Kuzu driver and its own module documentation marks that backend deprecated. |

No other `TemporalGraphPort` implementation currently exists in this repository.

### 2.1 `InMemoryTemporalGraph`

`InMemoryTemporalGraph` is the executable reference substrate. It is intentionally permissive below governance: direct substrate writes do not acquire authority merely because they succeed. PAMA and the governed adapter remain the authority boundary above it.

The reference durability work under #363 now provides more than the original file checkpoint:

- component-owned checkpoint export/restore rather than private-field scraping;
- substrate-owned identifier progress;
- serialized generation publication and compare-and-commit conflict detection;
- generation journal integrity;
- explicit schema/profile migration and governed rollback;
- public checkpoint transaction support for higher-layer coordination;
- owner-level auxiliary state restart contracts;
- atomic composition of explicitly declared auxiliary owners into the same committed generation.

That evidence qualifies the **reference persistence contract**. It does not make the in-memory substrate a production storage recommendation.

### 2.2 `GraphitiSubstrate`

`GraphitiSubstrate` remains useful as an interoperability and governance-pressure adapter, but its status must be stated narrowly.

Current implementation facts:

- it implements `TemporalGraphPort` over `graphiti-core`;
- it uses Graphiti's direct driver path rather than treating model inference as authority;
- it imports `graphiti_core.driver.kuzu_driver.KuzuDriver` directly;
- its module documentation identifies Kuzu as deprecated upstream;
- it uses a simplified graph shape and substring retrieval because retrieval quality is not the purpose of the adapter;
- it does not expose `CheckpointableTemporalGraphPort` state export/restore;
- it has no canonical-substrate qualification artifact.

Therefore:

```text
GraphitiSubstrate exists
    != Graphiti is qualified as Agent Memory's production canonical store

real graph database exercise
    != restart-safe production durability
```

A future Graphiti-backed production candidate would need a fresh, exact-version adapter and qualification against a supported Graphiti backend rather than inheriting maturity from this Kuzu-based probe.

---

## 3. First-party memory implementations above the substrate

These are not substrates. They are governed memory implementations that use substrate/runtime contracts underneath them.

| Implementation | Location | Role |
| --- | --- | --- |
| Epistemic belief memory | `reference/agentmem_ref/memory/epistemic_memory.py` | governed epistemic belief surface |
| Procedural / skill memory | `reference/agentmem_ref/memory/procedural_memory.py` | bounded procedure/skill memory |
| Predictive / counterfactual memory | `reference/agentmem_ref/memory/predictive_memory.py` | governed predictive/counterfactual memory |
| Conditional memory influence | `reference/agentmem_ref/memory/conditional_memory_influence.py` | admission evidence for model-internal conditional memory |
| Code-graph qualification surface | `reference/agentmem_ref/crg/code_graph_qualification.py` | provider-neutral code-graph evidence normalization within the CRG package |

The capability maturity ladder remains:

```text
declared -> implemented -> runtime_wired -> evidence_proven -> reference_qualified
```

Nothing self-promotes because a lower layer became durable.

---

## 4. Qualified external capability providers

These providers are deliberately **not** listed as canonical substrates. Their qualification is bounded to the capability actually proven.

| Component | Qualified capability | Earned maturity | Authority effect |
| --- | --- | --- | --- |
| `hindsight-v0.9.0` | `resource_artifact_memory v1.0` | `evidence_proven` | `none` |
| `memos-local-plugin-v2.0.17` | `resource_artifact_memory v1.0` | `evidence_proven` | `none` |

Their underlying storage choices do not promote those databases into Agent Memory substrates. In particular:

```text
Hindsight using PostgreSQL
    != PostgreSQL canonical substrate qualification

MemOS local plugin using SQLite
    != SQLite canonical substrate qualification
```

The qualification artifacts prove bounded provider behavior, source-rights posture, restart/reconciliation behavior where specified, and no authority effect. They do not prove the `TemporalGraphPort` contract or the #363 canonical generation semantics.

---

## 5. Code Reality Graph status

The old inventory described the Code Reality Graph as an owned contract whose module/package structure had not yet been built. That is no longer current.

Agent Memory now has an explicit package boundary:

```text
reference/agentmem_ref/crg/
```

The package declares itself as Agent Memory's Code Reality Graph surface and contains:

- `code_graph_qualification.py`;
- `codegenome_profile.py`;
- `codegenome_cognitive_mesh.py`;
- `codegenome_scope_residue.py`.

The architectural ownership decision remains unchanged:

- Agent Memory owns the Code Reality Graph contract and name;
- CodeGenome is a first-party implementation profile under ADR-035 / ADR-036;
- provider-native evidence must remain distinguishable from Agent Memory authority;
- the CRG package does not become a `TemporalGraphPort` substrate merely because it represents graph-shaped reality.

So the current distinction is:

| Statement | Current state |
| --- | --- |
| Agent Memory owns the CRG contract | **decided** |
| CRG has a named package boundary | **implemented** |
| CodeGenome profile modules exist in that boundary | **implemented** |
| CRG is itself the canonical temporal substrate | **no** |
| external graph provider becomes authoritative through CRG ingestion | **no** |

---

## 6. Package architecture is now layered

The previous inventory stated that `agentmem_ref` was a flat namespace with zero subdirectories. That structural finding has been superseded.

The package now enforces an ordered layered topology through `scripts/restructure_package.py`:

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

Compatibility alias modules remain at the package root for older imports, but the implementation modules live in their assigned layers. The package-layout test enforces the mapping and dependency direction.

This matters for substrate decisions because durability code now has a real boundary:

```text
state substrate semantics
    -> runtime checkpoint mechanics
    -> memory governance consumers
    -> API / CRG / harness surfaces as appropriate
```

A production persistence implementation should fit those boundaries rather than force provider-specific semantics upward into memory doctrine.

---

## 7. Persistence mechanisms that are still not substrates

### Graph databases

Neo4j, FalkorDB, Neptune, Kuzu, and similar systems are storage/database technologies until an Agent Memory `TemporalGraphPort` implementation is built and qualified against them.

The current Graphiti probe's use of Kuzu is not a production endorsement.

### Postgres / SQLite

Postgres and SQLite remain persistence mechanisms. They may be excellent implementation choices for a future substrate, but neither currently has an Agent Memory `TemporalGraphPort` implementation or canonical-substrate qualification artifact.

### Markdown / files

Files and Markdown may be appropriate representations for bounded memory artifacts. They are not canonical substrates by implication.

### Object stores / event logs

Likewise, object stores and event logs may participate in backup, evidence, or implementation-specific durability. Their presence does not establish the current-state, migration, deletion, tenancy, or authority contracts required of the canonical substrate.

---

## 8. Current #363 persistence state

The original #363 audit finding bundled several distinct defects. Most of the **reference-profile correctness** defects are now remediated.

Completed slices:

| Slice | Result |
| --- | --- |
| #413 | component-owned checkpoint state; restart orchestration no longer scrapes private state |
| #414 | serialized generation publication, CAS conflict detection, journal integrity |
| #417 | governed schema/profile migration and rollback |
| #419 | public checkpoint transaction-support seam |
| #422 / #423 | owner-level restart contracts for projection, write-claim, and telemetry state |
| #424 / #425 | atomic auxiliary composition into the same committed generation |

The resulting reference profile proves coherent single-host checkpoint generations with fail-closed corruption, stale-writer refusal, governed migration, and owner-specific recovery semantics.

What remains open is **production qualification**, not permission to relabel the reference implementation:

1. qualify at least one non-toy durable canonical substrate/provider against the current contract;
2. decide whether product requirements need an external monotonic anchor against whole-state-directory rollback;
3. select and qualify a production transaction mechanism when a production substrate is chosen.

No database or graph provider should be promoted merely to make #363 close.

---

## 9. Production substrate qualification gate

A candidate production substrate must earn the role by executable evidence. At minimum, qualification must cover:

- the full `TemporalGraphPort` behavioral surface used by the governed adapter;
- exact identity and version of the provider/backend;
- restart reconstruction without losing currentness, scope, tombstone, or identifier semantics;
- compatibility with the runtime's generation/CAS publication contract or an explicitly equivalent transaction contract;
- stale-writer and concurrent-writer behavior;
- crash/torn-write behavior;
- migration and rollback semantics;
- deletion and residue behavior;
- tenant/scope isolation at the Agent Memory boundary;
- deterministic recovery of required governance interpretation;
- evidence that provider-native ranking, inference, or graph semantics do not acquire authority;
- source-rights and operational deployment posture;
- explicit limitations rather than inferred production maturity.

A provider may use a stronger native transaction model than the reference file protocol. It does not need to imitate the implementation, but it must satisfy the same correctness obligations.

---

## 10. Summary

| Category | Current state |
| --- | --- |
| First-party temporal substrates | **2**: one reference implementation, one declared/experimental Graphiti adapter |
| Restart-safe reference substrate | **1**: `InMemoryTemporalGraph` under the reference checkpoint profile |
| Production-qualified canonical substrates | **0** |
| First-party governed memory implementations | multiple, above the substrate layer |
| Qualified external resource-memory providers | **2**, both bounded and `authority_effect: none` |
| CRG package boundary | **implemented** |
| Layered package architecture | **implemented and enforced** |
| Reference persistence correctness remediation | **implemented through #425** |
| Production persistence qualification | **open under #363** |

The gap is now narrower and more useful: Agent Memory has a concrete persistence contract worth qualifying a production implementation against. It does not yet have evidence to call any non-toy canonical substrate production-qualified.

---

## 11. Maintenance rule

Update this inventory in the same change that:

- adds or removes a `TemporalGraphPort` implementation;
- changes a substrate's checkpoint capability;
- adds a canonical-substrate qualification artifact;
- changes CRG/module ownership or package structure;
- changes an external provider's earned qualification status;
- materially changes #363 production durability posture.

A substrate or durability change that leaves this inventory stale is a Tier 1 governance drift defect.
