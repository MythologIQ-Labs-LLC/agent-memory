# Letta 0.16.8 archival memory: LongMemEval-S full 500, both planes. Preregistration

Committed before any full-500 question runs. `preregistration.json` was written by the driver's `--preregister-only` at 2026-10-16T00:51:41.818037+00:00.

## Cohort and evaluator

- **Input:** `longmemeval_s_cleaned.json`, sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442`.
- **Selection:** all 500 questions, ids sha256 `7d738ae585fd4014c9d231088ff824864fded501adc07b0e08c2b97a28210c03`. This is identical to the reviewed Hindsight and MemPalace full-500 lane on `claude/810-external-exec-no-ci`.
- **Planes and depth:** session and turn, retrieval depth 50.
- **Evaluator:** frozen `reference/run_longmemeval.py`, blob `6b9c237380f1d527e564161c2dac7fe32ada0ef9`, driven by `reference/run_longmemeval_resumable.py`.
- **Exclusions:** the runner's own (abstention and no-user-target).

## System and adapter

- **System:** Letta 0.16.8 at tag `1131535`. The server runs in its own venv (freeze `../subset50/letta-venv-freeze.txt`, byte-identical) on PostgreSQL 18.1 + pgvector 0.8.5, with Letta `init.sql` and Alembic head `1c28e167b74f`. No Redis.
- **Embeddings:** loopback OpenAI-compatible endpoint (`reference/local_embedding_server.py`) serving fastembed `BAAI/bge-small-en-v1.5`. ONNX `qdrant/bge-small-en-v1.5-onnx-q@aa8f8b06`, sha256 `51f1bd0a…`, 384 dimensions.
- **Adapter:** `reference/longmemeval_letta_bridge.py` **0.1.1-candidate**, blob `2c719e1e6b85ae36b73ba08922dbfc7f338fa164`. Per question it:
  1. creates a fresh agent;
  2. makes one `create_passage` call per corpus item;
  3. runs `search_archival_memory` with `top_k=50`;
  4. deletes the agent **and its archive** through Letta's own API.

  Step 4 is the only change from 0.1.0, which the subset50 runs used. Ingestion and retrieval are unchanged. The change stops orphaned passages accumulating, which Letta otherwise keeps after an agent is deleted.
- **What is not used:** no LLM call, and no tags, dates or filters. This is the archival-memory component tier, **not** Letta's stateful agent.

## Host and operations

- **Host:** a 4-vCPU, 15 GiB cloud container, idle at launch apart from the Letta stack.
- **Restarts:** the container has restarted twice in the last hour. The resumable driver writes one row per completed question, so after a restart the stack is brought back with `letta_stack_up.sh` and the same command resumes. The README will record every restart and resume.
- **Postgres settings:** `max_wal_size` is capped at 256 MB. This is a disk-bound infrastructure setting with no effect on Letta's behaviour.

## Outcomes reported

- recall_all@5, @10 and @50 and ndcg_any@k per plane;
- failure counters, which must be 0 for any score to be reported;
- Letta ingestion refusals (oversize passages), counted and never split;
- paired comparison against the Agent Memory full-500 control and the Hindsight and MemPalace full-500 rows, on the common scored set: W/L/T, exact McNemar and a fixed-seed bootstrap CI;
- an **overlap check against the subset50 rows** (bridge 0.1.0) on the 50 shared questions. Metrics are expected to be identical; any difference will be reported.

## Stopping rule

None other than completion. No subset, plane or setting will be narrowed after launch. If the run cannot finish, partial rows are reported as incomplete, with no score.
