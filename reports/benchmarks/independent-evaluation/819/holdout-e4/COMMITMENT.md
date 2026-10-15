# #819 hidden holdout e4 (evaluator cohort 4): pre-candidate commitment (for C6 onward)

This file is committed after the C6 freeze notice (`171e67db041434e1144dd83a73423af6d4c267e1`) arrived, and **before C6 was checked out or run, and before `FREEZE-C6.md` was read**. The commit carrying it fixes the registration time.

## Why a new cohort

v3's aggregates were published in `../REVIEW-C4.md`, so v3 is spent. The engineering session's own sealed "v4" is engineering-authored, so it is not used for this independent check.

e4 is newly authored:

- a new seed (`am-819-holdout-e4`)
- new vocabulary, domains and phrasings
- the same twelve categories and case format
- multi-hop bridges that share no content word with the question (checked)
- aggregation and paraphrase questions phrased in varied grammar, not only "which …s" forms

The cohort content stays private.

| File | SHA-256 |
| --- | --- |
| `generate.py` | `4340df920ccecb28aa7ab4526cfdbdb23609ad2b7d85f6a97b2b90098e33b4f7` |
| `harness.py` (byte-identical to v1, v2 and v3) | `805d76b1a4eb61207aefdb527648388f1d68985dcc841720435551ec1a35d365` |
| `cases.json` | `976f1f9d5f82a217f8288aebab672d2d4e5da12dbcead8abe1f8f5d45b0c1c07` |

## Public shape

There are 192 scenarios and 208 queries, with 16 per category in the same twelve categories as v3, at `recall(budget=5)` through the public facade.

Non-default facade configurations, such as `semantic_retrieval="required"`, are applied by a separate wrapper that sets `AgentMemory.open` keyword defaults before calling the unchanged `harness.main`. The scorer bytes never change.

## Integrity dry run

One dry run on baseline A checked case construction only. It found 0 evaluation failures and 0 operation refusals, and no case was changed afterwards.
