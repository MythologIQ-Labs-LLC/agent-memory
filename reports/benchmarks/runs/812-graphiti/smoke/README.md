# Graphiti AMB bridge: synthetic smoke (#812)

The smoke used four hand-written documents and no benchmark data. It ran through the real
Graphiti 0.31.1 stack: embedded FalkorDB Lite, plus local Qwen2.5-3B and nomic-embed behind
`reference/graphiti_llamacpp_shim.py`. Run with `scripts/smoke_graphiti_amb_bridge.py`. Exit 0.

| Check | Result |
|---|---|
| Every document ingested (4 episodes, 290–520 s each on a shared 4-vCPU host) | pass |
| Fact edges extracted (5 edges over 4 episodes) | pass |
| "Where does Alice work now?" returns Alice's documents | pass |
| No cross-user leak in either direction (group ids) | pass |
| Persistent across a restart (same 3 edge uuids from the reopened database file) | pass |
| Correction invalidated the superseded fact | **no**: an observation, not a gate |

## The correction was not applied

Episode s3 says "Alice left Acme Corp and now works at Globex". Graphiti extracted it as a new
fact. The earlier "Alice works … at Acme Corp" edge kept `invalid_at = None` and
`expired_at = None`, and search returned both facts. Graphiti's invalidation step is an LLM
judgement, and with the local 3B model at temperature 0 it did not mark the contradiction. That
is the system plus this model, measured as-is. It is not adapter behaviour.

## Model usage

Model usage comes from `shim-calls.jsonl.gz`, the full request and response log:

| Item | Value |
|---|---|
| Chat calls, all HTTP 200 | 14, about 3 per episode plus 1 manual test |
| Prompt tokens | 14,027 |
| Completion tokens | 689 |
| Total LLM wall time | 1,481 s |
| Embedding requests | 29 |
| Failed embedding probes | 3 |

The 3 failed embedding probes were multi-input batch requests made before the shim began
splitting list inputs; the reason is in the shim's docstring. All inference ran locally and
cost nothing.
