# #819 independent evaluation: C4 (selection policy 2.3.0)

**Recommendation: CHANGES REQUIRED.** C4 is statistically indistinguishable from C3 on everything measured here:

- It gives an identical verdict on all 208 queries of a new sealed cohort.
- AMB is +1 (39 against 38).
- LongMemEval is +4/−1 (session) and +5/−7 (turn), neither significant.

C4 keeps C3's gains over baseline A on all three benchmarks. It does **not** fix the defect found in C3, and that defect now replicates on fresh content: the default return withholds evidence whose wording does not overlap the query. Both multi-evidence aggregation and paraphrase recall fall to recall 0.17 and 0.00.

| Item | Value |
| --- | --- |
| Baseline A | `7c06468aae1aed0d2115c42f9588fbbe8417657e` |
| C3 | `6a2255c0f46daa1d546758daa93f4402fed14108` |
| C4 | `bc2be6319a3eda96731fdb235f4feba882bcb9be` (evidence head `9942a8a6`), selection policy 2.3.0, contract 1.9.0, defaults |
| Evaluator | Independent session. It did not read `FREEZE-C4.md` before committing v3 |
| Host | 4 vCPU, 15 GiB RAM, no GPU. CPU shared with competitor jobs, so latencies are indicative only |

## Configuration checks

- C4 runs from a clean detached worktree with a hard-linked baseline venv. Only the editable path is repointed, and `pyproject.toml` is identical.
- These blobs are identical to A's:
  - `amb_agent_memory_bridge.py` (`3d9ccb3`)
  - `run_amb_external.py` (`0c7b438`)
  - `amb_retrieval_no_llm.py` (`1d3584f`)
  - `run_amb_local_evidence.py` (`fbf6d7c`)
  - `run_longmemeval.py` (`6b9c237`)
- The v3 cohort hashes were verified before the run.

## Hidden holdout v3: 208 queries, new sealed cohort

The hashes were committed in `holdout-v3/COMMITMENT.md` (commit `e626e453`, 18:32:34 UTC), before C4 was checked out. v3 is newly authored, and its multi-hop bridges share **no content word** with the question, which removes v2's limitation. Aggregates only.

| | A | C2 | C3 | **C4** |
| --- | ---: | ---: | ---: | ---: |
| Strict pass (of 208) | 49 | 136 | 135 | **135** |
| Mean precision | 0.449 | 0.796 | 0.793 | 0.793 |
| Mean recall | 0.926 | 0.788 | 0.788 | 0.788 |
| Hard-gate leaks | 0 | 0 | 0 | 0 |
| Paired against A | | | | +94 / −8, p < 1e-6; Δ recall −0.138 [−0.188, −0.091] |
| Paired against C3 | | | | **0 / 0** (identical on all 208) |
| Paired against C2 | | | | +6 / −7, p = 1.0 |

By category (strict passes, A / C2 / C3 / C4):

| Category | A | C2 | C3 | C4 |
| --- | ---: | ---: | ---: | ---: |
| Factual precision | 1 | 16 | 16 | 16 |
| Disambiguation | 0 | 8 | 14 | 14 |
| Corrected memory | 11 | 16 | 16 | 16 |
| Temporal currentness | 7 | 16 | 16 | 16 |
| Abstention | 3 | 16 | 16 | 16 |
| Multi-session (of 32) | 3 | 32 | 32 | 32 |
| Cross-scope isolation | 16 | 16 | 16 | 16 |
| Irrelevant context | 0 | 16 | 9 | 9 |
| **Multi-evidence aggregation** | **8** (recall 0.94) | 0 (0.17) | 0 (0.17) | **0 (0.17)** |
| **Paraphrase recall** | 0 (recall 0.75) | 0 (0.00) | 0 (0.00) | **0 (0.00)** |
| **Multi-hop (bridge disjoint from query)** | 0 (0.50) | 0 (0.50) | 0 (0.50) | 0 (0.50) |
| **Conflicting, newer first** | 0 | 0 | 0 | 0 |

- **The withheld-evidence defect replicates.** It appeared on v2 for C3 and now appears on a second, independently authored cohort for C2, C3 and C4 alike. A returns most of the paraphrased and aggregate evidence. Every candidate withholds it.
- **Multi-hop bridging is unsolved for every runtime,** A included. Every runtime returns the fact that names the entity and none returns the bridge. That agrees with the engineering session's own report. My v2 multi-hop numbers for C3 were an artifact of lexical overlap and are superseded by this.
- **Ordering conflicting statements is unsolved for every runtime.** No runtime ranks the newer of two unreconciled statements first.

## AMB PrecisionMemBench, 77 cases

| | A | C3 | **C4** |
| --- | ---: | ---: | ---: |
| Correct | 15 | 38 | **39** |
| Active passes | 4 | 21 | 22 |
| Precision / recall | 0.181 / 0.954 | 0.522 / 0.942 | 0.528 / 0.942 |
| Paired | | | against A +25 / −1 (p ≈ 1e-6); against C3 +1 / −0 |

The two repetitions show 0 differences.

## LongMemEval-S, 500 questions, accepted evaluator (419 scored, 0 failures)

| | A | C3 | **C4** |
| --- | ---: | ---: | ---: |
| Session recall_all@5 | 0.8234 | 0.8616 | **0.8687** |
| Session paired | | +23 / −7 | **+27 / −8**, p = 0.002; against C3 +4 / −1, p = 0.38 |
| Turn recall_all@10 | 0.7231 | 0.7637 | **0.7590** |
| Turn paired | | +24 / −7 | **+28 / −13**, p = 0.028; against C3 +5 / −7, p = 0.77 |
| Session recall_all@50 | 1.000 | 0.917 | 0.907 |
| Turn recall_all@50 | 0.859 | 0.847 | 0.816 |

Recall at depth falls a little further than in C3. The scored list still changes, so the LongMemEval lane still needs a new version.

## Safety and suite

- **Leaks:** none, on either cohort or AMB.
- **Full suite (2,654 tests):** there is exactly one new failure against A, `test_evaluation_only_change_keeps_runtime_baseline_equivalence`, because the Runtime Baseline successor is not declared. The other four (two Mem0 stub errors and two register-ancestry failures) are identical on A in this environment. See `candidates/c4-bc2be63/unittest/summary.txt`.

## Required changes

These are the same as for C3, now confirmed on two independent cohorts.

1. **Stop withholding low-overlap evidence by default.** Paraphrase recall at 0.00 and aggregation recall at 0.17 on an unseen cohort are generalisation failures that AMB and LongMemEval both miss. The floor needs a non-lexical relevance signal, a minimum return for enumerative or aggregate query shapes, or opt-in use. Keep the current gains while doing so.
2. **Abstain on positive evidence of irrelevance,** not on low overlap.
3. **Governance:** declare the Runtime Baseline successor, resolve the 1.9.0 numbering, and version the LongMemEval lane.
4. **Unfixed in every runtime:** multi-hop bridging, newer-first ordering of conflicting statements, and AMB supersession, type-routing and counter-signal cases.

**Cohort status:** v3 aggregates are published here, so v3 is spent for later candidates.

This is an independent recommendation. It confers no acceptance and changes no dashboard or feed row.
