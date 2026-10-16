# #819 C7 stopped at its preregistered gate: bounded rank fusion fails invariant I4

**Decision.** C7 is **not frozen and not handed off**. It met every rank-quality criterion (R1–R5), including both out-of-sample regression sets, and every selection and route-off invariant. It failed two invariants: **I4** (below) and **I5**, cost (see Measurements).

It failed invariant **I4**: the newer of two conflicting statements must rank first on at least as many conflict queries as under C4. C7 achieves 1 of 6; C4 achieves 2 of 6.

The preregistration says an invariant failure is fixed or the candidate is rejected, and that a fix may not change the preregistered constants. No fix inside C7's single-mechanism scope exists (see below), so C7 is rejected. **No threshold, constant or invariant was changed after seeing results.**

## Identity

| Item | Value |
|---|---|
| Branch | `claude/eager-dirac-bftkfg-819-c7` (pushed; no PR; no Actions) |
| Base | C6 frozen `171e67db` (untouched) |
| Preregistration | `415eb5c5`: diagnosis, preregistration, development set and fail-first tests, before any runtime change |
| Implementation | `d05bf2b1`: ranking policy 3.5.0, RRF k = 60 over admitted-set BM25, shared-evidence and dense ranks |
| Stop record | this commit |

## Gate results

### Development set (48 queries, 76 needed memories, in-sample): `dev/gate/gate-dev.json`

| Criterion | C7 | Comparator | Bound | Result |
|---|---:|---:|---|---|
| R1. All needed evidence in the top 5 (of 42) | **23** | C4+sem 19 | ≥ 22 | met |
| R2. Needed memories in the top 5 (of 76) | **41** | 33 | ≥ 39 | met |
| R3. All needed evidence in the top 10 | 27 | 24 | ≥ 24 | met |
| R3. All needed evidence in the top 3 | 18 | 14 | ≥ 14 | met |
| R4. Queries losing top-5 coverage | 1 (work-3) | — | ≤ 2 | met |
| S1. Returned sets equal C6+sem (`relevance_sufficient`) | equal on all 48 | — | equal | met |
| S2. Strict / extras / no-answer returning | 11 / 45 / 4 | C6+sem 11 / 45 / 4 | no worse | met |
| I1. Route off equals C4 | identical | — | identical | met |
| **I4. Newer statement first (conflict queries)** | **1 of 6** | **C4 2 of 6** | **≥ C4** | **failed** |

The runtime reproduces the offline feasibility estimate exactly: 18 / 23 / 27 coverage, 41 in the top 5.

### Out of sample: `oos/gate-oos.json`

Neither set was used in C7's design.

| Set | Selection | C4+sem | C7 | Result |
|---|---|---:|---:|---|
| C6 development union (78 queries) | `ranked_prefix`, recall@10 | 0.705 | 0.731 | R5 met |
| C6 development union | `ranked_prefix`, needed in top 5 | 49 | 51 | R5 met |
| C6 reviewer set (55 queries, independently authored) | `ranked_prefix`, recall@10 | 0.707 | 0.741 | R5 met |
| C6 reviewer set | `ranked_prefix`, needed in top 5 | 31 | **39** | R5 met |

Both sets also met the selection and route-off invariants:
- **S1, S2:** under `relevance_sufficient` (against C6+sem), returned sets, strict, extras and no-answer counts are identical on both sets. Only the order changed, on 4 and 9 queries.
- **I1:** with the route off, lists are identical to C6's.

## Why I4 failed, and why no fix fits C7

Conflict query `travel-6`: "Which airline do we usually fly with?"

| Statement | BM25 | Cosine | C4 rank | C7 rank |
|---|---:|---:|---:|---:|
| newer: "We now mostly fly easyJet because it serves our local airport." | 2.48 | 0.557 | 1 | 2 |
| older: "Our usual airline for holidays is TAP." | 2.10 | 0.582 | 2 | 1 |

- **Neither runtime orders by time here.** The question's temporal intent is unspecified, and the temporal stage comes after relevance.
- **C4's correct result was incidental.** It came from wording (BM25), and fusion's added dense signal reverses it.
- **On the other conflict queries, nothing turned.** The newer statement moved up in three (rank 3 → 2), and no other first place changed.

Restoring newer-first here needs a temporal-ordering mechanism for conflicting evidence under unspecified intent. That is:
1. a second mechanism, which the C7 brief excludes ("do not combine major ranking, multi-hop, temporal and abstention rewrites");
2. constrained by ADR-039, which forbids silently treating unspecified intent as current.

As preregistered, I4 protects an incidental outcome. That is a lesson for the next preregistration. It is not a reason to relax this one.

## Other findings

- **Preregistered fail-first test 1 was false for the preregistered mechanism.** RRF over lists where every admitted memory has a dense rank keeps a memory found only by the semantic route (one list, 1/61 at best) below lexical candidates (two lists).
  - The gains come from lexically weak evidence that dense similarity supports.
  - Semantic-only evidence (14 of the 27 low-ranked needed memories in the diagnosis) is not lifted.
  - The test is kept as an expected failure.
- **Multi-evidence questions:** all needed evidence in the top 5 rises from 1 to 3 of 17, and needed memories in the top 5 from 9 to 15 of 45. Discovery still loses 16 of 45 multi-evidence memories.

## Measurements

### I5: latency and memory (`latency.txt`)

The probe is a 200- or 1,000-memory store with 40 recalls, `OMP_NUM_THREADS=2`, two runs each, C6 against C7 (route on).

| Store | C6 p50 / p95, ms | C7 p50 / p95, ms | Peak RSS, MB (C6 / C7) | Bound | Result |
|---|---|---|---|---|---|
| 200 memories | 64.3 / 75.1; 68.7 / 94.8 | 89.7 / 108.1; 99.1 / 133.2 | 215, 214 / 215, 213 | p50 ≤ C6 + 10 ms | **failed** (+25 to +30 ms) |
| 1,000 memories | 302.7 / 372.9; 297.5 / 362.9 | 318.2 / 372.4; 317.9 / 371.5 | 213, 217 / 213, 213 | p50 ≤ 1.15 × C6 | met (1.06×) |

**Cause.** In this probe nearly every memory shares a word with the query, so about 200 are admitted. Fusion then:
- computes a pure-Python cosine for each admitted memory (cached vectors, 384 dimensions);
- ranks the admitted set twice (the 3.4.0 base order for selection, then the fused order), recomputing admitted-set BM25.

**Possible fixes,** none of which change a constant:
- reuse the base pass's BM25;
- vectorise the cosine;
- skip the base pass under `ranked_prefix`.

None was attempted, because I4 already rejects C7. A successor should budget fusion's cost explicitly.

### Determinism and full suite

- **Determinism (I3): met.** Two full development runs, the second with `PYTHONHASHSEED=7`, give identical ranked admitted orders on all 48 queries (`determinism.txt`). The tie test passes under three hash seeds.
- **Governance (I2): met.** The invariant tests pass: forgotten, other-scope and superseded memories never appear among admitted or returned memories, and no refused text leaks. Safety violations: 0 on all sets.
- **Full suite at `d05bf2b1`:** 2659 passed, 31 skipped, 1 expected failure (the falsified preregistered test 1), and 1 failed by design (`test_evaluation_only_change_keeps_runtime_baseline_equivalence`: the protected surface changed and no successor is declared) (`full-suite-d05bf2b1.log`).

## What the next hypothesis should take from C7

1. **Fusion generalises out of sample** on rank depth (reviewer set: +8 needed memories in the top 5) and leaves selection untouched.
2. **I4 must protect temporal decisions, not incidental ones.** Measure newer-first separately and gate only orderings that a temporal stage decides.

   Changing the invariant is a decision for the program owner or evaluator. It is not something engineering should do after seeing C7's results.
3. **Newer-first among conflicting evidence under unspecified intent is a real, separate deficit:** 2 of 6 here, and 0 of 16 in the evaluator's cohort. Addressing it needs an ADR-039 decision.
4. **RRF's single-list penalty** means semantic-only evidence needs either discovery-side help or a fusion form that does not penalise absence from the lexical list. Either should be preregistered on fresh data.
