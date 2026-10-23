# Bounded runtime candidate: content-term lexical admission (#819 Gate 2, experiment only)

**Verdict: NO-GO as a default. Keep it as a flag-gated research candidate.** Not for merge, not a
Runtime Baseline successor, no baseline declaration, no accepted fixture or register touched. Gate 2 is
not claimed.

| item | value |
|---|---|
| branch | `experiment/819-content-term-lexical-admission-no-ci` (isolated; base: PR #843 remediation commit `db81778c`) |
| E1 `25cabcd0` | `core/content_terms.py` (the selector's bounded function-word list and morphology fold, moved verbatim and re-exported by `api/context_selection`, which is behaviourally unchanged); `runtime/adapter.eligible_search` (the single function every lexical route goes through) keeps a candidate only if it shares a content term with the query, **only when** `AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION=content_term`; MCP harnesses forward and record the flag |
| E2 `c115b958` | selector **0.5.2**: lexical absence is never a grounded decline, single statements included (`undetermined_single_statement`); a conflict of named subjects stays a decline |
| cohort `815cbd26` | `task_cases_disjoint.json` (sha256 `03b1bb06…`), committed **before** any arm ran on it |
| `c0bb7d40` | test-only fix (an admission test leaked an unset flag into later tests in a flag-on full suite) |
| arms ran at | `815cbd26` (`arms/identity-*.txt`; `c0bb7d40` changes one test file only) |
| lanes ran at | `815cbd26` (experiment) and `db81778c` (PR head, in the PR's `review-843-followup/lanes/`) |
| suites ran at | `c0bb7d40` (`suites/`) |
| environment | CPython 3.12.3, Linux x86_64, `venv-freeze.txt`; same pinned ONNX reader as the PR (hash-verified) |

## Why this candidate

The Gate 2 diagnosis at `1943c57f` found that every irrelevant item on the dev cohort comes from the
lexical route admitting a fact on a shared function word ("the", "is"). The review asked for that
admission to be investigated behind a flag. The PR follow-up then found that the selector's
single-statement absence rule, kept since 0.3.0, also discards one-sentence paraphrases. The owner's
no-safe-answer control can only hold without that rule if function-word-only candidates are never
admitted. The first version of the rule used the substrate's exact tokens and lost
`I graduated with a degree…` for `What degrees did my friends graduate with?`. Today such a fact is
admitted only through "with". So admission uses the selector's morphology fold, one definition for both.

## Results (flag OFF = existing default, byte for byte; flag ON = candidate)

**Default unchanged when the flag is off.** On all 500 questions of both LongMemEval planes, the
default arm returned the same ids at the experiment head with the flag off as at the PR head. Dev, task
and LoCoMo default-arm totals are also identical.

### Development and task cohorts (real stdio MCP server, k=5; `arms/`)

| cohort | arm | required complete | unexpected items | no-answer empty / abstained | phrase / **exact match** / F1 (ONNX) |
|---|---|---|---|---|---|
| dev (11 + 3) | default | 11/11 | 47 | 0/3 | n/a |
| dev | **default, flag ON** | 11/11 | **27** | 1/3 | n/a |
| dev | opt-in 0.5.2, flag ON | 11/11 | 26 | 1/3 | n/a |
| dev | SQLite FTS5 | 11/11 | 22 | 1/3 | n/a |
| post-freeze (16 + 6) | default | 16/16 | 83 | 0/6 | 15 / **10** / 0.812 |
| post-freeze | **default, flag ON** | 16/16 | **43** | 0/6 | 15 / **10** / 0.812 |
| post-freeze | SQLite FTS5 | 16/16 | 45 | 0/6 | 14 / **10** / 0.771 |
| disjoint (18 + 8) | default | **17/18** | 96 | 1/8 | 15 / **9** / 0.715 |
| disjoint | opt-in 0.5.1 (PR head) | 15/18 | 41 | 2/8 | 13 / 8 / 0.622 |
| disjoint | opt-in 0.5.2, flag off | 17/18 | 80 | 2/8 | 15 / 9 / 0.715 |
| disjoint | **default, flag ON** | **15/18** | **25** | 2/8 | 13 / **8** / 0.622 |
| disjoint | SQLite FTS5 | 15/18 | 26 | 2/8 | 13 / 8 / 0.637 |

On the disjoint cohort the flag loses D14 (`Who fixed the bicycle?` / `Mechanic Ivo trued the rear wheel
of the tandem.`) and D15 (`Which pharmacy is open after midnight?` / `The nearest late-night chemist is
on Dunmore Street.`). Both are paraphrases that share only "the"/"is". The default answers both
correctly. FTS5 loses the same two.

### Regression lanes (`lanes/TABLES.md`; drivers unmodified from `819-evidence-qualified-context/tools/`)

| set | default (flag off) | **default, flag ON** | FTS5 |
|---|---|---|---|
| LongMemEval_S session, 500 q, k=50: complete / required / delivered | 428/428 / 803/803 / 19,187 | **406/428 / 775/803 / 6,586** | 401/428 / 768/803 / 8,891 |
| LongMemEval_S turn, 500 q, k=50 | 369/428 / 756/842 / 21,400 | **382/428 / 780/842 / 11,928** | 362/428 / 737/842 / 13,819 |
| LoCoMo, 1,540 q, k=10 | 1278/1531 / 1734/2102 / 15,310 | **1277/1531 / 1733/2102 / 15,261** | 1273/1531 / 1732/2102 / 15,269 |
| #825 synthetic 1k and 19k (14 cases, k=5): needed / strict / extras | 11/11 / 0 / 52 | **11/11 / 1 / 34** | 11/11 / 1 / 42 |

Per question, flag ON against flag OFF (default arm):
- **LongMemEval session:** 0 questions gain and **22 lose (28 items)**. Every lost item shares no
  content term with its question in the stored user-turn text
  (`lanes/lme-session-lost-items-under-flag.txt`). They are paraphrase and aggregation evidence:
  `How many projects have I led…`, `How many different doctors did I visit?`.
- **LongMemEval turn:** 27 questions gain (+37 items) and **11 lose (13 items)**. Removing the
  function-word candidates frees k=50 slots for real turns.
- **LoCoMo:** one item lost.
- **No-answer abstention:** unchanged on every lane (0/72 LongMemEval, 0/9 LoCoMo). A non-empty
  candidate set always reaches the reader, and the SQuAD 1.1 reader never abstains on non-empty
  context.

For comparison, selector 0.5.1 on the synthetic sets (single-sentence facts) reaches strict 4 / extras 21
(`../README.md` section 9.2). Selector 0.5.2 gives that up without the flag (extras 50) and gets 34 with
it. On single-sentence corpora, part of 0.5.1's precision came from the rule this experiment shows is
unsound.

### Suites (`suites/`)

| suite | result |
|---|---|
| full reference, flag OFF, `c0bb7d40` | 3269 passed, 5 failed: the 4 by-design v7 identity guards, plus the owner's `test_no_safe_answer…` (expected: selector 0.5.2 without content-term admission delivers the two function-word distractors as uncertain) |
| full reference, flag ON, `c0bb7d40` | 3260 passed, 14 failed. 4 v7 guards. **The owner's `test_no_safe_answer…` passes.** 6 selector tests and `test_776…share_admission` whose fixture fact reaches recall only through a shared function word (the security assertions of test_776 still hold). **`test_temporal_currentness_gauntlet::test_live_runtime_is_monotonic_against_frozen_pre_550_baseline`**: frozen gauntlet case A3 expects "The office plants are watered every Monday." to be returned, below the relevant fact, for a query that shares only "the" with it; under the flag it is not admitted. **This changes a frozen gauntlet outcome.** `test_locomo_evidence_benchmark` pins lexical-only micro precision 0.011111; under the flag it is 0.055556. `test_836…two_creator_race` failed under two parallel suites and passes 7/7 alone with the flag on and off (load flake, not the flag) |
| owner controls + #841 challenges + admission tests, flag ON | 18 passed |
| MCP integration suites, flag OFF | 55 OK |

## What this establishes

1. Content-term admission is the mechanism that closes the irrelevant-context gap to indexed FTS5:
   - dev 47 → 27 (FTS5 22);
   - post-freeze 83 → 43 (FTS5 45);
   - disjoint 96 → 25 (FTS5 26);
   - LongMemEval session 19,187 → 6,586 delivered items (FTS5 8,891).

   On the LongMemEval turn plane it also increases required-evidence recall (+13 complete questions).
2. It does not preserve required evidence. It loses one-sentence and conversational paraphrases that
   the default reaches only by accident through shared function words. That is 22 questions on
   LongMemEval session, 11 on turn and 2 of 18 on the disjoint cohort. FTS5 has the same blind spot. The
   owner's zero-loss gate is not met.
3. It does not give abstention. No-answer behaviour is unchanged on every set except where the context
   becomes empty (dev 1/3, disjoint 2/8, the same as FTS5). A no-answer decision needs a calibrated
   no-answer signal, which neither this candidate nor the SQuAD 1.1 reader provides.
4. Task outcomes on the cohorts:
   - post-freeze: equal to the default (exact match 10/16);
   - disjoint: one exact match lower than the default (8 against 9), equal to FTS5.
5. Selector 0.5.2 together with this admission is the only combination tested here that satisfies both
   the review's principle (lexical absence is never a grounded negative) and the owner's no-safe-answer
   control.

## What would be needed before any default change (owner decisions; none taken here)

- A recall route that reaches paraphrases without lexical overlap (the semantic route, today `off`),
  measured on the same lanes, so that tightening lexical admission does not lose them.
- A decision on frozen gauntlet case A3, whose expectation assumes function-word admission.
- A calibrated no-answer signal, or an abstaining reader, evaluated on a sealed cohort written by
  someone who has not seen this code.
- A Runtime Baseline successor declaration covering `runtime/adapter.py`, `core/content_terms.py`, the
  alias, and `api/context_selection.py`.
