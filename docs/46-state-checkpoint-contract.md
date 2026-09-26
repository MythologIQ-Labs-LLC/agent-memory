# State checkpoint ownership contract

Status: **implementation profile for issue #363, including auxiliary owner contracts and composed auxiliary checkpoint custody**

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
| projection declarations and superseded versions | `ProjectionStore` | derived correctness/deletion-residue state | owner-defined export/restore; optionally composed through `ComposedRestartSafeRuntime` |
| write-claim records and audit evidence | `SharedWriteCoordinator` | coordination/evidence state | owner-defined export/restore; pre-crash active claims invalidate rather than revive; optionally composed through `ComposedRestartSafeRuntime` |
| retained minimized telemetry records | `TelemetryStore` | derived operational state that may participate in deletion-completeness evidence | owner-defined export/restore of records, expiry, and key-generation identity; optionally composed through `ComposedRestartSafeRuntime` |

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

## SQLite governance persistence: `gsect-v1` (#562)

This applies only to the qualified SQLite profile (`sqlite_transactional_runtime_v1`). The adapter still owns its state and exports the same v1 governance fields. What changes is how the SQLite runtime persists and commits them.

Before #562, every generation, including every governed recall, serialized the whole governance snapshot to canonical JSON, hashed it, and rewrote it inside the runtime-state row. That scheme is `full-json-v1`, and its digest has the form `sha256:<hex>`. Its cost grew with retained state.

`gsect-v1` persists governance as sections in the same SQLite transaction as canonical rows, the runtime-state envelope, and the journal record:

| section kind | sections | stored as | committed by |
| --- | --- | --- | --- |
| keyed map | `fact_scope`, `fact_memory`, `current_fact_by_memory`, `state_version`, `tombstones` | one `governance_entries` row per key | per-section root over 256 buckets of entry hashes |
| append-only log | `events` (the audit log) | one `governance_log` row per record, each carrying its chain link | hash chain: record count + head |
| residual | tenant, scalars, disputes, shared-space members, rejected values, containment violations, extension state, visibility snapshots | one `governance_residual` row | one digest of its canonical JSON |

The governance root is `gsect-v1:<hex>`: a hash over the scheme, the five map roots, the log count and head, and the residual digest.

**What generation N attests.** Its journal record binds `governance_digest`, the root after generation N, alongside the substrate digest, the interpretation digest, and the previous record digest. The journal record schema is unchanged (1.0.0), because the digest string names its own scheme.

**Normal commit.** The adapter tracks which map keys changed and which log records were appended since the last publication. The runtime writes only those rows. It updates only the touched buckets, extends the chain, rewrites the residual if its content changed, and computes the root from the maintained bucket digests. A section replaced wholesale, or a log edited rather than appended to, falls back to one full publication of the same root. Cost is O(changed entries + touched buckets + residual size), independent of retained facts and audit length.

**Checkpoint.** An explicit checkpoint is an ordinary publication; no separate snapshot is materialized.

**Recovery (full verification).** Every entry hash is recomputed from its stored value, and every entry must sit in its own bucket. Every bucket digest, every chain link, the residual digest, and the root are recomputed from the stored rows alone. The root must equal both the runtime-state envelope and the journal tail. The journal chain is verified end to end as before. Unknown sections, gaps in the log, and a missing residual all refuse recovery.

The maintained bucket index (`governance_buckets`) is derived data. It is trusted only after this process rebuilt it or verified it row for row, so a tampered index cannot change a recovery answer; the next publication rebuilds it.

**Envelope versions and migration.**

| runtime-state envelope | governance | digest |
| --- | --- | --- |
| `1.0.0` | embedded snapshot | `sha256:` (`full-json-v1`) |
| `1.1.0` | `governance_scheme: gsect-v1`, no embedded snapshot | `gsect-v1:` |

- A `1.0.0` store recovers under full-JSON verification. Its next generation migrates it atomically: all sections are written, and the envelope becomes `1.1.0`, in one transaction. A failed migration generation leaves the legacy store intact.
- Earlier journal records keep their `sha256:` commitments and are never reinterpreted. A mixed chain verifies end to end.
- An envelope whose schema and scheme disagree is refused.
- Migration is forward-only. Earlier code refuses a `1.1.0` envelope rather than misreading it.

**Tracking boundary.** Map sections are tracked key by key, so their values must be replaced, not mutated in place. The audit log must only be appended to. The residual has no such requirement, because it is hashed by content. Under the reference test suite, every publication is re-read from the rows and compared with a full export (`AGENT_MEMORY_GOVERNANCE_SELF_CHECK=1`), so a governance change that escapes tracking fails loudly.

Tests: `reference/tests/test_governance_attestation.py`.

## Auxiliary correctness-state contracts

Issue #422 defines owner-level restart contracts. They are intentionally not
normalized into one "persist everything" rule.

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

Restore preserves the distinction between:

```text
matching key generation available -> targeted membership can be evaluated
matching key generation unavailable -> deletion completeness remains false
```

Restart cannot turn an unavailable retired key into proof that no retained
telemetry belongs to a deleted memory.

## Atomic auxiliary composition

Issue #424 adds `ComposedRestartSafeRuntime` as an opt-in composition profile.
The runtime receives explicit component factories from the host. It does not
search process globals and it does not import higher-layer component semantics.

Each composed owner exports its own checkpoint snapshot. The runtime places a
versioned auxiliary custody envelope under the governed adapter's declared
`extension_state` seam:

```text
runtime_auxiliary_checkpoint_v1
    -> component id
        -> owner snapshot
        -> snapshot digest
```

That custody envelope is part of the normal governance payload. Therefore the
existing #414 transaction already provides the publication boundary:

```text
auxiliary owner snapshots
    -> governed extension_state
    -> governance payload digest
    -> runtime manifest
    -> generation journal
```

No parallel auxiliary commit exists. A stale writer that cannot publish the
normal governance generation also cannot publish newer auxiliary state. A torn
or mixed-generation governance payload fails the existing governance digest
check before auxiliary recovery begins.

The persisted component-id set must exactly match the host-declared recovery
factories. Adding, removing, or renaming a composed auxiliary owner requires an
explicit migration/profile transition; recovery does not fabricate empty state.
A legacy checkpoint with no auxiliary custody envelope may still recover through
plain `RestartSafeRuntime`, but it cannot be promoted into a composed runtime by
supplying factories after the fact.

The #417 migration contract already treats adapter `extension_state` as a
protected governance checkpoint field. Auxiliary custody is therefore bound to
migration rather than silently stripped by a representation transform.

## What remains open under #363

The ownership, single-host generation-publication, governed migration, public
transaction seam, auxiliary owner contracts, and atomic auxiliary composition
remove the direct reference-profile persistence defects identified in the audit.
They do not by themselves qualify a production storage provider.

Still required:

1. qualify at least one non-toy durable provider against the contract;
2. add an external monotonic anchor if protection against rollback of the entire
   state directory is a product requirement;
3. select and qualify a production transaction mechanism when a production
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
- composed auxiliary owners recover from the same committed generation as
  substrate/governance/visibility state;
- stale writers and mixed-generation payloads cannot partially publish auxiliary
  state;
- composition drift and implicit promotion from legacy checkpoints fail closed;
- incompatible auxiliary checkpoint schemas/owners refuse rather than coerce;
- existing retain/correct/recall/restart, deletion-after-restart, action-authority
  restart, configured-restart, identifier-progress, migration, and full reference
  regression evidence remains green.

Transactional generation acceptance evidence is defined separately in
`docs/47-transactional-checkpoint-generations.md`.
