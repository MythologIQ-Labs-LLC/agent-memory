# Plan: #669 Step B evidence — `-v3` same-harness lanes for Runtime Baseline v3

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**parent plan**: docs/plan-669-semantic-vector-route.md (Gate PASS at Entry #87; Step A merged as `aede8fd`; `main` prints TRANSITION to v3)
**precedent**: docs/plan-640-lanes-v2-return-budget.md (LD1, LD5, LD6, LD7)
**owner rulings in force**: `decision-temporal-posture` (lanes receive only question and item text), `decision-embedding-dependency`
**iteration**: 1

## Purpose

`reports/runtime/baseline-v3-declaration.json` names `longmemeval-s-retrieval-parity-v3` and `amb-precisionmembench-retrieval-v3` as the acceptance evidence for publishing v3. #669's gate requires two things:

- turn-plane recall_all@50 and session recall_all@5 must **move** on LongMemEval_S;
- the AMB active passes must **not regress**;
- in both lanes, the Mem0 row is re-run for parity.

These lanes are frozen before any score. The Agent Memory control runs with `semantic_retrieval="required"`, the configuration whose effect v3 claims.

## Locked Decisions

**L1 — The runner declares the semantic mode.**
- `reference/run_longmemeval.py`:
  - `_AGENT_MEMORY_CONFIGURATION` gains `"semantic_retrieval": "off"`;
  - a CLI flag `--agent-memory-semantic-retrieval {off,required}` passes `semantic_retrieval=` to `AgentMemory.open`;
  - when the mode is `required`, the report's `execution` records `semantic_retrieval_posture()` from the first opened handle (representation ref/version/config_digest, minimum similarity, candidate limit), so a row binds its representation identity.
- `scripts/import_longmemeval_lane_evidence.py`:
  - `RUNNER_CONFIGURATION_DEFAULTS` gains `"semantic_retrieval": "off"`, so v1/v2 records, which lack the key, keep reading as `off`;
  - the importer refuses a row whose recorded `semantic_retrieval` differs from the lane's declared configuration, and refuses a `required` row that has no representation posture.

**L2 — The AMB bridge 0.3.0.**
- `reference/amb_agent_memory_bridge.py` reads the semantic mode from `AGENT_MEMORY_SEMANTIC_RETRIEVAL` (`off` default | `required`). It passes it to every `AgentMemory.open`, records it, and records the posture, in the raw response metadata `agent_memory_configuration`.
- `BRIDGE_VERSION` becomes `0.3.0`.
- The AMB importer gains the same default and refusal rules as L1.

**L3 — The lane files.**
- `reference/agentmem_ref/evaluation/lanes/longmemeval-s-retrieval-parity-v3.json` and `amb-precisionmembench-retrieval-v3.json` are copies of their `-v2` lanes with:
  - `lane_id` `-v3`, `status: "frozen"`, `frozen_before_any_score: true`, `owning_issue: 669`, and `not_comparable_to` naming `-v2` and `-v1`;
  - `harness.source_blobs` re-pinned to the new runner and bridge blobs;
  - the control row's `configuration` gaining `"semantic_retrieval": "required"` and keeping `budget` exactly as in `-v2` (LongMemEval 50, AMB case budget);
  - `configuration.runtime_baseline_posture` pinning `reports/runtime/baseline-v3-declaration.json`'s blob and the TRANSITION line;
  - the representation identity: `multi-qa-MiniLM-L6-cos-v1@b207367` with its file digests and `representation_version`;
  - the baseline and Mem0 rows unchanged in configuration and re-executed (no copying forward);
  - the dataset, selection, evaluator and scored k identical to `-v2`.
- `freeze_rationale` states that the lane's purpose is to measure the effect of the subordinate semantic route on recall@k. Any change is attributed to that route alone, because every other runtime identity is the v2 identity apart from policy 3.2.0, which is identical with the route off. The point is measurement, not tuning: nothing in the configuration was chosen after a score.

**L4 — The workflows.**
- `longmemeval-competitive.yml` and `amb-competitive.yml`:
  - add the `-v3` lane id to the `lane_id` choice;
  - when the lane's control configuration declares `semantic_retrieval: required` (read from the lane file, not inferred from the id), install `reference/requirements-semantic.txt`, restore and fetch the pinned model by digest (the `actions/cache` key from `semantic-representation.yml`), set `AGENT_MEMORY_REPRESENTATION_DIR`, and pass the flag or environment variable to the Agent Memory row only.
- The workflow policy (manual dispatch) is unchanged; the inventory mechanical fields are synced.

**L5 — Tests.**
- `reference/tests/test_same_harness_lane.py`:
  - the sorted lane list (:231) gains the two `-v3` ids;
  - new lane-scoped tests: the `-v3` lanes are frozen, bind the v3 declaration blob, declare `semantic_retrieval: required` only on the control, pin the current runner and bridge blobs, and are field-for-field identical to `-v2` apart from the fields listed in L3.
- Importer tests: defaults for legacy records, and refusal of a mode mismatch or a missing posture.
- Runner and bridge unit tests: the flag reaches `AgentMemory.open`; `off` is byte-identical to v2 behaviour.

**L6 — Execution and acceptance (after merge, on `main`).**
- Dispatch the LongMemEval `-v3` rows: agent_memory, lexical_overlap and mem0_explicit, each on the session and turn planes (6 runs).
- Dispatch the AMB `-v3` rows: agent-memory, bm25 and mem0 (3 runs).
- Import through `amb-evidence-import.yml` with the lane input.
- Acceptance follows each lane's existing rules (complete selection, digests, unmapped counts).
- The #669 gate is evaluated **as measured**:
  - if LongMemEval turn recall_all@50 and session recall_all@5 do not move, or AMB regresses, that is recorded and #669 stays open;
  - no configuration is changed after a score;
  - a regression is a finding, not a re-freeze.
- Accepted rows are then cited in docs/67 Step B1 for v3.

## Boundaries

- **non_goals:**
  - changing any runtime file. Lanes and bridges only; the runtime is the merged v3 candidate;
  - a semantic-off control row. That would be the v2 control by construction.
- **exclusions:**
  - no temporal metadata;
  - no ranking variant;
  - no answer generation;
  - no change to `-v1` or `-v2` lanes or evidence.

## Open Questions

None blocking.
