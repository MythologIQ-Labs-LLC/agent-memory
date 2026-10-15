# Agent Memory on the independent AMB harness: PrecisionMemBench single-turn (local execution, 2026-10-15)

Agent Memory was run as a memory provider inside the upstream
[Agent Memory Benchmark](https://github.com/vectorize-io/agent-memory-benchmark) (AMB), at a
frozen revision, on the full PrecisionMemBench `single-turn` split in AMB's `retrieval` mode.
AMB loads the dataset, drives ingestion and queries, and scores with its own code. No LLM is
involved anywhere in this mode, and no inference API was called.

This is a self-run result. It is **not** an official AMB leaderboard entry, and nothing here
claims one. An official entry exists only once the AMB maintainers accept and publish it.

## Result (AMB native metrics)

| Run | Cases executed | Errors | Correct (AMB accuracy) | Active passes | Structural passes | Trivially-empty passes | Mean precision | Mean recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `agent-memory` (rep 1) | 77 / 77 | 0 | **15 / 77 (19.5%)** | 4 / 43 | 6 / 25 | 5 / 9 | 0.1806 | 0.9535 |
| `agent-memory` (rep 2) | 77 / 77 | 0 | 15 / 77 (19.5%) | 4 / 43 | 6 / 25 | 5 / 9 | 0.1806 | 0.9535 |
| `bm25` (AMB built-in baseline, same run conditions) | 77 / 77 | 0 | 8 / 77 (10.4%) | 0 / 43 | 5 / 25 | 3 / 9 | 0.0536 | 0.9651 |

"Correct" means the case passed every one of its must-include and must-exclude assertions under
AMB's `PrecisionMemBenchDataset.score_retrieval`. "Errors" means harness or provider exceptions:
none occurred. The 62 failed Agent Memory cases are scored failures, and each failure reason is
in `case-outcomes-agent-memory.csv` (`judge_reason`). The dominant reason is extra beliefs in
`relevantBeliefs`: recall is high (0.95), precision is low (0.18). Four cases have a blank
query, and AMB answers them with an empty retrieval without calling the provider
(`edge-empty-query`, `edge-whitespace-query`, `narrator-voice-pinned-in-own-scope`,
`recency-tiebreak-reinforcement`).

Per category, Agent Memory passed: Alias resolution 3/23, Fuzzy matching and prefix guards 3/7,
Budget eviction and capacity 3/5, Design boundary cases 2/6, Cross-user isolation 1/1, Persona
prelude content 1/4, Ranking stability 1/3, Cold start behavior 1/1. It passed nothing in Scope
disambiguation 0/12, Type routing and open questions 0/6, Relation expansion 0/4, Supersession
chain exclusion 0/3, or Counter-signal retrieval 0/2.

### Latency and memory

| Run | Ingest 35 docs | Retrieve p50 | Retrieve p95 | Retrieve max | Wall time (whole CLI) | Peak RSS (whole CLI process) |
|---|---:|---:|---:|---:|---:|---:|
| `agent-memory` rep 1 | 277 ms | 22.7 ms | 25.5 ms | 41.8 ms | 9.6 s | 1321 MiB |
| `agent-memory` rep 2 | 277 ms | 22.5 ms | 25.6 ms | 26.8 ms | 9.0 s | 1321 MiB |
| `bm25` | 269 ms | 3.1 ms | 4.7 ms | 5.9 ms | 7.7 s | 1315 MiB |

Retrieve times are AMB's own `retrieve_time_ms`, measured over the 73 non-blank queries. Peak
RSS is `ru_maxrss` of the single process running the AMB CLI. It is dominated by AMB importing
every provider's dependencies (torch, sentence-transformers and others), so the Agent Memory
increment over the BM25 run is about 6 MiB. The scored Agent Memory runtime store is 668 KiB on
disk (`full-agent-memory-rep1/.../_store`). Host: 4 vCPU, 15 GiB RAM, Linux x86_64, CPython
3.12.3.

## Comparison with published AMB results

The AMB checkout publishes exactly one result for this dataset, split and mode
(`results-manifest.json`, `outputs/precisionmembench/hindsight/retrieval/single-turn.json.gz`):
**Hindsight (`hindsight-cloud`, Hindsight 0.10.0): 66/77 (85.7%), active 33/43, precision 0.8481,
recall 1.0.** The harness revision, dataset fixtures, split, mode and scorer
(`src/memory_bench/dataset/precisionmembench.py`, unchanged since that run was published in
`50b30a7`) are the same, so the scores are directly comparable. The providers differ in two
ways, both inside the protocol:

- Hindsight declares `supports_filters = True`, so it receives the dataset's structured
  `retrieval_filter`. Agent Memory's bridge declares `supports_filters = False` and receives
  only the query text.
- Hindsight runs an extraction LLM at ingestion. Agent Memory runs none.

On this protocol, Agent Memory scores **15/77 against Hindsight's 66/77**: well below the one
published entry, and above AMB's BM25 baseline.

AMB's `external_results.json` also lists PrecisionMemBench numbers for other systems. AMB itself
labels them "PrecisionMemBench baselines (tenurehq) — unverified", and they came from the
upstream PrecisionMemBench harness, not AMB. They are not protocol-equivalent and are not
compared here. Its `agentmemory` row is a different product, not this repository.

## What was changed to run, and why scoring is unaffected

The frozen CLI builds three LLM clients even in retrieval mode, and refuses to start without
`GEMINI_API_KEY` and `GROQ_API_KEY`. `reference/amb_retrieval_no_llm.py` replaces only those
three construction points with objects that refuse every use:
`cli._resolve_gemini_key`, `cli.get_answer_llm` and `runner.GeminiJudge`. It is applied at
runtime by `reference/run_amb_external.py`, and the AMB checkout is not modified. To show that
scoring is unchanged, both providers were also run through the **unmodified** CLI path
(`--no-retrieval-guard`) with inert placeholder keys, which satisfy client construction and are
never used. `comparisons/` holds the case-by-case results from `scripts/compare_amb_runs.py`,
which compares every result and summary field except wall-clock timings:

| Comparison | Cases | Differences |
|---|---:|---:|
| guarded vs unmodified CLI, `agent-memory` (raw provider responses included) | 77 | 0 |
| guarded vs unmodified CLI, `bm25` | 77 | 0 |
| `agent-memory` rep 1 vs rep 2 | 77 | 0 |
| earlier hosted-CI run (lane v6, Agent Memory `24048d5`) vs this run, `agent-memory`, `raw_response` excluded | 77 | 0 |
| earlier hosted-CI run vs this run, `bm25` | 77 | 0 |
| negative control: `agent-memory` vs `bm25` (the comparator must detect differences) | 77 | 343 |

A second environment fix: AMB counts context tokens with `tiktoken` `cl100k_base`, which it
downloads from `openaipublic.blob.core.windows.net`. That host was blocked here (HTTP 403 from
the egress proxy). The byte-identical encoding file ships inside `litellm`, which is installed
from AMB's own `uv.lock`. Its sha256 `223921b7…65b2a7` equals tiktoken's pinned
`expected_hash`, and tiktoken checks that hash when it loads the file. A copy of it was supplied
through `TIKTOKEN_CACHE_DIR`.

## Identity

| Item | Value |
|---|---|
| Agent Memory revision | `b9a9307484f4bc4312203c9dc54b951002e3ee90` (clean worktree at every run) |
| AMB revision | `03c1d0f1d27da63034f0931121c858faba512383` (clean) |
| Bridge | `reference/amb_agent_memory_bridge.py` 0.4.0, blob `3d9ccb3`; guard blob `2273248` |
| AMB scorer blobs | `precisionmembench.py` `47432e9`, `modes/retrieval.py` `416dd4d`, `runner.py` `190bb2b` |
| Dataset | tenurehq/precisionmembench @ `b95d6ab`; `beliefs.seed.json` sha256 `35659b3b…`, `retrieval.cases.json` sha256 `09e99f08…` (equal to the pins in `reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v6.json`) |
| Environment | AMB `uv.lock` (sha256 `de4408d1…`) exported to 295 pip constraints (`amb-constraints.txt`, sha256 `8a7f4b9b…`); only this repository's own pins (`cryptography`, `jsonschema`, `rfc8785`) are lifted; installed with `uv pip`; full distribution list in each `execution-identity.json` |
| Credentials in the child process | none (`credentials_present_in_child: []`), except the two inert placeholders in the `stock-cli-*` runs |
| Runner | local container, not hosted CI |

Each run directory holds `execution-identity.json` (command, exit code, wall time, peak RSS,
revisions, scorer blobs, fixture digests, installed distributions, sha256 of every AMB output),
`stdout.txt`, `stderr.txt`, and AMB's own result file at
`amb-outputs/precisionmembench/<provider>/retrieval/single-turn.json`, with every case's raw
outcome. `sha256.txt` covers every file in this directory.

## Reproduce

```bash
git clone https://github.com/vectorize-io/agent-memory-benchmark /tmp/agent-memory-benchmark
git -C /tmp/agent-memory-benchmark checkout 03c1d0f1d27da63034f0931121c858faba512383
python scripts/amb_harness_constraints.py --amb-root /tmp/agent-memory-benchmark --memory agent-memory \
  --output /tmp/amb-constraints.txt --provenance /tmp/amb-constraints-provenance.json
uv venv -p python3.12 /tmp/amb-venv
VIRTUAL_ENV=/tmp/amb-venv uv pip install -c /tmp/amb-constraints.txt -e . -e /tmp/agent-memory-benchmark
# only if openaipublic.blob.core.windows.net is unreachable:
mkdir -p /tmp/tiktoken-cache && cp /tmp/amb-venv/lib/python3.12/site-packages/litellm/litellm_core_utils/tokenizers/9b5ad71b2ce5302211f9c61530b329a4922fc6a4 /tmp/tiktoken-cache/

# smoke (as requested): 5 queries
TIKTOKEN_CACHE_DIR=/tmp/tiktoken-cache /tmp/amb-venv/bin/python reference/run_amb_external.py \
  --amb-root /tmp/agent-memory-benchmark -- run --dataset precisionmembench --split single-turn \
  --memory agent-memory --mode retrieval --query-limit 5

# full split, with the evidence bundle
python scripts/run_amb_local_evidence.py --amb-root /tmp/agent-memory-benchmark --python /tmp/amb-venv/bin/python \
  --evidence-dir /tmp/evidence/full-agent-memory --set-env TIKTOKEN_CACHE_DIR=/tmp/tiktoken-cache \
  -- run --dataset precisionmembench --split single-turn --memory agent-memory --mode retrieval

# tests against the real AMB package
AMB_ROOT=/tmp/agent-memory-benchmark TIKTOKEN_CACHE_DIR=/tmp/tiktoken-cache \
  /tmp/amb-venv/bin/python -m unittest discover -s reference/tests -t reference -p 'test_amb_*.py'
```
