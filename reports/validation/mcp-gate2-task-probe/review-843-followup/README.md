# Review 5628673295 follow-up: controls executed, generalization, answer and evidence scoring

**Gate 2 is not passed and is not claimed.** This directory adds independent execution of the owner's
seven review controls, generalization probes with fresh vocabulary, one shared full-evidence contract,
strict answer measures, a disjoint task cohort, the PR integration path, and the evidence the 0.5.1
section of `../README.md` left as `TBD`. Every earlier receipt in `../` is unchanged; new outputs are new
files.

| item | value |
|---|---|
| reviewed head | `c461ddaa378e4e8a3be3786094e5c573babd594c` (selector blob `e186d895`, `task_eval.py` blob `f706088c`) |
| current candidate before this follow-up | `993ba1c4ab5b8e253eb6cad1e2fdce46709ba238` (selector 0.5.1, blob `57bfb3fc`) |
| this follow-up's code commit | `db81778c924ea6449938d211c996002056c67380` (evaluation harness only; selector, runtime, schema unchanged) |
| merged with the implementation session's evidence | `31c223d6` merges `80b52786` (0.5.1 lanes `7e088e36`, full suite at `993ba1c4`); nothing outside `reports/` differs from `db81778c`, so every result taken at `db81778c` holds for the merged head |
| review controls | branch `review/819-gate2-selection-and-answer-judge-adversarial-no-ci` at `1945848ef0b5a538123d32801819333dcb4ea76f`, test file blob `508fc96f` (byte-identical to the copy committed on this branch) |
| environment | CPython 3.12.3, Linux x86_64, isolated venv (`venv-freeze.txt`: `mcp` 2.3.0, `mcp-types` 2.3.0, `pydantic` 2.14.1, `anyio` 4.15.1, `onnxruntime` 1.31.0, `tokenizers` 0.23.3, `numpy` 2.5.4); `agentmem_ref` imported only from the tree under test (identity files record the import path) |
| reader | `Xenova/distilbert-base-cased-distilled-squad` quantized ONNX, re-downloaded; all four files byte-identical to `../phase5/reader-model-SHA256SUMS.txt` (`harness/reader-model-SHA256SUMS-verified.txt`) |

## 1. The seven review controls, executed (actual RED/GREEN)

The review file was taken from the review branch, not from this branch, and run against each exact head
from a clean checkout (`controls/`).

| control | `c461ddaa` (reviewed) | `993ba1c4` | `db81778c` |
|---|---|---|---|
| `test_named_third_person_fact_has_implicit_landing_answer` | **RED** | GREEN | GREEN |
| `test_named_third_person_fact_has_implicit_heating_answer` | **RED** | GREEN | GREEN |
| `test_unavailable_is_not_a_negative_evidence_verdict` | GREEN | GREEN | GREEN |
| `test_explicit_negation_cannot_be_scored_correct` | **RED** | GREEN | GREEN |
| `test_gold_word_inside_another_word_cannot_be_scored_correct` | **RED** | GREEN | GREEN |
| `test_missing_answer_is_not_correct_on_answerable_task` | GREEN | GREEN | GREEN |
| `test_truncated_returned_key_does_not_count_as_complete_evidence` | **RED** | GREEN | GREEN |
| **total** | **5 RED / 2 GREEN** | 7/7 GREEN | 7/7 GREEN |

This independently reproduces the counts the `32dbc837` commit message states.

## 2. Do the repairs generalize? (`integrations/agent-memory-mcp/tests/test_gate2_review_generalization.py`)

Fresh vocabulary that appears in no review test, fixture or cohort. At `993ba1c4`: 7 failures, 7 errors
(`generalization/generalization-at-993ba1c4-RED.log`). At `db81778c`: 13 OK, 2 expected failures.

1. **Paraphrase exclusion: fixed for longer facts; still present for one sentence, and kept RED on purpose.**
   Selector 0.5.1 still declines a *single statement* that shares no content term with the query, as
   `no_query_term_evidence` with `certainty: grounded`. Three fresh one-sentence paraphrases are declined
   (`Who repaired the bicycle?` / `Mechanic Oren fixed Tamsin's bike.`; first person
   `Where is my automobile parked?` / `I left the car in bay nine.`; no names
   `What time does the ferry depart?` / `Boats to the island leave at noon.`). That is the same lexical
   mismatch the review identified, for one sentence instead of several. The rule dates from 0.3.0.
   On the disjoint cohort (section 4) it removes real answers.

   It is **not** withdrawn on this PR. Withdrawing it makes the owner's control
   `test_819_served_context_quality_contract::test_no_safe_answer_does_not_serve_distractors_as_an_answer`
   fail, because that control's two distractors share only "the" with the question, and it must not be
   weakened. Both requirements hold together only if function-word-only candidates are never admitted.
   That is the bounded runtime candidate on branch `experiment/819-content-term-lexical-admission-no-ci`
   (selector 0.5.2 plus content-term admission), where the owner's control passes and these probes turn
   GREEN. The two probes are therefore `expectedFailure` with the reason in the file. They fail the suite
   as unexpected successes the day the rule changes without this record being updated.
2. **Answer scoring: the phrase proxy is kept and labelled, and a standard strict measure is added.**
   `judge()` now also reports SQuAD 1.1 normalised `exact_match` and `token_f1` against the gold
   aliases, and `aggregate()` reports `answerable_exact_match` and `answerable_mean_token_f1` next to
   `answerable_gold_phrase_match`. A hedge (`Vesper Strip or Halden Field`), a wrong answer that mentions
   the gold (`Halden Field, after leaving Vesper Strip`) or a negated mention is never an exact match.
   Exact match is a lower bound: `by a propane burner` is not credited for `propane`. The proxy is an
   upper bound. Neither is a verified judgement of correctness.
3. **Truncated evidence: one contract, and no default that can be forgotten.** The review's defect existed
   because `quality_probe.score()` defaulted `fully_delivered_keys=None` to "every returned key is
   complete", and each harness had its own copy of the filter. Now:
   - `quality_probe.fully_delivered_keys(evidence, seeded)` is the one contract (resolved, attributed,
     whole seeded text);
   - both harnesses call it;
   - `score()` has no default, so a caller must state what was fully delivered. The FTS5 arms pass their
     returned keys explicitly; FTS5 returns whole texts.

## 3. Re-measured at `db81778c` (`harness/`; the `993ba1c4` receipts reproduce exactly)

Reader answers on the post-freeze cohort are identical to the `993ba1c4` receipts, row by row, for both
profiles, and the dev cohort reproduces 47 / 40 / 22. The new columns change the reading:

| post-freeze cohort, ONNX reader, 16 answerable / 6 no-answer | gold-phrase proxy | **SQuAD exact match** | token F1 | no-answer abstained / false answer | required complete | unexpected items |
|---|---|---|---|---|---|---|
| MCP default `all_returned` | 15 | **10** | 0.812 | 0 / 6 | 16/16 | 83 |
| MCP opt-in 0.5.1 | 14 | **10** | 0.771 | 0 / 6 | 16/16 | 59 |
| SQLite FTS5 | 14 | **10** | 0.771 | 0 / 6 | 16/16 | 45 |

The 15-versus-14 advantage reported for the default exists only under the proxy. Under exact match the
three arms tie at 10/16. Token F1 keeps a small default edge (the T16 propane/paraffin case). The
deterministic extractive reader returns whole sentences (exact match 0 by construction) and is plumbing
only.

## 4. Disjoint task cohort (`disjoint/`): opt-in 0.5.1 loses required evidence

`disjoint/task_cases_disjoint.json` (sha256 `03b1bb06…`, committed on the experiment branch before any
arm ran on it) has 24 fictional records and 26 questions, written by category: direct, morphological
variant, paraphrase sharing only a function word, paraphrase sharing no token, first person, and
no-answer with function-word or content-word distractors. It is disjoint from both earlier cohorts. It
is **not** a sealed holdout: the author also wrote the admission rule.

| PR head `db81778c`, ONNX reader, 18 answerable / 8 no-answer | required complete | phrase proxy | exact match | token F1 | no-answer abstained | unexpected items |
|---|---|---|---|---|---|---|
| MCP default `all_returned` | **17/18** | 15 | 9 | 0.715 | 1/8 | 96 |
| MCP opt-in 0.5.1 | **15/18** | 13 | 8 | 0.622 | 2/8 | 41 |
| SQLite FTS5 | 15/18 | 13 | 8 | 0.637 | 2/8 | 26 |

D14 `Who fixed the bicycle?` (`Mechanic Ivo trued the rear wheel of the tandem.`) and D15
`Which pharmacy is open after midnight?` (`The nearest late-night chemist is on Dunmore Street.`) are
single statements sharing only "the"/"is". The default delivers them and the reader answers both
(`Mechanic Ivo`, `Dunmore Street`). **Opt-in 0.5.1 declines both as grounded single-statement absence
and both answers are lost.** The "zero loss on every regression set" property does not carry to a fresh
cohort. D7 (`Which language am I studying?` / `I'm learning Portuguese…`) shares no token and no arm
retrieves it.

## 5. 0.5.1 regression lanes and full suite (the `TBD` entries of `../README.md` section 9.2)

Re-executed at `db81778c` (selector 0.5.1, blob `57bfb3fc`, identical to `993ba1c4`). The drivers are
the #819 paired drivers committed in `reports/validation/819-evidence-qualified-context/tools/`, unmodified,
with the same inputs: LongMemEval_S cleaned (sha256 `d6f21ea9…`, equal to the earlier lanes' recorded
`input_sha256`); LoCoMo from the AMB export pinned in `amb-competitive.yml` (`03c1d0f1`), with all three
`data_sha256` equal to the earlier run. Outputs and identities are in `lanes/`, and the runner is
`lanes/run_lane.sh`.

| set | arm | complete | required items | delivered items | questions losing required evidence vs default |
|---|---|---|---|---|---|
| LongMemEval_S session (500 q, k=50) | default `all_returned` | 428/428 | 803/803 | 19,187 | - |
| LongMemEval_S session (500 q, k=50) | opt-in 0.5.1 | 428/428 | 803/803 | 18,390 | **0** |
| LongMemEval_S session (500 q, k=50) | SQLite FTS5 | 401/428 | 768/803 | 8,891 | 27 |
| LongMemEval_S turn (500 q, k=50) | default `all_returned` | 369/428 | 756/842 | 21,400 | - |
| LongMemEval_S turn (500 q, k=50) | opt-in 0.5.1 | 369/428 | 756/842 | 19,316 | **0** |
| LongMemEval_S turn (500 q, k=50) | SQLite FTS5 | 362/428 | 737/842 | 13,819 | 19 |
| LoCoMo (1,540 q, k=10) | default `all_returned` | 1278/1531 | 1734/2102 | 15,310 | - |
| LoCoMo (1,540 q, k=10) | opt-in 0.5.1 | 1278/1531 | 1734/2102 | 15,310 | **0** |
| LoCoMo (1,540 q, k=10) | SQLite FTS5 | 1273/1531 | 1732/2102 | 15,269 | 56 |

These match, item for item, the 0.5.1 lanes the implementation session ran independently at `32dbc837`
(`../lanes-0.5.1/`, commit `7e088e36`, `../README.md` section 9.2). That session also ran AMB 77
(strict 15, 0 regressed) and the synthetic sets, which this container could not reproduce (see below).
The two runs used different machines, venvs and sessions. The default arm reproduces the earlier lanes
exactly (19,187 / 21,400 / 15,310 delivered). 0.5.1 loses
nothing on these sets. Its single-statement rule fires on few items there, because LongMemEval and LoCoMo
store multi-sentence first-person conversation. The loss appears on short third-person notes (section 4),
which is what an agent writes through `memory_remember`.

**Not re-executed here:**
- **AMB 77:** needs the PrecisionMemBench fixture workspace, which is not in this container.
- **LoCoMo adversarial:** needs the raw snap-research `locomo10.json`.
- **The #825 synthetic sets at 0.5.1:** these were run on the experiment branch with the flag off. Their
  default arm is the same code, but their opt-in arm is 0.5.2 there.

Full reference suite at `db81778c` (selector blob `57bfb3fc`, identical to `993ba1c4`), run with the
venv first on `PATH`: **3263 passed, 35 skipped, 1 xfailed, 4 failed**
(`suite/full-suite-db81778c.log`). The four are the by-design v7 identity guards listed in `../README.md`.
A first run with the system Python first on `PATH` also failed
`test_gauntlet_durability::…qualifies_first_durability_slice` (`adapter_error`: its subprocess adapter ran
a Python without the package's dependencies). It passes 4/4 at both `993ba1c4` and `db81778c` once the
venv is first on `PATH` (`suite/durability-PATH-confound.txt`). This is an environment effect, not a
regression.

MCP integration suites at `db81778c`: 55 OK, 2 expected failures (`mcp-suites-at-db81778c.log`).
Selector, owner-control, challenge, package and audit suites: 95 passed
(`selector-suites-at-db81778c.log`).

Note on the lane runs: the two LongMemEval *turn* runs on the experiment branch lost only their final
`rc=` identity line, because `run_lane.sh` was edited while they ran and bash re-read it. Their 500 rows
and `summary.json` are complete. No PR-head lane was affected.

## 6. Integration path

PR #843 targeted `main` (1,393 files, 294 commits). Its real dependency is #842
(`product/mcp-minimum-memory-loop-no-ci` at `5584fd27`), itself stacked on #841
(`development/819-served-context-quality-controls-no-ci`), which targets
`integration/post-v7-839-840-combined-preview-no-ci`. #843 was retargeted to #842's branch before any push
from this follow-up. It now shows 80 files and 14 commits (`mergeable_state: clean`). No workflow was
started by the retarget. No workflow file uses `pull_request_target`, `types:` or `edited`, and the check
runs on the head were unchanged afterwards. The two evidence pushes the implementation session made after
the retarget (`7e088e36`, `80b52786`) produced **0** check runs. CodeQL default setup had analysed every push to #843 while
it targeted `main`, despite `[skip ci]` (4 Analyze jobs per push). #842, which targets a non-default
branch, has 0 check runs. So the retarget also stops those runs. Merge order, when the owner decides:
#841 → #842 → #843. Nothing is merged here.

## 7. Recommendation for this PR

Keep 0.5.1 opt-in. Do **not** promote it to the `memory_find` default (owner option B): section 4 shows
it removes real answers on a fresh cohort. Do **not** adopt owner option A (ground every third-person
absence): it extends the rule that section 4 shows is unsound. The default `all_returned` profile and
frozen v7 behaviour are unchanged by this follow-up.

## 8. Bounded runtime candidate (separate branch, not part of this PR)

Branch `experiment/819-content-term-lexical-admission-no-ci`, head `557f2157`, evidence in its
`reports/validation/mcp-gate2-task-probe/admission-experiment/README.md`. It contains content-term
lexical admission behind a default-off flag, plus selector 0.5.2.
- **Flag off:** the default is reproduced byte for byte.
- **Flag on, irrelevant context:** it matches indexed FTS5 (dev 27 / FTS5 22; post-freeze 43 / 45;
  disjoint 25 / 26; LongMemEval session 6,586 / 8,891 delivered items).
- **Flag on, required evidence:** it loses evidence the default reaches only through shared function
  words: 22 LongMemEval session questions, 11 turn questions (27 gained), and 2 of 18 on the disjoint
  cohort. It also changes frozen temporal-currentness gauntlet case A3.
- **Flag on, abstention:** it does not produce abstention.

**NO-GO as a default.** It is the only tested combination that satisfies both the review's principle
and the owner's no-safe-answer control, and it shows what a default change still needs: a non-lexical
paraphrase route, a calibrated no-answer signal, a decision on A3, and a baseline successor.
