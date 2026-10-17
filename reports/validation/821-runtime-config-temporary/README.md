# #821 follow-up: `runtime-config.json` through an exclusive temporary

- **Change:** `5ca4bc5be2fa561b1100c5f9346c02ef9e80d148`, parent `e88bced2` (the #821 R-1 repair). Its `reference/` tree is `9d175984`. It is carried here as `0001-runtime-config-exclusive-temporary.patch`, and has not been pushed to any implementation branch.
- **Protected file:** `reference/agentmem_ref/api/surface.py` changes from blob `ba8924d4` to `1a2630cd`. A Runtime Baseline successor must bind the new blob.
- **Independence:** this session authored the change, so it cannot qualify it. Another reviewer must re-qualify it. The #821 R-1 qualification of `e88bced2` is unaffected.

## Defect (reproduced on `e88bced2`)

`AgentMemory.open` writes the packaged default `runtime-config.json` through one shared `.runtime-config.json.tmp` opened with truncation, which is the pattern R-1 found in the generation witness. `probe_rc.py` reproduces three failures:

| Case | `e88bced2` | `5ca4bc5b` |
| --- | --- | --- |
| Two first openers, one killed after opening the temporary (×3) | Config 0 bytes; every later open refuses (`runtime configuration is not valid JSON`), 3/3 | Valid config, reopen OK, 3/3 |
| Symlink planted at the old name | File outside the store overwritten; the config becomes the symlink (CWE-59) | Target unchanged; regular config |
| FIFO planted at the old name | First open hangs | OK |

## Fix

`_atomic_write_text` now opens `.runtime-config.json.<pid>.<random>.tmp` with `O_CREAT|O_EXCL`, keeping mode `0o666` less the umask. It then writes, calls fsync and `os.replace` as before. On any failure before the rename, it closes the descriptor and removes only its own temporary.

## Validation (neutral venv, same pipeline as the R-1 qualification)

- **New tests:** `reference/tests/test_821_runtime_config_temporary.py` adds 7 tests. They pass 7/7 on `5ca4bc5b` in 3 runs. On `e88bced2` there are 5 failures and 1 error, and only the mode test passes.
- **Existing gates:**
  - `test_821_atomic_config_binding` and `test_816_runtime_owned_writes`: OK.
  - All 7 security replays: PASS, with observations identical to #816.
  - Crash-window probe: identical to `e88bced2` once hashes are masked.
  - `adv821 --reps 3`: all OK. The only differences are process IDs and the counts from the timed kill loops.
- **Full suites:** the results are in `runs/` once they finish.

## Not changed (same fixed-temp pattern, outside this request)

- `runtime/configured_restart.py` `_atomic_json_write` (legacy binding file)
- `runtime/restart_runtime.py` (file-checkpoint profile)
- `runtime/checkpoint_transactions.py`
- `memory/checkpoint_migration.py`
- `evaluation/contract.py`
- `evaluation/gauntlet_orchestrator.py`
