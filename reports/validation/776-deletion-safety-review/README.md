# #776 P0 deletion safety: independent adversarial qualification

| | |
|---|---|
| Candidate | `implementation/776-logical-deletion-historical-admission-no-ci` @ `c34a340fc25cc21df3aa9d987d7712712f00caa6` (verified), base v7 `9b025f945e7ec4a1e349e56bba251e3122413e88` |
| Validation branch | `validation/776-deletion-safety-review` (from `c34a340`) |
| Environment | Claude Code cloud, Python 3.13, `reference/requirements.txt`. No Actions, no PR, no merge, v7 declaration and register unchanged, v8 draft not activated. |
| Verdict on `c34a340` | **CHANGES REQUIRED (P0 open).** The authored fix closes historical *recall*, but a deleted memory's earlier values are still disclosed through the public `AgentMemory.write_semantics` API, including after restart. It also introduces two availability regressions and an O(tombstones) admission cost. |
| Verdict on repaired head `24bbef1` | **All findings repaired; tests pass.** No P0 exposure on four corpora and no served-quality change. Still needs a successor declaration and independent replay before any baseline use (it is a protected change). |

## Commits (tests before repairs)

| Commit | What | Result at that point |
|---|---|---|
| `a641723` | 13 adversarial tests, including #774 `PreExistingDeletionLeak` **without** `expectedFailure` | 7 fail at `c34a340` (`logs/adversarial_at_c34a340.log`) |
| `f43037b` | typed-graph route control | passes at `c34a340` |
| `4d7c361` | deleting a superseded version must not hide the live memory | fails at `c34a340` |
| `be255a6` | **repair** (adapter only) | all pass |
| `223832c` | a further deletion must extend, not rebuild, the index | fails at `be255a6` |
| `24bbef1` | **index extended in place** | 23/23 #776 tests (`logs/776_tests_final.log`) |

The 5 authored tests pass at `c34a340` and fail 5/5 at the tests-first commit `5edf72b`, as claimed.

## Findings against `c34a340` (per invariant)

| # | Invariant | Result at `c34a340` | Severity | Repaired at `24bbef1` |
|---|---|---|---|---|
| 1 | Deletion blocks every superseded version from historical recall | **Holds.** The #774 reproduction passes without `expectedFailure`. | – | holds |
| 2 | Other memories' history stays available | Holds | – | holds |
| 3 | Tenant, project, task and purpose restrictions intact; an out-of-scope reader never learns of the deletion | Holds: the scope reason precedes the deletion reason | – | holds |
| 4a | **Indirect disclosure.** `AgentMemory.write_semantics(old_uuid)` after `forget()` | **Returns the deleted earlier value** (typed `value: "Oslo"`), also after `close()`/reopen. `semantic_proposals()` still lists a proposal targeting the deleted earlier version. `_semantics_visible` checked only the head tombstone. | **P0** | refused |
| 4b | Semantics of a fact derived from an earlier version (`evidence_refs`) | Recall refuses it, but `write_semantics` serves it | P1 | refused |
| 5 | Re-creating a deleted memory id (governed `remember` after `forget`) | Commits (`committed: true`) but is **permanently invisible** (`logical_memory_deleted`). This is a regression versus v7, which admits it. | P1 (availability; silent) | admitted as a new lineage; the old lineage stays refused |
| 6 | `governed_delete` of one superseded version (accepted by GAP-SEC-03 LD2) | **Hides the live current memory**, although `current_fact_uuid` still names it | P1 (availability) | only that version is deleted |
| 7 | Permanent deletion follows its declared policy (physical removal) | Removes only the head. **Earlier versions' text stays in the substrate and in `substrate.json`.** Never admitted, but contrary to the declared policy. | P1 (erasure) | every version in the lineage is physically removed |
| 8 | Pruning keeps content recoverable and inadmissible | Holds | – | holds |
| 9 | Restart and checkpoint recovery cannot resurrect history | Recall holds after `ConfigBoundRestartRuntime.recover`; semantics did not (4a) | see 4a | holds; legacy tombstones without the new field fail closed |
| 10 | Exact-identity, lexical, vector, typed-graph, historical and composed routes share admission | Holds. The vector and graph routes rediscover the residue as a *candidate*, and it is refused at admission. | – | holds |
| 11 | Tombstone checks at scale | `tombstoned_ids()` was rebuilt per candidate. Admission cost: 3 µs at 0 tombstones → 12 ms per candidate at 100k; recall of 40 facts took 322–414 ms at 100k (`logs/perf_tombstones_c34a340.log`). | P1 (performance) | O(1) indexed lookup; recall flat at about 2–3 ms at 100k (`logs/perf_tombstones_repaired.log`). The index is extended in place per deletion. |

## The repair (`reference/agentmem_ref/runtime/adapter.py` only)

- **Lineage record:** a tombstone now records `deleted_fact_uuids`.
  - Deleting a head records the memory's whole live lineage.
  - Deleting a superseded version records only that version.
  - An earlier deleted lineage is never re-recorded.
- **Admission and semantics share one check:** `_admission_refusal` and `_semantics_visible` both use `_deleted_lineage_reason`, an indexed fact→memory map.
  - This governs `write_semantics`, `semantic_proposals`, `current_governed_typed_claim` and the transition witnesses.
- **Permanent deletion** physically deletes every version in the recorded lineage and drops them from the in-memory slot index.
- **Pre-#776 tombstones:**
  - A head tombstone (a fact never replaced) covers every fact bound to the memory and created no later than `deleted_at`. This fails closed.
  - A superseded-version tombstone covers only itself.
  - Tested after a real checkpoint and restart.

## Served quality (v3 runner from adopted evaluator `9961067`; instant `2026-10-12T12:00:00Z`)

| Corpus | Runtime | P0 prohibited / stale | answer@1 | all-critical |
|---|---|---|---|---|
| Halcyon v1.1 | v7 / `c34a340` / `24bbef1` | 0/0 · 0/0 · 0/0 | 13/21 each | 19/21 each |
| Cedarline v1.1 | v7 / `c34a340` / `24bbef1` | 0/0 each | 14/20 each | 14/20 each |
| Brightwater v1 | v7 | **1**/0 (B05 `meter-arq`) | 4/10 | 8/10 |
| | `c34a340`, `24bbef1` | 0/0 | 4/10 | 8/10 |
| **Fenmoor v1** (frozen at `de1eda5` before any #776 run) | v7 | **2**/0 (F02 and F11 serve the deleted `chute-n`) | 9/12 | 12/12 |
| | `c34a340`, `24bbef1` | 0/0 | 9/12 | 12/12 |

- **Halcyon and Cedarline:** served lists are byte-identical across all three runtimes.
- **Brightwater:** the only change is B05, which no longer serves `meter-arq`.
- **Fenmoor:** the only changes are F02 and F11.
- **Repair vs candidate:** identical served lists on every corpus.
- Manifests and quality reports are in `runs/`.

## Full suite and baseline governance

- **Full suite:**
  - `c34a340`: 2715 run, 5 failures.
  - `24bbef1`: 2733 run, the **same 5** failures (`logs/full_776_*.summary.log`).
  - Those failures are 4 protected-runtime freeze/staleness guards (an undeclared change to protected `adapter.py`) and the pre-existing durability `adapter_eof`, which also fails on v7.
  - The three `test_644_v7_replays.EvidenceVerification` tests fail only on an *uncommitted* working tree, and pass once committed.
- **Baseline checker:** `scripts/check_runtime_baseline_equivalence.py --candidate HEAD` fails identically for the candidate and the repair (`declared blob mismatch for reference/agentmem_ref/runtime/adapter.py`). That is the intended response to an undeclared protected change.
- **Not modified:** the candidate overlay `reports/runtime/proposals/776-…overlay.json` still names the candidate blob `eba06291`. The repaired blob is `251972b0f85a4bdc286db9d58f23f35cf7479d6c`.

## Remaining risks (not fixed here)

1. **Merge conflict with #774:** `memory_deleted` / `lineage_head` treat a memory id as deleted forever, using memory-level `tombstoned_ids()`. Combined with this repair, a re-created memory would be invisible to the #774 selector. They must be reconciled to lineage semantics before combining.
2. **Graph identifiers:** `ControlledRecallResult.graph_candidate_hits` keeps the paths of refused candidates, including deleted fact uuids as intermediate nodes. This exposes identifiers only, not content, and is pre-existing.
3. **One-hop derivation:** derived-from-deleted refusal follows one hop (`evidence_refs`), matching the pre-existing `derived_from_tombstoned_source`. Transitive derivation is not governed.
4. **Relation metadata:** a surviving fact's own write-time `relations` still name the deleted fact uuid and memory id (pre-existing for head deletion too).
5. **Checkpoint cost:** the durable checkpoint serializes every tombstone on each commit, an O(T) write cost that this repair does not change.
