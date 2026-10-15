# AMB PrecisionMemBench single-turn, retrieval mode: Hindsight local added (cycle 2, candidate)

This is candidate evidence. It has not been independently reviewed or accepted, and it is not an official AMB leaderboard entry.

**Setup.** AMB is at `03c1d0f` with fixtures `35659b3b`/`09e99f08`. All 77 cases were run with no LLM. The tooling comes from PR #818 `1df28f8` unchanged, plus one provider registration. Runs were local on 4 vCPU with no GPU.

## Protocol tier A: query-only providers (`supports_filters = False`)

| System | Configuration | Correct | Active | Mean precision | Mean recall | Retrieve avg | Context tokens | Evidence |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Agent Memory | runtime `7c06468`-equivalent (this branch's runtime is unchanged), bridge `3d9ccb3` | 15 | 4 | 0.1806 | 0.9535 | 84.8 ms | 542 | `am-amb-control` (0 case differences from the reproduced #819 baseline) |
| Mem0 OSS 2.2.1 explicit (infer=False) | accepted lane `amb-precisionmembench-retrieval-v6` | 10 | 0 | 0.1049 | 1.0000 | — | — | accepted, `reports/benchmarks/amb/…-v6/mem0-explicit-24048d55e26d` |
| **Hindsight OSS 0.10.2, chunks, no LLM** | `hindsight-chunks-local` (this cycle) | **9** | 0 | 0.0552 | 0.9884 | 98.5 ms | 300 | `hs-amb-rep1`, `hs-amb-rep2` |
| BM25 (AMB built-in baseline) | | 8 | 0 | 0.0536 | 0.9651 | 11.4 ms | 926 | `bm25-amb-control` (0 differences) |

- **Hindsight configuration.** The setup is the #751 H3 posture: pinned checkout `5fc4ce2`, `llm_provider=none`, embedded PostgreSQL, ONNX `intfloat/multilingual-e5-small@03415a4` (graph SHA-256 `ca456c06…`, verified), and reranker `rrf`. Each bank is created fresh with `retain_extraction_mode=chunks` and observations, temporal and graph retrieval and reranking all off, and is verified through `get_bank_config` (config SHA-256 `36320167…`). Each document is retained once under the id `sha256(id)`. Recall uses `max_tokens=65536` and budget `mid`, projected to AMB's k.
- **Repetition.** Rep 1 and rep 2 give identical pass/fail on all 77 cases, with identical relevant-belief sets and metrics. In 19 cases the order of tied results differs, and no score changes.
- **Reading this table.** In this tier Agent Memory leads: 15 correct against 10 for Mem0, 9 for Hindsight and 8 for BM25. All four reach high recall, at 0.95 or above, but precision is low for every system. Hindsight's no-LLM chunk mode returns about the full k for every query, because dense similarity has no relevance floor. That is the same failure class #819 diagnosed for Agent Memory, but stronger.

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
