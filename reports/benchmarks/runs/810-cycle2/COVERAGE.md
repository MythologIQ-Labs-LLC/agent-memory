# Competitive coverage inventory, reconciled across lanes (#810 / #789), 2026-10-15 23:30 UTC

**Status.** Every row is **candidate** evidence. Nothing is accepted by this document. Final leaderboard admission and dashboard integration belong to the repository hygiene and delivery owner.

**Sources, reconciled without overwriting anyone's work:**

| Lane | Branch | Head | Reviewed? |
|---|---|---|---|
| External execution (separate session) | `claude/810-external-exec-no-ci` | `8887bbe` | Independent adversarial review `competitive-diagnostics/independent-review-810.md`: acceptable as candidate, SHOULD-FIX applied |
| Cycle 2 (this session) | `claude/810-competitive-cycle2-no-ci` | this branch | Self-reported, repeat-checked; **pending independent review** |
| First comparator runs | `claude/817-jev-mem-execution-no-ci` | `13302fc6` | Earlier LongMemEval subset50 rows; owner provenance checks on #811 |
| #819 independent evaluation | `claude/819-independent-evaluation-no-ci` | `81b02a25` | Independent evaluator; runtime revisions, not competitors |

**Counting rule.** A product is counted once, whatever the number of adapters, tiers or configurations. Two independent Hindsight AMB adapters (external lane and this branch) are one system, and they agree: 9/77 with the same 9 cases. Controls (BM25, lexical overlap) are never counted.

## Inventory

**Classes:**
- **A:** complete and independently reviewed.
- **B:** complete, pending review.
- **C:** experimental or exploratory.
- **R:** running.
- **X:** blocked.
- **N:** not implemented.

The #789 status code is in brackets.

| System (pinned) | Architecture family | LongMemEval-S full 500 | LongMemEval-S subset50 | AMB PrecisionMemBench 77 | Class [#789 status] |
|---|---|---|---|---|---|
| **Hindsight 0.10.2** `5fc4ce2`, chunk-only, no LLM | hybrid dense + BM25 with RRF | **A**: session r@5 0.888, turn r@10 0.835 | A: repeated (recall identical, order varies) | A: 9/77 (external); B: 9/77 (this branch's independent adapter) | **A** [executed_unaccepted]. LLM product tier X |
| **MemPalace 3.11.0** | dense with rerank, wing/room structure | **A**: session r@5 0.881, turn r@10 0.804; **B** repeat on an independent host (`../810-mempalace-repeat/full500`): ranked lists identical on 500/500 questions on both planes | — | A: 9/77, repeat identical | **A** [executed_unaccepted] |
| **Mem0 OSS 2.2.1**, explicit (`infer=False`) | vector store, MiniLM | — | A: repeated 100/100 identical | accepted lane v6: 10/77 | **A** [AMB accepted_same_harness; LongMemEval executed_unaccepted] |
| **Letta 0.16.8**, archival memory only | dense passages over pgvector (component tier, not the stateful agent) | **B**: session r@5 0.857, turn r@10 0.780, turn r@50 0.955 (`../810-letta/full500`, preregistered) | **B**: session r@5 0.953, turn r@10 0.814, both planes **repeated** (0 metric differences); identical metrics to the full-500 rows on the same questions | B: 9/77, repeated identical | **B** [executed_unaccepted]. Agent tier N |
| **Cognee 1.6.4**, local GLiNER, no LLM | graph + vector (fastembed bge-small) | — | C: gen-1 session 0.953, **exploratory** (preregistration erratum). External gen-2: 3/50, stopped per owner directive. This host's duplicate gen-2: **R** (see below) | B: 9/77, repeated identical | **B** on AMB; **C** on LongMemEval [executed_unaccepted] |
| **LangMem 0.0.30** + local Qwen2.5-3B | LLM-managed memories over a vector store | — | — | C: 9/77, precision 0.017, recall 0.093; LLM-ingestion tier; nondeterministic; one run (external) | **C** [executed_unaccepted, separate tier]. A valid LangMem measurement is X (needs a capable model) |
| **Graphiti 0.31.1** + local 3B | temporal knowledge graph (LLM extraction) | X: compute (about 5 h per question) | X | R/X: attempt 3 relaunched in the external lane, outcome not recorded | **X** [blocked_cost] |
| **Jev-Mem** `7ab0c73` + Laya | multi-relational graph with a learned controller | X | C: CPU fp32 rows 2/50 (external) and 8/50 on this host (stopped), partial, no score | — | **X** [blocked_dependency: GPU] |
| **Supermemory local 0.0.9** | LLM-extracted memories with hybrid search | — | — | — | **X** [blocked_cost and licence review: closed binary, "lite license"] |
| OpenViking, MemOS, MIRIX, EverOS, TencentDB, A-Mem, Memobase, Honcho | various | — | — | — | **N** [source_qualified or not_started]; see `NEXT-QUEUE.md` |
| Zep (managed) | managed temporal graph | — | — | — | **X** [blocked: hosted only]; Graphiti is its open-source engine |

**Distinct external products with completed same-harness results:** 6, namely Hindsight, MemPalace, Mem0, Letta (component tier), Cognee (AMB) and LangMem (separate LLM tier, one run). Of these:
- **2** have reviewed full-500 LongMemEval results: Hindsight and MemPalace. Letta has a complete full-500 result pending review (class B), and MemPalace has an identical independent-host repeat.
- **4** are repeated with matching verdicts on at least one family: Hindsight, Mem0, Letta and Cognee (AMB).
- **2** are repeated on both families: Hindsight and Letta.

**Benchmark families with external peers:** 2, LongMemEval-S retrieval and AMB PrecisionMemBench. Both are retrieval and selectivity families. The first is depth-oriented and the second precision-oriented, and they are never pooled.

**Not yet covered:** QA or answer generation, write-time update and correction at scale, cross-session agent outcomes, and lifecycle (deletion and permission) against peers.

**Architecture families covered:**
- hybrid dense + lexical (Hindsight);
- dense with rerank (MemPalace);
- pure vector (Mem0, Letta archival);
- graph + vector, no-LLM (Cognee);
- LLM-managed memories (LangMem, separate tier).

Knowledge-graph-with-LLM (Graphiti) and learned-controller graph (Jev-Mem) are blocked.

## Active runs on shared hosts and directives

| Run | Host | State | Note |
|---|---|---|---|
| Cognee gen-2 (`811-cognee/subset50-gen2`, preregistered 16:53Z) | this host | **stopped** at 12/50 (owner-authorised 2026-10-16; a container restart at about 00:14Z ended it first) | It duplicated the external lane's gen-2 and conflicted with the owner directive. Its 12 rows are execution evidence only: never scored, never pooled. `STOPPED-2026-10-16.md` on `claude/817-jev-mem-execution-no-ci` (`38e80cde`) |
| Jev-Mem CPU subset50 | this host | **stopped** at 8/50 (same authorisation and restart) | Partial CPU fp32 rows, no score; never pooled with GPU rows. `STOPPED-CPU-2026-10-16.md` |
| #819 C6 held-out evaluation (cohort e4) | this host | **complete** (C6+sem 144/208); text-free per-case record handed to the evaluation lane (`bdbd8a63`) | Independent evaluation lane. The C6 LongMemEval-500 semantic runs I had queued were **cancelled before starting**, under the "no resource-heavy launches while saturated" rule |
| Graphiti AMB attempt 3 | external lane | unknown | No outcome recorded on the branch, per the review |

## Typed blockers, with evidence

1. **Local LLM throughput (LangMem, and the same class for Graphiti, Supermemory local, OpenViking, MemOS and Hindsight's LLM tier).**
   - The only credential-free inference available is a CPU LLM. That is Qwen2.5-3B-Instruct Q4_K_M under llama.cpp (`llama-cpp-python 0.3.16`, GGUF sha256 `626b4a66…`), at about 7 tok/s for prompt processing and 2 tok/s for generation on 2 dedicated threads.
   - While the 5 long-running benchmark jobs share the 4 vCPUs (load average about 12), one LangMem extraction call for one short document did not finish in more than 10 minutes. The LLM server also held 4.9 GB resident.
   - AMB ingests 35 documents, and LangMem makes at least one tool-calling extraction per document. One repetition is therefore on the order of 10 hours or more, and the Graphiti episode pipeline needs several structured calls per episode.
   - A 3B model would also be a weak, non-representative extractor. Any number from it measures the model as much as the product, and must be labelled as such.
   - **Re-measured on a quieter host** (load about 5.7, 22:40 UTC), using a single clear fact (*"I switched our team's CI from Jenkins to GitHub Actions…"*):
     - One LangMem `create_memory_store_manager` call took **266 s**: 519 prompt tokens at 6.0 tok/s, then 521 generated tokens at 3.0 tok/s.
     - It wrote **0 memories** and recorded **0 LLM errors**. The 3B model's tool-calling output gave LangMem nothing to store.
     - A full AMB run would therefore measure the local model's tool-calling failure, not LangMem. It would mostly produce empty stores and trivially empty passes, and that is **not a valid LangMem measurement**.
   - **Unblock:** a capable tool-calling model, through a GPU host or an approved inference budget. The hard stops forbid paid inference.
2. **Hardware (Jev-Mem).** Laya is ModernBERT-large running fp32 on CPU, at about 64 to 78 minutes per session-plane question. The CUDA handoff has pinned commands and hashes. CPU fp32 and CUDA bf16 rows must never be pooled.
3. **Supermemory local.**
   - The vendor's own docs at `server-v0.0.9` say: *"needs one model provider to power summaries, contextual chunking, and memory extraction"* and *"the only required input is one LLM provider key"*. That is the same LLM blocker as above.
   - The docs also say the self-hosted binary is *"free within its lite license limit … Its server source is not in the public repository"*. The open repository (MIT) does not contain the engine. The licence terms need owner review before benchmarking or publishing results.
   - The `supermemory.ai` installer host is blocked by egress policy. The Docker Hub image itself pulled fine.
4. **Hindsight filtered tier.** AMB's native `hindsight-http` provider filters on tags that only Hindsight's ingestion LLM assigns. With no LLM, all 77 recalls come back empty, so that run is recorded as INVALID, not scored. See `../cycle2-amb-precisionmembench/README.md`.
5. **Zep.** It is managed-only (`zep-cloud` 4.0.0 is an HTTP client), so it needs credentials and a paid hosted service. The open-source Graphiti is not Zep, and Zep-cloud author scores must not be attributed to it.

## What the measured systems show

These results are retrieval-only and query-only, on the same harness.

- **AMB PrecisionMemBench, 77 cases:**
  - Agent Memory leads, with 15 correct and 4 active passes out of 43.
  - Mem0 explicit gets 10, BM25 8, and Hindsight-chunks, Letta-archival and Cognee-GLiNER 9 each.
  - All three dense-retrieval peers pass **the same 9 cases**: 6 structural and 3 trivially empty, with **0 active passes**. Their returned sets differ in most cases.
  - None of them has a relevance floor, so they return about k items for every query. Mean precision is about 0.055 against recall of about 0.99. Precision is set by AMB's k, not by the system.
  - Agent Memory's lead comes entirely from its 4 active passes, and its precision is also low, at 0.18. #819 diagnosed this as the shared failure class: no selective return.
- **LongMemEval-S subset50** (43 scored, same preregistered selection, evaluator blob `6b9c237`):
  - Session recall_all@5: Letta-archival 0.953, Hindsight-chunks 0.930, Mem0 0.884, Agent Memory 0.837, lexical 0.814. Paired against Agent Memory: Letta +7/−2 (p=0.18).
  - Turn recall_all@10: Hindsight 0.837, Letta 0.814, Agent Memory 0.721, Mem0 0.651, lexical 0.605. At recall_all@50, Letta reaches 0.977 against Agent Memory's 0.814 (+7/−0, p=0.016).
  - Agent Memory trails dense chunk retrieval on multi-session evidence recall.
- **Capability explanation.**
  - Dense chunk and passage retrieval wins on LongMemEval: it aggregates semantically related evidence and returns long ranked lists.
  - Agent Memory wins AMB's selective cases (alias, budget and scope) through its typed, scoped belief handling.
  - Neither side passes AMB's supersession, type-routing or counter-signal cases.
  - No universal score is computed or implied.

## Egress observation

From 16:35 UTC the agent egress proxy refused about 20 connection attempts to `mobile.events.data.microsoft.com:443`. Every attempt was refused, so no data left the host.

The host string appears only in the onnxruntime 1.31.0 binary of the LangMem environment. That environment also runs `reference/local_embedding_server.py`, which serves embeddings to Letta. That process is the likely source, though this is not proven.

Future runs of that server should disable onnxruntime telemetry explicitly. No other benchmark environment contains the string.
