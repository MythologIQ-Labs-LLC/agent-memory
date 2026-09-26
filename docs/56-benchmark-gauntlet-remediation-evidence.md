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
