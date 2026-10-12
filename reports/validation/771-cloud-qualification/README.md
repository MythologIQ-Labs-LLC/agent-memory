# #771 Independent cloud qualification: served-memory quality

| | |
|---|---|
| Candidate | `evaluation/served-memory-quality-first-no-ci` @ `23321e4bc1d8039ea64f8d135aac080fc98806fa` (SHA verified) |
| Validation branch | `validation/771-served-memory-quality-cloud` (forked from the exact candidate SHA) |
| Final measurement revision | recorded in `measurements-baseline.json` (`runtime_revision`); runtime files identical to the candidate |
| Environment | Claude Code cloud container, Linux, Python 3.13.16, deps from `reference/requirements.txt`, full (unshallowed) clone |
| Verdict | **CHANGES REQUIRED**: evaluator defects (repaired here, need adoption) and measured runtime quality gaps (reproduced here, not patched) |

No GitHub Actions were triggered, no PR was opened, nothing was merged. The frozen v7 declaration and accepted baselines are untouched: `git diff 23321e4 HEAD -- reference/agentmem_ref reports/runtime` is empty, and no protected runtime file changed.

## Verdict

**The measurement could not be defended as delivered.**
- **11 of the 31 authored tests never executed.** The provenance suite overwrites `TestCase.run`.
- **The scorer's P2 averages could reward empty delivery** and mixed unanswerable cases into answerable utility.
- **Recall was not reported at the served budget.**
- **"Correct memory at rank 1" was actually "any grade ≥ 2 memory at rank 1"**, which overstated real top-1 correctness by 19 points on the holdout.
- **The v1 runner can only write**, so corrections, deletions, validity windows and tenants were inexpressible. "Stale" on the authored corpus is therefore a gold annotation the runtime has no way to act on.

All five evaluator defects are repaired here, each with a failing test committed first. I added a lifecycle (v2) runner and measured an independent holdout that was frozen before its first run.

**What the runtime does right:**
- Zero prohibited exposure on every query, on both backends, in every write-order permutation. Deleted, other-project and other-tenant memories (including a tenant reusing the same project name) were never served.
- Superseded values are never served for current questions.
- Declared historical intent admits state-change history but not error-corrected values.

**What it does wrong:**
- It never serves an empty context; every unanswerable question gets a full budget of unrelated memories.
- An elapsed declared validity window is served as current context.
- Historical intent admits the old value but still ranks the current one first.
- Why-questions rank the "what" fact above the "why" fact.
- Long compound questions push required facts past the budget.
- An unconfirmed claim can outrank the recorded fact.
- `governed-lexical` rankings depend on write order.

## Phase 1: reproduction on the exact SHA

| Authored suite | Tests | On `23321e4` |
|---|---|---|
| `tests/test_served_memory_quality.py` | 12 | 12 OK |
| `tests/test_served_memory_provenance.py` | 11 | **0 executed**. `cls.run = {...}` shadows `unittest.TestCase.run`, giving `TypeError: 'dict' object is not callable`. The plan's own discovery command crashes and takes the scorer tests with it (`logs/candidate_tests_served_memory_discovery_crash.log`). With only the attribute renamed, all 11 pass. |
| `reference/tests/test_771_served_memory_integration.py` | 8 | 8 OK |

**Real runs** were made with the plan's CLI on a clean exact-SHA checkout, with a fresh SQLite store per backend (`candidate-23321e4/runs/`):
- Both manifests carry `input_sha256 = 6b99154e…` and their `execution_backend`.
- Returned IDs map back to opaque corpus IDs.
- The other-project `hidden-endpoint` was never served.

**Temporal intent** is forwarded to the composed path and checked, but on the v1 corpus nothing is ever superseded, so intent cannot change any result there.

**Assertion weaknesses:**
- `test_labels_do_not_enter_the_runtime_execution_path` is vacuous: the runner never receives gold.
- The real leakage channel is write IDs placed into proposal `target_reference` and `evidence_refs`. I tested it directly by renaming every ID to a random token over 3 seeds: results are identical on both backends, so **no label leakage**.
- The integration tests assert only P0 = 0 and shape, so they cannot detect a quality regression.

**Broader suite** (validation branch): 2559 reference tests, 1 failure, `test_gauntlet_durability…first_durability_slice` (`adapter_eof`). It also fails on the pre-existing base outside #771 (see the #769 review). Log: `logs/full_reference_suite_validation_branch.log`. Final top-level served-memory suites: all pass, with 6 expected failures (the runtime-gap reproductions).

## Phase 2: evaluator defects (failing tests first, then repair)

| ID | Defect | Effect | Failing test → fix |
|---|---|---|---|
| E1 | Provenance tests shadow `TestCase.run` | 11/31 authored tests never ran | `18d8068` → `47f9a49` |
| E2 | Empty context on an **answerable** case had precision `None`, dropped from the macro mean | Serving nothing scored better than serving the answer plus one distractor (1.0 vs 0.5) | `18d8068` → `47f9a49` (scores 0.0) |
| E3 | No-safe-answer cases averaged into answerable P2 macros | Adding an unanswerable query changed answerable precision and nDCG | `18d8068` → `47f9a49` (`macro_scope=answerable_cases_only`, `no_safe_answer_served_total`) |
| E4 | Recall divided by all safe relevant memories | A perfect budget-2 context over 4 relevant memories scored 0.5 | `18d8068` → `47f9a49` (`relevant_recall_at_budget`) |
| E5 | `top1_relevant` accepts any grade ≥ 2 memory | Supporting evidence ahead of the asked-for memory counted as a correct top-1: Halcyon v1.1 composed 0.810 reported vs **0.619** actual answer-at-rank-1 | `17125c4` → `b2c266c1` (`top1_critical`, `top1_critical_rate`) |

**Held on the candidate, now pinned** (`AdversarialControls`):
- Supporting context at rank 1 is not the answer.
- A forbidden but relevant memory earns no credit and counts as P0.
- Covering 1 of 2 required memories is reported as partial.
- An old value is credit for historical questions and stale for current ones.
- **Empty retrieval is never reported as answer abstention**: `answer_abstention_verified` is always `null` and there is no abstention rate.
- Unlabelled and over-budget output is refused.
- Gold cannot make a stale or forbidden memory critical.
- No composite score.

**Before/after on identical runs** (`scorer-before-after.json`; only the scorer differs):
- P0 and the existing P1 fields are identical.
- P2 changes because unanswerable zeros were removed from answerable utility. Examples:
  - Halcyon v1.1 composed: precision 0.389 → 0.444, nDCG 0.833 → 0.826.
  - v1 composed: precision 0.400 → 0.500.
- E2 did not fire on these runs (no empty answerable context), but the regression shows it is reachable.
- E5 adds a field rather than changing one, and is the largest correction to what the numbers mean.

### Evaluation lane: gaps closed (evaluation code only)

- **`scripts/run_served_memory_lifecycle_scenarios.py`** (schema `served-memory-lifecycle-v2`) replays ordered history through the real governed PAMA path:
  - `retain` (optionally into another project or another tenant on the same substrate, optionally with a declared validity window);
  - `correct` (error correction: the old value was false);
  - `update` (state change: the old value was true until now);
  - `delete`.

  The host adjudication corpus is derived from the declared history only, never from queries or gold. Unscored diagnostics record admitted IDs ranked **beyond** the budget, so "relevant but too late" is observable.
- **The qualifier refuses lifecycle-inconsistent gold.** Deleted and out-of-scope facts must be prohibited for every question; superseded values must be stale for current questions.
- **`TransitionRuleCorpus` holds one rule per (memory, criterion)**, so a value changed twice could not be adjudicated. Fixed with one corpus per transition behind a composite host verifier (`0ee4ed7`).

## Phase 3/4: measured quality

The generated per-query tables for every corpus and backend are in **[`SCORECARD.md`](SCORECARD.md)**, produced from `measurements-baseline.json` with no hand-copied numbers.

**Independent holdout** (`holdout/`, "Halcyon" payments platform), **frozen at `7499007` before its first run**:
- 32 governed events, 24 questions (21 answerable, 3 no-safe-answer).
- Strata: repeatedly changing facts, historical why-questions, multi-fact tasks, an unreliable rumor, an expired declared deploy freeze, a deleted secret, another project, another tenant reusing the project name, lexical traps, paraphrase.

**Disclosed authoring defect.** Holdout v1 encoded six real-world state changes (DB upgrades, on-call transfer, region expansion, ADR supersession, timeout change) as `correct`, which tells the runtime the old values were false. That contradicts v1's own gold for historical questions.
- v1 and its first measurement are kept (`measurements-run1-holdout-v1.json`, and the `halcyon-holdout` rows in the scorecard).
- `halcyon-holdout-v1.1-input.json` changes **only those six `op` fields**; questions, budgets, intents and gold are byte-identical.

### Halcyon v1.1 (answerable n = 21, no-safe-answer n = 3)

| | composed-multiroute | governed-lexical |
|---|---|---|
| **P0** prohibited exposure (cases) | **0** | **0** |
| **P0** stale exposure for the question's intent (cases) | 1 (H09) | 2 (H09, H20) |
| **P1** answer (critical evidence) at rank 1 | **0.619** (13/21) | 0.476 (10/21) |
| P1 strong evidence (grade ≥ 2) at rank 1 | 0.810 | 0.571 |
| **P1** all critical evidence groups served | 0.905 (19/21) | 0.714 (15/21) |
| P1 missing critical evidence (cases) | 2 (H04, H20) | 6 |
| P1 empty context although evidence exists | 0 | 0 |
| P1 no-safe-answer questions given context | 3/3 (9 memories) | 3/3 (9 memories) |
| **P2** precision @budget / recall @budget | 0.444 / 0.905 | 0.357 / 0.738 |
| P2 graded nDCG @budget | 0.826 | 0.656 |
| P2 distractors per answerable question | 1.33 | 1.43 |
| Write-order robustness (queries whose output changed in ≥ 1 of 5 permutations) | 1/24 (H02, 3/5) | 20/24 |

### Case-by-case failures (composed, v1.1)

| Q | What was served (rank order) | Failure | Cause |
|---|---|---|---|
| H01 current PG version | `bus`, `migration-rule`, **`pgver-16`** | Answer only at rank 3 | Lexical overlap on "ledger" and function words; no morphology ("run" ≠ "runs") |
| H02 PG version *before* last upgrade (historical) | `pgver-16`, **`pgver-15`**, `adr-db-v2` | Current value outranks the asked-for history; order-dependent (3/5) | **G6**: historical intent widens admission but does not prefer historical evidence in ranking |
| H04 why we left MySQL (historical) | `bookclub`, `adr-db-v1`, `fx-fetch` | Answer `adr-db-v2` admitted but ranked **past budget**; rank 1 overlaps only on "the" | "ledger's" ≠ "ledger", "move" ≠ "moved"; G1 |
| H09 deploy this Thursday? | **`deploy-days`**, `region-eu-us`, `freeze-bf25` | Expired freeze served as current context (**P0 stale**) | **G2**: by #549 design an elapsed `valid_until` never refuses or demotes |
| H12 why cache FX for an hour | `fx-fetch`, **`fx-why`**, `money-repr` | The "what" fact outranks the "why" fact | No notion of causal/rationale evidence in ranking |
| H14 regions before 2024 (historical) | `region-eu-us`, **`region-eu`**, `region-draft` | Current value ahead of the asked-for history | G6 |
| H17 / H18 / H19 (no safe answer) | full budgets of `oncall-lrt`, `bookclub`, `room`, `ratelimit`… | Context served where nothing safe exists (deleted key and other-project owner correctly withheld) | **G1**: no relevance floor; function-word overlap admits |
| H20 compound refund question (budget 4) | `fx-why`, `ratelimit-rumor`, `fx-fetch`, `inc-2207` | **0/3** required facts served; all 3 admitted but ranked past budget | **G4**: long questions reward incidental overlap; no per-clause coverage |
| H22 "Is the limit 1000 rpm?" | `ratelimit-rumor`, **`ratelimit`**, `fx-why` | Unconfirmed rumor at rank 1 | **G3**: no reliability or hedging signal |
| H23 why no plain ALTER TABLE | `migration-rule`, **`inc-2207`**, `bookclub` | The "what" rule outranks the incident that explains it | as H12 |

Passing strata on composed include:
- current values after repeated updates: H06, H08, H13;
- H03 history (`adr-db-v1` at rank 1);
- multi-fact H10;
- paraphrase H15 ("keep customers' card numbers");
- unseen terminology H21 ("message bus … shards");
- the H24 lexical trap.

### Authored v1 corpus (5 questions), repaired scorer

| | composed-multiroute | governed-lexical |
|---|---|---|
| P0 prohibited / stale (cases) | 0 / 1 | 0 / 1 |
| Answer at rank 1 / all critical served | 1.00 / 1.00 | 0.75 / 1.00 |

**Gold critique (frozen, not changed):**
- `Q-release-current` labels `release-old` both grade 3 and stale. But nothing supersedes it: "1.0 was delayed" is a true historical fact, not an obsolete value of "current release". That stale exposure measures text understanding the v1 schema gives the runtime no lifecycle signal for.
- `Q-no-owner` receives 2 irrelevant memories (G1).

## Phase 5: repairs and runtime gaps

**Repaired, evaluation-only:**
- E1–E5.
- The v2 lifecycle runner and lifecycle-consistent qualifier.
- Repeated-correction adjudication.
- The `update` state-change op.

Each repair is covered by focused tests. The broader suite was re-run with no new failures, and every holdout and permutation run has **zero prohibited exposure**, so there is no privacy or governance regression.

**Runtime gaps: reproduced, not patched.** Minimal reproductions against the real runtime are in `tests/test_served_memory_runtime_gaps_771.py`, marked `expectedFailure`. Each fails on its assertion when the decorator is removed:

| Gap | Minimal reproduction | Fix would land in |
|---|---|---|
| G1 function-word overlap fills a no-answer context | 2 unrelated memories served for "Who is the data protection officer?" | Lexical tokenization/scoring (`state/sqlite_substrate._tokens`) or an admission relevance floor |
| G2 elapsed declared validity served as current | Window ended 2025-12-01 ranked **first** for "this Thursday" | Applicability ranking/admission (#549 design) |
| G3 unconfirmed claim outranks recorded fact | Rumor first when the question quotes its number | Ranking has no reliability signal |
| G4 compound question's required facts past budget | 3 required plus 3 overlapping distractors, budget 4 | Ranking: per-clause coverage / diversity |
| G5 lexical tie order depends on write order | Equal overlap; reversed writes flip top-1 | `governed-lexical` tie-break by insertion-ordered ID |
| G6 historical intent ranks current value first | Identical overlap, declared historical intent: `pg16` above `pg` | Applicability-aware ranking under explicit historical intent |

**Why no runtime patch in this qualification:**
- Every gap lives in protected candidate generation, ranking or admission. Those are the baselined v6/v7 files that also drive the frozen LongMemEval/AMB lanes.
- A tokenizer, relevance-floor or ranking change alters every lane and needs a sanctioned successor baseline, which this qualification may not authorize.
- Tuning against a 24-question holdout that I also authored is the overfitting the brief prohibits.
- The defensible sequence:
  1. Adopt the evaluator repairs.
  2. Author a *second* independent holdout.
  3. Make one generalizable change per gap behind a successor declaration.
  4. Report before/after on both holdouts and on the frozen benchmark lanes.

## Remaining product-quality gaps (by user impact)

1. **No empty context, ever (G1).** Every unanswerable question gets a full budget of unrelated memories, priming a downstream model to answer from them.
2. **The asked-for memory is not at rank 1 in 8/21 answerable questions** (composed). With small budgets this decides what a model leads with.
3. **Expired declared windows are presented as current (G2).**
4. **History questions lead with the current value (G6).**
5. **Compound questions lose required facts past the budget (G4).**
6. **Reliability-blind ranking (G3)** and weak rationale ranking (H12, H23).
7. **`governed-lexical` is order-sensitive (G5).** Single-order lexical numbers are not reproducible for corpora assembled in a different order; compare only over multiple permutations.
8. **Answer-level correctness and abstention are not measured.** That needs an answering layer and an independent adjudicator; the scorer correctly refuses to infer them.

## P3: performance (separate engineering dimension, not a scalability result)

- Governed build plus all queries on a fresh SQLite store: 0.05 s for v1 (7 writes, 5 queries) and about 0.24–0.29 s for Halcyon (32 events, 24 queries). Per-run values are in `SCORECARD.md`.
- No large stores were built, per the brief.
- The #769 review on the same runtime family measured governed `retain` build cost as roughly quadratic (~46 s at 1k memories, ~390 s at 3k). That should be tracked separately before any 10k quality lane.

## Reproduce

```bash
git checkout validation/771-served-memory-quality-cloud
python -m pip install -r reference/requirements.txt
python -m unittest discover -s tests -p 'test_served_memory_*.py'
python -m unittest discover -s reference/tests -t reference -p 'test_771_served_memory_integration.py'
python reports/validation/771-cloud-qualification/measure.py --label replay   # clean tree required
python reports/validation/771-cloud-qualification/compare_scorer.py
python reports/validation/771-cloud-qualification/render_scorecard.py
```

Failing-first evidence:
- `logs/candidate_validation_regressions.log` (E1–E4 failing on the unrepaired scorer);
- `logs/e5_failing_before_repair.log`;
- `logs/candidate_tests_*.log` (authored suites on the exact SHA).
