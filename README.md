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

## Independently run external benchmarks (October 15, 2026)

A separate **external evaluation directory** is published under `#external-evaluations`. Its versioned source is `data/external-evaluations.json`, rendered by `assets/external-evaluations.js` and checked with `tools/test-external-evaluations.cjs`. Sources link to the current official public evaluation program and directly to upstream methods, not transcribed external score numbers.

Tracked external programs:
- AML (Agent Memory Leaderboard): participant-hosted Add/Search API and official cycle submissions. **No verified Agent Memory official submission or placement.** Cycle 2 material deadline: October 31, 2026, 23:59 UTC+8.
- AMB (Agent Memory Benchmark): public upstream native harness and results board. Agent Memory has a source-pinned provider bridge on main, but **the directory does not claim an upstream run or official placement**.
- MemoryArena: preview research benchmark for multi-session agent task outcomes. **No verified Agent Memory execution**.

Directory maintenance is intentionally separated from the accepted `data/snapshot.json` numeric metrics. No browser-side scraping or remote leaderboard dependency is used. Source links, manual participation status, exact as-of date and next concrete execution step are explicit. An `official_result` may only be added after an external organizer's publicly verifiable result, declared metric+dataset+evaluator version, system commit, date, and independent review. The validator refuses unproven "official" status. External results must not be merged into the accepted same-harness leaderboard or extrapolated as cross-program ranks.

Run `node tools/test-external-evaluations.cjs` and inspect `#external-evaluations` on mobile/keyboard before publication. Updating `gh-pages` will trigger only the native GitHub Pages deployment, not our benchmark CI.

## Read-only live candidate benchmark tracker (October 15, 2026)

The GitHub Pages site adds a prominent `#live-runs` section **immediately below the accepted leaderboard**. This section is intentionally separate from frozen accepted `data/snapshot.json`. The script is `assets/live-evidence.js`; it refreshes on load, on user request, and every 15 minutes in a visible browser tab.

This fixes the problem that `gh-pages` does not automatically rebuild when benchmark workers commit fresh evidence. Instead, the browser retrieves the two known public source-branch heads through read-only GitHub REST refs and then fetches report files from `raw.githubusercontent.com` at their **immutable SHA**:
- `claude/817-jev-mem-execution-no-ci`: the preregistered 50-question LongMemEval-S candidate comparisons for Agent Memory, Mem0, Hindsight, and partial Jev-Mem/Cognee progress.
- `claude/wizardly-cray-bmkfrr`: self-run upstream AMB full-split PrecisionMemBench case CSVs and the bounded MemoryArena native result summaries in draft PR #818.

Only **complete, zero-error, exact-input+selection-verified** 50-question LongMemEval-S session+turn results are displayed numerically. Partial Cognee/Jev-Mem summaries show completed/planned counts, **never extrapolated scores**. The native AMB self-run is parsed from all 77 raw case-level outcomes, compared to BM25, and shows the 60/62 unexpected-memory failure pattern. MemoryArena remains labeled a one-task exploratory test. The script renders links to exact source SHA files and is XSS-escaped. It never calls protected APIs or stores credentials. Gzip results use browser `DecompressionStream`; browsers without support withhold those rows rather than guessing.

**Provenance boundaries:** Only source report files at the specifically allowlisted branches and paths are shown. Updating a tracked source branch changes what the live section shows without a Pages build or hosted CI. Adding a new branch or new report path requires a deliberate source registry change and site deploy. The source hash is shown prominently; if a source ref/report is missing, the section fails visibly and retains the independently accepted older table above. It never changes `data/snapshot.json`, official external leaderboards, or qualification state. If the AMB full-split result differs from the reviewed 15/77 vs 8/77, this version withholds the previous result and requires a new independent review before updating the public presentation contract.

The **accepted** snapshot above is still intentionally frozen until separately reviewed and republished. A future source-bound, budget-free accepted publication workflow may be built after benchmark-governance approval; do not use automated acceptance just because an execution branch pushed rows.

Offline contract testing: `node tools/test-live-evidence.cjs`. Use a browser with JavaScript and public GitHub access for integration QA. Under GitHub API public anonymous rate limits, the manual refresh can be throttled; it makes two unauthenticated branch-ref calls per cycle, not any Actions jobs.

### External directory refresh after first real runs

The October 15 local executions recorded in draft PR #818 have been reflected in `data/external-evaluations.json`: AMB `external_run` for the **77-case upstream native self-run**, and MemoryArena `external_run` for the **one-task bounded exploratory experiment**. Neither is an official listing. Both link to exact evidence at `1df28f84c236f5369b004465252610bd88ae07c9`; AML remains `not_verified` until officially assessed. The source directory's `official_result` fields remain null for all three programs. No accepted evidence table changed.

## Auto-discovery of new run manifests (read-only, October 15, 2026)

`assets/run-discovery.js` reads `data/live-sources.json`, a strict allowlist of at most four publicly tracked source branches. It resolves their current head commits and Git trees via GitHub's read-only REST API, and discovers standard `reports/benchmarks/runs/**/*.manifest.json` and `*.summary.json` within that prefix. Adding a new **run folder, system, cohort, or native benchmark family within an approved branch needs no Pages changes**.

Manifest records must follow issue #808's published version `schema_version: "1.0.0"` and include `run_id`, exact benchmark/dataset/selection identity, `normalized_run.uri` plus SHA-256, system and adapter identities, exit code 0, and a `review.status` of candidate/reproduced/reviewed (never auto-accepted). The browser downloads normalized reports from the exact branch-head commit and verifies **SHA-256 of their raw bytes through WebCrypto**. Scores are shown only for native LongMemEval-S retrieval profiles when the report's benchmark input, selection hash, plane/backend identity, zero-error counters, and population denominator all match the manifest. It never infers scores for unknown benchmark families. The native value `recall_all@5` (session) or `recall_all@10` (turn) is shown alongside its explicit profile and input population; unlike the accepted canonical leaderboard, no cross-profile ranking is calculated.

Partial-progress `*.summary.json` records from the same run prefix display completed/planned counts only when all zero-error and missing-question list constraints pass; **partial ratios are never benchmark scores**. Files and sources are capped, and tree-truncation, source-drift, missing WebCrypto, gzip incompatibility, bad sha256, or result failures refuse numeric publication. On transient branch lookup failure, the last validated candidate projection remains and the status reports stale verification. The historical accepted leaderboard stays independent.

The site looks for new source evidence automatically every ~15 minutes while visible and when the existing manual refresh button is clicked. Subsequent checks against unchanged branch-head SHAs reuse in-memory verified results, so they only need one lightweight GitHub ref request per configured source. No GitHub Actions are triggered by the browser, and no private credentials are needed. Unregistered branches remain intentionally excluded. To add one, review its identity and update the allowlist in `data/live-sources.json`, with one deliberate Pages deployment.

Tests: `node tools/test-run-discovery.cjs`, in addition to existing `node tools/test-live-evidence.cjs` and `node tools/test-external-evaluations.cjs`. This is a publication projection, not benchmark qualification; never move a candidate into `data/snapshot.json` without governance acceptance.

## Outcome-first measured leaderboard (2026-10-15)

The primary **Benchmark leaderboard** ranks memory products based on measured outcomes, including unaccepted candidate benchmarks and poor Agent Memory results, instead of hiding those metrics beneath the accepted-only archive. Users may select `All measured results` (default) or `Accepted results only`. The older accepted archive remains present and unchanged for audit, but is explicitly labeled historical.

The source-pinned curated fallback is `data/candidate-leaderboard.json`: preregistered LongMemEval-S 50-question session and turn recall, Hindsight/Mem0/Agent Memory/lexical baseline, and full upstream AMB PrecisionMemBench strict-case success (15/77 vs BM25 8/77). The curator captures the exact Claude evidence branch commits as of October 15, statuses `candidate` or `reviewed_self_run_unofficial`, and full source URLs. The fallback is **not a new acceptance decision**.

`assets/measured-leaderboard.js` listens to cryptographically verified `agent-memory:candidate-runs` events from `assets/run-discovery.js` and updates LongMemEval-S cohorts when more complete approved-branch manifests arrive. Profiles are keyed by exact dataset, selection, sample count, evaluator revision, granularity and native metric; unrelated cohorts and methods are kept separate. Previously verified fallback rows remain when public network access fails. New manifest files on the currently allowlisted Claude benchmark branches are therefore discoverable without Pages redeployment. New branch names or unrecognized benchmark metric decoders require explicit review and site registration.

The ranking counts memory systems, excluding lexical/BM25 baselines; it displays Agent Memory's rank and percentage-point delta against the best measured external memory system. For the 50-question session sample, that means Agent Memory is **3rd of 3 measured memory systems**; on the turn sample it is **2nd of 3**. AMB strict success 15/77 is shown with the real BM25 same-protocol baseline. Hindsight's separately published AMB 66/77 uses structured filters and ingestion LLM, and is disclosed but **excluded from the query-only leaderboard ranking**.

The accepted snapshot `data/snapshot.json` remains frozen pending independent qualification. The measured board cannot write to it. Offline suite: `node tools/test-measured-leaderboard.cjs`. The existing `tools/test-live-evidence.cjs` and `tools/test-run-discovery.cjs` must still pass.

## Data-only benchmark publication contract (October 15, 2026)

**Keep the website's shape unchanged.** The page's existing measured leaderboard now reads the versioned public candidate feed at `benchmark-public-feed:reports/benchmarks/public-feed/v1.json`. This branch is deliberately **separate from the Pages application files, accepted benchmark snapshot and `main`**. A new candidate benchmark cohort or competitor requires an evidence-verified **feed data update only**, not a redesign, HTML/CSS change or new Pages deployment. The browser checks this branch for updates on load, on manual refresh and every ~15 minutes while the tab is visible.

The feed contains only immutable artifact coordinates (exact source commit and path), artifact SHA-256, frozen benchmark/evaluator identity, cohort/denominator, runtime revision when available, evidence status, extraction path, and expected result. `assets/public-measurement-feed.js` re-reads the original JSON/CSV/gz native result, cryptographically verifies report bytes, recalculates scores, validates native denominator/revision and rejects discrepant values. Only verified rows enter the primary leaderboard, and the status remains `candidate` or `reviewed_self_run_unofficial`. Verified feed rows outrank the original curated fallback, and the original fallback remains available during public-network outages. The accepted `data/snapshot.json` is not altered. No general-purpose cross-benchmark rank is calculated.

Runtime engineering #819 data are represented by **separate self-measured revision comparisons**, not competitive product rankings, while independent holdout evaluation is pending. These include the AMB improvement (15/77 to 39/77) and the LongMemEval-S full500 recall-all@10 declines (session 89.26% to 75.42%; turn 72.32% to 63.25%). No claim of default-runtime qualification is made.

For data maintainers: append or update evidence records in `benchmark-public-feed:reports/benchmarks/public-feed/v1.json` only after the original benchmark result has been committed, frozen, and source-pinned. Preserve exact cohort identity. Verify the feed locally using `node tools/test-public-measurement-feed.cjs`; use the publication branch's README as the exact contract. Do not trigger hosted CI/PR workflows as part of candidate publication. The public page should reflect new validated measurements without additional site code changes. Change the site's appearance only for an explicit owner-approved design update.
