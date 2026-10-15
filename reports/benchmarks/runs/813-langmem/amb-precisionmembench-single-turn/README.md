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
  memories**. On the other 7 of the 35 calls, the model answered without any tool call, so
  nothing was stored for those documents.
- **Recall and precision follow from that.** Most beliefs are not retrievable (recall 0.09).
  What is returned maps through a few broad memories, each attributed to several documents, so
  failures include unexpected beliefs (precision 0.02).
- **This is LangMem plus this model.** It shows how LangMem behaves with a small local model. It
  says nothing about LangMem with its documented hosted models, which were not authorised here.
- **The smoke shows the same system can apply corrections.** In `../smoke/`, LangMem rewrote a
  superseded memory. In this run's data, consolidation dominates instead.

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
