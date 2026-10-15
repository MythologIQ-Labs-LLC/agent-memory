# MemPalace on AMB PrecisionMemBench single-turn, all 77 cases (#810)

**Status: preregistered before execution. Candidate result; not reviewed or accepted.**

`preregistration.json` was written at 2026-10-15T16:57:38Z, before MemPalace ran on any
PrecisionMemBench case. The only earlier execution was `synthetic-smoke.json`: four hand-written
documents, with all five structural checks passing.

## Protocol

The protocol matches the reviewed Agent Memory (15/77) and BM25 (8/77) runs:

| Item | Value |
|---|---|
| AMB revision | `03c1d0f` |
| Run | `--dataset precisionmembench --split single-turn --mode retrieval` |
| Fixtures | Pinned (`35659b3b…`, `09e99f08…`) |
| Scorer | AMB's own |
| No-LLM guard | Unchanged |
| Evidence wrapper | Unchanged |
| Budget | AMB's per-case `retrieval_limit` |
| Filters | None (protocol A) |
| Capability tier | Same as Agent Memory and BM25: no LLM anywhere |

## System

MemPalace 3.11.0 at `602d796c`, with its default local configuration: Chroma, the MiniLM ONNX
model, and the 0.6 vector + 0.4 BM25 rerank. It is driven through its own MCP tools.

- **Ingestion:** one `mempalace_add_drawer` per AMB document, with the content verbatim and an
  opaque `source_file`.
- **Retrieval:** one `mempalace_search(query, limit=k)` per case.
- **Isolation:** each AMB user gets their own palace and server.
- **Withheld from MemPalace:** belief ids, scope tags, context markers, timestamps, gold and
  query categories.

## Runs and failure handling

- Run 1 is the result.
- A fresh full rerun (run 2) serves as repeatability evidence and never replaces run 1.
- A provider or harness exception fails the run, which is then reported rather than scored.
- No configuration changes after this registration.
