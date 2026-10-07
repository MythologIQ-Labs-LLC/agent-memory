"""The intended GitHub Actions estate is data; the YAML must match it (#662 Phases 2-4).

``data/github-actions-workflow-policy.json`` is the single statement of intent: triggers,
concurrency, per-job timeouts and full-suite passes for every workflow file. This test derives
the same shape from the YAML and refuses any drift, plus three estate-wide invariants. It is a
pure function of the committed files; nothing here reads run history or conclusions.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sync_workflow_inventory as estate  # noqa: E402

POLICY_PATH = REPO_ROOT / estate.POLICY
UMBRELLA = ("validate-doctrine-evidence.yml", "validate")

# Phase 1 of docs/plan-662-ci-cost-phases-2-4.md: the files and jobs that violate invariants
# (i)-(iii) in today's estate, visible before they are enforced. Phase 2 empties every list.
EXPECTED_FAILURES = {
    "push_without_main": """
        agent-manifest-external-evidence.yml architecture-family-closeout.yml authority-laundering-evidence.yml autonomous-maintenance-evidence.yml
        capability-behavior-contract.yml cedar-policy-comparator.yml cli-doctor.yml cmcp-external-evidence.yml conditional-memory-evidence.yml
        conditional-memory-influence.yml config-bound-recovery.yml derivation-currentness-evidence.yml derivation-output-custody.yml
        domain-schema-discovery-evidence.yml domain-schema-mutation-contract.yml external-evidence-contract.yml langgraph-lifecycle-comparator.yml
        long-horizon-memory-benchmark.yml maf-lifecycle-comparator.yml maintenance-evidence.yml memory-metabolism-benchmark.yml
        opa-policy-comparator.yml operational-memory-benchmark.yml p9-systems-characterization.yml policy-projection-compatibility.yml
        precedent-candidate-retrieval.yml provider-discovery.yml restart-safe-runtime.yml retrieval-quality-benchmark.yml
        reusable-grant-authority-transition.yml runtime-baseline.yml runtime-composition.yml runtime-configuration.yml sleeper-poisoning-evidence.yml
        sqlite-production-substrate.yml structural-mutation-governance.yml temporal-commitment-evidence.yml unsafe-composition-evidence.yml
        uor-addr-compatibility.yml validate-doctrine-evidence.yml write-readable-visibility.yml
    """.split(),
    "jobs_without_timeout": """
        agent-manifest-external-evidence.yml/agent-manifest-external-evidence agent-memory-runtime-adapter.yml/runtime-adapter
        agmi-agent-memory-qualification.yml/reproduce-external-row architecture-family-closeout.yml/architecture-family-closeout
        atlas-research-intake.yml/pinned-atlas-intake authority-laundering-evidence.yml/authority-laundering
        autonomous-maintenance-evidence.yml/autonomous-maintenance benchmark-integration-contract.yml/contributor-contracts
        canonical-json-v2-migration-contract.yml/validate-contract canonical-json-v2-migration-preflight.yml/preflight
        canonical-json-v2-parity.yml/python-candidate canonical-json-v2-parity.yml/rust-candidate
        canonical-json-v2-transaction-qualification.yml/qualify canonical-json-v2-vector-acceptance.yml/validate-acceptance
        canonical-json-v2-vector-integrity.yml/validate-vectors canonical-reachability.yml/qualify canonical-scheme-registry.yml/qualify
        canonical-surface-inventory.yml/inventory capability-behavior-contract.yml/validate cedar-policy-comparator.yml/cedar-policy-comparator
        cli-doctor.yml/validate cmcp-external-evidence.yml/cmcp-external-evidence codegenome-multicapability-profile.yml/validate-profile
        codegenome-reality-mesh-evidence.yml/codegenome-reality-mesh codegenome-scope-residue-closeout.yml/closeout
        cognitive-mesh-evidence.yml/cognitive-mesh-evidence component-qualification-evidence.yml/qualify-code-graph
        component-qualification-foundation.yml/qualification-foundation conditional-memory-evidence.yml/conditional-memory
        conditional-memory-influence.yml/validate config-bound-recovery.yml/acceptance dashclaw-external-verdict.yml/provider-proof
        derivation-currentness-evidence.yml/derivation-currentness derivation-output-custody.yml/derivation-output-custody
        domain-schema-discovery-evidence.yml/domain-schema-discovery domain-schema-mutation-contract.yml/domain-schema-mutation
        enforce-issue-labels.yml/ensure-label evolveai-cognitive-mesh-evidence.yml/evolveai-cognitive-mesh
        evolveai-multicapability-qualification.yml/qualify-evolveai external-evidence-contract.yml/external-evidence-contract
        gauntlet-durability-recovery.yml/durability-recovery-alpha gauntlet-external-contestant-dogfood.yml/public-quickstart
        hermes-observe-govern-integration.yml/hermes-integration hermes-recursive-learning-research.yml/verify-hermes-research
        langgraph-lifecycle-comparator.yml/langgraph-lifecycle logical-state-algebra-pressure.yml/logical-state-algebra-pressure
        long-horizon-memory-benchmark.yml/local-representations long-horizon-memory-benchmark.yml/vjepa2-1-frozen-representation
        maf-lifecycle-comparator.yml/maf-lifecycle maintenance-evidence.yml/validate memory-component-program-closeout.yml/validate-closeout
        memory-metabolism-benchmark.yml/native-memory-metabolism opa-policy-comparator.yml/opa-policy-comparator
        operational-memory-benchmark.yml/local-representations operational-memory-benchmark.yml/vjepa2-1-frozen-representation
        p9-systems-characterization.yml/characterize policy-projection-compatibility.yml/compatibility precedent-candidate-retrieval.yml/validate
        procedural-memory-evidence.yml/procedural-memory-evidence provider-discovery.yml/validate publish-wiki.yml/publish
        restart-safe-runtime.yml/acceptance retrieval-quality-benchmark.yml/rc-retrieval-quality
        reusable-grant-authority-transition.yml/reusable-grant-authority-transition runtime-baseline.yml/validate runtime-composition.yml/compose
        runtime-configuration.yml/validate rust-shadow-kernel.yml/qualify seal-anchors.yml/verify sleeper-poisoning-evidence.yml/sleeper-poisoning
        sqlite-production-substrate.yml/qualification structural-mutation-governance.yml/validate temporal-commitment-evidence.yml/temporal-commitment
        unsafe-composition-evidence.yml/unsafe-composition uor-addr-compatibility.yml/uor-addr-compatibility validate-doctrine-evidence.yml/validate
        write-readable-visibility.yml/characterize
    """.split(),
    "without_concurrency": """
        agent-manifest-external-evidence.yml agent-memory-runtime-adapter.yml agmi-agent-memory-qualification.yml architecture-family-closeout.yml
        atlas-research-intake.yml authority-laundering-evidence.yml autonomous-maintenance-evidence.yml benchmark-integration-contract.yml
        canonical-json-v2-migration-contract.yml canonical-json-v2-migration-preflight.yml canonical-json-v2-parity.yml
        canonical-json-v2-transaction-qualification.yml canonical-json-v2-vector-acceptance.yml canonical-json-v2-vector-integrity.yml
        canonical-reachability.yml canonical-scheme-registry.yml canonical-surface-inventory.yml capability-behavior-contract.yml
        cedar-policy-comparator.yml cli-doctor.yml cmcp-external-evidence.yml codegenome-multicapability-profile.yml
        codegenome-reality-mesh-evidence.yml codegenome-scope-residue-closeout.yml cognitive-mesh-evidence.yml component-qualification-evidence.yml
        component-qualification-foundation.yml conditional-memory-evidence.yml conditional-memory-influence.yml config-bound-recovery.yml
        dashclaw-external-verdict.yml derivation-currentness-evidence.yml derivation-output-custody.yml domain-schema-discovery-evidence.yml
        domain-schema-mutation-contract.yml evolveai-cognitive-mesh-evidence.yml evolveai-multicapability-qualification.yml
        external-evidence-contract.yml federated-resource-exchange.yml gauntlet-durability-recovery.yml gauntlet-external-contestant-dogfood.yml
        hermes-observe-govern-integration.yml hermes-recursive-learning-research.yml hindsight-v090-qualification.yml
        langgraph-lifecycle-comparator.yml logical-state-algebra-pressure.yml long-horizon-memory-benchmark.yml maf-lifecycle-comparator.yml
        maintenance-evidence.yml memory-component-program-closeout.yml memory-metabolism-benchmark.yml memos-v2017-substitution.yml
        opa-policy-comparator.yml operational-memory-benchmark.yml p9-systems-characterization.yml policy-projection-compatibility.yml
        precedent-candidate-retrieval.yml procedural-memory-evidence.yml proposition-semantics-score.yml provider-discovery.yml publish-wiki.yml
        recall-validation-characterization.yml recall-validation-external-replay.yml restart-safe-runtime.yml retrieval-quality-benchmark.yml
        reusable-grant-authority-transition.yml runtime-baseline.yml runtime-composition.yml runtime-configuration.yml rust-prefilter-performance.yml
        rust-shadow-kernel.yml seal-anchors.yml sleeper-poisoning-evidence.yml sqlite-production-substrate.yml structural-mutation-governance.yml
        temporal-commitment-evidence.yml temporal-currentness-final-replay.yml unsafe-composition-evidence.yml uor-addr-compatibility.yml
        validate-doctrine-evidence.yml write-readable-visibility.yml
    """.split(),
    "extra_full_suite_jobs": """
        capability-behavior-contract.yml/validate cli-doctor.yml/validate config-bound-recovery.yml/acceptance provider-discovery.yml/validate
        restart-safe-runtime.yml/acceptance runtime-composition.yml/compose runtime-configuration.yml/validate
        structural-mutation-governance.yml/validate write-readable-visibility.yml/characterize
    """.split(),
}


def policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


class WorkflowPolicyTests(unittest.TestCase):
    def test_policy_matches_the_workflow_yaml(self):
        declared = policy()
        derived = estate.derive_policy(REPO_ROOT)
        self.assertEqual(sorted(declared["workflows"]), sorted(derived["workflows"]), "every workflow file needs a policy entry and vice versa")
        self.assertEqual(declared["concurrency_group"], estate.CONCURRENCY_GROUP)
        for name, entry in derived["workflows"].items():
            self.assertEqual(declared["workflows"][name], entry, name)

    def test_no_push_trigger_without_branches_main(self):
        offenders = sorted(name for name, entry in policy()["workflows"].items() if entry["push"] not in (None, "main", "main_paths"))
        self.assertEqual(offenders, EXPECTED_FAILURES["push_without_main"], "a push trigger must be restricted to main (#662 Phase 4)")

    def test_every_hosted_job_has_a_timeout(self):
        offenders = sorted(f"{name}/{job}" for name, entry in policy()["workflows"].items() for job, shape in entry["jobs"].items() if shape["timeout_minutes"] is None)
        self.assertEqual(offenders, EXPECTED_FAILURES["jobs_without_timeout"], "every hosted job carries a measured timeout (#662 Phase 3)")

    def test_every_pr_or_push_workflow_declares_concurrency(self):
        offenders = sorted(
            name
            for name, entry in policy()["workflows"].items()
            if (entry["pull_request"] or entry["push"]) and entry["concurrency"] not in ("cancel_superseded", "complete_every_run")
        )
        self.assertEqual(offenders, EXPECTED_FAILURES["without_concurrency"], "every supersedable workflow cancels or queues (#662 Phase 2)")

    def test_the_unconditional_pr_path_runs_the_full_suite_exactly_once(self):
        unconditional = []
        filtered = []
        for name, entry in policy()["workflows"].items():
            for job, shape in entry["jobs"].items():
                if shape["full_suite_passes"] == 0:
                    continue
                (unconditional if entry["pull_request"] == "unfiltered" else filtered).append((name, job))
        extra = sorted(f"{name}/{job}" for name, job in unconditional if (name, job) != UMBRELLA)
        self.assertIn(UMBRELLA, unconditional)
        self.assertEqual(extra, EXPECTED_FAILURES["extra_full_suite_jobs"], "only the required umbrella job runs the whole suite on every PR")
        self.assertEqual(policy()["workflows"][UMBRELLA[0]]["jobs"][UMBRELLA[1]]["full_suite_passes"], 2)
        for name, _job in filtered:
            self.assertEqual(policy()["workflows"][name]["pull_request"], "paths", f"{name} runs the full suite and must be path-filtered")

    def test_complete_every_run_workflows_are_the_cited_set(self):
        # OQ2 of the plan: the PR/push workflows whose runs are cited by run id in committed
        # records, plus the publication workflow and the dispatch-only lanes.
        expected = {
            "agmi-agent-memory-qualification.yml",
            "amb-competitive.yml",
            "amb-evidence-import.yml",
            "canonical-json-v2-vector-integrity.yml",
            "gauntlet-external-contestant-dogfood.yml",
            "hindsight-v090-qualification.yml",
            "longmemeval-competitive.yml",
            "memos-v2017-substitution.yml",
            "proposition-semantics-score.yml",
            "publish-wiki.yml",
            "runtime-baseline.yml",
            "rust-shadow-kernel.yml",
            "temporal-currentness-final-replay.yml",
        }
        actual = {name for name, entry in policy()["workflows"].items() if entry["concurrency"] == "complete_every_run"}
        pending = set(EXPECTED_FAILURES["without_concurrency"])
        self.assertEqual(actual, expected - pending)

    def test_inventory_mechanical_fields_follow_the_yaml(self):
        inventory = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        self.assertEqual(estate.sync_inventory(inventory, REPO_ROOT), inventory, "run scripts/sync_workflow_inventory.py --write")


if __name__ == "__main__":
    unittest.main()
