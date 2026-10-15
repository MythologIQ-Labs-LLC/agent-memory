# Agent Memory on the independent AMB harness: PrecisionMemBench single-turn (local execution, 2026-10-15)

Agent Memory was run as a memory provider inside the upstream
[Agent Memory Benchmark](https://github.com/vectorize-io/agent-memory-benchmark) (AMB), at a
frozen revision, on the full PrecisionMemBench `single-turn` split in AMB's `retrieval` mode.
AMB loads the dataset, drives ingestion and queries, and scores with its own code. No LLM is
involved anywhere in this mode, and no inference API was called. An independent review of the
adapter, evaluator identity, isolation, output integrity and failure handling is in
`independent-review.md`; how each finding was handled is listed under "Review" below.

This is a self-run result. It is **not** an official AMB leaderboard entry, and nothing here
claims one. An official entry exists only once the AMB maintainers accept and publish it.

## Result (AMB native metrics)

| Run | Cases executed | Errors | Correct (AMB accuracy) | Active passes | Structural passes | Trivially-empty passes | Mean precision | Mean recall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `agent-memory` (rep 1) | 77 / 77 | 0 | **15 / 77 (19.5%)** | 4 / 43 | 6 / 25 | 5 / 9 | 0.1806 | 0.9535 |
| `agent-memory` (rep 2) | 77 / 77 | 0 | 15 / 77 (19.5%) | 4 / 43 | 6 / 25 | 5 / 9 | 0.1806 | 0.9535 |
| `bm25` (AMB built-in baseline, same run conditions) | 77 / 77 | 0 | 8 / 77 (10.4%) | 0 / 43 | 5 / 25 | 3 / 9 | 0.0536 | 0.9651 |
| `agent-memory` smoke (`--query-limit 5`) | 5 / 5 | 0 | 1 / 5 | 1 / 4 | 0 / 1 | 0 / 0 | 0.4111 | 1.0 |

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
chain exclusion 0/3, or Counter-signal retrieval 0/2. The cross-user isolation case is a weak
test: BM25 passes it too, and it passes even while unrelated beliefs are returned (see the
review).

### Latency and memory

| Run | Ingest 35 docs | Retrieve p50 | Retrieve p95 | Retrieve max | Wall time (whole CLI) | Peak RSS (whole CLI process) |
|---|---:|---:|---:|---:|---:|---:|
| `agent-memory` rep 1 | 319 ms | 22.7 ms | 26.5 ms | 30.1 ms | 10.4 s | 1322 MiB |
| `agent-memory` rep 2 | 296 ms | 23.3 ms | 26.0 ms | 34.9 ms | 11.2 s | 1322 MiB |
| `bm25` | 270 ms | 3.3 ms | 4.2 ms | 6.1 ms | 8.8 s | 1316 MiB |

Retrieve times are AMB's own `retrieve_time_ms`, measured over the 73 non-blank queries.
Percentiles are nearest-rank: the ⌈p·n⌉-th smallest value. Peak RSS is `ru_maxrss` of the
single process running the AMB CLI. It is dominated by AMB importing every provider's
dependencies (torch, sentence-transformers and others). The difference between providers is
within run-to-run noise, so this harness cannot measure Agent Memory's own footprint. The
scored Agent Memory runtime store is 668 KiB on disk (`full-agent-memory-rep1/.../_store`).
Host: 4 vCPU, 15 GiB RAM, Linux x86_64, CPython 3.12.3, not hosted CI. The host was also
running other local work at the time, so treat wall times as indicative.

## Comparison with published AMB results

The AMB checkout publishes exactly one result for this dataset, split and mode
(`results-manifest.json`, `outputs/precisionmembench/hindsight/retrieval/single-turn.json.gz`):
**Hindsight (`hindsight-cloud`, Hindsight 0.10.0): 66/77 (85.7%), active 33/43, precision 0.8481,
recall 1.0.** That result was published at AMB `50b30a7`. The scoring path
(`dataset/precisionmembench.py`, `modes/retrieval.py`, `runner.py`) is byte-identical between
`50b30a7` and the frozen `03c1d0f` used here, and the fixtures, split and mode are the same. The
protocol is therefore the same, but the providers receive different inputs:

- Hindsight declares `supports_filters = True`, so it receives the dataset's structured
  `retrieval_filter`. Agent Memory's bridge declares `supports_filters = False` and receives
  only the query text.
- Hindsight runs an extraction LLM at ingestion. Agent Memory runs none.

On this protocol, Agent Memory scores **15/77 against Hindsight's 66/77**: far below the one
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
runtime by `reference/run_amb_external.py`, and the AMB checkout is not modified. For
`task_type == "retrieval"` the runner scores with `score_retrieval` and never reads the judge,
so any judge use would raise rather than score.

To check this empirically, both providers were also run through the **unmodified** CLI path
(`--no-retrieval-guard`) with inert placeholder keys, which satisfy client construction and are
never used. `comparisons/` holds the case-by-case results from `scripts/compare_amb_runs.py`. It
compares every result and summary field except wall-clock timings and `run_name`; a missing key
counts as a difference, and duplicate `query_id`s are reported. AMB writes
`raw_response: null` for every case, so provider raw responses are not part of any comparison.

| Comparison | Cases (left / right) | Differences |
|---|---:|---:|
| guarded vs unmodified CLI, `agent-memory` | 77 / 77 | 0 |
| guarded vs unmodified CLI, `bm25` | 77 / 77 | 0 |
| `agent-memory` rep 1 vs rep 2 | 77 / 77 | 0 |
| previous local run at `b9a9307` (git history of this directory) vs this run, `agent-memory` | 77 / 77 | 0 |
| earlier hosted-CI run (lane v6, Agent Memory `24048d5`) vs this run, `agent-memory` | 77 / 77 | 0 |
| earlier hosted-CI run vs this run, `bm25` | 77 / 77 | 0 |
| negative control: `agent-memory` vs `bm25` (the comparator must detect differences) | 77 / 77 | 343 |

Two environment adaptations were needed:

- **tiktoken encoding file.** AMB counts context tokens with `tiktoken` `cl100k_base`, which it
  downloads from `openaipublic.blob.core.windows.net`. That host was blocked here (HTTP 403 from
  the egress proxy). The byte-identical file ships inside `litellm`, which is installed from
  AMB's own `uv.lock`. Its sha256 `223921b7…65b2a7` equals tiktoken's pinned `expected_hash`,
  and tiktoken checks that hash when it loads the file. A copy was supplied through
  `TIKTOKEN_CACHE_DIR`.
- **`HF_HUB_OFFLINE=1`.** This was set so that no Hugging Face download could occur; nothing on
  this path needs one.

## Identity

| Item | Value |
|---|---|
| Agent Memory revision | `7c06468aae1aed0d2115c42f9588fbbe8417657e` (clean worktree at every run) |
| AMB revision | `03c1d0f1d27da63034f0931121c858faba512383`: clean (untracked files included), scorer blobs identical before and after each run |
| Bridge | `reference/amb_agent_memory_bridge.py` 0.4.0 (blob `3d9ccb3`); guard and runner blobs in each `execution-identity.json` |
| AMB scorer blobs | `precisionmembench.py` `47432e9`, `modes/retrieval.py` `416dd4d`, `runner.py` `190bb2b` |
| Dataset | tenurehq/precisionmembench @ `b95d6ab`, read from `<amb>/.datasets/precisionmembench`: `beliefs.seed.json` sha256 `35659b3b…`, `retrieval.cases.json` sha256 `09e99f08…` (equal to the pins in `reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v6.json`) |
| Environment | AMB `uv.lock` (sha256 `de4408d1…`) exported to 295 pip constraints (`amb-constraints.txt`, sha256 `8a7f4b9b…`). Only this repository's own pins (`cryptography`, `jsonschema`, `rfc8785`) are lifted. Installed with `uv pip`. The full distribution list is in each `execution-identity.json` |
| Child environment | No inference credentials, except the two inert placeholders in the `stock-cli-*` runs. No `AMB_*`, `OMB_*`, `PRECISIONMEMBENCH_*` or `AGENT_MEMORY_AMB_*` variables (`scoring_env_in_child: {}`) |

Each run directory holds:

- `execution-identity.json`: the command, exit code, wall time, peak RSS, revisions, scorer
  blobs, fixture digests, installed distributions, and the sha256 of every AMB output
- `stdout.txt` and `stderr.txt`
- AMB's own result file, with every case's raw outcome, at
  `amb-outputs/precisionmembench/<provider>/retrieval/single-turn.json`

`sha256.txt` covers every committed file in this directory. Only the scored run's runtime store
(`full-agent-memory-rep1/.../_store`) is committed. The other runs' stores are listed in their
`outputs_sha256` but were not kept, so those entries cannot be re-verified.

## Review

`independent-review.md` was written by a separate reviewing agent that re-ran both providers
and probed isolation and `k` against the real AMB package. Its verdicts were: adapter PASS,
evaluator identity PASS, isolation PASS, output integrity CONCERN (minor), failure handling
CONCERN. How each finding was handled:

| Finding | Resolution |
|---|---|
| The comparator treated a missing key as `None`, collapsed duplicate `query_id`s, and reported one side's count | Fixed in `b2ccbf5`, with tests (`reference/tests/test_compare_amb_runs.py`). All comparisons were re-run |
| p95 used an unstated, lowest-valued method | Now nearest-rank, and stated |
| "raw provider responses included" was vacuous | Removed: AMB stores `raw_response: null` |
| The 6 MiB RSS increment claim was within noise | Removed |
| Hindsight "same harness revision" was imprecise | Now: published at `50b30a7`, with a byte-identical scoring path |
| Scorer-affecting env vars were neither cleared nor recorded; fixtures were hashed from the default path only; the AMB dirty check ignored untracked files; scorer blobs were hashed only after the run | Fixed in `scripts/run_amb_local_evidence.py` (`b2ccbf5`). This bundle was produced with the fixed recorder |
| `requested_mode` read the first `--mode`, while Click uses the last | Fixed, with a test |
| `unittest discover` silently skips the pytest-style bridge tests | The reproduce section below uses pytest for that file. CI still runs `unittest` only, which is a pre-existing gap |
| The bridge silently drops returned facts missing from its index, recording them under a misnamed `unmapped_admitted` field | Not changed here. The bridge blob is pinned by the accepted same-harness lanes, so changing it needs a new lane. No such drop occurred in this run |
| Re-ingesting a document creates a second fact | Not applicable to single-ingest runs. Not changed |

## Reproduce

```bash
git clone https://github.com/vectorize-io/agent-memory-benchmark /tmp/agent-memory-benchmark
git -C /tmp/agent-memory-benchmark checkout 03c1d0f1d27da63034f0931121c858faba512383
python scripts/amb_harness_constraints.py --amb-root /tmp/agent-memory-benchmark --memory agent-memory \
  --output /tmp/amb-constraints.txt --provenance /tmp/amb-constraints-provenance.json
uv venv -p python3.12 /tmp/amb-venv
VIRTUAL_ENV=/tmp/amb-venv uv pip install -c /tmp/amb-constraints.txt -e . -e /tmp/agent-memory-benchmark pytest
# only if openaipublic.blob.core.windows.net is unreachable:
mkdir -p /tmp/tiktoken-cache && cp /tmp/amb-venv/lib/python3.12/site-packages/litellm/litellm_core_utils/tokenizers/9b5ad71b2ce5302211f9c61530b329a4922fc6a4 /tmp/tiktoken-cache/

# smoke (as requested): 5 queries
TIKTOKEN_CACHE_DIR=/tmp/tiktoken-cache /tmp/amb-venv/bin/python reference/run_amb_external.py \
  --amb-root /tmp/agent-memory-benchmark -- run --dataset precisionmembench --split single-turn \
  --memory agent-memory --mode retrieval --query-limit 5

# full split, with the evidence bundle
python scripts/run_amb_local_evidence.py --amb-root /tmp/agent-memory-benchmark --python /tmp/amb-venv/bin/python \
  --evidence-dir /tmp/evidence/full-agent-memory --set-env TIKTOKEN_CACHE_DIR=/tmp/tiktoken-cache --set-env HF_HUB_OFFLINE=1 \
  -- run --dataset precisionmembench --split single-turn --memory agent-memory --mode retrieval

# tests: real-AMB guard tests (unittest) and the pytest-style bridge tests
cd reference && AMB_ROOT=/tmp/agent-memory-benchmark TIKTOKEN_CACHE_DIR=/tmp/tiktoken-cache \
  /tmp/amb-venv/bin/python -m pytest -q tests/test_amb_retrieval_no_llm.py tests/test_amb_agent_memory_bridge.py \
  tests/test_compare_amb_runs.py tests/test_amb_harness_constraints.py
```
