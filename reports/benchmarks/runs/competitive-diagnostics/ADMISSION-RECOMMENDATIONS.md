# Per-system admission recommendations (#810): executor's recommendation, not an acceptance

These recommendations come from the executing session. **They do not admit anything.** Admission
to the benchmark-public-feed or to any accepted register remains with the owner and the
publication owner, under #808. Every row below is a **candidate**: self-run, with one
independent adversarial review (`independent-review-810.md`, verdict "acceptable as candidate
evidence", should-fix items addressed in `8887bbe`).

Tier vocabulary:
- **no-LLM:** retrieval with local embedders or lexical signals only.
- **LLM-ingestion:** a local LLM extracts or updates memory at write time.

Rows from different tiers or different protocols are never ranked together.

| System and profile | Tier | Result (native) | Repeatability | Recommendation | Conditions or labels required |
|---|---|---|---|---|---|
| Hindsight 0.10.2 **chunk-only**, LongMemEval-S full 500, session and turn | no-LLM | session r@10 0.964, turn r@10 0.835 (419 scored, 0 failures) | Same-host query time deterministic. Fresh ingestion reorders tied BM25 hits (mechanism shown). recall_all@5/@10/@50 stable; nDCG and @1/@3 single-run | **Admit as candidate comparison row** | Label "chunk-only, llm_provider=none; not Hindsight's LLM product". Mark nDCG as single-run. Show the turn and session planes separately |
| MemPalace 3.11.0 default (own MCP tools), LongMemEval-S full 500, both planes | no-LLM | session r@10 0.940, turn r@10 0.804 (0 failures) | AMB repeat byte-identical; LongMemEval run single (two execution segments) | **Admit as candidate comparison row** | Label "not MemPalace's published raw-ChromaDB figure". Disclose the two-segment execution. Read @30/@50 with chunking in mind |
| Hindsight chunk-only, AMB PrecisionMemBench 77, protocol A | no-LLM | 9/77, precision 0.054 | Two full runs, outcome-identical; order varies on 27/77 (one set change at budget 2). **Cross-lane replication** by an independent adapter: 9/77, per-case correctness identical | **Admit as candidate row** | Disclose that timestamps were withheld while Agent Memory received them. Never place next to the published 66/77 (LLM ingestion plus filters) |
| MemPalace, AMB 77, protocol A | no-LLM | 9/77, precision 0.056 | Two full runs, byte-identical | **Admit as candidate row** | Timestamp asymmetry disclosure |
| Mem0 OSS 2.2.1 explicit, LongMemEval-S 50-question subset | no-LLM | session r@10 0.907 (= Agent Memory), turn r@10 0.651 (Agent Memory 0.721) | Independent repeat 100/100 rows identical | **Admit as candidate row** (subset profile only) | Subset label (43 scored); differences are not significant at this n |
| LangMem 0.0.30, AMB 77, protocol A | LLM-ingestion (local 3B) | 9/77, precision 0.017, recall 0.093 | **Single complete run.** Ingestion varies across attempts even at temperature 0 | **Do not admit as a LangMem measurement.** Keep as exploratory evidence of LangMem with a 3B local model | The result is dominated by the small model's tool calling: only 7 of 35 documents changed memory, and 4 memories in total. Another lane, independently, recorded 0 memories written for a single clear fact (`claude/810-competitive-cycle2-no-ci`, COVERAGE.md at `692e185`). A valid LangMem row needs a capable tool-calling model, which requires a GPU host or an approved inference budget |
| Graphiti 0.31.1, AMB 77, protocol A | LLM-ingestion (local 3B) | 9/77, precision 0.066, recall 0.996; Supersession 0/3 (all three expect no relevant beliefs; default `search` has no relevance cutoff). 35/35 episodes, 47 edges, 0 unmapped | **Two complete runs, outcome-identical; all 167 LLM completions byte-identical.** Independently reviewed: acceptable as candidate evidence (`../812-graphiti/amb-precisionmembench-single-turn/independent-review-812-graphiti.md`) | **Admit as an LLM-tier candidate row** | Label as "Graphiti with a local 3B model at temperature 0; not a frontier LLM; not Zep". Separate from no-LLM rows. Graphiti, like Agent Memory, receives timestamps |
| Graphiti, LongMemEval-S | LLM-ingestion | not run | — | **Blocked (compute)** | `../812-graphiti/BLOCKER-longmemeval-2026-10-15.md` |
| Cognee 1.6.4 GLiNER local, generation 2 (LongMemEval-S 50) | no-LLM (GLiNER extraction) | 3/50 session questions, no score | — | **Not admissible (incomplete)** | Stopped per owner directive; handoff in `../811-cognee/subset50-g2/` |
| Jev-Mem | — | not run | — | **Blocked (no CUDA host)** | `../817-jev-mem/BLOCKER-2026-10-15.md` |

## Cross-cutting conditions for any admitted row

1. **Separate profiles.** LongMemEval measures evidence retrieval at depth; AMB measures
   selectivity. Neither is combined into a universal rank.
2. **Agent Memory's row** is the frozen baseline. Its AMB lead (15/77) and its LongMemEval
   deficit (session r@10 0.893, turn r@10 0.723) must both be shown.
3. **Identity.** The #808 v1 manifests in each bundle are the identity records. The independent
   review found that some run records name a HEAD captured after launch (code unchanged).
   Future runs record the revision at launch.
4. **No paid inference, no hosted CI.** All local LLM calls are logged in each bundle's shim log.
