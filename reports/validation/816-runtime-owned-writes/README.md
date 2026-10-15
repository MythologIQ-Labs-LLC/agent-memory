# #816: durable writes on a runtime-owned SQLite store happen only inside a runtime generation

| Item | Value |
|---|---|
| Issue | #816. An adapter-level `governed_recall` on a facade-owned SQLite handle, followed by `close()`, fails the next `open` with "SQLite canonical substrate digest mismatch". |
| Base (unmodified security candidate) | #815 head `77c472e6f91fd292ac90eedd105c272f5cb21aea`, on #805 `28f257c9`; contract 1.8.0 |
| Branch | `claude/eager-dirac-bftkfg-816-recovery` |
| Frozen repair | **`e13d8c58`** (`e13d8c58...`; full SHA in the #816 handoff), a strict descendant of `77c472e6` |
| Status | Implemented, tested, independently reviewed. **Not integrated, not released.** No PR, no hosted Actions, no contract bump, no Runtime Baseline successor. |

## 1. Reproduction on the unmodified base

- **Probe:** `probes/probe_paths.py`, run on both heads (`probes/probe-paths-base-77c472e6.log`, `probes/probe-paths-e13d8c58.log`).
- **Store:** a disposable SQLite store opened through the facade. Each case writes one memory, makes the call, closes the handle and reopens.

| Case | Base `77c472e6` | Repair |
|---|---|---|
| Positive control: no call | Reopen OK | Reopen OK |
| Positive control: facade `recall` | Reopen OK | Reopen OK |
| `m.runtime.adapter.governed_recall(...)` (the issue) | **Reopen FAILED: canonical substrate digest mismatch** | Call refused (`UngovernedDurableWrite`); reopen OK |
| `adapter.mint_id()` | **Reopen FAILED: digest mismatch** | Refused; reopen OK |
| `adapter.now()` | Reopen OK, but the clock tick is published later | Refused; reopen OK |
| Base SQLite runtime driven directly (`durable_runtime.base.governed_recall`) | **Reopen FAILED: configuration binding does not match recovered base checkpoint** | Call publishes, binding follows; reopen OK |
| Stale handle, another process committed, then a direct adapter call | **Reopen FAILED: digest mismatch.** The other process's committed generation no longer recovers. | Refused; reopen OK with both processes' facts |
| Stale handle, another process committed, then facade `recall` | `RuntimeCheckpointConflict`; reopen OK | Unchanged |

Negative controls held on both heads: facade-only sessions and integrity tampering are rejected.

## 2. Root cause (source references at `77c472e6`)

1. **The identifier sequence is durable and part of the canonical digest.**
   - `SqliteDeterministicIds.next()` (`state/sqlite_substrate.py:98`) executes `UPDATE agent_memory_meta SET value = value + 1 WHERE key = 'id_counter'` on the substrate connection.
   - Its value is part of the canonical substrate commitment (`_bucketed_root`, `:1074-1079`; `state_digest`, `:1054`).
2. **Every governed act allocates first.** `governed_recall` (`runtime/adapter.py:1391`), `commit_proposal`, `governed_dispute` and `governed_delete` all begin by calling `self._ids.next()`.
   - When the call does not run inside `SQLiteRestartSafeRuntime._transactional_operation` (`runtime/sqlite_runtime.py:539`), the connection is in autocommit and the counter advance is committed immediately.
   - The adapter's in-memory decisions and events are not published.
3. **Only a generation publishes the digest.**
   - The digest recovery verifies (`runtime/sqlite_runtime.py:343`) is written by `_persist_unlocked` (`:419`), and only at the end of a generation.
   - `AgentMemory.close()` (`api/surface.py:1373`) and `SQLiteRestartSafeRuntime.close()` (`:401`) publish nothing.
   - The recorded digest therefore no longer matches, and the next `recover()` fails closed.
4. **Why a facade recall "repairs" it.** The next facade operation is a generation. It re-publishes whatever the live state has become: the advanced counter plus the unpublished governance from the direct call. The defect is masked, not resolved, and the direct call's effects are attributed to a later generation.
5. **Same defect class one layer up.**
   - `SQLiteConfigBoundRestartRuntime` advanced its configuration binding only in its own wrapper methods.
   - Driving the base runtime directly committed a generation the binding never followed (`configured_restart.py:337`).

## 3. Options compared

| Option | Verdict |
|---|---|
| `close()` publishes outstanding governed state | **Rejected.** It would bind whatever drift the live state holds, including a refused or partly failed act, under the authority of a generation the act never had. |
| Prevent direct state-mutating adapter operations on facade-owned handles | **Adopted, at the lowest sound point.** The guard sits on the identifier sequence and the clock, which are the first durable effects of every governed act. It also covers module-level stages, the planner and preselected admission without enumerating them. |
| Move the durable publication boundary into a lower-level operation | **Partly adopted.** The base runtime notifies its owner after each published generation, so the configuration binding follows every generation. |
| Unsupported-operation refusal or recovery diagnostic | **Adopted** as the refusal itself: `UngovernedDurableWrite`, with a fixed message, raised before anything moves. Recovery's digest checks are unchanged. |

**Considered and withdrawn during implementation: making the owned connection `query_only` outside a generation.**
- It broke the privileged storage-level layer that fixtures, the #574 canonical-JSON migration tests and `reference/retrieval_regression.py` use, where rows are written directly and published with an explicit checkpoint.
- It cannot stop a second connection anyway.
- The suite run that showed this is recorded in the review.

## 4. The repair

**Generation token.** `SQLiteRestartSafeRuntime` binds its substrate to its generations (`state/sqlite_substrate.py:592`, `require_runtime_generations`):
- A governed act may allocate an identifier (`ensure_allocatable`, `:118`), or tick the deterministic clock (`adapter.py:70-74`, `Clock.guard`), only on the thread running the runtime's open generation.
- The generation is entered through `SQLiteRestartSafeRuntime._generation` (`runtime/sqlite_runtime.py:535`), which opens `transaction()` and then `generation_opened()` (`state/sqlite_substrate.py:610`).
- Anywhere else, `UngovernedDurableWrite` is raised before the clock, the sequence or any governance state moves.
- The guard survives the clock rebuild on governance restore (`restart_runtime.py:384`).

**Owner notification.**
- `on_generation_published` / `_published` (`runtime/sqlite_runtime.py:262-268`) notify the owner after each generation.
- `SQLiteConfigBoundRestartRuntime` binds there (`:723`), exactly once per generation.

**Failure handling.**
- Rollback and governance restore are `BaseException`-safe (`state/sqlite_substrate.py:657`, `runtime/sqlite_runtime.py:586`).
- `persist_visibility_snapshot` (`:645`) undoes its in-memory snapshot only if no generation committed.

**Unchanged.**
- `close()` publishes nothing, and digest, journal, governance and binding verification are untouched.
- Supported paths are unchanged: the facade, and the runtime's governed operations (`recall`, `retain`, `correct`, `dispute`, `delete_current`, `governed_recall`, `commit_proposal`, `governed_delete`, `run_governed_read`, `persist_visibility_snapshot`, `checkpoint`).

**Docs.** docs/47 "Runtime-owned writes (#816)" states the boundary, what it does not cover, and the open window.

**Existing tests.** Four existing tests performed module-level governed acts on facade-owned SQLite adapters, which are instances of #816. They now run those acts through `durable_runtime.run_governed_read` or `runtime.recall`, and assert the same things:
- `test_786_cross_scope_write_authority` F-B;
- `test_809_evidence_reference_authorization` `SharedDomainDurable`;
- `test_domain_eligibility_prefilter`;
- `test_facade_recall_control`.

## 5. Tests and execution

**Test file:** `reference/tests/test_816_runtime_owned_writes.py`, 23 tests. Coverage:
- the issue and its controls;
- each governed act refused with rows, governance export and generation unchanged;
- a store that saw refused acts is row-for-row identical to one that did not;
- storage-level writes stay privileged, are never bound by `close()`, and are refused by recovery;
- the refusal discloses nothing;
- the facade lifecycle across restarts: remember, correct, forget, recall, reopen;
- runtime governed operations and the facade legacy upgrade publish;
- repeated close, close after a refusal, and a handle abandoned without close;
- failure injection in journal publication, with rollback and the guard still holding;
- the commit-then-bind window failing closed;
- a cross-process stale handle;
- tampered fact text, identifier sequence and governance rows rejected;
- a cross-scope correction refused (#786);
- deleted lineage kept and tombstones untouched by a refused delete (#777);
- #802 sidecar erasure across reopen after a refused act;
- review findings F1, F3 and F4.

**Results:**

| Run | Revision | Command | Result |
|---|---|---|---|
| Fail-first | `77c472e6` plus the committed test file plus a two-line import shim (`fail-first/shim.diff`) | `python3 -W ignore -m unittest -v tests.test_816_runtime_owned_writes` | 19 tests at the time (the 4 review-finding tests were added later): 18 failures and 2 errors across 12 guarded behaviours; 7 controls pass (`fail-first/base-run.log`) |
| Focused | `e13d8c58` | the same, from `reference/` | 25 / 25 pass |
| Full suite, base | `77c472e6`, clean | `python3 -m unittest discover -s reference/tests -t reference` | 3008 tests, 4 failures |
| Full suite, repair | `dc7d3f3f` and `e13d8c58`, clean | the same | 3031 and 3033 tests; 4 failures each, the same four as base (`runs/`) |
| Security replays, fresh | `e13d8c58`, clean tree | `python3 reference/run_786_security_replays{,_dsl2,_dsl3}.py --all --output-dir …` | v2: 3 families, 28 cases, PASS. v3: 3 families, 31 cases, PASS. #809 `evidence-reference-authorization-v1`: 13 cases, PASS. Manifests bind the revision (`security-replays-e13d8c58/`; also executed at `dc7d3f3f`, all PASS). |

**Full-suite failures, explained.** The four failures on base and on the repair are the same: the Runtime Baseline equivalence guard, two `test_770` lane-freeze freshness tests and `test_644_v7_gauntlet_identity`. All are by design or environment checks. A full-suite run on the *uncommitted* working tree, before `dc7d3f3f` was committed, also reported four replay-evidence staleness guards (three in `test_644_v7_replays`, one in `test_786_security_replays_v3`). Those guards mark committed replay evidence STALE while runtime files are dirty. They do not fire on the clean commit, and the fresh replay executions above pass.

## 6. Independent adversarial review

`review/REVIEW-816-independent.md`, with runnable probes and their outputs on both heads (`review/probes/`). The reviewer was a separate agent, read-only, in its own worktrees.

**First pass, at `51452b88`.** No blocking findings.

| Finding | Severity | Disposition |
|---|---|---|
| F1: preselected admission and the planner ticked the clock before the guard | Should-fix | **Fixed.** The clock carries the guard. |
| F2: in-memory administrative seams are published by the next generation | Should-fix | **Recorded; owner decision.** Docs narrowed. The seams are `set_shared_domain_members`, `bootstrap_shared_domain_members`, `record_correction` and direct edits to `events`/`extension_state`; this behaviour predates #816. |
| F3: a binding failure after the commit dropped a committed visibility snapshot | Should-fix | **Fixed.** |
| F4: an open transaction is not a generation (unlocked thread, bare `transaction()`, an interrupt leaving the transaction open) | Should-fix | **Fixed.** Thread token; `BaseException`-safe rollback. |
| F5: docs/44 module-level stages raise instead of returning a refusal envelope on a durable handle | Note | **Documented.** Use `run_governed_read`. |
| F6: derived sidecar vectors are written before a refused planner recall | Note | **Documented.** Derived data only. |
| F7: a second `SQLiteTemporalGraph` instance on the same file is not governed | Note | **Documented** as the storage-level layer. |

**Re-verification at `dc7d3f3f`.**
- **Result:** no blocking findings. F1, F3 and F4 are confirmed fixed, and F2, F5, F6 and F7 are confirmed accurately documented.
- **Probes:** p1–p13 were re-run. The new ones cover reentrancy, token leaks, read-only and supported paths, `recover()`, legacy migration and the file profile, and all of them held.
- **Full suite:** 3031 tests, with the same four failures as base.

Two new notes were closed at `e13d8c58`, each with a regression test:

| Finding | Severity | Disposition |
|---|---|---|
| N1: the generation marker `generation_opened()` was public, so a substrate holder could forge a generation and recreate the #816 failure (p11) | Note | **Fixed.** The marker requires the capability that `require_runtime_generations()` returns only to the owning runtime, and refuses nested or cross-thread entry. |
| N2: an interrupt during `persist_visibility_snapshot` left the uncommitted snapshot in memory, and the next generation published it (p13) | Note | **Fixed.** A `BaseException` undoes an uncommitted snapshot, while the committed-generation check is kept. |

**Remaining private-attribute tampering.** Assigning `adapter._clock.guard = None` (p10) is in the same host-privileged class as the storage layer, and is recorded.

## 7. Integration with #815 (for the delivery integrator)

- **Base and diff.** The branch is based on #815's head `77c472e6` and is a strict descendant. Its diff touches:
  - `state/sqlite_substrate.py`, `state/substrate.py`, `runtime/adapter.py`, `runtime/sqlite_runtime.py` and `runtime/restart_runtime.py`;
  - docs/47;
  - four existing tests and one new test file;
  - reports.
- **Protected runtime files change**, so a Runtime Baseline successor declaration must cover the integrated head. The proposed v8 declaration on #805/#815 would need its blob entries regenerated with the sanctioned tool. That is not done here.
- **Landing order:** #805 → #815 → this branch, a fast-forward on #815. Then #691 (`6edc28a3`, also on `77c472e6`) merges with this branch. The expected overlap is `runtime/adapter.py`, in separate regions. Then C-lineage selection.
- **The #691 `recall_context` is compatible, checked by trial merge.** Merging `dc7d3f3f`, and again `e13d8c58`, into #691's `6edc28a3` (scratch worktree, not pushed) auto-merges `runtime/adapter.py` with no conflict. On the merged tree:
  - `test_context_package` and `test_816_runtime_owned_writes` pass, 43/43;
  - `scripts/demo_context_package.py` reports ALL CHECKS PASSED.

  `recall_context` resolves content inside the facade's serialized recall and allocates no identifier outside a generation.
- **At the integrated head, re-run:**
  - the full suite;
  - `test_816_runtime_owned_writes`;
  - the #786 v2 and v3 and #809 replays, executed fresh;
  - the #802 suite;
  - `test_context_package` (with #691).
- **Contract.** No contract version change: the public facade surface is unchanged.

## 8. Remaining failure conditions

1. **The commit-then-bind window, pre-existing.** The configuration binding file is written after the SQLite commit. A crash, or an injected failure, between the two makes recovery fail closed (`configuration binding does not match`). This needs an atomic or derivable binding; it is an owner and design decision.
2. **F2:** in-memory administrative seams are published by the next generation.
3. **The storage-level layer is privileged:** substrate methods, raw SQL, a second substrate instance or an external connection. It is detected at recovery, not prevented.
4. **Derived sidecar vectors** may be written before a refusal.
5. **The file-checkpoint profile** (`RestartSafeRuntime`, `ConfigBoundRestartRuntime`) is unchanged. A direct adapter call there mutates only in-memory state, which is lost at close or published by the next checkpoint; it never causes a digest mismatch.
