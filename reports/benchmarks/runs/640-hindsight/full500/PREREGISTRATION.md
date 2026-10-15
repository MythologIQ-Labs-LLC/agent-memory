# Hindsight chunk-only retrieval: full 500-question LongMemEval-S (#640, #810)

**Status: preregistered before execution; candidate, not reviewed or accepted.**

Registered 2026-10-15T13:15:24Z, before any question of this generation ran. `preregistration.json`
was written by `reference/run_longmemeval_resumable.py --preregister-only` and fixes:

- Input `longmemeval_s_cleaned.json`, sha256 `d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442` (500 source questions).
- Selection `all`: 500 questions in source order, ID-list sha256 `7d738ae585fd4014c9d231088ff824864fded501adc07b0e08c2b97a28210c03`. The frozen runner's own rules then exclude 30 abstention and 51 no-user-target questions from scoring.
- Planes `session` and `turn`; backend `hindsight_chunks_onnx` via `longmemeval_hindsight_bridge:install_longmemeval_hindsight_backend`.
- Evaluator: `reference/run_longmemeval.py` unchanged from `38f6a7d`; the resumable driver imports its selection, corpus construction and scoring.

## Configuration: identical to the 50-question generation (`../subset50/`)

| Item | Value |
|---|---|
| Product | Hindsight OSS `hindsight-all` 0.10.2, editable from pinned clean checkout `5fc4ce20917b916240cef27c212c387a177f115b` |
| Environment | `uv pip install --no-sources` under the recorded `subset50/hindsight-venv-freeze.txt`; resulting freeze is byte-identical to it (235 entries) |
| Server | in-process `HindsightServer(db_url="pg0", llm_provider="none", llm_api_key="")`, embedded PostgreSQL on loopback, run as an unprivileged user |
| Embeddings | local ONNX `intfloat/multilingual-e5-small` @ `03415a4be176a1620747c692ed433219fabc3def`, graph sha256 `ca456c06…8665`, snapshot manifest sha256 `4c0e50e7d52121bc5e3ce582959d09d2eaec203ec9c04634c0af9b166f59fd7f` (same as subset50) |
| Bank | `retain_extraction_mode=chunks`, observations off, temporal off, graph off, bank reranking off (reranker `rrf`), text search on; verified per bank before ingest |
| Recall | one recall per question, `budget=mid` (product default), `max_tokens=65536`, projected to the runner's 50-deep ranking |
| Isolation | fresh bank per question, deleted after recall |
| Credentials | none present; no LLM call is possible (`llm_provider=none`) |

## What this measures, and what it does not

This is Hindsight used as a **credential-free chunk retrieval memory**. Hindsight's product modes
that use an LLM are **not** exercised and are not represented by this result: LLM fact extraction
on retain, observations/consolidation, entity/graph retrieval, temporal retrieval, cross-encoder
reranking, and `reflect`. The published Hindsight LongMemEval figures and the AMB Hindsight entry
(66/77, with structured filters and LLM extraction) come from those modes and are a different
evidence family; do not pool them with this run.
