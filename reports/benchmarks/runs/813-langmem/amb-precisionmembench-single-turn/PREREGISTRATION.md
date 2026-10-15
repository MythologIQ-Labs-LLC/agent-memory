# LangMem on AMB PrecisionMemBench single-turn, all 77 cases (#813, #810)

**Status: preregistered before execution. This is a candidate run, not reviewed and not
accepted.** All identities are recorded in `preregistration.json`. The only earlier execution
was the synthetic smoke (`../smoke/`), which passed 5/5 checks.

## Configuration

| Component | Setting |
|---|---|
| LangMem | 0.0.30 at commit `48e3c11f`, store-backed memory manager with LangMem's defaults |
| Store | LangGraph `InMemoryStore` with a vector index; not persistent |
| LLM | Local Qwen2.5-3B at temperature 0, with tool calls through the Hermes shim |
| Embeddings | nomic-embed (local) |
| Harness | AMB `03c1d0f` with pinned fixtures; AMB's own scorer; guard and wrapper unchanged; protocol A |

- **Ingestion:** each document is sent to the manager as one user message, in a namespace per
  user.
- **Search:** `manager.search(query, limit=k)`, where k is AMB's per-case budget.
- **Provenance:** LangMem does not record where a memory came from. Any memory created or changed
  while a document is processed is attributed to that document.
- **Capability tier:** the LLM runs at ingestion, the same tier as Graphiti. The result is
  reported as a separate row and not ranked against the no-LLM systems.
- **Model deviation:** LangMem's documentation assumes hosted models; this run uses a local 3B
  model.

## Run rules

- Run 1 is the result.
- An exception fails the run and it is reported, not scored.
- No case is retried.
- The configuration does not change after this registration.
