# Next competitor execution queue (#810 / #789), 2026-10-15

**Sources.** Each candidate's README and licence were read at a pinned commit on 2026-10-15. Registry versions come from PyPI and npm metadata. Nothing was installed or run for this assessment, and vendor benchmark claims are quoted as **published references**, never as same-harness results.

**Ordering criteria, in this order:**
1. Architectural differentiation from the five families already measured: hybrid dense + BM25, dense with rerank, pure vector, graph + vector no-LLM, LLM-managed.
2. Evidence value for a #719 gap (FRONTIER.md and ENGINEERING-HANDOFF.md).
3. Feasibility without paid inference.
4. Cost.

## The constraint that orders everything

**Every remaining candidate requires an LLM at ingestion for its native behaviour.** The no-LLM sub-modes that exist would not represent the product:

- OpenViking's own configuration guide says that without a VLM, *"summaries are empty… Do not treat this as completed semantic indexing."*
- The only local, free inference on this host is a 3B CPU model. It took 266 s for one LangMem extraction and stored nothing (`COVERAGE.md`, blocker 1). Graphiti costs 5–8 min per episode.

So the queue below is ranked for execution **after an owner decision on inference**: a GPU host with a 7–8B instruct model, or an approved and bounded inference budget. Without that decision, only the CPU-feasible items in the last section can run.

## Ranked queue

| Rank | System (pinned) | Licence | Architecture (distinct?) | Model requirement | Infrastructure and deployment cost | Adapter feasibility | Benchmark fit and evidence value | #789 status |
|---|---|---|---|---|---|---|---|---|
| 1 | **Graphiti** `getzep/graphiti` 0.31.1 (`d50741d`) | Apache-2.0 | Temporal knowledge graph with LLM entity and edge extraction plus invalidation. **Distinct, and the only one aimed at Gap 5** (supersession, currentness) | LLM with structured output on every episode | FalkorDB Lite or Neo4j; local embeddings | Done (external lane adapter and smoke) | AMB-77 attempt 3 is pending; LongMemEval is blocked on compute. **Owned by the external lane; do not duplicate** | blocked_cost |
| 2 | **MemOS** `MemTensor/MemOS` (`a7367d0`), PyPI `MemoryOS` 2.0.33 | Apache-2.0 | Graph-structured "memory cubes", with multi-type and skill memory. Distinct | OpenAI-compatible LLM (defaults to DashScope); embedding through Ollama or a universal API | Neo4j + Qdrant (docker compose); heavy | `/product/add` and `/product/search` with `top_k`, and memory ids exist. Response provenance is not yet verified | **Published reference:** *"LongMemEval 89.20, LoCoMo 88.83"*, self-evaluated with their OmniMemEval, a QA protocol. High value as a P3 published-reference gap to reproduce on our retrieval lane | source_qualified |
| 3 | **EverOS** `EverMind-AI/EverOS` (`ec32f4b`), PyPI `everos` 1.4.2 (2026-10-14) | Apache-2.0 | Markdown as source of truth, with SQLite + LanceDB (vector + BM25); episodes, atomic facts, profiles. Distinct (file-native, fact extraction) | *"The minimum production path needs only an LLM"*; an embedding extra is needed for hybrid search | Light: Python 3.12 and embedded stores, no external services | `/api/v2/memory/add`, `/flush`, `/search` (`top_k`). The id fields in responses need verifying | Retrieval and fact extraction; a good LongMemEval candidate once an LLM is available | source_qualified |
| 4 | **A-Mem** `agiresearch/A-mem` (`ceffb86`) | MIT | Zettelkasten notes the LLM links and evolves; ChromaDB + BM25. Distinct (LLM-evolved note graph) | LLM per note (OpenAI or Ollama via litellm); local MiniLM embeddings | Light: pip, embedded ChromaDB | Clean: `add_note()` returns `memory_id`, `search_agentic(q, k)` returns ids. Install from source; the PyPI name `agentic-memory` is **a different project** | Order-dependent evolution needs repeats. No numeric vendor claim | source_qualified |
| 5 | **TencentDB Agent Memory** `TencentCloud/TencentDB-Agent-Memory` (`e9a8293`) | MIT | Layered L0 conversation → L1 atom → L2 scenario → L3 persona, with BM25 + vector + RRF. Partly overlaps Hindsight's hybrid | Two LLM configurations (memory and agent); L0 writes need none | Docker, three services, images on `:latest` (must be digest-pinned); Node ≥ 22.16 | `/v3/conversation/add` returns ids; `/v3/conversation/search` and `/v3/atomic/search` return id and score | **Published reference:** *"PersonaMem 48% → 76%"*. **Owned by #806** | source_qualified |
| 6 | **OpenViking** `volcengine/OpenViking` (`6006fc3`), PyPI 0.5.0 | **AGPL-3.0** | Virtual filesystem `viking://` with L0/L1/L2 summaries and directory-scoped vector search. Distinct (hierarchical context) | **VLM + embedding**; local `bge-small-zh` GGUF embedding by default | uv; local vectordb; asynchronous processing to poll | `add_resource` returns a task id; `find(query, limit)` returns URIs | Mapping URIs back to documents is feasible. **Published reference:** LoCoMo *"80–83%"* with Doubao models | source_qualified |
| 7 | **Honcho** `plastic-labs/honcho` (`9579ca2`), `honcho-ai` 2.6.0 | **AGPL-3.0** | Peer and session representations from a background "deriver" LLM; BM25 + vector over messages. Partly distinct (peer modelling) | LLM mandatory even to start the server | Postgres + pgvector; Docker | Search API exists; provenance not verified | Better suited to a persona or theory-of-mind family than document retrieval | source_qualified |
| 8 | **MIRIX** `Mirix-AI/MIRIX` (`8cb06a6`) | Apache-2.0 | Six agent-managed memory types; built on Letta | LLM per add (Gemini in the example); local not stated | pgvector, Redis Stack, `:latest` images | **The documented `mirix-client` is missing from PyPI**; ids not stated | Low feasibility until packaging is fixed | not_started |
| 9 | **Supermemory local 0.0.9** (image `sha256:55778146…`) | Server: closed binary under a "lite license" (repo MIT) | LLM-extracted memories with hybrid search | LLM required | Docker image (pulled and inspected) | Memory API exists | **Licence review by owner required** before benchmarking | blocked (cost and licence) |
| 10 | **Memobase** `memodb-io/memobase` (`358c16b`) | Apache-2.0 | User profiles plus an event timeline; *source blobs are "removed once they're processed"* by default | LLM required | Postgres + Redis | Weak provenance back to source documents | **Not comparable** on document-retrieval lanes. Fits a persona or profile family only. Published reference: LoCoMo 75.78 | rejected_noncomparable (for current lanes) |
| — | **Jev-Mem** `7ab0c73` | MIT | Learned-controller multi-relational graph | Laya ModernBERT; GPU | CUDA host | Done | Handoff ready | blocked_dependency (GPU) |

## Recommended next actions

**Do now. CPU-feasible, no inference, once the host is not saturated:**

1. ~~MemPalace LongMemEval repeat~~ **done** 2026-10-16: identical on both planes (`../810-mempalace-repeat/full500`). The external lane's original run was not modified.
2. **Letta full 500, session plane** (about 48 inserts per question at about 55 s, so roughly 8 h on one core). It would move Letta from the subset to the reviewed full-500 lane. Run it only after the Cognee gen-2 and Jev-Mem CPU runs on this host are resolved, because the host is saturated now.
3. **Independent review of this branch's cycle-2 rows** (Letta, Cognee AMB, the second Hindsight adapter), mirroring `independent-review-810.md`. These rows are currently class B.

**Needs an owner decision on inference (GPU host or budget):** ranks 1–6 above, in that order. Graphiti stays in the external lane. MemOS goes first among new systems because it carries the largest published-reference gap and a distinct architecture. EverOS and A-Mem come next for their low infrastructure cost and distinct designs.

**Needs an owner decision on licence:** Supermemory local, and AGPL systems if results or adapters are to be published. Running them locally for evaluation is not distribution, but the owner should confirm.

**Do not count toward breadth:**
- additional configurations of measured products, for example Letta with another embedder;
- client wrappers;
- shared vector backends.

Letta and Cognee already share an embedder and differ in only 2 of 77 AMB cases. Further dense-retriever variants add little evidence.
