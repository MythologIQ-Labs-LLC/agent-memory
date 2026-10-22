# #819 served-context quality: opt-in `evidence_qualified` consumer profile

**Implementation SHA: `87a957a535b72b6af40444a183ff1105c201779f`** (selector blob `8d261817`, policy
`evidence-qualified-context-selection/0.4.1`, package `agent-memory-context/0.2.0`), branch
`development/819-served-context-quality-controls-no-ci`, draft PR #841, base = the independently
qualified #839/#840 composed preview `a76e6465`. Every commit is `[skip ci]`; no GitHub Actions,
merge, publication, baseline declaration or accepted-fixture change. Frozen v7 (#836), the published
v6 register, the #839/#840 review heads and the combined-preview record are untouched.

**Verdict: CHANGES REQUIRED for the #819 precision objective; READY FOR INDEPENDENT REVIEW as an
opt-in, experimental, inspectable delivery profile that loses no governed evidence.** Section 7.

This is an execution record. `docs/ARCHITECTURE_INDEX.md` routes ownership; `docs/44` owns the API;
accepted lanes and the baseline register are untouched. Nothing here is lane evidence or a holdout
claim.

## 1. What was built

`AgentMemory.recall_context(..., consumer_profile="evidence_qualified")` runs a versioned
post-admission selector (`reference/agentmem_ref/api/context_selection.py`) over the facts the
governed recall already returned:

- `recall()`, admission, ranking and the `returned` prefix are unchanged; the default profile
  (`all_returned`) still produces package `0.1.0` byte-compatibly (tested).
- A declined fact stays in `items` as `omitted_selection` with a reason token, spends no budget,
  and is counted (never quoted) in the `memory.context_delivery` receipt.
- Delivered facts carry `evidence` and `certainty` (`grounded` / `uncertain`); the package's
  `selection.assessment` tells `evidence_delivered` / `undetermined` / `no_relevant_evidence` /
  `no_returned_candidates` apart.
- Grounded declines (only two): `no_query_term_evidence` for a **single-statement** fact that shares
  no folded content term with the question; `subject_mismatch` when the question names a subject by
  a proper-noun possessive (or is first person) and a **non-first-person** fact grounds a different
  subject by possessive or persisted write-time proposition. Exact-identity, corroborated-route and
  historical admissions are always delivered. Everything else is delivered and labelled uncertain:
  multi-sentence texts without a shared term, same-subject facts whose predicate is phrased
  differently, ungrounded subjects, questions without content terms.
- Morphology fold (possessive, plural, `-ing`/`-ed`, final `-e`) and a bounded function-word list;
  no learned model, no corpus or benchmark vocabulary, no gold, no question ids.

Files: `api/context_selection.py` (new), `api/context_package.py`, `api/surface.py`,
`schemas/api-context-package.schema.json`, `scripts/restructure_package.py`, alias
`agentmem_ref/context_selection.py`, `scripts/demo_served_context_workflow.py`, tests
`test_819_served_context_quality_contract.py` (owner), `test_819_evidence_qualified_selection.py`
(mechanism, 25 tests), `test_841_independent_product_quality_challenges.py` (owner review controls,
4), one assertion re-pointed in `test_691_authorization_privacy_challenge.py`.

## 2. Step 1: fail-first and test review (`step1/`)

Owner controls blob `e8c2e9aa` at `706971c8`: RED 7/7 (keyword refused). Default-profile variant:
5 pass, 2 behavioural failures (wrong subject/object delivered; distractors served on an
unanswerable question). Review in `step1/TEST_REVIEW.md`: all seven defensible; one correction
later directed by the owner's review (section 4). Mechanism tests cannot import at the base
(`step1/mechanism-tests-red-706971c8.log`).

## 3. Policy history, every step disclosed (`diagnostics/`)

| policy | head | what changed | why | result |
|---|---|---|---|---|
| 0.1.0 | `0fc1cde9` | initial selector | | runs stopped **unread** when the demo exposed a first-person gap; not evidence |
| 0.2.0 | `32431e6d` | first-person queries anchor the speaker | workflow demo | AMB strict **30/77**, but LongMemEval session **31/428** questions lose required evidence, LoCoMo **9/1531** (`diagnostics/policy-0.2.0/LOSS_ANALYSIS.md`) |
| 0.3.0 | `4a9940b3` | term/attribute absence grounded only for single-statement facts; proper-noun possessives | loss analysis of 0.2.0 (regression sets, read) | LongMemEval session 1 loss (`08f4fc43`), LoCoMo 0; AMB back to 15/77 |
| 0.3.1 | `5e428c73` | a first-person fact is never a subject mismatch | that one loss | session 0 loss; superseded before the turn plane finished |
| 0.4.0 | `f8556a79` | attribute absence is uncertainty; uninspected facts make the assessment `undetermined` | owner review (PR #841 comment 6350329872), 4 controls RED 4/4 at `5e428c73` (`review-841/`) | session 0 loss, **turn 3 losses** (`diagnostics/policy-0.4.0/NOTE.md`) |
| 0.4.1 | `87a957a5` | contracted first-person markers (`I'm`, `I've`) recognised | the three turn losses were a tokeniser bug | **zero loss on every set** (section 5) |

LoCoMo was loaded for the first time at 0.2.0 as a frozen-before-exposure check; once its losses
were read and used, it became regression evidence. LongMemEval was regression evidence from the
start (owner brief). The 446 AMB-excluded LoCoMo adversarial (category 5) questions were first
loaded after 0.3.0 froze and were never used to change the selector.

## 4. Owner review (PR #841 comment 6350329872)

Both findings confirmed from source and execution and fixed in 0.4.0; the four controls pass from
the source tree and the installed wheel. The owner's control 1 had asserted that
`Liora's bicycle is black.` is declined for `What color is Liora's canoe?`; that is the same
structure as the review's cello counterexample, so it was corrected (correct fact delivered as
grounded evidence and ranked first, wrong subject declined, other delivered facts labelled
uncertain), documented in `step1/TEST_REVIEW.md`; the original stays at blob `e8c2e9aa`.

## 5. Paired results at the implementation SHA (`results/`, tools in `tools/`)

Arms on one governed store and one recall per question: **default** (`all_returned`, equals raw
`recall()`); **lexical** = the rejected `bc98e965` rule replayed post hoc (diagnosis only);
**eq** = `evidence_qualified`; **FTS5** = in-memory SQLite FTS5 (unicode61, bm25) over the same
texts. Raw-recall invariance across the arms is asserted on every question. Gold is joined after
retrieval. Denominators are this driver's (every question with at least one gold item), not the
accepted lane's.

### 5.1 Required-evidence gate (the blocking criterion): zero loss

| set | default complete | eq complete | required items default → eq | lexical lost | FTS5 lost |
|---|---|---|---|---|---|
| LongMemEval_S session, 500 q, k=50 | 428/428 | **428/428** | 803/803 → 803/803 | 1 (`2e6d26dc`) | 27 |
| LongMemEval_S turn, 500 q, k=50 | 369/428 | **369/428** | 756/842 → 756/842 | 2 (`2e6d26dc`, `830ce83f`) | 19 |
| LoCoMo, 1,540 q, k=10 | 1278/1531 | **1278/1531** | 1734/2102 → 1734/2102 | 1 | 56 |
| AMB 77 (native scorer) | recall .9535 | **.9535** | | 0 | 0 |
| 19k synthetic (#825 harness) | 11/11 | **11/11** | | 0 | 0 |

The rejected lexical rule reproduces exactly the owner's recorded losses; FTS5 loses far more at the
same budget.

### 5.2 Burden, precision, strict success

| set | metric | default | lexical (rejected) | eq 0.4.1 | FTS5 |
|---|---|---:|---:|---:|---:|
| LongMemEval session | delivered items | 19,187 | 16,268 | **18,399** (−4.1%) | 8,891 |
| | micro precision | .04185 | .04930 | **.04364** | .08638 |
| LongMemEval turn | delivered items | 21,400 | 18,784 | **19,319** (−9.7%) | 13,819 |
| | micro precision | .03533 | .04014 | **.03913** | .05333 |
| LoCoMo | delivered / micro precision | 15,310 / .1133 | 15,264 / .1135 | **15,310 / .1133** | 15,269 / .1134 |
| AMB 77 | strict / mean precision / items | 15 / .1806 / 686 | 22 / .3243 / 236 | **15 / .1806 / 686** | 19 / .2903 / 254 |
| 19k synthetic (13 primary) | strict / extras / forbidden | 0 / 52 / 2 | 4 / 21 / 2 | **4 / 21 / 2** | 1 / 42 / 2 |
| 1k synthetic | strict / extras | 0 / 52 | 4 / 21 | **4 / 21** | 1 / 42 |

Where the gain comes from: on LongMemEval the selector declines 880 (session) / 2,267 (turn)
single-sentence texts with no shared content term and 54 / 64 grounded subject mismatches; every
multi-sentence text without a shared term (13,470 / 11,683) is delivered as
`undetermined_multi_statement`. On AMB every belief is 2 to 3 sentences, so nothing is declined.
On the 19k synthetic corpus (single-sentence facts) the selector matches the rejected rule's
strict result without the rejected rule's losses.

### 5.3 No-answer calibration

| set | no-answer questions | default empty | eq empty | eq assessment |
|---|---:|---:|---:|---|
| LongMemEval session (abstention + no-user-target) | 72 | 0 | 0 | items 3,344 → 3,197 |
| LongMemEval turn | 72 | 0 | 0 | items 3,600 → 3,347 |
| LoCoMo (no gold session) | 9 | 0 | 0 | |
| LoCoMo adversarial category 5 (unseen, 446 q) | 446 | 0 | 0 | 446 `evidence_delivered`, 159 items uncertain, 0 declined |
| 19k synthetic | 2 | 0 | 0 | the poisoned email is delivered, labelled untrusted |
| owner control 3 (single-sentence distractors) | 1 | served | **empty**, `no_relevant_evidence` | |

Abstention improves only where memories are single statements. On conversation-sized documents the
selector cannot ground absence and says so (`undetermined` / uncertain), which is the owner's
stated requirement; it does not improve no-answer behaviour there.

### 5.4 Cost (P3; shared 4-vCPU container, concurrent runs, descriptive only)

| | default context p50 / p95 | eq context p50 / p95 | FTS5 search p50 |
|---|---|---|---|
| LongMemEval session (≈45 items, ≈260 words each) | 35.1 / 52.7 ms | 57.6 / 92.2 ms | 0.5 ms |
| LongMemEval turn (50 items) | 56.6 / 102.1 ms | 66.9 / 119.5 ms | 0.6 ms |
| AMB (≈9 items) | 15.7 ms | 17.3 ms | |
| 19k synthetic, k=5 | 595 / 4,526 ms | 568 / 3,142 ms | 0.17 / 5.9 ms |

Ingest: Agent Memory 152 s for 19,014 governed writes vs 90 ms for the FTS5 build; LongMemEval
session ingest p50 434 ms per question. The selector adds roughly 10 to 25 ms per package on 45 to
50 long items (term folding over the full texts). The governed store's cost is the lineage's, not
the selector's.

## 6. Regression evidence at the implementation tree (`logs/`, `replays/`, `install/`, `demo/`)

- Full reference suite from the repo root: **3,268 passed, 4 failed, 27 skipped, 1 xfail**, 2,191
  subtests; the four are the by-design v7 identity guards for any successor tree
  (`test_644_v7_gauntlet_identity`, two `test_770_v7_lane_freeze_independent` freshness guards,
  `test_benchmark_integration_contract::test_evaluation_only_change_keeps_runtime_baseline_equivalence`).
- 13 replay families all PASS, `observations_sha256` identical to the `2ad4cf23` v7 record (13/13
  SAME); `verify_786` / `verify_644 --reexecute` exit 0; #821 crash matrix outcome-identical to the
  `07cd8692` record after volatile keys.
- `check_runtime_baseline_equivalence --candidate HEAD` exits 1 by design (undeclared successor
  files; `logs/checker.txt`).
- Validators: schemas, fixtures, architecture index, doctrine boundaries, wiki links; package layout
  table matches; `restructure_package.py --check` clean.
- Wheel and sdist built from `git archive HEAD`; in a fresh venv with `python -I` outside the
  checkout: both #819 modules and the owner's #841 controls pass (36), the workflow demo passes
  58/58 (`install/`).
- `scripts/demo_served_context_workflow.py`: ingest → ask → inspect evidence and provenance →
  correct → forget → restart → ask again → other project reads nothing; raw recall compared with the
  default and qualified packages on every question (`demo/`). It also records a known limitation
  without asserting it: "garage door code" delivers the "VS Code" memory on the shared term `code`.

## 7. Verdict and what remains

**CHANGES REQUIRED against the #819 objective** ("fix broad irrelevant recall" on AMB: 60/62
failures with unexpected beliefs). On AMB and on conversation-sized memories the 0.4.1 selector
declines nothing, so the measured 15/77 and the LongMemEval no-answer deficit are unchanged. The
only policy that moved AMB (0.2.0, 30/77) lost required LongMemEval and LoCoMo evidence and is
rejected by the owner's gate. The data in `diagnostics/policy-0.2.0/LOSS_ANALYSIS.md` show why no
lexical absence rule above one sentence survives that gate: lost gold turns (2 to 4 sentences) sit
in the same size class as AMB beliefs.

**READY FOR INDEPENDENT REVIEW as an opt-in experimental profile**: zero loss of governed evidence
on every set; 4 to 10% fewer delivered items on LongMemEval with precision up; strict 0 → 4/13 and
extras 52 → 21 on the 19k synthetic facts at the FTS5 comparator's 1/13; every decline inspectable
and versioned; uncertainty reported rather than suppressed; raw `recall()`, admission, ranking,
lifecycle, scope and audit unchanged; replays and crash matrix identical.

Not done, candidly:
- No owner-controlled sealed holdout exists. LoCoMo and LongMemEval are both exposed; the
  adversarial category-5 set is unseen but adds no discrimination at 0.4.1.
- The selector is lexical. Paraphrase and implicit relations are delivered as uncertain, never
  resolved; a word with another sense is evidence (`code`).
- Per-statement span selection (owner's suggested next direction) was not attempted: it needs an
  authorised span contract and audit binding of partial text, which is a package-schema decision.
- Windows not executed. Latency is descriptive.
- Owner decisions pending: whether an opt-in profile that is loss-free but precision-neutral on
  document-sized memories is worth carrying into the successor; package version `0.2.0` for the
  selective package; whether control 1's corrected reading stands.
