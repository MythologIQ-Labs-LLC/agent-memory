# Plan: Runtime Baseline v6 evidence — `-v6` lanes, `mesa-formal-v3` (extractor off), B1/B2

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**owning issue**: #732 (remediation plan `docs/plan-732-remediation.md`, Gate PASS Entry #116; implementation Entry #118, merged at #741 `e98e6e7`)
**declared transition**: v5 → v6 (`reports/runtime/baseline-v6-declaration.json`; acceptance evidence: the public Gauntlet probe, `amb-precisionmembench-retrieval-v6`, `longmemeval-s-retrieval-parity-v6` and replay `mesa-formal-v3`)
**precedent**: `docs/plan-671-evidence-v5.md` (E1–E9), whose machinery is reused unchanged unless stated
**iteration**: 2

**Gate history**: attempt 1 was a VETO on one blocking finding, K1: the re-pin list was incomplete, the same gap as v5's B3. Iteration 2 adds V6-E8 and folds in advisories L1–L6.

## Purpose

v6 adds typed write-time propositions and an opt-in extractor. The extractor is **off** by default, and nothing in the lanes or MESA declares a typed proposition. So with the extractor off, v6 must be **observationally identical** to v5 on every same-harness workload.

The only differences allowed are version identity strings:
- ranking policy 3.4.0;
- assertion filter 6.1.0;
- contract 1.6.0.

This plan freezes that claim before any score and publishes v6 through docs/67, with the typed and extractor path marked **unaccepted** (remediation advisory V1).

## Decisions

**V6-E1 — The `-v6` rule is equality, not attribution.**
- **LongMemEval** (agent_memory, budget 50, both planes): every question's `ranked_top` and `metrics` equal the accepted `-v5` control.
- **AMB** (agent-memory): every case's `correct`, `context` and the nine `meta` fields equal the accepted `-v5` control.
- **Cross-fact records.** These are the existing E2 records: LongMemEval `cross_fact` and the AMB `cross-fact.jsonl` sidecar. They must equal `-v5` in `limited_count`, `limited_item_ids`/`limited_document_ids` and `refusal_counts`, with `-v5`'s 0 limited carried over.
- **The attribution script.** `scripts/check_cross_fact_attribution.py` is reused unchanged, with its `--v4-dir` set to the `-v5` lanes and its `--v5-dir` set to the `-v6` lanes. The actual directories are recorded, because the script labels its summary "v4/v5".
- **The acceptance test enforces more than the script (L1).** The script exits 0 on ATTRIBUTED and never compares cross-fact records, so the test asserts:
  - `verdict_counts == {"EQUAL": 1000}` for LongMemEval;
  - `verdict_counts == {"EQUAL": 77}` for AMB;
  - per-row equality of the cross-fact records with `-v5`.

  Anything else blocks v6 publication. This is stricter than v5 because no mechanism is expected to act.
- **Reported, never gated:** up/down counts and summary deltas, which must be zero.

**V6-E2 — Other `-v6` rows.**
- **Re-executed:** lexical overlap, BM25 and Mem0. Lexical and BM25 must equal `-v5` exactly. A Mem0 difference is an environment finding, as at `-v4` and `-v5`.
- **Deferred rows:** the shadow and semantic rows stay `deferred`. Their reasons gain one sentence: "ranking policy 3.4.0 and assertion filter 6.1.0 add only typed-basis branches that no lane input reaches; the next measurement belongs to #673's lanes".
- **Scorecards:** all 9 `-v6` sources are appended to `SOURCES` (append-only), and `evidence_history` grows.

**V6-E3 — Lane-file differences from `-v5`, exhaustive and tested field for field.** These follow plan-671-evidence-v5 E4, with `-v5` read as `-v4` and `-v6` as `-v5`:
- **Top level:** `lane_id`, `status`, `frozen_on`, `owning_issue: 732`, `description`, `freeze_rationale` and `comparability.notes`.
- **Findings:** the `-v5` acceptance finding is not carried forward.
- **Rows:**
  - executed rows are `frozen`;
  - deferred reasons follow V6-E2;
  - the control's `display_name` names the declared v6 transition.
- **`runtime_baseline_posture`:** predecessor v5, `declared_successor` v6, the declaration path and blob.
- **`comparability.not_comparable_to[0]`:** describes the `-v5` relation as **equality** (V6-E1).
- **Spelled out (L2).**
  - **Changes:** LongMemEval `execution.environment.dispatch_unit`, which names the lane id, becomes the `-v6` lane.
  - **Carried over unchanged:**
    - the LongMemEval runner blob (`6b9c2373…`, unchanged since `-v5`);
    - the AMB bridge blob (`3d9ccb31…`) and version 0.4.0;
    - every `execution_identity_requirements` and `artifact_requirements` line;
    - every `adapter.revision_rule`.

  v5 E4's line edits are **not** re-applied. A field-by-field test asserts that exactly the listed paths differ from `-v5`.
- **Workflows:** the `lane_id` choice gains the `-v6` id and makes it the default. The AMB cross-fact sidecar env var is unchanged.

**V6-E4 — `mesa-formal-v3`: a successor freeze, extractor off.**
- **The freeze.** `reference/fixtures/benchmarks/agentmembench/mesa-formal-v3-freeze.json` is a new file; v2 is never edited. Relative to v2, these fields change, and they are listed and tested exhaustively:
  - `freeze_id`: `agent-memory-agentmembench-mesa-formal-v3`;
  - `owning_issue`: 732;
  - `supersedes`: `{freeze_id, path, sha256}` of v2;
  - `frozen_on` and `status`;
  - `run_id`: `agent_memory_formal_v3_s2027_9170`;
  - `adapter.surface`: "contract 1.6.0";
  - `adapter.ranking_policy`: "runtime default (multi-route-default 3.4.0 at freeze time); no variant; no proposition extractor";
  - `agent_memory.runtime_tree`: the `reference/agentmem_ref` tree at the freeze PR's base;
  - `agent_memory.ranking_policy_version` `3.4.0` and `public_contract_version` `1.6.0`;
  - `runner.sha256`: unchanged if the runner is unchanged;
  - `predictions`: V6-E5.

  Everything else is copied unchanged, including D1–D6, the upstream pins, arguments, phases, judge identity, stop lines and classifier version.
- **Environment (L3).** The Python 3.11 and package pins are copied too, and the replay runs in the same environment as v2. Any environment drift found before the score is recorded as a pre-score amendment.
- **Misses (L4).** v3's `on_miss` states explicitly that a miss on any of P1–P3 or P5, or any P6 difference, blocks.
- **The runner.** `reference/run_agentmembench_formal.py` already takes `--freeze`, and no runner change is expected. If one is needed, its source-hash pins follow v5 E5, and the change is listed as an amendment before any score.

**V6-E5 — MESA confirmation (frozen in the v3 freeze before the replay).** v3 must reproduce v2 exactly:
- **P1:** `outcomes == {"new_fact": 250}`, and the upstream `dual_version_rate == 0.0`;
- **P2:** `win_basis_counts == {"currentness_mechanism": 250}`;
- **P3:** `primary_stage_counts == {}` and `unmet_stage_counts == {}`;
- **P4:** no pair fails a guard. Any pair that does is listed with its guard, using the C7 report shape over the replay's own M4 traces;
- **P5:** `upstream_consistency.consistent == true`;
- **P6:** M1 retrieval digests and the isolation, deletion, concurrency and scale non-latency fields all equal v2. Latency is reported only.

Missing any of P1–P3 or P5, or any P6 difference, blocks v6 publication. Nothing is tuned; a remedy would be a new plan.

The extractor-on MESA run is **not** part of this plan. It belongs to remediation R6, after the provider-freeze record.

**V6-E6 — Guards at the execution revision.**
- #584 M1–M15 and the #580 frozen labels are unchanged; the existing tests are re-run.
- The C7 ordering-difference report is regenerated with 0 blockers and M4 250/250 limited.

**V6-E7 — Sequencing.** Nothing writes into `reference/agentmem_ref` between the freeze and the replay.
1. **MESA PR:** the v3 freeze, the E8-style re-pins (the formal-runner test binds the v2 freeze to its historical record) and this plan's acceptance skeleton. It never touches `reference/agentmem_ref`.
2. **Replay** at the MESA PR's merge commit. Output: `reports/benchmarks/agentmembench-mesa-formal/agent_memory_formal_v3_s2027_9170.json`.
   **Order constraint (L6).** The replay must run before the lanes PR merges, because the v3 `runtime_tree` covers `reference/agentmem_ref/evaluation/lanes/`.
3. **Lanes PR:** the V6-E3 lane files, the workflows and the re-pins (`test_same_harness_lanes_v5.py` reads its committed evidence; the default `lane_id` regex is widened).
4. **Dispatch.**
   - LongMemEval: `agent_memory`, `lexical_overlap` and `mem0_explicit` on both planes (6 runs).
   - AMB: `agent-memory`, `bm25` and `mem0-explicit` (3 runs).
   - Imports go through the existing importers. A re-dispatch is allowed only for an infrastructure failure before any score.
5. **Acceptance,** in one ledger entry: V6-E1 (all EQUAL), V6-E2, V6-E3, V6-E5 and V6-E6.
6. **docs/67 Step B1 for v6:**
   - the record, boundary, qualification and `.md`;
   - the Gauntlet manifest and stdio adapter (`PUBLIC_CONTRACT_VERSION` 1.6.0);
   - the register entry;
   - the CONTRIBUTOR_ARCHITECTURE ranking text (3.3.0 → 3.4.0, including `:243`);
   - the C7 report docstring's version text (L5).

   The v6 record, `.md` and dashboard state that **the typed proposition and extractor path is unaccepted** until the remediation R6 acceptance PR. If acceptance fails, the next attempt needs a v7 declaration.
7. **Step B2** binds the probe from the `runtime-baseline.yml` run on the B1 PR head.

**V6-E8 — Re-pins, listed per PR before implementation (K1).** A listed test that goes stale is updated, never deleted. The `-v5` lanes and the v2 freeze are never edited.
- **MESA PR:** `reference/tests/test_agentmembench_formal.py`. The current-runtime binding moves to the **v3** freeze, and v2 binds to its historical record (`reports/runtime/baseline-v5.json`), as v1 did at the v3 transition.
- **Lanes PR:**
  - `test_same_harness_lanes_v5.py:217` (2 tests): the default-lane assertion tolerates the later `-v6` default;
  - `test_same_harness_lane.py:233-241`: the hard-coded lane-id list gains the two `-v6` ids, and the frozen-status rule allows `-v6`;
  - `test_same_harness_lanes_v3.py:172` (2 tests): the default regex `-v[345]` becomes `-v[3456]`;
  - `test_same_harness_lanes_v4.py:138` (2 tests): the default regex `-v[45]` becomes `-v[456]`;
  - a new `test_same_harness_lanes_v6.py` covering V6-E1/E3 and the L1 acceptance assertions.
- **B1 PR:**
  - `test_runtime_baseline_succession.py:722-797`: the v5 current-entry test becomes historical, a v6 current-entry test is added, and the `[-1]` rendering and record checks move to v6;
  - the Gauntlet adapter and contestant assertions for the v6 manifest and stdio adapter (contract 1.6.0).
- **B2 PR:** the v6 qualification binding (workflow run, `verified_head`, `published_commit`) in the same succession tests.
- **Catch-all:** any other failing test found during implementation is listed as an amendment, with its reason, **before** it is changed. No test is deleted, skipped or weakened.

## Boundaries
- **Non-goals:**
  - any runtime change;
  - the extractor-on MESA run;
  - holdout work;
  - provider configuration;
  - #673.
- **Exclusions:**
  - no `-v5` lane is edited;
  - no v2 freeze is edited;
  - nothing is re-scored after any result.

## Open Questions
None.

## Gate result

The plan passed at attempt 2 (META_LEDGER Entry #119; audit sha256 `0e4546c6…`). Two advisories are binding:
- **N1:** P4's guard identity cannot be computed from the replay's own traces, because the frozen runner's ranking digest omits the cross-fact fields. It is taken instead from the C7 report regenerated at the execution revision, as at v2.
- **N2:** in P6, "M1 retrieval digests" means the per-item `retrieved` sha256 digests. The trace digests carry `policy_version` and so differ by construction.

## Results (accepted 2026-10-08, META_LEDGER Entry #120)

**MESA (V6-E5).** `mesa-formal-v3` was executed at `d7b2974` with the extractor off (`reports/benchmarks/agentmembench-mesa-formal/agent_memory_formal_v3_s2027_9170.json`). It reproduces v2:
- **P1:** `outcomes {"new_fact": 250}`, upstream `dual_version_rate` 0.0;
- **P2:** `win_basis_counts {"currentness_mechanism": 250}`;
- **P3:** no primary or unmet stage;
- **P4:** no pair fails a guard; the guard identity is taken from the regenerated C7 report (N1);
- **P5:** upstream consistent;
- **P6:** every other phase's non-latency fields and the M1 per-item `retrieved` digests equal v2 (N2).

**Lanes (V6-E1), nine runs on `24048d5`.** The attribution script ran unchanged with `--v4-dir` set to the `-v5` lane evidence directories and `--v5-dir` set to the `-v6` ones.
- LongMemEval (runs 37718255173, 37718257278, 37718259916, 37718262620, 37718265216, 37718267521): `verdict_counts {EQUAL: 1000}` across both planes.
- AMB (runs 37718270129, 37718272612, 37718275682): `verdict_counts {EQUAL: 77}`.
- The cross-fact records (LongMemEval `cross_fact`, AMB `cross-fact.jsonl`) equal `-v5` row by row, with 0 limited carried over.

**Comparators (V6-E2).**
- Lexical overlap and BM25 equal `-v5` exactly.
- Mem0 equals `-v5` on every LongMemEval row's `ranked_top` and `metrics` (500 per plane) and on every AMB case's `query_id`, `correct` and `context`. Unlike `-v5` (45 turn-row near-tie reorders), no reorder was observed.
- All 9 `-v6` sources are appended to the scorecard `SOURCES`, and `evidence_history` grows by the `-v6` entries.

**Guards (V6-E6).** The C7 report, regenerated at the execution revision (`reports/runtime/cross-fact-currentness-671/ordering-difference-report-v6.json`), has assertion filter 6.1.0, ranking 3.4.0 on and 3.2.0 off, 0 blockers, M4 250/250 limited, top-1 new 50 off → 250 on, no refusals, #580 pre-registered units only and 0 admitted #584 order changes. It is identical in structure and counts to the v5 report. The guard tests (`test_temporal_currentness_gauntlet`, `test_temporal_unknown_basis_ordering_contract`, `test_cross_fact_currentness`, `test_typed_propositions`) pass.

**Interpretation.**
- With the extractor off, v6 is observationally identical to v5 on every same-harness workload, as frozen.
- The typed proposition and extractor path is **unaccepted** until the remediation R6 acceptance (`docs/plan-732-remediation.md`, advisory V1). These results do not measure it.
- Next: docs/67 Step B1 and B2 for v6 (V6-E7 steps 6–7).
