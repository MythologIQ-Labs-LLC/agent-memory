# Plan: #644 Step B evidence — `-v4` same-harness lanes for Runtime Baseline v4

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**parent plan**: docs/plan-644-t-controller.md (Gate PASS at Entry #94; implementation Entry #95; merged as `729a6c8`; `main` prints TRANSITION to v4). This plan is that plan's S9.
**precedent**: docs/plan-669-lanes-v3.md (D1, D2, D3, D5, D6, D7, IA1, IA2)
**owner rulings in force**: `decision-temporal-posture`, `decision-embedding-dependency`
**doctrine**: controller output != truth; stop recommendation != actual stop reason; benchmark score != truth
**iteration**: 1

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
  - AMB: the harness summary (`active_passes`, `mean_precision`, `mean_recall`, `correct`, `accuracy`) and every case's `retrieval_precision`, `retrieval_recall` and `resolution`.
  - Timing and governance counters are excluded. The envelope's `contract_version` reads 1.5.0 and is not in any report.
- Any difference blocks v4 publication.

**L2 — A shadow row on each lane.**
- **LongMemEval:**
  - row `row_id` `agent-memory-recall-control-shadow`, `provider_key` `agent_memory_shadow`, `role: "comparator"`, `system_id` `agent-memory`;
  - `notes`: "measured shadow recall-control row (#644 S9); not the v4 publication control; evidence for T-controller-2";
  - `source`, `adapter`, `inference_posture`, `credentials`, `capability_posture` and `dependency_pins` are copied from the control;
  - `configuration` is the control's plus `recall_control: "shadow"` and a `recall_control_telemetry` description string.
- **AMB:**
  - row `agent-memory-recall-control-shadow`, `provider_key` `agent-memory-shadow`, the same role and system;
  - `configuration` is the control's plus `recall_control: "shadow"` and the same description key.
- **Acceptance (blocking):**
  - every scored metric and every per-question `ranked_top`/`metrics` (LongMemEval), or every per-case field above (AMB), equals the **same lane's** control exactly;
  - every question or case with no runtime error carries a `recall_control` record with `authority_effect: "none"`.
- **Recorded telemetry:**
  - **Per question (LongMemEval rows; AMB raw response per case), deterministic fields only:**
    - `decision_status`;
    - `fallback_events`;
    - `actual_stop.reason` and `actual_stop.class`;
    - `routes_executed`;
    - `route_candidate_counts`;
    - `shadow_delta` (`route` → `proposed_limit`, `actual_count`, `would_truncate`).
    - `elapsed_ms` and every timing field are excluded.
  - **Aggregate (LongMemEval report):**
    - counts per `actual_stop.reason`;
    - counts per `decision_status`;
    - per route, the count of questions with `would_truncate: true`;
    - `authority_effect: "none"`.
- **Pre-registered prediction (frozen before any score):**
  - With the semantic route off, no route has a host cap. Every question with at least one candidate therefore reports `frontier_exhausted` (class `search_space`), and every question with zero candidates reports `no_evidence`.
  - `max_candidates` never appears.
  - `decision_status` is `complete` on every question.
  - `would_truncate` counts are reported, with no prediction.
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
  - `execution.execution_identity_requirements` gains:
    - the shadow row's raw responses carry `recall_control` per case;
    - every other row's carry none.
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
  - in `shadow`, each question row records the L2 per-question record, and the report records the L2 aggregate.
- **`reference/amb_agent_memory_bridge.py`** (`BRIDGE_VERSION` 0.3.0):
  - `install_amb_agent_memory_provider` registers `agent-memory`, unchanged in behaviour, and `agent-memory-shadow`, which opens the facade with `recall_control="shadow"` on retrieve. Ingest is identical;
  - the shadow provider's raw response adds the L2 per-case record. The `agent-memory` raw response is unchanged except `bridge_version`.
- **`scripts/import_longmemeval_lane_evidence.py`:**
  - `RUNNER_CONFIGURATION_DEFAULTS` gains `recall_control: "off"`;
  - the matched-row rule (plan-669-lanes-v3 IA1) extends to the shadow row;
  - a check refuses a shadow run that is missing the per-question record, or a non-shadow run carrying one.
- **`scripts/import_amb_lane_evidence.py`:**
  - the row is matched by `provider_key`, as today;
  - a check binds the raw responses' `recall_control` presence to the row's `configuration.recall_control`.
- **Workflows:**
  - `longmemeval-competitive.yml`:
    - the backend choice gains `agent_memory_shadow`;
    - it reads the row's `recall_control` and passes `--agent-memory-recall-control`;
    - it writes `identity.runner_backend = agent_memory`.
  - `amb-competitive.yml`:
    - the memory choice gains `agent-memory-shadow`;
    - the credential-free retrieval allowlist gains `agent-memory-shadow`.
  - Both workflows' `lane_id` default becomes `-v4`. Timeouts are unchanged.
- **Tests:**
  - `reference/tests/test_same_harness_lanes_v4.py`: L5 exhaustive;
  - runner `shadow` rows, and `off` byte-equality with the pre-change runner on a fixture question;
  - the bridge's two provider keys, with equal documents for one query;
  - importer refusals;
  - the CLI lane-list count;
  - the workflow inventory.

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
