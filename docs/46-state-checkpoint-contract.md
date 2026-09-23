# State checkpoint ownership contract

Status: **implementation profile for issue #363, including auxiliary owner contracts**

This document defines who owns durable Agent Memory runtime state and what the
`reference_file_checkpoint_v1` profile may claim after the #363 persistence
refactors.

It does **not** choose a production database or promote Graphiti. Transactional
publication and compare-and-commit generation semantics are defined separately
in `docs/47-transactional-checkpoint-generations.md`; keeping that contract
separate avoids conflating state ownership with publication mechanics. Governed
schema/profile migration is implemented separately by the #417 migration
contract.

## Core rule

```text
component state is exported and restored by the component that defines its semantics

restart orchestration
    != permission to inspect or rewrite another component's private fields
```

A component may participate in ordinary runtime behavior without implementing a
durability contract. In that case a restart-safe profile must fail closed and
report that the capability is unavailable. It must not infer checkpoint support
from Python object layout, provider resemblance, or the presence of convenient
dictionaries.

## State ownership table

| State | Owner | Classification in v1 | Current checkpoint behavior |
| --- | --- | --- | --- |
| episodes | temporal substrate | canonical retained state | provider-owned export/restore |
| facts and temporal validity | temporal substrate | canonical retained state | provider-owned export/restore |
| substrate write log | temporal substrate | correctness/evidence state for the reference provider | provider-owned export/restore |
| substrate-scoped identifier progress | temporal substrate | correctness state | provider-owned identifier checkpoint; legacy governance field retained for v1 compatibility |
| tenant binding | governed adapter/runtime binding | canonical authority context | retained in governance envelope and adapter construction |
| memory state versions | governed adapter | canonical governance state | adapter-owned export/restore |
| dispute state | governed adapter | canonical governance state | adapter-owned export/restore |
| tombstones | governed adapter | canonical governance state | adapter-owned export/restore |
| fact-to-scope bindings | governed adapter | canonical authority state | adapter-owned export/restore |
| fact-to-memory bindings | governed adapter | canonical authority state | adapter-owned export/restore |
| shared-domain membership | governed adapter | canonical authority state | adapter-owned export/restore |
| current fact per logical memory | governed adapter | canonical currentness state | adapter-owned export/restore |
| rejected/readmitted value history | `RejectedValueRegistry` | canonical correction/readmission state | registry-owned export/restore called by adapter owner |
| audit/containment state | governed adapter | retained audit/governance evidence | adapter-owned export/restore |
| extension state | governed adapter as custody seam for later layers | correctness/evidence state where the owning feature declares it durable | adapter-owned envelope export/restore |
| runtime profile and interpretation digest | restart runtime | canonical interpretation binding | runtime-owned envelope/manifest |
| checkpoint generation and payload digests | state store/runtime | canonical recovery metadata | manifest-owned; publication governed by `reference_generation_cas_v1` |
| visibility snapshots | restart runtime | correctness state for in-flight visibility obligations | runtime-owned governance envelope |
| projection declarations and superseded versions | `ProjectionStore` | derived correctness/deletion-residue state | owner-defined export/restore; not yet composed into `RestartSafeRuntime` |
| write-claim records and audit evidence | `SharedWriteCoordinator` | coordination/evidence state | owner-defined export/restore; pre-crash active claims invalidate rather than revive; not yet composed into `RestartSafeRuntime` |
| retained minimized telemetry records | `TelemetryStore` | derived operational state that may participate in deletion-completeness evidence | owner-defined export/restore of records, expiry, and key-generation identity; not yet composed into `RestartSafeRuntime` |

## Declared substrate durability

`TemporalGraphPort` remains the ordinary runtime contract. It is intentionally
not expanded with persistence methods because doing so would falsely make every
existing external temporal-graph implementation a durability provider.

Durability is an optional, separately detectable contract:

```python
CheckpointableTemporalGraphPort
    export_checkpoint_state()
    restore_checkpoint_state(snapshot)
    identifier_checkpoint()
    restore_identifier_checkpoint(value)
```

`InMemoryTemporalGraph` implements that contract for the reference durability
profile.

A provider that implements `TemporalGraphPort` but not the checkpoint contract
is still usable for non-durable runtime work. `RestartSafeRuntime` must refuse to
checkpoint it.

## Governed adapter durability

The ordinary `GovernedMemoryAdapter` does not automatically claim durability.
The reference restart profile uses `CheckpointableGovernedMemoryAdapter`, a
bounded specialization whose checkpoint methods own access to adapter state.

This distinction is intentional:

```text
usable governed adapter
    != proven restart-safe adapter
```

The restart orchestrator no longer serializes `_state_version`, `_fact_scope`,
`_fact_memory`, `_tombstones`, `_shared_domain_members`, `_rejected_values`, or
other adapter-private structures directly.

The specialization preserves the existing v1 governance wire fields so current
runtime/configuration composition does not need a gratuitous durability-profile
version change merely because ownership was corrected.

## Rejected-value registry durability

`RejectedValueRegistry` owns serialization and restoration of its rejection
records. The v1 wire representation remains the existing row list under
`rejected_values`.

The registry validates a supplied `rejection_id` against the reconstructed
record. A checkpoint cannot change a record's identity while retaining the old
identifier.

## Legacy v1 compatibility

The ownership metadata added by #363 is additive:

- `checkpoint_owner` on new substrate and adapter snapshots;
- `rejected_values_descriptor` inside the adapter snapshot;
- substrate `id_counter`, while the legacy governance `id_counter` remains for
  v1 compatibility.

A legacy v1 checkpoint may omit those additive fields. Recovery may use the
already-existing v1 correctness fields, but it must not fabricate missing facts,
scope, tombstones, rejection history, extension state, or other authority data.

The duplicate identifier location is temporary compatibility debt. The substrate
is the semantic owner. A later explicit migration/profile version may remove the
legacy governance copy after compatibility evidence exists.

Issue #414 adds a transaction journal without changing these component state
representations. A pre-transaction v1 checkpoint can still recover after the
original v1 checks succeed and is baselined into the generation journal only on
its next write. See `docs/47-transactional-checkpoint-generations.md`.

## Auxiliary correctness-state contracts

Issue #422 defines owner-level restart contracts before these stores are admitted
into the general restart runtime. They are intentionally not normalized into one
"persist everything" rule.

### ProjectionStore

`ProjectionStore` exports live declarations and retained superseded versions,
including the basis/version relationships used to compute `current`, `stale`,
and `residual`. Restore is fail-closed on owner/schema mismatch or malformed
projection declarations.

The checkpoint does not store a `stale` or `residual` boolean. Those remain
computed relations against current canonical state. Preserving the declaration
basis is what prevents restart from erasing a deletion-residual relationship.

### SharedWriteCoordinator

The write coordinator exports claim records, terminal status/reason, claim audit
events, event-sequence progress, and a stable commit receipt reference where a
claim reached the adapter.

An in-process lease is **not durable authority**. A record that was `ACQUIRED`
at the checkpoint boundary restores as `INVALIDATED`, emits
`memory.write_claim_invalidated`, and is not inserted into the active-claim
index. A fresh claim is required after restart.

The executable `CommitResult` object is deliberately not reconstructed. Its
stable receipt reference and audit events are retained as evidence; replaying a
Python result object is not a second commit path.

### TelemetryStore

`TelemetryStore` exports privacy-minimized telemetry projections together with
expiry metadata. The projection already carries `key_id`, which is the retained
key-generation identity needed for rotation-safe deletion checks. Raw memory ids
and HMAC keys remain absent.

Restore therefore preserves the distinction between:

```text
matching key generation available -> targeted membership can be evaluated
matching key generation unavailable -> deletion completeness remains false
```

Restart cannot turn an unavailable retired key into proof that no retained
telemetry belongs to a deleted memory.

## Not yet composed into RestartSafeRuntime

The three auxiliary owner contracts above exist **before** runtime composition.
That sequencing is deliberate. `RestartSafeRuntime` still does not own these
objects, and the #414 generation manifest does not yet publish them atomically
with substrate/governance state.

Therefore:

```text
owner checkpoint contract proven
    != atomically composed runtime durability proven

not currently composed
    != safely ignorable
```

The next integration slice may add auxiliary payload ownership to the generation
checkpoint only where the runtime actually composes the corresponding feature.
It must preserve #414 generation/CAS semantics and the owner-specific restart
rules above.

## What remains open under #363

The ownership, single-host generation-publication, governed migration, and
owner-level auxiliary-state slices remove the most direct persistence defects.
They do not satisfy the full #363 exit condition.

Still required:

1. compose correctness-bearing auxiliary stores into the transactional generation
   checkpoint as those features enter the RC runtime;
2. qualify at least one non-toy durable provider against the contract;
3. add an external monotonic anchor if protection against rollback of the entire
   state directory is a product requirement;
4. select and qualify a production transaction mechanism when a production
   durable substrate is chosen.

No database should be selected as a substitute for those obligations.

## Acceptance evidence

The ownership/restart contracts are acceptable when tests prove:

- a checkpoint-capable substrate round-trips its own state and identifier
  progress;
- a valid ordinary substrate without durability support fails closed when used
  with `RestartSafeRuntime`;
- rejected/readmitted value state round-trips through registry-owned methods;
- tampered rejection identity is refused;
- governed adapter state is exported through the declared adapter durability
  specialization;
- legacy v1 snapshots without additive owner metadata remain recoverable where
  their original correctness state is complete;
- `ProjectionStore` round-trips live and superseded declarations without losing
  residual semantics;
- `SharedWriteCoordinator` never revives a pre-crash active claim and emits
  explicit invalidation evidence;
- terminal write-claim audit/receipt evidence survives owner-level recovery;
- `TelemetryStore` round-trips retained projections and expiries while preserving
  missing-key deletion uncertainty;
- incompatible auxiliary checkpoint schemas/owners refuse rather than coerce;
- existing retain/correct/recall/restart, deletion-after-restart, action-authority
  restart, configured-restart, identifier-progress, and full reference regression
  evidence remains green.

Transactional generation acceptance evidence is defined separately in
`docs/47-transactional-checkpoint-generations.md`.
