# Native-metric frontier analysis (#810 / #789 / #719), 2026-10-15

**Status.** This is candidate analysis of candidate evidence. It confers no acceptance and no dashboard row.

**Inputs.** All inputs are committed rows on:
- [`claude/810-external-exec-no-ci`](https://github.com/MythologIQ-Labs-LLC/agent-memory/tree/claude/810-external-exec-no-ci) at `8887bbe`, independently reviewed (`competitive-diagnostics/independent-review-810.md`: acceptable as candidate, should-fix items applied);
- this branch, `claude/810-competitive-cycle2-no-ci`, for the cycle-2 rows;
- `claude/817-jev-mem-execution-no-ci`.

**Reproduction.** The row-level numbers below are reproduced by `scripts/frontier_row_analysis.py`, aggregate output only, in `analysis/frontier-rows.json`. That script recomputes every recall_all@k from the stored ranked lists and aborts if any recomputed value disagrees with the row's own metric. None disagreed.

**Rules followed:**
- There is no universal score. Profiles, protocols and planes are never pooled.
- Same-harness results and published vendor figures are kept apart.
- Controls (lexical overlap, BM25) are reported but are never "the frontier".
- "Frontier" means the strongest **same-harness reproduced** external product per native metric.

## 1. LongMemEval-S retrieval, full 500 (419 scored), frozen input `d6f21ea9…`, evaluator blob `6b9c237`, no LLM, depth 50

| Plane, metric | Agent Memory | Frontier (system) | Signed gap (AM − frontier) | Paired vs frontier W/L/T, exact McNemar | Δ, 95% bootstrap CI | Other peers |
|---|---:|---|---:|---|---|---|
| session recall_all@5 | 0.8234 | 0.8878 (Hindsight chunk-only) | **−0.064** | 34/7/378, p = 2.53e-5 | +0.064 [+0.036, +0.093] | MemPalace 0.8807 |
| session recall_all@10 | 0.8926 | 0.9642 (Hindsight) | **−0.072** | 32/2/385, p = 6.94e-8 | | MemPalace 0.9403 |
| session recall_all@50 | 1.0000 | 1.0000 (both) | 0 | | | |
| turn recall_all@5 | 0.6014 | 0.7064 (Hindsight) | **−0.105** | 57/13/349, p = 1.03e-7 | | MemPalace 0.6683 |
| turn recall_all@10 | 0.7232 | 0.8353 (Hindsight) | **−0.112** | 51/4/364, p = 2.05e-11 | +0.112 [+0.081, +0.146] | MemPalace 0.8043 |
| turn recall_all@50 | 0.8592 | 0.9570 (Hindsight) | **−0.098** | | | MemPalace 0.9427 |

**#719 posture: `competitive deficit`, P1.** Retrieval is a core claimed capability. The deficit is material, significant on both planes, and holds against both reproduced hybrid peers.

**Repeat status:**
- Agent Memory: 2,000 of 2,000 control rows identical on a second host.
- Hindsight: recall_all@{5,10,50} identical across hosts; order and recall_all@3 vary (D2).
- MemPalace: repeated on an independent host (`../810-mempalace-repeat/full500`, preregistered). Ranked lists identical on 500/500 questions on both planes, so the paired results above are unchanged. Pending independent review.

### Where the gap comes from

The figures below show where each evidence item sits in each system's ranked list, from `analysis/frontier-rows.json`.

| Evidence position | AM session | Hindsight session | AM turn | Hindsight turn | MemPalace turn |
|---|---:|---:|---:|---:|---:|
| ranks 1–5 | 0.870 | 0.935 | 0.654 | 0.757 | 0.727 |
| ranks 6–10 | 0.052 | 0.042 | 0.099 | 0.114 | 0.105 |
| ranks 11–30 | 0.064 | 0.020 | 0.112 | 0.083 | 0.094 |
| ranks 31–50 | 0.014 | 0.004 | 0.033 | 0.019 | 0.040 |
| **absent from top 50** | **0.000** | 0.000 | **0.103** | 0.026 | 0.035 |
| — questions with 3+ evidence items: ranks 1–5 | 0.678 | 0.876 | 0.352 | 0.522 | 0.459 |
| — questions with 3+ evidence items: absent from top 50 | 0.000 | 0.000 | **0.225** | 0.055 | 0.075 |

- **Session plane: an ordering deficit.** Agent Memory has every evidence session in its top 50, yet places only 68% of the evidence for 3+-evidence questions in its top 5, against 88% for Hindsight. The missing share sits at ranks 6–30. This matches handoff O2/O3 and D1.
- **Turn plane: a reach deficit and an ordering deficit.** 10.3% of evidence turns are absent from Agent Memory's top 50, and 22.5% for 3+-evidence questions, against 2.6–3.5% for the peers. Better ordering inside the admitted list cannot recover these items. Candidate generation, failure-stage 4 in #719's taxonomy, has to reach them first.
- **Union oracle (an upper bound, not a system):**
  - Session @5: Agent Memory **or** Hindsight is fully correct on 0.905, against 0.888 for Hindsight alone. Agent Memory solves some questions the frontier misses, so the signals are complementary.
  - Turn @10: 0.845, against 0.835.

## 2. LongMemEval-S retrieval, preregistered 50-question subset (43 scored), selection `5266568e…7339`

This is a smaller cohort used to add systems too slow for the full 500. It is never pooled with section 1.

| System | session r@5 | session r@10 | turn r@10 | turn r@50 | vs AM paired | Status |
|---|---:|---:|---:|---:|---|---|
| Agent Memory | 0.837 | 0.907 | 0.721 | 0.814 | — | control |
| **Letta 0.16.8, archival search only** (bge-small) | **0.953** | **0.977** | 0.814 | **0.977** | session @5 +7/−2 (p = 0.180); turn @50 **+7/−0 (p = 0.0156)** | complete, repeated (0 metric differences) |
| Hindsight chunk-only (subset run) | 0.930 | 0.953 | **0.837** | 0.977 | session @5 +4 net | complete, repeated |
| Mem0 OSS 2.2.1 explicit (MiniLM) | 0.884 | 0.907 | 0.651 | 0.977 | session @5 6/4 (p = 0.754); turn @5 1/6 (p = 0.125) | complete, repeated (100/100 identical) |
| Cognee 1.6.4 GLiNER, gen-1 | 0.953 | 0.977 | — | — | — | **exploratory** (preregistration erratum); not ranked |
| Lexical overlap (control) | 0.814 | 0.860 | 0.605 | 0.767 | | control |

**#719 posture: `competitive deficit`, P1.** This agrees in direction with section 1. Small-sample p-values are reported as-is: only the turn @50 depth result reaches p < 0.05 on its own.

- **Mem0 is the one product that does not beat Agent Memory here.** It trails on turn @5 and @10 and is at parity on session @10.

## 3. AMB PrecisionMemBench single-turn, 77 cases, retrieval mode, protocol tier A (query-only), evaluator `03c1d0f`

| System | Correct | Active passes (of 43) | Precision | Recall | Paired vs AM (peer wins / AM wins, p) | Repeated |
|---|---:|---:|---:|---:|---|---|
| **Agent Memory** | **15** | **4** | **0.181** | 0.954 | — | yes (reviewed) |
| Mem0 explicit | 10 | 0 | 0.105 | 1.000 | 1 / 6, p = 0.125 | accepted lane v6 |
| MemPalace 3.11.0 | 9 | 0 | 0.056 | 1.000 | 0 / 6, p = 0.031 | yes |
| Hindsight chunk-only, **two independent adapters** | 9 | 0 | 0.054–0.055 | 0.985–0.988 | 0 / 6, p = 0.031 | yes, both |
| Letta archival | 9 | 0 | 0.055 | 0.988 | 0 / 6, p = 0.031 | yes |
| Cognee GLiNER | 9 | 0 | 0.055 | 0.988 | 0 / 6, p = 0.031 | yes |
| BM25 (control) | 8 | 0 | 0.054 | 0.965 | 0 / 7, p = 0.016 | yes |
| *LangMem 0.0.30 + local 3B, LLM-ingestion tier* | *9* | *0* | *0.017* | *0.093* | *separate tier, not ranked* | *one run, nondeterministic* |

**#719 posture: `frontier_but_inadequate`.** Agent Memory is the same-harness frontier, but 4 of 43 active passes is not adequate precision.

- **9/77 is a no-skill floor.** Every external system passes the **same** 9 cases, 6 structural and 3 trivially empty. LangMem reaches them with 4 stored memories. So AMB's correct count does not separate the external systems, and Agent Memory's +6 is the entire signal.
- **What the +6 consists of.** It sits in alias resolution and fuzzy matching: name, alias and slot handling.
- **What no system passes:** scope disambiguation, supersession (0/3), type routing, relation expansion and counter-signal.

**Input asymmetry, disclosed.** Agent Memory's AMB bridge passes `observed_at` timestamps. Every external provider here, including this branch's Hindsight, Letta and Cognee services, receives none. Agent Memory's lead is in alias and fuzzy cases, not temporal ones, so this is unlikely to drive it, but the inputs are not identical.

**Published reference, not same-harness:** Hindsight cloud's published 66/77. It uses LLM ingestion plus structured filters, which is a different tier. Track it as a `published-reference gap`, P3, and do not claim inferiority until it is reproduced.

## 4. Hidden held-out cohorts (#819 independent evaluation), runtime revisions only

These compare runtime revisions of Agent Memory, not competitors. They are listed because they are the only unseen-cohort evidence on capability classes that LongMemEval and AMB do not isolate. Aggregates only; cohort content stays sealed.

| Cohort (208 queries) | A (accepted runtime) | Best candidate | Capability findings replicated on unseen content |
|---|---:|---:|---|
| v2 | 59 | C3: 161 | multi-evidence aggregation recall: A 0.83 → C3 0.33; paraphrase recall: 1.0 → 0.25 |
| v3 | 49 | C3 / C4: 135 | aggregation 0.94 → 0.17; paraphrase 0.75 → 0.00; multi-hop with a lexically disjoint bridge 0/16 **for all**; newer-first ordering of conflicting statements 0/16 **for all** |
| e4 (C6 evaluation, in progress) | 30 | C4 default 128; **C4 with the semantic route 133, recall 0.947** (C4 default 0.773) | C6 route-off = C4 exactly; C6 with the semantic route is running |

The e4 result is the first unseen-cohort measurement of the runtime's own optional semantic route. It recovers most of the low-overlap evidence the selective default withholds, at roughly 13 times the recall latency (p50 753 ms against 58 ms on this shared host).

## 5. Operational cost (orders of magnitude; shared 4-vCPU host)

| System | LongMemEval ingest, median per question (about 48 sessions) | Recall median | Notes |
|---|---:|---:|---|
| Agent Memory | 0.85 s | 25 ms | |
| Hindsight chunk-only | 12.1 s | 74 ms | |
| MemPalace | 12.4 s | 178 ms | |
| Letta archival | 55 s (turn plane 161 s for about 245 items) | 560–650 ms | REST plus Postgres plus embedding endpoint per insert |
| Cognee GLiNER | 652 s | 219 ms | 15 min to 75 min per question depending on contention; owner directive halts multi-day runs |
| Graphiti + local 3B | about 5–8 min per episode | — | LongMemEval blocked on compute |

Agent Memory is one to three orders of magnitude cheaper at ingestion and fastest at recall. **Posture: `frontier / preserve`** for cost: keep it as a regression ceiling when remediating retrieval.

## Summary of postures

| Profile | Posture | Priority |
|---|---|---|
| LongMemEval-S full 500, session and turn | competitive deficit (same-harness, significant) | P1 |
| LongMemEval-S subset50 | competitive deficit (consistent with full 500) | P1, evidence for the same deficit |
| AMB PrecisionMemBench 77, query-only tier | frontier_but_inadequate | P1, adequacy target |
| AMB published Hindsight 66/77 (LLM + filters) | published-reference gap | P3 |
| Cost and latency | frontier / preserve | regression ceiling |
| Supersession and contradiction ordering (AMB 0/3; held-out 0/16) | architecture gap, unsolved by every measured system | P2 |
