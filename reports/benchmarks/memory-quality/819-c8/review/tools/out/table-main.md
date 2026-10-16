| query | kind | C4+sem-rp | C6+sem-rp | C8-rp | C6+sem-rs | C8-rs |
|---|---|---|---|---|---|---|
| h-multi-pets | multi_list | 46/16/11 ret=10(0) | 46/16/11 ret=10(0) | 46/6/4 ret=10(2) | 46/16/11 ret=3(1) | 46/6/4 ret=3(1) |
| h-multi-chain | multi_chain | 4/9 ret=10(2) | 4/9 ret=10(2) | 5/6 ret=10(2) | 4/9 ret=3(1) | 5/6 ret=3(1) |
| h-multi-allergy | multi_exception | 6/- ret=9(1) | 6/- ret=9(1) | 6/- ret=9(1) | 6/- ret=3(1) | 6/- ret=3(1) |
| h-near-dentist | near_miss | - ret=10(0) | - ret=10(0) | - ret=10(0) | - ret=2(0) | - ret=2(0) |
| h-near-gp | near_miss | 2 ret=10(1) | 2 ret=10(1) | 1 ret=10(1) | 2 ret=0(0) | 1 ret=0(0) |
| h-stuff-wifi | stuffing | 14 pl=1/2 ret=10(0) | 14 pl=1/2 ret=10(0) | 5 pl=1/2 ret=10(1) | 14 pl=1/2 ret=2(0) | 5 pl=1/2 ret=2(0) |
| h-stuff-bins | stuffing | 45 pl=1 ret=10(0) | 45 pl=1 ret=10(0) | 45 pl=1 ret=10(0) | - pl=1 ret=2(0) | - pl=1 ret=2(0) |
| h-decl-open-car | declared_open | 4 pf=N ret=10(1) | 4 pf=N ret=10(1) | 2 pf=N ret=10(1) | 4 pf=N ret=2(1) | 2 pf=N ret=2(1) |
| h-asof-car | as_of_open | 2 pf=Y ret=10(1) | 2 pf=Y ret=10(1) | 1 pf=Y ret=10(1) | 2 pf=Y ret=2(1) | 1 pf=Y ret=2(1) |
| h-decl-closed-gym | declared_closed | 3 pf=Y ret=10(1) | 3 pf=Y ret=10(1) | 1 pf=Y ret=10(1) | 3 pf=Y ret=3(1) | 1 pf=Y ret=3(1) |
| h-hist-gym | historical | 1 pf=Y ret=10(1) | 1 pf=Y ret=10(1) | 1 pf=Y ret=10(1) | 1 pf=Y ret=3(1) | 1 pf=Y ret=3(1) |
| h-conflict-barber | conflict | 3 pf=N ret=10(1) | 3 pf=N ret=10(1) | 2 pf=N ret=10(1) | 3 pf=N ret=2(1) | 2 pf=N ret=2(1) |
| h-noans-boat | no_answer | . ret=10 | . ret=10 | . ret=10 | . ret=1 | . ret=1 |
| h-noans-dentist-cost | no_answer | . ret=10 | . ret=10 | . ret=10 | . ret=0 | . ret=0 |
| m-multi-compare | multi_compare | 1/3 ret=10(2) | 1/3 ret=10(2) | 1/2 ret=10(2) | 1/3 ret=2(2) | 1/2 ret=2(2) |
| m-multi-homes | multi_sequence | 12/6/5 ret=10(2) | 12/6/5 ret=10(2) | 6/4/1 ret=10(3) | 12/6/5 ret=0(0) | 6/4/1 ret=0(0) |
| m-multi-subs | multi_list | 3/19/17 pl=1/2 ret=10(1) | 3/19/17 pl=1/2 ret=10(1) | 3/19/17 pl=1/2 ret=10(1) | 3/-/- pl=1/2 ret=2(0) | 3/-/- pl=1/2 ret=2(0) |
| m-near-passport | near_miss | 1 ret=6(1) | 1 ret=6(1) | 1 ret=6(1) | 1 ret=3(1) | 1 ret=3(1) |
| m-decl-open-work | declared_open | 3 pf=N ret=8(1) | 3 pf=N ret=8(1) | 2 pf=N ret=8(1) | 3 pf=N ret=2(1) | 2 pf=N ret=2(1) |
| m-asof-work | as_of_open | 4 pf=Y ret=8(1) | 4 pf=Y ret=8(1) | 2 pf=Y ret=8(1) | 4 pf=Y ret=2(1) | 2 pf=Y ret=2(1) |
| m-decl-closed-bank | declared_closed | 1 pf=Y ret=10(1) | 1 pf=Y ret=10(1) | 1 pf=Y ret=10(1) | 1 pf=Y ret=2(1) | 1 pf=Y ret=2(1) |
| m-hist-bank | historical | 1 pf=Y ret=9(1) | 1 pf=Y ret=9(1) | 1 pf=Y ret=9(1) | 1 pf=Y ret=2(1) | 1 pf=Y ret=2(1) |
| m-conflict-commute | conflict | 5 pf=Y ret=9(1) | 5 pf=Y ret=9(1) | 4 pf=Y ret=9(1) | 5 pf=Y ret=3(0) | 4 pf=Y ret=3(0) |
| m-noans-crypto | no_answer | . ret=10 | . ret=10 | . ret=10 | . ret=0 | . ret=0 |
| t-multi-trips | multi_list | 14/-/11 pl=2 ret=10(0) | 14/-/11 pl=2 ret=10(0) | 13/-/6 pl=1 ret=10(1) | 14/-/11 pl=2 ret=1(0) | 13/-/6 pl=1 ret=1(0) |
| t-multi-chain | multi_chain | 5/6 ret=7(2) | 5/6 ret=7(2) | 5/6 ret=7(2) | 5/6 ret=2(1) | 5/6 ret=2(1) |
| t-multi-quit | multi_exception | 6/3 ret=9(2) | 6/3 ret=9(2) | 3/7 ret=9(2) | 6/3 ret=0(0) | 3/7 ret=0(0) |
| t-near-book | near_miss | 1 ret=10(1) | 1 ret=10(1) | 1 ret=10(1) | 1 ret=3(1) | 1 ret=3(1) |
| t-conflict-phone | conflict | 2 pf=Y ret=10(1) | 2 pf=Y ret=10(1) | 2 pf=N ret=10(1) | 2 pf=Y ret=3(1) | 2 pf=N ret=3(1) |
| t-noans-ski | no_answer | . ret=8 | . ret=8 | . ret=8 | . ret=0 | . ret=0 |

| aggregate | C4+sem-rp | C6+sem-rp | C8-rp | C6+sem-rs | C8-rs |
|---|---|---|---|---|---|
| queries with needed | 26 | 26 | 26 | 26 | 26 |
| all needed in top 1 | 5 | 5 | 8 | 5 | 8 |
| all needed in top 3 | 12 | 12 | 14 | 12 | 14 |
| all needed in top 5 | 15 | 15 | 16 | 15 | 16 |
| all needed in top 10 | 18 | 18 | 20 | 18 | 20 |
| needed memories (total) | 39 | 39 | 39 | 39 | 39 |
| needed in top 5 | 21 | 21 | 24 | 21 | 24 |
| needed in top 10 | 26 | 26 | 31 | 26 | 31 |
| needed not admitted | 3 | 3 | 3 | 6 | 6 |
| needed returned | 26 | 26 | 31 | 18 | 18 |
| strict pass | 0 | 0 | 0 | 11 | 11 |
| extras returned | 248 | 248 | 243 | 26 | 26 |
| no-answer queries returning | 4 | 4 | 4 | 1 | 1 |
| planted memory at rank 1 | 3 | 3 | 4 | 3 | 4 |
| near_miss: answer at rank 1 | 2 | 2 | 3 | 2 | 3 |
| temporal pairs preferred first | 8 | 8 | 7 | 8 | 7 |
| forbidden in admitted/returned | 0 | 0 | 0 | 0 | 0 |
| forbidden among candidates only | 2 | 2 | 2 | 2 | 2 |
| p50 ms | 23.82 | 23.95 | 21.7 | 25.33 | 27.48 |
