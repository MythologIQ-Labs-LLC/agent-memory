# Competitive product-viability study: AMB v6 matched case outcomes

**Status: HISTORICAL SOURCE-BOUND QUANTITATIVE ANALYSIS, HUMAN QUALITATIVE REVIEW NOT YET PERFORMED.**

This document supplements #601, #640, #771, #787 and #789. It is not a runtime qualification, no new competitor execution has occurred, and it does not update the canonical dashboard or claim general product superiority.

## Exact comparison and what the evidence says

Frozen AMB PrecisionMemBench `single-turn`, retrieval-mode v6. All three accepted integration-descriptor source reports use the same frozen input and include the same 77 **identical query strings and gold-ID arrays**. Exact main source tree `3eebb6d54e2a218c4fd10cf53c52acac8384c3e6`.

| System/role | Raw source file Git blob | Native exact-case passes | Native pass rate | Mean precision | Mean recall |
| --- | --- | ---: | ---: | ---: | ---: |
| Agent Memory (subject) | `ea40e74850e2621ff39c65926c5ede89768e1a43` | **15/77** | **19.5%** | **18.06%** | 95.35% |
| Mem0 OSS (external product) | `426a2f3c69220efcf5e461aef54aa593b4b82155` | 10/77 | 13.0% | 10.49% | 100.00% |
| BM25 (non-product control) | `4a7b779a2aed19dc4ef71d4fa5493b83220e6c92` | 8/77 | 10.4% | 5.36% | 96.51% |

**Native verdicts** are from the already recorded benchmark scorer. These are not human task-success or answer-quality ratings. The passing threshold is the benchmark's own exact case contract, not a claim that 19.5% of real customer tasks succeed.

### Paired Agent Memory versus Mem0 results

| Matched case outcome | Number |
| --- | ---: |
| Agent Memory passes, Mem0 fails | 6 |
| Mem0 passes, Agent Memory fails | 1 |
| Both pass | 9 |
| **Both fail** | **61** |
| **Total** | **77** |

On the seven discordant cases, an exploratory **two-sided exact McNemar sign comparison gives p = 0.125** (unadjusted, no multiplicity corrections). This finite same-harness sample does **not** demonstrate a statistically reliable overall advantage. Even when Agent Memory leads on the native metric, **61 shared failures and low absolute precision** mean useful-memory selection remains a major product risk.

Categories in the 77 cases expose gaps: no system passes any of 12 `Scope disambiguation` cases, any of 3 `Supersession chain exclusion` cases, any of 2 `Counter-signal retrieval` cases, or any of 4 `Relation expansion` cases. These are exploratory groupings with small and uneven category denominators. They support investigation, not a feature-level superiority claim.

The native scorer reason flags further indicate that most failed Agent Memory cases include *unexpected beliefs in served context*. That is not an independent human determination of relevance or cause. Review the actual case contents and source paths before attributing mechanism.

## Reproducible full-population audit

The source-derived `reports/benchmarks/audits/789-amb-v6-case-dossiers.json` contains:

- all 77 joined case IDs, each system's native pass/fail status and retrieval context size/time;
- the actual scorer's machine-detectable `unexpected_belief` / `missing_expected_belief` flags;
- category-level counts and a complete four-cell paired-outcome matrix;
- exact raw source file paths and their Git blob IDs;
- **no copied gold answer IDs, unreviewed free-form critique, human scores, or generated false benchmark result**.

The audit verified identical `query` strings and `gold_answers` arrays by case ID across all three raw files. **Case contents are not in this proposed report** to avoid accidental privacy or benchmark answer distribution. Source reviewers can inspect the original committed raw artifacts under appropriate controls.

Any future machine-derived update must revalidate query IDs, raw counts, exact source SHA and all input identities; no new row is admissible because it has the same `query_id` alone.

## Qualitative review: a real study, not automated praise

A numerical retrieval score does not tell us whether users can finish a task, trust a source, recover after a wrong answer, or understand why old information was superseded.

**Panel and sampling:** Review the entire 77-case quantitative population. Separately preregister **24** qualitative cases, selected mechanically *before human judgment*: all seven Agent Memory/Mem0-discordant cases, at least one previously unselected case per category where possible, then lexical ID order to 24. The 24 are **purposively selected, not random**, so findings illustrate failure mechanisms; they must never be used to estimate population rates.

**Blinding:** A study coordinator constructs a review packet from original case prompts and provider outputs, masking product identities and numeric/pass verdicts. The assignment key remains outside reviewers' reach until their ratings are locked. Remove vendor headers when safely possible and disclose any unmistakable stylistic unblinding. Do not show gold labels before initial unguided task-utility rating. Then unseal only the reference evidence needed for provenance/accuracy adjudication in a separately recorded second pass.

**Two reviewers** should independently evaluate each case, with case ID, blind arm, raw-run SHA, review timestamp, anchored rationale and explicit supporting source references. One reviewer may be a local LLM for a *separately labeled machine judge* only if model identity, prompt and output are recorded; that does not substitute for two independent human reviews.

### Anchored ordinal dimensions

Each dimension uses **0 = materially unusable or unsafe**, **1 = weak / substantially wrong or inefficient**, **2 = partially useful with material repair required**, **3 = adequate for the stated bounded task**, or **not_applicable with a justification**. Reviewers must quote/cite actual source evidence, not a vendor description.

1. **Task utility:** Could the caller do the concrete next step correctly with this context?
2. **Source accuracy and provenance:** Are claims supported by the correct source and can the origin be inspected?
3. **Temporal/currentness:** Is the correct version used for the requested as-of/current state?
4. **Selection precision:** Is the evidence focused on the question rather than burying it in irrelevant context?
5. **Safe absence and refusal:** Does it recognize unknown, deleted, and prohibited evidence without pretending to know?
6. **Workflow recoverability:** Can a user identify and correct a wrong prior memory without losing the underlying provenance?

The dimensions are **not weighted or averaged into a single quality score**. Mark ones that cannot be judged from retrieval-only output as `not_applicable`, especially task utility and workflow recoverability when no downstream agent answer was generated. Never grant points for lack of data.

### Nonnegotiable review controls

- **P0 privacy/authority violations remain categorical blockers**, not 0/3 points that can be offset by high speed.
- Reviewers must record actual `source_path` + case-row evidence and a narrative for each low rating. If provenance is missing, mark `unsupported` and do not infer from semantic similarity.
- Report **all material disagreements**, per-dimension agreement and adjudicated resolutions. No cherry-picked anecdote replaces the full 77-case population.
- Report **time/cost separately** and disclose whether ingestion, embedding, storage, inference and reviewer cost are included.
- Compare outcomes only within supported common tasks. Missing competitor lifecycle functions are `unsupported`, not zero accuracy.
- Every real-world study should add tasks for decade-long codebase decisions, contradictory updates, deletion privacy, cross-project isolation, across-agent portability, procedural reuse and long-term task resumption. Freeze case specifications **before** testing candidate runtime changes.

### Initial prompts for investigating failures, not causal conclusions

- `alias-gha-resolves`: Agent Memory passed, Mem0 did not. Inspect whether context focus or the native alias mechanism changes the user-relevant outcome.
- `questions-pinned-active-only`: Mem0 passed, Agent Memory did not. Inspect whether Agent Memory admitted unrelated beliefs instead of an explicit question/pinned fact.
- `out-of-scope-coin-collecting`: neither passed. Determine whether proper safe absence is measurable and why irrelevant memories appear.
- `fuzzy-scope-filter-discriminates-after-fuzzy-fires`: Agent Memory passed, Mem0 did not; compare retrieved context inflation and scope safety.
- `happy-stack-repository-layer`: neither passed; assess distractor burden and whether either output truly enables repository work.

These five are illustrations drawn from **existing** benchmark cases. They do not constitute independent human judgments or future holdout successes.

## Decision rule for product viability

An investment-grade evidence story needs **both**:

- **Quantitative, source-qualified measurements:** multiple architectural peer systems, same-harness exact native metrics, full denominators, replays, resource cost and uncertainty; fixed budgets, separated retrieval and end-to-end task success.
- **Qualitative, independently challenged examples:** preregistered representative workflow scenarios, blinded case comparison, provenance, failure modes, error recovery, abstention and actual task completion.

At present, AMB v6 offers a meaningful narrow relative comparison but **does not establish absolute product quality**. A prudent next milestone is improving selection precision, relevance/abstention and scope correctness against independent frozen cases while broadening external competition. Do not raise a leaderboard banner proclaiming product viability based on 15/77 correct or a single competitor.

**Release relevance:** PR #788's cross-scope security repair is independently tracked and not published as a successor. Historical v6 results should not be represented as the performance of that newer runtime. #787's canonical-dashboard lane reconciliation remains a separate acceptance gate.


## Executable qualitative-review acceptance guard

`scripts/check_789_qualitative_review.py` and `reference/tests/test_789_qualitative_review_contract.py` are executable, pure-Python guards. The **14 negative/positive contract tests passed in a local reconstructed checkout** without external inference; the exact full-repository test command still needs a repo checkout run:

```bash
python -m unittest discover -s reference/tests -p test_789_qualitative_review_contract.py -v
python scripts/check_789_qualitative_review.py \
  reports/benchmarks/audits/789-amb-v6-case-dossiers.json \
  reports/benchmarks/audits/789-qualitative-reviews.PENDING.json
```

Current expected output is `incomplete_not_publishable`: the pending review ledger is `[]`, **zero human evaluations exist**, and no qualitative preference scores are asserted. A nonaccepted, unlocked example input is `789-qualitative-review-form.TEMPLATE.json`.

Each locked review must identify the frozen case, blinded arm A/B, independently verified reviewer, source trace, all six anchored rating dimensions (0–3 or justified `not_applicable`), evidence citations, and explicit categorical P0 privacy flags. Reviewers cannot indicate they saw the native scoring outcome before review lock. A value of `true` is never accepted as a numeric rating, and all-dimensions-`not_applicable` submissions are rejected. At least **two distinct human reviewers per blind case/arm** are required to advance from `incomplete_not_publishable` to `ready_for_independent_adjudication`; this latter status is **not publication approval**. The checker reports rater disagreements and any P0 flags separately, never averages away safety and never assigns a model-to-case winner.

A study coordinator must independently verify reviewer identities, true output blinding, original source provenance, lack of outcome leakage, adjudication notes, and completion of the qualitative evidence package. The checker alone cannot prove those organizational facts or make a commercial claim.

For 24 selected cases × 2 measured product arms × 2 human raters, full human coverage requires **96 locked review forms**. The third BM25 control remains quantitatively recorded but is not a product arm in this initial human study. This is intentionally a substantial evidence gate, not a nominal checkbox.
