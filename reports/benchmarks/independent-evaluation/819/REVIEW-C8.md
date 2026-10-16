# #819 independent evaluation: C8 (ranking policy 3.5.0, reciprocal-rank fusion with a cost budget)

**Recommendation: CHANGES REQUIRED.**

C8 delivers a real, clean ranking improvement. Under its default selection that improvement does not reach the caller, and C8 keeps the recall loss that made C6 CHANGES REQUIRED.

**Ranking (independently confirmed).** Fusion ranks needed evidence higher.
- **Against C6+sem (default selection):** depth recall@5 rises by +0.076 [+0.042, +0.117] on the sealed e5 cohort. All needed evidence is in the top 5 on 11 more queries and 0 fewer.
- **Against C4+sem under `ranked_prefix`:** the same gain, with identical discovery.
- **No losses:** fusion causes no strict loss against its own base in either mode.

**Discovery and selection (unchanged from C6).** Under the default `relevance_sufficient` selection:
- **Returned sets equal C6's** on 199 of 208 e5 queries. Recall at the budget is identical: Δ 0.000.
- **Against C4+sem, the essential comparator:**
  - needed recall at the budget falls by −0.227 [−0.287, −0.169];
  - discovery falls by −0.086 [−0.129, −0.050];
  - strict is +19 / −17 (p = 0.87, not significant).
- **Ranking gains are withheld.** C8 ranks 170 needed memories into its top 5 (C4+sem: 164, C6+sem: 152), then withholds 51 of them as insufficient (C4+sem: 11). The reason: sufficiency is decided on the 3.4.0 order, and C6's capped proposals, not fusion's dense scores, decide what counts as semantically found.

{{LME_SUMMARY}}

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

{{ISOLATION_LME}}

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

{{TIES}}

## 2. LongMemEval-S 500

{{LME_SECTION}}

## 3. Cost near the fusion boundary (400–520 admitted)

{{COST}}

## 4. Verdict and integration recommendations

{{VERDICT}}

## 5. Cohort integrity

| Cohort | Status |
| --- | --- |
| v1–v3, e4 | Spent |
| **e5** | **Spent with this review.** The aggregates and per-case results are published here. Content stays with this evaluator, and e5 must not be used for tuning or for qualifying a later candidate |
| v4 | Engineering's sealed cohort. Reserved and unopened; not used here |
| Evaluator probes (C6 review) | Development-visible; not used here |

A fresh independent cohort will be authored and committed when the next candidate is frozen.

This is an independent recommendation. It confers no acceptance and changes no register, feed, dashboard or leaderboard row.
