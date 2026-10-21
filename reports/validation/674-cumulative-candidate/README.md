# Cumulative runtime candidate: security/durability lineage + PR #835 graph discovery, one v7 successor declaration

**Status: READY FOR INDEPENDENT REVIEW.** Not merged, not published, not security-accepted. No
hosted Actions were run; every commit is `[skip ci]`; every result below was produced locally on
the exact head named. This folder is evidence for the integration decision recorded on
[#674](https://github.com/MythologIQ-Labs-LLC/agent-memory/issues/674#issuecomment-6309464680).

## 1. Identities and ancestry

| Item | Value |
|---|---|
| Base | `main` `7d4c9be63d151a8b7272dea6b8beefd259f994e8` (published Runtime Baseline v6, `declared_successor: null`) |
| Frozen security/durability runtime | `3edbb9ada2cac07acfefe2976cb3a6004525a15b` (runtime tree `3386ec0f`), branch `claude/eager-dirac-bftkfg-809-selfcite`; evidence head `1c0e55311b4d88b491c061f34e61958d9bd53f6f` = the branch head. Merge base with `main`: `38f6a7dcc358e8ee50a38d703b0addb9d8e660d7` (157 commits on the lineage, 281 on `main`). |
| PR #835 | `fix/433-authorized-graph-seeds-no-ci` at `4dda9b00f9c696f9df9214e94f1c4de8b78d2f40`; tested runtime head `8d9612c6` is an ancestor; the branch is a direct child of `main 7d4c9be`. |
| Integration branch | `claude/cool-meitner-0q368g` |
| `2c447c4` | merge of the lineage onto `main` (merge commit; conflict in `docs/ARCHITECTURE_INDEX.md` only) |
| `6f1f39b` | merge of PR #835 (merge commit; conflicts in `runtime/recall_control.py`, `tests/test_recall_control.py`) |
| `e656776f` | cumulative v7 declaration, register pointer, v7 candidate lanes re-pinned |
| **`2d83db0e6eafc4ab12bfe91ad0314b85103dfe6f`** | **the candidate head** (declaration names only replays with frozen fixtures; lanes re-pinned). Protected tree unchanged since `6f1f39b`. |

Neither frozen branch, nor PR #805/#815, nor any historical fixture or evidence folder was modified.
Published v6 record, boundary and qualification are byte-unchanged.

## 2. What main contributed, what each lineage contributed, and how conflicts were resolved

`main` changed exactly one protected file since the merge base: `runtime/runtime_composition.py`
(#829 `MultiRouteRecallResult.selection_trace()`). It auto-merged with the lineage's additions
(the #786 seed gate and the #774 opt-in historical-predecessor API) and with #835's seed gates. The
candidate's protected tree equals the frozen `3edbb9ad` tree plus exactly:

| Path | Source behaviour kept | Why |
|---|---|---|
| `runtime/runtime_composition.py` | main's `selection_trace()` **and** the lineage's #786/#774 code **and** #835's `domain_eligible_identity` / `domain_eligible` seed and neighbour gates on the shared-evidence route | three disjoint hunks; none alters another's semantics |
| `runtime/query_driven_recall.py` | #835 as committed | the lineage did not touch it |
| `runtime/recall_control.py` | **both**: the lineage's #777 `exclude` hook (a deleted generation confers no reachability, reported paths traverse under the reader's context, #809) and the #644 observation receipt / sufficiency code; #835's `eligible` / `eligible_identity` predicates on every seed and hop, eligible-only fan-out accounting, the `max_fanout * 16` eligibility-probe ceiling, and eligible-only exact-identity / graph-seed quotas | the one real behavioural conflict. In the merged traversal the probed checks run in #835's order (identity, fact, then the #777 `exclude`) before a path is accepted. The #777 "reported" traversal now receives the same eligibility predicates as the canonical one, so reported paths cannot cross an ineligible node either (the lineage's version passed none because #835 did not exist). Diff against `3edbb9ad`: #835's diff plus those two touches. |

Deliberately carried from the frozen lineage although older than #809/#821: the #774 opt-in
historical-predecessor API (inside the qualified `3edbb9ad` tree; removing it would have produced an
unqualified tree) and the #644 diagnostic modules. Deliberately **not** carried: the lineage's
`baseline-register.json` pointer and its #644 `baseline-v7-declaration.json`; PR #835's register
pointer and its three-blob declaration; nothing else was dropped. Excluded by instruction: the #691
`lexical_content` selective-context candidate (CHANGES REQUIRED on LongMemEval), unqualified TypeGraph /
TypeScript work, #688 / #831-#834 ontology changes, new storage backends, benchmark tuning.

Documentation: `docs/44` carries the lineage's contract `1.8.0` / #786 / #809 text; `docs/41` carries
#835's graph/provenance seed-boundary paragraph; `docs/ARCHITECTURE_INDEX.md` keeps main's catalog
structure with the lineage's documents 76, 77, 78, 79, 81, 82 filed (validator: 84 numbered docs,
one shelf each). No new architecture document.

## 3. The one successor declaration (docs/67 Step A)

`reports/runtime/baseline-v7-declaration.json`: `agent-memory-runtime-baseline-v7`, predecessor v6,
issue #674, **21 declared blobs** written by `scripts/declare_runtime_baseline_changes.py`, identity
delta `identity.public_contract_version 1.6.0 -> 1.8.0` (the owner's provisional adoption at the PR
#805 checkpoint), `pyproject_change: null`, acceptance evidence = the union of both lineages' lists
(public Gauntlet probe, the two v7 lanes, the five #644 replays, the four security replay families
under the `security_replay` kind adopted at that checkpoint). #835's planned
`scope-safe-graph-discovery-v7` replay is **not** declared: no fixture exists and the #644
fail-closed inventory refuses a declared replay without one; it stays a planned gate to be added by
amending the open declaration. Both superseded declarations (#644 eight blobs, #835 three blobs)
called themselves v7 against v6; neither is carried.

| Command (at `2d83db0e`) | Result |
|---|---|
| `python scripts/declare_runtime_baseline_changes.py --declaration reports/runtime/baseline-v7-declaration.json` | 21 blobs |
| `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` | `TRANSITION; baseline=v6; declared_successor=v7 (issue #674); protected surface = frozen e98e6e7b + 21 declared blobs; deltas=identity.public_contract_version 1.6.0->1.8.0` |
| `... --pinned-only` | exit 1 by design (a transition is not a pinned baseline) |
| `python scripts/validate_runtime_baseline_source.py` | v1-v6 identities match their frozen revisions; `declared successor agent-memory-runtime-baseline-v7 (issue #674) is open` |

The two staged, unscored v7 candidate lanes (#770) pinned the #644 declaration blob; they now pin
the cumulative blob and describe the cumulative change set (`repin_v7_lanes.py`, the same act the
lineage performed at `a8bcf3a3`). Lane id, `frozen_on`, owning issue, rows, budgets and gold
identity are unchanged; no score exists.

## 4. Tests executed on the candidate (clean tree, Python 3.13.16, `reference/requirements.txt`)

| Suite | Result | Log |
|---|---|---|
| `tests.test_multi_route_recall tests.test_query_driven_recall tests.test_recall_control tests.test_typed_graph_retrieval tests.test_domain_eligibility_prefilter tests.test_candidate_materialization` | **84 OK** (includes every #835 required test and the lineage's recall-control tests) | `runs/targeted-retrieval-e656776f.txt` |
| `test_809_legacy*` (13 self-reference + 12 frozen-store) | 25 OK | `runs/focused-test_809_legacy_-e656776f.txt` |
| `test_809_evidence_reference_authorization*` / `test_809_security_replay*` | 25 OK / 8 OK | `runs/` |
| `test_776*` / `test_777*` / `test_786*` | 46 OK / 27 OK / 68 OK (1 expected failure) | `runs/` |
| `test_deletion_completeness*` / `test_deletion_authority` / `test_historical_evidence_admission` | 6 / 11 / 10 OK | `runs/` |
| `test_821*` / `test_816*` / `test_802*` / `test_sqlite*` / `test_774*` | 48 / 25 / 16 (1 skip) / 10 / 58 OK | `runs/` |
| `test_644*` / `test_770*` | 59/60, 20/22: only the three pre-existing freeze guards fail (below) | `runs/focused-test_644_-2d83db0e….txt`, `runs/focused-test_770_-2d83db0e….txt` |
| #821 crash-window matrix (`probes/crash_window.py`, 9 kill points) | **outcome-identical** to `crash-window-3edbb9ad.json` (only `crash_unix_time` / `elapsed_s` differ) | `runs/crash-window-e656776f.{json,txt}` |
| 7 security replay families (`run_786_security_replays{,_dsl2,_dsl3}.py --all`) | **all PASS**; `observations_sha256` **identical** to the frozen `3edbb9ad` record for every family (`0507a3a8`, `1b533268`, `a90b8a84`, `617805b9`, `510ff2a6`, `1049e537`, `70da7a3a`); manifests bind `source_commit 2d83db0e` | `security-replays-2d83db0e…/` |
| `scripts/verify_786_security_replays.py --reexecute` | 4/4 VERIFIED, re-executed, `evidence_verified: true` | `security-replays-…/verify-reexecute.json` |
| 5 #644 replays (`run_644_v7_replays.py --all`) + `verify_644_v7_replays.py --reexecute` | all PASS, `observations_sha256` identical to `644-v7-replays-at-head`; 5/5 VERIFIED re-executed | `644-v7-replays-2d83db0e…/` |
| Workflow policy / inventory / FinOps preflight (`test_github_actions_workflow_policy`, `test_sync_workflow_inventory`, `test_finops_local_preflight`) | 31 OK | — |
| Validators | architecture index OK (84 docs); schemas (74) and fixtures (64) OK; doctrine boundaries OK; wiki links OK; `git diff --check` clean on every authored file (three pre-existing Markdown hard-break lines in lineage plan docs and main's index line 3 are the only trailing-whitespace hits) | — |
| **Full reference suite, `2d83db0e`** | **3134 tests, 6 failures + 1 error, 22 skipped, 1 expected failure** (299 s) | `runs/full-suite-candidate-2d83db0e….txt` |
| Full reference suite, `main 7d4c9be` (same environment) | 2573 tests, 4 failures + 1 error, 21 skipped | `runs/full-suite-main-7d4c9be.txt` |

Fail-first evidence is inherited, not re-manufactured: the lineage's preregistered REDs
(`809-legacy-upgrade/self-reference/fail-first-*.txt`, `821-atomic-config-binding/fail-first/`) and
#835's recorded fail-first runs stand at their own revisions; on this head every one of those tests is green.

### Existing versus newly introduced failures

| Test | Also fails on | Cause | Introduced here? |
|---|---|---|---|
| `test_keyed_rebinding_benchmark…test_wave2_harvest_matrix_records_uor_r4_disposition` (error) | `main` | `reference/fixtures/harvest-closeout-wave2.json` absent in the checkout | no |
| `test_benchmark_author_golden_path…`, `test_gauntlet_durability…`, `test_gauntlet_external_example…` | `main` | Gauntlet adapter subprocesses exit 2 in this container → `blocked` | no |
| `test_644_v7_gauntlet_identity…test_own_checkout_at_frozen_revision_is_served` | `3edbb9ad` | the #644 contestant is pinned to runtime `16a248b1` | no (lineage freeze guard) |
| `test_770_v7_lane_freeze_independent.ReplayEvidenceFreshness` (2) | `3edbb9ad` | asserts the runtime unchanged since `16a248b1` | no (lineage freeze guard) |
| `test_benchmark_integration_contract…keeps_runtime_baseline_equivalence` | `main`, `3edbb9ad` | **passes on the candidate**: main's #829 drift was undeclared; the cumulative declaration declares it | resolved |

Newly introduced failures: **none**. The six posture-binding failures the stale #644 lane pin caused at
the first integration commit, and the five #644 inventory failures the fixture-less #835 replay caused,
were both fixed before the head (`e656776f`, `2d83db0e`); the logs of those intermediate states are kept.

## 5. Task correctness (Phase E): candidate `2d83db0e` versus `main 7d4c9be` versus frozen `3edbb9ad`

Harness: `phase-e/compare_recall.py` (deterministic, in-process, SQLite composition runtime; the same
script runs against any tree). Results: `phase-e/*.json`.

| Scenario | `main` | frozen `3edbb9ad` | candidate |
|---|---|---|---|
| A1 required accessible neighbours ranked **behind** 12 other-project neighbours (fan-out 8) | required recalled **0/3**; foreign not caller-visible | 0/3 | **3/3**; foreign not caller-visible |
| A2 eligible target reachable only **through** an other-project intermediate | reached (bridges through the foreign node) | reached | **not reached** (docs/41: no hop through an ineligible node); bridge never caller-visible on any tree |
| A3 one eligible neighbour ranked behind 129 ineligible ones | not recalled (fan-out spent) | not recalled | **not recalled**: the `max_fanout * 16 = 128` eligibility-probe ceiling is the bounded-work trade-off #835 declared; 1.5 ms |
| B shared-domain neighbour (held in `shared:team`, which the reader holds) via typed graph / shared-evidence route / default multi-route; other-project private fact exposure | recalled / recalled / recalled; none exposed | — | **recalled / recalled / recalled; none exposed** (the fix does not suppress legitimate shared-domain evidence) |
| C wrong-subject lexical collision (`bob phone` over `alice phone`) | top-1 correct | — | top-1 correct |
| D no-answer query | 0 candidates / 0 admitted / 0 returned | — | same |
| E facade deletion: source withheld after `forget`; derived memory citing it withheld; deleted id in public `candidates` | yes / yes / **id visible** | — | yes / yes / **id hidden** (#777 projection) |
| F context budget `k=1` | admitted 2, returned 1, `applied` | — | same |
| G facade `recall` p50 / p95 ms (1,500-fact corpus, 200 queries, ~393 admitted per query; three alternating runs) | 60.6-64.6 / 88.3-97.1 | 75.3 / 116.6 | 77.0-81.5 / 113.0-128.6 |
| G facade `remember` p50 / p95 ms | 5.6-5.9 / 8.3-8.4 | 6.5 / 9.3 | 6.1-7.0 / 9.3-10.1 |
| G controlled graph recall on a 400-neighbour hub (half other-project), p50 / p95 ms; eligible neighbours admitted | 1.5-1.7 / 2.0-2.3; **4** of 8 slots | 2.5 / 3.3; 4 | 2.3-2.6 / 2.6-3.3; **8** of 8 slots |

Reading: the ~25 % recall-latency and ~50 % hub-traversal overheads are already present at the frozen
security head (per-fact deletion-lineage, derivation and public-projection work) and are **not** added
by the #835 changes, which cost nothing measurable here and fill the graph budget with eligible
neighbours instead of spending it on hidden ones. The surviving trade-off is explicit: bounded work
(probe ceiling) over recall completeness for an eligible neighbour ranked behind more than 128
ineligible ones, plus the full-adjacency sort #835 already disclosed.

**Not run, acceptance blocker:** the full AMB PrecisionMemBench and LongMemEval_S lane evaluations at
this head (the v7 lanes exist, unscored; no external harness or dataset is available in this
container), the public Gauntlet probe, and #835's scope-safe graph replay (no fixture yet). No accepted
benchmark denominator or historical score was touched.

## 6. Statuses (kept distinct)

| | |
|---|---|
| Implementation | **integrated** at `2d83db0e` (one tree, both lineages, conflicts resolved as above) |
| Declaration | **TRANSITION** under the real register; one successor slot, v7 over v6 |
| Exact-head regression | **done**: no integration-introduced failure; replay digests identical; crash matrix identical |
| Security acceptance | **not reached**: needs the owner's read of the lineage's review records and an independent adversarial read of the merged `recall_control.py` traversal (the one hand-reconciled protected hunk) |
| Lane / Gauntlet / graph-replay qualification | **not run** (blockers above) |
| Merge, publication, activation | **not done, not requested** |

Disposition: **READY FOR INDEPENDENT REVIEW**; **BLOCKED for acceptance** on the lane, Gauntlet and
graph-replay evidence and the security sign-off.
