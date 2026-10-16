# Independent adversarial review: Graphiti OSS 0.31.1 on AMB PrecisionMemBench single-turn (#812)

- Reviewed commit: `0c6e807d95c19581cdbc310f37bb3155a245cfd8`. The local branch is named `ext-exec-810`; it equals `origin/claude/810-external-exec-no-ci`.
- Evidence: `reports/benchmarks/runs/812-graphiti/` (with `amb-precisionmembench-single-turn/`).
- Frozen AMB: `/tmp/agent-memory-benchmark` at `03c1d0f1d27d…`, clean worktree.
- Graphiti source: `/tmp/graphiti-src` at `v0.31.1` (`5961293865a5…`). The installed `graphiti_core` in `/tmp/am-bench/graphiti-amb-venv` has no file differences from the tag source (`diff -rq` is empty).
- Method: read-only. All analysis used python3 stdlib (run with `-I`), with scripts in the scratchpad `an/` folder. I imported AMB's own `precisionmembench.py` scorer, with `rich` stubbed out, and re-ran it on documents parsed back out of each case's `context` listing. Nothing in `/home/user/ext-exec` was modified, and I did not start or stop any process.

## Verdict

**ACCEPTABLE AS CANDIDATE EVIDENCE, with SHOULD-FIX corrections to the README narrative.**

The headline numbers reproduce exactly. They are 9/77 correct, 0/43 active, 6/25 structural and 3/9 trivially-empty passes, with mean precision 0.0657 and mean recall 0.9961. The per-category passes and the paired comparison (+0/−6 vs Agent Memory, exact McNemar p = 0.03125) also reproduce.

- **Preregistration:** it predates every benchmark execution.
- **Leakage:** none found.
- **Configuration:** it matches the preregistration in code and in all 167 logged requests.
- **Repeatability:** rep1 and rep2 are equal in outcome. All 167 requests, 167 completions and token usages are identical.
- **Ingestion claims:** these verify.

No finding is BLOCKING. Two README statements are wrong or misattributed and should be corrected before acceptance:

- the "36 facts under more than one belief" explanation (SF-1);
- the causal explanation of Supersession 0/3 (SF-2).

## A. Headline and repeatability

| Claim | Independent result | Status |
|---|---|---|
| 9/77; active 0/43, structural 6/25, trivially-empty 3/9 | Same, from AMB's own `score_retrieval` re-run on parsed documents; 0 mismatches against stored `meta` (pass_type, relevant_beliefs, precision, recall, resolution, failures, correct) on 77/77 | verified |
| Mean precision 0.066 / recall 0.996 | 0.065675 (n = 69) / 0.996124 (n = 43) | verified |
| Per-category passes (README, `paired-vs-cohort.json`) | Budget eviction 3/5, Design boundary 2/6, Cross-user 1/1, Persona 1/4, Ranking 1/3, Cold start 1/1; all others 0 (Supersession 0/3) | verified |
| +0/−6 vs Agent Memory 15/77, p = 0.031 | From `/tmp/am-bench/amb-ref/full-agent-memory-rep1.json`: wins 0, losses 6, two-sided exact p = 0.03125. vs BM25 8/77: +1/−0, p = 1 | verified |
| Same nine passes as MemPalace, Hindsight, LangMem | Pass sets identical to each system's rep1 `single-turn.json` | verified |
| ID resolution: source_id only, no fallback | Resolution counts are `source_id = 1371` only. No doc_id, marker or lexical resolution | verified |
| 1,391 documents vs 1,371 resolutions | The 20-document gap is entirely `budget-zero-graceful-empty`. AMB's `RetrievalMode` uses `int(retrieval_limit or 20)`, so a maxBeliefs of 0 becomes k = 20, and the scorer then skips resolution when cap = 0. "AMB's resolver accounting" is correct but vague | verified |
| rep1 vs rep2: 0 differences | My own JSON tree diff differs only in `retrieve_time_ms` (72 cases), `avg_retrieve_time_ms` and `ingestion_time_ms` | verified |
| All 167 LLM completions identical | Both shim logs: 167 chat requests identical (sorted-key JSON), 167 completions identical, 167 usages identical; 225 embedding requests each; all HTTP 200 | verified |
| Per-episode ingestion identical | 35/35 episodes with identical (doc, nodes, edges, invalidated) tuples. Graphiti episode uuids differ, as uuid4 is expected to | verified |

Supporting observations:

- **Committed rep2 file matches /tmp.** The committed `rep2/single-turn.json` is byte-identical to the `/tmp` file that `rep1-vs-rep2.json` names.
- **Shared LLM server did not change outputs.** Rep1 shared the LLM server with the concurrent LangMem run (until 22:29Z) and rep2 did not, yet the completions are identical. Contention therefore did not affect outputs.
- **Concurrency was effectively 1.** The shim log shows 0 overlapping calls of 392, so SEMAPHORE_LIMIT=1 was in effect.

## B. Preregistration timing and fidelity

**Timing.**
- `preregistration.json` has `registered_utc` 16:53:14Z. It was committed in `2e82cbb` at 16:53:43Z, and the local remote-tracking reflog shows the push at 16:53:50Z.
- The first benchmark LLM call (aborted attempt 1) was at 17:12:10Z. Rep1 started at 20:53:24Z and rep2 at 00:08:44Z.

**Code blobs.**
- Bridge `37a538c…` and shim `e15ef8c…` are unchanged from `4144695` (16:51Z) through HEAD; `git log` shows only that one commit touching them.
- The guard (`1d3584f…`) and the evidence wrapper (`fbf6d7c…`) equal the preregistration.
- Served copies match. `/tmp/am-bench/graphiti-serving/graphiti_llamacpp_shim.py` hashes to `e15ef8c…`. The `/tmp` serving scripts are identical to the committed `serving-start-*.sh`.

**Runner.** The executed `run_amb_external.py` is `1208551…` and the preregistered one is `3666114…`. The diff is only three additive imports and three `install_*` registrations (MemPalace, Hindsight, LangMem). Those modules have no import-time side effects beyond constants and imports.

**Configuration in code and logs.**

| Item | Value | Matches preregistration? |
|---|---|---|
| Model | `qwen2.5-3b-instruct-q4_k_m` on all 167 calls | yes |
| Temperature | 0.0 on all 167 calls | yes |
| Response format | `json_object` + schema on all 167 calls (translated from json_schema) | yes |
| `max_tokens` | 16384, Graphiti's OpenAIGenericClient default | yes |
| Finish reason | `stop` on all calls; all completions parse as JSON with the schema's required keys | n/a |
| Search | `Graphiti.search(query, group_ids=[user], num_results=k)` | yes |
| Ingest | `add_episode(name=uuid5, body=content, reference_time=timestamp, group_id=user)` | yes |

**Environment.**
- The installed distributions equal `graphiti-amb-venv-freeze.txt` exactly; its sha256 `67062a7c…` equals the preregistered value.
- Model files on disk match `model-pins.txt` today.

**Launch identity.**
- **Rep1 has no launch-identity record.** `execution-identity.json` records the post-run HEAD `b637f8d`, and the README discloses this. The claimed launch HEAD `2522e474` is consistent with the commit and push timeline: no commit lands between 20:22:56Z and 20:54:03Z. It is an inference, not a captured artifact (N-3).
- **Rep2 is fully captured.** `rep2/launch-identity.json` shows HEAD `b03a681`, a clean worktree and the preregistered blobs. Since rep2 reproduced rep1 exactly, any doubt about rep1's code identity is resolved in practice.

**Undisclosed command difference.** The detached launcher adds `--set-env PYTHONHASHSEED=0`, which is not in the preregistered command (N-4).

## C. Leakage and mapping

**Bridge.** The bridge passes only `document.content`, the timestamp, `user_id` (as `group_id`) and an opaque uuid5 name. It never uses `document.tags`, `document.context` or `query.meta`. `supports_filters=False`, so AMB passes no `retrieval_filter`.

**Prompts.** I scanned 1,028,463 characters of message content across all 167 LLM requests in rep1:
- 0 belief ids (no exact ids, and no `\bb-…` regex hits);
- 0 `beliefId`, `scope:`, `scope=`, `domain:` or `context=`;
- 0 of the three scope values;
- 0 `mustInclude` or `shouldOnlyInclude`;
- 0 case ids and 0 category names;
- 0 `test-user` or `other-user`.

One case query string ("mongod") appears, but only as a substring of belief text ("MongoDB"), which is benign.

**Not checked by log.** Embedding inputs are not logged by the shim; only counts are. Leakage through embeddings cannot be checked from the log, but the code shows they are Graphiti's own entity names, facts and queries.

**Provenance mapping and fallback.** The mapping cannot inflate correctness: every document resolved via `source_id`, and no lexical, marker or doc-id fallback fired.

**Per-supporting-episode duplication.** Quantified from the context listings:
- Across all 1,391 documents there are 44 distinct fact texts. **None is listed under more than one belief.**
- So the preregistered "one document per supporting episode" expansion never produced a second belief for any returned fact in this run. Its effect on precision and recall is **zero** here.
- This agrees with `ingestion-and-usage.json`'s `returned_edges_with_multiple_source_episodes: 0`.
- In principle the expansion could raise recall and lower precision on graphs where deduplication merges facts across episodes. With this 3B model's sparse deduplication it did not occur.

The repeats that do exist are a different phenomenon; see SF-1.

## D. Faithfulness to Graphiti

**Documented local path.** This is a fair use of it:
- `OpenAIGenericClient` with the default `structured_output_mode="json_schema"`, plus `OpenAIEmbedder` with nomic-embed-text at 768 dimensions. That is exactly the embedder in Graphiti's README local example.
- Embedded FalkorDB Lite and the default `Graphiti.search` recipe (`EDGE_HYBRID_SEARCH_RRF`: BM25 + cosine, RRF, default `SearchFilters()`).

**Shim.** It does only what it claims:
- It routes chat and embedding traffic.
- It rewrites `json_schema` into llama-cpp's `json_object` + `schema`, which is grammar-constrained.
- It splits list embedding inputs one per request and reassembles them in order.
- It logs.

Re-serialising the JSON does not change the body. It forwards temperature and max_tokens unchanged; the logs confirm this.

**Temperature 0.** This is disclosed as a deviation from Graphiti's default of 1 in `PREREGISTRATION.md`, `preregistration.json` and the bridge constant. The run README mentions "temperature 0, seed 0" only under Repeatability and does not label it a deviation (N-5).

**Points not disclosed in the run README (fairness context).**
- Graphiti's own README example uses a 7B model and advises "Prefer the most capable model you can run". The README's "small local model" framing covers this.
- `Graphiti.search`'s own docstring calls it "our basic out-of-the-box search, for more robust results we recommend using … `search_()`". The preregistration's "documented primary retrieval" is defensible, but this is worth stating (N-6).

**Supersession mechanism checked against the v0.31.1 source.**
- *Invalidation.* `add_episode` returns `entity_edges = resolved_edges + invalidated_edges` (`graphiti.py`). `_apply_temporal_invalidation` / `resolve_edge_contradictions` (`utils/maintenance/edge_operations.py:715-783`) set `invalid_at`/`expired_at` only when the LLM marks `contradicted_facts`.
- *The single invalidation.* Exactly one dedup call returned a non-empty `contradicted_facts` (rep1 chat call #81). The new fact "narrator_voice_old replaced by close third-person." (valid_at 2026-01-01) contradicted the later "narrator_voice uses close third-person…" (valid_at 2026-09-01). Graphiti therefore expired the *new, older-dated* edge. No extraction or temporal call set `invalid_at`, so the "1 invalidation" is a genuine LLM-judged contradiction, as claimed.
- *Search filtering.* `SearchFilters()` has every field set to `None`, and no `expired_at IS NULL` / `invalid_at IS NULL` appears in the search path. "Default search returns facts regardless of validity" is supported.
- **However**, the README's conclusion that these two facts *explain* the 0/3 is not supported; see SF-2.

## E. Ingestion claims (all verified from logs)

| Claim | Independent result |
|---|---|
| Episodes | 35/35, 0 with zero edges, 0 failures |
| Nodes / edges / invalidated | 95 / 47 / 1 (sums of the per-episode `graphiti-ingest` lines in `stderr.txt.gz`) |
| Ingestion time | 11,455.5 s; median 213.6 s per episode |
| LLM chat calls | 167, all 200 |
| Tokens | 253,829 prompt / 9,010 completion, from response `usage` |
| LLM wall time | 11,179 s |
| Embedding requests | 225, all 200 (357 inputs) |
| Peak RSS | rep1 1,152,320 KiB, i.e. 1.10 GiB; rep2 1.10 GiB |
| Rep2 ingestion | 7,890.1 s |

The LLM calls break down as 35 entity extraction, 35 fact extraction, 40 entity dedup, 45 fact dedup, 10 summaries and 2 temporal.

Caveats on labels (N-1, N-2):
- **Nodes and edges are per-episode sums, not distinct graph totals.** Nodes resolved to existing nodes are counted again in later episodes. `result.edges` also includes re-resolved and invalidated edges.
- **Not all 225 embedding requests are ingestion.** About 74 of them, with 77 inputs, were made after the last LLM call, i.e. retrieval-time query embeddings. They are reported in the "Ingestion: extraction yield and cost" table.
- **Undisclosed extraction artefacts.** Stderr has 12 Graphiti warnings, "Materialized 1 dangling edge endpoint node(s)". On the first episode the 3B model also copied "Dr. Amara Osei" and "AAN" from the prompt's in-context example into the extracted entities, and the fact "Dr. Amara Osei shapes the response length and opening style of AAN." entered the graph.

These are 3B-model quality artefacts, measured as-is. They are not disclosed, and they strengthen the "not Graphiti with a stronger model" framing.

## F. Disclosures

**Aborted attempts.** Both are disclosed, and neither scored a case (stdout ends during ingestion; no `[query:` lines).
- Attempt 1's 25 committed chat calls are identical to rep1's first 25, so the same configuration was used.
- Small bookkeeping gap (N-7). The `/tmp` log for attempt 2 (`amb-rep1-calls.aborted-attempt2.jsonl`) begins with one fact-extraction call for episode 6 at 19:09:26Z. That call belongs to attempt 1, whose process was still running after its committed log ends at 19:02Z. The shim recorded a BrokenPipe at 19:15, consistent with that client being killed. So attempt 1 actually reached episode 6. Attempt 2's shim log is not committed. Neither point affects rep1, which ran after the container restart killed all processes.

**Other disclosures.**
- *Timestamps.* Graphiti receives `reference_time`; this is disclosed under "Input asymmetry".
- *Tier separation.* Stated in the README, preregistration, `system.json` and manifest.
- *"Not frontier LLM / not Zep".* Stated in the preregistration, `system.json` and manifest limitations. The run README's own text never says "not Zep" (N-5).

**LongMemEval blocker.** The reasoning holds:
- Measured cost on the PMB run: about 4.8 LLM calls per episode, about 1.5k prompt tokens per call, median 214 s per episode.
- Graphiti's fact-extraction prompt already carries 5 previous episodes (seen in the logs). LongMemEval sessions would push prompts to many thousands of tokens at about 12 tok/s.
- So the "≈5 h/question, ≈10 days for 50" estimate is if anything optimistic.
- A 1–3 question feasibility probe is not discussed (N-8).

## Findings

### BLOCKING
None.

### SHOULD-FIX

**SF-1. False explanation of the "36 facts listed under more than one belief".**
- *Where:* README §Mapping; `rep1/mapping-from-amb-context.json` `facts_listed_under_more_than_one_belief: 36`.
- *What the data shows:* no fact text is listed under more than one belief (44 distinct fact texts, each under exactly one `source_id`). The 36 is the number of *cases* in which one fact appears three times under the *same* belief (`b-error-handling`).
- *Cause:* the 3B fact extractor emitted three distinct edges with the identical fact text "error_handling_explicit shapes error handling patterns…". They differ only in the target entity: error handling, try-catch, Result type (see the rep1 shim log, fact-extraction response for that episode).
- *Effect:* these repeats use 68 of the 1,391 document slots. They are not provenance expansion. In `cap-stress-late-position-entity-at-risk` (the only case with recall < 1, missing `b-kubernetes-entity`) they took 2 of the 20 slots. Pass/fail is unaffected, since that case also fails on 9 unexpected beliefs.
- *Also:* the README's statement contradicts its own `ingestion-and-usage.json` (`returned_edges_with_multiple_source_episodes: 0`).
- *Fix:* rename the metric and correct the text.

**SF-2. The Supersession 0/3 attribution is wrong as stated.**
- *Where:* README §Ingestion, last paragraph; echoed in the handoff and admission docs.
- *Why:* all three supersession cases expect `relevantBeliefs.shouldOnlyInclude: []`, so any non-pinned belief returned fails them. Graphiti returned 16, 17 and 16 beliefs. Of these, only 4–5 per case are superseded or resolved beliefs; **11–13 per case are non-superseded, unrelated beliefs.**
- *Consequence:* perfect invalidation *and* validity filtering would still fail all three. The 0/3 is caused by default search returning about k facts for every query with no relevance cutoff, the same failure as every full-budget system.
- *Over-claim:* "they reflect this configuration, not Graphiti's capability with a stronger model" goes too far. A stronger model would not change it under the default search recipe.
- *Fix:* state that the 0/3 is caused by the default search returning about k facts for every query (no relevance cutoff), and that invalidation affects at most the superseded subset.

**SF-3. "Byte-identical" overstates what was compared.**
- *Where:* README §Repeatability heading; `system.json` limitations; commit message.
- *Why:* the two `single-turn.json` files are not byte-identical; their sha256s differ (`d381acd0…` vs `429546df…`). They are equal on everything except timing fields.
- *What is byte-identical:* the LLM completions.
- *Fix:* say "outcome-identical (timing fields excluded); LLM completions byte-identical".

**SF-4. Two pieces of tooling misreport or leave stale records.**
- *Missing-belief undercount.* `paired-vs-cohort.json` gives graphiti `failures_with_missing_belief: 0`, but `cap-stress-late-position-entity-at-risk` has a "missing expected belief: b-kubernetes-entity" failure. `scripts/paired_amb_systems.py:70` reads `judge_reason`, which AMB truncates to the first 4 failures. The same undercount can affect the cohort rows.
- *Unmeasured fields reported as 0.* `ingestion-and-usage.json` reports `returned_edges_with_invalid_or_expired: 0` alongside `queries_with_provider_raw: 0`. This is unmeasured, not zero, and should be `null`.
- *Stale limitation.* `rep1/manifest.json` still says "Single complete run; no repeat yet".
- *Stale status.* `ADMISSION-RECOMMENDATIONS.md` and `2026-10-15-819-handoff.md` still say "run 2 running" / "in progress".
- *Wrong interpreter version.* The manifest gives `environment.runtime_version` "3.13.16", but the run interpreter was 3.12.3 (`execution-identity.json`).

### NOTE

- **N-1. Node and edge counts are per-episode sums.** 95 nodes and 47 edges include re-resolved nodes and edges and the invalidated edge. Label them "per-episode extraction results (summed)", not graph size.
- **N-2. The 225 embedding requests include retrieval.** They include about 74 retrieval-time query embeddings, but the README lists them under ingestion cost.
- **N-3. Rep1 launch HEAD is inferred, not captured.** `2522e474` comes from the commit timeline; worktree cleanliness at launch is unrecorded. Rep2's exact reproduction mitigates this.
- **N-4. Undisclosed `PYTHONHASHSEED=0`.** The detached launcher sets `--set-env PYTHONHASHSEED=0` (`scripts/run_amb_detached.sh`), which is not in the preregistered command. It is harmless but undisclosed.
- **N-5. Run README omits two labels.** It does not label temperature 0 as a deviation from Graphiti's default of 1.0, and never says "not Zep". Both are in the preregistration and `system.json`.
- **N-6. Context worth stating.** Graphiti's docstring recommends `search_()` over `search()` for robustness. Graphiti's README example uses a 7B model and advises using the most capable model available.
- **N-7. Attempt bookkeeping.** Attempt 1 actually reached episode 6 (see F). Attempt 2's shim log is in `/tmp` only.
- **N-8. Unconsidered LongMemEval probe.** The blocker does not consider a 1–3 question feasibility probe; this is a scoping choice.
- **N-9. Undisclosed extraction artefacts.** These are the in-prompt example copied into the graph on episode 1 and 12 dangling-endpoint warnings (see E).
- **N-10. Synthetic smoke overlapped the preregistration.** The smoke started at 16:43:22Z and ran 1,666 s, ending about 17:11Z. That is after the preregistration at 16:53Z. The preregistration says it was the only prior execution, which is true, but the smoke's "no invalidation" observation postdates the registration, so it could not have shaped the configuration. This is favourable rather than a problem; noted for accuracy.
- **N-11. "Full-budget" wording.** The README calls LangMem one of "the other full-budget systems", but LangMem returns 5.49 documents per case on average. The same-nine-passes fact is correct.

## What I could not verify

- **Model and server identity at run time.** Model files and served shim/scripts match today. Request bodies carry the LLM model alias. The shim does not log embedding model names or inputs, and the logs do not prove which GGUF files were loaded at 20:53Z. `llm-server.log` was not fully inspected.
- **Rep1's worktree state at launch.** No artifact exists, and the launch HEAD is inferred.
- **Push times.** These come only from the local remote-tracking reflog, not from GitHub's server.
- **Graph-level contents.** These include distinct node and edge totals, and which returned edges carried `invalid_at`. AMB does not keep provider raw output, and I did not open `graphiti.db`, which would require starting FalkorDB Lite.
- **Effect of deduplicating the triplicated `b-error-handling` edges.** Edges beyond the k cut are not observable.
- **Cohort references.** The Agent Memory and BM25 results in `/tmp/am-bench/amb-ref/` were taken as given from the earlier reviewed evidence (`1df28f8`); I did not re-derive them.
- **Unit tests and smoke.** I did not run `reference/tests/test_amb_graphiti_bridge.py` or the smoke, to stay read-only.
