# Graphiti OSS 0.31.1 on AMB PrecisionMemBench single-turn (all 77 cases): 9/77, LLM-at-ingestion tier

**Status: candidate.** This is a self-run result, not reviewed and not accepted, and not an
official AMB entry. It was preregistered before execution (`PREREGISTRATION.md`, pushed in
`2e82cbb`).

Run 1 is the first *complete* run. Two earlier attempts were aborted during ingestion, one by the
executor's tool time limit and one by a container restart. Neither scored any case; see
`aborted-attempt*/`.

## Result (AMB native scoring)

| Item | Value |
|---|---|
| Correct | **9/77** |
| Active passes | 0/43 |
| Structural passes | 6/25 |
| Trivially-empty passes | 3/9 |
| Mean precision | 0.066 |
| Mean recall | 0.996 |
| Mean documents returned | 18.1 of the 20 budget |
| Paired vs Agent Memory 15/77 | +0 / −6, exact McNemar p = 0.031 |
| ID resolution | all `source_id`; no lexical, doc-id or marker fallback |

- **Same nine passes as the other full-budget systems.** Graphiti passes exactly the same nine
  cases as MemPalace, Hindsight and LangMem: budget eviction 3/5, design boundary 2/6, and the
  structural singletons. Every system that returns nearly the whole budget sits at this floor.
- **Graphiti's design target scores zero here.** Supersession chain exclusion is **0/3**.
- **Separate profile.** This row is in the LLM-ingestion tier and is not ranked with the no-LLM
  rows.

## Ingestion: extraction yield and cost

Source: `rep1/ingestion-and-usage.json`. All inference ran locally; nothing was paid for.

| Item | Value |
|---|---|
| Episodes ingested | **35 / 35**, 0 failures, 0 episodes with no edge |
| Entity nodes / fact edges extracted | 95 / 47 |
| Edges marked invalid at ingestion | **1** |
| Ingestion wall time | 11,456 s (median 214 s per episode, shared host) |
| LLM chat calls | 167, all HTTP 200 |
| Tokens | 253,829 prompt, 9,010 completion |
| Embedding requests | 225, all HTTP 200 |
| Peak RSS of the AMB CLI | 1.1 GiB |

Graphiti's invalidation step marks a superseded fact by LLM judgement. With the local 3B model it
fired once in 35 episodes. Graphiti's default `search` returns facts without filtering on
validity. Together these explain the 0/3 on supersession: they reflect this configuration, not
Graphiti's capability with a stronger model.

## Mapping: episode associations vs fallback

Source: `rep1/mapping-from-amb-context.json`. AMB does not keep the provider's raw output, so this
is derived from AMB's own context listing.

- **0 unmapped edges.** Every returned fact mapped to a supporting episode, so nothing went
  through AMB's lexical fallback.
- **36 facts were listed under more than one belief.** These facts have several supporting
  episodes, and each is emitted once per episode, as preregistered.
- **Documents returned:** 1,391, against 1,371 `source_id` resolutions reported by AMB. MemPalace's
  run shows the same 1,391 / 1,371 split, so the difference is AMB's resolver accounting and is
  not specific to Graphiti.

## Input asymmetry

Graphiti receives each document's timestamp as `reference_time`, as Agent Memory's `observed_at`
does. MemPalace, Hindsight and LangMem receive none.

## Identity

| Item | Value |
|---|---|
| Graphiti | `graphiti-core[falkordblite]==0.31.1` (tag commit `5961293`); environment `../graphiti-amb-venv-freeze.txt` |
| Models | `../model-pins.txt`: Qwen2.5-3B Q4_K_M `626b4a66…`, nomic-embed f16 `f7af6f66…` |
| Serving | `../serving-*.sh`, llama-cpp-python 0.3.16 (freeze `../llamacpp-venv-freeze.txt`) |
| Launch HEAD | `2522e474` |
| Revision in `execution-identity.json` | the post-run HEAD `b637f8d` (a known limitation, see the independent review) |
| Bridge / shim blobs | `37a538c…` / `e15ef8c…`, equal to the preregistration |
| Runner | differs from the preregistered blob only by three additive provider registrations (MemPalace, Hindsight, LangMem) |
| Credentials | none in the child (`execution-identity.json`), launched with `AWS_*` unset |
| Manifest | `rep1/manifest.json` (#808 v1) |
