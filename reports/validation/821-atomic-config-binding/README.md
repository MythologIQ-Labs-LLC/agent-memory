# #821: atomic configuration binding for the SQLite runtime

**Frozen runtime candidate:** `d0d2a97c63b50700001da06b9df7fe81b580fc09` on
`claude/happy-lovelace-32j5im`. Commits after it on the branch touch `reports/` only.

**Status:** the preregistered durability contract (PREREGISTRATION.md plus AMENDMENT-1.md) holds
at the frozen SHA. The independent review reports no blocking finding. This is not merged, not
activated, and no default is changed. No hosted Actions ran: the branch was pushed (no
push-triggered workflow matches it) and no PR was opened (see §8).

## 1. Lineage

`main 38f6a7dc` → #805 `28f257c9` → #815 `77c472e6` → #816 frozen runtime `e13d8c58` → #816
branch head `d2fc9782` (evidence only) → this branch. Each step is a strict ancestor, confirmed
against `origin` on 2026-10-15. No predecessor branch was modified.

## 2. The window and the fix

**The window.** The SQLite config-bound runtime committed generation N+1, and only then wrote
`configuration-binding.json` (the `_bind_current_base` hook after COMMIT, and in `create` after
generation 1). A process that died between the two left N+1 committed with the binding at N, and
recovery refused the store for good. It was reproduced on `d2fc9782` with real process kills
(`fail-first/crash-window-d2fc9782.json`), and the byte-frozen `fixtures/821-legacy-stores/stranded`
store was produced by `d2fc9782` itself. Its database is byte-identical to `coherent`; only the
binding file lags.

**The fix: protocol `sqlite_same_transaction_config_binding_v1`.**

- **The binding is a row.** It is the singleton row `runtime_configuration_binding`, written by the
  owning runtime inside the generation's own SQLite transaction, after the runtime state and
  journal row and before COMMIT (`SQLiteRestartSafeRuntime.bind_generations`). A generation and its
  binding commit or roll back as one transaction. Generation 1 is included.
- **What the row binds:**
  - the configuration digest, the plan digest and the plan;
  - the required projections;
  - the tenant;
  - the generation's substrate, governance, interpretation and journal-tail digests;
  - an unkeyed record checksum over all of the above.
- **Recovery verifies and never repairs.** It never writes. If the table exists, the row is
  required; the legacy file is read only when there is no table.
- **The binder verifies the row it replaces** exactly as recovery would, against the handle's
  previous generation. A changed row raises `RuntimeCheckpointConflict` and the generation rolls
  back. The binder also refuses a visibility obligation the plan does not require.
- **Generation witness (amendment 1).** `generation-witness.json` is an advisory high-water mark
  that can only refuse:
  - **When it is written:** first inside generation 1, then after every COMMIT, never before one.
    It may lag the database but never lead it.
  - **When it is read:** before the database.
  - **What it refuses:**
    - a database behind it;
    - a database whose journal disagrees with it;
    - a witness that cannot be read;
    - a witness without its database;
    - a witnessed store without its binding table.
- **Pre-#821 stores** are verified through their file exactly as before. The first generation a
  current runtime publishes writes the row and the witness, and the file is then left
  byte-unchanged. A stranded store stays refused.

**Unchanged** (A7, proven below): the substrate digest, the governance digest, the journal record
schema 1.0.0 and the chain material.

## 3. Interruption matrix (crash harness at the frozen SHA)

The crash harness is `probes/crash_window.py`, recorded in `runs/crash-window-d0d2a97.{txt,json}`.
In the table, "gen" columns give state / row / witness.

| Phase | Point | `d2fc9782` | `d0d2a97`: gen | `d0d2a97`: reopen |
|---|---|---|---|---|
| steady | before COMMIT | recovers 2 | 2 / 2 / 2 | recovers 2 |
| steady | right after COMMIT | **refused (window)** | 3 / 3 / 2 | **recovers 3** |
| steady | during binding publication | **refused (window)** | 2 / 2 / 2 | rolled back; recovers 2 |
| steady | after the operation | recovers 3 | 3 / 3 / 3 | recovers 3 |
| create | after generation 1 COMMIT | **refused (window)** | 1 / 1 / 0 | **recovers 1** |
| create | before generation 1 COMMIT | refused | no state | refused (by design, §8 of the preregistration) |

The reviewer's p1 matrix (10 kill points × 7 phases) and p10 (kills in and around the witness
write) show 0 split states on the candidate, against 24 violations on the base.

## 4. Tests

**`reference/tests/test_821_atomic_config_binding.py`: 42 tests.** They cover M1–M30 and the
review findings F6 and N1–N5.

- **Fail-first runs:**
  - `fail-first/base-run-d2fc9782.log`: the original 24 tests on the base, with 12 failures and
    17 errors traced to the window or the absent binding. The controls pass.
  - `fail-first/review-n1-n5-on-96a3f59.log`: the N-repair tests on the unrepaired `96a3f59`.
- **Existing tests retargeted, each recorded in its commit:**
  - `test_816` F3 now injects after COMMIT, where only in-memory evidence runs. The reviewer
    confirmed it is still discriminating with a mutant.
  - `test_developer_facade` asserts the row instead of the file.
  - The `test_governance_attestation` pre-#562 fixture gets the legacy file it historically had,
    and no witness.

## 5. Validation at the exact SHA

All runs are on clean detached worktrees, with Python 3.13.16, SQLite 3.45.1 and
`reference/requirements.txt`.

| Gate | Result |
|---|---|
| Full suite, base `d2fc9782` | 3033 tests, 4 failures (`runs/full-suite-base-d2fc9782.txt`) |
| Full suite, `69ccd3a`, `96a3f59`, **`d0d2a97`** | 3059, 3070, **3075** tests. Each has **the same 4 failures as the base**: the Runtime Baseline equivalence guard, two `test_770` freshness guards and `test_644_v7_gauntlet_identity`. These are environment and declaration guards. |
| Focused suites | 225 tests OK: SQLite production, transactional generations, configured restart, governance attestation, incremental attestation, #774, #802, #809 legacy upgrade (on the real v7-origin stores), canonical-json-v2 SQLite and transaction, restart, doctor, facade, #816, #821 |
| #786 v2, v3 and #809 security replays, fresh | 7 families, **all PASS**. The **`observations_sha256` of every family is byte-identical** to the frozen #816 record at `e13d8c58`. Manifests bind `d0d2a97c` (`security-replays-d0d2a97/`). |
| `test_context_package` (#691) | Trial merge `6edc28a3` + `d0d2a97` auto-merges `surface.py` and `adapter.py`. 87 tests OK; the demo reports ALL CHECKS PASSED (`runs/trial-merge-691-*.txt`). |
| A10 / M21 downgrade | The pre-#821 runtime refuses created and migrated stores and still opens an untouched legacy store (`runs/downgrade-d0d2a97-vs-d2fc9782.json`). |

## 6. Independent adversarial review

`review/REVIEW-821-independent.md`, with probes p1–p13 and their outputs. The reviewer was a
separate agent working read-only in its own worktrees.

**First review, at `69ccd3a`.**

| Finding | Severity | Disposition |
|---|---|---|
| F1: a lost database was re-created as empty memory | **Blocking** | **Fixed.** The witness refuses a missing database (W4). |
| F2: rolling back only the database file was undetected | Should-fix | **Fixed.** W1 and W2. |
| F3: the legacy-file fallback was reachable while the table existed | Should-fix | **Fixed.** The table requires its row; N4 also requires the table for a witnessed store. |
| F4: M21 had no record | Should-fix | **Fixed.** See `runs/downgrade-*`. |
| F5: the binder trusted the row it replaced | Note | **Fixed.** Full verification. |
| F6: doctor misreported binding presence on failure | Note | **Fixed.** |
| F7: migration is one-way | Note | **Documented** in docs/47. |
| F8a: recovery reads are not done in one snapshot | Note, pre-existing | **Open**, residual. |
| F8b: an out-of-plan visibility obligation stranded the store | Note, pre-existing | **Fixed.** The binder refuses it and the generation rolls back. |
| F8c: a bare base runtime | Pre-existing | Unchanged; fails closed. |
| F9: wording, and a connection leak in `create` | Note | **Fixed**, except the agmi wording (§8). |

**Re-verification at `96a3f59`.** No blocking findings. New notes N1–N5 were all fixed at
`d0d2a97`:

- N1: the witness is now read before the database.
- N2: the generation-0 witness is now written inside generation 1.
- N3: any `OSError` on the witness is now refused as unreadable (W3).
- N4: a witnessed store now requires its binding table.
- N5: the refusal now names the deliberate-restore step.

**Final check at `d0d2a97`.** **PASS.** N1–N5 are confirmed fixed, and no new findings were
raised.

- **N4 cannot strand a migrating legacy store.** The reviewer checked a witness write that fails
  or is interrupted after COMMIT, and a kill between COMMIT and the witness write (p10, p14).
- **Regression sweep:** p1, p2, p3, p5, p7 and p9.
- **Full suite:** 3075 tests, with the same 4 failures as the base.

The only open items are the pre-existing F8a and the agmi wording (§8).

## 7. Residuals (recorded, not hidden)

- **Unkeyed local state.** The row checksum and the witness detect corruption, mismatch and
  partial rollback. They are not authentication.
  - Rolling back the whole directory, deleting the witness and the binding table together, or a
    storage-level writer (raw SQL, a second `SQLiteTemporalGraph`) is the privileged #816
    storage layer.
- **F8a, pre-existing.** Recovery reads are not done in one SQLite read transaction. A writer
  committing during another handle's open can make that open refuse as stale. It fails closed,
  and a reopen succeeds.
- **Deliberately restoring a backup** over a live store is refused as a rollback until the operator
  removes `generation-witness.json`; the refusal says so.
- **The witness lags after a post-commit write failure.** If an `OSError` stops the witness write
  after COMMIT, the generation stays committed and the next generation rewrites the witness.
  `generation_witness_current` reports the lag.
- **A crash during a store's first `open`** before generation 1 commits leaves a refused directory.
  This is the pre-existing "never reinitialize" posture.
- **Out of scope:**
  - The file-checkpoint profile is unchanged and has an analogous manifest-then-binding sequence.
  - F2 (in-memory administrative seams) is unchanged and not widened. A generation still
    publishes what it published before, now with its binding in the same transaction. The binding
    grants no authority.

## 8. Integration handoff

- **Landing order:** #805 → #815 → #816 (`d2fc9782`) → this branch, as a fast-forward. Then #691
  merges cleanly, per the trial merge.
- **Protected runtime files change**: `state/sqlite_substrate.py`, `runtime/sqlite_runtime.py`,
  `runtime/configured_restart.py`, `runtime/doctor.py` and `api/surface.py`.
  - A Runtime Baseline successor declaration must therefore cover the integrated head.
  - **No register or declaration was regenerated here.** That needs owner authorization.
- **agmi gauntlet evidence.** `reports/gauntlet/agmi-agent-memory-v1/` describes its T1–T9
  boundary using the "configuration-binding sidecar", which new stores no longer have. That is
  accepted evidence, so it was not edited. Re-run it at integration.
- **Release note:**
  - Migration is one-way: any generation a current runtime publishes makes the store unopenable
    by pre-#821 runtimes. Even a `recall` publishes one.
  - New stores carry `generation-witness.json`, and no `configuration-binding.json`.
- **No PR was opened.** All 82 workflows that listen on `pull_request` would fire on a draft too,
  and at least `agmi-agent-memory-qualification` and `canonical-reachability` match this diff.
  Hosted Actions were out of bounds for this task.
- **No contract version change.** The facade surface is unchanged; posture gains the additive
  `configuration_binding_scheme`.
