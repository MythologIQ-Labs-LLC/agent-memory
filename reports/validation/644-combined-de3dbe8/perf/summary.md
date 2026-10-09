
### 1,000 facts (median / p95 ms)

| measure | v6f | e002536 | de3dbe8 | 46d84ad |
|---|---|---|---|---|
| governed recall (includes receipt capture where present) | 27.03 / 33.03 | 27.05 / 36.02 | 28.41 / 42.99 | 24.57 / 31.82 |
| receipt capture alone | — | — | 0.20 / 0.31 | 0.17 / 0.22 |
| receipt verification (observation_unchanged) | — | — | 0.06 / 0.12 | 0.05 / 0.07 |
| slot audit (e002536: full-store scan) | — | 62.03 / 80.90 | 1.57 / 2.58 | 1.41 / 1.86 |
| combined observer (coverage + audit [+ receipt check]) | — | 64.28 / 86.97 | 4.91 / 7.32 | 4.38 / 5.75 |
| reference: full-store enumeration, same per-fact work | — | 59.63 / 75.43 | 65.15 / 73.99 | 61.32 / 73.48 |
| index rebuild (warm process) | — | 17.99 / 25.71 | 20.95 / 26.48 | 16.29 / 18.14 |
| cold open | 146.33 / 201.39 | 156.40 / 194.93 | 144.61 / 173.93 | 175.97 / 196.74 |
| cold first recall | 23.93 / 32.37 | 28.02 / 36.40 | 24.18 / 37.75 | 31.14 / 41.22 |
| cold first index build | — | 22.29 / 30.16 | 16.95 / 25.60 | 21.30 / 24.80 |
| cold first audit | — | 60.56 / 68.66 | 1.44 / 1.80 | 1.52 / 2.67 |
| cold first observer | — | 60.26 / 70.44 | 4.73 / 5.14 | 4.96 / 6.66 |
samples: warm v6f=30, e002536=30, de3dbe8=30, 46d84ad=30; cold v6f=5, e002536=5, de3dbe8=5, 46d84ad=5; admitted/candidates v6f=8/8, e002536=8/8, de3dbe8=8/8, 46d84ad=8/8

### 3,000 facts (median / p95 ms)

| measure | v6f | e002536 | de3dbe8 | 46d84ad |
|---|---|---|---|---|
| governed recall (includes receipt capture where present) | 81.16 / 103.03 | 79.83 / 101.82 | 84.01 / 121.96 | 76.14 / 93.58 |
| receipt capture alone | — | — | 0.21 / 0.30 | 0.18 / 0.23 |
| receipt verification (observation_unchanged) | — | — | 0.06 / 0.09 | 0.05 / 0.07 |
| slot audit (e002536: full-store scan) | — | 184.11 / 244.91 | 4.39 / 6.79 | 3.69 / 4.28 |
| combined observer (coverage + audit [+ receipt check]) | — | 189.05 / 220.73 | 7.83 / 10.94 | 7.18 / 8.10 |
| reference: full-store enumeration, same per-fact work | — | 166.88 / 229.23 | 202.18 / 214.66 | 172.79 / 188.39 |
| index rebuild (warm process) | — | 65.39 / 71.78 | 64.94 / 81.00 | 57.08 / 72.88 |
| cold open | 457.83 / 594.05 | 451.18 / 525.39 | 497.91 / 731.89 | 450.31 / 524.23 |
| cold first recall | 76.85 / 111.11 | 77.51 / 121.23 | 93.89 / 104.08 | 87.35 / 105.75 |
| cold first index build | — | 55.29 / 73.86 | 87.02 / 94.54 | 57.99 / 72.39 |
| cold first audit | — | 176.47 / 198.40 | 6.73 / 7.75 | 3.67 / 5.39 |
| cold first observer | — | 170.06 / 198.91 | 11.10 / 12.24 | 7.49 / 8.88 |
samples: warm v6f=30, e002536=30, de3dbe8=30, 46d84ad=30; cold v6f=5, e002536=5, de3dbe8=5, 46d84ad=5; admitted/candidates v6f=8/8, e002536=8/8, de3dbe8=8/8, 46d84ad=8/8

### 10,000 facts (median / p95 ms)

| measure | v6f | e002536 | de3dbe8 | 46d84ad |
|---|---|---|---|---|
| governed recall (includes receipt capture where present) | 285.26 / 345.18 | 262.04 / 365.32 | 286.04 / 343.28 | 279.63 / 343.84 |
| receipt capture alone | — | — | 0.20 / 0.26 | 0.19 / 0.23 |
| receipt verification (observation_unchanged) | — | — | 0.06 / 0.10 | 0.05 / 0.07 |
| slot audit (e002536: full-store scan) | — | 617.74 / 686.64 | 12.27 / 19.15 | 12.33 / 13.51 |
| combined observer (coverage + audit [+ receipt check]) | — | 661.34 / 760.11 | 15.79 / 23.46 | 15.30 / 17.24 |
| reference: full-store enumeration, same per-fact work | — | 663.33 / 720.14 | 613.09 / 664.28 | 627.55 / 681.76 |
| index rebuild (warm process) | — | 232.43 / 284.52 | 272.91 / 290.08 | 228.02 / 294.42 |
| cold open | 1734.56 / 2456.31 | 1577.54 / 1604.53 | 1538.70 / 1606.24 | 1574.22 / 1717.55 |
| cold first recall | 265.88 / 307.50 | 321.09 / 408.34 | 356.79 / 415.28 | 397.70 / 496.76 |
| cold first index build | — | 250.79 / 292.75 | 257.17 / 343.49 | 222.63 / 298.25 |
| cold first audit | — | 639.32 / 708.26 | 13.08 / 16.65 | 12.78 / 13.20 |
| cold first observer | — | 614.00 / 683.66 | 17.15 / 18.82 | 16.50 / 19.18 |
samples: warm v6f=30, e002536=30, de3dbe8=30, 46d84ad=30; cold v6f=5, e002536=5, de3dbe8=5, 46d84ad=5; admitted/candidates v6f=8/8, e002536=8/8, de3dbe8=8/8, 46d84ad=8/8
