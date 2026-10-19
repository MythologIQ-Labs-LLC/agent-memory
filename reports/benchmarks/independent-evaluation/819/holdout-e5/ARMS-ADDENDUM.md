# e5 arms addendum: fixed before any candidate run

- **Timing.** Written after reading C8's preregistration (`24d4dd26:reports/benchmarks/memory-quality/819-c8/PREREGISTRATION-C8.md`) and its runtime diff against C6. No candidate has been run on e5, and the cohort and scorer are unchanged (see `COMMITMENT.md`).
- **Why.** C8's preregistration states two applicable configurations with the route on:
  - `ranked_prefix`, used by its rank-quality gate against C4+sem;
  - the default `relevance_sufficient`, used by its selection gate against C6+sem.

  Under `relevance_sufficient`, sufficiency is decided on the 3.4.0 order, while the returned facts and the budget cut follow the fused 3.5.0 order. Both modes are therefore evaluated.

## Wrapper

`run_rp.py` (sha256 `f756a5c650d96fcec691e1622a52a868c9a62fdf7fafd1c49e45efaee135f84d`) sets only `AgentMemory.recall`'s default `return_selection` to `ranked_prefix`, then runs the sealed `harness.py` unchanged.

## Arms

| # | Runtime | Semantic | Return selection |
|---:|---|---|---|
| 1 | C4 `bc2be631` | off | default (`relevance_sufficient`) |
| 2 | C4 | required | default |
| 3 | C4 | required | `ranked_prefix` (C8's rank-gate comparator) |
| 4 | C6 `171e67db` | required | default |
| 5 | C6 | required | `ranked_prefix` |
| 6 | **C8 `24d4dd26`** | required | default |
| 7 | **C8** | required | `ranked_prefix` |
| 8 | C8 | off | default (route-off equivalence against C4 and C6) |

## Primary paired comparisons

- **C8 against C4+sem, the essential comparator:** arms 6 against 2, and 7 against 3.
- **C8 against C6+sem:** arms 6 against 4, and 7 against 5.
- **C8 against C4 default:** arms 6 against 1.

## Rank depth

Rank depth is read from the full ranked admitted list in every arm, as depth recall@{1, 3, 5, 10}.

## LongMemEval-S 500

The runner `6b9c2373` has no return-selection option, so it runs the default only:
- C8+sem;
- C8 with the route off.

Both are compared with this lane's committed C4, C4+sem and C6+sem outputs from the same host type, input and runner.
