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
from unittest.mock import patch

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

    def test_finops_discretionary_benchmarks_are_deliberate_dispatch_only(self):
        # #662: protected reference safety remains in the doctrine umbrella;
        # these six expensive comparative/measurement workflows are invoked
        # deliberately at one reviewed SHA, not on each incremental commit.
        manual = {
            "long-horizon-memory-benchmark.yml",
            "memory-metabolism-benchmark.yml",
            "operational-memory-benchmark.yml",
            "precedent-candidate-retrieval.yml",
            "retrieval-quality-benchmark.yml",
            "semantic-representation.yml",
        }
        policy_workflows = policy()["workflows"]
        inventory = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        records = {item["path"].split("/")[-1]: item for item in inventory["records"]}
        for name in sorted(manual):
            workflow = policy_workflows[name]
            with self.subTest(name=name):
                self.assertIsNone(workflow["pull_request"])
                self.assertIsNone(workflow["push"])
                self.assertEqual(workflow["other_triggers"], ["workflow_dispatch"])
                self.assertEqual(records[name]["lifecycleClass"], "async_assurance")
                self.assertEqual(records[name]["consequenceClass"], "discretionary")
                self.assertEqual(records[name]["proposedDisposition"], "ASYNC")
                self.assertGreater(len(workflow["jobs"]), 0)
                self.assertTrue(all(job["timeout_minutes"] is not None
                                    for job in workflow["jobs"].values()))
        self.assertEqual(policy_workflows["validate-doctrine-evidence.yml"][
            "pull_request"], "unfiltered")

    def test_discretionary_research_keeps_pr_gate_but_drops_repeated_main_push(self):
        names = (
            "atlas-research-intake.yml",
            "evolveai-multicapability-qualification.yml",
            "hermes-recursive-learning-research.yml",
        )
        rows = policy()["workflows"]
        for name in names:
            with self.subTest(workflow=name):
                self.assertEqual(rows[name]["pull_request"], "paths")
                self.assertIsNone(rows[name]["push"])
                self.assertIn("workflow_dispatch", rows[name]["other_triggers"])
        self.assertEqual(rows["evolveai-multicapability-qualification.yml"][
            "jobs"]["qualify-evolveai"]["full_suite_passes"], 0)

    def test_retention_is_explicit_only_for_classified_discretionary_evidence(self):
        review = {
            "long-horizon-memory-benchmark.yml": 30,
            "memory-metabolism-benchmark.yml": 30,
            "operational-memory-benchmark.yml": 30,
            "precedent-candidate-retrieval.yml": 30,
            "retrieval-quality-benchmark.yml": 30,
            "component-qualification-evidence.yml": 90,
            "hindsight-v090-qualification.yml": 90,
        }
        data = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        rows = {row["path"].split("/")[-1]: row for row in data["records"]}
        for name, days in review.items():
            with self.subTest(workflow=name):
                record = rows[name]
                self.assertEqual(record["consequenceClass"], "discretionary")
                self.assertEqual(record["artifactState"]["retentionDays"], [days])
                workflow = estate.load_workflow(
                    REPO_ROOT / estate.WORKFLOWS / name
                )
                artifact, missing = estate.artifact_retention_fields(workflow)
                self.assertEqual(missing, 0)
                self.assertEqual(artifact["retentionDays"], [days])
        self.assertEqual(data["inventorySummary"][
            "artifactUploadWithoutExplicitRetentionCount"], 50)

    def test_uncapped_artifacts_are_protected_evidence_pending_explicit_review(self):
        inventory = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        pending = [
            row for row in inventory["records"]
            if row["artifactState"]["producesArtifacts"]
            and not row["artifactState"]["retentionDays"]
        ]
        self.assertEqual(len(pending), 43)
        self.assertTrue(all(row["consequenceClass"] == "protected"
                            for row in pending))
        self.assertEqual(inventory["inventorySummary"][
            "artifactUploadWithoutExplicitRetentionCount"], 50)
        semantic = next(row for row in inventory["records"]
                        if row["path"].endswith("/semantic-representation.yml"))
        self.assertFalse(semantic["artifactState"]["producesArtifacts"])

    def test_upload_retention_audit_counts_steps_without_deleting_evidence(self):
        synthetic = {
            "jobs": {
                "evidence": {
                    "steps": [
                        {"uses": "actions/checkout@v7"},
                        {"uses": "actions/upload-artifact@v7",
                         "with": {"retention-days": 7}},
                        {"uses": "actions/upload-artifact@v7",
                         "with": {"path": "protected-evidence.json"}},
                    ]
                },
            },
        }
        evidence, missing = estate.artifact_retention_fields(synthetic)
        self.assertEqual(evidence, {"producesArtifacts": True,
                                    "retentionDays": [7]})
        self.assertEqual(missing, 1)
        empty, missing = estate.artifact_retention_fields(
            {"jobs": {"none": {"steps": [{"uses": "actions/checkout@v7"}]}}}
        )
        self.assertEqual(empty, {"producesArtifacts": False,
                                 "retentionDays": []})
        self.assertEqual(missing, 0)
        synthetic["jobs"]["evidence"]["steps"][1]["with"]["retention-days"] = 0
        with self.assertRaisesRegex(ValueError, "retention-days"):
            estate.artifact_retention_fields(synthetic)
        synthetic["jobs"]["evidence"]["steps"][1]["with"]["retention-days"] = 400
        bounded, missing = estate.artifact_retention_fields(synthetic)
        self.assertEqual(bounded["retentionDays"], [400])
        self.assertEqual(missing, 1)

    def test_protected_artifact_exceptions_match_exact_sources(self):
        inventory = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        registry = json.loads(
            (REPO_ROOT / estate.RETENTION_EXCEPTIONS).read_text(encoding="utf-8")
        )
        result = estate.verify_retention_exceptions(REPO_ROOT, inventory, registry)
        self.assertEqual(result["unbounded_upload_steps"], 50)
        self.assertEqual(result["protected_workflows"], 43)
        self.assertEqual(result["unbounded_discretionary_upload_steps"], 0)
        self.assertEqual(result["authorized_deletions"], 0)
        self.assertEqual(result["approved_retention_policy_changes"], 0)
        self.assertFalse(result["billing_minutes_known"])

    def test_protected_retention_register_cannot_grant_authority(self):
        inventory = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        registry = json.loads(
            (REPO_ROOT / estate.RETENTION_EXCEPTIONS).read_text(encoding="utf-8")
        )
        registry["upload_step_exceptions"][0]["retention_authorized"] = True
        with self.assertRaisesRegex(ValueError, "unreviewed retention"):
            estate.verify_retention_exceptions(REPO_ROOT, inventory, registry)
        registry["upload_step_exceptions"][0]["retention_authorized"] = False
        registry["rules"]["new_unbounded_discretionary_uploads_allowed"] = True
        with self.assertRaisesRegex(ValueError, "stop lines"):
            estate.verify_retention_exceptions(REPO_ROOT, inventory, registry)

    def test_new_protected_retention_exception_requires_source_review(self):
        inventory = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        registry = json.loads(
            (REPO_ROOT / estate.RETENTION_EXCEPTIONS).read_text(encoding="utf-8")
        )
        removed = registry["upload_step_exceptions"].pop()
        with self.assertRaisesRegex(ValueError, "unreviewed retention"):
            estate.verify_retention_exceptions(REPO_ROOT, inventory, registry)
        registry["upload_step_exceptions"].append(removed)
        inventory["inventorySummary"]["artifactUploadWithoutExplicitRetentionCount"] -= 1
        with self.assertRaisesRegex(ValueError, "step count"):
            estate.verify_retention_exceptions(REPO_ROOT, inventory, registry)

    def test_uncapped_artifact_cannot_be_discretionary(self):
        inventory = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        registry = json.loads(
            (REPO_ROOT / estate.RETENTION_EXCEPTIONS).read_text(encoding="utf-8")
        )
        first = registry["upload_step_exceptions"][0]["workflow"]
        next(row for row in inventory["records"]
             if row["path"].endswith("/" + first))["consequenceClass"] = "discretionary"
        with self.assertRaisesRegex(ValueError, "discretionary artifact"):
            estate.verify_retention_exceptions(REPO_ROOT, inventory, registry)

    def test_one_time_retirement_candidates_are_not_deleted_without_review(self):
        # #662: inventory intent to RETIRE is not authority to remove a
        # protected status context or its accepted run/artifact evidence.
        inventory = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        pending = [r for r in inventory["records"]
                   if r["proposedDisposition"] == "RETIRE"]
        expected = {
            "architecture-family-closeout.yml",
            "canonical-json-v2-migration-contract.yml",
            "canonical-json-v2-migration-preflight.yml",
            "codegenome-scope-residue-closeout.yml",
            "memory-component-program-closeout.yml",
            "temporal-currentness-final-replay.yml",
        }
        self.assertEqual(
            {r["path"].split("/")[-1] for r in pending}, expected
        )
        self.assertTrue(all(r["consequenceClass"] == "protected" for r in pending))
        self.assertTrue(expected <= set(policy()["workflows"]))
        self.assertTrue(all(r["retirementOrReviewCondition"] for r in pending))

    def test_candidate_trust_regressions_reuse_the_protected_doctrine_umbrella(self):
        # Prevent recurrence of the #767 separate top-level workflow; the
        # governed reference test suite is already discovered by doctrine CI.
        self.assertNotIn(
            "candidate-trust-state-qualification.yml", policy()["workflows"]
        )
        doctrine_path = REPO_ROOT / ".github/workflows/validate-doctrine-evidence.yml"
        body = doctrine_path.read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s reference/tests -t reference", body)

    def test_finops_trigger_envelope_cannot_make_a_billing_claim(self):
        envelope = estate.trigger_budget_envelope(policy())
        self.assertIsNone(envelope["authoritative_billing_minutes"])
        self.assertIsNone(envelope["calculated_dollar_savings"])
        self.assertEqual(envelope["unfiltered_pr_workflow_starts_per_head"], 35)
        self.assertEqual(envelope["potential_path_scoped_pr_workflows_per_head"], 40)
        self.assertEqual(envelope["main_push_workflows"], 41)
        self.assertEqual(envelope["potential_all_pr_workflows_per_head"], 75)
        self.assertEqual(len(
            envelope["discretionary_benchmarks_not_automatically_triggered"]
        ), 6)
        self.assertIn("validate-doctrine-evidence.yml",
                      envelope["unfiltered_pr_workflow_names"])
        self.assertEqual(envelope["provenance"],
                         "committed_workflow_configuration_only")

    def test_inventory_write_refuses_unreviewed_protected_uploads(self):
        # An inventory rewrite cannot launder a newly uncapped artifact into
        # the canonical metadata before its custody exception is reviewed.
        with patch.object(estate, "verify_retention_exceptions",
                          side_effect=ValueError("synthetic uncapped upload")), \
             patch.object(estate, "dump") as dump:
            self.assertEqual(
                estate.main(["--root", str(REPO_ROOT), "--write"]), 1
            )
            dump.assert_not_called()

    def test_inventory_mechanical_fields_follow_the_yaml(self):
        inventory = json.loads((REPO_ROOT / estate.INVENTORY).read_text(encoding="utf-8"))
        self.assertEqual(estate.sync_inventory(inventory, REPO_ROOT), inventory, "run scripts/sync_workflow_inventory.py --write")


if __name__ == "__main__":
    unittest.main()
