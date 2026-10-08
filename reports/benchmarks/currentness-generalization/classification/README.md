# #732 currentness generalization: G8 classification

This classification is derived from the frozen, single measurement in
`reports/benchmarks/currentness-generalization/measurement/measurement-v1.json`.
Nothing is re-scored or re-thresholded here.

## Fork outcome

**FAIL** because overall legitimate-change engagement recall is **0/212 (0.000)**,
below the owner-frozen FAIL boundary of 0.50.

All zero-tolerance invariants held:

- structural-guard false engagements: 0;
- non-structural false engagements: 0;
- must-change variants refraining: 320/320;
- unattributed ranking changes: 0;
- invariance: 164/164.

Those safety/invariance results are not treated as evidence of useful currentness
coverage because the mechanism engaged on no base case.

## Positive-family classification

Every P and R family is `deficient` at recall 0.000 and therefore receives the
FAIL-only G8 `:recall` deficit row.

| Family | Valid | Recall | Primary stage | Secondary stages |
|---|---:|---:|---|---|
| P1 | 12 | 0.000 | S3 | — |
| P2 | 12 | 0.000 | S3 | — |
| P3 | 12 | 0.000 | S3 | S2 |
| P4 | 12 | 0.000 | S3 | S2 |
| P5 | 12 | 0.000 | S3 | — |
| P6 | 12 | 0.000 | S3 | S2 |
| P7 | 12 | 0.000 | S3 | S1 |
| P8 | 12 | 0.000 | S3 | — |
| P9 | 12 | 0.000 | S3 | S2 |
| P10 | 12 | 0.000 | S3 | S2 |
| P11 | 12 | 0.000 | S3 | — |
| P12 | 12 | 0.000 | S3 | S2 |
| P13 | 12 | 0.000 | S3 | S2 |
| R1 | 8 | 0.000 | S3 | — |
| R2 | 8 | 0.000 | S3 | — |
| R3 | 8 | 0.000 | S3 | — |
| R4 | 8 | 0.000 | S3 | — |
| R5 | 8 | 0.000 | S3 | — |
| R6 | 8 | 0.000 | S3 | — |
| R7 | 8 | 0.000 | S3 | S2 |

Across all positive cases:

- S3 / no write-time relation: **197/212**;
- retrieval admission S1/S2: **15/212**.

## Routing

The dominant S3 failure is owned by #732's typed write-time semantic remediation.
The S1/S2 tail remains retrieval evidence and must not be hidden by that dominant
cause.

Closure requires the pre-registered replay set:

1. one fresh single-use G6 holdout meeting every frozen PASS criterion over
   non-narrowed families;
2. MESA v2 M4 = 1.000 with every win attributed to
   `currentness_mechanism`;
3. #580 and #584 unchanged.

#673 remains held until #732 remediation is accepted.
