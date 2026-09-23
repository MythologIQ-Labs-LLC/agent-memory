# Transactional checkpoint generation semantics

Status: **implementation profile for issue #414 under #363**

This document defines the transaction semantics wrapped around the existing
`reference_file_checkpoint_v1` state representation.

It does not choose a database, change the component checkpoint wire formats, or
claim an external monotonic trust anchor.

## Why this is separate from the durability profile

`reference_file_checkpoint_v1` describes **what state is serialized and how it
is interpreted during recovery**. Issue #413 made ownership of that state
explicit.

Issue #414 addresses a different question:

> When more than one runtime can try to publish a checkpoint, what makes one
> generation canonical, and how does recovery distinguish a completed commit
> from a torn write or stale replay?

Changing publication semantics does not require pretending the state schema is a
new format. The reference implementation therefore keeps the v1 substrate,
governance, and manifest representation and adds a separately named transaction
protocol:

`reference_generation_cas_v1`

## Transaction records

The flat v1 files remain:

1. `substrate.json`
2. `governance.json`
3. `runtime-manifest.json`

The transaction protocol adds:

4. `runtime-generation-journal.jsonl`
5. `.runtime-checkpoint.lock`

The lock is an advisory POSIX `flock` used by the reference file profile. It is
held across compare, component snapshot, payload writes, manifest publication,
and journal append. Because the lock belongs to an open file descriptor, the OS
releases it if the writer process dies. The reference transaction protocol fails
closed on hosts where that locking primitive is unavailable rather than silently
claiming cross-process safety.

The journal is append-only from the runtime's point of view. Each record binds:

- transaction protocol version;
- generation;
- digest of the exact manifest;
- substrate digest;
- governance digest;
- interpretation digest;
- previous journal record digest;
- current journal record digest.

The first record may start above generation 1 when an already-valid legacy v1
checkpoint is baselined. Later journal generations must be contiguous.

## Compare-and-commit rule

Each `JsonRuntimeStateStore` carries the generation and manifest digest it most
recently recovered or successfully committed.

A checkpoint proceeds only when:

```text
observed_generation == currently_published_generation
```

and, when an observed manifest digest exists:

```text
observed_manifest_digest == digest(current_manifest)
```

A store instance pointed at an existing runtime but which has never recovered
that runtime is not allowed to write. It must observe the current generation
first.

Therefore two writers that both recover generation N may both *propose* a next
checkpoint, but after serialization through the lock only one can publish N+1.
The second writer observes current generation N+1 while still holding an
expectation of N and receives `RuntimeCheckpointConflict`. It does not write a
payload.

## Publication order

Within the exclusive checkpoint lock, a successful new generation uses this
order:

```text
validate current manifest/journal
    -> compare observed generation
    -> snapshot component-owned state
    -> fsync + atomically replace substrate.json
    -> fsync + atomically replace governance.json
    -> fsync + atomically replace runtime-manifest.json
    -> append + fsync generation journal record
    -> advance writer's observed generation
```

`runtime-manifest.json` remains the state publication point. The journal record
is the commit witness used by the transaction protocol.

Directory entries are fsynced after replacements/appends in addition to fsyncing
the file contents.

## Crash semantics

There are deliberately no recovery guesses.

### Crash before manifest publication

The old manifest remains canonical while one or both payload files may contain
new bytes. Their digests no longer match the old manifest. Recovery refuses the
state.

This is stricter than silently falling back to whichever payload happens to look
reasonable. The current file profile does not keep a second complete generation,
so there is no safe old payload set to choose automatically.

### Crash after manifest publication but before journal append

The manifest names generation N+1 while the journal head still names N. Recovery
refuses the state as a journal/manifest mismatch.

This creates a small fail-closed window rather than a false successful commit.
A future generation-directory or transactional-store implementation may narrow
that availability cost while preserving the same safety rule.

### Crash after journal append

The manifest and journal head agree on the committed generation. Recovery may
continue if payload and interpretation digests also validate.

## Recovery serialization

Recovery acquires the same checkpoint lock used by writers. A reader therefore
does not inspect the intentional payload-before-manifest interval while a live
writer is still completing a checkpoint.

After acquiring the lock, recovery validates:

1. manifest schema and durability profile;
2. generation journal structure and hash chain when present;
3. journal head against the exact manifest when present;
4. substrate and governance payload digests against the manifest;
5. runtime profile and component interpretation;
6. component-owned checkpoint restoration.

Any mismatch fails closed.

## Legacy v1 compatibility

A pre-#414 `reference_file_checkpoint_v1` runtime has no transaction journal and
its manifest has no `transaction_protocol` field.

Such a checkpoint may still recover after all original v1 digest and
interpretation checks succeed. Recovery records the observed generation in the
runtime instance but does not rewrite durable state merely because it was read.

On the next checkpoint, while holding the transaction lock, the store appends a
baseline journal record for the fully validated legacy manifest and then commits
the next generation. The new manifest declares `reference_generation_cas_v1`.

A manifest that already declares the transaction protocol but is missing its
journal is **not** treated as legacy. It fails closed.

## Replay protection boundary

The journal detects replay of an older `substrate.json`, `governance.json`, and
`runtime-manifest.json` set while the journal head remains at the later committed
generation.

It does **not** provide a trusted monotonic anchor outside the state directory.
An operator or attacker who restores the *entire* directory, including the
journal, to an older mutually consistent backup can also restore the local
history used to detect rollback.

Detecting that stronger rollback class requires an external anchor such as a
trusted monotonic counter, remote append-only ledger, transactional database
revision held outside the restored snapshot, or equivalent mechanism. This
reference file protocol does not claim one.

## Concurrency evidence

Acceptance for #414 requires both logical and actual process-level contention:

- two recovered runtime objects from the same generation yield one next commit
  and one deterministic conflict;
- two separate POSIX processes racing from the same generation yield one commit
  and one conflict;
- the losing writer cannot overwrite the winner's payload;
- a fresh unobserved store cannot write over an existing runtime;
- generation numbers advance monotonically for one continuing writer.

## Failure and replay evidence

Acceptance also requires:

- a simulated crash between component payload writes never recovers a mixed
  generation;
- a manifest published without its matching journal record fails closed;
- replaying an older payload/manifest trio against a newer journal head fails
  closed;
- deleting a journal from a transactional manifest fails closed;
- journal digest tampering fails closed;
- a pre-transaction v1 checkpoint can recover and becomes journal-baselined only
  on its next write.

## What remains after #414

This transaction protocol closes the single-host file-profile generation race.
It does not finish #363.

Still open are:

1. durable ownership/rebuild contracts for auxiliary correctness-bearing stores
   as they enter the composed runtime;
2. explicit schema/profile migration behavior and rollback/refusal semantics;
3. qualification of at least one non-toy durable provider;
4. an external monotonic anchor if the product needs protection against complete
   state-directory rollback;
5. a production transaction mechanism appropriate to the eventually selected
   durable substrate.

No database choice should be used as a substitute for those contracts.
