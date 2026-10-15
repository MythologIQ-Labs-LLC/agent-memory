# AMB PrecisionMemBench single-turn, retrieval mode: Hindsight, Letta and Cognee local added (cycle 2, candidate)

This is candidate evidence. It has not been independently reviewed or accepted, and it is not an official AMB leaderboard entry.

**Setup.** AMB is at `03c1d0f` with fixtures `35659b3b`/`09e99f08`. All 77 cases were run with no LLM. The tooling comes from PR #818 `1df28f8` unchanged, plus one provider registration. Runs were local on 4 vCPU with no GPU.

## Protocol tier A: query-only providers (`supports_filters = False`)

**Input asymmetry, disclosed after the #810 independent review (`8887bbe`, finding 2).** Agent Memory's AMB bridge (`reference/amb_agent_memory_bridge.py`) passes each document's timestamp as `observed_at`. The Hindsight, Letta and Cognee providers on this branch receive no timestamps: the service provider forwards them, but neither service uses them, and the Hindsight provider retains without one. So "same inputs" is not exact. Agent Memory's whole AMB lead is in alias and fuzzy-matching cases, and supersession is 0/3 for every system, so this is unlikely to drive the result. It is still an input difference.


| System | Configuration | Correct | Active | Mean precision | Mean recall | Retrieve avg | Context tokens | Evidence |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Agent Memory | runtime `7c06468`-equivalent (this branch's runtime is unchanged), bridge `3d9ccb3` | 15 | 4 | 0.1806 | 0.9535 | 84.8 ms | 542 | `am-amb-control` (0 case differences from the reproduced #819 baseline) |
| Mem0 OSS 2.2.1 explicit (infer=False) | accepted lane `amb-precisionmembench-retrieval-v6` | 10 | 0 | 0.1049 | 1.0000 | — | — | accepted, `reports/benchmarks/amb/…-v6/mem0-explicit-24048d55e26d` |
| **Hindsight OSS 0.10.2, chunks, no LLM** | `hindsight-chunks-local` (this cycle) | **9** | 0 | 0.0552 | 0.9884 | 98.5 ms | 300 | `hs-amb-rep1`, `hs-amb-rep2` |
| **Letta 0.16.8 archival memory, no LLM** | `letta-local` service (this cycle) | **9** | 0 | 0.0552 | 0.9884 | 369.4 ms | 301 | `letta-amb-rep1`, `letta-amb-rep2` |
| **Cognee 1.6.4 local GLiNER, no LLM** | `cognee-local` service (this cycle) | **9** | 0 | 0.0552 | 0.9884 | 436 ms / 1,764 ms* | 301 | `cognee-amb-rep1`, `cognee-amb-rep2` |
| BM25 (AMB built-in baseline) | | 8 | 0 | 0.0536 | 0.9651 | 11.4 ms | 926 | `bm25-amb-control` (0 differences) |

- **Hindsight configuration.** The setup is the #751 H3 posture: pinned checkout `5fc4ce2`, `llm_provider=none`, embedded PostgreSQL, ONNX `intfloat/multilingual-e5-small@03415a4` (graph SHA-256 `ca456c06…`, verified), and reranker `rrf`. Each bank is created fresh with `retain_extraction_mode=chunks` and observations, temporal and graph retrieval and reranking all off, and is verified through `get_bank_config` (config SHA-256 `36320167…`). Each document is retained once under the id `sha256(id)`. Recall uses `max_tokens=65536` and budget `mid`, projected to AMB's k.
- **Repetition.** Rep 1 and rep 2 give identical pass/fail on all 77 cases, with identical relevant-belief sets and metrics. In 19 cases the order of tied results differs, and no score changes.
- **Reading this table.** In this tier Agent Memory leads: 15 correct against 10 for Mem0, 9 for Hindsight and 8 for BM25. All four reach high recall, at 0.95 or above, but precision is low for every system. Hindsight's no-LLM chunk mode returns about the full k for every query, because dense similarity has no relevance floor. That is the same failure class #819 diagnosed for Agent Memory, but stronger.

- **Letta configuration.**
  - The server is Letta 0.16.8, the last PyPI release that ships the server, at tag `1131535`. Later `letta` releases on PyPI are the Letta Code CLI. Dependencies were resolved with `--exclude-newer 2026-05-15`, the release date, because unbounded resolution drifted (`mcp` and `pydantic` became incompatible). The freeze is `letta-venv-freeze.txt`.
  - The 0.16.8 server needs Postgres: its async engine ignores SQLite. The database is PostgreSQL 18.1 with pgvector 0.8.5 on loopback, initialised with Letta's own `init.sql` and `alembic upgrade head` (revision `1c28e167b74f`). Redis is off.
  - Embeddings come from `reference/local_embedding_server.py`. It is an OpenAI-compatible loopback endpoint serving fastembed `BAAI/bge-small-en-v1.5` (ONNX `qdrant/bge-small-en-v1.5-onnx-q@aa8f8b06`, SHA-256 `51f1bd0a…`), the same model the LangMem service uses. Its vectors are byte-identical to direct fastembed output.
  - The provider is `letta-local` in `reference/competitor_service.py`, which calls Letta's REST API. It creates one agent per AMB user, makes one `create_passage` call per document, and retrieves with Letta's own `search_archival_memory` (pgvector cosine) at `top_k=k`. Provenance is the passage id returned at insert.
  - No tags, date filters or LLM are used. The agent's required `llm_config` points at a closed port and is never called. The database holds exactly 35 passages for 35 documents.
  - This measures Letta's archival retrieval, not its self-editing agent memory.
- **Letta repetition.** Rep 1 and rep 2 are identical, including result order, on all 77 cases.
- **Letta compared with Hindsight.** The two pass exactly the same 9 cases: 6 structural and 3 trivially empty, with 0 active passes. Their returned sets differ in 71 of 77 cases. Both are pure dense retrieval with no relevance floor, so precision is decided by k rather than by the system.

- **Cognee configuration.** Cognee 1.6.4 `f154b32`, `cognee[gliner]`, documented no-LLM mode: local GLiNER graph extraction and local fastembed `BAAI/bge-small-en-v1.5` embeddings. It runs through `reference/competitor_service.py` (`cognee-local`), with one dataset per AMB user and `remember(DataItem(text, data_id=uuid5, literal_text=True))`. Retrieval uses `recall(query, datasets=[user], top_k=k)`. Every prepare runs `prune_data` and `prune_system(metadata=True)`. Ingestion is about 23 to 33 minutes for 35 documents on a contended CPU, dominated by GLiNER.
- **Cognee repetition.** Rep 1 and rep 2 are identical on all 77 cases, including result order. \*Rep 2's retrieve latency was taken while a second Cognee job shared its CPU core. Neither latency is a performance measurement.
- **Same embedder, near-identical results.** Cognee's local mode embeds with fastembed `bge-small-en-v1.5`, and Letta was configured with the same model through the loopback endpoint, because Letta has no bundled local embedder. Their returned sets differ in only 2 of 77 cases, and their pass sets are identical. In this retrieval-only, query-only tier these two products are largely measuring their shared embedding model, not their memory architectures. Hindsight uses `multilingual-e5-small` and differs in 71 cases, yet passes the same 9.

## Protocol tier B: AMB's native Hindsight provider with structured filters. INVALID, typed blocker

AMB's own `hindsight-http` provider was run against the same local server, as `hs-native-filtered-rep1/2`. It declares `supports_filters = True`, and it filters recall on tags that Hindsight's extraction LLM assigns during ingestion. With `llm_provider=none`, no tags are ever assigned, so **every one of the 77 recalls returned nothing**. The run reports "34 correct" only because those cases pass when nothing is returned; precision, recall and active passes are all 0.

**This is not a valid score and must not be reported as one.** The provider also always applies a PrecisionMemBench-specific retain mission, which is inert here because no LLM runs. The blocker is that the filtered tier needs a structured-output ingestion LLM. Hindsight cloud's published 66/77 uses exactly that combination: an LLM at ingestion plus structured filters. It therefore measures a different capability tier from every row above.

## Reproduce

Start the server as an unprivileged user:

```bash
python reference/hindsight_local_server.py --source-dir <hindsight@5fc4ce2> --model-dir <e5-small snapshot> --url-file server.json
```

Then run the recorder:

```bash
python scripts/run_amb_local_evidence.py --amb-root <amb@03c1d0f> --python <amb venv> --evidence-dir out \
  --set-env TIKTOKEN_CACHE_DIR=… --set-env HF_HUB_OFFLINE=1 \
  --set-env AGENT_MEMORY_HINDSIGHT_URL_FILE=server.json \
  --set-env AGENT_MEMORY_HINDSIGHT_CLIENT_DIR=<hindsight>/hindsight-clients/python \
  --set-env PYTHONPATH=<hindsight>/hindsight-clients/python \
  -- run --dataset precisionmembench --split single-turn --memory hindsight-chunks-local --mode retrieval
```
