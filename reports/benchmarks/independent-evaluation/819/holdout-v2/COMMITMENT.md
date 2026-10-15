# #819 hidden holdout v2: pre-candidate commitment (for C3 onward)

Registered 2026-10-15 at 17:40 UTC. That is after the C3 freeze notice (`6a2255c0f46daa1d546758daa93f4402fed14108`) arrived, and **before C3 was checked out, inspected or run**.

## Why a new cohort

The v1 cohort (176 queries) is spent for any candidate frozen after its C1/C2 per-category aggregates were published in `../REVIEW.md`. Those aggregates could have steered development, for example the multi-hop finding. v2 is newly authored:

- a new seed (`am-819-holdout-v2`)
- new vocabulary, domains and phrasings
- the same case format
- two added categories

The cohort content stays private until no further candidate will be assessed on it. Only these hashes are published now, so neither the cohort nor its scoring can change after candidate performance is seen.

| File | SHA-256 |
| --- | --- |
| `generate.py` (deterministic, fixed seed) | `9ca8001566bd366580622e0511e90fb4c96e68e1527bbdeee9ae5cb9e3ff7dd4` |
| `harness.py` (byte-identical to v1's frozen scorer) | `805d76b1a4eb61207aefdb527648388f1d68985dcc841720435551ec1a35d365` |
| `cases.json` (generated cohort) | `93a67015366f135462c210c47903e5c6c05985d6cb397ee1ada50a84d887a6e2` |

## Public shape

There are 192 scenarios and 208 queries, with 16 scenarios in each of twelve categories:

- factual precision
- query disambiguation
- corrected memory
- temporal currentness
- conflicting unreconciled statements
- multi-hop
- **multi-evidence aggregation** (new: all of several separately stored facts are needed)
- abstention
- cross-scope isolation
- irrelevant context
- multi-session (which also checks that a forgotten memory never resurfaces)
- **paraphrase recall** (new: low lexical overlap between query and fact)

Every scenario runs in a fresh store through the public `AgentMemory` facade only, at `recall(budget=5)`. Scoring and the hard gates (cross-scope, forgotten and stale leaks) are unchanged from v1.

## Integrity dry run

Before this commitment, one dry run on baseline A (`7c06468`) checked case construction only. It found 0 evaluation failures and 0 operation refusals, and no case was changed afterwards. Its aggregate will be reported together with the candidates.
