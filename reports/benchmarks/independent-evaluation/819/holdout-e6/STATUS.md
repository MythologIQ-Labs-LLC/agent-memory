# e6 lane status, 2026-10-17 (interim; no candidate evaluated yet)

## Verdict

**Integration is not recommended.** No isolated discovery or selection candidate has been frozen and posted on #819. At 2026-10-17T18:00Z the only C9 ref was the instrumentation branch `implementation/819-c9-selection-funnel-no-ci` @ `535de734`, which is not a quality candidate. Candidate arms 4–8 of `PREREGISTRATION.md` are pending.

## Done

| Step | Evidence |
|---|---|
| e6 sealed and arms and gates preregistered before any candidate access | `97f76dd4` (`COMMITMENT.md`, `PREREGISTRATION.md`) |
| Baseline arms 1–3 and a C4 repeat on e6 | `receipts/*.exec.json`, `receipts/SHA256SUMS-sealed-results.txt`. All runs: 288/288 executed, 0 operation failures, 0 errors. |
| Determinism | C4 default repeat: identical returned lists on 288/288 |
| LongMemEval-S 500 host reproduction (C4 default, runner `6b9c2373`) | 500/500 per-question metrics are identical to the lane's committed `c16d890f…` output on both planes (`receipts/lme-c4def-host-reproduction.json`) |
| LME tool validation | The committed C4+sem → C6+sem outputs reproduce REVIEW-C6: turn recall_all@10 0.7924 → 0.7613, +1/−14, p = 0.00098 |
| Cost probe for arms 1–3 | `cost/` |

## e6 disclosure before the verdict

Scores, per-category results and labels stay sealed.

There is one exception, a safety-gate status. **The preregistered G3, zero leaks, already fails for all three baseline arms (C4, C4+sem and C6+sem).**
- **Why this is disclosed.** The leaking class is the one already published in REVIEW-C6: as-of recall returns a successor that only becomes valid after the as-of date. Disclosing it reveals nothing new.
- **Other safety classes.** No other safety class leaked in any baseline arm.

G3 is not relaxed. A candidate that inherits this behaviour fails G3. Whether to accept an inherited, pre-existing defect is an owner decision outside this lane.

## Cost probe (synthetic; all N memories admitted; budget 5; two repetitions)

| Arm | N | warm p50 (ms) | warm p95 (ms) | cold first recall (ms) | peak RSS (MiB) |
|---|---:|---|---|---|---:|
| C4 default | 200 | 26.3 / 24.8 | 42.0 / 28.4 | 34 / 32 | 41 |
| C4 default | 400 | 49.7 / 50.0 | 95.3 / 107.7 | 58 / 88 | 47 |
| C4 default | 450 | 56.2 / 53.9 | 81.4 / 69.4 | 130 / 128 | 49 |
| C4 default | 500 | 59.4 / 61.2 | 73.2 / 77.9 | 66 / 101 | 50 |
| C4+sem | 200 | 53.8 / 50.0 | 133.9 / 55.8 | 1706 / 1749 | 333 |
| C4+sem | 400 | 91.8 / 97.0 | 133.2 / 143.2 | 3331 / 3853 | 334 |
| C4+sem | 450 | 97.5 / 102.6 | 116.1 / 145.2 | 3987 / 3729 | 333 |
| C4+sem | 500 | 119.0 / 112.6 | 283.7 / 135.4 | 4079 / 3950 | 335 |
| C6+sem | 200 | 54.0 / 51.1 | 175.0 / 86.1 | 1882 / 1759 | 332 |
| C6+sem | 400 | 89.6 / 95.6 | 103.1 / 137.6 | 3211 / 3247 | 332 |
| C6+sem | 450 | 105.1 / 103.6 | 137.1 / 144.4 | 4079 / 3580 | 334 |
| C6+sem | 500 | 113.4 / 117.0 | 151.9 / 144.4 | 4032 / 4152 | 332 |

**How to read it:**
- **The G5 reference** is C6+sem's p95 at 400–500 admitted: 103–152 ms.
- **p95 is noisy.** It varies up to 2× between repetitions (C4+sem, N = 500: 284 and 135 ms). Verdicts will therefore use the maximum over repetitions, and a candidate will be run interleaved with C6+sem.
- **Cold first recall** with the route on is 1.7–4.2 s, because embedding happens at first recall.
- **What this lane cannot measure.** End-to-end timing cannot separate discovery, ranking and selection costs. A candidate must expose those itself.

## Next

1. **On a posted freeze:** fetch the exact SHA, build a venv from its own pins, and run arms 4–8 on e6.
2. **LongMemEval:** run it on runner blob `6b9c2373`.
3. **Cost probe:** run it interleaved with C6+sem.
4. **Verdict:** compute the paired statistics with `e6_analyze.py`, publish the verdict, and then disclose the e6 content, which spends the cohort.
