# Plan: #669 Step B evidence — `-v3` same-harness lanes for Runtime Baseline v3

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**parent plan**: docs/plan-669-semantic-vector-route.md (Gate PASS at Entry #87; Step A merged as `aede8fd`; `main` prints TRANSITION to v3)
**precedent**: docs/plan-640-lanes-v2-return-budget.md (LD1, LD5, LD6, LD7)
**owner rulings in force**: `decision-temporal-posture`, `decision-embedding-dependency`
**iteration**: 4 (Gate Tribunal PASS at attempt 4, META_LEDGER Entry #89)

Gate history:
- Attempt 1 VETO: the AMB lock conflict; no AMB evidence channel for the mode; representation identity under-bound; the gate structurally decided; an incomplete re-pin list.
- Attempt 2 VETO: no distinct identity for the D2 row; schema-invalid `role` and `status`; superseded text left in place.
- Attempt 3 VETO: D5 was not exhaustive (row statuses, the control's `display_name`, `not_comparable_to[0]`).

This iteration is a single normative list.

## Purpose

`reports/runtime/baseline-v3-declaration.json` names `longmemeval-s-retrieval-parity-v3` and `amb-precisionmembench-retrieval-v3` as acceptance evidence for publishing Runtime Baseline v3.

v3's shipped default is `semantic_retrieval="off"` under ranking policy 3.2.0. Publication evidence must therefore show that this default reproduces v2 on both external benchmarks (D1).

The opt-in semantic route is measured separately on LongMemEval (D2).

#669's original gate ("turn recall_all@50 and session recall_all@5 must move") is **structurally unattainable under policy 3.2.0**:
- a candidate found only by the semantic route ranks after every lexical candidate;
- the v2 control admits at least 113 lexical candidates per turn question and at least 33 per session question.

That gate therefore transfers to #673 (D4).

## Decisions

**D1 — The control rows run the shipped default and must equal `-v2`.**
- In both lanes the `agent_memory` / `agent-memory` row is the `control`, at the v3 runtime with the facade default.
- It declares no `semantic_retrieval` and no `semantic_representation`. The importer reads absence as `off` through `RUNNER_CONFIGURATION_DEFAULTS`.
- Its configuration is otherwise identical to the `-v2` control (LongMemEval `budget` 50; AMB case budget).
- **Acceptance check:** every scored metric equals the accepted `-v2` control's exactly. For LongMemEval this means `headline`, `knowledge_update_headline` and `latest_gold_ranked_first` on both planes; for AMB, the harness summary metrics. Timing and governance counters are excluded.
- Any difference blocks v3 publication.
- The relation to `-v2` sits in `comparability.notes` (held to equality), not in `not_comparable_to`.

**D2 — A measured semantic row on LongMemEval only.**
- Row `row_id` / `provider_key` `agent_memory_semantic`, `role: "comparator"`.
- `notes`: "measured semantic route row (#669 D2); not the v3 publication control; evidence for #673".
- `source`, `adapter`, `inference_posture`, `credentials`, `capability_posture` and `dependency_pins` are copied from the control row. `dependency_pins` adds `reference/requirements-semantic.txt`.
- Its `configuration` is the control's plus:
  - `semantic_retrieval: "required"`;
  - `semantic_representation`: `representation_ref` `sentence-transformers/multi-qa-MiniLM-L6-cos-v1@b207367`, `representation_version` `onnx-mean-l2-f32/1.0.0`, `config_digest` `sha256:7447705443160d1ae7c1de49902b786bd3f578d06e7125c05dabaed52dd31aee`, `dimensions` 384, `minimum_similarity` 0.30, `candidate_limit` 16.
- The runner records `execution.agent_memory_semantic_posture`, a flattening of `semantic_retrieval_posture()`:
  - `status` and `mode` from the top level;
  - `representation_ref`, `representation_version`, `config_digest` and `dimensions` from `representation`;
  - `minimum_similarity` and `candidate_limit` from the top level.
- The importer requires `status == "enabled"` and `mode == "required"`, and requires the other six fields to equal `semantic_representation` field for field.
- A report from the control row must carry no such posture.
- **Pre-registered prediction (frozen before any score):**
  - turn recall_all@50 and session recall_all@5/@10 equal D1, or differ only by tie reordering;
  - session recall_all@30/@50 may rise, because semantic-only candidates can reach ranks 34–50 on the session plane;
  - "move" means a strict increase on the same 419 scored questions.
- **Route diagnostics** per question (runner, `required` mode only):
  - the semantic-only admitted count;
  - gold items reached only through the semantic route;
  - the rank of each gold item in the full admitted list.

**D3 — The AMB lane has no semantic row.**
- AMB installs under its own uv.lock constraints (onnxruntime 1.22.1, tokenizers 0.22.2, numpy 2.4.3, protobuf 5.29.6, packaging 24.2). These conflict with the pinned `semantic` numerics.
- The AMB `-v3` lane therefore carries the rows `agent-memory` (D1 control), `bm25` and `mem0-explicit`, each re-executed.
- It records `agent_memory_semantic` with `status: "deferred"` and a `status_reason` naming the lock conflict.
- It mirrors the Hindsight deferred row: `source`/`adapter` declare the intended identity, with `configuration` and `capability_posture` as `{}`.
- The AMB lane's `freeze_rationale` names the deferred row, so the row that is not run is visible at freeze.
- The AMB bridge stays at 0.2.0, unchanged; no bridge blob is re-pinned.

**D4 — The #669 gate disposition.**
- The "must move" gate is recorded as not attainable under policy 3.2.0. It transfers to #673 (fusion), together with D2's diagnostics and the default-on question.
- #669 closes at v3 publication (Step B1/B2), with D1 accepted and D2 measured.
- No lane in this plan is re-frozen or re-configured after any score.

**D5 — Lane-file differences from `-v2`, exhaustive.** The lane test asserts field-for-field equality with `-v2` except exactly these:
- `lane_id`, `status: "frozen"`, `frozen_on`, `owning_issue: 669`, `description`, `freeze_rationale`, `comparability.notes`;
- each row's `status` becomes `frozen` and its `status_reason` is removed; a `deferred` row (Hindsight) keeps its status and reason unchanged;
- the control row's `display_name` names the declared transition to Runtime Baseline v3;
- `comparability.not_comparable_to[0]` describes the `-v2` relation. Same-system rows are re-executed, never copied forward. The control is held to D1 equality, so the entry says it is not a comparability claim;
- LongMemEval only:
  - `harness.source_blobs["reference/run_longmemeval.py"]`;
  - `evaluator.scorer`;
  - any `adapter.revision_rule` text naming the runner blob;
  - the new D2 row;
  - `budget.forbidden_overrides` gains "`--agent-memory-semantic-retrieval` only on `agent_memory_semantic`; `auto` refused";
  - `execution.environment` notes the semantic install and model fetch for D2 only;
  - `execution_identity_requirements` gains the D2 posture;
- AMB only: the D3 deferred row;
- both lanes: the control's `configuration.runtime_baseline_posture` object is replaced as a whole:
  - `predecessor` becomes v2;
  - `declared_successor` becomes v3;
  - `declaration` becomes `reports/runtime/baseline-v3-declaration.json`;
  - `declaration_blob` becomes that file's blob;
  - `checker_state_required` is unchanged;
- lexical and bm25 rows: `source.revision` follows the executing-revision rule.

Additional acceptance checks:
- the lexical/bm25 rows must equal `-v2` exactly;
- the Mem0 rows are expected to equal `-v2` (same pins), and any difference is recorded as an environment finding.

**D6 — Runner, importer and workflows.**
- `reference/run_longmemeval.py`:
  - `_AGENT_MEMORY_CONFIGURATION` gains `semantic_retrieval: "off"`;
  - `--agent-memory-semantic-retrieval {off,required}` is accepted only with `--backend agent_memory`;
  - when the mode is `required`, the report records the posture and the D2 diagnostics.
- `scripts/import_longmemeval_lane_evidence.py`:
  - `RUNNER_CONFIGURATION_DEFAULTS` gains `semantic_retrieval: "off"`;
  - the row is selected by `identity.backend` (the row's `provider_key`), and the report is checked against `identity.runner_backend`;
  - the expected configuration, including `semantic_representation`, comes from the **matched row**, not from `control_row()`;
  - the destination directory, normalizer manifest names and `evidence_history` ids use the row's `provider_key`.
- Tests:
  - D1 and D2 identities at the same revision import side by side;
  - a D2 report checked against the control row is refused;
  - a posture mismatch is refused.
- `longmemeval-competitive.yml`:
  - the backend choice gains `agent_memory_semantic`;
  - the workflow reads the selected row's configuration from the lane file;
  - it refuses `agent_memory_semantic` on lanes that have no such row;
  - it writes `identity.backend = agent_memory_semantic` and `identity.runner_backend = agent_memory`;
  - for that row only, it installs with `-c reference/requirements-semantic.txt`, restores and fetches the pinned model by digest, and sets `AGENT_MEMORY_REPRESENTATION_DIR`.
- Both workflows' `lane_id` default becomes `-v3`.
- **Timeout.** Expected D2 session-plane cost is about 80 minutes (embedding about 70, opens about 7, ingest about 3), or about 2 hours on a slower runner. The LongMemEval job timeout rises from 180 to 240 minutes, together with the workflow policy and the inventory.
- The CLI lane-list test covers six lanes: four accepted and two frozen.

**D7 — Execution and acceptance (after merge, on `main`).**
- Dispatch the LongMemEval rows `agent_memory`, `agent_memory_semantic`, `lexical_overlap` and `mem0_explicit`, each on the session and turn planes (8 runs).
- Dispatch the AMB rows `agent-memory`, `bm25` and `mem0-explicit` (3 runs).
- Import through `amb-evidence-import.yml`.
- Re-dispatch is allowed only after an infrastructure failure that occurred before any score was produced, with identical inputs (plan-640 LD7).
- Accept per D1, D2 and D5.
- Cite the accepted rows, plus the public gauntlet probe, in docs/67 Step B1. The probe is out of this plan's scope and is run at B1.

## Boundaries

- **non_goals:**
  - any runtime change (the runtime is the merged v3 candidate);
  - an AMB semantic row (D3);
  - fusion or default-on (#673).
- **exclusions:**
  - no temporal metadata;
  - no ranking variant;
  - no answer generation;
  - no change to `-v1` or `-v2` lanes or evidence.

## Open Questions

None blocking.

## Implementation amendments

**IA1 — three lane-file differences D5 left implicit, and the selection of the configuration row.**
- `findings`: the `-v2` acceptance entry ("accepted rows …") describes `-v2` rows. It is not carried into an unexecuted lane. All other findings are unchanged.
- `execution.timeout` (LongMemEval) restates the workflow timeout: 240 minutes (D6).
- `execution.execution_identity_requirements` (AMB) gains one line stating that no `agent_memory_semantic` run is importable under the lane (D3). This is the gate's attempt-3 advisory.
- The importer takes the expected Agent Memory configuration, the semantic posture and the runtime-baseline posture from the matched row **when that row runs the `agent_memory` backend** (the control, or D2). Lexical and Mem0 runs record the control's Agent Memory configuration, as in `-v2`, because the workflow passes the control's budget to every row. Their expectation therefore stays the control's.
- `reference/tests/test_same_harness_lanes_v3.py` asserts that the v2→v3 difference is exactly D5 plus these items.
