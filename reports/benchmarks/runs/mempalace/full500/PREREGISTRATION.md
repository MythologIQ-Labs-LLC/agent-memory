# MemPalace (default local agent-memory path): full 500-question LongMemEval-S (#810)

**Status: preregistered before execution; candidate, not reviewed or accepted.**

`preregistration.json` was written by `reference/run_longmemeval_resumable.py --preregister-only` for backend
`mempalace_default_local` (`longmemeval_mempalace_bridge:install_longmemeval_mempalace_backend`).

- Input: `longmemeval_s_cleaned.json`, sha256 `d6f21ea9…a3442`.
- Selection: all 500 questions, ID-list sha256 `7d738ae585fd4014c9d231088ff824864fded501adc07b0e08c2b97a28210c03`, the same as the Hindsight full-500 generation.
- Planes: `session`, then `turn`.
- Evaluator: `reference/run_longmemeval.py`, unchanged from `38f6a7d`.
- Adapter: `reference/longmemeval_mempalace_bridge.py` 0.1.0-candidate at `d4a6804`.

## Configuration

| Item | Value |
|---|---|
| Product | MemPalace 3.11.0, tag commit `602d796c699cabba2971982cd9dccbbf46abfe79` (MIT), installed non-editable from that checkout. The installed package tree is hash-checked at startup |
| Environment | `../mempalace-venv-freeze.txt`, constrained by upstream `uv.lock`. One departure: pydantic is 2.13.5 instead of the locked 2.12.5, because this repository's `agentrust-trace` requires it |
| Product path | MemPalace's own MCP server, one per question: `mempalace_add_drawer(wing, room, verbatim item)` per item, then one `mempalace_search(question, limit=50)` |
| Defaults kept | chroma backend; `minilm` embedder; 800-character drawer chunking; search fetches limit×4 vector candidates, then reranks 0.6 vector + 0.4 BM25; `max_distance` 1.5; hits that are identical copies are folded into `also_in` |
| Embedder | ChromaDB ONNX all-MiniLM-L6-v2 archive, sha256 `913d7300…16ec3` (chromadb's own pin). Per-file hashes are in `../model-pins.txt`. One embedding thread. Offline |
| LLM | None reachable on this path. The bridge refuses to start if inference or cloud credentials are present |
| Isolation | fresh palace, config dir, HOME and server process per question, deleted after search |

## What this measures

MemPalace as an agent's local verbatim memory, through its documented tools. This is **not**
MemPalace's published LongMemEval "raw" figure (96.6% R@5). That figure comes from
`benchmarks/longmemeval_bench.py`, which writes text into a bare ChromaDB collection and does not
call the MemPalace package, and its R@5 metric may differ from this runner's `recall_all@5`.
Because drawers are chunked, several hits from one session can use up places in the top 50, so
values at depths @30/@50 should be read with care.
