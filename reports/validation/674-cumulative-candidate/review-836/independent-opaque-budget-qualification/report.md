# Independent qualification: opaque graph neighbours and the typed-graph discovery budget (PR #836, comment 6318816265)

Independent runtime security / retrieval-correctness engineer. Executed 2026-10-21 in a full checkout
(environment: `environment.txt`). Nothing in PR #836, its frozen candidate `07cd8692`, the benchmark
branch, any lane, declaration, fixture or accepted evidence was modified by this review. The only
commits of this review are on `claude/peaceful-carson-o5qw6f`: this evidence directory and one test
module. An independently written repair exists as local commit `a055e0e` (diff recorded here); it was
not pushed because the owner's follow-up `2ad4cf23` already carries the same correction.

## 1. Verified exact source and runtime

| Item | Verified value |
|---|---|
| Cumulative runtime | `07cd8692bcf26fd677c71f805f04f73a6332ed91`; `runtime/recall_control.py` blob `c16452efa05bdb3f4db892e3a0918cba25dc5ec2` |
| Declaration blob | `a78797cbfca0e017e99c7e3e00823ded3ef1653b` = `reports/runtime/baseline-v7-declaration.json` at `07cd8692`; names `recall_control.py` `c16452ef` |
| Test branch / commit | `review/836-opaque-budget-failfirst-no-ci` @ `ef8fff690eee4a24ecb423691b815abda26f9fd2`, parent `07cd8692` (ancestry verified), one file added, clean worktree |
| Owner follow-up (pushed 15:06Z, after this review's source snapshot) | `2ad4cf23d366fc784a486b0245550230e64bfa25` on the #836 branch; `recall_control.py` `9fa861c3`; declaration `7de94f11`; lanes re-pinned to it |
| Equivalence check | `TRANSITION`, 21 declared blobs at `07cd8692` and at `2ad4cf23`; declared-blob mismatch (expected) on the un-re-pinned independent repair |
| Environment | Python 3.13.16, `reference/requirements.txt` pins installed; shallow clone (affects only `validate_runtime_baseline_source.py` and the two register-pin tests, both trees alike) |

## 2. Fail-first results (raw: `fail-first-RED-preregistered-tests-at-07cd8692.txt`)

Both preregistered tests are **RED on the unmodified runtime**, each failing on the assertion the
reviewer predicted: the live sibling `shelf` is absent from `admitted` (only the seed is admitted).

* `test_opaque_node_must_not_spend_eligible_fanout_one` (`max_fanout=1`, `graph_limit=2`): RED.
* `test_opaque_node_must_not_fill_only_canonical_candidate_slot` (`max_fanout=2`, `graph_limit=1`): RED.

Fixture and positive controls were verified before interpreting RED: the control arm (hidden node
absent) admits the sibling at both budgets; the withheld precondition holds; store identities align
across arms. **Test-harness defects found: none** in the preregistered module. The one harness defect
of this review was in my own control module (the seed's eligibility check was counted as a neighbour
probe); corrected before any conclusion was drawn, no expectation changed. The owner's module
`test_836_opaque_fanout_noninterference.py` labels one case "public facade": it installs the controlled
planner by assigning `runtime.recall_planner` directly, which no supported constructor or facade
parameter does (section 4); the test is valid for the governed planner, the label overstates the surface.

## 3. Confirmed versus rejected hypotheses

Confirmed at the retriever (`retriever-differential-three-trees.txt`) and through the governed planner
with full diagnostics (`planner-differential-at-07cd8692.txt`):

* **Opaque neighbour spends eligible fan-out.** `_traverse_seed` incremented `accepted_fanout` before the
  `opaque` skip. With `max_fanout=1` the higher-weighted deleted neighbour consumed the only slot; the
  visible sibling was never probed. Canonical candidates `[seed, deleted]`, admitted `[seed]`.
* **Opaque candidate spends the final candidate limit.** `search()` ranked by path score and truncated
  `ordered[:candidate_limit]`; with `candidate_limit=1` the deleted node (score 1.0) displaced the
  visible one (0.8).
* **Canonical refusal audit versus reported paths.** The deleted node never appeared in
  `graph_candidate_hits`, in any reported `path_refs`, or in `admitted`; its canonical refusal
  (`logical_memory_deleted`) was recorded. In the RED arms the reported traversal (`exclude`) still
  listed the visible sibling while the canonical traversal had dropped it: diagnostics and candidates
  disagreed. That incoherence is the clearest internal symptom of the defect.
* **Visible retrieval change, not information disclosure.** No withheld identifier reached any
  caller-facing field. The only observable is the absence of a visible sibling that depends on hidden
  state. By docs/44 (#809) the withholding applies only to a reader whose context could have read the
  deleted generation, so the reader could infer at most that a same-scope generation it was already
  eligible for has since been deleted. Low sensitivity; still a noninterference defect against the
  reviewer's proposed contract and against the retriever's own documented accounting ("the fanout
  counts usable NEW paths, not ineligible or stale edges").

Rejected / bounded by controls (both trees):

* **Cross-project neighbour**: eligibility is checked before fan-out accounting, so an other-project
  neighbour spends nothing; the visible sibling is admitted at every budget. No existence oracle.
* **Accessible higher-ranked sibling**: legitimately takes the slot; expected displacement.
* **Superseded, non-deleted version** (currentness): spends budget and is refused `superseded_not_current`.
  This is pre-existing, accepted design (admission owns currentness) and is unchanged by either repair.
* **Direct alternate path / sole deleted bridge / withheld seed**: unchanged from #836 A and B; the 47
  existing graph, replay and projection tests pass on all three trees.
* **Finite traversal work**: the eligibility-probe ceiling (`max_fanout * 16`) still bounds the scan.
  Recorded trade-off: more opaque neighbours than the ceiling, ranked ahead of a visible one, still hide
  it (test `test_probe_ceiling_still_bounds_the_work_and_records_the_trade_off`), the same trade-off
  #835 accepted for ineligible neighbours.

## 4. Actual public exposure and severity

* `ConfiguredCompositionRuntime` constructs `DeterministicMultiRouteRecallPlanner`; that planner has no
  typed-graph route (`routes_executed = lexical, exact_logical_identity, shared_evidence_neighbor`), and
  neither `ConfiguredCompositionRuntime.create/__init__` nor `AgentMemory.open` accepts a graph retriever
  or planner (`public-path-probe-at-2ad4cf23.txt`; pinned by `PublicPathBoundary` in the test module).
  `recall_control="shadow"` plans beside the executed recall and executes nothing.
* The only production constructor of `ControlledRecallPlanner` with a graph retriever is the
  retrieval-quality benchmark harness. The reachable surface is therefore the library-level controlled
  planner and the retriever itself.
* **Severity: Low.** Retrieval-completeness / noninterference defect on a non-default, library-level
  surface; no cross-scope disclosure; no supported public API path. Not an exploitable default public
  API defect. It does bear on v7 security sign-off of the controlled planner, because the amended
  candidate's own design (#836 B) makes withheld nodes confer no reachability while still letting them
  consume the reader's discovery budget.

## 5. Corrective commit and test receipts

* **Independent repair** (local `a055e0e`, `independent-repair-a055e0e.diff`), written before reading
  the owner's follow-up: no `accepted_fanout` for an opaque neighbour (probe still counted); visible
  candidates fill `candidate_limit` first, opaque ones take only remaining slots, selection re-sorted by
  the deterministic hit key. Preregistered tests GREEN; 47 existing graph/replay/projection tests OK;
  all 13 replay families PASS with **observation digests identical** to `07cd8692`
  (`replay-digests-three-trees.txt`); full reference suite 3162 tests with the same 10 failures + 1 error
  count as the unmodified head in this environment (shallow clone / missing harvest fixture / Gauntlet).
* **Owner repair** (`2ad4cf23`, blob `9fa861c3`): behaviourally identical to `a055e0e`
  (`independent-a055e0e-vs-owner-9fa861c3.diff`: the two differ only in comments and in how the
  accessible-first selection is written). Verified independently on a clean worktree at `2ad4cf23`:
  preregistered tests 2/2 OK; this review's control module 12/12 OK; existing graph suites 47 OK;
  pin-guard, lane-import, #644 replay and #835 replay tests 67 OK; equivalence `TRANSITION` 21 blobs;
  all 13 replay families PASS on a **clean** tree with digests identical to `07cd8692` (the owner's own
  record was produced on a dirty tree with `BLOCKED` verdicts; this is the clean-tree confirmation);
  full reference suite 3161 tests with exactly the candidate's pre-existing 8 failures + 1 error and
  nothing new (`full-suite-comparison.txt`).
* **Negative controls** (`controls-module-at-07cd8692-negative-control.txt`): seven tests of the control
  module fail on the unmodified runtime for the predicted fan-out or slot reason and pass on both
  repairs; the controls (opaque hop never continued, raw traversal without the predicate unchanged,
  determinism, cross-project) pass on all trees. Removing either repair reintroduces the regression.
* **Performance** (`bench-hub400-three-trees.txt`, 400-neighbour hub, `max_fanout=8`, `limit=8`): no
  opaque neighbours, unchanged (~0.21 ms). With every second neighbour opaque, the unmodified code
  returned 4 visible of 8 in 0.22 ms; the independent repair returns 8 of 8 in 0.26 ms; the owner's
  returns 8 of 8 in 0.39 ms (it evaluates `opaque()` twice per ranked hit; a one-line memoisation,
  optional, no behaviour change). Completeness improves; cost is bounded by the unchanged probe ceiling.

## 6. Impact on #836's protected blobs, declaration, replay and benchmark qualification

* `recall_control.py` is a declared protected blob: any repair re-pins the declaration (owner did:
  `a78797cb -> 7de94f11`; the independent repair would give `6f862106`) and the two v7 lanes.
* Replays: no fixture or expectation change needed; all 13 families' observation digests are byte
  identical across `07cd8692`, `a055e0e` and `2ad4cf23`. `scope-safe-graph-discovery-v2` passes
  unchanged; its budgets do not reach the fan-out or slot boundary this defect needs.
* **Benchmark qualification dependency: found at the 15:40Z snapshot, closed by `5ed105d7`.** At the
  review snapshot (branch head `2ad4cf23`) the v7 lane evidence imported at `30c57237` (AMB 3 rows,
  LongMemEval 4 rows, executed at `79172267` / runtime `07cd8692`) recorded
  `execution-identity.declaration_blob = a78797cb` while both lanes pinned `7de94f11`;
  `scripts/import_amb_lane_evidence.py` refuses an import whose executed declaration blob differs from
  the lane pin, so that evidence was no longer revision-bound to the amended runtime, and this review
  reported the lanes as needing re-execution. **Update (check-in 16:33Z, verified against the branch):**
  commits `9d0ba703` and `5ed105d7` on the #836 branch re-executed both lanes on the repaired tree and
  moved the `79172267` rows aside; at `5ed105d7` the protected tree and declaration are unchanged from
  `2ad4cf23` (`recall_control.py` `9fa861c3`, declaration `7de94f11`), all 7 lane evidence rows record
  `declaration_blob = 7de94f11` (AMB rows at `9d0ba703`, LongMemEval rows at `2ad4cf23`/`9d0ba703`),
  `checks/import-verification.txt` is VERIFIED 7/7 with `failures: 0`, and the lane freeze-guard and
  importer tests (15) pass. The owner reports the two LongMemEval `mem0_explicit` comparator rows and
  the public Gauntlet probe as still pending; this review did not execute any lane itself.
* Unaffected: PAMA and baseline authority; frozen `3edbb9ad` / `1c0e5531` trees; v1-v6 records;
  accepted gold, fixtures and -v1 replay evidence; the #777 audit pin (`GraphProjection` unchanged).

## 7. Recommendation

**CHANGES REQUIRED, satisfied in code by `2ad4cf23`; the lane re-binding this review flagged at
15:40Z was closed by `5ed105d7` (verified at the 16:33Z check-in).** The reviewer's hypothesis is
confirmed and correctly repaired on the #836 branch; this review's independent repair converged on the
same mechanism and the owner's repair passes every independent receipt here. For the opaque-budget
question nothing further is required of the runtime. Still outstanding for v7 per the owner's own
record, outside this review's scope: the two LongMemEval `mem0_explicit` comparator rows, the public
Gauntlet probe, the `1.8.0` contract decision and the owner's security sign-off. The probe-ceiling
completeness trade-off is the one accepted bounded-work trade-off and is now pinned by a test rather
than implied. No v7 acceptance is claimed or implied by this review.
