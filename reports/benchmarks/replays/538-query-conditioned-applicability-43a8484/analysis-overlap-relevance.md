| config | revision | ranking variant | temporal metadata | policy |
| --- | --- | --- | --- | --- |
| frozen | `f73b872` | n/a (pre-option) | none | clean |
| universal | `9c2ba70` | n/a (pre-option) | none | clean |
| qc_overlap | `43a8484` | overlap_query_conditioned | none | clean |
| qc_overlap_refasc | `43a8484` | overlap_query_conditioned_ref_asc | none | clean |
| qc_overlap_dates | `43a8484` | overlap_query_conditioned | host_declared | clean |

### session plane (scored n=419)

| metric | lexical | frozen | universal | qc_overlap | qc_overlap_refasc | qc_overlap_dates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| recall_all@5 | 0.730 | 0.675 | 0.687 | 0.668 | 0.673 | 0.668 |
| ndcg_any@5 | 0.767 | 0.722 | 0.732 | 0.729 | 0.719 | 0.729 |
| recall_all@10 | 0.826 | 0.797 | 0.802 | 0.795 | 0.792 | 0.795 |
| ndcg_any@10 | 0.793 | 0.756 | 0.761 | 0.760 | 0.752 | 0.760 |
| latest_gold_first, knowledge-update | | 0.343 (n=70) | 0.629 (n=70) | 0.486 (n=70) | 0.371 (n=70) | 0.486 (n=70) |
| latest_gold_first, all multi-date gold | | 0.372 (n=282) | 0.532 (n=282) | 0.457 (n=282) | 0.383 (n=282) | 0.461 (n=282) |
| failures (runtime/ingest/out-of-corpus) | | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |

recall_all@5 by question type; Δ columns are paired vs `universal`, mean [95% CI] better/worse

| question type | n | frozen | universal | qc_overlap | qc_overlap_refasc | qc_overlap_dates | Δ frozen | Δ qc_overlap | Δ qc_overlap_refasc | Δ qc_overlap_dates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| knowledge-update | 72 | 0.931 | 0.889 | 0.889 | 0.917 | 0.889 | +0.042 [-0.014,+0.111] 4/1 | +0.000 [+0.000,+0.000] 0/0 | +0.028 [+0.000,+0.069] 2/0 | +0.000 [+0.000,+0.000] 0/0 |
| multi-session | 121 | 0.488 | 0.479 | 0.479 | 0.488 | 0.479 | +0.008 [-0.058,+0.074] 9/8 | +0.000 [-0.050,+0.050] 5/5 | +0.008 [-0.058,+0.074] 9/8 | +0.000 [-0.050,+0.050] 5/5 |
| single-session-assistant | 5 | 0.800 | 0.800 | 0.800 | 0.800 | 0.800 | +0.000 [+0.000,+0.000] 0/0 | +0.000 [+0.000,+0.000] 0/0 | +0.000 [+0.000,+0.000] 0/0 | +0.000 [+0.000,+0.000] 0/0 |
| single-session-preference | 30 | 0.333 | 0.433 | 0.400 | 0.333 | 0.400 | -0.100 [-0.200,+0.000] 0/3 | -0.033 [-0.100,+0.000] 0/1 | -0.100 [-0.200,+0.000] 0/3 | -0.033 [-0.100,+0.000] 0/1 |
| single-session-user | 64 | 0.938 | 0.984 | 0.953 | 0.938 | 0.953 | -0.047 [-0.109,+0.000] 0/3 | -0.031 [-0.078,+0.000] 0/2 | -0.047 [-0.109,+0.000] 0/3 | -0.031 [-0.078,+0.000] 0/2 |
| temporal-reasoning | 127 | 0.654 | 0.677 | 0.638 | 0.654 | 0.638 | -0.024 [-0.071,+0.024] 4/7 | -0.039 [-0.087,+0.008] 2/7 | -0.024 [-0.071,+0.024] 4/7 | -0.039 [-0.087,+0.008] 2/7 |
| ALL | 419 | 0.675 | 0.687 | 0.668 | 0.673 | 0.668 | -0.012 [-0.041,+0.017] 17/22 | -0.019 [-0.041,+0.002] 7/15 | -0.014 [-0.043,+0.014] 15/21 | -0.019 [-0.041,+0.002] 7/15 |

latest_gold_first by interpreted intent class (knowledge-update)

| intent class | n | frozen | universal | qc_overlap | qc_overlap_refasc | qc_overlap_dates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current (orders) | 15 | 0.533 (15) | 0.667 (15) | 0.667 (15) | 0.667 (15) | 0.667 (15) |
| no temporal ordering | 55 | 0.278 (54) | 0.611 (54) | 0.426 (54) | 0.278 (54) | 0.426 (54) |
| prospective (orders) | 2 | 1.000 (1) | 1.000 (1) | 1.000 (1) | 1.000 (1) | 1.000 (1) |

### turn plane (scored n=419)

| metric | lexical | frozen | universal | qc_overlap | qc_overlap_refasc | qc_overlap_dates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| recall_all@5 | 0.487 | 0.439 | 0.434 | 0.432 | 0.439 | 0.434 |
| ndcg_any@5 | 0.527 | 0.502 | 0.484 | 0.490 | 0.498 | 0.490 |
| recall_all@10 | 0.587 | 0.525 | 0.532 | 0.516 | 0.525 | 0.516 |
| recall_all@50 | 0.761 | 0.764 | 0.766 | 0.759 | 0.764 | 0.759 |
| latest_gold_first, knowledge-update | | 0.486 (n=70) | 0.743 (n=70) | 0.643 (n=70) | 0.571 (n=70) | 0.643 (n=70) |
| latest_gold_first, all multi-date gold | | 0.411 (n=282) | 0.589 (n=282) | 0.500 (n=282) | 0.440 (n=282) | 0.500 (n=282) |
| failures (runtime/ingest/out-of-corpus) | | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |

recall_all@10 by question type; Δ columns are paired vs `universal`, mean [95% CI] better/worse

| question type | n | frozen | universal | qc_overlap | qc_overlap_refasc | qc_overlap_dates | Δ frozen | Δ qc_overlap | Δ qc_overlap_refasc | Δ qc_overlap_dates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| knowledge-update | 72 | 0.736 | 0.736 | 0.722 | 0.736 | 0.722 | +0.000 [-0.056,+0.056] 2/2 | -0.014 [-0.042,+0.000] 0/1 | +0.000 [-0.056,+0.056] 2/2 | -0.014 [-0.042,+0.000] 0/1 |
| multi-session | 121 | 0.322 | 0.306 | 0.322 | 0.322 | 0.322 | +0.017 [-0.041,+0.074] 7/5 | +0.017 [-0.017,+0.050] 3/1 | +0.017 [-0.041,+0.074] 7/5 | +0.017 [-0.017,+0.050] 3/1 |
| single-session-assistant | 5 | 0.600 | 0.600 | 0.600 | 0.600 | 0.600 | +0.000 [+0.000,+0.000] 0/0 | +0.000 [+0.000,+0.000] 0/0 | +0.000 [+0.000,+0.000] 0/0 | +0.000 [+0.000,+0.000] 0/0 |
| single-session-preference | 30 | 0.100 | 0.167 | 0.100 | 0.100 | 0.100 | -0.067 [-0.167,+0.000] 0/2 | -0.067 [-0.167,+0.000] 0/2 | -0.067 [-0.167,+0.000] 0/2 | -0.067 [-0.167,+0.000] 0/2 |
| single-session-user | 64 | 0.828 | 0.875 | 0.844 | 0.828 | 0.844 | -0.047 [-0.109,+0.000] 0/3 | -0.031 [-0.078,+0.000] 0/2 | -0.047 [-0.109,+0.000] 0/3 | -0.031 [-0.078,+0.000] 0/2 |
| temporal-reasoning | 127 | 0.543 | 0.543 | 0.512 | 0.543 | 0.512 | +0.000 [-0.055,+0.047] 6/6 | -0.031 [-0.079,+0.008] 2/6 | +0.000 [-0.055,+0.047] 6/6 | -0.031 [-0.079,+0.008] 2/6 |
| ALL | 419 | 0.525 | 0.532 | 0.516 | 0.525 | 0.516 | -0.007 [-0.033,+0.021] 15/18 | -0.017 [-0.036,+0.002] 5/12 | -0.007 [-0.033,+0.021] 15/18 | -0.017 [-0.036,+0.002] 5/12 |

latest_gold_first by interpreted intent class (knowledge-update)

| intent class | n | frozen | universal | qc_overlap | qc_overlap_refasc | qc_overlap_dates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current (orders) | 15 | 0.467 (15) | 0.867 (15) | 0.867 (15) | 0.867 (15) | 0.867 (15) |
| no temporal ordering | 55 | 0.481 (54) | 0.704 (54) | 0.574 (54) | 0.481 (54) | 0.574 (54) |
| prospective (orders) | 2 | 1.000 (1) | 1.000 (1) | 1.000 (1) | 1.000 (1) | 1.000 (1) |
