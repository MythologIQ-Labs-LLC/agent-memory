# #819 C8: exact-head handoff to the repository delivery lane

**Disposition: CHANGES REQUIRED.** The full evidence is in `REVIEW-C8.md`.

| Item | Value |
| --- | --- |
| Head evaluated | `24d4dd2697047fc622a6087f7005775133b60209` (branch `claude/eager-dirac-bftkfg-819-c8`), `reference/` tree `c8cdb0e8`, clean worktree |
| Runtime lineage | C6 `171e67db` → C7 fusion `d05bf2b1` → C8 cost `69611b3f` → review fix `f2626d0e` (time-ordered intents keep 3.4.0) → freeze `24d4dd26` (docs and evidence only after `f2626d0e`) |
| Comparators | C4 `bc2be631` (route off, and route on under both selections); C6 `171e67db` (route on under both selections) |
| Sealed cohort | e5, committed at `fe056bc4` before C8 was fetched; arms fixed at `8f217f08` before any run. e5 is now spent |

## Do not

- **Do not merge, rebase-for-merge or open an integration PR** for `24d4dd26`.
- **Do not change the Runtime Baseline register.**
- **Do not promote** any C8 number to a feed, dashboard or leaderboard.
- **Do not retune C8's constants in place:** `FUSION_K` 60, rounding, `FUSION_MAX_ADMITTED` 512, and C6's proposal policy. A change makes a new candidate with its own preregistration and a fresh independent cohort.
- **Do not reuse e5, e4, the evaluator probes or the developer fixtures as holdouts.** v4 stays reserved and unopened.

## What is verified and reusable

- **Ranking policy 3.5.0 (RRF of admitted BM25, shared-evidence and dense lists)** moves needed evidence up on sealed data:
  - e5 depth@5 +0.076 [+0.042, +0.117] against C6+sem, and against C4+sem under `ranked_prefix`;
  - all needed evidence in the top 5: +11 / −0;
  - no strict loss against its own base.
- **Time-ordered intents skip fusion,** with no temporal reversal on e5 in either selection.
- **Similarity reuse** is correct, and fusion adds no memory.
- **Route off is identical to C4** on e5 (208/208) and on LongMemEval (500/500, both planes).
- **Determinism:** identical repeat runs (208/208). Exact fused ties occur, but insertion order did not change the fused top 5 in the tie probe.
- **Safety:** 0 leaks of excluded memories, by reference or by text.

## What blocks qualification

1. **Default selection: no evidence gain, C6 recall loss kept.**
   - C8 returns C6's sets.
   - Against C4+sem it loses recall on e5 (−0.227 [−0.287, −0.169]) and on LongMemEval turn @50 (0 / −19, p = 4e-6).
   - 51 needed memories ranked in C8's top 5 are withheld as insufficient: sufficiency is decided on the 3.4.0 order with C6's capped proposals.
2. **LongMemEval turn recall_all@3 regression:**
   - against C6+sem: +16 / −41, p = 0.0013;
   - against C4+sem: +17 / −42;
   - against C4: +16 / −42.

   Single-evidence and multi-evidence questions are both affected.
3. **Cost at 400–500 admitted, default selection:** +17% to +32% over C6+sem. The preregistered cost bound was evaluated only where fusion is skipped.
4. **Silent regime switch at 512 admitted:** fusion off, ranking reverts to 3.4.0, and the posture does not report it.

## Required in a successor (full list in `REVIEW-C8.md` §4)

1. **Reachable gains.** Selection must credit what fusion ranks, or be decided on the returned order. Recall and discovery must be non-inferior to C4+sem on fresh held-out data (lower bound ≥ −0.02), and the C6 review's criteria still apply.
2. **No significant LongMemEval-S loss** at @3, @5 or @10, either plane, against C4+sem, C6+sem or C4. The dense list's influence must be bounded by preregistration, not tuned against LongMemEval or e5.
3. **Cost:** ≤ 1.15× C6+sem at 400–500 admitted under the default selection.
4. **Boundary transparency:** report the 512 fallback in the posture and summaries, and preregister its behaviour.
5. **Ties:** break fused ties by a meaningful signal before the uuid digest.
6. **The developer review's remaining should-fix items:** the dense-failure fallback, the cache key and the `base_ranked_admitted` labelling.

## Still open from C6

- Rebase onto #805 → #815 → #816 and re-run the security replays.
- Declare a Runtime Baseline successor for the protected files.
- Version the LongMemEval lane, recording the ranking policy and fusion status.
- Get an approved semantic-on option for the AMB adapter.

## Evidence

| Evidence | Location |
| --- | --- |
| Review and verdict | `REVIEW-C8.md` |
| e5 commitment and arms | `holdout-e5/COMMITMENT.md` (`fe056bc4`), `holdout-e5/ARMS-ADDENDUM.md` (`8f217f08`) |
| e5 results (9 runs), exec records, steal log, analysis | `candidates/c8-24d4dd2/e5/` |
| LongMemEval-S 500 for C8 route on and off; paired details at each depth | `candidates/c8-24d4dd2/lme500/` |
| Boundary cost and tie probes | `candidates/c8-24d4dd2/probes/` |
| Environment, isolation and pip freeze | `candidates/c8-24d4dd2/provenance/` |

**Next independent cohort (e6):** authored and committed only when a successor is frozen.
