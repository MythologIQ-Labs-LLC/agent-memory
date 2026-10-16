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

---

## Re-verification at 96a3f59

**Scope.** Candidate `96a3f59703e0ffdf96d1e92a5659601f4c119a27`, which is `4652356` (review and AMENDMENT-1) followed by the repairs. I reviewed it in a fresh detached worktree `review-821/cand2` and modified nothing in `/home/user/agent-memory`. I read AMENDMENT-1 and `git diff 69ccd3a 96a3f59 -- reference/agentmem_ref docs`.

**Tests.**
- `test_821` and `test_816` pass: 62 tests, which now include M22–M30.
- Full suite: 3070 tests, `FAILED (failures=4, skipped=24, expected failures=1)`. These are the same 4 pre-existing failures as at `d2fc9782` and `69ccd3a` (`probes/out-fullsuite-cand2.txt`).

**Probes.** p1–p9 were re-run on cand2 (`probes/out-p*-cand2.txt`; for p5, both directions against the base). New probes:
- p10: kill matrix around the witness.
- p11: witness attacks.
- p12: opening a store while another process writes to it.
- p13: a deterministic version of the p12 race.

I also re-ran the author's `crash_window.py` and `downgrade.py` (`out-authors-*-cand2.txt`).

### Per-finding status

| Finding | Status | Evidence |
|---|---|---|
| F1 lost database re-created as empty memory | **FIXED** | `open`, doctor and `create` all refuse: "generation witness exists without SQLite runtime database". Nothing is created (p6, p11 W4). Residual: if the witness is deleted as well, the store is reinitialized (documented). |
| F2 rollback of the database file only | **FIXED** | Each of these is refused: an older copy of the own database (W1), a `backup_to` copy restored over the live directory (W1), a fork that shares the history prefix at the same or a higher generation (W2), and another store's database at a higher generation (W2) or a lower one (W1) (p6, p11). Residuals: a deleted witness, a witness still at generation 0, and a byte-identical fork are all accepted (expected and documented). |
| F3 legacy-file fallback while the table exists | **FIXED** | An empty table, or a deleted row with the table kept, is refused as corrupt even when a forged legacy file verifies (p3). Residual: drop the whole table and forge the file is still accepted (documented; see N4). |
| F4 M21/A10 evidence | **PARTIAL** | `probes/downgrade.py` exists. I ran it at cand2 against `d2fc9782`: both migrated and new stores are `failed_closed`, and the unmigrated store recovers. p5 agrees. The run record is not committed yet; it is promised at freeze. |
| F5 binder trusted unverified fields of the previous row | **FIXED** | A row rewritten out of band under an open handle makes the next generation fail with `RuntimeCheckpointConflict` and roll back. A later reopen still refuses the corrupted row, so nothing is repaired (p3). |
| F6 doctor misreported on failure | **FIXED** | `configuration_binding_present: true`, `configuration_binding_scheme: "unverified"` (p8). |
| F7 one-way migration | **FIXED** (documented in doc 47) | p5 is unchanged: the base refuses a migrated store. |
| F8a recovery reads not in one snapshot | **OPEN** (pre-existing, out of scope) | Under concurrent writers it is still the dominant source of spurious refusals, on the base as well (p4, p12). See N1. |
| F8b out-of-plan snapshot through the base runtime | **FIXED** | It is refused and rolled back, and the store stays openable (p9a). |
| F8c bare base runtime | unchanged (pre-existing) | Fails closed with "stale or replayed" (p9e). |
| F9 wording, `create` leak | **FIXED**, except the agmi item (**OPEN**, NOTE) | Doc wording is corrected and `create` closes its substrate. `reports/gauntlet/agmi-agent-memory-v1/*` still describes the boundary in terms of the "configuration-binding sidecar", and the external adapter was not re-run (it is not installed here). |

### What held on 96a3f59

- **(1) Crash interleavings.** p10 killed a real child process before, inside and after `GenerationWitness.record` (temp file written; renamed but directory not yet fsynced; after), and between COMMIT and the witness write. It covered create (the gen-0 and gen-1 witnesses), remember, recall, visibility snapshot, and a legacy store's first migrating generation.
  - The witness never leads a committed database.
  - Every store that committed a generation reopens to exactly that generation.
  - A leftover `.generation-witness.json.tmp` is harmless.
  - p1 (70 kill points) shows 0 violations, and p2 (60 in-process injections) shows 0 problems.
- **(2) Defeating W1–W4.** Every attempt above was refused except the documented residuals.
  - W3 refuses malformed witnesses: `true`, `2.0`, `-1`, `"2"`, and non-JSON.
  - A forged witness can only refuse. A matching witness does not rescue a corrupt row (p11).
- **(3) The witness never causes acceptance, and nothing writes it outside a generation.** Recovery, `posture()`, `close()` and doctor leave it byte- and mtime-identical. Opening and closing a legacy store creates no witness (p11).
  - If the witness write fails with `OSError` after COMMIT, the call still reports success. `generation_witness_current` becomes False, and the next generation rewrites the witness.
- **(4) p3–p9.** Every earlier "held" result still holds. The previous "unexpected" lines in p3 are now the intended F3/F5 refusals.
- **(5) No new regression against the base:**
  - Legacy 821 coherent and 809 stores: opening writes nothing; the first generation writes the row and the witness; the legacy file is byte-unchanged.
  - The stranded store stays refused and byte-identical.
  - A base-written store opens normally on cand2.
  - A7: every table is byte-identical to the base except the binding table (p7 diff).
  - The author's crash window shows no split state.

### New findings

**N1. NOTE (borderline SHOULD-FIX): the witness is checked after base recovery, so a concurrent commit looks like a rollback.**
- **The race.** `SQLiteConfigBoundRestartRuntime.recover` checks the witness only after `SQLiteRestartSafeRuntime.recover` has read the database. Suppose another process commits and writes its witness in between. The opener then refuses with "SQLite database is behind this store's generation witness (2 < 3): it was rolled back or replaced; explicit operator action is required". Nothing was rolled back, and a reopen succeeds.
- **Why only a note.** The race itself predates the witness: at `69ccd3a` the same interleaving gave "stale or replayed", and at the base it gave "does not match … generation" (p13, all three revisions). Under a tight write loop, F8a's governance-digest mismatch dominates anyway (p12).
- **What the witness changes.** It turns a transient race into a diagnostic that tells an operator to intervene. The obvious intervention, deleting the witness, switches the protection off.
- **Fix.** Read the witness *before* base recovery. It is written only after the COMMIT it names, so a value read at T0 is never ahead of a database read at T1 ≥ T0, and W1/W2 become race-free (the journal is append-only).

**N2. NOTE: a crash or failure during the very first `open` can permanently refuse a directory that never held memory.**
- **The window.** At create, the gen-0 witness is written before the SQLite file exists. A kill in that window (p10, create `w_renamed` / `w_after` call 1), or any failure there, leaves the witness with no database. Every later `open`, `create` and doctor then refuses with "incomplete durable state", until an operator deletes the witness.
- **Why it matters.** No data is at risk, but at `69ccd3a` and at the base, a retry simply created the store. The diagnostic also wrongly implies a lost database.
- **Fix.** Write the gen-0 witness after `SQLiteTemporalGraph` has created the file and before generation 1 commits. A crash there leaves a database file with no state, which is the existing §8 refusal. Alternatively, give a witness at generation 0 with no database its own diagnostic, plus a documented removal step.

**N3. NOTE: a witness that exists but cannot be read escapes as a raw `OSError`.** `GenerationWitness.verify` catches only `FileNotFoundError`.
- If the witness path is a directory, or unreadable, `open` raises `IsADirectoryError` or `PermissionError` rather than `RuntimeRecoveryError`. It still refuses.
- `doctor.diagnose`, and therefore `posture()`, crash with that exception instead of reporting `failed_closed` (p11).
- Related: a `KeyboardInterrupt` during the witness write leaves `generation_witness_current` at True, even though the witness lags (p11).
- **Fix.** Map every `OSError` to W3, and set the flag to False before writing.

**N4. NOTE (hardening): the witness could close F3's remaining downgrade.** A #821 runtime writes a witness at generation ≥ 1 only after a generation that wrote the binding row. So a store whose witness generation is ≥ 1 but which has no binding table is inconsistent. Refusing it, instead of falling back to the legacy file, closes "drop table + forge file" unless the attacker also deletes the witness.

**N5. NOTE: legitimate disaster recovery now needs a documented step.** Restoring an intentional `backup_to` copy into the live directory is refused (W1, correctly). The message says only "explicit operator action is required", and neither doc 47 nor `backup_to` names the action, which is to remove or replace `generation-witness.json` deliberately.

### Updated verdict

**No blocking findings remain.**

F1, F2, F3, F5, F6, F7, F8b and F9 are fixed, apart from the agmi wording. F4 becomes complete once the downgrade run record is committed. The witness never leads a committed database under any interruption I could produce, never causes acceptance, and is never written by recovery, `close()` or doctor. Nothing regresses against the base on the legacy fixtures or the 809 stores.

Before freeze I recommend:
- **N1:** read the witness before base recovery. It is a one-line move, and it removes a misleading "operator action required" refusal under concurrent use.
- **N2:** reorder the gen-0 witness write.
- **N3:** map `OSError` to W3, so doctor never crashes.
- **N4:** optional hardening.
- **N5 and the agmi wording:** documentation.

None of these blocks freezing.

---

## Final check at d0d2a97

**Scope.** Commit `d0d2a97`, which follows `96a3f59` and changes only `sqlite_runtime.py` and doc 47. I checked it in a fresh detached worktree, `review-821/cand3`, and modified nothing in `/home/user/agent-memory`.

**Tests.**
- `test_821`, `test_816` and `test_governance_attestation` pass (91 tests).
- Full suite: 3075 tests, `FAILED (failures=4, skipped=24, expected failures=1)`. The 4 failures are the same pre-existing ones as at the base (`probes/out-fullsuite-cand3.txt`).

**Probes.** p13, p10, p11 and p6 were re-run, plus p1, p2, p3, p5, p7 and p9 as a regression sweep. p14 is new: it covers a witness write failure inside generation 1, and N4 on migrated legacy stores. Outputs are in `probes/out-*-cand3.txt`.

| Item | Status | Evidence |
|---|---|---|
| N1: witness read before base recovery | **FIXED** | The p13 race no longer produces the witness's rollback message. It now produces the pre-existing row diagnostic ("stale or replayed"), which belongs to the F8a race class, and a reopen succeeds. |
| N2: gen-0 witness written inside generation 1 | **FIXED** | p10 kills inside generation 1, both after and before the gen-0 witness write and before COMMIT. Both leave a database with no runtime state and give the same §8 refusal, with or without the witness. A directory with no database file is no longer bricked. p14: an `OSError` or `KeyboardInterrupt` in that write rolls generation 1 back into the same §8 state. That matches the base, where a binding-file failure at create also refuses the store permanently. |
| N3: witness read errors | **FIXED** | A witness path that is a directory now gives W3 `RuntimeRecoveryError`, and doctor reports `failed_closed`. After an interrupted witness write, `generation_witness_current` is False (p11). |
| N4: witness ≥ 1 with no binding table refused | **FIXED, no stranding** | On a legacy store's first migrating generation, a witness write that fails or is interrupted after COMMIT leaves no witness (legacy stores have none), so the store reopens at generation 4; the next generation writes the witness and the store reopens at 5 (p14). Killing between COMMIT and the witness write also reopens (p10 migrate). A cleanly migrated store reopens. "Drop table + forge legacy file" is now refused while the witness exists (p3, p14). The remaining residual is deleting the witness as well (documented). |
| N5: operator hint | **FIXED** | W1/W2 refusals now end "…remove generation-witness.json to accept it" (p6, p11), and doc 47 is updated. |
| Regressions | **none** | p1 shows 0 violations and p2 shows 0 problems. In p3, every change from cand2 is a stricter refusal coming from N4. p7 is byte-identical to the base except the binding table. p5: A10 holds and the 809 and 821 legacy stores behave as before. p9a still rolls back. |

**New findings:** none.

**Still open, all non-blocking:**
- F4 needs its downgrade run record committed at freeze. I re-ran `downgrade.py` at d0d2a97 against `d2fc9782`: migrated and new stores fail closed, the unmigrated store recovers (`probes/out-authors-downgrade-cand3.txt`).
- F8a: recovery reads are not taken in one read snapshot. This is pre-existing and also present at the base.
- The agmi gauntlet wording still describes the old sidecar.

**Final verdict: PASS.** No blocking or should-fix findings remain. Freeze is acceptable once the F4 run record is committed at the frozen SHA.
