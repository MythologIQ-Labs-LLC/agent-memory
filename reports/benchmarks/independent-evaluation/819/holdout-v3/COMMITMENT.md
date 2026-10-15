# #819 hidden holdout v3: pre-candidate commitment (for C4 onward)

This file is committed after the C4 freeze notice (`bc2be6319a3eda96731fdb235f4feba882bcb9be`) arrived, and **before C4 was checked out, inspected or run**. The commit carrying it fixes the registration time.

## Why a new cohort

v2's category aggregates were published in `../REVIEW-C3.md`, so v2 is spent for C4. v3 is newly authored:

- a new seed (`am-819-holdout-v3`)
- new vocabulary, domains and phrasings
- the same twelve categories and the same case format

Multi-hop is rebuilt to remove v2's limitation. The bridging fact shares **no content word** with the question, and the generator was checked for this.

The cohort content stays private. Only these hashes are published now.

| File | SHA-256 |
| --- | --- |
| `generate.py` (deterministic, fixed seed) | `e0882dc5a8f1bd63147e2c435a1b293bb180b79781de8a51ac3827f6ed51af36` |
| `harness.py` (byte-identical to v1 and v2) | `805d76b1a4eb61207aefdb527648388f1d68985dcc841720435551ec1a35d365` |
| `cases.json` (generated cohort) | `c869a7bc12e7da8c829fd8ea8e33bcd8457fe9153c03885f720d70754f0269ba` |

## Public shape

There are 192 scenarios and 208 queries, with 16 scenarios in each of twelve categories:

- factual precision
- query disambiguation
- corrected memory
- temporal currentness
- conflicting unreconciled statements
- multi-hop (bridge disjoint from the query)
- multi-evidence aggregation
- abstention
- cross-scope isolation
- irrelevant context
- multi-session (which also checks that a forgotten memory never resurfaces)
- paraphrase recall

Every scenario runs through the public facade at `recall(budget=5)`, with the unchanged scorer and hard gates.

## Integrity dry run

One dry run on baseline A checked case construction only. It found 0 evaluation failures and 0 operation refusals, and no case was changed afterwards.
