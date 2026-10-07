# Plan: #644 Step B evidence — `-v4` same-harness lanes for Runtime Baseline v4

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**parent plan**: docs/plan-644-t-controller.md (Gate PASS at Entry #94; implementation Entry #95; merged as `729a6c8`; `main` prints TRANSITION to v4). This plan is that plan's S9.
**precedent**: docs/plan-669-lanes-v3.md (D1, D2, D3, D5, D6, D7, IA1, IA2)
**owner rulings in force**: `decision-temporal-posture`, `decision-embedding-dependency`
**doctrine**: controller output != truth; stop recommendation != actual stop reason; benchmark score != truth
**iteration**: 4 (Gate Tribunal PASS at attempt 4, META_LEDGER Entry #97)

Gate history:
- **Attempt 1, VETO, four findings:**
  - **B1:** the frozen AMB runner stores no provider raw response (`raw_response=None`, `src/memory_bench/runner.py:273` at `03c1d0f1`), so AMB shadow telemetry would never reach evidence.
  - **B2:** telemetry field paths were misnamed.
  - **B3:** no re-pin list for four existing tests.
  - **B4:** AMB L1 omitted ranked outputs, which parent S9 requires.

  The L2 prediction, L5 exhaustiveness and lane-schema validity were verified sound by a prototype. Scratch work is in `scratchpad/gate644v4/`.

  Iteration 2 amends L1, L2, L5 and L6 and adds L9. The attempt-1 advisories are folded in.
- **Attempt 2, VETO, one finding.** Four of the 77 AMB cases have a blank query (`edge-empty-query`, `edge-whitespace-query`, `narrator-voice-pinned-in-own-scope`, `recency-tiebreak-reinforcement`). The frozen `RetrievalMode` answers them without calling `retrieve()` (`modes/retrieval.py`). L9's "one record per case" join would therefore refuse every valid run.

  Iteration 3 joins over non-blank cases only, and blank cases are "no recall executed". The attempt-2 advisories are folded in:
  - adjacent duplicates are refused, not superseded;
  - concurrency 1 is pinned, and `call_index` must be contiguous;
  - the importer's copy target is named;
  - the superseded L2 wording is removed.
- **Attempt 3, VETO, one finding.** For a blank-query case, L9 required an empty `meta.retrieved_questions`. The harness fills pinned open questions from the seed corpus whether or not a retrieval runs (`precisionmembench.py:528-529`), and every retained run has a non-empty list there. Iteration 4 replaces that condition with `retrieved_count == 0`, `resolution == {}` and an empty `context`.

## Purpose

`reports/runtime/baseline-v4-declaration.json` names `longmemeval-s-retrieval-parity-v4` and `amb-precisionmembench-retrieval-v4` as acceptance evidence for publishing Runtime Baseline v4.

v4 changes only:
- the public contract, 1.4.0 → 1.5.0, with the optional `recall_control` result field;
- an opt-in shadow controller (`recall_control="shadow"`) that adds telemetry and never changes retrieval;
- the harness-only domain prefilter (S6).

Ranking policy stays 3.2.0.

The lanes must show two things:
- **L1:** the shipped default (`recall_control="off"`) reproduces `-v3` exactly.
- **L2:** the shadow mode reproduces the default exactly at benchmark scale, the S1 invariant. Its per-question telemetry is recorded as evidence for T-controller-2's budget design. It is not a quality claim.

## Decisions

**L1 — The control rows run the shipped default and must equal `-v3`.**
- In both lanes, the `agent_memory` / `agent-memory` row is the `control`, at the v4 runtime with the facade default.
- It declares no `recall_control` and no `semantic_retrieval`. The importer reads their absence as `off` through `RUNNER_CONFIGURATION_DEFAULTS`.
- Its configuration is otherwise identical to the `-v3` control (LongMemEval `budget` 50; the AMB case budget).
- **Acceptance check: exact equality with the accepted `-v3` control.**
  - LongMemEval: every scored metric (`headline`, `knowledge_update_headline`, `latest_gold_ranked_first`, on both planes) and every question's `ranked_top` and `metrics`.
  - AMB: the harness summary (`active_passes`, `mean_precision`, `mean_recall`, `correct`, `accuracy`), plus every case (77), compared by `query_id`, on:
    - `correct`;
    - `context`, the ordered rendered retrieval;
    - `meta.relevant_beliefs`, `meta.pinned_beliefs` and `meta.retrieved_questions`, as ordered lists;
    - `meta.retrieval_precision`, `meta.retrieval_recall`, `meta.pinned_coverage`, `meta.resolution`, `meta.failures` and `meta.retrieved_count`.

    The gate verified that the `-v2` and `-v3` controls are byte-equal on every case field except `retrieve_time_ms`, so this check is attainable.
  - Timing and governance counters are excluded. The envelope's `contract_version` reads 1.5.0 and is not in any report.
- Any difference blocks v4 publication.

**L2 — A shadow row on each lane.**
- **LongMemEval:**
  - row `row_id` `agent-memory-recall-control-shadow`, `provider_key` `agent_memory_shadow`, `role: "comparator"`, `system_id` `agent-memory`;
  - `notes`: "measured shadow recall-control row (#644 S9); not the v4 publication control; evidence for T-controller-2";
  - `source`, `adapter`, `inference_posture`, `credentials`, `capability_posture` and `dependency_pins` are copied from the control;
  - `display_name`: "Agent Memory (public facade, shadow recall control, declared transition to Runtime Baseline v4)";
  - `configuration` is the control's plus `recall_control: "shadow"` and a `recall_control_telemetry` description string.
- **AMB:**
  - row `agent-memory-recall-control-shadow`, `provider_key` `agent-memory-shadow`, the same role and system;
  - the same `display_name`;
  - `configuration` is the control's plus `recall_control: "shadow"` and the same description key.
- **Acceptance (blocking):**
  - every scored metric and every per-question `ranked_top`/`metrics` (LongMemEval), or every L1 per-case field (AMB), equals the **same lane's** control exactly;
  - every question (LongMemEval) or retrieval call (AMB, through the L9 sidecar) with no runtime error carries a telemetry record whose `authority_effect` is `"none"`.
- **Recorded telemetry:**
  - **Per question (LongMemEval rows) or per non-blank case (AMB, the L9 sidecar record), deterministic fields only:**
    - `response.decision_status`;
    - `usage.fallback_events`;
    - `usage.controller_decisions_used`;
    - `actual_stop.actual_stop_reason` and `actual_stop.stop_class`;
    - `routes_executed`;
    - `route_candidate_counts`;
    - `shadow_delta` (`route` → `proposed_limit`, `actual_count`, `would_truncate`);
    - `authority_effect`.

    These are the exact key paths of the `recall_control` block that `shadow_control_report` emits (`runtime/recall_control.py`). The recorded record is that block with `usage.elapsed_ms` removed. No other timing field exists in the block.
  - **Aggregate (LongMemEval report; AMB evidence record per L9):**
    - counts per `actual_stop.actual_stop_reason`;
    - counts per `response.decision_status`;
    - per route, the count of questions with `would_truncate: true`;
    - `authority_effect: "none"`.
- **Pre-registered prediction (frozen before any score):**
  - With the semantic route off, no route has a host cap (`host_caps` is `{}`).
    - Every question with at least one candidate therefore reports `actual_stop.actual_stop_reason == "frontier_exhausted"` (`stop_class` `search_space`).
    - Every question with zero candidates reports `no_evidence`.
  - `max_candidates` never appears.
  - `response.decision_status` is `complete` on every question.
  - `would_truncate` counts are reported, with no gate. One expectation is stated before any score so it is not read afterwards as a finding: the controller's lexical proposal is at most 32, and LongMemEval turn questions admit at least 113 lexical candidates. `would_truncate` on the lexical route is therefore expected on nearly every LongMemEval question. It describes the proposal's size, not a defect.
- A `decision_status` other than `complete`, or a stop reason outside the prediction, is recorded as a finding. It blocks `jh-14-telemetry` from becoming `shipped` (L8) but not v4 publication. Retrieval equality is the publication check, and controller failure is designed to have no effect.

**L3 — The semantic row.**
- **LongMemEval:** `agent_memory_semantic` keeps its `-v3` declaration but becomes `status: "deferred"`, with a `status_reason`:
  - ranking policy 3.2.0 and the semantic route are unchanged since `-v3`;
  - the route's ordering effect was measured there (plan-669-lanes-v3 D2);
  - its next measurement belongs to #673's lanes;
  - the row is not re-executed and is never copied forward.
- **AMB:** `agent_memory_semantic` stays deferred with the `-v3` reason unchanged (the uv.lock conflict).
- A deferred row keeps `configuration` as declared. The Hindsight deferred rows are unchanged.

**L4 — Scorecards.** Both shadow rows stay out of the scorecards, by the plan-669-lanes-v3 IA2 rule: one system per comparison group. They carry evidence records, `evidence_history` entries without `normalized_reports`, the lane row and the L2 analysis.

**L5 — Lane-file differences from `-v3`, exhaustive.** The lane test asserts field-for-field equality with `-v3` except exactly these:
- **Top level:** `lane_id`, `status: "frozen"`, `frozen_on`, `owning_issue: 644`, `description`, `freeze_rationale`, `comparability.notes`.
- **`findings`:** the `-v3` acceptance entry is not carried into an unexecuted lane (plan-669-lanes-v3 IA1). All other findings are unchanged.
- **Row status:** each executed row's `status` becomes `frozen` and its `status_reason` is removed. A deferred row keeps its status and reason unchanged, except the L3 LongMemEval semantic row.
- **Row display names:** the control's `display_name` and the LongMemEval semantic row's `display_name` name the declared transition to Runtime Baseline v4.
- **`comparability.not_comparable_to[0]`** describes the `-v3` relation. Same-system rows are re-executed, never copied forward. The control is held to L1 equality, so the entry says it is not a comparability claim.
- **Both lanes, `runtime_baseline_posture`:** in the control's and every Agent Memory row's `configuration` (the semantic row's included), the object is replaced as a whole:
  - `predecessor` becomes v3;
  - `declared_successor` becomes v4;
  - `declaration` becomes `reports/runtime/baseline-v4-declaration.json`;
  - `declaration_blob` becomes that file's blob;
  - `checker_state_required` is unchanged.
- **Both lanes:** the new L2 shadow row.
- **LongMemEval only:**
  - `harness.source_blobs["reference/run_longmemeval.py"]`;
  - `evaluator.scorer`, where it names the runner blob;
  - every `adapter.revision_rule` naming the runner blob;
  - `budget.forbidden_overrides` gains "`--agent-memory-recall-control` only on `agent_memory_shadow` (shadow); every other row runs it off";
  - `execution.environment.dispatch_unit` names the `-v4` lane and the backend set `{agent_memory, agent_memory_shadow, lexical_overlap, mem0_explicit}`;
  - `execution.execution_identity_requirements`:
    - the configuration line gains `recall_control: off`, or `shadow` for `agent_memory_shadow`;
    - a shadow line: `identity.backend == agent_memory_shadow` and `identity.runner_backend == agent_memory`;
    - every question without a runtime error carries the L2 record, and every other row carries none.
- **AMB only:**
  - `harness.source_blobs["reference/amb_agent_memory_bridge.py"]` and the control's `adapter.revision_rule` (blob, and `bridge_version 0.3.0`);
  - `execution.execution_identity_requirements` gains a line: the shadow row's artifact carries the L9 sidecar with exactly one joined record per non-blank-query case and none for a blank-query case, and every other row's artifact carries no sidecar;
  - `execution.artifact_requirements` gains the L9 sidecar (`recall-control.jsonl`, shadow row only).
- **Both lanes:** the `lane_id` workflow `choice` options gain the `-v4` lane id. This is a workflow edit, listed here for completeness, not a lane-file field.
- **Lexical and BM25 rows:** `source.revision` follows the executing-revision rule.

Additional checks:
- the lexical and BM25 rows must equal `-v3` exactly;
- the Mem0 rows are expected to equal `-v3` (same pins). Any difference is recorded as an environment finding.

**L6 — Runner, bridge, importers, workflows.**
- **`reference/run_longmemeval.py`:**
  - `_AGENT_MEMORY_CONFIGURATION` gains `recall_control: "off"`;
  - `configure_agent_memory(recall_control=...)` accepts `off` or `shadow`;
  - `--agent-memory-recall-control {off,shadow}` is accepted only with `--backend agent_memory` alone;
  - an `off` run opens the facade exactly as before. No `recall_control` keyword is passed, so the facade default applies;
  - in `shadow`, each question row records the L2 per-question record under `recall_control`, and the report records the L2 aggregate under `recall_control_summary`;
  - `shadow` combined with `--agent-memory-semantic-retrieval required` is refused, because shadow-plus-semantic is an L3 non-goal.
- **`reference/amb_agent_memory_bridge.py`** (`BRIDGE_VERSION` 0.3.0):
  - `install_amb_agent_memory_provider` registers `agent-memory`, unchanged in behaviour, and `agent-memory-shadow`, which opens the facade with `recall_control="shadow"` on retrieve. Ingest is identical;
  - the shadow provider writes the L9 sidecar. The `agent-memory` raw response is unchanged except `bridge_version`. The frozen runner discards raw responses either way;
  - `install_amb_agent_memory_provider` keeps returning the control class. The tests and `run_amb_external.py` use that single return value.
- **`scripts/import_longmemeval_lane_evidence.py`:**
  - `RUNNER_CONFIGURATION_DEFAULTS` gains `recall_control: "off"`;
  - the matched-row rule (plan-669-lanes-v3 IA1) extends to the shadow row;
  - a check refuses a shadow run that is missing the per-question record, or a non-shadow run carrying one.
- **`scripts/import_amb_lane_evidence.py`:**
  - the row is matched by `provider_key`, as today;
  - `configuration.recall_control` absent is read as `off`;
  - the L9 sidecar is copied and hashed when the row is `shadow`, and its absence refuses the import. A sidecar on any other row refuses the import too;
  - the join and record checks follow L9.
- **Workflows:**
  - `longmemeval-competitive.yml`:
    - the backend choice gains `agent_memory_shadow`;
    - it reads the row's `recall_control` and passes `--agent-memory-recall-control`;
    - it writes `identity.runner_backend = agent_memory`.
  - `amb-competitive.yml`:
    - the memory choice gains `agent-memory-shadow`;
    - the credential-free retrieval allowlist gains `agent-memory-shadow`;
    - for `agent-memory-shadow` only, it sets `AGENT_MEMORY_AMB_RECALL_CONTROL_SIDECAR` to `$RUNNER_TEMP/amb-output/recall-control.jsonl`, so the sidecar lands in the uploaded artifact and the `sha256.txt` inventory.
  - Both workflows' `lane_id` default becomes `-v4`. Timeouts are unchanged.
- **Tests:**
  - `reference/tests/test_same_harness_lanes_v4.py`: L5 exhaustive;
  - runner `shadow` rows, and `off` byte-equality with the pre-change runner on a fixture question;
  - the bridge's two provider keys, with equal documents for one query;
  - importer refusals;
  - the CLI lane-list count;
  - the workflow inventory;
  - **re-pins (attempt-1 B3; a listed test becomes stale and is updated, never deleted):**
    - `reference/tests/test_same_harness_lanes_v3.py`: the workflows' `lane_id` default assertion becomes tolerant of the later `-v4` default, as the `-v3` test did for the succession state;
    - `reference/tests/test_same_harness_lane.py`: the live `BRIDGE_VERSION` assertion becomes 0.3.0. The `-v1`, `-v2` and `-v3` lanes' frozen `bridge_version 0.2.0` text stays;
    - `reference/tests/test_amb_agent_memory_bridge.py`: `BRIDGE_VERSION` and `raw["bridge_version"]` become 0.3.0;
    - `reference/tests/test_import_longmemeval_lane_evidence.py`: the exact expected configuration gains `recall_control: "off"`.

    Any other failing test found during implementation is listed as an implementation amendment with its reason before it is changed.

**L7 — Execution and acceptance (after merge, on `main`).**
- **LongMemEval:** `agent_memory`, `agent_memory_shadow`, `lexical_overlap` and `mem0_explicit` on both planes (8 runs).
- **AMB:** `agent-memory`, `agent-memory-shadow`, `bm25` and `mem0-explicit` (4 runs).
- Import through `amb-evidence-import.yml`.
- A re-dispatch is allowed only after an infrastructure failure that occurred before any score, with identical inputs (plan-640 LD7).
- Accept per L1, L2 and L5.
- Then docs/67 Step B1 for v4:
  - the record, boundary, qualification and `.md`;
  - the Gauntlet manifest and an adapter with `PUBLIC_CONTRACT_VERSION` 1.5.0;
  - the CONTRIBUTOR_ARCHITECTURE capability corrections from plan-644 S7 (`typed_relations_graph_traversal` and the controller planner become harness-only).
- Then Step B2 binds the probe artifact.

**L8 — Closeout.**
- At acceptance, `harvest-closeout-final-v4.json` supersedes v3 and changes one row: `jh-14-telemetry` becomes `shipped`, citing the accepted shadow rows, if L2 held without findings.
- v3 is never edited.
- Its consumers move to v4 as S8 did: `reference/run_rc1_evidence_closeout.py`, `reference/tests/test_rc1_evidence_closeout.py`, a `test_harvest_closeout_v4.py` that keeps the v3 assertions as published, and the CONTRIBUTOR_ARCHITECTURE "(v3 since …)" text.
- If L2 recorded a finding, no v4 fixture is cut, and `jh-14` stays `tranche` with the finding attached.

**L9 — The AMB shadow telemetry sidecar (attempt-1 B1).**
- **Writing.** When `AGENT_MEMORY_AMB_RECALL_CONTROL_SIDECAR` is set, the `agent-memory-shadow` provider appends one JSON line per `retrieve()` call:
  - `call_index`, starting at 0 and counted per provider instance;
  - `scope`, the bridge's sha256-derived scope;
  - `query_sha256`, the sha256 of the UTF-8 query text;
  - `budget`;
  - `recall_control`, the L2 record without `usage.elapsed_ms`.

  The control provider never writes one. If the variable is unset, the shadow provider refuses to retrieve, so a shadow run can never produce scores without telemetry.
- **Join.** `retrieve()` receives no `query_id`.
  - The frozen harness runs cases in `results[]` order at concurrency 1 (`runner.py` `_run_all`, a FIFO semaphore). It calls `retrieve()` exactly once per case whose `query.strip()` is non-empty, and never for a blank query.
  - Its transient-error retry cannot fire, because the bridge raises no transient code.
  - The importer requires:
    - `call_index` runs 0..n-1 with no gap or repeat;
    - no two adjacent records share `(scope, query_sha256)` (any adjacent duplicate refuses the import);
    - n equals the number of non-blank-query cases.
  - Records are joined positionally to the non-blank-query cases in file order, and each record's `query_sha256` must equal the sha256 of that case's `query`.
  - Each blank-query case must have:
    - no record;
    - `retrieve_time_ms == 0.0`;
    - empty `meta.relevant_beliefs`;
    - `meta.retrieved_count == 0`;
    - `meta.resolution == {}`;
    - `context == "## Retrieved memories (0)"`.

    `meta.retrieved_questions` and `meta.pinned_beliefs` are seed-corpus pins, not retrieval, and are not checked here.

    It is reported as `no_recall_executed`. It is never a zero, and it never counts in any stop or truncation count. Four such cases exist at freeze.
  - Any mismatch refuses the import as a blocked execution. It is never a score, and a missing record is never counted as zero.
  - The shadow provider class keeps `concurrency = 1`, and a test pins it.
- **Storage.** The importer copies the sidecar to `recall-control.jsonl` in the row's evidence directory, inventoried in `files` with its sha256. The evidence record gains `recall_control_sidecar: {file: "recall-control.jsonl", sha256, records, no_recall_executed_cases}`.
- **Reporting.** The AMB evidence record reports:
  - counts per `actual_stop.actual_stop_reason`;
  - counts per `response.decision_status`;
  - the per-route `would_truncate` count;
  - the `no_recall_executed` case count.

  These are reported under L2's terms and are not benchmark authority.

## Boundaries

- **non_goals:**
  - any runtime change (the runtime is the merged v4 candidate);
  - a semantic or shadow-plus-semantic row (L3);
  - enforced budgets or adaptive stopping (T-controller-2);
  - fusion (#673).
- **exclusions:**
  - no temporal metadata;
  - no ranking variant;
  - no answer generation;
  - no change to `-v1`, `-v2` or `-v3` lanes or evidence;
  - no lane is re-frozen or re-configured after any score.

## Open Questions

None blocking.
