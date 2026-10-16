# Graphiti OSS 0.31.1 on AMB PrecisionMemBench single-turn (all 77 cases): 9/77, LLM-at-ingestion tier

**Status: candidate.** This is a self-run result, not an official AMB entry, and it has not been
accepted. It was independently reviewed: `independent-review-812-graphiti.md` reached the verdict
"acceptable as candidate evidence", and its should-fix corrections are applied here. The run was
preregistered before execution (`PREREGISTRATION.md`, pushed in `2e82cbb`).

**What this measures:** Graphiti with a local Qwen2.5-3B model at temperature 0 (Graphiti's default
is 1.0; temperature 0 was declared before execution). It does **not** measure Graphiti with a
frontier LLM, and it is **not Zep's** hosted product.

Run 1 is the first *complete* run, and run 2 repeats it (see Repeatability). Two earlier attempts
were aborted during ingestion and scored no case:
- attempt 1 by the executor's tool time limit, after 5 completed episodes (during the 6th);
- attempt 2 by a container restart, after episode 4.

Their records are in `aborted-attempt*/`.

## Result (AMB native scoring)

| Item | Value |
|---|---|
| Correct | **9/77** |
| Active passes | 0/43 |
| Structural passes | 6/25 |
| Trivially-empty passes | 3/9 |
| Mean precision | 0.066 |
| Mean recall | 0.996 |
| Mean documents returned | 18.1 per case |
| Paired vs Agent Memory 15/77 | +0 / −6, exact McNemar p = 0.031 |
| ID resolution | all `source_id`; no lexical, doc-id or marker fallback |

- **Same nine passes as the other external systems.** Graphiti passes exactly the same nine cases
  as MemPalace, Hindsight and LangMem: budget eviction 3/5, design boundary 2/6, and the
  structural singletons. MemPalace, Hindsight and Graphiti return nearly the whole budget, about
  18 documents per case. LangMem returns about 5.5, but its stored memories cover very little.
- **Supersession chain exclusion is 0/3, and better invalidation would not fix it.**
  - All three cases expect **no** relevant beliefs (`shouldOnlyInclude: []`), yet Graphiti
    returned 20 documents for each.
  - Most of those documents are not superseded beliefs at all.
  - Graphiti's default `search` returns about k facts with no relevance cutoff. Even perfect
    invalidation plus a validity filter would still fail these cases.

  *(Corrected after independent review. An earlier version blamed the single invalidation.)*
- **Separate profile.** This row is in the LLM-ingestion tier and is not ranked with the no-LLM
  rows.

## Repeatability: run 2 is outcome-identical, and its LLM completions are byte-identical

Run 2 was a complete, fresh rerun with a new graph and the same models and settings. Its launch
identity (`rep2/launch-identity.json`) was captured before it started:
- HEAD `b03a681`;
- a clean worktree;
- bridge and shim blobs equal to the preregistration.

| Comparison | Result |
|---|---|
| AMB output (`rep1-vs-rep2.json`, `scripts/compare_amb_runs.py`) | **0 differences outside timing fields**: same correctness, sets, order and fact texts on 77/77 cases. The `single-turn.json` files are not byte-identical, because of timing fields |
| Ingestion | identical per episode: 95 nodes and 47 edges (summed over episodes), 1 invalidation |
| LLM | all **167 requests and completions byte-identical** to run 1 (temperature 0, seed 0, one inference slot, `PYTHONHASHSEED=0`) |
| Run 2 cost | 7,890 s of ingestion, on a quieter host; peak RSS 1.1 GiB |

Run 2's manifest is `rep2/manifest.json`.

## Ingestion: extraction yield and cost

Source: `rep1/ingestion-and-usage.json`. All inference was local, with no paid inference.

| Item | Value |
|---|---|
| Episodes ingested | **35 / 35**, 0 failures, 0 episodes with no edge |
| Entity nodes / fact edges extracted | 95 / 47, summed per episode; not distinct graph totals |
| Edges marked invalid at ingestion | **1** (a genuine contradiction judgement, per review) |
| Ingestion wall time | 11,456 s (median 214 s per episode, shared host) |
| LLM chat calls | 167, all HTTP 200, all at temperature 0 with schema-constrained JSON, none concurrent |
| Tokens | 253,829 prompt, 9,010 completion |
| Embedding requests | 225, all HTTP 200, including about 74 made at retrieval time |
| Peak RSS of the AMB CLI | 1.1 GiB |

Some extraction-quality artefacts of the 3B model are visible in the review:
- it copied example entities from Graphiti's prompt into the graph;
- the logs show 12 dangling-endpoint warnings;
- it emitted three edges with identical fact text for one belief.

## Mapping: episode associations vs fallback

Source: `rep1/mapping-from-amb-context.json`. AMB does not keep the provider's raw output, so this
is derived from AMB's own context listing.

- **0 unmapped edges.** Every returned fact mapped to its supporting episode, so nothing went
  through AMB's lexical fallback.
- **No fact mapped to more than one belief.** The 44 distinct returned fact texts each map to
  exactly one belief, so the preregistered one-document-per-supporting-episode rule never
  expanded a fact.
  - The 3B extractor did create **three edges with identical text** for one belief
    (`b-error-handling`).
  - They appear together in 36 cases and take 68 of the 1,391 returned slots.

  *(Corrected after independent review. An earlier version said 36 facts were listed under more
  than one belief.)*
- **Documents returned:** 1,391, against 1,371 `source_id` resolutions in AMB. The difference is
  entirely the budget-zero case: AMB's `retrieval_limit or 20` turns a budget of 0 into 20.
  MemPalace's run shows the same split.

## Input asymmetry

Graphiti receives each document's timestamp as `reference_time`, as Agent Memory receives its
`observed_at`. MemPalace, Hindsight and LangMem receive no timestamp.

## Identity

| Item | Value |
|---|---|
| Graphiti | `graphiti-core[falkordblite]==0.31.1` (tag commit `5961293`); installed package matches v0.31.1 file for file (review); environment `../graphiti-amb-venv-freeze.txt` |
| Models | `../model-pins.txt`: Qwen2.5-3B Q4_K_M `626b4a66…`, nomic-embed f16 `f7af6f66…` |
| Serving | `../serving-*.sh`, llama-cpp-python 0.3.16 (freeze `../llamacpp-venv-freeze.txt`), CPython 3.12.3 |
| Launch HEAD | run 1 `2522e474`, *inferred from the commit timeline* (not captured); run 2 `b03a681`, captured at launch |
| Revision in run 1's `execution-identity.json` | the post-run HEAD `b637f8d`. This is a known limitation, made moot in practice by run 2's exact reproduction |
| Bridge / shim blobs | `37a538c…` / `e15ef8c…`, equal to the preregistration (including the served shim copy) |
| Runner | differs from the preregistered blob only by three additive provider registrations (MemPalace, Hindsight, LangMem) |
| Credentials | none in the child (`execution-identity.json`), launched with `AWS_*` unset |
| Manifests | `rep1/manifest.json`, `rep2/manifest.json` (#808 v1) |

## Not verified

The independent review could not verify:
- which model files were loaded at run time (the shim does not log them);
- the contents of the graph database;
- what deduplicating the triplicate edges would have changed.

It also notes that Graphiti's docstring recommends `search_()` over the `search()` used here, and
that Graphiti's README example uses a 7B model.
