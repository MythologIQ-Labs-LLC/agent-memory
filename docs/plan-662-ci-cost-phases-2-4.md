# Plan: #662 Phases 2–4 as one evaluation-only change (roadmap `prereq-ci-cost`)

**Status**: iteration 1 (2026-10-07), awaiting Gate Tribunal
**Issue**: #662 (FinOps + CI architecture; parent `Myth-Tech-Forge#482`); roadmap scope `scope-prereq-ci-cost-plan`, whose merged outcome resolves `prereq-ci-cost` in `scope-tranche-6-rebalance`
**Research**: `docs/research-brief-tranche-5-harvests-and-ci-cost-2026-10-07.md` finding E (Entry #74); measurements on PR heads e20c70d, 8e1211e, a370285 and merge commits a5c6de3, b7f6bd2
**Predecessor artifact**: `.qor/gates/2026-10-06T1200-668ns/research-iter2.json`

- purpose: a PR head stops triggering the 41 `push` runs that duplicate its `pull_request` runs, every hosted job carries a measured timeout, every supersedable PR workflow cancels its stale run, and the full reference suite runs once per trigger instead of eleven times, with the intended state written as data and enforced by one test so the estate cannot drift back.
- limitations: this plan changes triggers, concurrency, timeouts and one redundant step; it changes no benchmark input, scoring, evidence contract, check name or required control (#662 stop lines). Post-merge runs on `main` are kept for every workflow that has them today (Phase 4 names post-merge integration as a legitimate lifecycle boundary), so the 42 runs per merge are unchanged by design. Wall-minutes are run-volume facts, not spend (#662 "Starting evidence"). Phases 5 and 6 (reusable workflows, artifact retention) are out of scope. The protected surface (`pyproject.toml`, `reference/agentmem_ref/**` minus `evaluation/**`) is untouched: `python scripts/check_runtime_baseline_equivalence.py --candidate HEAD` stays `PASS` against Runtime Baseline v2.
- non_goals: retiring any of the 6 `one_time` workflows (that is #662's "retire after evidence review", not a trigger change); moving the 5 discretionary benchmark lanes off the PR path (they cost under 1.2 minutes each and the inventory keeps them `ASYNC` for Phase 5); machine-readable branch protection; a new top-level workflow (#662 Phase 0; the enforcement test runs inside the required `Validate Doctrine Evidence` job's full-suite pass); regenerating the inventory's provisional classification fields (`lifecycleClass`, `consequenceClass`, `proposedDisposition` are reviewed judgments, not derived state).

## Open Questions

1. **Post-merge runs on `main` kept (default taken).** The 40 bare `push:` triggers become `push: branches: [main]`, not a removal. #662 Phase 4 lists "post-merge/main integration" as a boundary that justifies a push run, and the merge commit's tree differs from the PR head's. The alternative, dropping `push` entirely from the 34 `required_hot_path` files, would also remove the 42 runs per merge but leaves `main` with no integration signal after a merge whose base moved; it is not taken here and would be its own Phase 4 slice with the inventory's lifecycle classes as the deciding data.
2. **The complete-every-run set (default taken).** Workflows whose uploaded artifacts are bound by run id into committed records keep every run (`cancel-in-progress: false`, queued by the same group) rather than cancelling a superseded head: `runtime-baseline.yml` (the B2 binding cites a PR-head run, `reports/runtime/baseline-v2-qualification.json`), `gauntlet-external-contestant-dogfood.yml` (`dogfood.workflow_run` in the baseline records), `temporal-currentness-final-replay.yml` (`final_replay_artifact.workflow_run` in `reports/runtime/baseline-v1.json`), `agmi-agent-memory-qualification.yml` and `gauntlet-durability-recovery.yml` (retired contestants whose re-pin two-step will bind a run), `recall-validation-external-replay.yml` (replay evidence under `reports/benchmarks/replays`), and `publish-wiki.yml` (a publication on `main`). Every other PR/push workflow uploads diagnostics that no committed record cites by run id and cancels its superseded run. If the Tribunal reads `seal-anchors.yml` (verification only, no upload) as evidence, it moves into this set; the policy file is the only place that changes.
3. **PR #665 (`finops/discretionary-stale-run-cancel-1`, five discretionary lanes, same group expression as LD4).** This plan carries the identical block for those five files among the 73 it adds, so #665 becomes a strict subset of this change. Default taken: after this plan's PR merges, one comment on #665 states that it is subsumed and names the merge commit; closing it is left to its author.
4. **Timeout tiers (default taken).** Three tiers derived from the 49 measured pull_request jobs on head 8e1211e (every job under 2.5 minutes except `Validate Doctrine Evidence / validate` at 6.1): 10 minutes for a job measured at or below 2.5 minutes, 20 for the umbrella job, 15 for a hosted job that did not run on that head (path-filtered, unmeasured) unless it builds Rust (`cargo` in its setup family), which gets 30; jobs that already declare a timeout keep it. A timeout failure stays distinguishable from a product failure because GitHub reports it as `The job running on runner … has exceeded the maximum execution time`, and the policy test does not read conclusions.

## Locked Decisions

**LD1 — The intended estate is data, enforced by one test.** New `data/github-actions-workflow-policy.json`: `{"schema_version": 1, "governing_issue": "#662", "concurrency_group": "${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}", "full_suite_command": "python -m unittest discover -s reference/tests -t reference", "workflows": {"<file name>": {"pull_request": "unfiltered" | "paths" | null, "push": "main" | "main_paths" | null, "other_triggers": ["workflow_dispatch", ...], "concurrency": "cancel_superseded" | "complete_every_run" | "none", "jobs": {"<job id>": {"timeout_minutes": <int>, "full_suite_passes": <int>}}}}}` with one entry per file under `.github/workflows/` (85). New `reference/tests/test_github_actions_workflow_policy.py` loads every workflow with `yaml.safe_load` (PyYAML pinned in `reference/requirements.txt`; the `on` key parses as the boolean `True`, which the reader normalizes) and derives the same shape: `pull_request` is `"unfiltered"` when the trigger has no `paths`, `"paths"` otherwise; `push` is `"main"` when `branches == ["main"]` and no `paths`, `"main_paths"` with paths, and the test **fails on any push trigger without `branches: [main]`**; `concurrency` is `"cancel_superseded"` when the top-level block has exactly the policy's group and `cancel-in-progress: true`, `"complete_every_run"` with `false`, `"none"` when absent; per job, `timeout_minutes` is the literal `timeout-minutes` (the test fails on a job that runs on a hosted runner without one) and `full_suite_passes` counts `run:` steps whose text contains the policy's `full_suite_command` and no `-p `. The test asserts derived == declared for every file, that the set of files equals the set of policy keys, and three global invariants: (i) no `push` trigger without `branches: [main]`; (ii) exactly one job in the estate declares `full_suite_passes > 0` (`validate-doctrine-evidence.yml` / `validate`, with 2); (iii) every workflow with a `pull_request` or `push` trigger has `concurrency != "none"` except `enforce-issue-labels.yml` (an `issues` trigger). Nothing reads `conclusion`s or run history; the test is a pure function of the YAML.

**LD2 — Phase 4: the bare `push:` becomes `push: branches: [main]` in the 40 files and `runtime-baseline.yml`.** The 40 files (every file whose `on:` is a bare `push:` plus bare `pull_request:` at lines 3–5: agent-manifest-external-evidence, architecture-family-closeout, authority-laundering-evidence, autonomous-maintenance-evidence, capability-behavior-contract, cedar-policy-comparator, cli-doctor, cmcp-external-evidence, conditional-memory-evidence, conditional-memory-influence, config-bound-recovery, derivation-currentness-evidence, derivation-output-custody, domain-schema-discovery-evidence, domain-schema-mutation-contract, external-evidence-contract, langgraph-lifecycle-comparator, long-horizon-memory-benchmark, maf-lifecycle-comparator, maintenance-evidence, memory-metabolism-benchmark, opa-policy-comparator, operational-memory-benchmark, p9-systems-characterization, policy-projection-compatibility, precedent-candidate-retrieval, provider-discovery, restart-safe-runtime, retrieval-quality-benchmark, reusable-grant-authority-transition, runtime-composition, runtime-configuration, sleeper-poisoning-evidence, sqlite-production-substrate, structural-mutation-governance, temporal-commitment-evidence, unsafe-composition-evidence, uor-addr-compatibility, validate-doctrine-evidence, write-readable-visibility) get

```yaml
on:
  push:
    branches: [main]
  pull_request:
```

and `runtime-baseline.yml:4-5` gains `branches: [main]` above its existing `paths:`. Nothing else in the trigger blocks changes; the 8 files already restricted to `main` and the 40 path-filtered PR-only files are untouched. Effect on a PR head: the 43 push jobs (86 → 43 fixed check runs) stop; effect on `main`: unchanged. The `seal-anchors.yml` push on `main` with no paths is already in the kept shape.

**LD3 — Phase 4: the full reference suite runs once per trigger.** The step `Execute full reference regression suite` (or its local name) that runs the unpatterned `python -m unittest discover -s reference/tests -t reference` is deleted from nine workflows: `capability-behavior-contract.yml:28-29`, `cli-doctor.yml:63-64`, `config-bound-recovery.yml:28-29`, `provider-discovery.yml:80-81`, `restart-safe-runtime.yml:28-29`, `runtime-composition.yml:28-29`, `runtime-configuration.yml:28-29`, `structural-mutation-governance.yml:31-32`, `write-readable-visibility.yml:28-29`. Each keeps the targeted step that precedes it (`-p 'test_<module>.py'` or an explicit module), so each still gates its own contract. `validate-doctrine-evidence.yml` keeps both passes (`:38` and `:168`, the second against the optionally installed real substrate) because it is the required check (`docs/ARCHITECTURE_PLAN.md:102`; `docs/programs/runtime-evidence/procedural-memory.md:242`) and the only place the whole suite must hold. Effect per PR head: 22 full-suite passes become 2 (about 18 of the measured 41 pull_request wall-minutes).

**LD4 — Phase 2: one concurrency block on every PR/push workflow.** Each of the 81 workflows with a `pull_request` or `push` trigger (every file except the three dispatch-only lanes, which keep their existing blocks and `cancel-in-progress: false`, and `enforce-issue-labels.yml`) gets, directly after `on:` and before `permissions:`:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true
```

The group keys on the PR number for pull_request events and on the ref for push events, so two PRs never cancel each other and a `main` push never cancels a PR run (#662 "verify branch/PR isolation"). The seven complete-every-run workflows of OQ2 carry the same group with `cancel-in-progress: false`: their runs queue behind each other and none is cancelled, so a superseded run can never be mistaken for accepted evidence and no run that a record may cite is lost. PR #665's five files are inside the 74 that get `true`.

**LD5 — Phase 3: a measured timeout on every hosted job.** Every job without `timeout-minutes` (77 of 90) gets one from the OQ4 tiers; the 13 jobs with an explicit value keep it. Tier 10 (measured ≤ 2.5 min on 8e1211e): the 43 P/PR jobs other than `validate-doctrine-evidence/validate` and `cli-doctor/wheel-install` (already 15), plus the measured PR-only jobs `benchmark-integration-contract/contributor-contracts`, `seal-anchors/verify`, `runtime-baseline/validate`, `gauntlet-external-contestant-dogfood/public-quickstart`, `gauntlet-durability-recovery/durability-recovery-alpha`, `agmi-agent-memory-qualification/reproduce-external-row`. Tier 20: `validate-doctrine-evidence/validate` (6.1 min measured, two full passes plus the comparator install). Tier 15 (unmeasured hosted jobs): the remaining path-filtered jobs (agent-memory-runtime-adapter, atlas-research-intake, the canonical-json-v2-* and canonical-* jobs except Rust ones, canonical-scheme-registry, canonical-surface-inventory, codegenome-*, cognitive-mesh-evidence, component-qualification-*, dashclaw-external-verdict, evolveai-*, hermes-*, logical-state-algebra-pressure, memory-component-program-closeout, procedural-memory-evidence, publish-wiki, enforce-issue-labels). Tier 30 (Rust builds, unmeasured): `canonical-json-v2-parity/rust-candidate`, `rust-shadow-kernel/qualify`. The exact value per job is the policy file's `timeout_minutes`; the YAML carries the same literal. Timeout failures stay distinguishable from evaluator failures (GitHub's own `exceeded the maximum execution time` annotation), and no job's work changes.

**LD6 — The inventory's mechanical fields follow the YAML, by script.** New `scripts/sync_workflow_inventory.py`: for each record in `data/github-actions-workflow-inventory.json` it recomputes `triggers` (event names, sorted), `pathScope` (`"paths"` when any trigger has `paths`, `"branches"` when push is branch-restricted without paths, `"repository-wide-or-unscoped"` otherwise), `timeoutState` (`explicit`, `valuesMinutes` sorted unique) and `concurrencyState` (`configured`, `cancelInProgress`) from the YAML and rewrites `inventorySummary.triggerCounts`, `missingExplicitTimeoutCount` and `supersedablePrOrPushWithoutConcurrencyCount`; `--check` exits 1 when the committed file differs (the policy test calls the same function and asserts no drift); `--report` prints the before/after trigger table #662 "Required validation" asks for (one row per workflow: pull_request, push, concurrency, timeouts) from two revisions (`git show <rev>:<path>`). The provisional judgment fields are never touched. A new top-level `postSnapshotChanges` entry records this plan's change set with the merge commit.

**LD7 — Documentation and governance.** `docs/CONTRIBUTOR_ARCHITECTURE.md` gains a short "CI estate" paragraph (after §8): the policy file is the intended state, the test enforces it, a PR head triggers pull_request runs only, `main` keeps post-merge runs, the full suite runs in the required check only, and a new workflow needs a policy entry (so #662 Phase 0's freeze has a mechanical check: the test fails on a file with no policy entry). `docs/GOVERNANCE_INDEX.md` Tier 4: this plan. One comment on #662 after merge with the `--report` table, the check-run count on the implementation PR's head and on its merge commit, and the PR #665 note (OQ3). The roadmap node `prereq-ci-cost` is resolved by pointer at the merge commit.

## Phase 1: policy data, enforcement test, inventory sync (no workflow behaviour change yet)

### Affected Files

- `reference/tests/test_github_actions_workflow_policy.py` - new; derives the estate from YAML and asserts it equals the policy (LD1) and the inventory sync is clean (LD6); at this phase the policy file describes the **current** estate, so the global invariants (i)–(iii) are declared as `expected_failures` listing the files that violate them, which Phase 2 empties
- `reference/tests/test_sync_workflow_inventory.py` - new; round-trips one synthetic workflow YAML through the sync function and checks `--check`/`--report` on a temporary copy
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
- the 81 PR/push workflows - LD4 concurrency block (74 `true`, 7 `false`)
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

- **D1**: `data/github-actions-workflow-policy.json` covers all 85 files and `test_github_actions_workflow_policy.py` fails on any YAML that drifts from it, on any push trigger without `branches: [main]`, on any hosted job without a timeout, on any PR/push workflow without concurrency, on more than one full-suite job, and on a workflow file with no policy entry.

### Deliverable: Phases 2–4 landed

- **D2**: on the implementation PR's head the GitHub API shows no `push` workflow runs and exactly one job running the unpatterned full suite; every job has `timeout-minutes`; 74 PR/push workflows carry `cancel-in-progress: true` and 7 carry `false` with the same group; the merge commit still triggers its 42 post-merge runs.

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
