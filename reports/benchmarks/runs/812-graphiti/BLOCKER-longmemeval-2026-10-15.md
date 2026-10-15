# Graphiti on LongMemEval-S: blocked by compute on this host (typed blocker, #812)

**Status: `blocked_compute`.** This is not a benchmark failure and not missing functionality.
Graphiti supports the LongMemEval profile in principle. Its documented path is one
`add_episode` per haystack session, followed by `search` for each question.

## Measured cost

The measurement comes from Graphiti 0.31.1 on embedded FalkorDB Lite, using local Qwen2.5-3B
Q4_K_M plus nomic-embed via llama.cpp, on a 4-vCPU host shared with other runs:

- **Per episode:** in the smoke (`smoke/`), each short episode (1–2 sentences) took 290–520 s.
  It used about 3 LLM calls of about 1,000 prompt tokens each, plus about 50 completion tokens.
- **Throughput:** prompt evaluation ran at about 12 tokens/s, and generation at about
  2 tokens/s under contention.

## Why LongMemEval-S does not fit

LongMemEval-S has about 48 haystack sessions per question. User turns per session run to
thousands of tokens, so each `add_episode` prompt carries a full session, which is several times
the smoke's prompts. Graphiti's deduplication prompts also grow with the graph.

Even at the smoke's per-episode cost, one question takes 48 × ~6 min, about 5 hours. The
50-question subset would therefore take about 10 days, and the 500-question set months.

## What would unblock it

Each of the following needs owner authorisation:

- **A GPU host with a 7B–8B instruct model.** That is a 50–100× throughput gain, which would make
  the 50-question subset a matter of hours.
- **Hosted inference.** Paid; not authorised.

## What runs instead

Graphiti runs on AMB PrecisionMemBench, which ingests 35 short beliefs once for all 77 cases.
That run fits this host. See `amb-precisionmembench-single-turn/`. It is a separate profile with
a separate capability tier: an LLM at ingestion.
