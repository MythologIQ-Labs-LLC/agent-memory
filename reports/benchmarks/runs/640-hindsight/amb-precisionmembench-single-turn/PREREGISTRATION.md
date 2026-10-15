# Hindsight OSS chunk-only (no LLM) on AMB PrecisionMemBench single-turn, all 77 cases (#640, #810)

**Status: preregistered before execution. This is a candidate result: not reviewed and not
accepted.** All identities are recorded in `preregistration.json`. The only earlier execution
was `synthetic-smoke.json`: four hand-written documents, with all 5 checks passing.

## Configuration

The Hindsight configuration is the same as the LongMemEval chunk-only lane:

| Setting | Value |
|---|---|
| Version | 0.10.2 at `5fc4ce2` |
| LLM | `llm_provider=none` |
| Bank mode | chunks |
| Retrieval | dense e5-small + text search, fused with RRF |
| Observations, temporal, graph, reranking | All off |
| Recall | `mid`, 65,536 tokens |

- **Isolation:** one bank per AMB user.
- **Retain:** documents are retained verbatim under opaque sha256 document ids.
- **Recall:** each call uses `top_k = k`, where k is AMB's per-case budget.
- **Not this run:** AMB's own `hindsight` provider, which uses LLM extraction, and Hindsight's
  published 66/77, which used LLM ingestion plus structured filters. Neither is compared here as
  if it were this configuration.

## Protocol

The protocol is the one used for the reviewed Agent Memory 15/77 and BM25 8/77 runs:

- AMB `03c1d0f`;
- the pinned fixtures;
- AMB's own scorer;
- the guard and evidence wrapper, unchanged;
- protocol A, with no filters;
- the same capability tier, with no LLM.

## Runs and failure rules

- Run 1 is the result. A fresh run 2 is repeatability evidence only.
- A provider or harness exception fails the run, and the run is reported, not scored.
- There are no per-case retries.
- No configuration changes after this registration.
