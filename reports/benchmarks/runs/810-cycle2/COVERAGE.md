# Competitive benchmarking cycle 2: coverage, maturity and typed blockers (#810)

As of 2026-10-15. Everything here is **candidate** evidence: nothing is REVIEWED or ACCEPTED by this document.

**Host:** one Claude cloud VM with 4 vCPU, 15 GiB RAM, no GPU and Python 3.12. Network egress is allowlisted: GitHub, PyPI, Hugging Face and Docker Hub are reachable; vendor installer hosts such as `supermemory.ai` are not.

**Isolation:**
- Every competitor runs in its own environment: a venv, a loopback service or a container.
- The environment is allowlisted, with no GitHub, cloud or LLM credentials.
- No paid inference was used, no hosted CI ran, and no PR was opened.

## Maturity classes

The classes below follow the #817 request: INSTALLED, EXECUTED, REPRODUCED, REVIEWED and ACCEPTED.

- **EXECUTED, repeated** means two independent executions of the same configuration, compared case by case.
- **Partial** means fewer rows than the preregistered population. No score may be inferred from a partial run.
- A system with no completed run gets no score, **never a zero**.

| System, pinned | Tier measured | Installed | AMB PrecisionMemBench 77 (query-only, retrieval) | LongMemEval-S subset50 (retrieval) | Status / blocker |
| --- | --- | --- | --- | --- | --- |
| Mem0 OSS 2.2.1, explicit `infer=False` | explicit store, no LLM | yes | accepted lane v6, 10/77 | session and turn, 1 run each | ACCEPTED (AMB v6); LongMemEval subset is candidate |
| Hindsight 0.10.2 `5fc4ce2`, chunks, ONNX e5-small, `llm_provider=none` | no-LLM chunk retrieval, **not** Hindsight's LLM product mode | yes | **9/77, repeated** (identical verdicts) | session and turn, 1 run | EXECUTED, repeated on AMB. The filtered/LLM tier is BLOCKED (below) |
| Letta 0.16.8 `1131535`, archival memory over REST, bge-small | archival passage retrieval, **not** the stateful self-editing agent | yes | **9/77, repeated** (identical, including order) | session in progress, turn queued | EXECUTED, repeated on AMB |
| Cognee 1.6.4 `f154b32`, local GLiNER, no LLM | documented no-LLM mode | yes | 9/77 rep 1, rep 2 running | gen-1 37/50 session (exploratory, preregistration erratum); gen-2 preregistered | EXECUTED (AMB rep 1); LongMemEval partial |
| Jev-Mem `7ab0c73` + Laya `7b928d8` (fp32 CPU) | native graph with System-One | yes | — | session 5/50 partial | BLOCKED: hardware (GPU); see `817-jev-mem/HANDOFF.md` |
| LangMem 0.0.30, memory store manager + Qwen2.5-3B-Instruct Q4_K_M (llama.cpp, local) | LLM extraction and consolidation, real LangMem behaviour | yes (service built) | — | — | BLOCKED: local LLM throughput on a shared CPU |
| Supermemory local 0.0.9 (image digest `sha256:55778146…`, tag `server-v0.0.9` at `4036c7d`) | — | image pulled and inspected, then removed | — | — | BLOCKED: LLM required, plus licence review |
| Graphiti 0.31.1 (`getzep/graphiti`) | — | no | — | — | BLOCKED: LLM with structured output for every episode, plus a graph database |
| OpenViking 0.5.0 (`volcengine/OpenViking`, AGPLv3) | — | no | — | — | BLOCKED: VLM and embedding provider required |
| MemOS (`MemTensor/MemOS`, PyPI `MemoryOS` 2.0.33) | — | no | — | — | BLOCKED: LLM plus Neo4j and Qdrant services |
| Zep (managed) | — | — | — | — | BLOCKED: hosted service and credentials; Graphiti is its open-source engine |
| TencentDB Agent Memory | — | — | — | — | Owned by #806, not attempted here |

The baselines BM25 (8/77) and lexical overlap are controls, not memory products. Agent Memory scores 15/77 on AMB here. Its control rerun has 0 case differences from the reproduced #819 baseline.

## Typed blockers, with evidence

1. **Local LLM throughput (LangMem, and the same class for Graphiti, Supermemory local, OpenViking, MemOS and Hindsight's LLM tier).**
   - The only credential-free inference available is a CPU LLM. That is Qwen2.5-3B-Instruct Q4_K_M under llama.cpp (`llama-cpp-python 0.3.16`, GGUF sha256 `626b4a66…`), at about 7 tok/s for prompt processing and 2 tok/s for generation on 2 dedicated threads.
   - While the 5 long-running benchmark jobs share the 4 vCPUs (load average about 12), one LangMem extraction call for one short document did not finish in more than 10 minutes. The LLM server also held 4.9 GB resident.
   - AMB ingests 35 documents, and LangMem makes at least one tool-calling extraction per document. One repetition is therefore on the order of 10 hours or more, and the Graphiti episode pipeline needs several structured calls per episode.
   - A 3B model would also be a weak, non-representative extractor. Any number from it measures the model as much as the product, and must be labelled as such.
   - **Unblock:** a GPU host, or explicit approval for a paid inference budget. The hard stops forbid paid inference.
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
- **LongMemEval-S subset50** (43 scored), from earlier evidence on `claude/817-jev-mem-execution-no-ci`:
  - Session recall_all@5: Hindsight-chunks 0.930, Mem0 0.884, Agent Memory 0.837, lexical 0.814.
  - Turn recall_all@10: Hindsight 0.837, Agent Memory 0.721, Mem0 0.651, lexical 0.605.
  - Agent Memory trails dense chunk retrieval on multi-session evidence recall.
- **Capability explanation.**
  - Dense chunk and passage retrieval wins on LongMemEval: it aggregates semantically related evidence and returns long ranked lists.
  - Agent Memory wins AMB's selective cases (alias, budget and scope) through its typed, scoped belief handling.
  - Neither side passes AMB's supersession, type-routing or counter-signal cases.
  - No universal score is computed or implied.
