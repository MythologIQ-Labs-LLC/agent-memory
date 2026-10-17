# #819 independent evaluation: C8 (ranking policy 3.5.0, reciprocal-rank fusion with a cost budget)

**Recommendation: CHANGES REQUIRED.**

On the sealed cohort, C8 delivers a real ranking improvement. It is not uniform: LongMemEval turn-level top-3 regresses. Under the default selection the improvement does not reach the caller, and C8 keeps the recall loss that made C6 CHANGES REQUIRED.

**Ranking (independently confirmed on e5).** Fusion ranks needed evidence higher.
- **Against C6+sem (default selection):** depth recall@5 rises by +0.076 [+0.042, +0.117] on the sealed e5 cohort. All needed evidence is in the top 5 on 11 more queries and 0 fewer.
- **Against C4+sem under `ranked_prefix`:** the same gain, with identical discovery.
- **No e5 losses:** fusion causes no strict loss against its own base in either mode.

**Discovery and selection (unchanged from C6).** Under the default `relevance_sufficient` selection:
- **Returned sets equal C6's** on 199 of 208 e5 queries. Recall at the budget is identical: Δ 0.000.
- **Against C4+sem, the essential comparator:**
  - needed recall at the budget falls by −0.227 [−0.287, −0.169];
  - discovery falls by −0.086 [−0.129, −0.050];
  - strict is +19 / −17 (p = 0.87, not significant).
- **Ranking gains are withheld.** C8 ranks 170 needed memories into its top 5 (C4+sem: 164, C6+sem: 152), then withholds 51 of them as insufficient (C4+sem: 11). The reason: sufficiency is decided on the 3.4.0 order, and C6's capped proposals, not fusion's dense scores, decide what counts as semantically found.

**LongMemEval-S 500 agrees, and adds a regression.**
- **No gain where the returned set is fixed.** Against C6+sem, recall at @10 and @50 is identical, because the returned sets are the same.
- **Top-3 regression at turn granularity.** Fusion reshuffles near the top, and turn recall_all@3 falls significantly:
  - against C6+sem: +16 / −41, p = 0.0013;
  - against C4+sem: +17 / −42, p = 0.0015;
  - against C4 default: +16 / −42, p = 0.0009.
- **Top-5 is not significantly better** (+23 / −13 against C6+sem).
- **The C6 deficit stays.** Against C4+sem, C8 inherits C6's turn recall_all@50 deficit: 0 / −19, p = 4e-6.

**Safety and correctness hold:**
- 0 leaks;
- route off identical to C4;
- deterministic across repeat runs;
- no temporal reversal, because fusion is skipped for time-ordered intents.

**Near-miss promotion is real but modest.** It is visible in rank, not in the default returned set.

| Item | Value |
| --- | --- |
| C8 (frozen) | `24d4dd2697047fc622a6087f7005775133b60209`, branch `claude/eager-dirac-bftkfg-819-c8`. Runtime equals `f2626d0e`; `reference/` is unchanged after it |
| Comparators | C4 `bc2be631` (route off; route on under both selections); C6 `171e67db` (route on under both selections) |
| C8 mechanism | Ranking policy 3.5.0: RRF (k = 60) of admitted-set BM25, shared-evidence and dense lists, below the temporal applicability tier and exact identity. Skipped for time-ordered intents (review fix `f2626d0e`) and above 512 admitted. The semantic route's similarities are reused. Under `relevance_sufficient`, sufficiency is decided on the 3.4.0 order. C6's rank-bounded proposal policy is unchanged |
| Semantic configuration | `semantic_retrieval="required"`, `multi-qa-MiniLM-L6-cos-v1@b207367`, config digest `sha256:74477054…`. Pins identical to C6 (onnxruntime 1.30.0, tokenizers 0.23.2, numpy 2.4.6, protobuf 7.36.2); Python 3.12.3 |
| Runner blobs | `run_longmemeval.py` `6b9c2373` and `amb_agent_memory_bridge.py` `3d9ccb31`, identical across C4, C6 and C8 |
| Evaluator | `session_011h1ADQyj3ZTu9UHgBAhocF`. It took no part in C8, and it authored e5 before fetching C8 |

## Sealing, independence and resource isolation

**Sealing and arms:**
- **e5 hash commitment:** `fe056bc4` (14:11:52Z), before C8 was fetched, checked out or run, and before any C8 record was read. A construction dry run on A found 0 operation failures and 0 evaluation failures, and no case changed after it.
- **Arms addendum:** `8f217f08` (14:13:08Z), after reading `PREREGISTRATION-C8.md` and before any candidate ran. It fixes eight arms plus a repeat, and the `ranked_prefix` wrapper hash (`run_rp.py` `f756a5c6…`). The wrapper sets only `recall`'s default `return_selection`; scorer bytes are unchanged.
- **Hash checks:** all hashes were verified at launch by `sha256sum -c` (`e5/run_e5.out.txt`).

**Isolation**, checked before launch at the owner's request:
- **VM:** a Firecracker microVM with its own kernel, 4 vCPUs and 16 GB RAM (15.5 GB free).
- **Storage:** dedicated virtio block devices; no network or shared filesystem.
- **Model:** a local ONNX model on the VM's own disk; no model server, network inference or paid API, so no provider quota applies.
- **CPU contention:** steal was 0.25% under a 20-second 4-core load while the competitive bench's Letta and MemPalace runs were active in their own container. Every e5 arm's steal is logged in `run_e5.out.txt` and stayed between 0.085% and 0.211%.
- **Limit of the check:** the physical host may be shared, which a guest cannot see, but no contention was measurable.

**LongMemEval and probes.** Both LongMemEval runs (15:54–17:25Z) and the cost and tie probes ran afterwards, one at a time, in the same VM.

## 1. Sealed cohort e5: 208 queries, eight arms and a repeat

**Cohort.** 13 categories × 16 queries, one fresh store per query, `recall(budget=5)`, newly authored:
- multi-evidence, sparse and dense;
- rank depth;
- paraphrase;
- temporal current, ordering and as-of;
- question-shaped interference;
- near-miss with no answer, and near-miss beside the answer;
- fusion boundary;
- cross-scope;
- lifecycle.

**Strict pass** means:
- every needed memory is returned;
- nothing excluded is returned;
- nothing outside the needed and allowed sets is returned;
- the declared order holds among the returned items.

**Decomposition.** For every needed memory, three questions are kept separate:
- **Discovery:** was it admitted at all?
- **Ranking:** is it in the ranked admitted top 5 or top 10?
- **Selection:** was it returned, given it was admitted?

All nine runs had 0 operation failures, 0 evaluation failures, 0 excluded memories returned and 0 excluded text quoted.

| Arm | Strict (of 208) | Discovery | Ranked top 5 | Ranked top 10 | Returned at budget | Selection completeness | Extras | Order violations | Recall p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| C4 default | 70 | 0.708 | 0.568 | 0.674 | 0.360 | 0.509 | 142 | 18 | 6 ms |
| C4+sem, default | 86 | **0.890** | 0.695 | 0.843 | **0.767** | **0.862** | 200 | 16 | 88 ms |
| C4+sem, `ranked_prefix` | 9 | 0.881 | 0.691 | 0.839 | 0.691 | 0.784 | 653 | 16 | 83 ms |
| C6+sem, default | 87 | 0.792 | 0.644 | 0.754 | 0.525 | 0.663 | 154 | 14 | 86 ms |
| C6+sem, `ranked_prefix` | 9 | 0.881 | 0.691 | 0.839 | 0.691 | 0.784 | 653 | 16 | 86 ms |
| **C8+sem, default** | **88** | 0.792 | **0.720** | 0.775 | 0.525 | 0.663 | 154 | **12** | 89 ms |
| **C8+sem, `ranked_prefix`** | 9 | 0.881 | **0.767** | **0.852** | **0.767** | **0.870** | 635 | 14 | 89 ms |
| C8, route off | 70 | = C4 | = C4 | = C4 | = C4 | = C4 | 142 | 18 | 7 ms |

How to read the table:
- **Strict pass under `ranked_prefix`** is near zero for every runtime. A fixed top-5 prefix almost always carries extras. That mode is for rank quality, not for direct return.
- **C6 and C4 under `ranked_prefix` are identical** on every query. C6's policy applies only under the default selection.
- **C8 with the route off equals C4 default** on all 208 returned and admitted lists.
- **C8+sem's repeat run is identical** on all 208 returned lists, admitted top 10s and semantic provenance records.

### Paired comparisons

Strict uses exact McNemar. Deltas are per-query bootstrap 95% CIs, 10,000 resamples, seed 819.

| Pair | Strict W / L (p) | Δ recall at budget | Δ discovery | Δ depth@5 | All needed in top 5, W / L | Same returned set |
| --- | --- | --- | --- | --- | --- | ---: |
| **C4+sem → C8+sem (default)** | 19 / 17 (0.87) | **−0.227 [−0.287, −0.169]** | **−0.086 [−0.129, −0.050]** | +0.040 [−0.006, +0.086] | 11 / 6 | 124 |
| **C4+sem → C8+sem (`ranked_prefix`)** | 0 / 0 | +0.076 [+0.042, +0.117] | 0.000 | **+0.076 [+0.042, +0.117]** | **11 / 0** | 123 |
| C6+sem → C8+sem (default) | 1 / 0 (1.0) | 0.000 | 0.000 | **+0.076 [+0.042, +0.117]** | **11 / 0** | 199 |
| C6+sem → C8+sem (`ranked_prefix`) | 0 / 0 | +0.076 [+0.042, +0.117] | 0.000 | +0.076 [+0.042, +0.117] | 11 / 0 | 123 |
| C4 → C8+sem (default) | **25 / 7 (0.0021)** | +0.155 [+0.104, +0.207] | +0.084 [+0.046, +0.127] | +0.153 [+0.102, +0.205] | 23 / 0 | 154 |
| C4 → C4+sem (default) | 38 / 22 (0.052) | +0.382 [+0.312, +0.451] | +0.171 [+0.119, +0.227] | +0.112 [+0.070, +0.159] | 18 / 0 | 97 |
| C4+sem → C6+sem (default) | 18 / 17 (1.0) | −0.227 [−0.287, −0.169] | −0.086 [−0.129, −0.050] | −0.036 [−0.064, −0.014] | 0 / 6 | 129 |
| C4 → C8 off | identical | 0 | 0 | 0 | 0 / 0 | 208 |

**C4+sem → C8+sem (default), strict by category.**
- **C8 wins:** near-miss beside the answer (7), question-shaped (3), cross-scope (2), lifecycle (2), near-miss no-answer (2), as-of (1), paraphrase (1), ordering (1). These are precision wins from returning fewer extras.
- **C8 losses:** question-shaped (7), temporal current (3), as-of (3), multi-evidence sparse (2), paraphrase (2). These are reach losses.

### Better ranking is not better evidence: the selection block

| Default selection | Needed memories ranked in the admitted top 5 | Of those, withheld as insufficient | Returned at budget (of 236) |
| --- | ---: | ---: | ---: |
| C4+sem | 164 | 11 | 181 |
| C6+sem | 152 | 40 | 124 |
| **C8+sem** | **170** | **51 (30%)** | 124 |

**Where C8's 51 withheld memories fall:**
- question-shaped: 12;
- multi-evidence: 16;
- fusion boundary: 8;
- rank depth: 4;
- temporal: 8;
- paraphrase: 3.

**Why fusion's gain stops at selection.**
- Fusion orders every admitted memory by dense similarity (reused for the whole admitted set).
- Sufficiency is decided on the 3.4.0 order, and "surfaced by a non-lexical route" counts only C6's capped proposals: K ≤ 3, `min_best` 0.40.
- **Rank-depth example.** On 9 rank-depth queries the budget binds on lexical look-alikes. C8 then returns a different five distractors from C6, and never the answer, even when it ranks the answer in its top 5 (4 queries).

### Behaviour on the focus areas (counts of 16 per category)

| Behaviour | C4+sem default | C6+sem default | C8+sem default | C4+sem `ranked_prefix` | C8+sem `ranked_prefix` |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Temporal ordering** (unreconciled, newer must lead): newer first in the returned list | 4 | 4 | **6** | 4 | **7** |
| **As-of:** the earlier state is returned first | 15 | 12 | 12 | 8 | 8 |
| **Temporal current:** stale state returned | 0 | 0 | 0 | 0 | 0 |
| **Near-miss, no answer:** near-miss ranked 1 | 13 | 13 | **15** | 13 | **15** |
| Near-miss, no answer: near-miss returned (false answer) | 14 | 12 | 12 | 16 | 16 |
| **Near-miss beside the answer:** near-miss ranked above the answer | 4 | 3 | 3 | 4 | **5** |
| Near-miss beside the answer: near-miss returned | 14 | 6 | 6 | 15 | 16 |
| **Question-shaped note ranked 1** | 16 | 16 | **14** | 16 | **14** |
| Question-shaped note returned | 16 | 16 | 16 | 16 | 16 |
| Question-shaped: answers returned (recall) | 0.95 | 0.41 | 0.41 | 0.95 | 0.95 |

**Temporal correctness.**
- **No reversal.** In both modes C8's as-of and current-state behaviour equals its own base (C6 default; C4+sem `ranked_prefix`). The review fix holds: fusion is skipped for time-ordered intents.
- **Incidental gain.** Newer-first under unspecified intent improves (4 → 6 and 4 → 7). It is not decided by a temporal stage, and 9–10 of 16 are still wrong.
- **As-of difference between modes.** The default selection still returns the earlier state first more often than `ranked_prefix` (12 against 8). That is a C6/C4 selection property, not C8's.

**Near-miss and negation promotion.**
- Fusion lifts topical near-misses to rank 1 in 15 of 16 no-answer stores (13 before). Under `ranked_prefix` a near-miss outranks the true answer in one more case (5 against 4).
- Under the default selection, the returned near-misses equal C6's. The promotion is visible in rank order and under a binding budget.
- This replicates the developer-side review's note 6 on independent content.

**Question-shaped interference.**
- Fusion slightly reduces question-shaped notes at rank 1 (16 → 14).
- It does not fix C6's slot capture: answers are returned at recall 0.41 under the default selection, against 0.95 for C4+sem.

**Deterministic ties.**
- **Same history:** C8+sem's repeat run is identical on all 208 e5 queries, covering returned lists, admitted top 10s and semantic provenance.
- **Exact fused ties do occur.** A separate tie probe (`probes/tie_probe.py`: 3 stores, 9 queries, written forward and in reverse) found equal fused scores adjacent in the top 5 on 3 of 9 queries.
- **Insertion order did not change C8's fused top 5** on any of the 9 queries, under either selection.
- **The returned set did change on one query** ("Where does the cat sleep?": 5 items forward, 3 reversed) under the default selection. C6 shows the same reversal on that query, plus 3 top-5 order changes. This is pre-existing 3.4.0 / sufficiency behaviour, which C8 inherits rather than introduces.
- **Residual risk.** Tie-breaking still falls back to the uuid digest, so write order remains the last resort (developer review, note 9).

## 2. LongMemEval-S 500

**Configuration.**
- Unchanged runner `6b9c2373`, `--backend agent_memory --corpus-class external_frozen --granularity session --granularity turn`.
- Input sha256 `d6f21ea9…`. Every streaming pass agreed.
- `PYTHONHASHSEED=0`, offline.

**C8 runs** (`candidates/c8-24d4dd2/lme500/`):
- **C8+sem:** revision `24d4dd26`, clean worktree, mode `required`, digest `74477054…`. Wall 4,375 s, user CPU 3,199 s, peak RSS 363 MiB.
- **C8 off:** wall 1,048 s, peak RSS 91 MiB.
- Both exited 0. Each scored 419 questions, with the evaluator's standard exclusions (30 abstention, 51 no-user-target), 0 runtime errors and 0 ingestion failures.

**Comparators.** This lane's committed C4 default, C4+sem and C6+sem runs (`candidates/c6-171e67d/lme500/`): same runner, input, pins and VM type. C4 default there reproduced the earlier host's published run 500/500.

**Route off equals C4.** C8 off returns C4 default's ranked lists on all 500 questions in both planes.

| | C4 | C4+sem | C6+sem | **C8+sem** |
| --- | ---: | ---: | ---: | ---: |
| Session recall_all@3 | 0.7947 | 0.8019 | 0.7995 | 0.8138 |
| Session recall_all@5 | 0.8687 | 0.8807 | 0.8783 | 0.8831 |
| Session recall_all@10 | 0.9069 | 0.9260 | 0.9189 | 0.9189 |
| Turn recall_all@3 | 0.5346 | 0.5322 | 0.5322 | **0.4726** |
| Turn recall_all@5 | 0.6325 | 0.6563 | 0.6372 | 0.6611 |
| Turn recall_all@10 | 0.7589 | 0.7924 | 0.7613 | 0.7709 |
| Turn recall_all@50 | 0.8162 | 0.8711 | 0.8258 | 0.8258 |
| Mean returned (session / turn) | 3.86 / 9.80 | 4.12 / 12.75 | 3.97 / 10.09 | 3.97 / 10.09 |

**Paired results** (wins / losses on recall_all = 1, exact McNemar):

| Pair | Session @3 | Session @5 | Session @10 | Turn @3 | Turn @5 | Turn @10 | Turn @50 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C6+sem → C8+sem | +12 / −6 (0.24) | +4 / −2 (0.69) | identical | **+16 / −41 (0.0013)** | +23 / −13 (0.13) | +8 / −4 (0.39) | identical |
| **C4+sem → C8+sem** | +12 / −7 (0.36) | +4 / −3 (1.0) | +1 / −4 (0.38) | **+17 / −42 (0.0015)** | +23 / −21 (0.88) | +9 / −18 (0.12) | **0 / −19 (4e-6)** |
| C4 → C8+sem | +14 / −6 (0.12) | +8 / −2 (0.11) | +5 / −0 (0.063) | **+16 / −42 (0.0009)** | +25 / −13 (0.073) | +10 / −5 (0.30) | +4 / −0 (0.125) |

Bootstrap Δ recall (`tools/paired.py`, session @5 / turn @10):
- C6+sem → C8+sem: +0.005 [−0.007, +0.017] / +0.010 [−0.007, +0.026];
- C4+sem → C8+sem: +0.002 [−0.010, +0.014] / −0.022 [−0.045, +0.002];
- C4 → C8+sem: +0.014 [0.000, +0.029] / +0.012 [−0.005, +0.031].

**The turn-level top-3 regression.**
- **It hits both single-evidence and multi-evidence questions.**
  - One gold turn: +1 / −8 (p = 0.039).
  - Two or more gold turns: +15 / −33 (p = 0.013).
- **By question type:** temporal reasoning 22, multi-session 10, knowledge update 8, single-session user 1.
- **Mechanism.** Gold turns move from ranks 1–3 down to 4–5. Across all gold items, the mean rank change is −0.15 (216 improved, 203 worse). Fusion moves evidence in both directions near the top. At turn granularity, where many short turns are topically similar, the dense list promotes non-gold turns above gold ones often enough to lose top-3 coverage.
- **Session granularity** shows no such loss.
- **Not covered by the temporal fix.** Temporal-reasoning questions in LongMemEval are not "time-ordered intents" in C8's sense, so fusion applies to them.

**Cost on LongMemEval.**
- **Session recall p50:** C6+sem 2.46 s, C8+sem 2.64 s (+7%).
- **Turn recall p50:** C6+sem 3.16 s, C8+sem 3.26 s (+3%).
- **Wall time:** 4,155 s against 4,375 s (+5%).
- **Where it goes:** cold embedding of each fresh haystack dominates. The increment is the second ranking pass under the default selection, plus fusion.

## 3. Cost near the fusion boundary (400–520 admitted)

**Probe** (`probes/latency_boundary.py`):
- one store per run, where every memory shares a query word, so admitted ≈ N;
- 40 warm recalls at budget 5;
- two repetitions per point, run one after another in this VM.

**Warm p50 in ms** (repetition 1 / repetition 2; peak RSS 316–319 MiB for every arm and point):

| Admitted | C4+sem default | C6+sem default | **C8+sem default** | C8 − C6 | C4+sem `ranked_prefix` | C6+sem `ranked_prefix` | **C8+sem `ranked_prefix`** | C8 − C6 |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 200 | 44.7 / 43.8 | 47.8 / 44.7 | 52.9 / 53.1 | +5 / +8 | 38.5 / 38.8 | 38.5 / 38.3 | 40.5 / 41.2 | +2 / +3 |
| 400 | 79.6 / 85.6 | 83.2 / 82.4 | **100.2 / 96.8** | **+17 / +14 (+17–20%)** | 68.7 / 69.5 | 70.3 / 72.6 | 74.7 / 73.2 | +4 / +1 |
| 450 | 92.3 / 90.2 | 93.4 / 90.6 | **110.4 / 119.7** | **+17 / +29 (+18–32%)** | 76.9 / 77.4 | 77.1 / 76.8 | 84.5 / 82.4 | +7 / +6 |
| 500 | 101.8 / 99.9 | 105.0 / 100.4 | **130.9 / 125.7** | **+26 / +25 (+25%)** | 86.5 / 86.7 | 85.5 / 86.2 | 92.8 / 91.2 | +7 / +5 |
| 520 (fusion `skipped_over_limit`) | 105.0 / 105.1 | 104.9 / 104.5 | 108.7 / 107.1 | +4 / +3 | 90.2 / 92.8 | 87.3 / 88.2 | 89.2 / 91.5 | +2 / +3 |

**Reading:**
- **200 admitted:** C8 meets the preregistered I5 bound (p50 ≤ C6+sem + 10 ms) in both repetitions.
- **400–500 admitted, default selection** (the shipped configuration): C8 costs **+14 to +29 ms (+17% to +32%)** over C6+sem. That exceeds the 1.15× ratio C8's preregistration applied at 1,000 memories, the point where fusion is skipped and the bound is therefore vacuous (developer review, finding 3).
- **Where the cost comes from:** the second (3.4.0) ranking pass that the default selection needs. Under `ranked_prefix` the increment is only +1 to +7 ms.
- **Discontinuity at 512.** Above `FUSION_MAX_ADMITTED`, fusion is silently skipped. Cost falls back to C6's, and ranking reverts to 3.4.0. A store that grows past 512 matching memories therefore changes its ranking regime abruptly. This is recorded per memory as `fusion.status`, but it is not visible in the semantic posture.
- **Memory:** fusion adds none.

## 4. Verdict and integration recommendations

### Verdict: CHANGES REQUIRED

C8's fusion stage is a safe, deterministic **ranking** component that helps on short stores but not uniformly. Two things support that:
- on fresh sealed data it moves needed evidence up (e5 depth@5 +0.076 against both C6+sem and C4+sem `ranked_prefix`, with no strict losses against its own base);
- with the route off, or for time-ordered intents, it changes nothing.

It does not make the candidate acceptable for integration qualification, for four reasons.

1. **No evidence gain under the default selection, and C6's recall defect unresolved.**
   - Under `relevance_sufficient`, C8 returns C6's sets (199/208 identical on e5; identical @10/@50 on LongMemEval).
   - It therefore keeps C6's loss against C4+sem, the essential comparator: e5 recall −0.227 [−0.287, −0.169], discovery −0.086, and LongMemEval turn @50 0 / −19 (p = 4e-6). The C6 review's mandatory changes 1–5 are not addressed.
   - **Better ranking, no better evidence:** 51 needed memories that C8 ranks in its top 5 are withheld as insufficient.
2. **A significant top-rank regression on public long-haystack data.** LongMemEval turn recall_all@3 falls against C6+sem (+16 / −41), C4+sem (+17 / −42) and C4 default (+16 / −42), all with p ≤ 0.0015. Single-evidence and multi-evidence questions are both affected, so the fused order is not uniformly better.
3. **Cost near the boundary.** Under the default selection, C8 costs +17% to +32% over C6+sem at 400–500 admitted. The preregistered cost criterion was evaluated only where fusion is skipped.
4. **A ranking-regime cliff at 512 admitted.** It is silent at the API level.

**Not REJECT**, because:
- there are no safety, governance or temporal-correctness failures;
- determinism holds;
- route off is identical to C4;
- the ranking mechanism itself is worth carrying forward.

### Distinguishing the effects (e5, default selection unless stated)

| Effect | C8 against C6+sem | C8 against C4+sem |
| --- | --- | --- |
| Ranking (depth@5) | **+0.076 [+0.042, +0.117]** | +0.040 [−0.006, +0.086]; `ranked_prefix`: **+0.076 [+0.042, +0.117]** |
| Discovery (needed admitted) | 0.000 | **−0.086 [−0.129, −0.050]**; `ranked_prefix`: 0.000 |
| Selection completeness (returned / admitted) | 0.663 = 0.663 | 0.663 against **0.862** |
| Evidence returned at budget | 124 = 124 of 236 | 124 against **181** of 236 |

### Exact-head integration recommendations (for the delivery lane)

- **Do not integrate `24d4dd2697047fc622a6087f7005775133b60209`.** Do not declare a Runtime Baseline successor for it. Do not promote any number from it.
- **Components that can be carried forward** into a newly preregistered successor, all validated here:
  - ranking policy 3.5.0 with the time-ordered-intent skip (`f2626d0e`);
  - similarity reuse;
  - the single ranking pass under `ranked_prefix`;
  - route-off identity.
- **Required in that successor:**
  1. **Make ranking gains reachable, without inheriting C6's recall loss.** Selection must credit what fusion ranks, or be decided on the order that is returned. On fresh held-out data it must be non-inferior to C4+sem in recall and discovery (lower 95% bound ≥ −0.02), keeping the C6 review's criteria.
  2. **No significant top-rank loss on LongMemEval-S.** Turn and session recall_all@3, @5 and @10, against C6+sem, C4+sem and C4 default. State in advance how the dense list's influence is bounded at turn granularity. Do not tune it against LongMemEval or e5.
  3. **Cost at the boundary.** Measure I5 at 400–500 admitted under the default selection, and either meet ≤ 1.15× C6+sem or vectorise or remove the second ranking pass.
  4. **Boundary transparency.** Report the 512-admitted fallback in `semantic_retrieval_posture()` and in recall-level summaries. Preregister its behaviour, including any hysteresis.
  5. **Ties.** Break fused ties by a meaningful signal before the uuid digest.
  6. **Carry the developer review's should-fix items:** posture and docstring wording (now updated in `24d4dd26`), the unreachable dense-failure fallback, the similarity cache key, and the `base_ranked_admitted` labelling.
- **Unchanged dependencies from C6:**
  - rebase onto #805 → #815 → #816 and re-run the security replays;
  - declare a Runtime Baseline successor for the protected files;
  - version the LongMemEval lane, which should also record the ranking policy and fusion status;
  - an approved AMB semantic-on adapter option.

### Acceptance criteria for a successor (ACCEPTABLE FOR INTEGRATION QUALIFICATION)

**On a fresh independent sealed cohort (e6):**
- strict non-inferior to C4+sem and C4 default;
- recall and discovery non-inferior to C4+sem (lower bound ≥ −0.02);
- multi-evidence and question-shaped recall ≥ C4+sem's;
- 0 leaks;
- no temporal reversal against its base in either selection;
- route off identical.

**On LongMemEval-S 500, both planes:** no significant loss at @3, @5 or @10 against C4+sem, C6+sem or C4 default.

**Cost:** ≤ C6+sem + 10 ms at 200, and ≤ 1.15× C6+sem at 400–500 admitted under the default selection.

**Determinism:** two runs and two hosts.

Acceptable for qualification would still not make the candidate an activated runtime baseline.

## 5. Cohort integrity

| Cohort | Status |
| --- | --- |
| v1–v3, e4 | Spent |
| **e5** | **Spent with this review.** The aggregates and per-case results are published here. Content stays with this evaluator, and e5 must not be used for tuning or for qualifying a later candidate |
| v4 | Engineering's sealed cohort. Reserved and unopened; not used here |
| Evaluator probes (C6 review) | Development-visible; not used here |

A fresh independent cohort will be authored and committed when the next candidate is frozen.

This is an independent recommendation. It confers no acceptance and changes no register, feed, dashboard or leaderboard row.
