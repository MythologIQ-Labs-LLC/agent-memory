# #732 currentness generalization: measurement v1

This is the bound result of the single measurement required by `docs/plan-732-generalization-gate.md` (G9 step 4). It runs on `main` at `db20b4e867e65b7a0b7d3e9c4731f5558affeab7`, the merge of the freeze in #738, against **Runtime Baseline v5 unchanged**.

| Item | Value |
|---|---|
| Runtime Baseline equivalence checker | PASS (exit 0) |
| Assertion filter (G12) | 6.0.0 |
| Ranking policy | 3.3.0 |
| Corpus | `cf2e7646c4ba…` |
| Variants | `72588822196e…` |
| Scope | explicit change assertions only; bare restatements of a new value are not measured (plan-732 D4) |

## Verdict: **FAIL**

The FAIL reasons are `overall_recall_below_0.50`. Nothing is re-scored or re-thresholded.

| Metric | Result | Owner threshold |
|---|---|---|
| Overall engagement recall (P and R base cases) | **0.0** (0 of 212) | PASS ≥ 0.80; FAIL < 0.50 |
| Recall in every P and R family | 0.000 in all 20 families | ≥ 0.60 each |
| Non-structural false engagements | 0 | ≤ 1 |
| Structural-guard false engagements | 0 | 0 |
| M-inv (metamorphic invariance) | 1.0 (164/164) | ≥ 0.95 |
| M-flip (must-change variants refrain) | 1.0 (320/320) | 100% |
| M-attr (unattributed ranking changes) | 0 | 0 |
| S0 invalid-harness cases | 0 | — |

Every zero-tolerance invariant holds:
- no unattributed ranking change;
- no structural-guard false engagement;
- every must-change variant refrains.

They hold vacuously, because the mechanism engaged on **no** case.

M-inv = 1.0 for the same reason: every base case and its invariance variants refrain alike.

## Where positives stop (G4 stages, P and R base cases)

| Stage | Cases |
|---|---|
| `no_write_time_relation` | 197 |
| `newer_not_admitted` | 12 |
| `older_not_admitted` | 3 |

Of the 212 legitimate changes, 197 have **no write-time relation** from the newer fact to the older one (S3). The mechanism's read path is never reached.

The remaining 15 are retrieval misses (S1/S2), where one of the two memories was not admitted for the natural query.

## Negative families

| Stage | Cases |
|---|---|
| `no_write_time_relation` | 73 |
| `newer_not_admitted` | 28 |
| `guard_refusal:G9` | 2 |
| `relation_not_state_change` | 1 |

## Per family

| Family | Valid / size | Recall or false engagements | Class | Stages |
|---|---|---|---|---|
| P1 | 12/12 | 0.000 | deficient | S3 12 |
| P2 | 12/12 | 0.000 | deficient | S3 12 |
| P3 | 12/12 | 0.000 | deficient | S2 2, S3 10 |
| P4 | 12/12 | 0.000 | deficient | S2 2, S3 10 |
| P5 | 12/12 | 0.000 | deficient | S3 12 |
| P6 | 12/12 | 0.000 | deficient | S2 2, S3 10 |
| P7 | 12/12 | 0.000 | deficient | S1 3, S3 9 |
| P8 | 12/12 | 0.000 | deficient | S3 12 |
| P9 | 12/12 | 0.000 | deficient | S2 1, S3 11 |
| P10 | 12/12 | 0.000 | deficient | S2 1, S3 11 |
| P11 | 12/12 | 0.000 | deficient | S3 12 |
| P12 | 12/12 | 0.000 | deficient | S2 1, S3 11 |
| P13 | 12/12 | 0.000 | deficient | S2 2, S3 10 |
| R1 | 8/8 | 0.000 | deficient | S3 8 |
| R2 | 8/8 | 0.000 | deficient | S3 8 |
| R3 | 8/8 | 0.000 | deficient | S3 8 |
| R4 | 8/8 | 0.000 | deficient | S3 8 |
| R5 | 8/8 | 0.000 | deficient | S3 8 |
| R6 | 8/8 | 0.000 | deficient | S3 8 |
| R7 | 8/8 | 0.000 | deficient | S2 1, S3 7 |
| N1 | 8/8 | 0 | safe | S2 1, S3 7 |
| N2 | 8/8 | 0 | safe | S3 8 |
| N3 | 8/8 | 0 | safe | S2 1, S3 7 |
| N4 | 8/8 | 0 | safe | S2 1, S3 7 |
| N5 | 8/8 | 0 | safe | S2 1, S3 7 |
| N6 | 8/8 | 0 | safe | S3 8 |
| N7 | 8/8 | 0 | safe | S3 7, S5 1 |
| N8 | 8/8 | 0 | safe | S3 7, S5 1 |
| N9 | 8/8 | 0 | safe | S2 1, S3 7 |
| N10 | 8/8 | 0 | safe | S2 8 |
| N11 | 8/8 | 0 | safe | S2 3, S3 4, S4 1 |
| N12 | 8/8 | 0 | safe | S2 4, S3 4 |
| N13 | 8/8 | 0 | safe | S2 8 |

## Fork (owner direction, plan G7): FAIL

- **#673 stays held.** #732 remediation is inserted before #673.
- **Routing by stage:**
  - S3 (no write-time relation): 197 of 212 positives. These go to write-time recognition (typed write-time assertion and change semantics; #596/#597; #732's preferred direction).
  - S1/S2: 15. These go to retrieval.
- **Remediation constraints:**
  - it is generic, never case-by-case G12 expansion;
  - it is accepted only under G6: a fresh single-use holdout meeting every PASS criterion;
  - the MESA v2 M4 floor and #580/#584 must hold.
- **Interpretation:** MESA M4 1.000 is a property of benchmark-shaped language. On independently authored natural statements of legitimate single-valued change, Runtime Baseline v5 recognises none at write time. #671 stays open.

Classification rows in the #719 deficit ledger (G8) follow in the classification PR. That PR waits for the parent row from #733 (plan D8).
