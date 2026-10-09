# #662 FinOps — quiet staging and budget-safe benchmark promotion

**Status:** controlled implementation, 2026-10-09. **Base:** `main`. **Execution policy:** this branch has **no open pull request** and repository-wide push triggers are restricted to `main`; stage iterations here without generating PR workflow fan-out. Do not open a PR until local/off-GitHub qualification and a deliberately planned single CI pass.

## Cause and evidence

The October 5 #662 audit recorded 84 workflows, 80 PR hooks, 49 push hooks and 2,500 workflow runs in five days, but **did not measure billed minutes**. Subsequent accepted Phases 2–4 added PR stale-run concurrency cancellation, explicit per-job timeouts, main-only push gates and removed multiple redundant unfiltered full-suite runs. The pre-FinOps main snapshot contains 86 workflows, 41 unfiltered PR gates, 50 main-push gates and 20 async-assurance lanes. The staged outcome is 35 unfiltered PR gates, 75 possible PR gates, 41 main-push gates and 48 manual-dispatch workflows. The protected doctrine umbrella executes the full reference suite on every PR. A non-PR staging branch cannot use GitHub Actions as a test runner and should be qualified locally/through an independently authorized Claude checkout.

## Phase 5A: remove redundant broad automatic benchmark fan-out

The following **six `async_assurance` and `discretionary` inventory classifications** were checked before editing:
- `long-horizon-memory-benchmark.yml`
- `memory-metabolism-benchmark.yml`
- `operational-memory-benchmark.yml`
- `precedent-candidate-retrieval.yml`
- `retrieval-quality-benchmark.yml`
- `semantic-representation.yml`

All six currently trigger on every PR **and** `main` push. Replace both automatic triggers with **explicit `workflow_dispatch` only**, preserving their workflow names, job IDs, implementation steps, pinned source/model, evidence/artifacts, permissions and timeouts. The reference test suite stays in the protected unfiltered doctrine umbrella. The full benchmarks remain available for a consciously authorized release/benchmark qualification at an exact SHA, and a PR that substantively changes the corresponding capability must include a qualified dispatch receipt as an *explicit review obligation*, not fabricate a green check when no benchmark ran.

**Capacity impact per normal PR head:** six fewer workflow *runs* (the long-horizon and operational workflows each contain two jobs). **Per main push:** six fewer runs. This is a trigger count reduction, **not quantified billed minutes or dollar savings**. Exact total savings depend on which workflows used to start and how long they actually ran. Existing path-scoped hot-path safety and required security/release checks remain untouched.

## Before-code adversarial controls

F1. The six named workflows have no automatic `push` or `pull_request` trigger, and retain `workflow_dispatch` with all existing job IDs/steps and workflow names.
F2. No `required_hot_path`, `conditional_hot_path` or `protected` workflow changes trigger, job implementation, status check name or release semantics.
F3. New policy `data/github-actions-workflow-policy.json` matches the YAML under the repository's existing `test_github_actions_workflow_policy.py`.
F4. `data/github-actions-workflow-inventory.json` mechanical fields and summary counts exactly match YAML. Existing lifecycle/authority classifications are preserved, with review reasons explicitly extended for altered discretionary lanes.
F5. No PR auto workflows fire on push to the **unopened staging branch**. Existing push hooks remain main-only.
F6. The 6 deliberate benchmark workflows retain pinned inputs, scripts, evidence validation, output artifact handling and explicit timeouts.
F7. Evidence from a manual benchmark still carries the executing revision; cancellation is not mistaken for accepted evidence.
F8. The baseline register, runtime implementation, benchmark corpora, architecture IDs, scorecards, task suite and frozen holdouts are **unchanged**.
F9. Protected doctrine/test umbrella still runs exactly the allowed full suite; do not replace genuine required security gates with manual-only tests.
F10. CI is a deliberately controlled **final** exact-head qualification; no per-edit PR runs. If required status checks force additional work, make a separately reviewed safe path, never silently disable branch protection.

## Additional cleanup lanes gated by evidence

- Classify **six one-time**/retirement-candidate workflows for retirement only after their run/citation and branch protection dependencies are known. These are currently **protected** and are **not** removed in Phase 5A.
- **Phase 5B implemented:** `atlas-research-intake`, `evolveai-multicapability-qualification`, `hermes-recursive-learning-research` lose **only** duplicate `main` push triggers while retaining path-filtered PR checks and manual dispatch. EvolveAI drops the exact full-reference-suite pass already run by the required doctrine umbrella; its focused source/provider qualification is preserved.
- **Phase 6 bounded discretion:** ten `upload-artifact` steps across seven discretionary benchmark/comparator workflows receive explicit 30-day (routine benchmark) or 90-day (component/Hindsight qualification) retention. The dedicated `semantic-representation` workflow produces no artifact and its incorrect inventory classification was corrected.
- **Source audit corrected a stale counter:** all 86 workflow YAMLs were independently compared to their artifact inventory records. There are **50 remaining upload steps with missing explicit retention in 43 workflows**, and every one of those workflows is `protected`. The prior 50-step count was stale before this change; do not claim it fell to 40. Classify custody, branch protection, release citations and artifact lifetimes before changing those protected jobs.
- Consolidate repeated setup steps by proven compute reduction, not simply shrinking file count.
- Billing authority is unavailable from this connector. The target 1,000 hosted-runner-minutes/month and exception band 2,000 remain **provisional**, not measured spend or an imposed hard cap.

## Local qualification before creating a PR

```sh
python -m unittest discover -s reference/tests -t reference -p 'test_github_actions_workflow_policy.py' -v
python scripts/sync_workflow_inventory.py --check
python -m unittest discover -s reference/tests -t reference -p 'test_*.py'
```

Also run `python scripts/sync_workflow_inventory.py --finops-report` and verify all discretionary upload steps have explicit retention; the remaining 50 protected steps require separate evidence-owner approval. Run these in a local/Claude checkout at the final staged revision. Only then open a single review PR, obtain intentional CI qualification, and compare exact workflow triggers/statuses before merge. Never use Github Actions for debugging repeated edits.
