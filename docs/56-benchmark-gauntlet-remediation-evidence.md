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

## Post-prefilter scale probe and the LongMemEval_M decision (#537)

This probe was run after Slices 3 and 5 landed, to decide whether LongMemEval_M is justified and which remaining term dominates. It used `reference/run_write_recall_scaling.py` at `14b422c`, the prefilter head, whose runtime is identical to `main` `27c8e77`. The host was a 4-core container with no other benchmark running. Artifacts are in `reports/benchmarks/replays/537-post-prefilter-scale-14b422c/`.

| shape | facts | write p50 | write `_persist_unlocked` | recall p50 | recall search | recall admission | recall `_persist_unlocked` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 scopes | ~100 | 9.7 ms | 4.7 ms | 11.5 ms | 1.4 ms | 1.0 ms | 5.4 ms |
| 10 scopes | ~1,000 | 60.7 ms | 41.4 ms | 74.7 ms | 10.3 ms | 3.0 ms | 44.9 ms |
| 10 scopes | ~5,000 | 329.8 ms | 251.5 ms | 417.4 ms | 67.9 ms | 10.8 ms | 246.7 ms |
| 10 scopes | ~10,000 | 730.4 ms | 583.6 ms | 914.5 ms | 136.7 ms | 18.7 ms | 587.4 ms |
| 1 scope | ~100 | 10.6 ms | 5.4 ms | 14.2 ms | 1.9 ms | 2.5 ms | 5.3 ms |
| 1 scope | ~1,000 | 61.5 ms | 42.9 ms | 105.2 ms | 17.2 ms | 19.7 ms | 43.6 ms |
| 1 scope | ~5,000 | 314.5 ms | 228.5 ms | 524.1 ms | 84.2 ms | 90.8 ms | 222.7 ms |

The single-scope 10,000-fact point was not run. Its fill costs about an hour on this host, and the 10-scope row already establishes the trend.

Findings:

- **Persistence dominates and is linear in retained state.**
  - At 10,000 facts, `_persist_unlocked` is 80% of a write and 64% of a recall.
  - Nearly all of it is the governance snapshot: a canonical-JSON digest of the whole snapshot plus a rewrite of the whole blob.
  - Substrate attestation stays at 0.4–0.8 ms at every size (Slice 3).
  - Tracked as #562.
- **Lexical candidate generation is the next term.**
  - Search visits every tenant fact.
  - Admission cost follows the number of eligible matches.
  - Tracked as #563.
- **The prefilter holds at scale.** With 10 scopes, admission stays at 18.7 ms at 10,000 facts.
- **LongMemEval_M stays held.** Its turn plane implies thousands of commits per haystack. At ~0.3–0.7 s per commit at those sizes, a run would mostly re-measure the quadratic ingest that #562 already isolates. It becomes a promotion gauntlet after #562 is bounded, as #537 Phase 4 requires.

## Slice 6: incremental governance-state attestation (#562)

**Root cause.** After Slices 3 and 5, every generation still committed governance state the `full-json-v1` way. The whole snapshot was canonical-JSON serialized, hashed, and rewritten inside the runtime-state row. That happened on every write and on every recall, because recall commits audit and identifier progress.

The snapshot is dominated by two parts, measured on a 1,000-fact facade store:

| part | share of bytes | how it changes per operation |
| --- | ---: | --- |
| the append-only audit log (`events`) | 84% | +4 records on a write, +1 on a recall |
| four keyed maps (`fact_scope`, `fact_memory`, `current_fact_by_memory`, `state_version`) | 16% | ≤1 key each |
| everything else (disputes, tombstones, rejected values, extension state, scalars) | <0.1% | rarely |

The cost was O(state), but each generation's change is O(1).

**Change.** The new scheme is `gsect-v1`; its contract is in `docs/46-state-checkpoint-contract.md`.
- Map sections are written per changed key and committed by 256-bucket roots.
- The audit log is appended and committed by a hash chain.
- The small residual is content-hashed.
- The journal binds the self-describing `gsect-v1:` root.
- Recovery recomputes every entry hash, bucket, chain link, and the root from the stored rows.
- Envelope `1.0.0` stores migrate atomically at their next generation, historical `sha256:` journal records stay as they are, and mixed envelopes are refused.

Tests are in `reference/tests/test_governance_attestation.py` (24):
- equivalence with a full export;
- locality;
- tampering with an entry, a self-consistent forged entry, a log record, a forged log record with a valid chain, the residual, the root, and the journal binding;
- stale governance rows under a newer journal tail;
- the derived index;
- mixed envelopes, atomicity under an injected failure, and legacy migration.

Every publication in the full reference suite (1,638 tests) is also re-read from the rows and compared with a full export.

### Evidence

The artifacts are in `reports/benchmarks/replays/562-governance-attestation-2cedb6c/`. Before = `main` `0eba679`, after = `2cedb6c`, on a 4-core container with no other benchmark running. Scaling runs used the after revision's harness file over both runtimes, so manifests report a dirty worktree for harness-only changes. The ~10,000-fact "before" point is the post-prefilter probe at `14b422c`, whose persistence code is identical to `0eba679`.

**Write/recall scaling, 10 scopes.**

| facts | write p50 before → after | `_persist_unlocked` (write) before → after | governance publication (after) | substrate digest (after) | recall p50 before → after | store bytes before → after |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ~100 | 8.7 → 5.2 ms | 4.25 → 1.18 ms | 0.67 ms | 0.27 ms | 12.2 → 5.2 ms | 0.74 → 0.89 MB |
| ~1,000 | 56.0 → 4.6 ms | 40.2 → 1.44 ms | 0.86 ms | 0.33 ms | 75.5 → 15.6 ms | 4.50 → 4.42 MB |
| ~5,000 | 320.9 → 4.4 ms | 242.8 → 1.60 ms | 1.02 ms | 0.35 ms | 397.7 → 69.5 ms | 21.3 → 20.0 MB |
| ~10,000 | 730.4 → 5.6 ms | 583.6 → 2.22 ms | 1.42 ms | 0.45 ms | 914.5 → 177.8 ms | n/a → 39.6 MB |

**Acceptance bound.** Per-commit persistence at ~10,000 facts is **1.5×** the ~1,000-fact value (2.22 / 1.44 ms); before, it was 14×. Single-scope runs give 1.48 → 2.12 ms (1.4×). The residual term grows only with disputes, rejected values, and extension state, never with facts or audit length.

**AgentMemBench / MemDialogue v2, all deterministic phases**, on the same frozen input `33632710…`:
- **Zero non-timing differences** between `0eba679` and `2cedb6c` across retrieval, conflict/currentness, isolation, deletion, concurrency, and scale, including every governance refusal and outcome tally.
- Wall 226.2 → 46.3 s.
- Retrieval write p50 28.8 → 5.1 ms and read p50 97.4 → 14.3 ms.
- Scale at 1,000 records: write p50 30.6 → 5.1 ms, read p50 72.1 → 11.5 ms.
- Concurrency throughput 99–112 → 171–185 ops/s at 1–16 workers.

**LongMemEval_S, frozen `d6f21ea9…c442`.**
- Per-question rankings are **bit-for-bit identical** to the frozen policy-3.0.0 replay `148823f`: 500/500 session and 500/500 turn rows.
- Between `0eba679` and `2cedb6c`, only the per-row timing fields differ.
- Failures are zero.

| plane | ingest `0eba679` → `2cedb6c` | recall total |
| --- | ---: | ---: |
| session | 126.7 → 116.1 s | 11.0 → 10.2 s |
| turn | 1,262.9 → 606.5 s | 36.6 → 31.4 s |
| run wall | 1,475.6 → 811.7 s | |

At S scale (≤305 turns per store), the remaining ingest is the fixed per-write cost, about 5 ms: PAMA decision, receipts, canonical write, and SQLite fsync. It no longer depends on how much is retained.

### LongMemEval_M readiness

M's per-question size comes from an exact sample of 11 questions at upstream `98d7416c` (a range request on the 2.74 GB file): about 476 sessions and 2,426 user turns per question. That is ~9.9× S (47.7 sessions and 245 user turns).

| estimate (agent_memory backend, both planes) | before #562 | after #562 |
| --- | ---: | ---: |
| turn ingest, 500 × ~2,426 writes | ~25 h (per-write cost rising to ~150 ms by the end of each haystack) | **~1.7 h** at the measured flat ~4.95 ms per write |
| session ingest, 500 × ~476 writes | ~1.2 h | **~0.3 h** at ~4.9 ms per write |
| recall, 1,000 recalls on ~2.4k-fact single-scope stores | minutes | minutes (#563 governs this term) |

- **Runtime gate: passes.** #562's bound holds, no O(state) write path remains, and the expected cost is operationally reasonable.
- **Run: still held, on a new harness-side blocker.** `run_longmemeval.py` loads the whole input with `read_text` + `json.loads`. On S that peaks at 2.39 GB for a 277 MB file (8.6×), which projects to ~23.5 GB for M on this 15 GB host.
- A streaming, per-question loader is a benchmark-harness change outside #562. It is the next step before M.

### Remaining dominant costs

- **Recall: lexical candidate generation and candidate admission (#563).** At ~10,000 facts, search takes 143 ms of a 178 ms recall with 10 scopes. With a single scope it is 162 ms search plus 192 ms admission, for ~1,030 candidates.
- **Write: the fixed per-operation cost** (~4–5 ms), now independent of retained state.

## Slice 7: streaming LongMemEval input (#568)

**Finding.** After Slice 6 the LongMemEval_M runtime gate passed, but the harness did not fit. `run_longmemeval.py` read the whole input with `read_text` + `json.loads`. On S that peaks at 2.40 GB for a 277 MB file, which projects to ~23.5 GB for M's 2.74 GB on a 15 GB host. This slice changes the harness only; the runtime is untouched.

**Change.** `InputStream` in `reference/run_longmemeval.py`:
- Raw bytes are read in 1 MiB chunks. Every byte read goes into a SHA-256, so input identity is still the digest of the source bytes, never of parsed or re-serialized JSON.
- The bytes are decoded as strict incremental UTF-8.
- Each top-level array element is decoded by the standard library's `json.JSONDecoder.raw_decode`, the decoder `json.loads` uses. Element values are therefore identical.
- A byte-order mark, a non-array or empty top level, a malformed or truncated element, a missing separator, a trailing comma, content after the closing `]`, invalid UTF-8, and an element over 2^28 characters all fail closed.

`run` streams in two phases:
1. **Scan pass.** Validates every question with the unchanged rules: required fields, unique question ids, equal haystack lengths, repeated session ids carrying identical content, and answer ids present. It keeps only a per-question summary, and selection (prefix, or the seeded hash subset) runs on those summaries.
2. **Evaluation passes, one per (plane, backend).** Each streams the selected questions again, one resident at a time, in source order. It must reproduce the scan digest and the selected order, or the run fails.

For S, 1 + 2 × 3 passes of ~3 s each add about 20 s. For M they add about 7 min over a multi-hour run.

Report schema 2.1.0 adds, with no change to result semantics:
- `input.sha256_scope`, `input.source_question_count`;
- `execution.input_loading`: method, chunk size, resident question count, and the bytes and digest of each pass;
- `execution.resource_consumption`: `peak_rss_mb_process` and `peak_rss_mb_after_input_scan`.

**Tests.** `reference/tests/test_longmemeval_streaming.py` has 16 tests, using the pre-#568 loader kept verbatim as an oracle:
- equivalence at chunk sizes from 1 byte to 1 MiB, plus compact, indented and padded formatting;
- first and last element boundaries, and a single-question array;
- the raw-byte digest, a digest that is unavailable before the input is fully consumed, and bytes that change between passes;
- seeded subsets and prefixes matching whole-file selection;
- duplicate session ids across chunk boundaries and across questions, including the different-content refusal;
- non-ASCII text split mid-character, and invalid UTF-8;
- 15 malformed shapes, plus a malformed question between valid ones, which is never skipped;
- an oversized element, an empty array (still rejected), and whole-report equivalence with the whole-file evaluation path.

### Evidence

The artifacts are in `reports/benchmarks/replays/568-streaming-loader-fa8828c/`, from a 4-core, 15 GB container with no other benchmark running.

**LongMemEval_S equivalence**, full 500 questions, all three backends, runner `fa8828c` (clean tree):
- **IDENTICAL** on every non-timing field (`compare_semantics.py`):
  - input sha256 `d6f21ea9…c442`, size, question count, abstention / no-target / duplicate-session counts, and the selection and question-id digest;
  - question order;
  - every per-question row: gold, ranked top-50, metrics, candidate / admitted / refusal counts, out-of-corpus, unmapped, and failures;
  - every aggregate, numerator, denominator, currentness slice, and governance tally.
- The comparison covers 1,000 `agent_memory` rows against `2cedb6c` and 2,000 baseline rows against the frozen `f73b872`.
- Only wall-clock fields differ.

| | whole-file loader | streaming loader |
| --- | ---: | ---: |
| S loader-only peak RSS | 2,404.9 MB (25.1 s) | 53.2 MB (3.1 s) |
| S whole-run peak RSS, 3 backends × 2 planes | ~2.4 GB+ (not recorded before) | **80.8 MB** |
| M loader-only peak RSS | ~23.5 GB projected, not attempted | **166.1 MB** (60.3 s, 500 questions validated) |

**M input provenance.** `longmemeval_m_cleaned.json` from `xiaowu0162/longmemeval-cleaned` @ `98d7416c24c778c2fee6e6f3006e7a073259d48f`:
- 2,737,100,077 bytes;
- sha256 `9d79e5524794a2e6900a3aa9cb7d9152c5a3e8319c9a87c25494ba1eacee495f`, which equals the upstream LFS object id (`X-Linked-ETag`) at that revision.

### LongMemEval_M readiness decision: run

| gate | status |
| --- | --- |
| streaming loader bounded in memory | pass: 166 MB for the M scan; one question resident per pass |
| S semantic results identical | pass: 3,000/3,000 rows, all aggregates |
| input identity preserved | pass: raw-byte digest equal to frozen S, and M equal to the upstream LFS id |
| #562 bounded | pass: no runtime change since `2cedb6c` (only evaluation / Gauntlet modules changed) |
| no newly exposed O(state) ingest term | pass on S: turn ingest 619.6 s against 606.5 s at `2cedb6c`, a flat ~5 ms per write; re-checked on M during the run |
| host memory fits with margin | pass: projected well under 1 GB against 15 GB |

#563 (recall scaling) is minutes of M's cost and does not hold the run. M runs from the merge commit of this slice, with the same backends and planes as S (`no_memory`, `lexical_overlap`, `agent_memory`; session and turn) and the frozen default configuration (`temporal_metadata=none`, `ranking_variant=default`).

### LongMemEval_M run (frozen)

The artifacts are `reports/benchmarks/longmemeval/longmemeval-m-full-409098f.{json,rows.json.gz,analysis.json}`, with normalized manifests in `reports/benchmarks/normalized/*-409098ffeec5.json`.

**Run conditions.**
- Revision `409098f` (the merge of #573), run from a clean detached worktree.
- Input: `longmemeval_m_cleaned.json` @ `98d7416c`, sha256 `9d79e552…495f` (the upstream LFS id), all 500 questions.
- Backends and planes were the same as S, with the frozen default configuration.
- Host: 4 cores and 15 GB, with nothing else heavy running. The only exception was ~30 s of niced unit tests on a spare core.

| | value |
| --- | ---: |
| wall | 8,658 s (2.40 h) |
| peak RSS: after scan / whole run | 167.6 MB / 212.1 MB |
| input passes (all equal to the scan digest) | 7 × 2,737,100,077 bytes |
| runtime / ingestion / out-of-corpus / unmapped failures | 0 / 0 / 0 / 0 |
| questions scored (after upstream `_abs` and no-target exclusions) | 419 of 500 |
| questions with repeated haystack session ids (handled as upstream does) | 449 |

| plane | backend | recall_all@5 | ndcg_any@5 | recall_all@10 | ndcg_any@10 | recall_all@50 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| session | lexical_overlap | 0.4535 | 0.5282 | 0.5513 | 0.5560 | |
| session | agent_memory | **0.7088** | **0.7492** | **0.7780** | **0.7702** | |
| turn | lexical_overlap | 0.2983 | 0.3529 | 0.3986 | 0.3858 | 0.5537 |
| turn | agent_memory | **0.5322** | **0.5693** | **0.6110** | **0.5923** | **0.7422** |

`no_memory` is 0 everywhere.

**Comparison with S under the same runtime policy** (`fa8828c`, as above):
- Both backends lose recall on M, which has ~10× the haystack.
- Agent Memory's margin over the lexical baseline widens:
  - session recall_all@5: +0.093 on S, +0.255 on M;
  - turn recall_all@5: +0.115 on S, +0.234 on M.
- Knowledge-update recall_all@5, session plane:
  - agent_memory: 0.972 → 0.917;
  - lexical: 0.917 → 0.694.

**Currentness diagnostic** (latest gold ranked first, 70 applicable questions):
- Session plane: agent_memory 0.471 vs lexical 0.443.
- Turn plane: agent_memory 0.514 vs lexical 0.571.
- The turn-plane shortfall has the same sign and size as on S (0.557 vs 0.614), so it is the known currentness-ordering class (#531, #538), not a new M finding.

**Scale behavior.**
- Agent Memory wrote ~475 (session) and ~2,428 (turn) facts per question. The per-write cost was flat:
  - turn plane: p50 5.30 ms, p95 5.55 ms, max 5.87 ms;
  - the mean is 5.32 ms for both the smaller and the larger half of the stores.
- No O(state) ingest term reappeared, and #562's bound held across 1.45 M governed writes.
- Recall:
  - turn plane: p50 0.70 s, max 1.04 s, at ~2,041 candidates per recall;
  - session plane: p50 0.19 s.
- Recall is the #563/#572 cost term: minutes in total (341 s turn, 100 s session), not hours.
- Every candidate was admitted, because these are single-scope stores with no disputes or tombstones. This is expected, not a governance bypass: admission ran on every candidate.

**Classification.**
- Architecture validation at scale: bounded memory, flat write cost, zero failures, exact provenance.
- Benchmark difficulty: M's lower absolute recall affects both backends.
- The currentness ordering is the known class (#531, #538); no new defect was found.
- The run tuned nothing. Policy 3.0.0 and the ADR-039 status are unchanged, and M is not new validity/as-of evidence.
