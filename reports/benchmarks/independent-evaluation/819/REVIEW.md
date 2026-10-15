# #819 independent evaluation: relevance-sufficient return selection

**Recommendation: CHANGES REQUIRED for both C1 and C2.** Neither candidate should become the default yet.

Both candidates make AMB precision and abstention much better, and that gain holds up on a hidden holdout they never saw. But as the default `recall` return, both make the accepted LongMemEval lane clearly worse. They also drop multi-hop evidence, and they change the protected Runtime Baseline surface without declaring a successor.

| Item | Value |
| --- | --- |
| Baseline | `7c06468aae1aed0d2115c42f9588fbbe8417657e` (runtime identical to `main` `38f6a7d` and to #818's `1df28f8`) |
| C1 | `4bd38e6ca9cec9de7a054dd6b970ac26f05fb946`, return selection 1.0.0, contract 1.9.0 |
| C2 | `eaf60e4dd001c02ce00bb36f15f800996bf77da3`, return selection 1.1.0. It adds contraction handling, keeps function words written as names, and enforces ranking consistency |
| Protocol | A only (query-only facade). AMB bridge blob `3d9ccb3` unchanged |
| Evaluator | Independent session. It made no runtime changes and authored nothing it is reviewing |
| Host | 4 vCPU, 15 GiB RAM, no GPU, CPython 3.12.3, local only, 0 hosted CI. Other benchmark jobs shared the CPU, so latencies are indicative |

## Configuration checks

- Each candidate ran from a clean detached worktree. Its venv is a hard-linked copy of the baseline venv, with only the editable `agent-memory-reference` path repointed. So the dependency set is identical by construction, and `pyproject.toml` is byte-identical.
- The evaluation tooling has identical blobs at baseline and candidates: the AMB recorder, guard, runner and bridge; `run_longmemeval.py`; and the LoCoMo runner.
- AMB is at `03c1d0f`, with identical scorer blobs and fixtures `35659b3b…`/`09e99f08…`. No credentials reached the child process.
- The holdout's SHA-256 commitment was verified (`sha256sum -c`) before each run.

## Results

Strict pass means the evaluator's own pass/fail. "Paired" means per-case improved and regressed counts, an exact McNemar test, and a bootstrap 95% interval (10,000 resamples, seed 819).

### AMB PrecisionMemBench single-turn, 77 cases (known target)

| Metric | Baseline | C1 | C2 |
| --- | ---: | ---: | ---: |
| Correct | 15 | **39** | **39** |
| Active passes (of 43) | 4 | 21 | 21 |
| Mean precision | 0.1806 | 0.5415 | 0.5407 |
| Mean recall | 0.9535 | 0.8782 | 0.8782 |
| Mean context tokens | 542.2 | 90.2 | 90.8 |
| Paired vs baseline | | +24 / −0, p < 1e-6 | +24 / −0, p < 1e-6 |
| Δ pass rate, 95% CI | | +0.31 [0.21, 0.42] | same |
| Δ precision, 95% CI | | +0.34 [0.24, 0.43] | |
| Δ recall, 95% CI | | −0.075 [−0.15, −0.02] | |

- **Reproducibility:** two repetitions of each candidate differ in 0 cases. C1 and C2 differ in 1 case, `long-query-rambling-kubernetes`, where C2 keeps one more irrelevant belief because of its ranking-consistency rule. That case fails under both.
- **Per category:** Alias resolution 3→14 of 23; Budget eviction 3→5 of 5; Scope disambiguation 0→3 of 12; Ranking stability 1→3 of 3. Unchanged at 0: Supersession chain exclusion (3), Type routing and open questions (6), Counter-signal (2).
- **Wrongly returned beliefs:** fell from 199 to 52. The remainder: 23 in-scope but irrelevant, 13 out of scope, 9 superseded, 7 open questions.
- **Recall-only failures** rose from 2 to 6 cases, and "missing expected belief" reasons from 2 to 14.

### Hidden holdout: 176 queries, 160 scenarios, public facade, budget 5

The cohort was committed by SHA-256 at 13:36 UTC, before C1 was received. Its content is still sealed for any later candidate, so only aggregates appear here.

| Metric | Baseline | C1 | C2 |
| --- | ---: | ---: | ---: |
| Strict pass | 37 | **116** | **116** |
| Mean precision | 0.4395 | 0.7639 | 0.7639 |
| Mean recall | 0.8333 | 0.7778 | 0.7778 |
| Hard gates: cross-scope, forgotten, stale leaks | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Evaluation failures | 0 | 0 | 0 |
| Paired vs baseline | | +79 / −0, p < 1e-6, Δ pass 0.45 [0.38, 0.52] | same |
| Δ recall, 95% CI | | −0.056 [−0.083, −0.031] | same |

- **Per category, baseline → candidate strict passes:**
  - Abstention 0→16
  - Query disambiguation 0→16
  - Cross-scope isolation precision 0→16
  - Temporal currentness 8→16
  - Corrected memory 12→16
  - Factual precision 4→12
  - Multi-session 13→24 of 32
  - Unchanged at 0 of 16: conflicting unreconciled statements, multi-hop, irrelevant context
- **Regression:** every recall loss is in **multi-hop**, 16 of 16 queries, with recall falling from 1.0 to 0.5. The candidates keep the fact that names the entity and withhold the bridging fact that carries the answer. The baseline returned both.
- C1 and C2 return identical lists on all 176 queries.

### LongMemEval-S, 500 questions, frozen input `d6f21ea9…`, accepted evaluator (419 scored)

The runner scores the facade's `returned` list. The candidates change the test that pins this behaviour (`test_longmemeval.py`), so the default change flows straight into the accepted lane's numbers.

| Plane, metric | Baseline (accepted value) | C1 | C2 |
| --- | ---: | ---: | ---: |
| Session recall_all@5 | 0.8234 | 0.7422 | 0.7470 |
| Session recall_all@50 | 1.0000 | 0.7494 | 0.7566 |
| Session paired | | +2 / −36, p < 1e-6, Δ −0.081 [−0.110, −0.055] | +2 / −34, Δ −0.076 [−0.105, −0.050] |
| Turn recall_all@10 | 0.7231 | 0.6158 | 0.6325 |
| Turn recall_all@50 | 0.8592 | 0.6205 | 0.6539 |
| Turn paired | | +5 / −50, p < 1e-6, Δ −0.107 [−0.141, −0.074] | +6 / −44, Δ −0.091 [−0.124, −0.060] |
| Turn latest gold first | 0.557 | 0.529 | |
| Mean items returned, session / turn | 45.3 / 206.7 | 2.6 / 5.1 | |

- **Where it regresses (session / turn questions regressed, C1):** temporal reasoning 16 / 20, multi-session 13 / 14, knowledge update 7 / 14. Single-session questions are unchanged.
- **Mechanism:** questions that need two or three gold sessions get one or two back. The others score below half of the best match and are withheld. Top-1 is unchanged (session ndcg@1 0.809 → 0.814), so this is truncation of corroborating evidence, not worse ranking.

### LoCoMo evidence retrieval, 1,536 questions (independent family)

All 1,536 questions are identical to the baseline for both candidates. This harness calls runtime and planner recall below the facade, so the return-selection stage is not exercised. It confirms the candidates leave candidate generation, admission and ranking untouched, and it measures nothing about the selection itself.

## Runtime, cost and stability

- **Latency:** AMB p50 is 97.2 ms for the baseline against 88 to 95 ms for C1 and C2. p95 ranges 120 to 148 ms for all of them. On the holdout, p50 is 61 ms for the baseline against 62 to 64 ms for C1 and C2. Measured back to back on the same shared CPU, the difference is within noise.
- **Ingest and memory:** ingest is unchanged. Peak RSS is about 1.09 GiB in every case, dominated by the AMB process.
- **Context:** downstream context falls by 83%.
- **Stability:** repetitions are deterministic, with 0 case differences.

## Safety and canonical truth

- **No new leaks:** no stale, forgotten or cross-scope result was ever returned. The stage only removes items after admission and ranking, and C1/C2 never surfaced a refused fact. AMB cross-user isolation still passes.
- **Full reference suite (2,580 tests):** C1 has one new failure, `test_evaluation_only_change_keeps_runtime_baseline_equivalence`. The repository's own guard reports that C1 *"changes the protected Runtime Baseline source surface … and the register declares no successor"* (`api/contract.py`, `api/surface.py`, `return_selection.py`, `runtime/return_selection.py`). The other four failures happen identically on the baseline in this environment: AMB's environment bundles `fastembed`, which the Mem0 stub tests forbid, and the detached worktree's history lacks the register's first-parent ancestry.
- **Behaviour change for every caller:** the default return changes for all callers. The facade numbers this contract 1.9.0, skipping the 1.7.0 and 1.8.0 reserved by the unmerged v8 stack. That ordering needs an explicit governance decision.

## Required changes

These are architectural; the holdout specifics stay sealed.

1. **Do not withhold corroborating evidence by default.** A relative floor of half the best lexical score suits single-fact lookups, but cuts evidence-aggregation questions to one or two items: multi-session, temporal, knowledge-update and multi-hop. Either keep the 1.4.0 ranked prefix as the default and make selection opt-in per caller, or make sufficiency query-shape aware. Any redesign must be re-measured on LongMemEval and this holdout, not on AMB alone.
2. **Treat the LongMemEval change as a protocol change.** The runner's scored list changes with the default. Accepted LongMemEval rows must not move without a new lane version.
3. **Declare a Runtime Baseline successor** so the repository's own equivalence guard passes. Resolve the 1.9.0 numbering against the v8 stack.
4. **Name what stays unfixed.** Supersession exclusion (AMB 0/3), type routing (0/6), unreconciled conflicting statements (0/16 on the holdout, older still ranked first) and multi-hop are untouched by this stage. They need currentness, typed and relational signals, not a lexical floor.

**What is good and should be kept:** abstention, disambiguation, in-scope precision, 83% less context, no latency cost, no safety regression, deterministic behaviour, general-purpose code with no benchmark identifiers, and an honest opt-out via `return_selection="ranked_prefix"`.

## Evidence in this directory

- `baseline-7c06468/`: AMB, LoCoMo, LongMemEval controls (500) and holdout aggregate.
- `candidates/c1-4bd38e6/` and `candidates/c2-eaf60e4/`: AMB repetitions with execution identity, paired comparisons, taxonomy, LongMemEval reports (C1) and holdout aggregates.
- `holdout/COMMITMENT.md`: the pre-candidate hashes. The cohort is released after the final candidate.
- `tools/`: `amb_taxonomy.py` and `paired.py`.

This review is an independent recommendation. It confers no acceptance, and no dashboard or leaderboard row changes.
