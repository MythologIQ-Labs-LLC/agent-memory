# Plan: #662 Phases 2–4 as one evaluation-only change (roadmap `prereq-ci-cost`)

**Status**: iteration 3 (2026-10-07), Gate Tribunal PASS at Entry #77 (condition C1); iteration 1 VETOed at Entry #75 (V1 token-level full-suite detection, V2 measured timeouts for every job, V3 PR-only cancellation; A1, A2 applied); iteration 2 VETOed at Entry #76 (V4 the complete-every-run set derived from the records; A3 applied)
**Issue**: #662 (FinOps + CI architecture; parent `Myth-Tech-Forge#482`); roadmap scope `scope-prereq-ci-cost-plan`, whose merged outcome resolves `prereq-ci-cost` in `scope-tranche-6-rebalance`
**Research**: `docs/research-brief-tranche-5-harvests-and-ci-cost-2026-10-07.md` finding E (Entry #74); measurements on PR heads e20c70d, 8e1211e, a370285 and merge commits a5c6de3, b7f6bd2
**Predecessor artifact**: `.qor/gates/2026-10-06T1200-668ns/research-iter2.json`

- purpose: a PR head stops triggering the 41 `push` runs that duplicate its `pull_request` runs, every hosted job carries a measured timeout, every supersedable PR workflow cancels its stale run, and the full reference suite runs once per trigger instead of eleven times, with the intended state written as data and enforced by one test so the estate cannot drift back.
- limitations: this plan changes triggers, concurrency, timeouts and one redundant step; it changes no benchmark input, scoring, evidence contract, check name or required control (#662 stop lines). Post-merge runs on `main` are kept for every workflow that has them today (Phase 4 names post-merge integration as a legitimate lifecycle boundary), so the 42 runs per merge are unchanged by design. Wall-minutes are run-volume facts, not spend (#662 "Starting evidence"). Phases 5 and 6 (reusable workflows, artifact retention) are out of scope. The protected surface (`pyproject.toml`, `reference/agentmem_ref/**` minus `evaluation/**`) is untouched: `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` stays `PASS` against Runtime Baseline v2.
- non_goals: retiring any of the 6 `one_time` workflows (that is #662's "retire after evidence review", not a trigger change); moving the 5 discretionary benchmark lanes off the PR path (they cost under 1.2 minutes each and the inventory keeps them `ASYNC` for Phase 5); machine-readable branch protection; a new top-level workflow (#662 Phase 0; the enforcement test runs inside the required `Validate Doctrine Evidence` job's full-suite pass); regenerating the inventory's provisional classification fields (`lifecycleClass`, `consequenceClass`, `proposedDisposition` are reviewed judgments, not derived state).

## Open Questions

1. **Post-merge runs on `main` kept (default taken).** The 40 bare `push:` triggers become `push: branches: [main]`, not a removal. #662 Phase 4 lists "post-merge/main integration" as a boundary that justifies a push run, and the merge commit's tree differs from the PR head's. The alternative, dropping `push` entirely from the 34 `required_hot_path` files, would also remove the 42 runs per merge but leaves `main` with no integration signal after a merge whose base moved; it is not taken here and would be its own Phase 4 slice with the inventory's lifecycle classes as the deciding data.
2. **The complete-every-run set (derived, default taken).** Rule: a PR/push workflow whose run is cited by run id in a committed record keeps every run (`cancel-in-progress: false`, queued by the same group); so does `publish-wiki.yml` (a publication on `main`). Derivation (2026-10-07): `git grep -nE 'workflow_run(_id)?"?\s*[:=]\s*"?[0-9]{11}' -- reports docs reference/fixtures reference/agentmem_ref/evaluation fixtures examples` yields 40 distinct run ids; each resolved through the Actions API (`/actions/runs/<id>` → `path`) gives these PR/push workflows and their citing records:

| workflow | citing record(s) |
|---|---|
| `agmi-agent-memory-qualification.yml` | `reports/gauntlet/agmi-agent-memory-v1/accepted-result.json`, `qualification.json` |
| `canonical-json-v2-vector-integrity.yml` | `reference/fixtures/runtime/canonical-json-v2-vectors-accepted-v1.json` |
| `gauntlet-external-contestant-dogfood.yml` | `reports/gauntlet/external-contestant-v1/golden-evidence.json`, `reports/runtime/baseline-v1.json`, `baseline-v2.json` |
| `hindsight-v090-qualification.yml` | `reference/fixtures/component-qualification/hindsight-v0.9.0-resource-artifact-qualified-v12.json` |
| `memos-v2017-substitution.yml` | `reference/fixtures/component-qualification/memos-local-plugin-v2.0.17-resource-artifact-qualified-v12.json` |
| `proposition-semantics-score.yml` | `reports/benchmarks/replays/594-post-550-semantic-qualification/phase-b-score-v1.json` |
| `runtime-baseline.yml` | `reports/runtime/baseline-v1.json`, `reports/runtime/baseline-v2-qualification.json` |
| `rust-shadow-kernel.yml` | `reports/benchmarks/dashboard/current.json` |
| `temporal-currentness-final-replay.yml` | `reports/benchmarks/temporal-currentness/final-policy-3.1.1/accepted-evidence.json`, `reports/runtime/baseline-v1.json`, `baseline-v2.json` |

The two dispatch-only lanes (`amb-competitive.yml`, `longmemeval-competitive.yml`) are also cited and already carry `cancel-in-progress: false`. `gauntlet-durability-recovery.yml` and `recall-validation-external-replay.yml` are cited by no committed record and therefore cancel superseded runs like every other workflow; when a later record cites one of their runs, that workflow's policy entry changes and the test enforces the new state. The set is therefore ten complete-every-run workflows (nine cited plus `publish-wiki.yml`) and 71 cancel-superseded.
3. **PR #665 (`finops/discretionary-stale-run-cancel-1`, five discretionary lanes, same group expression as LD4).** This plan carries the block for those five files among the 71 cancel-superseded entries it adds (with the conditional expression instead of #665's literal `true`), so #665 becomes a strict subset of this change. Default taken: after this plan's PR merges, one comment on #665 states that it is subsumed and names the merge commit; closing it is left to its author.
4. **Timeout rule (default taken).** Every job without a timeout was measured: 49 jobs from the pull_request runs on head 8e1211e, the other 29 from the maximum job duration over each workflow's last three successful runs (GitHub API, 2026-10-07; the table is in LD5). The value is `max(10, ceil(3 × measured_minutes / 5) × 5)`: three times the measured duration, rounded up to a five-minute step, never below ten. Jobs that already declare a timeout keep it. A timeout failure stays distinguishable from a product failure because GitHub reports it as `The job running on runner … has exceeded the maximum execution time`, and the policy test does not read conclusions.

5. **The two path-filtered full-suite jobs (default taken).** `evolveai-multicapability-qualification.yml:148` and `hermes-observe-govern-integration.yml:167` run `unittest discover -s reference/tests -p 'test_*.py'` (through `python -m`), the whole reference suite under the default pattern, inside qualification workflows that fire only on their own paths. They are kept as they are and declared in the policy as full-suite jobs with their path triggers as the reason; narrowing them is a judgment about those qualifications, not a FinOps change. The invariant therefore reads: the unconditional pull_request path runs the full suite in exactly one job, and every other full-suite job is path-filtered.

## Locked Decisions

**LD1 — The intended estate is data, enforced by one test.** New `data/github-actions-workflow-policy.json`: `{"schema_version": 1, "governing_issue": "#662", "concurrency_group": "${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}", "workflows": {"<file name>": {"pull_request": "unfiltered" | "paths" | null, "push": "main" | "main_paths" | null, "other_triggers": ["workflow_dispatch", ...], "concurrency": "cancel_superseded" | "complete_every_run" | "none", "jobs": {"<job id>": {"timeout_minutes": <int>, "full_suite_passes": <int>}}}}}` with one entry per file under `.github/workflows/` (85). New `reference/tests/test_github_actions_workflow_policy.py` loads every workflow with `yaml.safe_load` (PyYAML pinned in `reference/requirements.txt`; the `on` key parses as the boolean `True`, which the reader normalizes) and derives the same shape: `pull_request` is `"unfiltered"` when the trigger has no `paths`, `"paths"` otherwise; `push` is `"main"` when `branches == ["main"]` and no `paths`, `"main_paths"` with paths, and the test **fails on any push trigger without `branches: [main]`**; `concurrency` is `"cancel_superseded"` when the top-level block has exactly the policy's group and `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`, `"complete_every_run"` with `cancel-in-progress: false`, `"none"` when absent, and any other block fails the test; per job, `timeout_minutes` is the literal `timeout-minutes` (the test fails on a job that runs on a hosted runner without one) and `full_suite_passes` counts `run:` steps that invoke `unittest discover` over `reference/tests` with no `-p` option or with the default pattern `test_*.py`: the reader tokenizes each `run:` script line with `shlex`, finds the `unittest discover` module invocation, reads `-s`/`--start-directory`, `-t`/`--top-level-directory` and `-p`/`--pattern` as options (any spelling, any order), and counts the line when the start directory resolves to `reference/tests` and the pattern is absent or `test_*.py`; a narrowed pattern or an explicit module list is not a full-suite pass. The policy carries no command literal; the rule lives in the reader and its unit test exercises all four spellings present today (`-s reference/tests -t reference`, `-s reference/tests -p 'test_*.py'`, `-s reference/tests -t reference -p 'test_x.py'`, explicit modules). The test asserts derived == declared for every file, that the set of files equals the set of policy keys, and three global invariants: (i) no `push` trigger without `branches: [main]`; (ii) among workflows whose `pull_request` is `"unfiltered"`, exactly one job declares `full_suite_passes > 0` (`validate-doctrine-evidence.yml` / `validate`, with 2), and every other job with `full_suite_passes > 0` belongs to a workflow whose `pull_request` is `"paths"` (today `evolveai-multicapability-qualification.yml` / `qualify-evolveai` and `hermes-observe-govern-integration.yml` / `hermes-integration`, OQ5); (iii) every workflow with a `pull_request` or `push` trigger has `concurrency != "none"` except `enforce-issue-labels.yml` (an `issues` trigger). Nothing reads `conclusion`s or run history; the test is a pure function of the YAML.

**LD2 — Phase 4: the bare `push:` becomes `push: branches: [main]` in the 40 files and `runtime-baseline.yml`.** The 40 files (every file whose `on:` is a bare `push:` plus bare `pull_request:` at lines 3–5: agent-manifest-external-evidence, architecture-family-closeout, authority-laundering-evidence, autonomous-maintenance-evidence, capability-behavior-contract, cedar-policy-comparator, cli-doctor, cmcp-external-evidence, conditional-memory-evidence, conditional-memory-influence, config-bound-recovery, derivation-currentness-evidence, derivation-output-custody, domain-schema-discovery-evidence, domain-schema-mutation-contract, external-evidence-contract, langgraph-lifecycle-comparator, long-horizon-memory-benchmark, maf-lifecycle-comparator, maintenance-evidence, memory-metabolism-benchmark, opa-policy-comparator, operational-memory-benchmark, p9-systems-characterization, policy-projection-compatibility, precedent-candidate-retrieval, provider-discovery, restart-safe-runtime, retrieval-quality-benchmark, reusable-grant-authority-transition, runtime-composition, runtime-configuration, sleeper-poisoning-evidence, sqlite-production-substrate, structural-mutation-governance, temporal-commitment-evidence, unsafe-composition-evidence, uor-addr-compatibility, validate-doctrine-evidence, write-readable-visibility) get

```yaml
on:
  push:
    branches: [main]
  pull_request:
```

and `runtime-baseline.yml:4-5` gains `branches: [main]` above its existing `paths:`. Nothing else in the trigger blocks changes; the 8 files already restricted to `main` and the 40 path-filtered PR-only files are untouched. Effect on a PR head: the 43 push jobs (86 → 43 fixed check runs) stop; effect on `main`: unchanged. The `seal-anchors.yml` push on `main` with no paths is already in the kept shape.

**LD3 — Phase 4: the unconditional PR path runs the full reference suite once.** The step `Execute full reference regression suite` (or its local name) that runs the unpatterned `python -m unittest discover -s reference/tests -t reference` is deleted from nine workflows: `capability-behavior-contract.yml:28-29`, `cli-doctor.yml:63-64`, `config-bound-recovery.yml:28-29`, `provider-discovery.yml:80-81`, `restart-safe-runtime.yml:28-29`, `runtime-composition.yml:28-29`, `runtime-configuration.yml:28-29`, `structural-mutation-governance.yml:31-32`, `write-readable-visibility.yml:28-29`. Each keeps the targeted step that precedes it (`-p 'test_<module>.py'` or an explicit module), so each still gates its own contract. `validate-doctrine-evidence.yml` keeps both passes (`:38` and `:168`, the second against the optionally installed real substrate) because it is the required check (`docs/ARCHITECTURE_PLAN.md:102`; `docs/programs/runtime-evidence/procedural-memory.md:242`) and the only place the whole suite must hold. Effect per PR head, unconditionally: 22 full-suite passes become 2; the nine deleted passes are 90–100 s each on the measured head, about 14–15 of the 41 measured pull_request wall-minutes, and the same again on the push side until LD2 removes it. The two path-filtered full-suite jobs of OQ5 are unchanged.

**LD4 — Phase 2: one concurrency block on every PR/push workflow.** Each of the 81 workflows with a `pull_request` or `push` trigger (every file except the three dispatch-only lanes, which keep their existing blocks and `cancel-in-progress: false`, and `enforce-issue-labels.yml`) gets, directly after `on:` and before `permissions:` (71 of them):

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

The group keys on the PR number for pull_request events and on the ref for push events, so two PRs never cancel each other and a `main` push never cancels a PR run (#662 "verify branch/PR isolation"). Cancellation is conditional on the event: a superseded PR head's run is cancelled, while post-merge runs on `main` (group `<workflow>-refs/heads/main`) queue behind each other and every one completes, because OQ1 keeps them as the integration signal for each merge. The ten complete-every-run workflows of OQ2 carry the same group with the literal `cancel-in-progress: false`: no run of theirs is cancelled on any event, so a superseded run can never be mistaken for accepted evidence and no run that a record may cite is lost. The policy test asserts the exact expression string per workflow (`"cancel_superseded"` ⇔ the conditional expression; `"complete_every_run"` ⇔ `false`). PR #665's five files (none cited by a record) are inside the 71 that get the conditional expression (its literal `true` is superseded).

**LD5 — Phase 3: a measured timeout on every hosted job.** Every job without `timeout-minutes` (77 of 90) gets `max(10, ceil(3 × measured / 5) × 5)` from its measurement (OQ4); the 13 jobs with an explicit value keep it. Measured maxima and resulting values (minutes; the 49 pull_request jobs on head 8e1211e, and the 29 others from each workflow's last three successful runs):

| value | jobs (measured max) |
|---|---|
| 25 | `codegenome-multicapability-profile/validate-profile` (7.6) |
| 20 | `validate-doctrine-evidence/validate` (6.1) |
| 15 | `codegenome-reality-mesh-evidence/codegenome-reality-mesh` (5.0), `component-qualification-evidence/qualify-code-graph` (4.8), `codegenome-scope-residue-closeout/closeout` (4.3) |
| 10 | every other job without a timeout: the 41 remaining P/PR jobs (max 2.4, `cedar-policy-comparator`; `cli-doctor/wheel-install` already has 15 and `validate-doctrine-evidence/validate` is the 20 above), the measured PR-only jobs (`benchmark-integration-contract/contributor-contracts` 0.4, `seal-anchors/verify`, `runtime-baseline/validate`, `gauntlet-external-contestant-dogfood/public-quickstart`, `gauntlet-durability-recovery/durability-recovery-alpha`, `agmi-agent-memory-qualification/reproduce-external-row`, all 0.2) and the 25 path-filtered jobs measured at or below 1.1 min (`evolveai-multicapability-qualification/qualify-evolveai` 1.1, `procedural-memory-evidence` 0.8, `rust-shadow-kernel/qualify` 0.7, `evolveai-cognitive-mesh-evidence` 0.7, `dashclaw-external-verdict/provider-proof` 0.7, `canonical-json-v2-migration-preflight/preflight` 0.5, `hermes-observe-govern-integration/hermes-integration` 0.4, the two `hermes-recursive-learning-research`/`cognitive-mesh-evidence`/`canonical-json-v2-transaction-qualification`/`canonical-json-v2-parity` jobs at 0.3, and the rest at 0.1–0.2 including `publish-wiki/publish` and `enforce-issue-labels/ensure-label`) |

The exact value per job is the policy file's `timeout_minutes`; the YAML carries the same literal; a job whose later measurement exceeds a third of its value is re-derived by the same rule in a later slice. Timeout failures stay distinguishable from evaluator failures (GitHub's own `exceeded the maximum execution time` annotation), and no job's work changes.

**LD6 — The inventory's mechanical fields follow the YAML, by script.** New `scripts/sync_workflow_inventory.py`: for each record in `data/github-actions-workflow-inventory.json` it recomputes `triggers` (event names, sorted), `pathScope` (`"paths"` when any trigger has `paths`, `"branches"` when push is branch-restricted without paths, `"repository-wide-or-unscoped"` otherwise), `timeoutState` (`explicit`, `valuesMinutes` sorted unique) and `concurrencyState` (`configured`, `cancelInProgress`) from the YAML and rewrites `inventorySummary.triggerCounts`, `missingExplicitTimeoutCount` and `supersedablePrOrPushWithoutConcurrencyCount`; `--check` exits 1 when the committed file differs (the policy test calls the same function and asserts no drift); `--report` prints the before/after trigger table #662 "Required validation" asks for (one row per workflow: pull_request, push, concurrency, timeouts) from two revisions (`git show <rev>:<path>`). The provisional judgment fields are never touched. A new top-level `postSnapshotChanges` entry records this plan's change set with the merge commit and states that `pathScope` gains the value `"branches"` (the Phase 1 snapshot used two values).

**LD7 — Documentation and governance.** `docs/CONTRIBUTOR_ARCHITECTURE.md` gains a short "CI estate" paragraph (after §8): the policy file is the intended state, the test enforces it, a PR head triggers pull_request runs only, `main` keeps post-merge runs, the full suite runs in the required check only, and a new workflow needs a policy entry (so #662 Phase 0's freeze has a mechanical check: the test fails on a file with no policy entry). `docs/GOVERNANCE_INDEX.md` Tier 4: this plan. One comment on #662 after merge with the `--report` table, the check-run count on the implementation PR's head and on its merge commit, and the PR #665 note (OQ3). The roadmap node `prereq-ci-cost` is resolved by pointer at the merge commit.

## Phase 1: policy data, enforcement test, inventory sync (no workflow behaviour change yet)

### Affected Files

- `reference/tests/test_github_actions_workflow_policy.py` - new; derives the estate from YAML and asserts it equals the policy (LD1) and the inventory sync is clean (LD6); at this phase the policy file describes the **current** estate, so the global invariants (i)–(iii) are declared as `expected_failures` listing the files that violate them, which Phase 2 empties
- `reference/tests/test_sync_workflow_inventory.py` - new; round-trips one synthetic workflow YAML through the sync function, checks `--check`/`--report` on a temporary copy, and exercises the full-suite detector on the four spellings of LD1
- `data/github-actions-workflow-policy.json` - new (LD1), generated from the current YAML by `scripts/sync_workflow_inventory.py --emit-policy` and committed
- `scripts/sync_workflow_inventory.py` - new (LD6)
- `reference/requirements.txt` - `pyyaml==6.0.3` (test-time dependency of the reference profile; `pyproject.toml` untouched)
- `data/github-actions-workflow-inventory.json` - mechanical fields re-synced (no classification change)

### Changes

Per LD1 and LD6. The policy file is emitted from the YAML once, so Phase 1 commits with the test green against today's estate; the `expected_failures` list makes the three invariants visible before they are enforced.

### Unit Tests

- `reference/tests/test_github_actions_workflow_policy.py` - derived == declared for all 85 files; set equality of files and keys; invariants (i)–(iii) with the Phase 1 exception list; `sync --check` clean.
- `reference/tests/test_sync_workflow_inventory.py` - a synthetic file with `push: branches: [main]` + `pull_request: paths` + concurrency + two jobs round-trips to the expected record fields; `--check` fails on a drifted copy; `--report` emits one row per file.

## Phase 2: the estate change (#662 Phases 4, 2, 3)

### Affected Files

- `reference/tests/test_github_actions_workflow_policy.py` - the `expected_failures` list becomes empty; invariants (i)–(iii) hold unconditionally
- `.github/workflows/*.yml` (the 40 P/PR files + `runtime-baseline.yml`) - LD2 triggers
- the nine workflows in LD3 - the unpatterned full-suite step deleted
- the 81 PR/push workflows - LD4 concurrency block (71 conditional on `pull_request`, 10 literal `false`)
- every job without a timeout (77 of the 90 jobs, in 74 files) - LD5 `timeout-minutes`
- `data/github-actions-workflow-policy.json` - updated to the intended state (the diff of this file **is** the before/after table of the change)
- `data/github-actions-workflow-inventory.json` - re-synced mechanical fields and summary counts; `postSnapshotChanges` entry

### Changes

Per LD2–LD5. One commit per locked decision (triggers; full-suite step; concurrency; timeouts) so each is reviewable as a mechanical transform, and a final commit for the policy and inventory files. The transforms are applied by a throwaway script kept out of the repository; the committed artefacts are the YAML files, the policy and the inventory.

### Unit Tests

- `reference/tests/test_github_actions_workflow_policy.py` - all invariants hold; the policy equals the YAML; `sync --check` clean.
- `python -m unittest discover -s reference/tests -t reference` - the full suite is unchanged in content; the only new modules are the two above.

## Phase 3: validation and governance (LD7)

### Affected Files

- `docs/CONTRIBUTOR_ARCHITECTURE.md` - CI estate paragraph
- `docs/GOVERNANCE_INDEX.md` - plan row
- `docs/META_LEDGER.md` - implementation entry carrying the measured before/after: check runs on the implementation PR's head (expected 43 fixed pull_request runs plus path-matched jobs and CodeQL; zero push runs) and on its merge commit (42 runs, unchanged), from the GitHub API
- `.qor/roadmaps/north-star-best-in-class/events.jsonl` - `prereq-ci-cost` resolved by pointer to the merge commit

### Changes

Per LD7. The `--report` table and the two check-run counts are the #662 "Required validation" evidence and go into the ledger entry and the #662 comment.

### Unit Tests

- none beyond Phase 2; `qor-logic governance-health --profile skill-entry` and `qor-logic verify-ledger` are the gates.

## Definition of Done

### Deliverable: the estate as data

- **D1**: `data/github-actions-workflow-policy.json` covers all 85 files and `test_github_actions_workflow_policy.py` fails on any YAML that drifts from it, on any push trigger without `branches: [main]`, on any hosted job without a timeout, on any PR/push workflow without concurrency, on a second full-suite job in an unconditional workflow, and on a workflow file with no policy entry.

### Deliverable: Phases 2–4 landed

- **D2**: on the implementation PR's head the GitHub API shows no `push` workflow runs and, among unconditional workflows, exactly one job running the full suite; every job has `timeout-minutes`; 71 PR/push workflows carry `cancel-in-progress: ${{ github.event_name == 'pull_request' }}` and 10 carry `false` with the same group; the merge commit still triggers its 42 post-merge runs.

### Deliverable: measurable and recorded

- **D3**: the inventory's mechanical fields and counts equal the YAML (`sync --check`), the `--report` before/after table and the two check-run counts are in the ledger entry and on #662, and `prereq-ci-cost` is resolved by pointer.

## Feature Inventory Touches

| entry_id | operation | test_path | test_descriptor |
|---|---|---|---|
| n/a (workflows, data, scripts, tests and docs; no `reference/agentmem_ref` module is touched) | n/a-justified | `reference/tests/test_github_actions_workflow_policy.py` | the intended workflow estate as data, enforced against the YAML |

## CI Commands

- `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` — stays `PASS` (no protected change)
- `python -m unittest reference.tests.test_github_actions_workflow_policy reference.tests.test_sync_workflow_inventory` — the policy and sync modules
- `python scripts/sync_workflow_inventory.py --check` — inventory in sync with the YAML
- `python -m unittest discover -s reference/tests -t reference` — the whole suite (runs in `Validate Doctrine Evidence`)
- `qor-logic governance-health --profile skill-entry`
