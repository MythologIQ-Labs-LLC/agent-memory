# LangMem AMB bridge: synthetic smoke (#813)

The smoke used four hand-written documents and no benchmark data, run through the real LangMem
stack with a local Qwen2.5-3B model and nomic-embed. All 5 structural checks pass: retrieval,
editor recall, no cross-user leak in either direction, and the budget limit.

## What LangMem did with the correction

The third document said that Alice moved from Acme to Globex. LangMem rewrote the first memory to
"Alice works as an engineer at Globex in Denver", which is now attributed to `s1` and `s3`, and it
added a second memory for the move. LangMem therefore applied the correction as an update. On the
same input, Graphiti's local run kept both facts valid.

## Model usage

The full log is in `shim-calls.jsonl.gz`.

| Measure | Value |
|---|---|
| Chat requests (all with tools) | 4, all HTTP 200, all returned structured `tool_calls` |
| Prompt tokens | 5,368 |
| Completion tokens | 319 |
| LLM wall time | 974 s |
| Ingest time per document | 139–395 s |
