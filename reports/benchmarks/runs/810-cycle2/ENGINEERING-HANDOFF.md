# Engineering handoff, cycle 2: prioritised capability gaps (#719 / #819), 2026-10-15

**For the runtime engineer.** This supplements, and does not replace, the independently reviewed `competitive-diagnostics/2026-10-15-819-handoff.md` on `claude/810-external-exec-no-ci` (`8887bbe`). Its O1–O8 and D1–D2 stand. This document adds the cycle-2 systems and an aggregate row analysis.

**Rules:**
- Everything here is aggregate. No question ids, gold labels, case text or hidden-cohort content are included or needed.
- Nothing here is a tuning target. Interventions must be general runtime mechanisms, judged on fresh sealed cohorts and the frozen lanes.
- Each item keeps three things apart:
  - **Observed:** measured.
  - **Hypothesis:** not demonstrated.
  - **Candidate intervention:** a design direction, not a prescription.

## Gap 1, P1: ordering of corroborating evidence at ranks 6–30 (session plane)

**Failure stage (#719):** 8, ranking and fusion.

**Observed:**
- On the full 500 session plane, Agent Memory's top 50 contains every evidence session (absent 0.0%).
- Even so, only 0.678 of the evidence for questions needing 3+ sessions is in its top 5. Hindsight places 0.876 there and MemPalace 0.777.
- The remainder is at ranks 6–10 (0.124) and 11–30 (0.168).
- Multi-session questions overall: 0.807 in the top 5, against 0.928 for Hindsight.
- In D1, a dense arm alone placed 95% of the missed evidence in its top 5. Hindsight's BM25 arm managed 72%, and Agent Memory 54%.

**Hypothesis:** the corroborating sessions share topic but not vocabulary with the question. The lexical ordering ranks them below lexically closer but irrelevant sessions.

**Offline counterfactual (not a runtime result):**
- On the 43-question subset, reciprocal-rank fusion (k=60, deterministic tie-break) of Agent Memory's committed ranking with a pure dense ranking (Letta, bge-small) lifts session recall_all@5 from **0.837 to 0.953**: +5/−0, exact p = 0.0625, Δ +0.116 [+0.023, +0.209].
- This shows complementarity between the signals. It does not show what the runtime would reach.

**Candidate intervention:** add a dense ordering signal that fuses with the lexical ranking before return selection.

**Acceptance gates:**
- the frozen full 500 lanes on both planes;
- a fresh sealed cohort;
- no regression in AMB selectivity;
- the cost ceiling in Gap 6.

## Gap 2, P1: candidate reach on the turn plane (evidence never admitted)

**Failure stage (#719):** 4, candidate generation and route reachability.

**Observed:**
- On the full 500 turn plane, **10.3%** of evidence turns are absent from Agent Memory's top 50. For questions with 3+ evidence items it is **22.5%**.
- Hindsight is at 2.6% and 5.5%, MemPalace at 3.5% and 7.5%.
- Turn recall_all@50 is 0.859, against 0.957 for Hindsight.
- On the subset, a dense ranking alone leaves 1.2% absent, against 15.1% for Agent Memory.
- Fusion with dense lifts turn recall_all@50 from **0.814 to 0.977**: +7/−0, p = 0.0156.

**Consequence:** this part of the deficit cannot be fixed by reordering or by return selection. The items are not in the candidate set at all.

**Hypothesis:** short turn items with low lexical overlap fall below lexical candidate generation. The same gap appears on the sealed #819 cohorts:
- paraphrase recall is 0.00–0.25 under the selective default;
- the optional semantic route raises held-out recall to 0.947 on e4.

**Candidate intervention:** a semantic candidate route that proposes into admission, not only into ranking. The runtime already has one, off by default.

**What to measure:** its reach gain, separately from its ordering gain, on turn-granularity data.

## Gap 3, P1: return selection withholds paraphrased and aggregate evidence

**Failure stage (#719):** 9, controller, allocation and stopping, with 4 secondary.

**Observed on sealed cohorts v2 and v3 (#819, aggregate only):**
- For C3 and C4 relative to A, multi-evidence aggregation recall fell **0.94 → 0.17** on v3, and paraphrase recall **0.75 → 0.00**. On v2, C3 returned nothing for half of the aggregation queries.
- On e4, C4 with the semantic route reached recall 0.947, against 0.773 for the default, and 133 strict passes against 128.

**Hypothesis:** a sufficiency floor relative to the best lexical score cannot tell "irrelevant" apart from "relevant but worded differently". The same signal also produces part of the abstention gain.

**Candidate intervention:**
- abstain only on positive evidence of irrelevance;
- give enumerative or aggregate query shapes a minimum return;
- base sufficiency on a non-lexical relevance estimate.

All of these must be validated on a cohort the candidate has not seen. v1, v2 and v3 are spent.

## Gap 4, P2: selectivity adequacy (AMB) while keeping depth

**Failure stages (#719):** 9 and 10.

**Observed:**
- Agent Memory is the AMB frontier (15/77, 4/43 active), but every system fails most selectivity cases.
- Every dense or hybrid peer returns about k items for every query: precision about 0.055, the 9/77 floor.
- The peers that win LongMemEval depth are therefore the least selective.

**Hypothesis (H3 of the reviewed handoff):** ordering (Gaps 1 and 2) and selection are separable. A better ordering signal should make a selection cut safer, because the relevant items would sit above the cut.

**Candidate intervention:** design ranking first, then selection. Report the trade-off as a non-dominated operating point, depth against selectivity. Do not hide either side.

## Gap 5, P2: temporal applicability and contradiction ordering

**Failure stages (#719):** 6, temporal applicability, and 7, relations.

**Observed:**
- AMB supersession chain exclusion is 0/3 for **every** measured system, Agent Memory included.
- On sealed cohort v3, ordering the newer of two unreconciled statements first is 0/16 for A, C2, C3 and C4.
- LongMemEval temporal-reasoning recall@10 on the turn plane: Agent Memory 0.740, against 0.843 for Hindsight and 0.803 for MemPalace.
- Knowledge-update is near parity: 0.931 against 0.986–1.000.
- Graphiti's LLM-based invalidation did not fire with a 3B model in its smoke.

**Hypothesis:** without a write-time relation between statements, recency or contradiction cannot be applied at ranking time. This agrees with #747's S3 finding: no write-time relation in 197 of 212 cases.

**Candidate intervention:** belongs to the existing write-time relation and currentness tranche, not to retrieval ranking.

## Gap 6, constraint, not a gap: cost and determinism are frontier, so keep them

**Observed:**
- **Ingest:** Agent Memory takes 0.85 s per question, against 12 s for Hindsight and MemPalace, 55 s for Letta and 652 s for Cognee.
- **Recall:** Agent Memory takes 25 ms, against 74–650 ms for the peers.
- **Determinism:** Agent Memory's repeats are bit-identical (2,000 of 2,000 rows).
- **Peers:** Hindsight's order varies from BM25 ties with no tie-break (D2). Letta's varies on 4 of 50 turn questions, from ties.
- **The runtime's own semantic route:** held-out recall p50 is 753 ms with the route on, against 58 ms off, about 13×, on a shared host.

**Constraint on any intervention:**
- keep a deterministic total tie-break inside any fusion;
- state a latency and ingest ceiling before measuring;
- report semantic-route cost next to its recall gain.

## Dense versus lexical contribution: what the data does and does not show

- **Observed:**
  - Pure dense rankings beat Agent Memory's lexical ranking on depth: Letta with bge-small, session @5 0.953 against 0.837.
  - Dense rankings are not uniformly better. Mem0 with MiniLM gets session @5 0.884, and turn @10 0.651, below Agent Memory's 0.721.
  - The embedder matters. Its quality differs by up to 0.16 recall on the same subset.
- **Observed:** fusion beats either signal on some cuts. Turn @5 is 0.744 fused, against 0.628 for each alone.
- **Not shown:**
  - that the runtime's pinned MiniLM-QA semantic route would match bge-small;
  - the effect of fusion at full-500 scale.

  Both need a runtime-owned experiment on the frozen lanes.

## What engineering should not take from this

- No question-specific behaviour, phrase lists or thresholds fitted to these cohorts.
- No claim that the offline fusion numbers are achievable as-is.
- No pooling of the subset with the full 500.
- No use of LLM-tier (LangMem) or published (Hindsight 66/77) numbers as same-harness targets.
