# #770 v7 lane freeze: independent validation

## Verdict

**`f6c0fa5`: CHANGES REQUIRED.** I found seven defects, L1 to L7. All are repaired on `validation/770-v7-lane-freeze-independent` at **`9b025f9`**, with failing reproducers committed first (`f50bdcf`, `4e75685`). The existing lane-catalogue test is the reproducer for L7.

- The protected runtime is unchanged.
- The v6 lanes and v6 evidence are byte-identical to `main`.
- The five replay fixtures are byte-identical.
- No workflow ran, and nothing is accepted, merged or published.

**At `9b025f9` the v7 lanes are ready for deliberate dispatch, subject to the owner adopting these commits.** A passing local probe and a valid lane freeze are not acceptance.

## 1. Identity

| Check | Result |
|---|---|
| Branch | `implementation/770-v7-lane-freeze-review-no-ci` @ **`f6c0fa5f961368e4aa113633fc29b5b8973c0e87`** equals the expected SHA, and the worktree is clean. |
| Ancestry | Eight commits on top of `f92ea42`, the #644 Gauntlet validation bundle, which in turn carries `b854d5e`, `29d4b79` and `16a248b`. |
| Changed files | The two `-v7` lane records, `baseline-v7-declaration.json` (2 lines), one dispatch option per workflow, and `test_770_v7_lane_freeze_guards.py`. |
| Declaration | Blob `ae8012a…`. It now requires the `-v7` lane IDs. `declare_runtime_baseline_changes.py` reproduces it byte for byte (`logs/declare-idempotence.log`). The generator owns only `declared_changes`, so the hand edit to `acceptance_evidence_required` is the sanctioned path. |
| Workflows | Each adds exactly the v7 option. Defaults stay at v6. Permissions stay `contents: read`. Referenced secrets are unchanged from `f92ea42`. |
| Runtime | The protected surface equals `16a248b`, and the checker reports TRANSITION v6 to v7 with no deltas, at `f6c0fa5` and at `9b025f9`. |

## 2. Commands as submitted (`f6c0fa5`)

| Command | Result |
|---|---|
| `agent-memory benchmark validate-lane …/amb-precisionmembench-retrieval-v7.json --json` | **rc 2, refused**: `$.findings[0] … is not of type 'string'` |
| `agent-memory benchmark validate-lane …/longmemeval-s-retrieval-parity-v7.json --json` | **rc 2, refused** (same error) |
| `validate-lane` on each v6 lane (control) | rc 0, valid |
| `agent-memory benchmark lanes --json` | **rc 2**: one invalid record breaks the whole catalogue |
| `-p test_770_v7_lane_freeze_guards.py` | 2/2 OK. The guard never validates the lanes. |
| Full suite, CPython 3.13 | **FAILED: 87 errors and 2 failures** in 2690 tests (`logs/full-py313-f6c0fa5.log`) |
| `check_runtime_baseline_equivalence.py --candidate HEAD` | TRANSITION, rc 0 |

## 3. Field-by-field v6 to v7 comparison

`scripts/lane_field_diff.py` compares each v7 lane with its v6 lane read as frozen. "Read as frozen" means accepted rows go back to frozen without a `status_reason`, and the v6 acceptance finding is dropped; this is the `_as_frozen` convention the v3 to v6 generation tests use. Every differing leaf is classified against the identity-only list that the v5 to v6 generation established:
- the lane-level fields (`lane_id`, `frozen_on`, `owning_issue`, `description`, `freeze_rationale`, `comparability.notes`, `comparability.not_comparable_to`);
- the runtime-baseline posture of every Agent Memory row that carries one;
- the control's display name;
- a v7 sentence on the deferred shadow and semantic reasons;
- on LongMemEval, the dispatch unit.

| | `f6c0fa5` | `9b025f9` |
|---|---|---|
| AMB | 18 differences. **7 unlisted:** `findings` replaced by an object, and `status_reason` on 3 frozen rows. **7 listed changes missing:** `not_comparable_to[0]`, the shadow posture, and the deferred reasons. | 18 differences, 0 unlisted, 0 missing |
| LongMemEval | 19 differences. **7 unlisted** (the same pattern). **11 listed changes missing:** `not_comparable_to[0]`, and the shadow and semantic postures and reasons. | 23 differences, 0 unlisted, 0 missing |

These items are unchanged from v6 in both versions: dataset, fixtures and digests, selection, budget, gold identity, evaluator and scorer, harness revision and source blobs, the runner and bridge blobs, every row's `source` and `adapter`, the dependency pins, execution requirements, `change_rule` and `authority_effect`. The details are in `lane-field-diff-f6c0fa5.json` and `lane-field-diff-9b025f9.json`.

**Status values are valid in both versions:** the lanes are `frozen`; the control, baseline and Mem0 rows are `frozen`; the shadow, semantic and Hindsight rows are `deferred`. No row is accepted.

**`frozen_on` is correct in both versions:** 2026-10-10 matches the commit dates.

## 4. Defects and repairs

| | Defect | Reproducer | Repair | After |
|---|---|---|---|---|
| **L1** | Both lanes violate `schemas/same-harness-lane.schema.json`: `findings[0]` is an object and `freeze_rationale` is a string. `list_lanes()` validates every lane, so `benchmark lanes`, `get_lane()` and every v1 to v6 lane test break. The workflows' first precondition step (`validate-lane`) refuses every v7 dispatch, and the importers' `lane_digest()` raises. | `test_lane_validates_and_resolves`, `test_every_committed_lane_still_lists` (`f50bdcf`) | The lanes are rebuilt by `scripts/rebuild_v7_lanes.py` (`e944f08`). | Both valid (rc 0). Digests: AMB `12acd4c7…`, LongMemEval `e730636f…`. |
| **L2** | **Inherited v6 governance.** `not_comparable_to[0]` and the rule note still hold the control to equality with **-v5** and say a difference "blocks Runtime Baseline **v6** publication". The description still says it re-executes the -v5 rows in the transition to v6. The rationale concatenates the v6 rationale. | `test_comparability_and_rationale_state_the_v7_rule` | The texts now state equality with the accepted **-v6** control, with any difference blocking **v7** publication. `scripts/check_cross_fact_attribution.py` is reused with -v6 as the base. | PASS |
| **L3** | **Incomplete runtime binding.** The deferred Agent Memory rows (AMB shadow; LongMemEval shadow and semantic) keep the v6 posture `1ac4d7d8…`. At -v6 every such row was re-pinned. The LongMemEval importer binds the posture per Agent Memory row. | `test_every_agent_memory_row_carries_the_v7_posture` | Every posture row now carries the v7 posture `ae8012a…`. | PASS |
| **L4** | **Acceptance metadata misuse.** Frozen rows carry a `status_reason`, and the v6 findings (environment facts that still apply) are replaced. The established acceptance check rebuilds the executed lane digest with `_as_frozen()`, which deletes row `status_reason`s. After acceptance, that rebuilt digest would no longer equal the digest the run executed. | `test_findings_and_rows_carry_over_without_v6_acceptance`, `test_acceptance_digest_reconstruction_round_trips` | Frozen rows carry no `status_reason`. The v6 findings carry over minus the v6 acceptance note. The "no v7 score accepted" statement moves to the description and rationale. | PASS |
| **L5** | **Gauntlet regression.** The `b854d5e` identity guard diffs all of `reference/agentmem_ref`, so the new lane records make the correct checkout answer `runtime_identity_unverified`. | The existing `test_own_checkout_at_frozen_revision_is_served` fails at `f6c0fa5`. | The guard uses the sanctioned Runtime Baseline source boundary, which excludes `evaluation/**` (the adapter process imports none of it). The adapter is re-pinned to `28b8333…` (`9d1fda0`). | Clean checkout: served. Edit or untracked file under `evaluation/`: served. Edit or untracked file under `runtime/`: refused (`logs/guard-negative-controls-9d1fda0.log`). |
| **L6** | **Replay verifier regression.** It compares the tree hash of all of `reference/agentmem_ref`, so all five replays report **STALE** (exit 1), although re-execution reproduces every observation. | `ReplayEvidenceFreshness` (`4e75685`) | Staleness is now checked against the runtime source boundary, which also catches uncommitted runtime edits that the old HEAD check missed (`7ee8ae5`). | 5 × VERIFIED with re-execution. The tamper challenge still detects every mutation. Acceptance: NOT GRANTED. Inventory: BLOCKED. |
| **L7** | `test_cli_lists_and_validates_lanes_without_execution` enumerates every lane ID and was not extended. L1 masked this at `f6c0fa5`; it fails at `9d1fda0`. | The existing test | It now lists the v7 IDs, requires them to be `frozen`, and requires every earlier lane, -v6 included, to be `accepted` (`9b025f9`). | PASS |

`frozen_before_any_score: true` is kept. The rationale discloses that non-importable local reproductions of this exact configuration at `b854d5e` (#644) were visible before the freeze. No frozen fact differs from -v6, so they could not have shaped any frozen choice.

## 5. Dispatch and import gates (credential-free, no Actions)

`scripts/workflow_gate_probe.py` runs each workflow's own lane-precondition step: the verbatim `validate-lane` call and inline Python, with only the `${{ inputs.* }}` values substituted. It also runs the Runtime Baseline posture computation. AMB fixtures are downloaded from their pinned URLs and digest-checked.

| Dispatch | `f6c0fa5` | `9b025f9` |
|---|---|---|
| AMB v7: agent-memory, bm25, mem0-explicit | REFUSED at `validate-lane` | **ADMITTED**; the workflow's declaration blob equals the lane pin |
| LongMemEval v7: agent_memory, lexical_overlap, mem0_explicit | REFUSED at `validate-lane` | **ADMITTED**; the workflow's declaration blob equals the lane pin |
| v7 deferred shadow row (both) | REFUSED | REFUSED (`row["status"] == "frozen"`) |
| v6 lane (both) | REFUSED (`accepted`) | REFUSED (`accepted`) |

The importer negative controls are in `test_770_v7_lane_freeze_independent.V7ImporterRefusals`, run against the v7 lanes.
- **Admitted:** TRANSITION with blob `ae8012a…`.
- **Refused:**
  - the v6 declaration blob `1ac4d7d8…`;
  - the pre-#770 v7 blob `6e13cbae…`;
  - no declaration blob;
  - checker FAIL;
  - a v6 lane given the v7 blob;
  - a v6 lane digest;
  - a v6 lane ID;
  - a deferred row;
  - an executing revision that does not carry the v7 lane (`16a248b`).

The importers trust the checker state that the workflow recorded and do not recompute it. That is the existing design, unchanged by #770, and is noted only.

## 6. Suites and checker at `9b025f9`

| Command | Result |
|---|---|
| Full suite, CPython 3.13.16 | **2710 OK** (skipped=25), rc 0 |
| Full suite, CPython 3.12.3 | **2710 OK** (skipped=17), rc 0 |
| `-p 'test_770_*.py'` | 22/22 OK |
| `-p 'test_644_v7_*.py'` (Gauntlet and replays) | 34/34 OK |
| `validate-lane` on each v7 lane | rc 0, valid, frozen |
| Gauntlet `validate-adapter` and `gauntlet-orchestration-retrieval-probe-v1` | valid; complete; `exact_top1` 1.0 over 3 samples; authority none (`gauntlet-run/`) |
| `check_runtime_baseline_equivalence.py --candidate HEAD` | TRANSITION v6 to v7, frozen `e98e6e7` plus 8 declared blobs, no deltas |

## 7. Not done, and still required

- **Workflow dispatch.** Once the owner adopts this freeze, dispatch the 3 AMB rows and the 3 LongMemEval rows × 2 planes from the commit that carries it. Then import the results with the importers, verify per-query equality with the accepted -v6 evidence, and have it independently reviewed. `9b025f9` changes the adapter blob and the verifier, but not the declaration or the lanes' pins.
- **Acceptance.** No META_LEDGER entry was made, and no acceptance or v7 publication was recorded.
- **Workflow defaults** remain `-v6`, which the workflows refuse as accepted. Whether to move the defaults is the owner's choice.
