# Agent Memory · Dedicated GitHub Pages publication branch

This branch contains the **static, read-only** Agent Memory evidence website. It does not contain the runtime, execute benchmarks, authenticate users, issue governed memory commands or decide source-of-truth.

## Publish
The intended URL is https://mythologiq-labs-llc.github.io/agent-memory/.

To enable: repository Settings → Pages → Build and deployment → Deploy from a branch → `gh-pages` → `/(root)` → Save. **This is not yet confirmed enabled.** Treat the link as provisional until an HTTP 200 and visible content check pass. Publishing may create GitHub's Pages deployment workflow; coordinate with organization Actions-spend governance first. Do not add a broad push-triggered workflow.

## Data / evidence
`data/snapshot.json` is a frozen presentation-only projection of the canonical dashboard at:
- commit: `38f6a7dcc358e8ee50a38d703b0addb9d8e660d7`
- blob: `2acc39d36b3b637a08289aa757919f55da04c54c`
- path: `reports/benchmarks/dashboard/current.json`
- as_of: 2026-10-07

Its `profiles` use **only accepted `competitive_evidence.frozen_lanes`** and the explicitly whitelisted fraction-valued native metrics (`mean_precision`, `mean_recall`, `recall_all@5`, `recall_all@10`, `ndcg_any@5`, `ndcg_any@10`, `knowledge_update_recall_all@5`, `latest_gold_ranked_first`). System rows retain exact lane, plane, pinned system revision, evidence link, harness revision and input SHA-256. Each metric compares only its accepted rows within that frozen lane/plane. System-native baselines are displayed but excluded from the best measured non-baseline score.

`competitors` separately lists discovery candidates with `not_run` or `published_reference` status. These statuses are not numeric zero and do not imply tested compatibility or comparative superiority. The site never introduces a universal aggregate score.

This release adds a standalone deterministic builder and synthetic contract tests on the publication branch. The canonical UI catalog remains repository-owned on `main`; migrating this builder into that upstream evidence pipeline is outstanding under #807. Follow-up #807 must add a **checked-in deterministic builder with tests** consuming `reports/benchmarks/ui/catalog.json` and the canonical dashboard, and publish site assets only when the projection is validated. Do not hand-edit numbers in the UI or snapshot. Existing snapshots must remain reconstructable from the pinned canonical source, and source identity must be surfaced on the page. GitHub Pages branch history alone is insufficient as an execution provenance manifest.

## Reproducibility requirements
Accepted future runs need a machine-validated run manifest capturing UTC wall time, host hardware/OS, container/build SHA, exact system/adapter/dataset/benchmark revisions and digests, inference and embedding providers/models/parameter values, judge settings, prompts, seeds, retrieval budget, costs/token counts, timeouts/retries, raw results, row-level outcomes, evaluator identity, reviewer, and security/redaction posture. Never publish tokens, private prompts, user memory, secrets or personally identifying information.

## Local static review
`python3 -m http.server 8000` from the branch root and browse `http://localhost:8000/`. Confirm that `data/snapshot.json` loads, metric+profile dropdowns change values, source links open, comparators filter, responsive layout works, keyboard focus is visible, and no metric from a published reference appears in same-harness tables.

## Guardrails
- This branch is a publication artifact and **must not be merged into `main`**.
- Content on this branch may be temporarily stale relative to main. Display the canonical dashboard's as-of date, not today's date.
- Runtime Baseline v6/v7/v8 qualification is unrelated to this Pages publishing branch.
- Do not configure automatic Actions publication while GitHub Actions spend remediation is unresolved.
- Issue #807 tracks architecture, deterministic rebuild, proof of deployment, UX QA and provenance completeness.
- Issue #806 tracks TencentDB adapter and real same-harness execution.

## Deterministic rebuild (implemented)

Check out this publication branch with full local access to the main repository's Git objects. From `gh-pages`:

```bash
git show 38f6a7dcc358e8ee50a38d703b0addb9d8e660d7:reports/benchmarks/dashboard/current.json > /tmp/am-dashboard.json
node tools/test-site-data.mjs
node tools/build-site-data.mjs --dashboard /tmp/am-dashboard.json --competitors config/competitors.json --denominators data/longmemeval-denominator-audit.json --out data/snapshot.json --source-head 38f6a7dcc358e8ee50a38d703b0addb9d8e660d7 --check
```

The builder pins source/evidence links to that exact immutable revision, computes the dashboard Git blob ID, rejects malformed provenance and out-of-range metrics, and fails when a competitor's `measured` / `not_run` status contradicts the accepted lane inputs. It cannot qualify new benchmarks or publish vendor references as same-harness evidence. Avoid editing `data/snapshot.json` by hand. A new dashboard revision requires a fresh deliberate source-head and rebuilt data. This branch is static and does not fetch data from visitors' browsers beyond its own JSON asset.


## Peer coverage explorer (publication candidate)

The candidate coverage explorer is read-only UI derived entirely from the source-pinned `data/snapshot.json`:
- `assets/evidence-transparency.js` computes exact accepted external product counts, per-frozen-profile peer coverage, and published-projection sample-count omissions. Missing/unsupported/unqualified sources never become zero scores.
- The comparison matrix excludes Agent Memory and lexical/BM25 controls from the competitor count. It counts an external product at most once, no matter how many native metrics it measures.
- `Export evidence CSV` exports accepted observed metric rows with frozen profile, plane, role, score, sample count (blank if unknown), pinned evidence URL and source revision. The CSV may contain repeated source/run links across native metrics; it is not a list of unique benchmark runs.
- `tools/test-evidence-transparency.mjs` is a Node 22 offline regression test, including negative cases for altered source hashes, status contradictions and CSV formula injection.

Test locally on this publication candidate branch:

~~~bash
node tools/test-evidence-transparency.mjs
python -m http.server 8000
~~~

For keyboard/mobile QA, inspect `http://localhost:8000/#coverage`: coverage counts, horizontal-scroll table, columns, evidence gaps, CSV download and focus. **This is an evidence surface, not a new benchmark scoring authority.**

Publication rule: test/review in an isolated branch first; updating the configured `gh-pages` branch runs GitHub's native Pages workflow and must be coordinated with the organization's Actions-spend controls. Do not merge this publication branch into `main`.

## Recovered accepted AMB query denominators

The initial Pages snapshot omitted `sample_count` for six AMB evidence records. The frozen AMB lane's `native.total_passes` includes a `passes/77` population denominator, and each of the six exact raw evidence files at canonical commit `38f6a7dcc358e8ee50a38d703b0addb9d8e660d7` independently records both `input.query_count=77` and `native_summary.total_queries=77`. `data/amb-query-count-audit.json` pins the six raw Git blob identities and the cross-check. Therefore the deterministic site builder now exposes `sample_count: 77` on its 12 AMB mean precision/recall metric observations, with `sample_count_source` explicitly naming the accepted native denominator. This is **total query population**, not the benchmark's separate active/structural subpopulation. No scores, sample selection, raw evidence or acceptance status were changed.

Future unmatched sample denominators remain null. The builder's additional tests reject malformed, zero and out-of-bounds native count strings and do not apply AMB-specific inferences to other benchmark families.

## Corrected LongMemEval per-metric populations

The initial site builder copied `native.scored_questions=419` to all LongMemEval metrics. That is correct only for general retrieval. A read-only independent inspection of all **12 pinned native `report.json` files** at `38f6a7dc` established that every source has `aggregate.evaluated_question_count=419`, `knowledge_update.evaluated_question_count=72`, and `latest_gold_ranked_first.applicable_question_count=70`. The 12 report paths, source Git blob SHAs, evaluator plane/backend, and all three denominators are recorded in `data/longmemeval-denominator-audit.json`. This is a derived publication audit, not new scoring authority.

The builder now **requires** that exact pinned audit for LongMemEval specialized metrics, verifies its source revision and dashboard blob, and rejects missing/mismatched report identities and invalid subset counts. The regenerated presentation snapshot corrects 24 historical `sample_count` observations from 419 to their actual 72/70 subpopulation. Score values, run identities, input selection and acceptance state are unchanged.

Never use total input queries (500), general retrieval evaluated questions (419), knowledge-update evaluated questions (72), or latest-date eligible questions (70) interchangeably. Review each metric's native denominator and exclusion rule when publishing new runs.
