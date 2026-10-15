# Graphiti OSS on AMB PrecisionMemBench single-turn, all 77 cases (#812, #810)

**Status: preregistered before execution. This is a candidate result, not reviewed or accepted.**
`preregistration.json` holds every identity below. It was written at 2026-10-15T16:53:14Z, before
any PrecisionMemBench case was run against Graphiti. The only Graphiti execution before this point
was the synthetic smoke (`../smoke/`), which uses four hand-written documents and no benchmark
data.

## Why this protocol

Graphiti builds its memory with an LLM. Each `add_episode` extracts entities and facts,
deduplicates them, and sets validity and invalidation. A faithful local run therefore needs local
inference. On this host that costs minutes per episode.

- **PrecisionMemBench fits that budget.** It ingests 35 short beliefs once for all 77 cases.
- **LongMemEval-S does not.** It needs about 50 long sessions per question, which is out of reach
  here and is recorded as a blocker with measured per-episode cost.

PrecisionMemBench also exercises what Graphiti is designed for:
- supersession and currentness;
- scope;
- relation expansion;
- typed retrieval.

## Protocol (identical to the reviewed Agent Memory 15/77 and BM25 8/77 runs)

| Item | Value |
|---|---|
| Harness | AMB `03c1d0f1d27da63034f0931121c858faba512383`, `--dataset precisionmembench --split single-turn --mode retrieval`, all 77 cases |
| Scoring | AMB's own `PrecisionMemBenchDataset.score_retrieval`; the scoring and loading blobs are listed in the JSON |
| Fixtures | `beliefs.seed.json` `35659b3b…`, `retrieval.cases.json` `09e99f08…`, the same files the reviewed run used |
| Guard | `reference/amb_retrieval_no_llm.py` 1.0.0, unchanged from `1df28f8` |
| Evidence wrapper | `scripts/run_amb_local_evidence.py`, unchanged from `1df28f8` |
| Budget | AMB's per-case `retrieval_limit` (`maxBeliefs`, default 20) is passed as `num_results` |
| Filters | None. This is protocol A, the same as Agent Memory and BM25. Graphiti gets no `retrieval_filter` |

## System configuration

| Item | Value |
|---|---|
| Product | `graphiti-core[falkordblite]==0.31.1` (tag `v0.31.1`, commit `5961293865a5`, Apache-2.0) |
| Graph store | Embedded FalkorDB Lite (`falkordblite` 0.10.0), using a fresh database file per run |
| Local path | Graphiti's documented OpenAI-compatible path: `OpenAIGenericClient` with `json_schema` structured output, `OpenAIEmbedder` and `OpenAIRerankerClient`. These point at `reference/graphiti_llamacpp_shim.py`, which sits in front of llama-cpp-python 0.3.16 |
| LLM | Qwen2.5-3B-Instruct Q4_K_M at revision `7dabda4d`, sha256 `626b4a66…`. Context 16k, seed 0, **temperature 0**. Graphiti's default is 1.0; temperature 0 is declared here for reproducibility |
| Embedder | `nomic-embed-text` v1.5 f16 at revision `0188c9bf`, sha256 `f7af6f66…`, 768 dimensions. This is the model in Graphiti's own local example |
| Ingest | One `add_episode` per AMB document. The episode name is an opaque uuid5. The body is the document content verbatim, `reference_time` is the belief's `created_at`, and `group_id` is the user |
| Search | `Graphiti.search(query, group_ids=[user], num_results=k)`, Graphiti's default hybrid fact search (BM25 + cosine, RRF) |
| Mapping | Provenance only. A returned fact maps to its supporting episodes, and each episode maps to its AMB document. Each supporting episode yields one result document, and the list is cut to k |
| Withheld | Graphiti never receives belief ids, scope tags, context markers, gold or query categories |

## Runs, outcomes and failure rules

- **Run 1 is the result.** A full fresh rerun (run 2) is repeatability evidence if host time
  allows. It never replaces run 1.
- **Outcomes reported:**
  - AMB's native metrics: correct/77, pass classes, precision, recall and per-category passes;
  - a per-case comparison with the reviewed Agent Memory and BM25 outcomes, with exact McNemar;
  - ingestion cost, from the per-episode log and the shim's call, token and time log;
  - latency and peak RSS.
- **A provider or harness exception fails the run.** It is then reported as failed, not scored.
  There are no per-case retries.
- **The configuration is fixed.** Nothing changes after this registration. A change would make
  a new, separately registered generation.

## Comparability

This uses the same harness, inputs, budgets, scorer and protocol as Agent Memory's 15/77, but a
**different capability tier**: Graphiti uses an LLM at ingestion, Agent Memory and BM25 use none.
It is reported as its own profile row and is not ranked as same-tier. The result describes
Graphiti with a small local model. It does not describe Graphiti with a frontier LLM, and it
does not describe Zep's hosted product.
