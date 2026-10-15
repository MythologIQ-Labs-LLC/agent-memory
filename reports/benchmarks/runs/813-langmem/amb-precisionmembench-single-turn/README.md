# LangMem on AMB PrecisionMemBench single-turn (all 77 cases): 9/77, LLM-at-ingestion tier

**Status: candidate.** This result is self-run and unreviewed; it is not an accepted result and
not an official AMB entry. It was preregistered before execution (`PREREGISTRATION.md`, pushed
in `26cabc7`). Two earlier attempts are recorded in `aborted-attempt*/`. One was stopped by the
executor's tool time limit and one by a container restart; neither scored any case.

## Result (AMB native scoring)

| Item | Value |
|---|---|
| Correct | **9/77** |
| Active / structural / trivially-empty passes | 0/43 / 6/25 / 3/9 |
| Mean precision | 0.017 |
| Mean recall | 0.093 |
| Mean memories returned | 5.5 |
| Paired vs Agent Memory 15/77 | +0 / −6, exact McNemar p = 0.031 |
| Per category | `paired-vs-cohort.json` |

This row belongs to the **LLM-at-ingestion tier**, alongside Graphiti. It is not ranked with the
no-LLM rows: Agent Memory 15, Mem0 10, MemPalace 9, Hindsight 9, BM25 8.

## What happened

- **Very few memories were stored.** With the local Qwen2.5-3B, LangMem's manager created or
  changed a memory for only **7 of 35** documents, and the user's store ended with **4
  memories**. Of the 35 calls, 7 returned no tool call. Of the 28 that returned tool calls, most
  changed nothing (21 of 23 PatchDoc calls were no-ops, per independent review).
- **Ingestion varies from run to run, even at temperature 0.** The two aborted attempts changed
  memories on different documents than run 1: attempt 2 changed 10 of its first 19. The model
  server was shared with the concurrent Graphiti run, and no second complete run exists. So "7 of
  35" is a single draw, not a stable property. *(Disclosed after independent review.)*
- **The attribution rule cuts both ways.** Every document whose ingestion changed a memory is
  credited to that memory. That can inflate recall and deflate precision. "Mean memories
  returned" counts attributed documents, not distinct memories.
- **Recall and precision follow from that.** Most beliefs are not retrievable (recall 0.09).
  What is returned maps through a few broad memories, each attributed to several documents, so
  failures include unexpected beliefs (precision 0.02).
- **This is LangMem plus this model.** It shows how LangMem behaves with a small local model. It
  says nothing about LangMem with its documented hosted models, which were not authorised here.
- **The smoke shows the same system can apply corrections.** In `../smoke/`, LangMem rewrote a
  superseded memory. In this run's data, consolidation dominates instead.

## Corroboration from another lane

A separate session, on `claude/810-competitive-cycle2-no-ci` at `692e185` in `COVERAGE.md`, ran
one LangMem `create_memory_store_manager` call with the same class of local 3B model. Given a
single clear fact, it wrote **0 memories**, with no LLM errors, and took 266 s. That lane
concluded that a full AMB run with this model measures the model's tool calling rather than
LangMem. This run agrees: it reached only 4 memories from 35 documents. **Recommendation: do not
admit this as a LangMem measurement.**

## Model usage

All inference was local; there was no paid inference.

| Item | Value |
|---|---|
| Chat calls | 35, all HTTP 200 |
| Calls that returned structured tool calls | 28 |
| Prompt tokens | 72,366 |
| Completion tokens | 4,422 |
| LLM wall time | about 5,390 s, sharing the LLM with the Graphiti run |
| Embedding requests | 150 |
| Full call log | `rep1/shim-calls.jsonl.gz` |

## Input asymmetry: timestamps

Agent Memory's reviewed AMB bridge passes each document's timestamp as `observed_at`
(`reference/amb_agent_memory_bridge.py`). This bridge, like the MemPalace, Hindsight and LangMem
bridges, passes no timestamp. Graphiti receives it as `reference_time`. "Same inputs" in the
cohort tables therefore means same documents, queries, budgets and scorer, **but not the same
timestamp metadata**. The difference is unlikely to explain the headline gap, because Agent
Memory's lead comes from Alias resolution and Fuzzy matching, not time-dependent categories.
It is still an input difference. *(Disclosed after independent review.)*

## Identity

| Item | Value |
|---|---|
| LangMem | 0.0.30 at `48e3c11f` (MIT) |
| Environment freeze | `../langmem-venv-freeze.txt` |
| Store | LangGraph `InMemoryStore` |
| LLM | Qwen2.5-3B Q4_K_M at `7dabda4d`, temperature 0, through `reference/llamacpp_hermes_tools_shim.py` |
| Embeddings | nomic-embed v1.5 at `0188c9bf` |
| Harness | AMB `03c1d0f`, launched with `AWS_*` unset; no credentials in the child |
| Run | exit 0, 5,768 s wall time, 1.05 GiB peak RSS for the whole CLI |
| Manifest | `rep1/manifest.json` (#808 v1) |
