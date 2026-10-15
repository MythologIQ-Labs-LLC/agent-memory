# #819 independent evaluation: C3 (query-shape-aware evidence sets)

**Recommendation: CHANGES REQUIRED. The scope is much narrower than for C1/C2.** C3 fixes the regression that blocked C1 and C2: native LongMemEval-S now improves over baseline A on both planes, with significant paired results. AMB and the precision gains are retained, and an unseen cohort confirms the gains, with zero safety leaks.

One generalisation defect remains, plus governance items. On the new sealed cohort the default return **withholds evidence whose wording does not overlap the query**:

- Multi-evidence aggregation is 0/16 against A's 8/16, and half those queries return nothing.
- Paraphrase recall falls from 1.0 to 0.25.

Neither AMB nor LongMemEval exposes this.

| Item | Value |
| --- | --- |
| Baseline A | `7c06468aae1aed0d2115c42f9588fbbe8417657e` |
| C2 | `eaf60e4dd001c02ce00bb36f15f800996bf77da3` (comparison only) |
| C3 | `6a2255c0f46daa1d546758daa93f4402fed14108` (evidence head `8549e942`), selection policy 2.2.0, contract 1.9.0, defaults (semantic route off, recall control off, no extractor) |
| Evaluator | Independent session. It made no runtime changes and read only the freeze notice's summary before the v2 cohort hashes were committed |
| Host | 4 vCPU, 15 GiB RAM, no GPU, CPython 3.12.3. Other benchmark jobs shared the CPU, so latencies are indicative only |

## Configuration checks

- C3 runs from a clean detached worktree. Its venv is a hard-linked copy of A's, with only the editable path repointed, and `pyproject.toml` is identical.
- These files have identical blobs in A and C3:
  - the AMB bridge, `reference/amb_agent_memory_bridge.py` (`3d9ccb3`)
  - `run_amb_external.py`
  - `amb_retrieval_no_llm.py`
  - `scripts/run_amb_local_evidence.py`
  - `run_longmemeval.py`
- C3 also adds `integrations/amb-upstream/*.patch`, an upstream-submission package. The harness never loads it.
- The v2 cohort's SHA-256 values were verified (`sha256sum -c`) before every run.

## Hidden holdout v2: 208 queries, 192 scenarios, public facade, budget 5

The cohort was committed by hash in `holdout-v2/COMMITMENT.md` at commit `34688065` (17:30:14 UTC), before C3 was checked out. The v1 cohort is spent, because its C1/C2 category aggregates were published. Only aggregates appear here.

| Metric | A | C2 | C3 |
| --- | ---: | ---: | ---: |
| Strict pass | 59 | 151 | **161** |
| Mean precision | 0.454 | 0.673 | 0.787 |
| Mean recall | 0.985 | 0.796 | 0.871 |
| Hard gates: cross-scope, forgotten, stale | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| Evaluation failures and operation refusals | 0 | 0 | 0 |
| Paired against A | | +105 / −13 | **+110 / −8**, p < 1e-6, Δ pass 0.49 [0.41, 0.57] |
| Paired against C2 | | | +10 / −0, p = 0.002 |
| Δ recall against A, 95% CI | | | −0.114 [−0.159, −0.068] |

Strict passes by category, A / C2 / C3:

| Category | A | C2 | C3 |
| --- | ---: | ---: | ---: |
| Factual precision | 8 | 16 | 16 |
| Disambiguation | 0 | 16 | 16 |
| Corrected memory | 7 | 16 | 16 |
| Temporal currentness | 10 | 8 | 16 |
| Conflicting, newer first | 16 | 16 | 16 |
| Cross-scope isolation | 0 | 16 | 16 |
| Abstention | 7 | 14 | 16 |
| Multi-session (of 32) | 0 | 26 | 26 |
| Irrelevant context | 3 | 3 | 3 |
| Multi-hop † | 0 | 16 | 16 |
| **Multi-evidence aggregation** | **8** | **0** | **0** |
| **Paraphrase recall** | 0 | 4 | 4 |

- **Regression.** All 8 of C3's losses against A are in **multi-evidence aggregation**.
  - Recall there falls from 0.83 to 0.33.
  - 8 of the 16 queries return nothing.
  - The other 8 return 3 or 4 items but omit required facts.
  - The answers need several separately stored facts that share few words with the question. The relative-sufficiency floor therefore keeps only the lexically closest fact, or abstains.
- **Paraphrase recall.** The fact is withheld in 12 of 16 queries, and 7 of them return nothing (recall falls from 1.0 to 0.25). A failed these queries only because it also returned a distractor.
- **Abstention shares the mechanism.** C3's abstention gain, 7 to 16, comes partly from the same behaviour: low query overlap leads to an empty return. The candidate cannot tell "nothing relevant" apart from "relevant, but worded differently".
- **† Cohort limitation (mine).** In v2's multi-hop items the bridging fact shares words with the question ("new table"), so the category did not test true bridging. Its 16/16 is **not** evidence that multi-hop works. The engineering session also reports multi-hop as unsolved.

## AMB PrecisionMemBench single-turn, 77 cases (known target)

| Metric | A | C2 | C3 |
| --- | ---: | ---: | ---: |
| Correct | 15 | 39 | **38** |
| Active passes (of 43) | 4 | 21 | 21 |
| Mean precision | 0.181 | 0.541 | 0.522 |
| Mean recall | 0.954 | 0.878 | **0.942** |
| Mean context tokens | 542 | 91 | 124 |
| Paired against A | | | +24 / −1, p ≈ 2e-6; Δ precision +0.33 [0.24, 0.42]; Δ recall −0.01 [−0.10, +0.08] |
| Paired against C2 | | | +3 / −4, p = 1.0 |

- **Reproducibility:** the two repetitions are byte-identical apart from timing (0 differences).
- **By category against C2:** relation expansion goes 1 → 2, ranking stability 3 → 1, and the rest are unchanged.
- **Still 0 for A, C2 and C3:** supersession chain exclusion (3), type routing and open questions (6), and counter-signal (2).

## LongMemEval-S, 500 questions, frozen input `d6f21ea9…`, accepted evaluator (419 scored, 0 failures)

| Plane, metric | A (accepted value) | C2 | C3 |
| --- | ---: | ---: | ---: |
| Session recall_all@5 | 0.8234 | 0.7470 | **0.8616** |
| Session recall_all@10 | 0.8926 | 0.7542 | **0.9045** |
| Session paired against A | | +2 / −34 | **+23 / −7**, p = 0.005, Δ +0.038 [0.014, 0.064] |
| Turn recall_all@10 | 0.7231 | 0.6325 | **0.7637** |
| Turn paired against A | | +6 / −44 | **+24 / −7**, p = 0.003, Δ +0.041 [0.014, 0.067] |
| Session recall_all@50 | 1.0000 | — | 0.9165 |
| Turn recall_all@50 | 0.8592 | 0.6539 | 0.8473 |
| Mean items returned, session / turn | 45.3 / 206.7 | | 4.7 / 13.2 |

- **Recommendation 1 of the C1/C2 review is met on LongMemEval.**
  - Session multi-session recall goes from 0.678 to 0.777, and temporal reasoning from 0.803 to 0.843.
  - Turn multi-session goes from 0.537 to 0.603.
  - The independent run reproduces the engineering session's figures, 0.862 and 0.764.
- **Recall at depth still falls.** C3 returns about 5 items per session question against 45 for A, so session recall_all@50 drops from 1.0 to 0.917.
  - Callers that consume a long ranked list still lose evidence.
  - The scored list therefore still changes under the accepted lane, which is why a lane version is still needed.

## Runtime, cost and stability

- **Latency:**
  - Holdout recall p50 is 60 ms for A, C2 and C3. p95 is 92 ms for C3 against 136 ms for A.
  - LongMemEval took 3,000 s for C3 against 3,089 s for C2.
  - Peak RSS for LongMemEval was 92 MiB.
  - All of this was measured on a shared CPU and is indicative only.
- **Determinism:** AMB repetitions show 0 differences.

## Safety and canonical truth

- **Leaks:** no cross-scope, forgotten or stale result appears on the holdout, and AMB's cross-user isolation still passes.
- **Full suite (2,633 tests):** there is one new failure, `test_evaluation_only_change_keeps_runtime_baseline_equivalence`, the same governance guard as C1. The other four fail identically on A in this environment:
  - two `fastembed`-related Mem0 stub errors
  - two register-ancestry failures in the detached worktree

## Required changes

These are architectural; the holdout specifics stay sealed.

1. **Do not let the sufficiency floor withhold evidence that merely has low wording overlap.** A floor relative to the best lexical score cannot tell irrelevant items from paraphrased or aggregate evidence.
   - Possible directions: a semantic or alias signal before the floor applies; a minimum-return rule for enumerative or aggregate query shapes ("which …s", "all", plural objects); or caller opt-in.
   - Re-measure on a fresh cohort that the next candidate has not seen, not on v2.
2. **Separate "nothing relevant" from "nothing lexically close".** Some of the abstention gain is the same behaviour that withholds paraphrased facts. Abstention should rest on positive evidence of irrelevance.
3. **Governance, unchanged from C1/C2:**
   - Declare a Runtime Baseline successor, since the equivalence guard fails.
   - Resolve 1.9.0 numbering against the v8 stack.
   - Version the LongMemEval lane, because the scored list changes (session recall_all@50 falls from 1.0 to 0.917).
4. **Name what stays unfixed:**
   - AMB supersession (0/3), type routing (0/6) and counter-signal (0/2).
   - Multi-hop bridging: untested by v2, and reported unsolved by engineering.
   - Untyped supersession.

**What should be kept:**
- the LongMemEval recovery, now above A on both planes
- AMB precision with recall restored to 0.94
- temporal currentness 16/16 on the unseen cohort
- zero safety regressions
- deterministic behaviour
- the exact `ranked_prefix` opt-out

**Cohort status:** v2's category aggregates are published here, so v2 is now spent for any candidate frozen after this review. The next candidate needs a new sealed cohort.

## Evidence

- `holdout-v2/COMMITMENT.md`: hashes committed before C3.
- `baseline-7c06468/holdout-v2-aggregate/`, `candidates/c2-eaf60e4/holdout-v2-aggregate/` and `candidates/c3-6a2255c/holdout-v2-aggregate/`: aggregate summaries and paired comparisons.
- `candidates/c3-6a2255c/amb/`: two repetitions with execution identity, and paired comparisons against A and C2.
- `candidates/c3-6a2255c/lme500/`: the 500-question report, exec record and paired comparisons against A and C2.
- `candidates/c3-6a2255c/unittest/`: the full-suite log.

This is an independent recommendation. It confers no acceptance and changes no dashboard or leaderboard row.
