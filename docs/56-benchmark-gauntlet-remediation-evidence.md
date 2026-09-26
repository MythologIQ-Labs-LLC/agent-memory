# Benchmark-Gauntlet Remediation Evidence

Status: living record for #537. Each remediation slice appends its before/after replay here. The pre-remediation evidence is immutable:

```text
LongMemEval_S  Agent Memory f73b872  input sha256 d6f21ea9…c442  reports/benchmarks/longmemeval/longmemeval-s-full-f73b872.*
AgentMemBench  Agent Memory 03197cd  input sha256 33632710…ca2a6  reports/benchmarks/agentmembench/memdialogue-v2-*-03197cd.json
```

Replays are executed from a clean git worktree pinned at the candidate revision. Paired comparisons are regenerated from committed artifacts:

```bash
python reference/compare_longmemeval_reports.py \
  reports/benchmarks/longmemeval/longmemeval-s-full-f73b872.json \
  reports/benchmarks/longmemeval/longmemeval-s-full-f73b872.rows.json.gz \
  <after>.json <after>.rows.json.gz
```

## Slice 1: explicit ranking policy and temporal tie-break (#538, #531 class A)

Candidate revision `9c2ba707ea24df64a75e2587328a5f8a2051dc57` (PR #540). Evidence is in `reports/benchmarks/replays/538-ranking-policy-9c2ba70/`.

**Change.**

- Post-admission ranking is an explicit, versioned `PostAdmissionRankingPolicy`, version 2.0.0.
- Among candidates equal on every relevance stage, explicit temporal evidence (`valid_at`, else `created_at`) orders newer first before the stable-id fallback. Previously the ascending insertion-counter id favored the earliest-ingested fact.
- The deterministic clock now emits valid, chronologically sortable timestamps.
- Admission, supersession, and authority are unchanged.

### Intended improvement: currentness ordering

| gauntlet | metric | f73b872 | 9c2ba70 |
| --- | --- | --- | --- |
| AgentMemBench conflict (250 pairs) | new-fact rate / staleness | 0.00 / 1.00 | **0.60 / 0.40** |
| LongMemEval_S session | latest-gold-ranked-first (70 KU) | 0.343 | **0.629** |
| LongMemEval_S turn | latest-gold-ranked-first (70 KU) | 0.486 | **0.743** |

On the knowledge-update questions, session and turn show **20 fixed / 0 newly broken** and **18 fixed / 0 newly broken**. The 20 session fixes are exactly the 20 exact-tie failures classified at `f73b872`.

AgentMemBench decomposes the same way:

- 3 of 5 conflict templates are exact ties (role, preference, numeric): fixed.
- 2 of 5 are stale-strictly-higher (location, status): unchanged.

### Regressions (recorded, not hidden)

| gauntlet | metric | f73b872 | 9c2ba70 | paired Δ [95% CI] |
| --- | --- | --- | --- | --- |
| LongMemEval_S turn | nDCG_any@5 | 0.502 | 0.484 | −0.018 [−0.035, −0.002] |
| LongMemEval_S session, KU slice | recall_all@5 | 0.931 | 0.889 | (3 questions) |
| LongMemEval_S turn, multi-session | recall_all@10 | 0.322 | 0.306 | |
| synthetic LoCoMo-schema fixture | multi-route MRR Δ vs lexical | +0.067 | −0.083 | |

Mechanism: newer, equally scored *non-gold* items now outrank older gold evidence. Among candidates with no relevance distinction, recency is no better a guess than insertion order for non-currentness questions. Across all questions whose gold spans several dates, the session plane shows 53 fixed and 8 newly broken latest-first orderings.

### Unchanged

Every other session and turn headline metric has a paired 95% interval that includes zero (for example session recall_all@5 +0.012 [−0.019, +0.041]). There were zero runtime, ingestion, out-of-corpus, or unmapped-admission failures.

### Not addressed by this slice

- **#531 class B.** 26 session-plane knowledge-update failures where stale evidence scores strictly higher. A relevance-tier sweep (ε = 0.05–0.30 relative) did not recover them on either gauntlet without losing retrieval: on AgentMemBench the stale fact is genuinely more lexically relevant to the question.
- **The broader lexical deficit (#538).** Session recall_all@5 is still below the lexical baseline (0.687 vs 0.730).

### Timing

The run shared its host with a concurrent replay for part of its duration. Timing from this slice is **not** performance evidence; #522 owns clean measurements.

## Slice 1b: admitted-set BM25 lexical relevance (#538)

Candidate revision `75bbe87` (branch `recall/538-admitted-bm25`). Evidence is in `reports/benchmarks/replays/538-admitted-bm25-75bbe87/`.

**Change.**

- `PostAdmissionRankingPolicy` 2.1.0 replaces the lexical route's raw token-overlap fraction with Okapi BM25 (k1 = 1.2, b = 0.75) as the lexical relevance stage.
- Document frequencies and length statistics are computed **over the admitted set only**. Facts refused at admission (other scopes, superseded, tombstoned) cannot influence the order of what a caller sees, so the statistic opens no cross-scope information channel. A test proves that foreign-scope text cannot change the ordering.
- Admission, candidate generation, route provenance, and the temporal and stable-id stages are unchanged. There is no LLM, embedding, or network dependency.

### Retrieval (full LongMemEval_S, 500 questions, paired 95% CI)

| plane | metric | lexical | f73b872 | 9c2ba70 | 75bbe87 | Δ vs 9c2ba70 |
| --- | --- | --- | --- | --- | --- | --- |
| session | recall_all@5 | 0.730 | 0.675 | 0.687 | **0.823** | +0.136 [+0.103, +0.172] |
| session | nDCG_any@5 | 0.767 | 0.722 | 0.732 | **0.863** | +0.131 [+0.109, +0.155] |
| turn | recall_all@10 | 0.587 | 0.525 | 0.532 | **0.723** | +0.191 [+0.150, +0.232] |
| turn | nDCG_any@5 | 0.527 | 0.502 | 0.484 | **0.649** | +0.165 [+0.138, +0.192] |

Agent Memory now exceeds the lexical baseline on every headline metric of both planes. Slice 1's turn nDCG@5 regression is more than recovered. AgentMemBench exact_source_recall@5 is 0.889 → 0.899 [0.880, 0.918], an interval that includes the before-value. Failures: zero.

### Regression recorded: currentness ordering gives back part of Slice 1

| gauntlet | metric | f73b872 | 9c2ba70 | 75bbe87 |
| --- | --- | --- | --- | --- |
| LongMemEval_S session | latest-gold-ranked-first | 0.343 | 0.629 | 0.457 |
| LongMemEval_S turn | latest-gold-ranked-first | 0.486 | 0.743 | 0.557 |
| AgentMemBench conflict | new-fact / staleness | 0.00 / 1.00 | 0.60 / 0.40 | 0.20 / 0.80 |

Relative to 9c2ba70, session latest-first has 19 fixed and 45 newly broken; turn has 14 fixed and 43 newly broken. Mechanism: many of Slice 1's currentness wins were exact ties. BM25 now separates those candidates by lexical relevance, and where the stale statement is the more relevant text, it ranks first. Recency is consulted only among relevance-equal candidates, by design: recency is not authority, and ranking is not truth.

**This is a policy trade-off, not a free improvement,** and it is flagged for the maintainer's decision on #538/#531. The policy is versioned, so 2.0.0 (currentness among ties, weaker retrieval) and 2.1.0 (stronger retrieval, currentness only among exact ties) remain distinguishable in every recall's ranking evidence.

### #531 class B disposition: explicit product limitation

Post-admission ranking cannot and must not infer which of two independently written, contradictory, both-admitted facts is current. The evidence:

- A relevance-tier sweep (ε = 0 to 0.30) did not recover class B without losing retrieval.
- On AgentMemBench the stale statement is genuinely the more relevant text.

Currentness for such writes is a **write-time** contract:

- a governed correction (`correct()`), which supersedes and is refused at admission as `superseded_not_current`; or
- caller-declared temporal intent, such as `valid_at` on the write or an explicit "latest" query mode. That would be a new, separately governed feature, not a ranking heuristic.

Benchmarks that write contradictory facts as independent remembers measure this limitation, and results should be read that way. Class B stays open on #531 as a product-contract item, not a ranking defect.
