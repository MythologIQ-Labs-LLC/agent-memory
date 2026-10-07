# Plan: #669 Step B evidence — `-v3` same-harness lanes for Runtime Baseline v3

**change_class**: evaluation
**doc_tier**: standard
**risk_grade**: L2
**parent plan**: docs/plan-669-semantic-vector-route.md (Gate PASS at Entry #87; Step A merged as `aede8fd`; `main` prints TRANSITION to v3)
**precedent**: docs/plan-640-lanes-v2-return-budget.md (LD1, LD5, LD6, LD7)
**owner rulings in force**: `decision-temporal-posture` (lanes receive only question and item text), `decision-embedding-dependency`
**iteration**: 2 (attempt-1 VETO grounds 1-5 and advisories addressed; see "Iteration 2 design" — supersedes L1-L6 where they conflict)

## Purpose

`reports/runtime/baseline-v3-declaration.json` names `longmemeval-s-retrieval-parity-v3` and `amb-precisionmembench-retrieval-v3` as the acceptance evidence for publishing v3. #669's gate requires two things:

- turn-plane recall_all@50 and session recall_all@5 must **move** on LongMemEval_S;
- the AMB active passes must **not regress**;
- in both lanes, the Mem0 row is re-run for parity.

These lanes are frozen before any score. Iteration 2 (below) supersedes iteration 1's control configuration.

## Iteration 2 design (gate attempt 1: VETO on five grounds)

Attempt 1 established a structural fact that changes the design (ground 4). Under policy 3.2.0, a candidate found only by the semantic route ranks after every lexical candidate. The v2 LongMemEval control admits at least 113 lexical candidates per turn question (median 211) and at least 33 per session question. With the scored k of 50 and 5, a semantic-only candidate therefore **cannot** enter the scored prefix, so the #669 gate ("turn recall_all@50 and session recall_all@5 must move") is unattainable under the subordinate policy by construction. On AMB the route would mostly fill empty or short responses. Those effects belong to fusion (#673), not to this tranche.

**D1 — The control rows run the shipped default.**
- In both `-v3` lanes the `agent_memory` control runs the v3 runtime with the facade default `semantic_retrieval: "off"`.
- Its configuration is identical to the `-v2` control (LongMemEval budget 50; AMB case budget).
- **Acceptance check:** every scored metric equals the accepted `-v2` control row's exactly. This makes "3.2.0 with the route off orders as 3.1.2" an observed fact on both external benchmarks (the attempt-1 advisory). Any difference is a blocker for v3 publication.

**D2 — A measured semantic row on LongMemEval only: `agent_memory_semantic`.**
- `semantic_retrieval: "required"`, otherwise the control's configuration.
- `configuration.semantic_representation` (the control row's open configuration object, ground 3) pins `representation_ref`, `representation_version`, `config_digest` `sha256:7447705443160d1ae7c1de49902b786bd3f578d06e7125c05dabaed52dd31aee`, `dimensions` 384, `minimum_similarity` 0.30 and `candidate_limit` 16.
- The importer requires the recorded `semantic_retrieval_posture()` to equal this block field for field.
- **Pre-registered prediction (frozen before any score):**
  - turn recall_all@50 and session recall_all@5 equal the D1 control, or differ only by tie reordering;
  - "move" means a strict increase on the same 419 scored questions.
- **Route diagnostics** recorded per question:
  - the semantic-only admitted count;
  - gold items found only by the semantic route;
  - each gold item's rank in the full admitted list.

  These diagnostics are the evidence #673 needs.
- The row is evidence for the route. It is not the v3 publication's control.

**D3 — No AMB semantic row in v3.**
- AMB installs under its own lock (onnxruntime 1.22.1, tokenizers 0.22.2, numpy 2.4.3, protobuf 5.29.6, packaging 24.2), which conflicts with the pinned `semantic` numerics (ground 1).
- Lifting those pins would change the representation identity and AMB's environment.
- The AMB `-v3` lane therefore runs `agent-memory` (D1 control, off), `bm25` and `mem0-explicit` (the frozen row key). It records `agent_memory_semantic` as `not_run`, with the lock conflict stated.
- Since the bridge is unchanged, ground 2 (no AMB evidence channel for the mode) does not arise. The bridge stays at 0.2.0, and the AMB `-v3` lane re-pins nothing on the bridge.

**D4 — The #669 gate disposition, pre-registered.**
- The "must move" gate is recorded as **not attainable under policy 3.2.0** and transfers to #673 (fusion), together with D2's diagnostics and the default-on question.
- #669 closes when v3 is published (Step B1/B2) with D1 accepted and D2 measured.
- An unmet gate is never answered by re-freezing or re-configuring this lane.

**D5 — The complete re-pin list (ground 5).** In each `-v3` lane file relative to `-v2`:
- `lane_id`, `status: frozen`, `frozen_on`, `owning_issue: 669`, `description`, `freeze_rationale` and `not_comparable_to`;
- `harness.source_blobs` for the runner (LongMemEval; the AMB bridge blob is unchanged);
- `evaluator.scorer` (it names the runner blob);
- `adapter.revision_rule` strings that name runner blobs;
- the lexical/baseline rows' `source.revision`, to the executing revision rule;
- `budget.forbidden_overrides`, which gains "`--agent-memory-semantic-retrieval` only on `agent_memory_semantic`; `auto` refused";
- `execution.environment` (the semantic install and model fetch for the D2 row only);
- `execution_identity_requirements`, which gains the semantic posture for D2;
- `configuration.runtime_baseline_posture`, pinning the v3 declaration blob and its TRANSITION line.

The v2 rule "control scored metrics equal the previous lane's" is kept for D1 (now relative to `-v2`) and does not apply to D2.

Added checks:
- the lexical/bm25 rows must equal `-v2` exactly (the ranker is unchanged);
- the Mem0 rows are expected to equal `-v2` (same pins), and any difference is recorded as an environment finding.

The test is field-for-field equality to `-v2` except exactly the D5 list.

**D6 — Runner, importer and workflow details.**
- `run_longmemeval.py`:
  - refuses `--agent-memory-semantic-retrieval` for any backend other than `agent_memory`, and refuses `auto`;
  - emits D2's per-question route diagnostics only when the mode is `required`.
- The `longmemeval-competitive.yml` backend choice gains `agent_memory_semantic`, which maps to `--backend agent_memory --agent-memory-semantic-retrieval required`. Only that row installs `reference/requirements-semantic.txt`, restores and fetches the pinned model, and sets `AGENT_MEMORY_REPRESENTATION_DIR`.
- Both workflows' `lane_id` default becomes `-v3`.
- Timeout: the measured cost is about 175 ms per 512-token embed. The session plane, about 23.9k sessions embedded once into the per-question derived store, could take about 70 minutes, so the LongMemEval job timeout is checked against the policy file and raised together with the policy and inventory if it is below 180 minutes.
- **Re-dispatch:** a row may be re-dispatched only after an infrastructure failure that occurred before any score was produced, with identical inputs (plan-640 LD7).
- The importer's `RUNNER_CONFIGURATION_DEFAULTS` gains `semantic_retrieval: off`.
- The CLI lane-list test covers six lanes: four accepted (v1, v2) and two frozen (v3).
- Docs/67 Step B1 also requires the public gauntlet probe, which is out of this plan's scope and done at B1.

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
