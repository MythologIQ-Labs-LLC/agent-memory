# #840 temporary-file staging on the integrated v7 candidate: preregistered fail-first tests

Written before any runtime change, on `integration/v7-786-836-reconciliation-no-ci` at
`0f90aa8e3cdecd83c33d017baf0689ce9f02b944` (runtime tree `e9dce74b`).

## Scope

PR #840 (`review/840-checkpoint-temp-isolation-no-ci` at `360de78f`) is stacked on an older #836 commit
(`ab4e549d`) and conflicts with the integrated head, so it is **not merged**. Only its security repair is
evaluated here. Its host-activation guard is assessed separately (section 5).

The integrated runtime stages whole-file writes through five writers:

| Writer | Integrated temporary | Opened with |
|---|---|---|
| `api/surface.py` `_atomic_write_text` (packaged runtime config on first open) | `.<name>.<pid>.<thread-id>.tmp` | `open("w")`: follows symlinks, truncates |
| `runtime/restart_runtime.py` `_atomic_json_write` (manifest, governance, checkpoint files) | `.<name>.tmp` (one shared name) | `open("wb")` |
| `runtime/configured_restart.py` `_atomic_json_write` (configured-runtime records) | `.<name>.tmp` | `open("wb")` |
| `memory/checkpoint_migration.py` `_atomic_json_write` (migration records) | `.<name>.tmp` | `open("wb")` |
| `runtime/checkpoint_transactions.py` `CheckpointTransactionSupport._atomic_journal_write` (journal restore) | `.<name>.tmp` | `open("wb")` |

Two other staging paths are already exclusive and are **controls**: the #786 store-identity claim (`open("x")`, then
`os.link`) and the #821 generation witness (`O_CREAT | O_EXCL`, random suffix).

## Threat model

An actor that can create directory entries in a store's directory, but has no other authority, must not be able to
do any of the following through the store's own writes:

- redirect a write outside the store;
- truncate or clobber an unrelated file;
- publish a torn or empty record.

Concurrent writers of the same record, and crashes or ENOSPC between create and rename, must not do so either.

## Fail-first tests (`reference/tests/test_v7_840_temporary_staging.py`)

Each test runs against all five writers.

| ID | Property | Expected on `0f90aa8e` |
|---|---|---|
| S1 | A symlink planted at every predictable temporary name, pointing at a victim file outside the store, leaves the victim byte-identical. The target becomes a regular file holding exactly the payload. | **RED** for all five |
| S2 | Two consecutive writes of the same path from one thread stage through different temporaries, so the name cannot be predicted from pid and thread. | **RED** for all five |
| S3 | N concurrent writers of one path, held at `fsync` until all have staged, all succeed. The target holds exactly one complete payload, and no temporary remains. | **RED** for the four shared-name writers, GREEN for `surface` |
| S4 | An `fsync` failure (ENOSPC) leaves the previous target bytes intact and no temporary behind. | **RED** for all five (temporary leaked) |
| S5 | A `replace` failure leaves the previous target bytes intact and no temporary behind. | **RED** for all five |
| S6 | The published file's mode is `0o666 & ~umask`, as before. The repair must not silently change durable-file permissions. | GREEN (regression guard) |

Interrupted initialization, through `AgentMemory.open` on a fresh root:

| ID | Property | Expected on `0f90aa8e` |
|---|---|---|
| I1 | A first open interrupted while writing the packaged configuration (`fsync` fails) raises. A retry with the same identity succeeds, binds the same store identity, and leaves no temporary in the root. | **RED** (temporary leaked) |
| I2 | A first open with a symlink planted at the predictable configuration temporary leaves the victim untouched and opens normally. | **RED** |
| I3 | A first open interrupted after the identity claim, at runtime creation, is completed by the claiming identity, refused for another project, and leaves no temporary. | GREEN (integrated #786 behaviour; control) |
| I4 | A symlink planted at the predictable identity-claim temporary is not followed. The victim is untouched, whether the open succeeds or refuses. | GREEN (control: `open("x")`) |

## Repair rule

Carry only the security repair: exclusive creation (`O_CREAT | O_EXCL`, plus `O_NOFOLLOW` where available) with an
unpredictable per-write name, and removal of the temporary on any failure before the rename. Keep these unchanged:

- function names, because existing tests patch them by name;
- payload bytes, fsync and directory-fsync order;
- file modes, i.e. `0o666 & ~umask`, the same decision as the #821 witness (review R-1).

#840's `NamedTemporaryFile` would change published files to `0o600`. That is a permission change, not part of the
repair, and is left for an owner decision.

Store profiles, facade identity binding and envelope contract 1.8.0 must be unaffected. The full suite must stay green.

## Host-activation guard (assessed, not carried by default)

#840 adds `agentmem_ref.api.host_activation.open_qualified_memory`. It is a host-side wrapper that refuses to yield a
facade unless `legacy_upgrade_status()` reports `fresh` or `legacy_qualified` with exactly 0 legacy facts. The
assessment checks it against #809 legacy-store qualification on the integrated tree:

- whether `legacy_upgrade_status()` exists with those fields;
- how the wrapper composes with store-open 1.0.0, where a legacy multi-project store is already refused at open;
- whether it adds a protected-surface API that requires declaration.

The result is recorded in `ASSESSMENT.md`.

## Addendum: harness correction before any runtime change

The first fail-first run (`logs/fail-first-0f90aa8e.txt`) gave 26 failures. All the predicted REDs were RED, and
S6, I3 and I4 were GREEN, but S4 and S5 also failed for the wrong reason: every subtest staged in one shared
directory, so the first writer's leaked temporary was attributed to later writers too. The tests now give each
writer its own directory. The runtime was not changed in between, and `logs/fail-first-corrected-0f90aa8e.txt` is
the binding fail-first result.
