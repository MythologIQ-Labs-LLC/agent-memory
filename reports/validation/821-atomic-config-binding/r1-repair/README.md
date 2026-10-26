# #821 R-1 repair: one exclusive witness temporary per writer

**Frozen runtime:** `e88bced24157d668179882f63e921ea569df1d51` (tree `4fbd6ebd…`; replay-manifest
runtime tree `4bfe33f2…`). This is a strict fast-forward of the original frozen candidate
`d0d2a97c` (kept immutable as the fail-first comparator) and of the evidence head `42d2d21`.

**Branch:** `claude/eager-dirac-bftkfg-821-r1`. Every commit is `[skip ci]`. No PR, no Actions, no
merge, no Runtime Baseline or register change.

| Commit | Content |
|---|---|
| `ceab2f24` | Fail-first tests and the record of their failure on `d0d2a97c` (no runtime change) |
| `52537ecf` | Runtime repair |
| `e88bced2` | Answers to the adversarial review of `52537ecf`, and docs/47 (**frozen runtime**) |
| evidence commit after `e88bced2` | This folder only (`reports/`) |

## The defect (independent review R-1, #821)

`GenerationWitness.record` wrote `.generation-witness.json.tmp` with `open("wb")` in every writer
process. The SQLite profile serialises writers only within a process, so this could happen:

1. Process A writes and fsyncs the temporary.
2. Process B opens the same name, which truncates A's inode.
3. B dies, or its write fails with `ENOSPC`.
4. A renames the empty inode over the witness.

Every later open was then refused (`generation witness is unreadable`) until an operator deleted
the witness. No committed data was lost.

## The repair (`runtime/sqlite_runtime.py`, `GenerationWitness` only, +43/−8 against `d0d2a97c`)

- **`_exclusive_temporary()`** creates `.generation-witness.json.<pid>.<secrets.token_hex(8)>.tmp`
  with `O_WRONLY|O_CREAT|O_EXCL` (plus `O_BINARY` where defined).
  - On `FileExistsError` it retries with a fresh name, up to 8 times.
  - The mode is `0o666` less the umask, as `open("wb")` gave it. `tempfile.mkstemp` was rejected
    because it forces `0600`.
- **`record()`:**
  - `os.fdopen`, closing the descriptor if that fails;
  - write, flush, file `fsync`;
  - `os.replace` over the witness;
  - directory `fsync`.

  This order is unchanged. On any `BaseException` before the rename completes, the writer removes
  its own temporary and re-raises. `_record_witness` still treats an `OSError` as a lagging witness.
- **The unreadable-witness refusal** now names the remedy:
  - fix permissions, or run the newer runtime;
  - if the witness is damaged and the database is this store's own, remove the witness.
- **Unchanged:**
  - verify-only recovery;
  - the binding row and its binder;
  - the witness value and `check()`;
  - the #816 storage capability boundary;
  - every authority, tenant, deletion and provenance check.

## Tests (`reference/tests/test_821_atomic_config_binding.py`, class `ConcurrentWitnessWriters`, 6 tests)

| Test | `d0d2a97c` | `e88bced2` |
|---|---|---|
| `test_r1_a_writer_killed_beside_another_never_publishes_an_empty_witness`: two real processes, barrier files, faults only at `open` and `rename` | **FAIL 3/3** (`fail-first/`) | ok |
| `test_r1_a_late_rename_lets_the_witness_lag_but_never_lead`: residual pin, strict lag, matching journal digest, reopen | ok | ok |
| `test_r1_another_writer_temporary_is_never_opened_or_truncated`: forced name collision; the other file is byte-unchanged | error (no seam) | ok |
| `test_r1_a_failed_witness_write_removes_its_temporary`: `ENOSPC` at rename | fail (shared temporary left) | ok |
| `test_r1_a_temporary_that_cannot_be_wrapped_is_closed_and_removed`: `os.fdopen` fails | n/a | ok (fails on `52537ecf`: a deleted temporary still open) |
| `test_r1_the_witness_keeps_the_mode_open_wb_gave_it`: umask 027 gives 0640 | ok | ok |

## Validation at `e88bced2` (clean detached worktree, local; `runs/validation-ladder-e88bced2.log`)

| Gate | Result |
|---|---|
| `test_821_atomic_config_binding` | **48 tests OK** (42 original + 6 new) |
| Crash-window matrix (`probes/crash_window.py`, 9 kill points) | Every outcome and durable state is **identical** to `runs/crash-window-d0d2a97.json`, with timing fields excluded (`runs/crash-window-e88bced2.json`) |
| Reviewer kill matrix and 20-kill loop (`runs/r1-kill-*-e88bced2.jsonl`) | Same as at `d0d2a97c`. Pre-commit kills recover N; post-commit kills recover N+1 with the witness lagging; create before generation 1 is refused by design; the loop recovers all 21 facts. |
| Crash points around the new code (`probes/p4_crash_points.py`, 6 points × {alone, B beside a held A}) | 12/12 OK, `PROBLEMS: 0` |
| Fault injection in `record()` (`probes/p1_fault_inject.py`) | Every fault leaves the old or the new complete witness, no temporary and no fd leak. The exception is the KeyboardInterrupt window noted below. |
| Security replays, 7 families | **All PASS.** `observations_sha256` is **identical** to the #816 record (`e13d8c58`) and to the independent `d0d2a97c` re-run, for every family (`security-replays-e88bced2/`) |
| Full suite without the model | 3081 tests: 4 failures, 35 skipped, 1 expected failure |
| Full suite with the pinned model | 3081 tests: 4 failures, 30 skipped, 1 expected failure |
| The 4 failures | The baseline-freeze guards (`test_644`, two `test_770`, Runtime Baseline equivalence). The assertion text hashes the same (`fd1ae14c…`) as at `d0d2a97c`. None are new. |
| Performance (`runs/r5-perf-…jsonl`, 3 alternating runs, N = 100) | `remember` p50 is 5.72–5.80 ms against 5.88–6.18 ms (about +0.2 ms, within noise). `recall` and open/close are within run-to-run noise. File sizes are identical. |

## Witness monotonicity (directive item 5)

- **Can it lead? No.**
  - A writer records `read_runtime_binding()` after its own COMMIT, which is always an already
    committed generation.
  - Under `synchronous = FULL` with WAL, that generation is fsync-durable before the witness is
    written.
  - `runtime_journal` is insert-only, so the recorded digest stays that generation's digest.
- **Can it regress? Yes. This is residual RES-W1, documented here and in docs/47.**
  - Two writers can rename in the opposite order of their commits. The deterministic
    `test_r1_a_late_rename_…` reproduces this.
  - The witness then names an older committed generation of the same history. Recovery accepts it
    as a lag.
  - Rollback detection temporarily weakens to that generation, which is the same exposure already
    accepted for a lag after a post-commit crash.
  - In probe R9 (`runs/r9-stress-…jsonl`), about 75,000 samples under random SIGKILLs showed no
    unparseable witness, no lead and no digest mismatch.
- **Is the repair sufficient for the declared contract? Yes.**
  - The contract is: the witness is advisory, may lag, never leads, and refuses only states it can
    prove are not this store's latest.
  - After the repair, every published witness is one writer's complete record of a committed
    generation.
- **Strict monotonicity would need a different protocol.**
  - It needs cross-process mutual exclusion over the read and the rename, for example recording
    under SQLite's write lock, or an `flock`, at the cost of one more lock acquisition per
    generation.
  - A compare-before-rename without a lock does not close the window.
  - Left for an owner decision; not implemented.

## Adversarial implementation review (`review/`)

An independent agent reviewed `52537ecf` read-only, with probes p1, p2 and p4.

**Verdict: PASS, no blocking findings.** It reproduced R-1 on `d0d2a97c` with the same sensitised
stress, and could not reproduce it on the repair. The 7 notes and their dispositions:

| # | Note | Disposition at `e88bced2` |
|---|---|---|
| 1 | fd leak if `os.fdopen` raises | **Fixed**, with a test |
| 2 | A KeyboardInterrupt between the exclusive `open` and the `try` leaves an fd and an orphan temporary | Residual. Python cannot close this window without masking signals; the published witness is unaffected. |
| 3 | Orphan temporaries from killed writers now accumulate, one per kill in the window | Residual **RES-W2**, documented in docs/47. Nothing reads them: recovery, doctor and the facade test the exact witness name; `backup_to` uses the SQLite backup API. Removing another writer's temporary without a lock is unsafe, so they are left for the operator. Doctor reporting is a possible follow-up. |
| 4 | The existing evidence probe `review/probes/p10_witness_crash.py` re-implements the old `record()` | Recorded. Do not cite p10 for this repair; p4 covers the new code path. |
| 5 | The docs do not cover the repair | **Fixed** in docs/47 and in this record |
| 6 | The unreadable-witness hint is too broad | **Fixed**: permissions and an older runtime are named before removal |
| 7 | The late-rename test should assert a strict lag, and a timed-out race should kill writer A | **Fixed** |

## Residuals

- **RES-W1:** the witness can regress across processes. This is lag only, accepted and documented.
- **RES-W2:** orphaned temporaries accumulate from writers killed between creating and renaming
  them. Each is about 170 bytes and nothing reads them.
- **The KeyboardInterrupt window** of note 2.
- **Pre-existing and unchanged:**
  - `surface.py` `_atomic_write_text` writes `runtime-config.json` through a fixed `.tmp` name, only
    when a store is first created. Two processes creating the same new store at once share the
    `.tmp`-name pattern. This predates #821 and is outside R-1.
  - The F8a recovery-snapshot race.
  - The state is unkeyed, so a whole-directory rollback is not detected.
  - The file-checkpoint profile is out of scope.

## For the integrator

- **The protected runtime blob changes again** (`sqlite_runtime.py` only). The single Runtime Baseline
  successor must bind `e88bced2`'s blobs, not `d0d2a97c`'s.
- **The integration strategy in the review verdict is unchanged.** It uses one cumulative #805 vehicle,
  now fast-forwarded to this branch's head. Whether to declare one successor, whether to bundle
  #691, and the CI budget remain owner decisions.
