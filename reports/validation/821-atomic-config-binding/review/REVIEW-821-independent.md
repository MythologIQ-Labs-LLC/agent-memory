# #821 independent adversarial review: atomic configuration binding

## Scope

| | SHA |
|---|---|
| Base (frozen #816 head) | `d2fc9782570ad4f58ac1cde3d067c1aa4aa5161a` |
| Candidate | `69ccd3a6666bf700b777e31de9b039ae8ecc52d7` (633530c preregistration, 0e90be3 fail-first tests, 69ccd3a implementation) |

I read the preregistration (A1–A10, M1–M21), `git diff d2fc9782 69ccd3a -- reference/agentmem_ref docs`, the new test file and the retargeted #816/facade/attestation tests. Everything ran in detached worktrees under
`review-821/{base,cand}`, plus one mutant copy (`review-821/mut`, made with `git archive`). Nothing in `/home/user/agent-memory` was modified. No network calls and no Actions.

Probes are in `review-821/probes/pN_*.py`; each takes a reference dir as argv[1]. p5 takes `<writer ref> <reader ref>`. Their outputs are `probes/out-pN-{cand,base}.txt`.

Baseline: `tests.test_821_atomic_config_binding` and `tests.test_816_runtime_owned_writes` pass on the candidate (51 tests). Full-suite result: see the end of this file.

## Findings

### F1. BLOCKING: a store whose database disappears is silently re-created as empty memory

- **Scenario.** A #821-created store has no `configuration-binding.json`, and nothing else outside the database marks that a generation was ever published. Suppose `agent-memory.sqlite3` is deleted, moved, or left out of a restore or sync, while `runtime-config.json` (and `derived/`) remain. Then `AgentMemory.open` takes the create branch and starts generation 1 of an **empty** store, with no error. `doctor` reports `not_initialized` / `configuration_valid_state_not_initialized`.
- **Base behaviour.** The base refuses: `incomplete durable state: configuration binding exists without SQLite runtime database`, and doctor reports `incomplete` / `failed_closed`.
- **Why it matters.** This breaks the `AgentMemory.open` docstring: "A partial state marker fails closed so a damaged or incomplete runtime cannot be silently reinitialized as empty memory". It also breaks doc 47's fail-closed list. The candidate quietly narrowed that list to "legacy configuration-binding file present but database absent". The preregistration does not mention this regression.
- **Probe.** `p6_marker_and_rollback.py` (a): on the candidate, open returns `OK gen=1` and a recall of the prior facts returns 0. On the base, open is refused.
- **Fix.** Keep a non-authoritative presence marker outside the database. Write it, with the directory fsynced, before or at generation 1. Have `open` and doctor refuse when the marker is present and the database is absent. This matches the §8 posture: if a crash happens before the first commit, refuse; never reinitialize. Combine it with the F2 fix.

### F2. SHOULD-FIX: rolling back only the database file is no longer detected

- **Scenario.** Copy the closed store's `agent-memory.sqlite3` at generation 3. Then forget a fact and write another, reaching generation 5. Then copy the old database file back over the current one.
- **Candidate behaviour.** It opens silently at generation 3, and the forgotten fact is recallable again.
- **Base behaviour.** The base refused (`configuration binding does not match recovered base checkpoint: generation`). The binding file sat outside the database and bound the newer generation.
- **Why it matters.** The documented boundary (`docs/47-transactional-checkpoint-generations.md` "Replay protection boundary", gauntlet agmi T9) disclaims only **whole-directory** rollback. The change widens the undetected class from "restore the whole directory" to "restore one file", and does not record that.
- **Probe.** `p6_marker_and_rollback.py` (b).
- **Fix.** Use an advisory high-water-mark file `{store_id, generation}`, written after COMMIT.
  - A lagging marker is accepted, so this does not reintroduce the #821 window.
  - Refuse when `marker.generation > db generation`, or when the marker is present and the database is absent (this also fixes F1).
  - At minimum, document the narrowed boundary in doc 47 and in preregistration §7.

### F3. SHOULD-FIX: the legacy-file fallback is still reachable on #821-bound stores, which allows a downgrade

- **The code path.** `read_runtime_configuration_binding()` returns `None` both when there is no table and when the table exists but has no row. `recover` then verifies the legacy file.
- **What breaks.**
  - The docs claim the file is "never consulted again once a row exists".
  - Test `test_m11_deleting_the_row_of_a_migrated_store_does_not_reach_the_legacy_file` is misnamed: the message it asserts (`...base checkpoint: generation`) is the legacy file's own lag diagnostic. The file *is* reached, and the store is refused only because the file lags.
  - Deleting the row (table kept) and writing a file derived from the row's content is accepted with `scheme=legacy_file`. This needs no secret. That file check is weaker than the row check: it binds no tenant and no journal tail.
  - A table that exists but is empty, next to a verifying file, is also accepted. A #821 runtime never produces that state.
- **Severity.** The row is an unkeyed SHA-256, so this is a downgrade path rather than a new forging capability. It still contradicts A3/A4 as written.
- **Probe.** `p3_tamper_types_downgrade.py`: the "DOWNGRADE: delete row + forge legacy file (table kept)" case, and the "legacy store + empty binding table" case.
- **Fix.** If the table exists, require the row and never fall back. Rename M11 or make it assert a row-path diagnostic. Document that dropping the whole table remains a residual, because no unkeyed in-database marker can prevent it.

### F4. SHOULD-FIX: preregistered M21 / A10 has no test and no recorded evidence

- **The gap.** The matrix says M21 is "executed against the `d2fc9782` worktree". No test, run record or probe output for it exists in the candidate.
- **It does hold.** `p5_cross_version_legacy.py` (cand writes, base reads) shows that a candidate-created store and a candidate-migrated legacy store are both refused by the base, and the base writes nothing.
- **Fix.** Record that cross-worktree run under `reports/validation/821-atomic-config-binding/runs/` before freezing.

### F5. NOTE: the binder's continuity check trusts unverified fields of the row it replaces

- **The gap.** `SQLiteConfigBindingStore.publish` checks only the generation column and `payload.plan_digest` of the current row. It does not check the seal or the base digests.
- **Effect.** Suppose a row is rewritten out-of-band while a handle is open, for example to `{"plan_digest": <same>}`. The next generation silently overwrites it.
- **Why only a note.** No false acceptance follows, because the new row is computed from the handle's verified state.
- **Where it matters.** The docs present this as a guard ("requires the replaced row to bind the previous generation under the same plan"). Separately, the `except` branch uses `current = ()` as a sentinel, so a corrupt row yields the misleading message "does not bind generation N under this plan".
- **Probe.** `p3`, last case.
- **Fix.** Verify the previous row with the recovery verifier, against the handle's last published or verified evidence. Alternatively, reword the docs and give corruption its own message.

### F6. NOTE: doctor misreports binding presence on the failure path

On a #821 store whose row fails verification, doctor reports `configuration_binding_present: False`, because that field still means "the file exists". `configuration_binding_scheme` is absent. The success path overrides both fields; the failure path does not. Probe: `p8_doctor_backup_fileprofile.py`. Fix: report row presence (read-only) in the failure report too.

### F7. NOTE: migration is one-way, and an ordinary recall triggers it

Any generation a #821 runtime publishes on a legacy store makes it unopenable by pre-#821 runtimes. That includes a plain `recall`. This is A10 by design, and it is correct to fail closed. The consequence is that a software rollback after deployment strands every store that was touched, and there is no downgrade tool. This belongs in the integration and release notes. Probe: `p5`.

### F8. NOTE: pre-existing problems not introduced by #821 (all three reproduce on the base)

(a) Recovery runs as several autocommit statements, not inside one read transaction.
- Concurrent writers cause spurious open refusals (`canonical substrate digest mismatch`, `governance commitment mismatch`).
- A CAS loser can raise `cannot restore governance after SQLite rollback` instead of `RuntimeCheckpointConflict`.
- The binding-row read adds one more statement outside the snapshot, but it never accepted falsely: the row matched the state in every round.
- Probe: `p4`, three-process kill loop.

(b) A base runtime driven directly can persist a visibility snapshot the plan does not require. That commits a generation, now with its row, which recovery then refuses: the store is stranded (`p9` a). The in-transaction binder is now the natural place to enforce `_assert_visibility_matches_plan` and roll back.

(c) A bare `SQLiteRestartSafeRuntime` publishing on a config-bound store strands it. This is the same posture as the base (`p9` e).

### F9. NOTE: wording and evidence drift

- **agmi evidence.** `reports/gauntlet/agmi-agent-memory-v1/{README.md,qualification.json,accepted-result.json}` define the T1–T9 boundary in terms of the "configuration-binding sidecar", which new stores no longer have. The external agmi adapter is not installed here, so I could not check whether it touches that file. Re-run it at integration.
- **Doc 47, "sealed by a record digest".** This is an unkeyed checksum: it detects corruption, not forgery.
- **Doc 47, "Only the owning runtime … can write it".** A second `SQLiteTemporalGraph` instance can call `require_runtime_generations()` itself and write a row (`p4`). That is the #816 privileged storage layer, and the docs should say so.
- **Minor resource leak.** `SQLiteRestartSafeRuntime.create` does not close its substrate if generation 1, now including the binder, raises.

## What I attacked that HELD

| Attack | Result | Probe |
|---|---|---|
| Real `os._exit` kill at 10 boundaries per generation, in 7 phases: create, remember, recall, visibility snapshot, forget, base driven directly, first migrating generation of a legacy store | **0 split states; every reopen recovers exactly the committed generation.** The only refusal is create-before-first-commit (§8). The base shows 24 violations, which reproduces the window. | `p1_crash_matrix.py` |
| In-process `OSError` and `KeyboardInterrupt` at 6 points, on 5 paths including bare `checkpoint()` and `base.checkpoint()` after an in-memory F2 seam change | Before COMMIT: durable rows byte-identical, governance restored, observed generation unchanged, handle keeps working, seam change not lost. After COMMIT: committed and bound. | `p2_inprocess_injection.py` |
| Tampered rows, odd storage types (TEXT/REAL generation, BLOB payload, NULL payload, extra rows), a view in place of the table, a dropped table, a corrupt row injected next to a verifying legacy file | Refused where meaningful, with no fallback. Recovery never changed a byte. The remaining "accepted" cases are value-identical or need a full forgery. Downgrade cases are under F3. | `p3_tamper_types_downgrade.py` |
| Stale handle in the same process, 4 threads × 8 writes, another thread writing during an open generation, a second substrate instance without the capability, 3 writer processes with random kills | CAS refuses stale handles and nothing is written. Other-thread and no-capability writes raise `UngovernedDurableWrite`. The row matches the state after every round. | `p4_concurrency_ownership.py` |
| A10 across worktrees; legacy fixtures 821/coherent, 821/stranded, and the three 809 stores | Open writes nothing. The first generation writes the row and leaves the legacy file byte-unchanged. The stranded store stays refused and byte-identical on repeated opens. The base refuses migrated and created stores. A base-written store reads fine on the candidate. | `p5_cross_version_legacy.py` |
| A7: a broad act sequence (remember, recall, correct, dispute, forget, snapshot, seam, checkpoint) on base vs candidate | Every table is byte-identical except `runtime_configuration_binding`. Substrate, governance and journal digests are equal. Journal schema 1.0.0. | `p7_digest_identity.py` (`diff out-p7-base.txt out-p7-cand.txt`) |
| doctor, `posture()` (schema-valid with the new key), `backup_to`, file-checkpoint profile | doctor and posture write nothing. A `backup_to` copy plus its config now opens on its own (the base refused it: an improvement). The file profile is unchanged (same keys and refusal). | `p8_doctor_backup_fileprofile.py` |
| Interrupt during a legacy store's first migrating generation; two legacy handles; concurrent create race | Rolls back with no table left. The second handle gets a CAS conflict. The race ends coherent (same as base). | `p9_misc_paths.py` |
| `configured_restart` refactor, line by line | `verify_binding_record`, `binding_record` and `checkpoint_evidence` are identical to the old `recover` body, file record and evidence. Every message, order and check is preserved. | diff review |
| Retargeted #816 F3 test | Still discriminating: removing the `_observed_generation == generation` guard in a mutant copy makes it fail. | `mut/` |
| close() / recovery publish nothing; refused governed acts outside a generation | Hold: M19, p8, and the unchanged #816 suite. | tests + p8 |
| The author's crash-window probe on the candidate | No split state. Create before first commit is refused by design. | `out-authors-crash-window-cand.txt` |

## Verdict

**Not ready to freeze: one BLOCKING finding (F1).**

The core change is sound. The binding now commits and rolls back inside the generation's own SQLite transaction. I could not produce a split state or a false acceptance under real kills, in-process interrupts, concurrency, tampering, or legacy and cross-version combinations. Digests and journal material are unchanged. The #816 guarantees and every existing check are preserved.

What is wrong is a side effect: removing the file also removed the only witness outside the database.
- F1: a lost database is silently reinitialized as empty memory, which is a regression of a documented fail-closed property.
- F2: rolling back only the database file is now undetected.

Fix F1 (one marker file can also close F2), then address F3 and F4 before freezing. F5–F9 are documentation and hardening notes.

## Full suite (candidate 69ccd3a, my worktree)

The command was `python3 -m unittest discover -s reference/tests -t reference`. It ran 3059 tests: `FAILED (failures=4, skipped=24, expected failures=1)`.

The 4 failures are the same tests that fail in the author's recorded base run (`runs/full-suite-base-d2fc9782.txt`):
- test_644 own-checkout identity
- two test_770 replay-freshness tests
- test_benchmark_integration_contract runtime-baseline equivalence

So the change adds no new failures. The Runtime Baseline declaration noted in preregistration §7 is still owed at integration. Output: `probes/out-fullsuite-cand.txt`.
