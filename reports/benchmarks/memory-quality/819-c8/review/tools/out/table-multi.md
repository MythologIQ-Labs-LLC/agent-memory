| query | kind | C4+sem-rp | C6+sem-rp | C8-rp | C6+sem-rs | C8-rs |
|---|---|---|---|---|---|---|
| mx-boiler-count | multi_count | 1/7/6 ret=10(3) | 1/7/6 ret=10(3) | 1/3/2 ret=10(3) | 1/7/6 ret=4(3) | 1/3/2 ret=4(3) |
| mx-3hop | multi_three_hop | 2/1/- ret=10(2) | 2/1/- ret=10(2) | 1/2/- ret=10(2) | 2/1/10 ret=5(3) | 1/3/10 ret=5(3) |
| mx-constraint | multi_constraint | 5/4 ret=10(2) | 5/4 ret=10(2) | 4/5 ret=10(2) | 5/4 ret=3(1) | 4/5 ret=3(1) |
| mx-alive | multi_set_difference | 14/1/15/12 ret=10(1) | 14/1/15/12 ret=10(1) | 14/1/15/12 ret=10(1) | -/1/-/- ret=1(1) | -/1/-/- ret=1(1) |
| mx-chores | multi_list | -/-/9 ret=9(1) | -/-/9 ret=9(1) | -/-/9 ret=9(1) | -/-/- ret=1(0) | -/-/- ret=1(0) |
| mx-jobs | multi_sequence | 25/10/4 ret=10(2) | 25/10/4 ret=10(2) | 25/3/5 ret=10(2) | 25/10/4 ret=4(2) | 25/3/5 ret=4(2) |
| mx-holiday | multi_sum | 1/2/3 ret=10(3) | 1/2/3 ret=10(3) | 1/2/4 ret=10(3) | 1/2/3 ret=4(3) | 1/2/4 ret=4(3) |
| mx-older | multi_compare | 2/1 ret=10(2) | 2/1 ret=10(2) | 2/1 ret=10(2) | 2/1 ret=4(2) | 2/1 ret=4(2) |

| aggregate | C4+sem-rp | C6+sem-rp | C8-rp | C6+sem-rs | C8-rs |
|---|---|---|---|---|---|
| queries with needed | 8 | 8 | 8 | 8 | 8 |
| all needed in top 1 | 0 | 0 | 0 | 0 | 0 |
| all needed in top 3 | 2 | 2 | 2 | 2 | 2 |
| all needed in top 5 | 3 | 3 | 4 | 3 | 4 |
| all needed in top 10 | 4 | 4 | 4 | 5 | 5 |
| needed memories (total) | 23 | 23 | 23 | 23 | 23 |
| needed in top 5 | 12 | 12 | 15 | 12 | 15 |
| needed in top 10 | 16 | 16 | 16 | 16 | 16 |
| needed not admitted | 3 | 3 | 3 | 6 | 6 |
| needed returned | 16 | 16 | 16 | 15 | 15 |
| strict pass | 0 | 0 | 0 | 0 | 0 |
| extras returned | 63 | 63 | 63 | 11 | 11 |
| no-answer queries returning | 0 | 0 | 0 | 0 | 0 |
| planted memory at rank 1 | 0 | 0 | 0 | 0 | 0 |
| near_miss: answer at rank 1 | 0 | 0 | 0 | 0 | 0 |
| temporal pairs preferred first | 0 | 0 | 0 | 0 | 0 |
| forbidden in admitted/returned | 0 | 0 | 0 | 0 | 0 |
| forbidden among candidates only | 0 | 0 | 0 | 0 | 0 |
| p50 ms | 28.55 | 27.35 | 30.62 | 27.75 | 28.81 |
