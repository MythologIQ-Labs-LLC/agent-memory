# Adversarial review: #816 runtime-owned writes (base 77c472e6, candidate 51452b88)

## Verdict

**No BLOCKING findings.** The repair does what issue #816 asks. A direct `adapter.governed_recall` on a facade-owned handle is refused before anything moves, and the store reopens afterwards. Supported paths still work. The integrity checks are not relaxed. The full suite has the same 4 failures at base and at candidate, and all 4 come from the environment.

Two SHOULD-FIX findings make claims in the change false as written:

- **F1:** one refusal path moves the clock before it refuses.
- **F3:** this change introduces a new in-memory/durable divergence when the binding hook fails.

F2 and F4 are pre-existing gaps. The new docs claim more than the code delivers there, so either the claims should be narrowed or the guard extended. The rest are NOTEs.

Worktrees used (left in place):

- Candidate: `/tmp/claude-0/-home-user-agent-memory/d36426e4-2c3f-5d02-b5a0-991ea8f96c90/scratchpad/review-816/cand`
- Base: `/tmp/claude-0/-home-user-agent-memory/d36426e4-2c3f-5d02-b5a0-991ea8f96c90/scratchpad/review-816/base`

Probes are in `/tmp/claude-0/-home-user-agent-memory/d36426e4-2c3f-5d02-b5a0-991ea8f96c90/scratchpad/review-816/probes/`. Run each one as `python3 -W ignore <probe> <worktree>/reference`. Captured output is in `probes/out-cand.txt` and `probes/out-base.txt`.

---

## F1 (SHOULD-FIX): a refused preselected admission or planner recall ticks the deterministic clock, and a later generation binds that tick

`admit_preselected_candidates` (`runtime/contextual_recall_adapter.py:82`) calls `base._clock.now()` before `base._ids.next()` (line 90). The guard only fires in `_ids.next()`, so the clock has already advanced when `UngovernedDurableWrite` is raised. This contradicts the docs/47 claim that the act is refused "before the identifier sequence, the deterministic clock or any governance state moves". It also contradicts the docstring on `UngovernedDurableWrite`. Every planner path reaches this function: `recall_planner.recall`, `ConfiguredCompositionRuntime.multi_route_recall`, `recall_control`, and `query_driven_recall`.

`close()` discards the tick, so reopen is fine. If the handle keeps going, the next facade generation publishes the extra tick. Every later timestamp and event then differs from a store that never saw the refused call.

Repro: `probes/p1_refusal_side_effects.py`. Candidate output:

```
admit_preselected_candidates  | raised UngovernedDurableWrite | adapter-export changed: ['clock_tick'] clock 7->8 | rows changed: [] | durably bound after next facade op: ['clock_tick', 'events']
recall_planner.recall         | raised UngovernedDurableWrite | adapter-export changed: ['clock_tick'] clock 7->8 | ...                | ['clock_tick', 'events']
```

At base the same calls succeed, advance `id_counter`, and break reopen (the original #816 failure). The candidate improves on this, but its refusal is not side-effect free.

Fix:
- Call `base._ids.ensure_allocatable()` as the first statement of `admit_preselected_candidates`, or allocate `correlation` before `evaluated_at`.
- Better, close the whole class of bug: route the adapter's clock through the guard, as `now()` already does, so that no `_clock.now()` can run outside a generation.
- Add `admit_preselected_candidates` and `recall_planner.recall` to `RefusalIsExplicitAndChangesNothing.acts`.

## F2 (SHOULD-FIX, for the docs claim; the behaviour is pre-existing): ungoverned in-memory governance mutations are not refused, and the next generation binds them silently

The guard is keyed to id allocation, so acts that change governance state without allocating an id pass straight through. The next supported generation then publishes their effect.

All of these are reachable from a facade handle:

- `handle.runtime.projections.correct(m)`, which calls `adapter.record_correction` (`state_version`)
- `adapter.set_shared_domain_members` and `shared_revocation.bootstrap_shared_domain_members` (shared-domain membership, which grants recall admission)
- `adapter.extension_state[...]`
- `adapter.events.append`

Repro: `probes/p1_refusal_side_effects.py`, candidate and base identical:

```
projections.correct (record_correction) | returned ... | adapter-export changed: ['state_version']         | durably bound after next facade op: ['state_version']
adapter.set_shared_domain_members       | returned None | adapter-export changed: ['shared_domain_members'] | durably bound after next facade op: ['shared_domain_members']
adapter.extension_state[...] = ...      | returned None | ['extension_state'] | ['extension_state']
```

`close()` without a later operation discards them; probe p6 shows no rows change and a clean reopen. This is not a regression, but docs/47 says "once a SQLite runtime owns the store, nothing may change it outside that runtime's transactional seam". The membership case is an authority change that becomes durable without going through `commit_shared_domain_membership_change`. Two ways to fix it:
- (a) Narrow the docs: only acts that allocate an id or read the clock are refused, and adapter state mutated outside a generation is published by the next one.
- (b) Make the claim true: on entry to `_transactional_operation` and `checkpoint`, refuse (or discard by restoring the last published state) when the adapter carries unpublished governance changes. The `TrackedMap`/`TrackedLog` dirty sets plus a clock/residual comparison already supply what is needed.

## F3 (SHOULD-FIX, regression, fault-path only): a failed binding write rolls back a committed visibility snapshot in memory, and the next generation drops it

Moving the bind into `_published` puts the hook inside the base's `persist_visibility_snapshot` `try/except`, which restores `self.visibility_snapshots = previous`:

```python
self.visibility_snapshots[operation_id] = snapshot
try:
    return self.checkpoint()        # COMMIT, then _published -> owner hook (binding write)
except Exception:
    self.visibility_snapshots = previous   # also runs when only the hook failed, after COMMIT
    raise
```

If the binding write fails after SQLite committed (for example ENOSPC), the in-memory snapshot is rolled back even though generation N holds it. The next successful generation then publishes visibility without it, and the committed obligation is lost on reopen. At base the bind ran outside this block, so the in-memory state stayed equal to the committed one.

Repro: `probes/p3_hook_failure.py`, which patches `ConfigBindingStore.checkpoint` to raise `OSError`.

Candidate:
```
(a) after failure: SQLite committed gen 3 contains op:probe; in-memory has op:probe: False
(a) after next facade op: committed = (4, []) ...
(a) reopened: recovered visibility ops = []
```
Base:
```
(a) after failure: ... in-memory has op:probe: True
(a) after next facade op: committed = (4, ['governance_residual'])
(a) reopened: recovered visibility ops = ['op:probe']
```

Case (b) (facade `remember`, where the binding fails, then close, then reopen raises `configuration binding does not match recovered base checkpoint`) behaves the same at base and candidate. That confirms the commit-then-bind window is pre-existing for governed operations. The docs' "unchanged by it" is not quite true for `persist_visibility_snapshot`.

Fix: in `SQLiteRestartSafeRuntime.persist_visibility_snapshot`, restore only when the transaction fails:

```python
with lock:
    try:
        with self.substrate.transaction():
            evidence = self._persist_unlocked()
    except Exception:
        self.visibility_snapshots = previous
        raise
    self._published(evidence)
```

Add the failure-injection case to the tests.

## F4 (SHOULD-FIX, hardening; the exposure is pre-existing): the guard checks `connection.in_transaction`, not "inside this runtime's generation on this thread"

`ensure_allocatable` accepts any open transaction on the shared connection (`check_same_thread=False`). Three bypasses follow:

- **(a) Another thread.** Thread B, not holding the serialization lock, makes a direct adapter call while thread A is inside a generation. B is not refused, and its effects are bound into A's generation. If A rolls back, the identifiers handed to B are reissued to the next caller (identifier reuse).
  - Repro: `probes/p2_thread_in_transaction.py`. Candidate output:
    ```
    A commits: B ... NOT refused; decision ids ['ref-0009']; recall events in live adapter after A: 1
    A fails:   B ... NOT refused; decision ids ['ref-0009']; ... next supported recall decision ids ['ref-0009']
    ```
  - This breaks the documented contract (direct callers must hold the lock). But a direct caller that does hold the lock is always refused, so the guard is only effective against the callers least likely to misuse it.
- **(b) `substrate.transaction()`.** This is public on `SQLiteTemporalGraph`, and `adapter.checkpoint_substrate()` reaches it. It is a transaction, not a generation: a governed act inside it passes the guard and COMMITs, and the store then fails to reopen with the original #816 error.
  - Repro: `probes/p7_substrate_transaction_bypass.py`. Candidate and base both print `NOT refused, committed` and then `reopen FAILED ... SQLite canonical substrate digest mismatch`.
  - The new `require_runtime_generations` docstring says `transaction()` *is* "the seam the runtime publishes as one generation", which is false.
- **(c) BaseException.** `transaction()` only handles `Exception`, so a `KeyboardInterrupt` inside an operation leaves the connection `in_transaction`. After that the guard is open on that handle (pre-existing leak; nothing becomes durable, because `close()` rolls back).
  - Repro: `probes/p5_baseexception_txn_leak.py`. Both base and candidate print `NOT refused`.

Fix: have `_transactional_operation` and `checkpoint` set a runtime-owned token while they hold the lock, for example `ids._generation_owner = threading.get_ident()` set and cleared in `try/finally`. `ensure_allocatable` would then require `_generation_owner == get_ident()`, which closes (a), (b) and (c). Also use `except BaseException` (or `finally`) for ROLLBACK in `transaction()`, and correct the docstring.

## F5 (NOTE): the documented module-level API stages now raise an uncaught exception on a durable adapter

docs/44 documents `surface.commit/recall/forget/authorize/witness(memory, ...)` with refusals returned as result envelopes. On a facade-owned SQLite adapter they now raise `UngovernedDurableWrite`, a `RuntimeError` that `surface.authorize`/`witness` do not catch. At base the same calls returned results and corrupted the store, so this is strictly better. Still:

- The facade has no `authorize`/`witness` methods, so durable action authority is only reachable as `durable_runtime.run_governed_read(lambda: surface.authorize(adapter, env))`. That form works and reopens cleanly.
- docs/44 does not say this. Three existing tests (786, prefilter, recall_control) had to be rewritten to this form, which shows it is a caller-visible change.

Repro: `probes/p4_public_surface_stages.py`. Candidate: direct calls raise `EXCEPTION UngovernedDurableWrite` and reopen is OK; calls via `run_governed_read` return results and reopen is OK. Base: direct calls return results, then `reopen FAILED ... digest mismatch`.

Suggestion: state in docs/44 that a durable adapter requires the runtime seam. Optionally, give the facade `authorize`/`witness` methods.

## F6 (NOTE): a refused direct planner recall still writes derived sidecar vectors

The vector route runs before admission, and admission is where the guard fires. So with semantic retrieval on, a refused `recall_planner.recall` has already embedded and committed vectors for uncached facts into the derived store.

Repro: `probes/p9_semantic_sidecar_on_refusal.py`, using the #802 offline provider. Candidate: `refused UngovernedDurableWrite; sidecar vector rows before=0 after refusal=1`.

The data is derived and not authority. It only covers facts that currently exist (deleted facts are not enumerated), so there is no #802 resurrection. The "refusal changes nothing" claim is only true for the canonical DB. Moving the guard to the planner's entry point would also fix F1.

## F7 (NOTE): ownership is per `SQLiteTemporalGraph` instance, not per store

A second `SQLiteTemporalGraph` opened on the same file, with a plain `GovernedMemoryAdapter`, allocates ids in autocommit, and the store then fails to reopen.

Repro: `probes/p8_second_substrate_instance.py`: `mint_id(): ref-0008 (not refused)`, then `reopen FAILED ... digest mismatch`.

This is defensible as the "privileged storage layer", but the docs speak of the store. A store-level marker would make ownership a property of the store: if `runtime_state` exists, the guard is armed in `SQLiteTemporalGraph.__init__`.

Smaller notes:
- `on_generation_published` holds a single callback slot, so a second owner silently replaces the first.
- docs/47 says storage-level writes are published "only by an explicit checkpoint". In fact any later supported generation publishes `SQLiteTemporalGraph`-method writes too, because they enter the digest dirty set.

---

## What held

- **Issue reproduction.** On the candidate the direct `adapter.governed_recall` is refused and the store reopens (p1, focused tests). At base it breaks reopen.
- **Guarded acts are side-effect free.** `governed_recall`, `commit_proposal`, `governed_delete`, `governed_dispute`, `mint_id`, `now`, `record_event` and `upgrade_canonical_derivation` refuse before anything moves. The adapter export and the raw rows (read through an independent connection) are unchanged, and nothing is bound later (p1 row 1, focused tests).
- **Collaborator modules.** `action_authority` (`_ledger` mints before `now`), `shared_revocation` (mints before mutating), `witness_execution`, and `governed_dispute`'s pre-guard `ValueError` all refuse with no prior mutation.
- **`close()` publishes nothing,** even after refused and ungoverned acts: rows are unchanged and in-memory changes are discarded on reopen (p6).
- **Integrity checks hold.** Recovery still fails after tampering with fact text, `id_counter` (+1 and -1), the last journal row, the `runtime_state` generation, or a `governance_log` row deletion (labelled "governance_residual edit" in p6 output), with the expected digest or journal errors (p6).
- **Hook timing.** The hook never fires for a rolled-back generation: `_published` runs only after COMMIT, and outside the restore `try` in `_transactional_operation` and `checkpoint`. There is no double binding: create binds explicitly before the hook is registered, and `checkpoint` returns the hook's evidence. The bind runs under the serialization lock.
- **Commit-then-bind window for governed operations.** It is the same at base and candidate (p3 b), so it is correctly described as pre-existing, apart from the F3 visibility path.
- **Cross-process and stale handles.** Every handle arms its own guard. A stale handle's governed operations hit the generation CAS (focused test `CrossProcessStaleHandle`).
- **Disclosure.** The exception message is constant and carries no data, and refusal ordering is not data-dependent. No new authority path was found: the cross-scope (#786), deleted-lineage (#777), derivation (#809) and sidecar-erasure (#802) suites pass.
- **Focused tests.** `tests.test_816_runtime_owned_writes` passes 19/19 at the candidate.
- **Full suite.** Candidate: 3027 tests, 4 failures. Base: 3008 tests, the same 4 failures. All 4 are frozen-revision or worktree-identity checks: `test_644...frozen_revision`, two `test_770` replay-staleness tests, and `test_benchmark_integration_contract`.

## Scope judgement

It is acceptable to leave storage-level substrate writes ungoverned. Fixtures and migration use them, and recovery still refuses anything unpublished. The docs should say "published by the next generation or checkpoint", not "only by an explicit checkpoint".

The real scope gap is that the guard is a proxy, "an id is being allocated inside some SQLite transaction", standing in for "inside this runtime's generation":

- F1 and F6 come from guarding at allocation rather than at the entry point.
- F4 comes from checking `in_transaction` rather than a runtime-owned token.
- F2 comes from guarding only ids.

The F4 owner token, plus an unpublished-changes check on generation entry (F2 b), would make the docs/47 claims true without changing any supported path.
