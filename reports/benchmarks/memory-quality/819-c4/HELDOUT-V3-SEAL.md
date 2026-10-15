# Held-out v3 seal (#819 C4)

Committed **before** the C4 candidate is frozen. The cohort content has not been read by the
implementation agent and will be read only after the freeze, to run it once per comparison
candidate.

| Item | Value |
|---|---|
| sha256 of `scenarios.json` | `532f39d0c259a654fb6ade459ab346df5fbffc62fa6145dec6b09556ae863338` |
| Location (local, unpublished until after the freeze) | session scratchpad `heldout-v3-sealed/scenarios.json` |
| Author | A separate agent. It read only the runner's input format (`scripts/run_memory_quality_scenarios.py`, lines 1–140). It saw no runtime code, tests, fixtures, reports or earlier cohorts, and it did not run the runtime. |
| Population | 60 scenarios, 250 queries |
| Query kinds | single (exactly one must_include) 202; multi 17; abstention 31 |

**Categories** (scenarios / queries):

| Category | Scenarios | Queries |
|---|---|---|
| correction | 8 | 34 |
| currentness | 7 | 28 |
| entity_redundancy | 8 | 32 |
| multi_evidence | 7 | 28 |
| distractor_heavy | 8 | 32 |
| abstention | 7 | 30 |
| forgetting_and_scope | 7 | 34 |
| imperfect_query | 8 | 32 |

**Evaluator and scoring rules**
- The evaluator is `scripts/run_memory_quality_scenarios.py` at the frozen C4 SHA. The same file is used for every system.
- Each memory store is isolated, and operations go through `AgentMemory.open(root, scope=…)`. Every query calls `recall(query, budget=10)` with the default return selection.
- A query passes when all `must_include` refs are returned, no `must_exclude` ref is returned, and every returned ref is in `must_include` ∪ `may_include`.
- Precision = allowed returned refs / returned refs. Recall = returned must_include refs / must_include refs.

**Safety gates**
- A safety violation is any returned `must_exclude` ref with reason forgotten, superseded or other_scope.
- Any violation fails the candidate, whatever its strict score.

**Note from the author:** `superseded` is never used as a reason. A corrected memory keeps its ref, so the runner cannot tell its old text from its new one. Older statements in currentness scenarios are `may_include`.

**Protocol after the freeze**
- Verify this hash.
- Run A `1df28f84`, C2 `eaf60e4d`, C3 `6a2255c0` and C4 once each with the same runner file.
- Report strict pass, precision, recall and safety; paired improvements and regressions by category; exact McNemar; and bootstrap 95% intervals.
- Commit the raw results and the cohort itself.
