# Held-out v4 seal (#819 C5)

This file is committed **before** any C5 runtime change and before the C5 freeze. The implementation agent has not read the cohort. It will be read only after the freeze, to run it once for each comparison label.

| Item | Value |
|---|---|
| sha256 of `scenarios.json` | `fe8dc55f97a41a61a94631a9e702b82073c4433b7fcde4254d9d8ef46100b027` |
| Location (local, unpublished until after the freeze) | session scratchpad `heldout-v4-sealed/scenarios.json` |
| Author | A separate agent. It read only the runner's input format (`scripts/run_memory_quality_scenarios.py` lines 1–140, copied as `RUNNER-INPUT-FORMAT.py`). It saw no runtime code, tests, fixtures, reports, the C5 dev set or earlier cohorts, did not run the runtime, and used no network. |
| Population (author's report) | 60 scenarios, 252 queries: 158 single, 61 multi, 33 abstention. Memories per scenario: 9 to 13. |
| Operations (author's report) | 641 remember, 15 correct and 10 forget. |

**Categories** (author's report; scenarios / queries):

| Category | Scenarios / queries |
|---|---|
| paraphrase | 7 / 28 |
| aggregate_list | 6 / 28 |
| low_overlap_support | 6 / 28 |
| topical_distractor | 7 / 28 |
| abstention | 7 / 28 |
| adversarial_text | 6 / 28 |
| correction_currentness | 7 / 28 |
| forgetting_scope | 7 / 28 |
| ordinary | 7 / 28 |

## Protocol after the freeze

The runner is `scripts/run_memory_quality_scenarios.py` as committed with this seal. The same file is used for every label, with budget 10 and `return_selection` set to each runtime's default.

1. Verify this hash.
2. Run each label in the preregistration once: A, C2, C4, C4+sem, C5 and C5+sem. The `+sem` labels use `--semantic-retrieval required` with the pinned MiniLM model directory, and every label runs under the same interpreter.
3. Report the preregistered measures and acceptance criteria (`PREREGISTRATION-C5.md`).
4. Commit the raw results and the cohort itself.
