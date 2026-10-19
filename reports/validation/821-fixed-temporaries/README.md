# #821 follow-up: every whole-file writer stages through an exclusive temporary

- **Head:** `f76ff127b32e241b4afc822d5440e1f39a67b13d`, on top of `5ca4bc5b` (runtime-config.json) and `e88bced2` (the #821 R-1 repair).
- **Delivery:** the patch series is `0001-*.patch` and `0002-*.patch`, applied with `git am` onto `e88bced2`. Nothing has been pushed to an implementation branch.
- **Independence:** this session authored both commits, so it cannot qualify them. Another reviewer must re-qualify them. The #821 R-1 qualification of `e88bced2` is unaffected.
- **Superseded:** `../821-runtime-config-temporary/`. Its fix is now `_atomic_write_text` calling the shared helper, and its 7 tests still pass.

## Defect (on `e88bced2` and `5ca4bc5b`)

Six writers staged into one fixed name opened with truncation:

| Writer | Fixed temporary |
| --- | --- |
| `runtime/restart_runtime._atomic_json_write` (file-checkpoint profile) | `.<name>.tmp` |
| `runtime/checkpoint_transactions` journal restore | `.<name>.tmp` |
| `runtime/configured_restart._atomic_json_write` (legacy binding file) | `.<name>.tmp` |
| `memory/checkpoint_migration._atomic_json_write` | `.<name>.tmp` |
| `evaluation/contract.write_run` | `<name>.tmp` |
| `evaluation/gauntlet_orchestrator._write_json` | `<name>.tmp` |
| Hermes integration `save_config` (found during the fix) | `config.tmp`, and its chmod also followed a planted symlink |

All six reference writers fail all four fail-first tests on `e88bced2` (24/24 cases, `runs/tests-on-e88bced2.log`):
- a writer killed beside another publishes an **empty file**;
- a planted **symlink is followed**;
- a planted **FIFO blocks** the writer;
- a failed rename **leaves its temporary** behind.

The Hermes `save_config` fails three of the same tests: symlink, FIFO and failed rename (`runs/hermes-tests-on-am-821-r1.log`).

For scope: the checkpoint writers hold the checkpoint lock, so for them the race needs a second writer outside it. The planted paths and the cleanup do not depend on the lock.

## Fix

`reference/agentmem_ref/core/atomic_files.py` lives in the core layer and uses only the standard library, so every layer and the evaluation package can use it without importing the runtime. It is registered in `scripts/restructure_package.py`, with its alias at `atomic_files.py`.
- It creates `.<name>.<pid>.<random>.tmp` with `O_CREAT|O_EXCL`, at mode `0o666` less the umask as before.
- It writes the payload, fsyncs where the writer did, and renames the temporary onto the target.
- On any failure before the rename, it closes the descriptor and removes only its own temporary.

All seven reference writers now use it, `runtime-config.json` included. Unchanged:
- function names and signatures, so the existing tests that patch them still apply;
- the bytes written, which are asserted byte for byte;
- the directory fsyncs;
- the no-fsync behaviour of the two evaluation writers.

Hermes `save_config` now creates its temporary exclusively at 0600, inline, because that package does not depend on `agentmem_ref`.

## Validation (neutral venv, same pipeline as the R-1 qualification)

| Gate | Result |
| --- | --- |
| `test_821_fixed_temporaries` (8 tests, per writer) and `test_821_runtime_config_temporary` (7) | OK, 3 of 3 runs |
| Hermes `test_config_temporary` (5) | OK. The rest of the Hermes suite fails the same 2 environment-dependent tests on `e88bced2` and here (package not installed, Hermes source absent) |
| `test_821_atomic_config_binding` (48), `test_816_runtime_owned_writes` | OK |
| 7 security replays | PASS, observations identical to #816 |
| Crash-window probe, `adv821 --reps 3` | OK, same outcomes as `e88bced2` |
| Full suite (3096), without and with the model | The failure set is identical to `e88bced2`: the 4 baseline-freeze guards |

The first pipeline run also failed `test_package_layout`, because the helper was then an unassigned package-root module. Moving it into `core` fixed that; `runs/` holds the final run only.

## Runtime Baseline (protected paths changed against `e88bced2`)

| Path | Blob |
| --- | --- |
| `reference/agentmem_ref/api/surface.py` | `ba8924d4` → `fcd44000` |
| `reference/agentmem_ref/core/atomic_files.py` | new, `d27a5372` |
| `reference/agentmem_ref/atomic_files.py` | new (alias), `bfd2b7cb` |
| `reference/agentmem_ref/memory/checkpoint_migration.py` | `9893e631` → `d12ca921` |
| `reference/agentmem_ref/runtime/checkpoint_transactions.py` | `9306514b` → `4999757a` |
| `reference/agentmem_ref/runtime/configured_restart.py` | `11ec6ac9` → `35ed03f8` |
| `reference/agentmem_ref/runtime/restart_runtime.py` | `85014e40` → `8f5d520b` |

Outside the protected surface: `evaluation/contract.py`, `evaluation/gauntlet_orchestrator.py`, `scripts/restructure_package.py`, the Hermes integration and the tests. A successor declaration must bind the protected blobs. This change edits no register.

## Residual

A writer killed between creating its temporary and renaming it leaves `.<name>.<pid>.<random>.tmp` behind. This is the same accumulation R-1 accepted for the witness (RES-W2). A store-open sweep is not part of this change.
