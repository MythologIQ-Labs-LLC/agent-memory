# #819 C7 preregistration: bounded reciprocal-rank fusion of admitted evidence

This file is committed with `DIAGNOSIS-C7.md`, the development set and the fail-first tests, before any C7 runtime change.

## Base, comparators and scope

| Item | Value |
|---|---|
| Development base | C6 frozen `171e67db`, branch `claude/eager-dirac-bftkfg-819-c7`. C6's history, source and evidence are untouched |
| Comparators (immutable) | A `7c06468a`; C4 `bc2be631` (route off and on); C6 `171e67db` (route on) |
| Not touched | #805/#815/#816 security lineage, #821, C1–C6 and their evidence, evaluator branches and cohorts, the Runtime Baseline register, `ranked_prefix` and semantic-route defaults |
| Architecture issue | #673 (post-admission route fusion) |

## Hypothesis (one mechanism, at the ranking stage)

**H.** With the optional local model present, ordering admitted memories by a bounded reciprocal-rank fusion (RRF) of their lexical, shared-evidence and dense ranks puts more of the required evidence of multi-evidence and low-overlap questions into the top of the ranked list. That is more than the current lexicographic order achieves, in which the semantic route is a subordinate tie-break.

Nothing outside the ranking stage changes:
- what is discovered, admitted or refused;
- which facts are sufficient under relevance-sufficient selection.

## Mechanism

**Ranking policy `3.5.0`, fusion `rrf-admitted-1.0.0`.** It applies only when the semantic provider is enabled and available for the store.

1. **After governed admission,** take the admitted set in the order the 3.4.0 policy gives it (the *base order*).
2. **Three signal lists** are formed over admitted memories only:
   - **lexical:** the existing admitted-set BM25 score (`lexical_relevance_score`) where > 0;
   - **shared evidence:** the existing `shared_evidence_neighbor` route score where present;
   - **dense:** cosine between the query and the memory's derived vector, rounded to 1e-6, for every admitted memory. The vectors come from the existing derived-vector store; the query vector is computed once per recall.
3. **Rank** within each list by competition ranking: equal values share a rank, so a tie never becomes an order.
4. **Fuse:** `fused = Σ 1 / (60 + rank)` over the lists the memory appears in, rounded to 1e-12.
   - k = 60 is the literature default, fixed now and never tuned.
   - The lists carry equal weight.
5. **Stage order in `3.5.0`:**
   1. temporal applicability tier (unchanged);
   2. exact identity (unchanged);
   3. **fused score, descending** (replaces route corroboration count, per-route scores and BM25);
   4. temporal order within the query regime (unchanged);
   5. subordinate semantic score (unchanged);
   6. neutral digest.

   The explicit-current constraint and cross-fact operations of 3.2.0/3.4.0 apply unchanged on top.
6. **Resource bound.** If more than `FUSION_MAX_ADMITTED` = 512 memories are admitted, fusion is skipped: the 3.4.0 order is used and recorded (`fusion.status = "skipped_over_limit"`).
7. **Degradation.**
   - No provider, or the route disabled (route off, `auto` without a model): the policy is exactly 3.4.0 with the same identity. Route off equals C6, and therefore C4.
   - Dense scoring raises `RepresentationUnavailable`: the base order is used, and `fusion.status = "unavailable"` is recorded.
   - The pre-existing behaviour where the discovery route raises at query time in `auto` (C6 review, finding 9) is out of scope and unchanged.
8. **Selection is unchanged.** Under `relevance_sufficient`, sufficiency (including ranking consistency, `ranked_above_sufficient`) is decided on the **base order**. The fused order only orders the returned facts and decides the budget cut.

   So C7 cannot make a fact sufficient. The returned set equals C6's whenever the budget does not bind.
9. **Evidence.**
   - Each admitted memory's `ranking_evidence.fusion` records:
     - `lexical_rank`, `shared_evidence_rank` and `dense_rank`;
     - `dense_similarity`;
     - `fused_score`;
     - `k`;
     - `authority_effect: none`.
   - The policy identity records fusion and its version.

**Similarity never authorises.** It orders admitted memories only. It never admits, refuses, supersedes or makes anything sufficient.

## Candidate configurations

| Label | Open | Recall |
|---|---|---|
| C7-sem-rp | `semantic_retrieval="required"`, pinned `multi-qa-MiniLM-L6-cos-v1@b207367` | `return_selection="ranked_prefix"`, budget 10 |
| C7-sem-rs | same | default `relevance_sufficient`, budget 10 |
| C7-off | default (route off) | either |

## Data

| Set | Use |
|---|---|
| `dev/c7-scenarios.json` (48 queries, 76 needed) | Diagnosis and gate. In-sample: the feasibility check used it |
| C6 development union (`819-c6/dev/*-scenarios.json`, 78 queries) | Regression only. Not used in C7's design or feasibility |
| C6 reviewer set (`819-c6/review/gen.json`, 55 queries; independently authored, unseen by C6 calibration) | Regression only. Not used in C7's design or feasibility |

**Negative controls** across the sets:
- no-answer queries;
- topical distractors;
- question-shaped notes;
- injected text;
- forgotten, corrected, disputed, other-scope and out-of-window memories;
- conflicts.

## Engineering gate (all required)

### Rank quality on the development set (C7-sem-rp against C4+sem `ranked_prefix`)

| Criterion | Requirement | C4+sem |
|---|---|---:|
| R1. All needed evidence in the top 5 | ≥ 22 of 42 | 19 |
| R2. Needed memories in the top 5 | ≥ 39 of 76 | 33 |
| R3. All needed evidence in the top 10 | ≥ 24 | 24 |
| R3. All needed evidence in the top 3 | ≥ 14 | 14 |
| R4. Queries that lose top-5 coverage C4+sem had | ≤ 2 | — |

### Out of sample (C6 development union and C6 reviewer set; neither used by C7)

- **R5. No loss of rank depth.** Under `ranked_prefix`, budget 10, route on:
  - needed recall@10 ≥ C4+sem's on each set;
  - needed memories in the top 5 ≥ C4+sem's minus 2 on each set.

### Selection invariance and precision (all three sets, C7-sem-rs against C6+sem)

- **S1.** The returned **set** equals C6+sem's on every query where C6+sem's sufficient set fits the budget.
- **S2.** Strict ≥ C6+sem's; extras ≤ C6+sem's; no-answer queries returning something ≤ C6+sem's.

### Invariants

| Criterion | Requirement |
|---|---|
| I1 | C7-off ranked admitted orders and returned lists are identical to C6 (and C4) on every query of all three sets |
| I2 | Zero safety violations. Forgotten, superseded, corrected, disputed, other-scope and other-tenant memories never appear in admitted or returned lists, in current-state, historical and as-of recall |
| I3 | Deterministic: two full runs give identical ranked orders. Exact fused ties order identically across fresh stores built with the same operations, through competition ranks and the existing neutral digest, never by process hash or wall clock. Fact identifiers are sequential, so write order is part of the history |
| I4 | The newer statement ranks first on at least as many conflict queries as under C4 (2 of 6) |

### Cost

- **I5. Latency and memory.** Recall p50 on the 200-memory probe ≤ C6+sem p50 + 10 ms. At 1,000 memories, p50 ≤ 1.15 × C6+sem. Peak RSS ≤ 1.10 × C6+sem.

### Stop conditions

- **R1–R5 failures: stop.** If any of R1–R5 fails, C7 stops and a negative-result record is published. k, the lists, their weights and the limit are not changed after results.
- **S1–S2 or I1–I5 failures:** fix or reject. A fix may not alter the preregistered constants.

## Fail-first tests (`reference/tests/test_c7_rank_fusion.py`)

The tests use a deterministic table representation that fixes every cosine.

**Must fail on C6 `171e67db` and pass on C7:**
1. A memory found only by the semantic route, with the top cosine, ranks above lexically found filler that shares only weak words with the query.
2. A memory with the second-best BM25 and the best cosine ranks above the memory with the best BM25 and a poor cosine.
3. The ranking policy identity reports `3.5.0` with fusion, and each admitted memory records fusion evidence.
4. If dense scoring is unavailable at ranking time, recall returns the base order and records `fusion.status = "unavailable"`.
5. More admitted memories than the limit: fusion is skipped and recorded.

**Must hold on both:**
6. Forgotten, other-scope and superseded memories never appear among admitted or returned memories, however similar.
7. Under `relevance_sufficient`, a memory below the relevance floor that fusion lifts above the best primary fact is not made sufficient.
8. Exact fused ties order identically across fresh stores built with the same operations, under different `PYTHONHASHSEED` values.
9. With the route off, ranking identity and order equal C6's.

## Independent review and handoff

- **Review before freeze.** A separate adversarial review must cover:
  - false-positive semantic matches;
  - query-shaped memory stuffing;
  - multi-evidence incompleteness;
  - temporal ordering;
  - security boundaries;
  - determinism;
  - provider outage;
  - over-selectivity and over-return.
- **Blocking findings** are fixed without changing the thresholds above.
- **If the gate is met:** freeze the exact SHA, record configuration and model identity, publish the evidence and disposition, and hand off to the independent evaluator.
- **No successor declaration** and no register change.

## Known limits (stated in advance)

- Discovery losses are unaffected: on the dev set, 16 of 45 multi-evidence memories are never discovered with the route on.
- Newer-first ordering under unspecified intent is unaffected.
- The gain needs the optional local model.
- The dev set is in-sample for the gate thresholds, which were set below the offline feasibility estimate. The two regression sets are out of sample for C7.
