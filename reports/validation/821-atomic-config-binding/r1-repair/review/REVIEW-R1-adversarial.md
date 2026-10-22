# Adversarial implementation review of the R-1 repair (`52537ecf` against `d0d2a97c`)

An independent agent, separate from the implementer, did this review read-only. It used its own
scratch worktrees and probes, and did not touch the candidate worktree. Its probes are in
`../probes/` (`p1_fault_inject.py`, `p2_kill_stress.py`, `p4_crash_points.py`) and their outputs
are in this folder (`out-p1.txt`, `out-p2-*.txt`, `out-p4.txt`).

**Verdict: PASS, with no blocking finding.**
- R-1 reproduced on `d0d2a97c` under sensitised kill stress (`out-p2-frozen-s2.txt`: an empty
  witness, `JSONDecodeError: Expecting value`).
- The same probes cannot reproduce it on the repair.
- The reviewer could not produce any of the following: a witness that leads the database, a
  partial or foreign witness, or a refusal when the database is fine.

## Findings (all NOTE)

1. **The fd leaks if `os.fdopen` raises.** Reproduced with p1 (MemoryError, OSError). Suggested fix:
   close the descriptor on failure, as `tempfile` does.
2. **A KeyboardInterrupt delivered between `_exclusive_temporary()` returning and the `try` leaks the
   fd and leaves an orphan temporary.** Simulated with p1. The published witness is unaffected.
3. **Orphan temporaries from killed writers accumulate without bound.** p2 left 23, 32 and 20 over
   about 240 kills per seed with the window widened; frozen left 0. The reviewer found them harmless
   to every reader:
   - recovery, `_refuse_witness_without_database`, the facade checks and doctor test only the exact
     witness name;
   - `backup_to` uses the SQLite backup API;
   - no glob or copy touches the store root.

   Suggested follow-ups: document them, and optionally have doctor count them. Do not sweep other
   writers' files.
4. **The earlier evidence probe `../../review/probes/p10_witness_crash.py` re-implements the old
   `record()`.** It does not test the repair; p4 does.
5. **docs/47 and the validation README did not describe the repair or its residuals.**
6. **The unreadable-witness hint ("remove …") is too broad.** It is wrong advice for a permission
   error, or for a newer schema on downgrade.
7. **Two gaps in the tests:**
   - the late-rename test can assert a strict lag;
   - `race()` should kill writer A if `communicate` times out.

## What held

- **The new tests.** 5/5 passed on the repair, three repeats, and the full `test_821` passed (47). On
  `d0d2a97c` they fail for the right reasons. No hooks leak between tests.
- **Every injected fault in `record()`** left the old or the new complete witness, no temporary of
  ours, and an `OSError` for `_record_witness`. The fault points:
  - `EDQUOT` on create;
  - 8 × `EEXIST`;
  - `ENOSPC` on write;
  - `EIO` on fsync;
  - rename failure;
  - KeyboardInterrupt in rename;
  - rename done, then an error;
  - directory fsync `EINVAL`.
- **Cleanup can never remove the published witness or another writer's temporary.**
- **Exclusive create.** strace shows `O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC, 0666`. A pre-planted
  symlink is refused and its target untouched. Names stay unique across threads, after fork, and
  across hosts that reuse pids.
- **Mode.** It matches `open("wb")` under umask 0022, 0077, 0027, 0002 and 0000.
- **Durability order** (strace of a real `remember`):
  1. create;
  2. write;
  3. fsync the file;
  4. close;
  5. rename;
  6. fsync the directory.

  The WAL is synced (`synchronous=FULL`) before the witness write.
- **Crash points (p4).** 6 kill points, run alone and with B beside a held A: 12/12 OK.
- **A late rename is lag only.** `runtime_journal` is insert-only, and the witness value is a
  committed `(generation, digest)` read after COMMIT.

## Dispositions at `e88bced2`

Notes 1, 5, 6 and 7 are fixed. Notes 2 and 3 are documented residuals. Note 4 is recorded. Details
are in `../README.md`.
