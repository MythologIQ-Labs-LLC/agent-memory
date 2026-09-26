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

## Slice 2: runtime-owned serialization for one handle (#530)

Candidate revision `59dc80d` (branch `runtime/530-serialized-handle`). Evidence is in `reports/benchmarks/replays/530-serialized-handle-59dc80d/`.

**Change.**

- One `AgentMemory` handle may be shared across threads. The runtime owns a single re-entrant lock covering the connection, governance state, generation compare-and-swap, journal append, and recovery.
- Every public facade operation and every composition entry point acquires that lock.
- `check_same_thread=False` is set only together with that lock. A connection-only change is falsified by the tests: it fails with `nested SQLite substrate transactions are unsupported`.
- No per-thread handles are created, and the isolation, admission, and PAMA paths are unchanged.

| AgentMemBench concurrency (200 records) | workers | 03197cd | 59dc80d |
| --- | --- | --- | --- |
| operation success / materialization | 1, 4, 8, 16 | 0.00 / 0.00 (200 `ProgrammingError` each) | **1.00 / 1.00**, 0 errors |
| throughput (ops/s) | 1 / 4 / 8 / 16 | n/a (all failed) | 69.5 / 62.2 / 69.2 / 67.0 |

**Stated cost.** Throughput is flat across worker counts because writes are serialized: a single handle is correct under concurrency but does not scale with threads. Latency grows with queue depth (p50 14 ms at 1 worker, 218 ms at 16). Multi-writer throughput would need a different design and is not claimed here. The host was shared with a concurrent replay, so the absolute latencies are not performance evidence.

## Slice 3: integrity attestation scaling (#522)

At ~1,000 facts the SQLite runtime re-derived its entire integrity posture on every commit. It serialized every canonical row into one SHA-256 digest (`state_digest`), re-validated the full journal chain, and parsed the whole runtime-state blob twice. Because governed recall also commits a generation (audit and identifier progress), recall paid the same cost.

**Change.** Three integrity layers that one O(state) pass had conflated are now separate. None is removed.

| layer | when | what is verified | cost |
| --- | --- | --- | --- |
| operation integrity | every commit | generation compare-and-swap (a `json_extract` binding read), and the journal **tail** being extended: self-consistent record digest, current generation, bound by the runtime state | O(1) |
| current-state attestation | every commit | `bmerkle-v1` root: 256 buckets of per-row hashes over episodes, facts, and typed relations, plus the identifier counter; maintained from the rows the transaction changed | O(changed rows + touched buckets) |
| recovery-time full verification | every open/recover | root **recomputed from canonical rows** (never from the maintained index), full journal chain, and the state-to-tail binding (new) | O(state), unchanged |

Boundaries:

- The digest index (`digest_rows`, `digest_buckets`) is derived data. It is trusted only after this process rebuilds it, or verifies it row-for-row against canonical rows during recovery. Otherwise the next commit rebuilds it. A tampered index cannot change any recovery answer.
- Every canonical write path is mapped to its table. An unmapped write raises instead of silently escaping the commitment.
- Digests are self-describing. A legacy `sha256:` store recovers under the full-JSON commitment and upgrades at its next commit. Mixed-scheme journal chains verify end to end. An unknown scheme refuses recovery.
- **Stronger than before on one path.** Previously, a canonical row altered out-of-band while a handle was open was folded into the next full digest, which laundered the alteration. It is now absent from the maintained root, so the next recovery refuses.
- `state_digest()` is unchanged and still used by harnesses and qualification.

Tests: `reference/tests/test_incremental_attestation.py`. 8 of its 15 tests fail against the previous runtime. The tamper-refusal tests pass on both, which shows the existing guarantees are preserved.

### Evidence

The artifacts are in `reports/benchmarks/replays/522-incremental-attestation/`. Scaling ran on a 4-core container with no other benchmark running: two interleaved runs per revision, before = `main` `0007f5f`, after = `bc902c4`. It was produced by `reference/run_write_recall_scaling.py` through the installed facade.

| facts in store | metric | 0007f5f | bc902c4 |
| --- | --- | --- | --- |
| ~100 | write median | 15.5 ms | 9.1–9.4 ms |
| ~100 | recall median | 22.6–23.5 ms | 15.0–15.2 ms |
| ~1,000 | write median | 120–130 ms | **64 ms** |
| ~1,000 | recall median | 174–179 ms | **107–108 ms** |
| ~1,000 | integrity work per commit (digest + journal validation + state reads) | 62–67 ms | **0.7 ms** |
| ~1,000 | governance-state rewrite per commit (`write_runtime_state`) | 20–23 ms | 20–21 ms |

AgentMemBench scale and retrieval were replayed at `58cbfe9`. That is the same attestation code, before the merge of #542's lock. The input is `33632710…`, compared against frozen `03197cd`.

| phase | metric | 03197cd | 58cbfe9 |
| --- | --- | --- | --- |
| scale, 1,000 records | write p50 / p95 | 50.6 / 104.1 ms | **30.8 / 62.0 ms** |
| scale, 1,000 records | read p50 / p95 | 496.8 / 625.3 ms | 450.7 / 571.7 ms |
| scale, 100 and 1,000 records | recall@3, write success | 1.0, 1.0 | 1.0, 1.0 |
| retrieval (1,000 records) | write p50 | 53.8 ms | **32.8 ms** |
| retrieval (1,000 records) | exact_source_recall@5 | 0.889 | 0.902 [0.883, 0.920] |

The exact_source_recall change comes from #540's ranking policy, which `58cbfe9` contains. It does not come from this slice.

Full LongMemEval_S was replayed at `58cbfe9`:

- **Retrieval is bit-for-bit identical to `9c2ba70`.** Every paired Δ is exactly 0 on every metric of both planes, including latest-first, with zero failures. The attestation change alters no ranking.
- Agent Memory ingest, turn plane: 2,163 s (`f73b872`) and 2,281 s (`9c2ba70`, shared host) → **1,232 s**.
- Session plane: 149 → 117 s.
- Run wall time: 2,406 → 1,435 s. Peak RSS is unchanged at 2.4 GB.

### Remaining O(state) terms (measured, not addressed here)

- The governance-state blob is re-serialized and rewritten every generation. That is ~20 ms per commit at ~1,000 facts, and it is now the largest persistence term.
- Lexical search tokenizes every fact in the tenant (~16 ms per recall at ~1,000 facts in one scope).
- AgentMemBench scale reads (~450 ms p50 at 1,000 records) are dominated by admission and audit work per candidate. #522 part B, the scope-aware prefilter, is measured but awaits a contract decision on #522: prefiltering changes which refusals are visible to callers and to the audit.

## Slice 4: query-conditioned applicability (#538, ADR-039 proposed)

Recorded separately in `docs/57-query-conditioned-applicability.md`. In summary:

- Under admitted-set BM25, the query-conditioned policy is metric-identical to the 2.1 universal tie-break on both gauntlets, with zero failures.
- Under tie-heavy overlap relevance, it keeps currentness gains where the query expresses current intent. It withholds recency elsewhere, with net retrieval against universal statistically indistinguishable from zero.
- Two reproduction variants match frozen `f73b872` and `9c2ba70` exactly.


## Slice 5: privacy-preserving domain-eligibility prefilter (#548, #522 Part B)

Before this slice, every lexical match in the tenant became a recall candidate, and governed admission then refused the foreign-scope ones one by one. Admission stayed correct, but two costs followed:

- candidate and admission work scaled with the whole tenant, not with the caller's scope;
- the caller-visible result and audit event carried foreign-scope identifiers as refusals.

**Change.**

```text
raw discovery matches -> necessary domain-eligibility prefilter -> candidate set
    -> full canonical governed admission -> admitted set
```

- The prefilter is the same predicate that full admission re-applies: tenant, scope metadata, isolation domains and required compartments, shared-space membership, project, task. It is a minimization boundary, never permission: it cannot admit and it changes no admission outcome.
- Public contract 1.3.0 (additive) documents that `candidates` are domain-eligible, and exposes only `candidate_policy` (policy id and version, `prefilter_authority: none`).
- No foreign identifier and no foreign-match count is observable. See `docs/44-public-api-contract.md`.

Tests: `reference/tests/test_domain_eligibility_prefilter.py`. The privacy tests fail with the prefilter bypassed, and admitted sets are identical with and without it.

### Evidence

The artifacts are in `reports/benchmarks/replays/548-domain-eligibility-prefilter/`. Before = `main` `1415da3`, after = `68d281c`. Everything ran on a 4-core container with no other benchmark running.

The before scaling runs used the after revision's harness file (which adds `--scopes` and the candidate counters) over the unchanged `1415da3` runtime, so their manifests report a dirty worktree. One after run overlapped a test run and was repeated on a quiet host.

**AgentMemBench / MemDialogue v2, isolation and retrieval phases.** The input is `33632710…`, the same as Slice 3.

| phase | metric | 1415da3 | 68d281c |
| --- | --- | --- | --- |
| isolation (100 users) | cross_user_leak_rate | 0.0 | **0.0** |
| isolation | candidates / admitted | 50,000 / 500 | **500 / 500** |
| isolation | refusals (`required_isolation_domain_missing`) | 49,500 | 0 (never candidates) |
| retrieval (1,000 records) | exact_source_recall@5 | 0.899 | **0.899** |
| retrieval | by event type (PERSONAL_FACT / TASK_REQUEST) | 0.962 / 0.836 | 0.962 / 0.836 |
| retrieval | candidates / admitted | 993,210 / 9,937 | **9,937 / 9,937** |
| retrieval | read p50 / p95 | 995.6 / 1,701.2 ms | **99.8 / 139.9 ms** |
| retrieval | write p50 | 29.8 ms | 31.1 ms |
| retrieval | phase wall time | 1,041.7 s | 133.0 s |

The admitted counts and retrieval scores are identical, so governance is not weakened. The only thing removed is the refusal of candidates that could never have been admitted.

**Write/recall scaling at ~1,000 facts** (`reference/run_write_recall_scaling.py`, two runs each).

| scopes | metric | 1415da3 | 68d281c |
| --- | --- | --- | --- |
| 10 | candidates / admitted per recall | 104.45 / 13.4 | **13.4 / 13.4** |
| 10 | admission work per recall (`admit_preselected_candidates`) | 18.7–18.9 ms | **2.7 ms** |
| 10 | lexical search per recall | 14.6–14.8 ms | 9.9–10.0 ms |
| 10 | recall median | 90.9–95.5 ms | **66.6–73.6 ms** |
| 1 | candidates / admitted per recall | 104.45 / 104.45 | 104.45 / 104.45 |
| 1 | lexical search per recall | 13.1–13.7 ms | 15.8–16.1 ms |
| 1 | recall median | 91.9–99.3 ms | 100.0–106.3 ms |

**Tradeoff recorded.** With a single scope there is nothing to exclude, and the per-fact eligibility check adds ~2–3 ms to lexical search. Recall persistence (`_persist_unlocked`, ~38–45 ms) is now the largest recall term, dominated by the governance-state rewrite. The lexical scan still visits every fact in the tenant; it only skips tokenizing ineligible ones.
