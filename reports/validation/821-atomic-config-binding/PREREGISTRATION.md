# #821 preregistration: atomic configuration binding for the SQLite runtime

**Status:** preregistered before any runtime change. Committed on top of the frozen lineage with
the crash-window record it is based on; implementation commits follow it.

## 1. Lineage (confirmed against `origin` on 2026-10-15)

| Ref | SHA | Relation |
|---|---|---|
| `main` | `38f6a7dc` | ancestor of all below |
| #805 `claude/eager-dirac-bftkfg-stack-main` | `28f257c9` | ancestor of #815 |
| #815 `claude/eager-dirac-bftkfg-809` | `77c472e6` | ancestor of #816 |
| #816 frozen runtime | `e13d8c58` | ancestor of the #816 branch head |
| #816 `claude/eager-dirac-bftkfg-816-recovery` | `d2fc9782` | `e13d8c58` + two evidence-only commits (`reports/` only) |

The #821 branch starts at `d2fc9782` (strict fast-forward of #816; runtime tree identical to
`e13d8c58`). None of the predecessor branches is modified.

## 2. The crash window, reproduced

`probes/crash_window.py` kills a real child process (`os._exit`, so no `finally`, `close()` or
atexit runs) at each boundary, then inspects the files through an independent connection and
reopens through the public facade. Record: `fail-first/crash-window-d2fc9782.json`.

| Phase | Interruption point | Durable after the crash (state gen / journal gen / binding file gen) | Reopen at `d2fc9782` |
|---|---|---|---|
| steady | inside the open transaction, after the journal row (`pre_commit`) | 2 / 2 / 2 | recovers generation 2; second fact absent |
| steady | immediately after `COMMIT` returns (`post_commit`) | **3 / 3 / 2** | **fails closed:** `configuration binding does not match recovered base checkpoint: generation` |
| steady | binding temp file written and fsynced, rename not done (`mid_bind_file`) | **3 / 3 / 2**, leftover `.configuration-binding.json.tmp` | **fails closed**, same message |
| steady | after the operation returned (`post_bind`) | 3 / 3 / 3 | recovers generation 3 |
| create | inside generation 1's transaction (`pre_commit`) | no runtime state | fails closed: `required SQLite runtime state is missing` (by design, see §8) |
| create | after generation 1's `COMMIT` (`post_commit`) | **1 / 1 / absent** | **fails closed:** `required configuration-bound state missing: configuration-binding.json` |
| create | binding temp file written, rename not done (`mid_bind_file`) | **1 / 1 / absent** | **fails closed**, same message |

**First offending boundary.** `SQLiteRestartSafeRuntime.checkpoint` / `_transactional_operation`
exit `self._generation()` (the SQLite `COMMIT`) and only then call `self._published(evidence)`,
whose owner hook `SQLiteConfigBoundRestartRuntime._bind_current_base` runs
`ConfigBindingStore.checkpoint` → `_atomic_json_write`. In create, `SQLiteRestartSafeRuntime.create`
commits generation 1 before `SQLiteConfigBoundRestartRuntime.create` writes the file at all.
Everything between that `COMMIT` and the `os.replace` is the window.

**Why it is durable that way.** The store runs WAL with `synchronous=FULL`: once `COMMIT`
returns the commit frame is fsynced and the generation survives process death and power loss.
An uncommitted transaction has no commit frame and is discarded at the next open. The binding
file is a separate object: `_atomic_json_write` fsyncs the temporary file but never the
directory after `os.replace`, so even the `post_bind` state is not power-loss durable for the
file (the rename can be lost while the SQLite commit is not). Process death and power loss both
split the two; only process death is executed here.

## 3. Protocol: `sqlite_same_transaction_config_binding_v1`

The configuration binding of a SQLite config-bound store becomes a singleton row,
`runtime_configuration_binding(singleton = 1, generation, payload_json)`, written by the owning
runtime **inside the generation's own SQLite transaction**, after the runtime-state row and the
journal row and before `COMMIT`. A generation and its binding therefore commit, or roll back,
as one SQLite transaction. There is no second durable object and no post-commit step that
publishes state.

Row payload (canonical JSON):

```
schema_version            "1.0.0"
binding_protocol          "sqlite_same_transaction_config_binding_v1"
durability_profile        "reference_config_bound_checkpoint_v1"   (unchanged)
configuration_digest, plan_digest, plan, required_projection_ids  (as in the file record)
tenant                    the governance tenant of the generation
base: generation, substrate_digest, governance_digest, interpretation_digest,
      journal_record_digest   (the journal tail the generation appends)
record_digest             sha256 over all fields above
```

The table is created lazily, inside the first generation that writes it, so opening or
diagnosing a pre-#821 store changes nothing in it.

## 4. Preregistered contract (invariants)

- **A1 Atomicity.** For every generation a config-bound SQLite runtime publishes after this
  change, the binding row for exactly that generation commits in the same transaction. No
  interruption point yields a state generation that differs from the row generation.
- **A2 Verification.** Recovery checks, before the runtime is returned: the row parses; schema
  and protocol; `record_digest`; the row's `generation` column equals the payload's; the tenant
  equals the recovered governance tenant; generation, substrate, governance and interpretation
  digests and the journal tail digest equal the recovered, already-verified base; then the
  configuration checks the file store applies today (configuration digest, plan digest,
  persisted plan digest, required projections). Each failure raises `RuntimeRecoveryError`
  with a distinct diagnostic.
- **A3 No trust of whatever is present.** Recovery writes nothing and never repairs. A row that
  is present but fails verification is refused; recovery does not fall back to the legacy file,
  and never chooses "the newest" of two bindings.
- **A4 Legacy compatibility.** When no row exists, the legacy `configuration-binding.json` is
  verified with exactly the pre-#821 checks and messages. A missing, lagging, corrupt, foreign
  or tampered legacy file fails closed as before: a store already stranded by the old window
  stays refused (no automatic migration of ambiguous state). Only a legacy store whose file
  verifies against the current generation recovers, and the first generation a #821 runtime
  then publishes writes the row inside that generation. The legacy file is left in place,
  never rewritten, and never consulted again once a row exists.
- **A5 Ownership and stale writers.** The row is writable only on the thread running the owning
  runtime's open generation (the #816 capability); a bare `transaction()`, another thread or a
  substrate holder is refused. The existing generation CAS runs first, and the binder
  additionally requires continuity: the row it replaces binds generation G-1 under the same plan
  digest, or there is none and G = 1 or this handle verified a legacy file. A stale handle or a
  second process can never rebind a newer generation.
- **A6 `close()` publishes nothing; recovery publishes nothing.**
- **A7 Digests unchanged.** The substrate digest, the governance digest, the journal record
  schema (1.0.0) and chain material are byte-identical for the same operations; the binding row
  is outside all of them.
- **A8 Configuration authorization unchanged.** A different configuration or plan still refuses
  with the existing "explicit migration is required" messages; no new migration path is added.
- **A9 Binding failure rolls the generation back.** An exception or interrupt while publishing
  the binding rolls back canonical, governance, journal and binding rows together and restores
  in-memory governance as any rollback does (this removes the #816 F3 class at its root).
- **A10 Downgrade fails closed.** Pre-#821 code opening a store whose current generation is
  bound only by a row refuses it (its file is absent or lags).

## 5. Fail-first / replay matrix (each row is a test in `reference/tests/test_821_atomic_config_binding.py`)

| # | Case | Expected at `d2fc9782` | Expected at candidate |
|---|---|---|---|
| M1 | crash (process death) before `COMMIT` | prior generation recovers | same |
| M2 | crash immediately after `COMMIT`, steady state | fails closed (window) | **recovers the committed generation exactly** |
| M3 | crash during binding publication | fails closed (window) | rolls back with the generation; prior generation recovers |
| M4 | crash after the operation returned | recovers | recovers |
| M5 | crash after generation 1's `COMMIT` in create | fails closed (window) | recovers generation 1 |
| M6 | injected exception / `KeyboardInterrupt` in binding publication | generation committed, binding not | nothing committed; next operation and reopen work; in-memory governance restored |
| M7 | binding row tampered (plan, configuration digest, base digest, generation column, record digest, invalid JSON) | n/a (no row) | refused, distinct diagnostic, not repaired, refused again on second open |
| M8 | row from another store / another tenant transplanted | n/a | refused (tenant / base mismatch) |
| M9 | stale row replayed (older generation's row copied back) | n/a | refused (stale) |
| M10 | row deleted on a #821-created store | n/a | refused (`required configuration-bound state missing`) |
| M11 | row deleted on a migrated store with its legacy file present | n/a | refused (legacy file lags) |
| M12 | stale handle after another process published | CAS conflict | CAS conflict; row still binds the other process's generation |
| M13 | substrate holder writes the row outside a generation | n/a | `UngovernedDurableWrite`, nothing written |
| M14 | legacy store (file, no row) | recovers | recovers; next generation writes the row; legacy file byte-unchanged |
| M15 | legacy store stranded by the old window (file lags) | fails closed | fails closed, same message |
| M16 | legacy file tampered / foreign | fails closed | fails closed, same message |
| M17 | changed configuration after restart | refused, "explicit migration is required" | same |
| M18 | restart/interrupt loop (kill at random points across N cycles) | some cycles strand the store | every cycle reopens to the last committed generation |
| M19 | `close()` and recovery write nothing | holds | holds (byte comparison of every table and the directory) |
| M20 | doctor on a #821 store | n/a | recovered; reports the binding scheme |
| M21 | pre-#821 code opens a #821-bound store | n/a | fails closed (A10), executed against the `d2fc9782` worktree |

## 6. Gates (all at the exact frozen candidate SHA, clean tree, local, no Actions)

1. `test_821_atomic_config_binding` passes; its fail-first run on `d2fc9782` is recorded.
2. `probes/crash_window.py` on the candidate: no split state and every reopen recovers the last
   committed generation (create `pre_commit` excepted, §8).
3. `test_816_runtime_owned_writes`, `test_context_package`, the #802 suite, transactional-generation
   and SQLite production tests pass.
4. Full suite: no failure beyond those on `d2fc9782` under the same environment.
5. #786 v2, v3 and #809 security replays executed fresh: PASS, manifests bind the SHA.
6. Independent adversarial review: no unresolved blocking finding.

## 7. Scope, interactions and non-goals

- **F2 (in-memory administrative seams).** Unchanged and not widened: #821 changes how the
  configuration identity of a generation is published, not what a generation publishes. A
  seam's in-memory change is still published by the next generation, now with its binding in
  the same transaction. The binding grants no authority.
- **File-checkpoint profile** (`RestartSafeRuntime` + `ConfigBoundRestartRuntime`) is out of
  scope and unchanged; it has an analogous manifest-then-binding sequence, recorded as a
  residual.
- **Baseline registers.** Protected runtime files change, so the Runtime Baseline equivalence
  guard reports an undeclared change. No declaration or register is regenerated here; that
  needs owner authorization at integration.
- No contract version change, no default change, no merge, no Actions.

## 8. Known pre-existing posture kept deliberately

A crash before generation 1 commits leaves a database file with no runtime state. The facade
refuses it rather than reinitializing ("a partial state marker fails closed so a damaged or
incomplete runtime cannot be silently reinitialized as empty memory"). #821 keeps that posture:
no generation was ever published, so there is nothing to recover and nothing to trust.
