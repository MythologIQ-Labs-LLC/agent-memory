# Plan: #640 / #670 — same-harness lanes `-v2`: the budgeted control under a declared transition

**change_class**: feature
**doc_tier**: standard
**risk_grade**: L2
**research_artifact**: docs/research-brief-north-star-six-tranches-2026-10-06.md (Finding C; Entry #60) plus the lane code map of 2026-10-06 (this session; facts restated below with file:line)
**roadmap**: `.qor/roadmaps/north-star-best-in-class` prerequisite `prereq-lane-v3-ids` (resolver `/qor-plan`; the roadmap node is named "v3" because it is the third lane generation, while the lane ids the Baseline v2 declaration names are `amb-precisionmembench-retrieval-v2` and `longmemeval-s-retrieval-parity-v2`)
**baseline**: evaluation-only work during the declared transition to Runtime Baseline v2 (PR #678); nothing under the protected surface changes, so the checker keeps printing `TRANSITION`
**iteration**: 1

**terms**:
- term: lane generation
  home: docs/CONTRIBUTOR_ARCHITECTURE.md §10
- term: budgeted control
  home: docs/CONTRIBUTOR_ARCHITECTURE.md §10

**boundaries**:
- limitations: a new lane id re-executes every row (control, baseline, comparator) at the executing revision; accepted v1 rows are never copied forward (`comparability.not_comparable_to`, longmemeval lane :2). The control's runtime is in a declared transition: the lane records that posture and the importer binds the checker's state to the evidence; it does not wait for Runtime Baseline v2, because the v2 publication is what these lanes are evidence for. The LongMemEval control passes `budget=50` and reads `returned`: at the deepest scored k the ranked prefix is the full ranking's prefix, so no scored metric can change; the AMB control passes the case budget and reads `returned`, which is the first measurement of truncation moved from the bridge to the facade. Hindsight stays deferred on both lanes (`decision-hindsight-provider`).
- non_goals: changing the runtime package or any `api-*` schema (the contract is 1.4.0 already); editing the accepted v1 lane files (`change_rule`: "never edited in place once status leaves frozen"); re-running v1 rows; changing the Mem0 bridges (`reference/amb_mem0_explicit_bridge.py`, `reference/longmemeval_mem0_explicit_bridge.py`), whose blobs the LongMemEval v1 lane pins and the v2 lane re-pins unchanged; publishing Runtime Baseline v2 (docs/67 Steps B1/B2, after these lanes are accepted); an LLM-judged lane; LongMemEval_M; a budgeted default.
- exclusions: `reference/agentmem_ref/runtime/**`, `api/**`, `pyproject.toml`, `schemas/api-*.json`, `reports/runtime/**`, both v1 lane files, both v1 evidence trees under `reports/benchmarks/{amb,longmemeval}/*-v1/`, the two Mem0 bridges.

## Open Questions

None blocking. Two defaults are taken and flagged:

1. **AMB normalized run ids gain the lane id** (LD5), so the v1 normalized manifests under `reports/benchmarks/normalized/amb-precisionmembench-single-turn-*.json` are regenerated under their new names in Phase 1 (derived artifacts, re-derived by the same normalizer from the same evidence; the scorecard `--check` proves it). The alternative, a lane id only for `-v2`, would leave two naming rules.
2. **The importer's expected Agent Memory configuration comes from the lane** (LD4). The accepted v1 lane carries that expectation only as prose (`execution_identity_requirements`, longmemeval lane :162), so the importer keeps the literal v1 expectation for the v1 lane id alone and reads the structured `configuration.agent_memory_configuration` from every later lane. That branch is named for the v1 lane, not a compatibility mode.

## Locked Decisions

**LD1 — Workflows take the lane as an input; the v1 lanes stay selectable and refuse to run.** `.github/workflows/longmemeval-competitive.yml` and `.github/workflows/amb-competitive.yml` gain `inputs.lane_id` (`type: choice`, options `longmemeval-s-retrieval-parity-v1`, `longmemeval-s-retrieval-parity-v2` and `amb-precisionmembench-retrieval-v1`, `amb-precisionmembench-retrieval-v2`; default the `-v2` id); `LANE_FILE` becomes `reference/agentmem_ref/evaluation/lanes/${{ inputs.lane_id }}.json` (today literal at longmemeval :54 and amb :62); the LongMemEval assertion `lane["lane_id"] == "longmemeval-s-retrieval-parity-v1"` (:100) becomes `== inputs.lane_id`. The existing `lane["status"] == "frozen"` assertions (longmemeval :99, amb :204) are what refuse an accepted v1 lane. Both workflows gain a step after install that runs `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` under `set -euo pipefail`, captures the line, and records `runtime_baseline_state` (`PASS` or `TRANSITION`) and the full line in the execution identity; a failing checker fails the run. The AMB workflow gains the LongMemEval workflow's blob loop (longmemeval :104-109) over `lane["harness"]["source_blobs"]` entries that start with `reference/` (the v1 AMB lane has none, so the loop is a no-op there) and records `lane_digest_sha256` from `validate-lane --json` as the LongMemEval workflow does (:187). Concurrency groups include the lane id.
Grep-evidence for `.github/workflows/longmemeval-competitive.yml:100`:
`git show origin/main:.github/workflows/longmemeval-competitive.yml | grep -nE 'assert lane\["lane_id"\] == ' -> 100:          assert lane["lane_id"] == "longmemeval-s-retrieval-parity-v1"`
Grep-evidence for `.github/workflows/amb-competitive.yml:62`:
`git show origin/main:.github/workflows/amb-competitive.yml | grep -nE 'LANE_FILE: ' -> 62:      LANE_FILE: reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v1.json`

**LD2 — The AMB bridge 0.2.0 asks the facade for the case budget and returns `returned`.** `reference/amb_agent_memory_bridge.py`: `BRIDGE_VERSION = "0.2.0"` (:27); `retrieve` refuses `k < 1` with `ValueError("AMB case budget must be at least 1")` instead of tolerating it (`max(0, int(k))`, :233), calls `memory.recall(str(query), budget=int(k))` (:212), iterates `outcome["returned"]` and never truncates in the loop; the raw response adds `return_policy` (the facade's object verbatim) and keeps `candidate_count`, `admitted_count` (from `admitted`, still the full set), `returned_count` (from `returned`) and `unmapped_admitted` (unmapped ids among `returned`). A second AMB sidecar field is not needed. The module docstring states that truncation is the facade's `ranked-prefix-return-budget` policy, never the bridge's.
Grep-evidence for `reference/amb_agent_memory_bridge.py:212`:
`git show origin/main:reference/amb_agent_memory_bridge.py | grep -nE 'outcome = memory.recall\(str\(query\)\)' -> 212:                outcome = memory.recall(str(query))`
Grep-evidence for `reference/amb_agent_memory_bridge.py:233`:
`git show origin/main:reference/amb_agent_memory_bridge.py | grep -nE 'if len\(documents\) >= max\(0, int\(k\)\)' -> 233:                if len(documents) >= max(0, int(k)):`

**LD3 — The LongMemEval runner gains a declared budget and reads `returned`.** `reference/run_longmemeval.py`: `_AGENT_MEMORY_CONFIGURATION` (:451) gains `"budget": "none"`; a CLI flag `--agent-memory-budget` (`none` or an integer ≥ 1, default `none`) sets it through `configure_agent_memory`; `_agent_memory` calls `memory.recall(question, reference_time=reference_time, budget=None if budget == "none" else int(budget))` (:534) and builds `ranked` from `recalled["returned"]` (:546), which equals `admitted` when unbudgeted so every existing replay is unchanged; each question row adds `returned_count` and the report's governance totals add `returned_total`; `execution.agent_memory_configuration` therefore carries three keys. The workflow passes `--agent-memory-budget` from the selected lane's control row (`configuration.agent_memory_configuration.budget`), so the lane, not the dispatcher, decides the budget. The runner blob changes; the v2 lane pins the new blob and the v1 lane keeps pinning `4acdecc…` as a historical fact (LD6).
Grep-evidence for `reference/run_longmemeval.py:534`:
`git show origin/main:reference/run_longmemeval.py | grep -nE 'recalled = memory.recall\(question, reference_time=reference_time\)' -> 534:            recalled = memory.recall(question, reference_time=reference_time)`
Grep-evidence for `reference/run_longmemeval.py:451`:
`git show origin/main:reference/run_longmemeval.py | grep -nE '^_AGENT_MEMORY_CONFIGURATION' -> 451:_AGENT_MEMORY_CONFIGURATION: dict[str, str] = {"temporal_metadata": "none", "ranking_variant": "default"}`

**LD4 — Importers bind what the lane declares, including the baseline posture.** `scripts/import_longmemeval_lane_evidence.py`: `FROZEN_AGENT_MEMORY_CONFIGURATION` (:54) becomes `expected_agent_memory_configuration(lane)`: the control row's `configuration.agent_memory_configuration` object when the lane declares one, else, for `lane_id == "longmemeval-s-retrieval-parity-v1"` only, the literal `{"temporal_metadata": "none", "ranking_variant": "default"}`; any other lane without the object is refused (`lane declares no agent_memory_configuration`). The equality check (:171-172) compares against that. Both importers require `identity["runtime_baseline_state"]` in `{"PASS", "TRANSITION"}` when the lane's control row declares `source.runtime_baseline_posture` (the v2 lanes do; the v1 lanes do not, and their imports are closed) and copy the state and line into `evidence.system.runtime_baseline`. `scripts/import_amb_lane_evidence.py` additionally refuses a `bridge_blobs` entry that differs from the lane's `harness.source_blobs` for any `reference/*` path the lane pins, and a `lane_digest_sha256` that differs from `lane_digest(lane at the executing revision)`, exactly as the LongMemEval importer does (:130, :137); the AMB v1 lane pins no `reference/*` blob and its identity carries no digest, so those checks are vacuous for v1 and binding for v2.
Grep-evidence for `scripts/import_longmemeval_lane_evidence.py:54`:
`git show origin/main:scripts/import_longmemeval_lane_evidence.py | grep -nE '^FROZEN_AGENT_MEMORY_CONFIGURATION' -> 54:FROZEN_AGENT_MEMORY_CONFIGURATION = {"temporal_metadata": "none", "ranking_variant": "default"}`
Grep-evidence for `scripts/import_amb_lane_evidence.py:150`:
`git show origin/main:scripts/import_amb_lane_evidence.py | grep -nE 'amb_pmb_return_cap' -> 150:    if identity.get("full_selection") is not True or identity.get("amb_pmb_return_cap") is not None:`

**LD5 — The AMB normalizer names the lane in `run_id`.** `reference/agentmem_ref/evaluation/normalize.py` `normalize_amb_precisionmembench` (:523): `run_id = f"{AMB_PRECISIONMEMBENCH_BENCHMARK_ID}:{record['lane_id']}:{execution['split']}:{system['id']}:{system['revision'][:12]}"`, so a v2 BM25 or Mem0 row (same harness and system revisions as v1) cannot overwrite a v1 manifest. The three v1 manifests are regenerated under the new names and the old files removed; `scripts/build_benchmark_scorecards.py` SOURCES and the dashboard `normalized_runs` entries follow. `task_profile` already carries the lane id (:532).
Grep-evidence for `reference/agentmem_ref/evaluation/normalize.py:523`:
`git show origin/main:reference/agentmem_ref/evaluation/normalize.py | grep -nE '"run_id": f"\{AMB_PRECISIONMEMBENCH_BENCHMARK_ID\}' -> 523:        "run_id": f"{AMB_PRECISIONMEMBENCH_BENCHMARK_ID}:{execution['split']}:{system['id']}:{system['revision'][:12]}",`

**LD6 — The two `-v2` lane files are frozen before any score, and the tests become lane-scoped.** `reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v2.json` and `longmemeval-s-retrieval-parity-v2.json`: copies of the v1 records with `lane_id`, `owning_issue` (640, with 670 and 674 in `description`), `frozen_on`, `status: frozen` and every row `frozen` (Hindsight `deferred`, same `status_reason`), `status_reason` removed from frozen rows, `comparability.not_comparable_to` naming the v1 lane ("the control's return shape and the executing runtime differ"), and these control-row changes: `display_name` "Agent Memory (public facade, declared transition to Runtime Baseline v2)"; `source.runtime_baseline_posture` `{"predecessor": "agent-memory-runtime-baseline-v1", "declared_successor": "agent-memory-runtime-baseline-v2", "declaration": "reports/runtime/baseline-v2-declaration.json", "checker_state_required": ["PASS", "TRANSITION"]}`; `source.revision_rule` "git rev-parse HEAD of the executing checkout; the protected runtime surface is pinned by scripts/check_runtime_baseline_equivalence.py, which must print PASS or TRANSITION (declared successor agent-memory-runtime-baseline-v2) for the run to be importable; the state is recorded in the execution identity"; AMB `configuration.recall` "memory.recall(query, budget=k) where k is the case's maxBeliefs budget; `returned` is the facade's ranked-prefix policy (contract 1.4.0); admitted stays whole and is counted" and `configuration.k` "the facade's return budget, never a bridge-side cap"; LongMemEval `configuration.agent_memory_configuration` `{"temporal_metadata": "none", "ranking_variant": "default", "budget": "50"}` and `configuration.recall`/`k` saying `budget=50` reading `returned`; `adapter.revision_rule` naming the new blobs. `harness.source_blobs` of the AMB v2 lane adds `reference/amb_agent_memory_bridge.py` and `reference/amb_mem0_explicit_bridge.py`; the LongMemEval v2 lane re-pins the three `reference/*` blobs with the new runner blob. `execution.execution_identity_requirements` lists the budget, the bridge blobs (AMB), the lane digest (AMB) and the checker state. `reference/tests/test_same_harness_lane.py`: the CLI list assertion (:227-229) becomes the four ids in sorted order with `accepted, accepted, frozen, frozen`; the AMB binding count (:92) filters bindings by the `lane:{LANE_ID}:` prefix as the LongMemEval test does (:327); `test_lane_binds_the_runner_and_bridge_blobs_it_freezes` (:360-375) compares the v1 lane's `reference/*` blobs against the committed v1 evidence records' `execution.source_blobs`, not against `HEAD` (the lane is accepted: its pins are a fact about the runs it bound); the workflow-text assertions (:409, :411) become `"lanes/${{ inputs.lane_id }}.json"` and the unchanged `frozen` literal; new classes `AmbPrecisionMemBenchV2LaneTests` and `LongMemEvalParityV2LaneTests` assert: status frozen, every non-deferred row frozen, no score keys, every pinned `reference/*` blob equal to `git hash-object` at HEAD, the control row's `runtime_baseline_posture` and budget configuration present, the AMB bridge `BRIDGE_VERSION == "0.2.0"`, and `resolve_lane` succeeding. `test_import_*_lane_evidence.py` gain one case each for the v2 lane (a synthetic identity with `runtime_baseline_state: TRANSITION` imports; `FAIL` or a missing state is refused; an AMB `bridge_blobs` mismatch is refused).
Grep-evidence for `reference/tests/test_same_harness_lane.py:227`:
`git show origin/main:reference/tests/test_same_harness_lane.py | grep -nE 'assertEqual\(\[lane\["lane_id"\] for lane in report\["lanes"\]\], \[LANE_ID, LME_LANE_ID\]\)' -> 227:        self.assertEqual([lane["lane_id"] for lane in report["lanes"]], [LANE_ID, LME_LANE_ID])`
Grep-evidence for `reference/tests/test_same_harness_lane.py:92`:
`git show origin/main:reference/tests/test_same_harness_lane.py | grep -nE 'self.assertEqual\(len\(bindings\), 3\)' -> 92:        self.assertEqual(len(bindings), 3)`
Grep-evidence for `reference/tests/test_same_harness_lane.py:360`:
`git show origin/main:reference/tests/test_same_harness_lane.py | grep -nE 'def test_lane_binds_the_runner_and_bridge_blobs_it_freezes' -> 360:    def test_lane_binds_the_runner_and_bridge_blobs_it_freezes(self):`

**LD7 — Execution, import and acceptance follow the lane v1 procedure, under the lane id input.** After the freeze PR merges, dispatch nine runs on `main`: AMB `lane_id=amb-precisionmembench-retrieval-v2` × `memory` in {`agent-memory`, `bm25`, `mem0-explicit`} (dataset precisionmembench, split single-turn, mode retrieval, query_limit 0), and LongMemEval `lane_id=longmemeval-s-retrieval-parity-v2` × `backend` in {`agent_memory`, `lexical_overlap`, `mem0_explicit`} × `granularity` in {`session`, `turn`}, subset_size 0. Import each completed run through `.github/workflows/amb-evidence-import.yml` (`lane` amb|longmemeval, the run ids, a branch), which writes `reports/benchmarks/{amb,longmemeval}/<lane_id>/...` with `evidence.json`. Acceptance is one commit per lane mirroring 5b38458 and 55b2b1d: lane and row statuses `accepted` with `status_reason`s naming date, revision, run ids, evidence directories and the `evidence_history` ids `lane:<lane_id>:<provider>[:<plane>]`; the integration descriptors' `evidence_history` entries with `report_binding`; `build_benchmark_scorecards.py` SOURCES; normalized manifests; `reports/benchmarks/dashboard/current.{json,md}` `frozen_lanes` entries; `docs/CONTRIBUTOR_ARCHITECTURE.md` §10. Acceptance gates from #670: the LongMemEval v2 control's recall_all@k and ndcg_any@k at every scored k equal the v1 control's (the ranked prefix at 50 is the full ranking's prefix); the AMB v2 control's mean precision and active passes are reported against v1 with the return-shape change named as the only difference; neither number is authority. If any row fails or is blocked, the lane records it as `blocked` with a reason and acceptance proceeds for the rows that completed, exactly as Hindsight is deferred today.

**LD8 — Documentation.** `docs/CONTRIBUTOR_ARCHITECTURE.md` §10 gains a paragraph on lane generations: a lane id names one frozen configuration; the workflows select the lane by input; a lane whose control runs during a declared transition records the checker state and the importer binds it; the `-v2` lanes are the first to read `returned`. `docs/54-*` (the LongMemEval lane document, if it names the lane id) and `docs/53` are not edited unless they state the v1 lane as the only lane. `docs/GOVERNANCE_INDEX.md` Tier 4: this plan `ACTIVE`. The roadmap node `prereq-lane-v3-ids` is resolved by pointer at the freeze merge (the ids exist and are bound), not at acceptance.

## Phase 1: lane-agnostic pipeline (no new lane yet)

### Affected Files

- `.github/workflows/longmemeval-competitive.yml`, `.github/workflows/amb-competitive.yml` - `lane_id` input, lane-derived `LANE_FILE`, checker state in the identity, AMB blob loop and lane digest, LD1
- `scripts/import_longmemeval_lane_evidence.py`, `scripts/import_amb_lane_evidence.py` - lane-declared configuration, checker-state binding, AMB blob and digest checks, LD4
- `reference/agentmem_ref/evaluation/normalize.py` - AMB `run_id` with the lane id, LD5
- `reports/benchmarks/normalized/amb-precisionmembench-*.json`, `scripts/build_benchmark_scorecards.py`, `reports/benchmarks/scorecards/*`, `reports/benchmarks/dashboard/current.{json,md}` - regenerated names, LD5
- `reference/tests/test_same_harness_lane.py` - lane-scoped assertions (:92, :227-229, :360-375, :409), LD6
- `reference/tests/test_import_longmemeval_lane_evidence.py`, `reference/tests/test_import_amb_lane_evidence.py` - the v1 behaviour unchanged; refusal cases for a missing or `FAIL` checker state when the lane declares a posture, LD4

### Changes

Per LD1, LD4, LD5 and the v1-scoped parts of LD6. The v1 lanes are untouched and still import their committed evidence unchanged (`test_import_*` v1 cases).

### Unit Tests

- `reference/tests/test_same_harness_lane.py` - the v1 classes pass with lane-scoped assertions; the v1 blob test compares lane pins to committed evidence.
- `reference/tests/test_import_*_lane_evidence.py` - v1 synthetic artifacts import as before; a v2-style lane (fixture built in the test from the v1 lane with `runtime_baseline_posture` added) refuses a missing or `FAIL` state and accepts `TRANSITION`.
- `python scripts/build_benchmark_scorecards.py --check` and `python -m unittest reference.tests.test_memory_evaluation_scorecards` - the regenerated AMB manifests and SOURCES agree.

## Phase 2: the budgeted control and the two frozen `-v2` lanes

### Affected Files

- `reference/amb_agent_memory_bridge.py` - 0.2.0, `budget=k`, `returned`, LD2
- `reference/run_longmemeval.py` - `--agent-memory-budget`, `returned`, counts, LD3
- `reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v2.json`, `longmemeval-s-retrieval-parity-v2.json` - new, frozen, LD6
- `reference/tests/test_same_harness_lane.py` - the two `V2` classes, LD6
- `reference/tests/test_longmemeval.py`, `reference/tests/test_amb_agent_memory_bridge.py` (or the existing bridge test module) - the budget flag and the `returned` path, LD2/LD3
- `docs/CONTRIBUTOR_ARCHITECTURE.md`, `docs/GOVERNANCE_INDEX.md` - LD8
- `.qor/roadmaps/north-star-best-in-class/events.jsonl` - `prereq-lane-v3-ids` resolved at the freeze merge, LD8

### Changes

Per LD2, LD3, LD6 and LD8. The lane files are written last, after the bridge and runner blobs are final (`git hash-object`), and the `V2` tests pin them.

### Unit Tests

- `reference/tests/test_longmemeval.py` - `--agent-memory-budget 50` records `budget: "50"`, `ranked` equals the first 50 of `admitted`, `returned_count` ≤ 50; `none` leaves every existing assertion unchanged.
- the AMB bridge test - `retrieve(query, k=3)` returns at most three documents from `returned`, raw carries `return_policy` with `requested_k 3`, `admitted_count` is the full count; `k=0` raises.
- `reference/tests/test_same_harness_lane.py` - the `V2` classes.

## Phase 3: execute, import, accept (procedure, LD7)

### Affected Files

- `reports/benchmarks/amb/amb-precisionmembench-retrieval-v2/*`, `reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v2/*` - imported evidence
- the two `-v2` lane files (statuses and `status_reason`s), the two integration descriptors (`evidence_history`), `scripts/build_benchmark_scorecards.py`, `reports/benchmarks/normalized/*`, `reports/benchmarks/scorecards/*`, `reports/benchmarks/dashboard/current.{json,md}`, `docs/CONTRIBUTOR_ARCHITECTURE.md` - acceptance

### Changes

Per LD7.

### Unit Tests

- `reference/tests/test_same_harness_lane.py` - the `V2` classes assert `accepted` statuses and the `evidence_history` entries; `test_memory_evaluation_scorecards` covers the new manifests; `python scripts/build_benchmark_scorecards.py --check` is green.

## Definition of Done

### Deliverable: a lane-agnostic pipeline that binds the baseline posture

- **D1**: both workflows run the lane their input names and refuse an accepted lane; the identity carries the checker state; the importers bind the lane's declared configuration, the AMB bridge blobs and the lane digest, and refuse a run whose checker state is not `PASS` or `TRANSITION` when the lane declares a posture.

### Deliverable: the budgeted control, frozen

- **D2**: the AMB bridge 0.2.0 and the runner read `returned`; the two `-v2` lane files validate, resolve, pin the new blobs and declare the budget and the transition posture; `prereq-lane-v3-ids` is resolved.

### Deliverable: nine accepted rows

- **D3**: every row of both `-v2` lanes is accepted (or `blocked` with a reason), bound in `evidence_history`, normalized, on the scorecards and the dashboard, with the LongMemEval control's scored metrics equal to v1's and the AMB control's precision reported against v1.

## Feature Inventory Touches

| entry_id | operation | test_path | test_descriptor |
|---|---|---|---|
| n/a (evaluation, workflows, reports and docs; no `reference/agentmem_ref` feature outside `evaluation/` is touched) | n/a-justified | `reference/tests/test_same_harness_lane.py` | lane-scoped v1 assertions; the frozen `-v2` lanes pin the budgeted control, the bridge blobs and the transition posture |

## CI Commands

- `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` — stays `TRANSITION` (no protected change)
- `agent-memory benchmark validate-lane reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v2.json` and the LongMemEval counterpart — valid, frozen
- `python -m unittest reference.tests.test_same_harness_lane reference.tests.test_import_longmemeval_lane_evidence reference.tests.test_import_amb_lane_evidence reference.tests.test_longmemeval reference.tests.test_memory_evaluation_scorecards` — the lane, importer, runner and scorecard modules
- `python scripts/build_benchmark_scorecards.py --check` — manifests and SOURCES agree
- `python -m unittest discover -s reference/tests -t reference` — the full suite, 0 failures (the known local-only `test_proposition_evaluator` ancestry skip on a shallow clone aside)
- `qor-logic governance-health --profile skill-entry` — green after the index edits
