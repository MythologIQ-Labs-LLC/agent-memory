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

# Invariants (i)-(iii) hold unconditionally since Phase 2 of docs/plan-662-ci-cost-phases-2-4.md;
# a future estate change that must land in steps lists its files here, and empties the lists again.
EXPECTED_FAILURES: dict[str, list[str]] = {
    "push_without_main": [],
    "jobs_without_timeout": [],
    "without_concurrency": [],
    "extra_full_suite_jobs": [],
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
            "currentness-extractor-smoke.yml",
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
