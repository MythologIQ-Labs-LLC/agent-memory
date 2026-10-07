# Plan: #671 C9 evidence — `-v5` same-harness lanes and the `mesa-formal-v2` replay for Runtime Baseline v5

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**parent plan**: docs/plan-671-cross-fact-currentness.md. Gate PASS at attempt 7 (Entry #100); implementation is Entry #104 (PR #726). This plan is the parent's C9, which pre-registered its shape. Amendments to the parent and to docs/69 are listed in E9.
**precedent**: docs/plan-644-lanes-v4.md (L1–L9); docs/plan-669-lanes-v3.md (IA1, IA2); docs/69 (formal MESA protocol, "Determinism"); the mesa-formal-v1 freeze
**owner rulings in force**: `decision-671-currentness-mechanism` (Option A now, Option D next, never D inside A); `decision-671-same-source`; `decision-eval-credential`
**doctrine**: benchmark score != truth; a higher score without attribution is not acceptance; no tuning after any score
**iteration**: 2 (Gate Tribunal PASS at attempt 2, META_LEDGER Entry #105; advisories folded below)

Gate history:
- **Attempt 1, VETO, four findings.** The prediction was confirmed by execution: the frozen classifier on this branch's runtime gave `new_fact` 250 and `currentness_mechanism` 250, and M1/M3/M5/M6 were equal to v1.
  - **B1:** the `mesa-formal-v2` runtime-tree binding can never be met. The `-v5` lane files and the imports live inside the bound `reference/agentmem_ref` tree, and the plan ran the replay after them.
  - **B2:** the runner change was under-specified. `PROFILE_ID`, the report's freeze binding, the judge's binding check and `main()` all hard-code v1. The claim that v1 is reproducible byte for byte was false. Copying v1 field for field carried false text forward (contract 1.4.0, policy 3.1.2, issue 694), and the plan said deviations D1–D3 where v1 has D1–D6. docs/69 was not amended.
  - **B3:** no re-pin list, and 10 tests would fail.
  - **B4:** the E4 difference list was incomplete:
    - the `-v4` runner blob appears 6 times in the LongMemEval lane;
    - the semantic-row reason states policy 3.2.0;
    - two AMB `-v4` lines contradict `-v5` and must be replaced, not appended to.

- **Attempt 2, PASS with advisories.** The tribunal verified the remedies by execution:
  - **AMB attribution is computable.** The frozen renderer, `modes/retrieval.py:50-54` (blob `416dd4df`), rebuilds all 77 `-v4` contexts byte for byte from ordered document ids.
  - **The off recompute is sound.** The facade reads `MULTI_ROUTE_RANKING_POLICY` at call time, the live policy is restored afterwards, and a later recall is identical whether or not an off recall preceded it.
  - **The MESA PR stays outside `reference/agentmem_ref`**, and the runner's checks pass there.
  - **E8 is complete except for one test:** 11 failures are simulated, 10 of them listed.

  Advisories A1–A8 are folded into "Advisories folded at attempt 2" below. Where that section and an E-clause differ, the section governs.
  Iteration 2 resequences execution (E7), specifies the runner change completely (E5), adds the re-pin list (E8) and a corrected E4, and folds in advisories A1–A11. A1 makes attribution causal, not co-occurrence (E1, E2).

## Purpose

`reports/runtime/baseline-v5-declaration.json` requires three pieces of acceptance evidence:
- the public Gauntlet probe;
- the lanes `longmemeval-s-retrieval-parity-v5` and `amb-precisionmembench-retrieval-v5`;
- the replay `mesa-formal-v2`.

v5 changes ranking policy 3.2.0 → 3.3.0 and nothing else at the identity level. The only behavioural change is the guarded cross-fact applicability label under explicit-current recall.

The evidence has to show two things:
- **(a) Causation.** Every ranked-output change against v4 is caused by the cross-fact mechanism.
- **(b) The pre-registered MESA M4 confirmation**, scored by the frozen classifier.

## Decisions

**E1 — The `-v5` control rows: a causal attribution rule, not equality.**
- **The rows.**
  - LongMemEval: `agent_memory`, budget 50, both planes.
  - AMB: `agent-memory`, the case budget.
  - Both run the v5 runtime with the facade default.
- **Rule (blocking), per question (LongMemEval) or non-blank case (AMB), against the accepted `-v4` control of the same lane:**
  - **(i)** if the `-v5` output equals `-v4` on the L1 fields of plan-644-lanes-v4 (LongMemEval: `ranked_top`, `metrics`; AMB: the 77-case field list), it passes;
  - **(ii)** otherwise it must carry `cross_fact.limited_count > 0`, **and** its mechanism-off recompute (E2) must reproduce `-v4`:
    - LongMemEval: `ranked_top_mechanism_off` equals the `-v4` `ranked_top`;
    - AMB: `returned_document_ids_mechanism_off` equals the `-v4` sidecar-free document order. The `-v4` case `context` is the ordered rendered retrieval, and the off ids rendered with the frozen harness renderer must reproduce it byte for byte. The attribution script performs that rendering.

  So the only difference from `-v4` is the mechanism. Any other difference **blocks** v5 publication.
- **Blank-query AMB cases** (four of them) run no recall and must equal `-v4`.
- **Questions with a runtime error** (`row.error` non-null) carry no `cross_fact` record. They must have equal `ranked_top` (empty) and equal metrics to `-v4`. Otherwise they block.
- **Reported, never gated:**
  - up/down counts;
  - the knowledge-update slice;
  - `latest_gold_ranked_first`;
  - the AMB summary deltas.
- **Expected effect (recorded before any score).** The mechanism needs explicit-current intent plus an open proposal between two admitted facts that pass G1–G13. LongMemEval and AMB declare no intent and are rarely phrased as first-party change sentences, so the expected number of changed questions is **small, possibly zero**. Zero satisfies the rule.

**E2 — Harness fields that make causation checkable.** These are harness-only. No runtime file changes, and they are recorded before any score.
- **Mechanism off.** It is defined exactly as in `reference/run_cross_fact_currentness_report.py`: ranking policy 3.2.0 (`ExplicitCurrentConstrainedRankingPolicy` built from the live policy's own fields, version excluded), substituted for `runtime_composition.MULTI_ROUTE_RANKING_POLICY` for the duration of one recall. It ignores cross-fact evidence.
  - It is computed only when the mechanism-on recall has `limited_count > 0`. Otherwise off equals on by C3 off-equivalence, which the parent's tests pin.
  - The extra recall is a read. A test pins that a question's on-output is identical whether or not an off recall preceded it, on a fixture with a limited pair.
- **`reference/run_longmemeval.py`** (`agent_memory` backend). Each question row records `cross_fact`:
  - `limited_count`;
  - `limited_item_ids`, in rank order;
  - `refusal_counts`, a count per `cross_fact_refusal_reason`;
  - `ranked_top_mechanism_off`: `null` when `limited_count == 0`.

  The report records `cross_fact_summary`: the questions with `limited_count > 0`, the total limited, and aggregated refusals. The values are read from the facade's `ranking_evidence` only.
- **`reference/amb_agent_memory_bridge.py`** (`BRIDGE_VERSION` 0.4.0).
  - **The `agent-memory` provider.** When `AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR` is set, it writes `cross-fact.jsonl` with one record per `retrieve()` call:

    `{call_index, scope, query_sha256, budget, limited_count, limited_document_ids, refusal_counts, returned_document_ids, returned_document_ids_mechanism_off}`

    The last field is `null` when `limited_count == 0`.

    When the variable is unset, `agent-memory` retrieves normally and writes nothing. This keeps the `-v1` to `-v4` lane behaviour and the other bridge tests valid. The `-v5` workflow always sets it for that row, and the importer refuses a `-v5` control artifact without it.
  - **The `agent-memory-shadow` provider** keeps its `-v4` behaviour (L9 sidecar, refusal when unset) and never writes the cross-fact sidecar: its `retrieve` passes `cross_fact=False` to the shared writer. A test pins both providers' sidecar behaviour.
  - **Join rules** follow L9:
    - concurrency 1;
    - `call_index` contiguous from 0;
    - the adjacent-duplicate key is `(scope, query_sha256)`;
    - blank-query cases have no record, and are recognised by `retrieved_count == 0`, `resolution == {}` and an empty `context`.
- **Importers.**
  - `import_longmemeval_lane_evidence.py` refuses a `-v5` `agent_memory` run where any error-free question lacks `cross_fact`, or a non-`agent_memory` row carrying it.
  - `import_amb_lane_evidence.py` copies and hashes `cross-fact.jsonl`. On the `-v5` `agent-memory` row it requires the sidecar and joins it per case, as for L9. On any other `-v5` row it refuses one.
- **`scripts/check_cross_fact_attribution.py`** (new) applies the E1 rule to the accepted `-v4` evidence and the imported `-v5` evidence of one lane. Per question or case it prints `EQUAL`, `ATTRIBUTED` or `UNATTRIBUTED`. Any `UNATTRIBUTED` result exits 1.

**E3 — The other `-v5` rows.**
- **Lexical overlap, BM25 and Mem0** are re-executed. Lexical and BM25 must equal `-v4` exactly. Mem0 is expected to equal `-v4`; a difference is an environment finding, as Mem0 turn's four L1 ranked diffs were at `-v4`.
- **The `-v4` shadow rows** become `deferred`, with the reason: "measured at `-v4` (jh-14 shipped); the next controller measurement belongs to T-controller-2's lanes".
- **Semantic rows** become or stay `deferred`, with a **rewritten** reason.
  - LongMemEval: "the semantic route is unchanged since `-v3`, where its ordering effect was measured (plan-669-lanes-v3 D2); ranking policy 3.3.0 adds only explicit-current cross-fact applicability, which never reads similarity; the next measurement belongs to #673's lanes".
  - AMB: the `-v4` uv.lock reason, unchanged, because it states no policy version.
- **Scorecards.** All 9 `-v5` evidence sources (6 LongMemEval, 3 AMB) are **appended** to `SOURCES` in `scripts/build_benchmark_scorecards.py`; the list only grows. The `-v5` control becomes the current Agent Memory row by the builder's existing latest-lane rule, comparators keep IA2, and no shadow row is added. `evidence_history` gains the `-v5` entries.

**E4 — Lane-file differences from `-v4`, exhaustive (tested field for field).**
- **Top level:** `lane_id`, `status: "frozen"`, `frozen_on`, `owning_issue: 671`, `description`, `freeze_rationale`, `comparability.notes`.
- **`findings`:** the `-v4` acceptance finding is not carried forward (IA1). All other findings are unchanged.
- **Rows:**
  - executed rows become `frozen`, with `status_reason` removed;
  - shadow rows become `deferred` with the E3 reason;
  - the semantic rows take the E3 reasons;
  - the control's `display_name` names the declared transition to Runtime Baseline v5.
- **`runtime_baseline_posture`** in every Agent Memory row (control, shadow, semantic) is replaced as a whole: predecessor v4, `declared_successor` v5, the declaration path, and the declaration blob.
- **`comparability.not_comparable_to[0]`** describes the `-v4` relation as causally attributed (E1), not equality.
- **LongMemEval:**
  - **every** occurrence of the `-v4` runner blob string is replaced by the `-v5` runner blob, with no exceptions:
    - `harness.source_blobs`;
    - `evaluator.scorer`;
    - `systems/lexical_overlap/source/revision`;
    - every row's `adapter.revision_rule`, including the shadow and semantic rows;
    - any other occurrence.

    The test asserts the `-v4` blob string is absent from the serialised `-v5` lane.
  - `execution.environment.dispatch_unit`: the `-v5` lane, backends `{agent_memory, lexical_overlap, mem0_explicit}`;
  - `execution.execution_identity_requirements`:
    - the `-v4` shadow lines are **removed**;
    - one line is **added**: "every error-free `agent_memory` question carries a `cross_fact` record; no other row carries one".
- **AMB:**
  - every occurrence of the `-v4` bridge blob and `bridge_version 0.3.0` is replaced by the 0.4.0 blob and version; the test asserts the old blob is absent;
  - `execution.artifact_requirements`: the `-v4` `recall-control.jsonl` line, which says "written by bridge 0.3.0", is **replaced** by "`cross-fact.jsonl`, written by bridge 0.4.0, on the `agent-memory` row only";
  - `execution.execution_identity_requirements`: the `-v4` sidecar line, which says "every other row's artifact carries no sidecar", is **replaced** by "the `agent-memory` row's artifact carries `cross-fact.jsonl` with exactly one joined record per non-blank-query case and none for a blank-query case; every other row's artifact carries neither sidecar".
- **Both:** the workflows' `lane_id` choice gains the `-v5` id and becomes the default. `amb-competitive.yml` sets `AGENT_MEMORY_AMB_CROSS_FACT_SIDECAR=$RUNNER_TEMP/amb-output/cross-fact.jsonl` for `agent-memory` only.

**E5 — `mesa-formal-v2`: a successor freeze and a fully specified runner change.**
- **The freeze.** `reference/fixtures/benchmarks/agentmembench/mesa-formal-v2-freeze.json` is a new file; v1 is never edited. Relative to v1, these fields are listed and tested exhaustively:
  - `freeze_id`: `agent-memory-agentmembench-mesa-formal-v2`;
  - `owning_issue`: 671;
  - `supersedes`: `{freeze_id, path, sha256}` of v1;
  - `frozen_on` and `status`;
  - `run_id`: `agent_memory_formal_v2_s2027_9170`;
  - `adapter.surface`: "contract 1.5.0";
  - `adapter.ranking_policy`: "runtime default (multi-route-default 3.3.0 at freeze time); no variant";
  - `agent_memory.runtime_tree`: the `reference/agentmem_ref` tree at the freeze PR's base, which is the merge of #726;
  - `agent_memory.ranking_policy_version` `3.3.0` and `public_contract_version` `1.5.0`;
  - `runner.sha256`: the new runner blob;
  - `predictions`: E6.

  Everything else is copied unchanged, including the deviations **D1–D6**, the upstream pins, arguments, phases, judge identity, stop lines and classifier version.
- **The runner** (`reference/run_agentmembench_formal.py`). Every v1 hard-coding becomes a property of the loaded freeze, and the runner gains `--freeze PATH` (default v1):
  - `PROFILE_ID` becomes `freeze["freeze_id"]`, through `load_freeze`;
  - the report's freeze binding (path and sha) uses the loaded path;
  - the judge's binding check compares against the path recorded in the raw report's binding, and refuses if that path is not a committed freeze or its sha differs;
  - `main()` threads `--freeze` through execution and judging;
  - `verify_self` compares against the loaded freeze's `runner.sha256`.
- **Not changed:** `classify_conflict_case`, `CURRENTNESS_STAGES`, `RELEVANCE_STAGES`, `RELEVANCE_STAGE_PREFIXES`, `CONTENT_TIE_STAGES`, `RECENCY_TIE_STAGES`, `STAGES`, `CLASSIFIER_VERSION`, the upstream verification, the adapter class and the report schema. A test pins the sha256 of `inspect.getsource(classify_conflict_case)` and of each tuple against their values at `7b041a7`.
- **v1 reproducibility (corrected).** v1 replays run at `7b041a7`, as docs/69 already states, and they continue to: the v1 freeze pins the old runner sha, so a v1 replay on the new runner is refused by design.
- **The `_DEMOTED` binding.** The classifier credits `temporal_applicability_tier` through `ranking_policy._DEMOTED`, which contains `limited_by_cross_fact_state_change`. That is the parent's C3 design, not a classifier change.
- **The judge (M2).** It stays unprovisioned (#706). D1 holds, and `recall_at_k` stays absent, as in v1. M4 needs no judge.
- **Upstream hygiene.** Before execution, the upstream checkout is re-verified pristine: ignored `__pycache__` is removed, and `verify_upstream` must pass.

**E6 — The MESA confirmation (frozen in the v2 freeze before the replay).**
- **Not blind.** The ordering-difference report and the attempt-1 audit already executed the conflict phase on this runtime, so E6 is a **confirmation** of a known result, not a blind prediction. It is frozen so that the replay cannot be re-interpreted.
- **Exact expected classifier dicts:**
  - **P1:** `outcomes == {"new_fact": 250}`, and the upstream `dual_version_rate == 0.0`;
  - **P2:** `win_basis_counts == {"currentness_mechanism": 250}`;
  - **P3:** `primary_stage_counts == {}` and `unmet_stage_counts == {}`;
  - **P4:** no pair fails a C2 guard. Any pair that does is listed with its guard by the C7 report shape, run over the replay's own M4 traces;
  - **P5:** `upstream_consistency.consistent == true`;
  - **P6:** M1 retrieval digests, and the isolation, deletion, concurrency and scale non-latency fields, all equal v1. Latency is reported only.
- **Span note.** v1 executed at Runtime Baseline v2 (3.1.2, contract 1.4.0), so P6 deltas span v3–v5. The attempt-1 audit found none.
- **Outcomes.**
  - Missing **P1–P3** or **P5** is a finding. v5 is not published on that evidence, and nothing is tuned; any remedy is a new plan.
  - A **P6** difference is recorded and attributed, and it blocks only if it is unattributed.

**E7 — Sequencing (resolves attempt-1 B1). Nothing writes into `reference/agentmem_ref` between the freeze and the replay.**
1. **#726 merges** (the v5 runtime, declared).
2. **The MESA PR**: the E5 runner change, the v2 freeze, the E8 MESA re-pins, and this plan's acceptance record skeleton. It touches only `reference/run_agentmembench_formal.py`, `reference/fixtures/benchmarks/agentmembench/`, `reference/tests/` and `docs/`, never `reference/agentmem_ref`.
   - The freeze's `runtime_tree` is the `reference/agentmem_ref` tree at the PR's base.
   - If `main` changes that tree before the PR merges, the freeze is re-cut against the new base before any score, and that is recorded.
3. **The replay** runs at the MESA PR's merge commit, whose `reference/agentmem_ref` tree equals the freeze. The runner verifies this.
   - Output: `reports/benchmarks/agentmembench-mesa-formal/agent_memory_formal_v2_s2027_9170.json`, committed and linked-only; the raw report is uncommitted.
   - Its import commit (any integration record under `reference/agentmem_ref/evaluation`) comes after the replay. Regeneration then runs at that merge commit, exactly as v1 runs at `7b041a7`.
4. **The lanes PR**: the E2 harness, the E4 lane files, workflows, importers and the E8 lane re-pins.
5. **Dispatch.**
   - LongMemEval: `agent_memory`, `lexical_overlap` and `mem0_explicit` on both planes (6 runs).
   - AMB: `agent-memory`, `bm25` and `mem0-explicit` (3 runs).
   - Import through `amb-evidence-import.yml`. A re-dispatch is allowed only for an infrastructure failure before any score, with identical inputs.
6. **Acceptance**, in one ledger entry:
   - E1 through `check_cross_fact_attribution.py`, for both lanes;
   - E3 and E4;
   - E6;
   - the #584 M1–M15 and #580 guardrail results at the execution revision (the parent's tests, plus the C7 report regenerated with zero blockers).

   The deficits ledger entry `mesa-m4-currentness` (ADR-043) gains its closure transition: status `closed`, `closed_by` the v2 report and this entry, and its prior state retained in history.
7. **docs/67 Step B1 for v5:**
   - the record, boundary, qualification and `.md`;
   - the Gauntlet manifest and adapter (`PUBLIC_CONTRACT_VERSION` 1.5.0);
   - the register entry, with the predecessor block copied from the declaration;
   - the CONTRIBUTOR_ARCHITECTURE ranking text (3.2.0 → 3.3.0) and its `read_semantics` currentness text.

   The closeout consumers (`harvest-closeout-final-v4`, `run_rc1_evidence_closeout.py`) do **not** move: no closeout row changes at v5.
8. **Step B2** binds the probe artifact. #671 closes. #673 is re-planned after that.

**E8 — Re-pins, listed before implementation (attempt-1 B3).** A listed test becomes stale and is updated, never deleted. The `-v4` lanes are never edited.
- **`reference/tests/test_same_harness_lanes_v4.py`:**
  - at `:167`, the `-v4` runner-blob pin and, at `:208-210`, the bridge blob and `0.3.0` are compared against the committed `-v4` evidence records, not HEAD, following the `test_same_harness_lane.py:376-387` pattern;
  - at `:137`, the workflow `lane_id` default assertion tolerates the later `-v5` default, as the `-v3` test did for `-v4`.
- **`reference/tests/test_same_harness_lanes_v3.py:172`:** the default regex `-v[34]` becomes `-v[345]`.
- **`reference/tests/test_same_harness_lane.py:606`** and **`reference/tests/test_amb_agent_memory_bridge.py:90-91`:** the live `BRIDGE_VERSION` becomes `0.4.0`. The frozen `bridge_version` text in the `-v1` to `-v4` lanes stays.
- **`reference/tests/test_agentmembench_formal.py:274-276`:** `test_runner_digest_matches_freeze` asserts the current runner against the **v2** freeze, and the v1 freeze's runner sha against `git rev-parse 7b041a7:reference/run_agentmembench_formal.py`'s blob sha256. The v1 assertions on D1–D6 and the historical binding stay.
- Any other failing test found during implementation is listed as an implementation amendment, with its reason, before it is changed.

**E9 — Amendments recorded.**
- **The parent plan's C9** said "runner and classifier unchanged, with the same sha256". The runner's sha changes (E5), and the classifier is pinned unchanged by source hash.
- **docs/69's replay statement** ("the same frozen runner, unchanged") gains a v2 section stating the following:
  - the `--freeze` runner;
  - the v2 freeze;
  - the execution revision;
  - that v1 replays remain at `7b041a7`.

## Advisories folded at attempt 2 (binding)

- **A1 (E8).** Add `reference/tests/test_same_harness_lane.py:222-239`. It hard-codes the lane ids and lets only `-v4` lanes be `frozen`. It gains the two `-v5` lane ids, and `frozen` is allowed for `-v5` (`-v4` is now `accepted`).
- **A2 (E7 step 6).** The deficit closure follows `schemas/benchmark-deficit-ledger.schema.json`. The schema allows no extra fields, so the closure sets exactly:
  - `state: "frontier"`, or `improved_not_frontier` if the accepted evidence does not reach the upstream frontier;
  - `closed_at`;
  - `closure_evidence`, citing the v2 report and the acceptance ledger entry;
  - `remaining_gap: 0`.

  It adds no `status`, `closed_by` or history field.
- **A3 (E8).** Shallow CI checkouts cannot read `7b041a7`. The v1 runner sha256 (`58b2fced…`), the classifier-source sha256 and the tuple sha256s are therefore hard-coded in the test, after being verified once against `git show 7b041a7:reference/run_agentmembench_formal.py`.
- **A4 (E2).** The off recall:
  - runs inside the single `mechanism()` context manager, which restores the policy on error;
  - runs after the on recall and outside any timed span;
  - writes one journal row and one governance row to the benchmark store, which changes no ranking.

  The no-effect test uses the AMB durable-store pattern, with a later recall on a different query.
- **A5 (E1).** The AMB renderer is `modes/retrieval.py:50-54` at `03c1d0f` (blob `416dd4df`). The content source is the `-v4` case contexts. The same ordered documents give the same per-case score fields.
- **A6 (E8).** The `-v4` evidence records carry the bridge blob, not the version string. The re-pin at `test_same_harness_lanes_v4.py:208-210` therefore checks the blob against the evidence records, and `bridge_version 0.3.0` against the `-v4` lane's own `revision_rule`.
- **A7 (wording).**
  - **E4, LongMemEval:** of the configuration identity line, only the `agent_memory_shadow` clause is dropped; the control's `recall_control: off` clause stays.
  - **E4, AMB:** the AMB semantic row has no `runtime_baseline_posture`, so none is replaced.
  - **E5:** `runner.sha256` is the file's sha256, not a git blob id.
- **A8 (E6 P4).** Guard verdicts come only from the C7 report regenerated at acceptance, because the frozen trace digest drops cross-fact fields. P1–P3 imply P4.

## Boundaries

- **non_goals:**
  - Option D;
  - any runtime change (`reference/agentmem_ref` is frozen at #726 for E7 steps 2–3);
  - semantic default-on;
  - controller enforcement;
  - judge provisioning (#706).
- **exclusions:**
  - no change to the upstream harness, dataset, arguments or classifier logic;
  - no gold-aware transformation;
  - no temporal enrichment;
  - no budget change;
  - no tuning after any score;
  - no edit to `-v4` lanes, the v1 freeze or v4 records.

## Open Questions

None.
