# FinOps: Development branches, manual qualification, and GitHub Actions budget

**Owner:** #662. **Effective staging plan:** `docs/plan-662-finops-quiet-staging.md`. The canonical workflow policy and inventory are `data/github-actions-workflow-policy.json` and `data/github-actions-workflow-inventory.json`. This page is operational guidance, **not** a release exemption or an assertion of saved billed minutes.

## Routine development

1. Work on an **unopened, non-`main` staging branch**. The recorded workflow policy prohibits push triggers outside `main`. Merely pushing that branch does not start the PR- or main-push-triggered workflow estate.
2. Do not create the PR prematurely. **Creating a PR is the qualification event** that will launch the broad protected suite, currently 35 unfiltered workflows after the six-lane manual conversion.
3. Run focused unit, integration and mutation tests on the local checkout or an independently authorized local Claude session. Include the same Python/runtime dependencies and pinned source revision where evidence matters. Use the existing repository smoke/gate scripts instead of remote hosted CI for diagnosis.
4. Accumulate changes and run a local preflight on the **final** staged revision: `python -m unittest discover -s reference/tests -t reference -p 'test_github_actions_workflow_policy.py' -v`; `python scripts/sync_workflow_inventory.py --check`; `python scripts/sync_workflow_inventory.py --finops-report`; the full reference tests; and relevant benchmark-specific qualification if they are affected.
5. Review branch-protection status contexts and current billing/remaining budget before opening a PR. Where an external capability needs an authoritative GitHub workflow artifact, run a **deliberate** `workflow_dispatch` exactly once on an approved branch revision, with the executing SHA recorded.
6. Open one coherent PR for review; check which workflows started and why. Fix findings locally before the next deliberate update. Do not use GitHub-hosted Actions as an iterative test runner.

This is a **development workflow policy**, not a claim that a local passing suite satisfies every provider/model, platform, release or audit obligation. An authorized release still requires whichever protected evidence is mandated by that tranche.

## Six discretionary qualification workloads

| Workflow | Why automatic PR/main execution was wasteful | Minimum intent for deliberate qualification |
| --- | --- | --- |
| `long-horizon-memory-benchmark.yml` | Runs local representations **and** a separate pinned V-JEPA model/source download | Long-history representation, keyed rebinding, staleness, and memory-horizon changes; retain both job artifacts |
| `memory-metabolism-benchmark.yml` | Re-runs lifecycle/unit suites in the required umbrella and produces separate measured latency/evidence | Metabolism, consolidation, pruning, retention and maintenance behavior changes |
| `operational-memory-benchmark.yml` | Runs local representations **and** an isolated V-JEPA comparator job | Failure memory, operational trajectories or representation changes; retain both artifacts |
| `precedent-candidate-retrieval.yml` | Re-runs precedent tests already included by doctrine and re-emits benchmark evidence | Precedent retrieval, applicability and scope/negative-precedent changes |
| `retrieval-quality-benchmark.yml` | Runs retrieval and synthetic SWE-context regression suites again, plus repeat/restart benchmark evidence | Candidate generation, ranking, admission, retrieval routes and SWE-context feature work |
| `semantic-representation.yml` | Pinned ONNX model download/inference is expensive and may be unavailable in regular local suites | Provider/model/digest/embedding/semantic store/facade changes. **Mandatory model-required (no skips) qualification before declaring semantic route ready.** |

The six workflows retain the same job IDs, steps, source/model pins, metrics, evidence checks, artifacts, timeouts, permissions and workflow names. Only their triggers changed to `workflow_dispatch`. The goal is to prevent **routine repetition**, not suppress the benchmark or its obligation. An author/reviewer cannot claim an affected capability is qualified based solely on an ordinary PR's green doctrine check.

## Three research post-merge duplicates eliminated

The following `async_assurance`, `discretionary` workflows remain **path-scoped PR validation** and `workflow_dispatch` qualification, but no longer duplicate it on a `main` push:

- `atlas-research-intake.yml`: preserves exact pinned-source checkout, synthesis/scaffold validations, hash evidence and 30-day artifact.
- `evolveai-multicapability-qualification.yml`: preserves exact EvolveAI source rights, native deletion, public-facade qualifications, normalizer and unavailable-provider negatives. Removes a second execution of the full Agent Memory reference suite already run in protected doctrine CI.
- `hermes-recursive-learning-research.yml`: preserves pinned-source checks, mutation-path negative controls and 30-day research evidence.

These removals save up to three redundant **main-push workflow starts** for commits that match the original path triggers. They do not remove protected check names or claim that a PR-head artifact qualifies a different merged SHA.

## Artifact custody and reproducibility

Routine discretionary benchmark reports from `long-horizon-memory`, `memory-metabolism`, `operational-memory`, `precedent-candidate-retrieval`, and `retrieval-quality` now have 30-day retention. Exact-head component and Hindsight qualification artifacts have 90-day retention. Every explicit duration is reflected in the authoritative inventory, and the inventory sync derives missing-step counts from workflow source. Neither retention policy changes historical artifacts retroactively nor replaces a required durable evidence archive.

All 43 workflows still missing explicit upload retention are classified as protected. Their 50 affected upload steps are **intentionally held**, with no duration guessed. See `docs/75-finops-protected-artifacts-and-closeout-review.md` for the unmerged review matrix.

## What this does and does not save

Before the bounded changes: **41** always-triggered PR workflows, **81** possible PR workflows, and **50** main-push workflows. Staged outcome: **35** always-triggered PR workflows, **75** possible PR workflows, and **41** main-push workflows, with the same 86 top-level workflow names. Six workflows' historical automatic PR and main-push starts have been replaced by deliberate dispatch; three more research/qualification workflows retain path-scoped PR checks but lose duplicate `main`-push execution. One redundant EvolveAI full-reference-suite pass has also been removed. Forty other PR workflows remain path-scoped. The observed number of runner minutes saved will be different from 6 times a fixed duration and is **not available from this connector**.

Run `python scripts/sync_workflow_inventory.py --finops-report` to generate a deterministic, non-billing configuration report. It does not know runner billing, free-tier benefits, OS multipliers, real duration, caching, cancellations or authorized release frequency. Billing in GitHub Settings remains the authoritative source.

## Critical remaining controls and hazards

- Protected `required_hot_path` / `conditional_hot_path` workflows are **not** converted to manual. Some deliver mandatory merge/release security, schema and provenance evidence, and branch-protection requirements have not been read via this connector.
- Six inventory-listed one-time retirement candidates are still classified `protected`; no deletion/retirement is justified without checking their final citations, status contexts and release obligations.
- A previous draft, PR **#767**, introduced a **new** `candidate-trust-state-qualification.yml` top-level workflow even though its tests were already included in the protected doctrine full reference suite. This must be **consolidated/removed in the #767 integration PR before merge**, together with its policy and inventory entry, or separately justified as a nonredundant requirement. Do **not** push iterative changes directly to #767's current PR branch.
- Open draft PRs #763–#768 are **not merged**. Their evidence and head dependencies must be reviewed/rebased intentionally; do not close them merely to make the list tidy.
- Ten discretionary artifact upload steps now explicitly retain results for 30 or 90 days; no protected artifact retention was changed. A full review of all 86 YAMLs found **50 remaining upload steps across 43 protected workflows** with no explicit retention. The previous summary was stale and undercounted the baseline, so the number 50 cannot be presented as no progress. Source matching also corrected `semantic-representation.yml`'s falsely positive `producesArtifacts` field. Protected evidence requires citation/retention authorization before adjustment.
- Existing `main`-only push runs are integration/release boundary candidates, **not automatically waste**. Deduplication of protected post-merge runs requires separate source/identity and branch-protection evidence.
- Until authoritative billed minutes are read and an approved clean usage baseline exists, #662's 1,000-minute target and 2,000-minute exception band remain provisional; do not impose an unreviewed spend stop that disables security release checks.

## Proof required before cost claims

A future invoice/usage report must capture dates, repository, workflow/job, runner class, billed minutes, successful/cancelled/failed, PR vs main vs manual event, artifact storage, cache and budget class. Compare a clean period **after** workflow consolidation to an equivalently active prior period. Saved *potential* runs and charged minutes are different measurements.
