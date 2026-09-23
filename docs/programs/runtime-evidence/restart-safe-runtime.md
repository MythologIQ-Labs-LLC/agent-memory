# Restart-safe reference runtime

Status: implementation evidence for #282 / persistence follow-on #363

This slice establishes the first executable process-restart boundary for Agent Memory. It is intentionally a bounded reference durability profile, not a storage recommendation.

## Earned claim

`reference_file_checkpoint_v1` proves that a governed reference runtime can stop, reconstruct durable substrate state plus governance-critical interpretation state, and continue enforcing currentness, supersession, scope, rejected-value history, stale-state protection, exact component interpretation, and pending write-to-readable obligations.

The #363 persistence follow-on preserves that state representation while adding explicit state-owner checkpoint contracts and the `reference_generation_cas_v1` single-host publication protocol.

It does **not** prove production HA, distributed consensus, transactional database semantics, protection against rollback of an entire state directory including its journal, or live DashClaw HTTPS restart behavior.

## Durable boundary

The v1 state representation keeps three canonical records:

1. `substrate.json` contains retained episodes/facts and physical temporal state.
2. `governance.json` contains the governance envelope required to interpret that state safely.
3. `runtime-manifest.json` binds both payloads plus the runtime/profile/component interpretation by SHA-256 digest and generation.

The #414 transaction protocol adds two publication artifacts without changing those component state formats:

4. `runtime-generation-journal.jsonl` is an append-only hash-chained witness of committed manifest generations.
5. `.runtime-checkpoint.lock` is the POSIX advisory lock used to serialize checkpoint writers and recovery readers for this reference file profile.

The separation is deliberate:

```text
substrate persisted
  != governance recovered
  != component interpretation recovered
  != generation committed
  != required read paths current
  != quiescent
```

A missing payload, malformed payload, digest mismatch, unsupported schema, changed profile, unavailable required capability, changed component interpretation, broken generation chain, stale-writer conflict, or transactional manifest without its journal causes the relevant checkpoint/recovery path to fail closed.

## Generation publication semantics

Each store records the generation and exact manifest it last recovered or successfully committed. Under the checkpoint lock, publication is permitted only when that observed generation is still current.

Two writers that both recover generation N therefore cannot both publish N+1. The first publishes the next generation; the second receives `RuntimeCheckpointConflict` before writing a payload.

Publication order is:

```text
lock
  -> validate current manifest/journal
  -> compare observed generation
  -> write + fsync substrate
  -> write + fsync governance
  -> replace + fsync manifest
  -> append + fsync generation journal record
  -> advance observed generation
  -> unlock
```

Recovery uses the same lock so it does not inspect the intentional payload-before-manifest interval while a live writer is still completing a checkpoint.

A crash before manifest replacement leaves payload/manifest digest disagreement and fails closed. A crash after manifest replacement but before the journal append leaves journal/manifest disagreement and also fails closed. The reference file profile chooses safety over guessing which bytes the operator probably wanted.

A pre-transaction v1 checkpoint with no journal can still recover after the original v1 integrity and interpretation checks succeed. Its current manifest is baselined into the journal only on the next write. A manifest that already declares `reference_generation_cas_v1` but lacks its journal is not treated as legacy.

The exact transaction contract and rollback boundary are documented in `docs/47-transactional-checkpoint-generations.md`.

## Governance state reconstructed

The first profile preserves or reconstructs:

- tenant identity;
- logical memory state version;
- current fact by logical memory identity;
- superseded physical fact state in the temporal substrate;
- fact isolation-domain/project/task bindings;
- shared-domain membership state used by the reference admission gate;
- disputed state;
- tombstones and deletion obligations already represented by the adapter;
- rejected-value fingerprints and lifecycle history;
- deterministic clock/identifier progress needed to prevent object identity reuse;
- audit/containment records retained by the reference adapter;
- exact runtime/profile/component/capability interpretation;
- #308 visibility snapshots, including pending required projection/currentness obligations.

The implementation currently supports deterministic selector recovery only. An unsupported selector fails rather than silently changing selection semantics.

## Component interpretation

The persisted runtime profile contains exact capability bindings:

- component id/version;
- capability id/version;
- maturity;
- evidence reference;
- source-rights posture.

Recovery currently requires the same exact interpretation. A component upgrade is not assumed compatible. Future #280/#300 compatibility evidence may permit an explicitly proven migration, but version movement alone cannot silently reinterpret durable memory.

## Acceptance scenario

`reference/tests/test_restart_safe_runtime.py` exercises the release-branch scenario through multiple independent runtime objects:

1. Session A retains `release_branch = release`.
2. Session B reconstructs state and recalls it.
3. an externally reviewed correction supersedes it with `release_branch = main`;
4. replay of the stale `v1` correction fails;
5. Session C/D reconstruct the current `main`, preserve historical `release` as superseded, and preserve rejected-value history;
6. project-scope mismatch remains blocked;
7. a pending required projection obligation from #308 remains pending after restart and is not relabeled quiescent;
8. missing provider interpretation fails closed;
9. corrupt governance state fails closed.

`reference/tests/test_transactional_checkpoint_generations.py` extends that evidence with:

- monotonic same-writer generation progression;
- stale-writer compare-and-commit refusal;
- an actual two-process generation race yielding exactly one commit and one conflict;
- refusal of a fresh writer that never observed existing state;
- crash injection between component payload writes;
- crash injection between manifest publication and journal commit witness;
- older payload/manifest replay against a newer journal head;
- missing/tampered journal refusal;
- pre-transaction v1 recovery and first-write journal baseline.

The exact-head runner emits machine-readable restart evidence:

```bash
python reference/run_restart_safe_runtime.py \
  --agent-memory-commit <exact-40-hex-commit> \
  --output restart-safe-runtime.json
```

CI also runs the complete reference regression suite before preserving that artifact, so the transactional generation tests are part of the same exact-head acceptance path.

## Remaining durability work

The persistence program is materially stronger after #413/#414, but it is not a production persistence stack. Remaining work includes:

- explicit checkpoint/rebuild contracts for auxiliary correctness-bearing stores as they enter the composed runtime;
- capability maturity downgrade and compatibility-migration evidence integrated with the common #280/#300 registry rather than the bounded exact-binding profile;
- schema/profile migration semantics with explicit rollback/refusal behavior;
- qualification of at least one non-toy durable provider;
- deletion/rebuild recovery beyond the currently persisted obligation representation where additional stores become authoritative;
- an external monotonic anchor if the product requires detection of rollback of the entire local state directory;
- a production transaction mechanism appropriate to the eventually selected durable substrate;
- live DashClaw external-verdict restart composition where required by #279;
- a service/CLI boundary suitable for the eventual attach-to-existing-stack installation flow.

The important product consequence is that future `agent-memory doctor` behavior can distinguish persistence, successful reconstruction, generation conflict, degraded currentness, and true quiescence instead of reporting a single cheerful but useless `healthy=true`.
