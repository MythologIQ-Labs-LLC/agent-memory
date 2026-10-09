# #662 — Protected artifact and one-time workflow retirement review

**Status:** risk-ranked review queue; no protected control disabled, 2026-10-09. **Inputs:** `data/github-actions-workflow-inventory.json`, `data/github-actions-workflow-policy.json`, and the exact staged workflow YAMLs. No authoritative billing or branch-protection API access was available through this connection.

## Why these are still open

All **86 workflow files** were source-checked for `actions/upload-artifact` steps and `retention-days`. After establishing 30/90-day durations on ten discretionary upload steps and correcting the semantic-representation misclassification, **50 upload steps across 43 workflow files** still have no explicit retention. All 43 are classified **protected** by the accepted inventory. An upload step with no explicit duration inherits repository/org retention settings, which are unknown here. These are evidence custody/retention decisions, not permission to delete.

Every remaining uncapped upload is now itemized by **workflow, job, upload ordinal, and artifact name** in `data/github-actions-retention-exceptions.json`. All 50 entries are in a `hold` state with `retention_authorized=false`. These entries neither grant permission for indefinite retention nor allow deletion: they are an explicit tracked exception backlog until an evidence owner decides on custody. `scripts/sync_workflow_inventory.py --check` validates exact alignment with the workflow YAML and fails when an uncapped artifact is introduced, removed, renamed or reclassified without reconciling the review record. Use `--retention-exception-report` for a local, non-billing summary.

The separate **six `one_time` / `RETIRE`** candidates are also still protected. Removing their workflows merely because a program closed could invalidate branch-required check names, release citations or evidence replay. None is deleted or converted to manual by this slice.

## One-time retirement candidates: explicit evidence gates

| Workflow | Current automatic triggers | Artifact upload? | Required before retirement |
| --- | --- | --- | --- |
| `architecture-family-closeout.yml` | PR (unfiltered) + main (main) | yes | Verify required status contexts, last accepted evidence pointer and immutable run/artifact citations; preserve local replay command and compare before/after check names |
| `canonical-json-v2-migration-contract.yml` | PR (paths) | no | Verify required status contexts, last accepted evidence pointer and immutable run/artifact citations; preserve local replay command and compare before/after check names |
| `canonical-json-v2-migration-preflight.yml` | PR (paths) | yes | Verify required status contexts, last accepted evidence pointer and immutable run/artifact citations; preserve local replay command and compare before/after check names |
| `codegenome-scope-residue-closeout.yml` | PR (paths) | yes | Verify required status contexts, last accepted evidence pointer and immutable run/artifact citations; preserve local replay command and compare before/after check names |
| `memory-component-program-closeout.yml` | PR (paths) + main (main_paths) | yes | Verify required status contexts, last accepted evidence pointer and immutable run/artifact citations; preserve local replay command and compare before/after check names |
| `temporal-currentness-final-replay.yml` | PR (paths) | yes | Verify required status contexts, last accepted evidence pointer and immutable run/artifact citations; preserve local replay command and compare before/after check names |

**Exit criteria for each retirement:** (1) accepted final outcome and source SHA recorded, (2) exact artifact run/digest retained according to its citation contract, (3) no active branch protection/ruleset/release gate requires its status, (4) its replay semantics are present in durable docs/local tools or a reviewed remaining workflow, (5) local validation shows no uncontrolled authority change, (6) deliberate final GitHub qualification. Until every condition is met, keep the workflow, even if marked `RETIRE`.

## Protected missing-retention work queue

There are **43 workflows** below, representing **50 distinct upload steps**. This table records workflow-level absence only; some workflows contain multiple uploads. A future retention decision must be made **per upload step** and identify whether it is an ephemeral diagnostic, reproduction evidence, benchmark evidence, release/provenance evidence, or security/governance evidence. Storage savings cannot be estimated without artifact sizes and billing.

| Workflow | Lifecycle | Current trigger class | Hold reason |
| --- | --- | --- | --- |
| `agent-manifest-external-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `authority-laundering-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `autonomous-maintenance-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `capability-behavior-contract.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `cedar-policy-comparator.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `cli-doctor.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `cmcp-external-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `conditional-memory-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `config-bound-recovery.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `derivation-currentness-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `domain-schema-discovery-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `external-evidence-contract.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `langgraph-lifecycle-comparator.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `maf-lifecycle-comparator.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `opa-policy-comparator.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `p9-systems-characterization.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `policy-projection-compatibility.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `provider-discovery.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `restart-safe-runtime.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `reusable-grant-authority-transition.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `runtime-composition.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `runtime-configuration.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `sleeper-poisoning-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `sqlite-production-substrate.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `structural-mutation-governance.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `temporal-commitment-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `unsafe-composition-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `uor-addr-compatibility.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `validate-doctrine-evidence.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `write-readable-visibility.yml` | `required_hot_path` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `codegenome-multicapability-profile.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `codegenome-reality-mesh-evidence.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `cognitive-mesh-evidence.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `dashclaw-external-verdict.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `federated-resource-exchange.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `logical-state-algebra-pressure.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `memos-v2017-substitution.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `procedural-memory-evidence.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `recall-validation-characterization.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `recall-validation-external-replay.yml` | `conditional_hot_path` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `architecture-family-closeout.yml` | `one_time` | PR unfiltered; push main | Protected; verify citation / release dependency and required retention before changing upload |
| `codegenome-scope-residue-closeout.yml` | `one_time` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |
| `temporal-currentness-final-replay.yml` | `one_time` | PR paths | Protected; verify citation / release dependency and required retention before changing upload |

## Four validation lanes before implementation

1. **Local source-of-truth check:** `python scripts/sync_workflow_inventory.py --check` must compare every committed workflow with mechanical trigger and upload data, including missing retention counts.
2. **GitHub security/ruleset read:** enumerate branch protections, required status-check contexts, repository rulesets, environments and release artifact dependencies. Existing GitHub connector cannot read all these directly. Unknown means hold, **not** no dependency.
3. **Evidence ownership decision:** each proposed reduction records artifact name, path, provenance/source SHA, retention reason, current allowed retention, actual citation users, whether an immutable copy exists, and a non-destructive migration test. For accepted provenance/evaluation evidence, never select an arbitrary 1–7-day TTL.
4. **Cost verification:** read authoritative Actions minutes and artifact storage from GitHub Billing. Derive measured before/after cost under comparable activity, excluding unscheduled benchmark work. No dollar-savings claim from static run counts.

## Continuation policy

The safe run-cost reduction (six manualized benchmark workflows, three PR/main deduplications, and one redundant full-reference pass eliminated) is committed on `finops/662-quiet-staging-and-benchmark-gates`. It remains an unopened **quiet** branch until independent local tests and a deliberate final CI qualification pass. The separate `finops/767-consolidate-qualification-no-ci` branch removes a redundant new workflow from PR #767 before integration. Neither changes protected runtime/benchmarks, frozen evaluations, authority semantics, or branch protection.

**This document is not evidence that the six retirement candidates are safe to delete.** It makes the unknowns and required proof explicit so the next FinOps changes do not accidentally erase essential evidence.
