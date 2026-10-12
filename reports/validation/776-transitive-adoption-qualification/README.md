# #776 transitive-deletion adoption at `5d90965`: qualification and traversal review

| | |
|---|---|
| Adopted | `implementation/776-logical-deletion-historical-admission-no-ci` @ `5d90965f62506f3c27f11247a329a4fec1f391f3` (verified) |
| Protected blob | `reference/agentmem_ref/runtime/adapter.py` = `6823eeaff24c5d94892ae2417fd6cfdae95339cb` (**identical** to the reviewed `42c218a`; `42c218a..5d90965` changes only docs and the overlay) |
| This branch | `validation/776-transitive-adoption-qualification`: review tests `3d8c510` (one fails) → memo fix `bd16a7e` (adapter blob `fe25923f…`) |
| Environment | Claude Code cloud, Python 3.13, evaluator `9961067` v3. No Actions, no PR, no merge, v7 unchanged, no successor published. |
| Verdict at `5d90965` | **CHANGES REQUIRED (P1, not P0).** Content-exposure P0s are closed on every measured corpus. A stale-cache defect makes the transitive refusal depend on cache state (repaired at `bd16a7e`). **Not a qualified baseline:** the protected change is undeclared, so the freeze guards fail as intended. |

## Execution at `5d90965`
| Suite | Result |
|---|---|
| 26 #776 tests | 26/26 (`logs/776_26_tests_at_5d90965.log`) |
| Full reference suite | 2736 run, 5 failures = 4 protected-runtime freeze guards plus the pre-existing durability failure (`logs/full_suite_5d90965.summary.log`) |

## Traversal review (`reference/tests/test_776_transitive_traversal_review.py`, written before any repair)
| Case | Result at `5d90965` |
|---|---|
| Cyclic provenance (no deletion) terminates; facts stay admitted | pass |
| Mutual/self-citation with a deleted source is refused | pass. Duplicate or empty `evidence_refs` are rejected at write time by the proposal schema. |
| Unknown provenance (non-fact refs, a not-yet-existing id) is not treated as deletion | pass |
| Re-created memory id: derivations of the new generation are live (2 hops); old-generation derivations stay refused | pass |
| Legacy tombstone without `deleted_fact_uuids`, after a real checkpoint and restart, still taints 2-hop derivations | pass |
| 300-hop chain refused in under 5 s | pass |
| **Decision independent of query order / cache** | **FAIL.** A fact citing an id before it exists; a later write binds that id to a deleted version (no new deletion). The live process admits the citing fact (`before=True live=True`); after restart it is refused (`fresh=False`). The negative memo was keyed on deletion state only. |

**Repair `bd16a7e`:** the memo key now also includes the fact-binding table (id and size), because every governed write binds a fact. Results:
- all 33 #776 tests pass (`logs/776_33_tests_at_bd16a7e.log`);
- full suite: 2743 run, the same 5 failures;
- tombstone scale unchanged: recall with 40 facts is about 2–3 ms at 0–100k tombstones (`logs/perf_memofix.log`).

## Five corpora (same v3 harness; `runs/`)
| Corpus | v7 P0 | `5d90965` and `bd16a7e` P0 | answer@1 / all-critical (identical across all three) | Changed served lists vs v7 |
|---|---|---|---|---|
| Halcyon v1.1 | 0 | 0 | 13/21 · 19/21 | none |
| Cedarline v1.1 | 0 | 0 | 14/20 · 14/20 | none |
| Brightwater v1 | 1 | 0 | 4/10 · 8/10 | B05 (deleted `meter-arq` removed) |
| Fenmoor v1 | 2 | 0 | 9/12 · 12/12 | F02, F11 (deleted `chute-n` removed) |
| Blind theatre v1 | 1 | 0 | 9/21 · 11/21 | Q15 (deleted `fee-900` removed) |

`5d90965` and `bd16a7e` serve **byte-identical** lists on all five corpora.

## Gates
1. **P0 deleted content: PASS** on the five corpora and all public API tests at `5d90965`.
2. **Traversal correctness: CHANGES REQUIRED** at `5d90965` (stale memo); repaired at `bd16a7e`.
3. **Quality: PASS.** Only deleted content was removed.
4. **Baseline qualification: BLOCKED / not claimed.** The protected change is undeclared, and a successor declaration and independent replay are required.
5. **Performance: PASS.**

Public metadata privacy (deleted IDs in diagnostics) is tracked separately in #777.
