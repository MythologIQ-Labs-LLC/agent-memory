"""#786 fail-first public-facade regression: foreign project cannot replace live key head.

This targets the canonical adapter write decision, not an MCP-only mitigation.
The separate deleted-key recreation rule (#776) is intentionally not changed.
Requires a fresh, installed reference runtime and controlled SQLite workdir.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm

TENANT = "tenant:write-target-786"
ACTOR = "agent:write-target-786"
KEY = "memory:gateway-region"


def open_in(root: Path, scope: str):
    return AgentMemory.open(
        root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="786 guarded target replay",
    )


def review_evidence(scope: str):
    """Use the same qualified procedural evidence route as the public facade tests."""
    skill = pm.SkillArtifact(
        skill_id="skill:786-scope-guard",
        version=1,
        purpose="governed lifecycle review for scope regression",
        scope=scope,
        isolation_domain_refs=(TENANT, scope),
        required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# verify\nConfirm the scope owns the live target before mutation.",
        provenance_refs=("evidence:786-independent-source",),
    )
    return pm.evidence_for(skill)


class CrossProjectWriteTargetTests(unittest.TestCase):
    def test_other_project_cannot_replace_owners_live_head(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as owner:
                first = owner.remember(KEY, "Orrin gateway region is Oslo")
                self.assertTrue(first["committed"], first)
                first_ref = first["fact_uuid"]
                self.assertEqual(owner.history(KEY)["history"]["current_fact_uuid"], first_ref)
            with open_in(root, "project:b") as other:
                # v6 and v7 have distinct public history projections.
                # An ordinary history read grants no authority to overwrite.
                other.history(KEY)
                wrong = other.remember(KEY, "Orrin gateway region is Turku")
                self.assertFalse(wrong["committed"], wrong)
                self.assertIsNone(wrong["fact_uuid"])
                # Do not return the owner's ref, project, source or other
                # privileged existence details as a refusal explanation.
                self.assertNotIn(first_ref, repr(wrong))
                self.assertNotIn("Oslo", repr(wrong))
            with open_in(root, "project:a") as reopened:
                self.assertEqual(reopened.history(KEY)["history"]["current_fact_uuid"], first_ref)
                admitted = reopened.recall("Orrin gateway region", logical_memory_refs=(KEY,))
                self.assertIn(first_ref, admitted["admitted"])

    def test_other_project_cannot_forge_owner_scope_in_proposal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as owner:
                initial = owner.remember(KEY, "Orrin gateway region is Oslo")
                self.assertTrue(initial["committed"])
                original = initial["fact_uuid"]
            with open_in(root, "project:b") as other:
                attempted = {
                    "scope": "project:a",
                    "project_ref": "project:a",
                    "isolation_domain_refs": [TENANT, "project:a"],
                    "required_isolation_domain_refs": [TENANT, "project:a"],
                }
                try:
                    forged = other.remember(
                        KEY, "Orrin gateway region is Turku", overrides=attempted,
                    )
                except ValueError:
                    forged = {"committed": False}
                self.assertFalse(forged["committed"], forged)
            with open_in(root, "project:a") as owner:
                self.assertEqual(owner.history(KEY)["history"]["current_fact_uuid"], original)

    def test_identity_override_cannot_forge_task_on_facade(self):
        with tempfile.TemporaryDirectory() as temporary:
            with open_in(Path(temporary), "project:b") as memory:
                with self.assertRaisesRegex(ValueError, "protected fields"):
                    memory.remember(
                        "memory:task-specific", "This task is in progress",
                        overrides={"task_ref": "task:owner"},
                    )

    def test_same_host_identity_override_is_not_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with open_in(Path(temporary), "project:a") as memory:
                domains = [TENANT, "project:a"]
                result = memory.remember(
                    "memory:legitimate", "The gateway is in Oslo",
                    overrides={
                        "scope": "project:a", "project_ref": "project:a",
                        "isolation_domain_refs": domains,
                        "required_isolation_domain_refs": domains,
                    },
                )
                self.assertTrue(result["committed"], result)

    def test_host_bound_identity_override_matrix_fails_before_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as owner:
                original = owner.remember(KEY, "Orrin gateway region is Oslo")
                self.assertTrue(original["committed"])
                original_ref = original["fact_uuid"]
            attempted_overrides = [
                {"tenant_ref": "tenant:other"},
                {"scope": "project:a"},
                {"project_ref": "project:a"},
                {"isolation_domain_refs": [TENANT, "project:a"]},
                {"required_isolation_domain_refs": [TENANT, "project:a"]},
                {"task_ref": "task:owner"},
                {"operation": "correction"},
                {"target_reference": "memory:different-target"},
            ]
            with open_in(root, "project:b") as other:
                for override in attempted_overrides:
                    with self.subTest(override=override), self.assertRaises(ValueError):
                        other.remember(KEY, "Orrin gateway region is Turku",
                                       overrides=override)
            with open_in(root, "project:a") as owner:
                self.assertEqual(
                    owner.history(KEY)["history"]["current_fact_uuid"], original_ref
                )

    def test_other_project_cannot_correct_owner_with_qualified_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as owner:
                first = owner.remember(KEY, "Orrin gateway region is Oslo")
                self.assertTrue(first["committed"])
                original = first["fact_uuid"]
            with open_in(root, "project:b") as other:
                attempted = other.correct(
                    KEY, "Orrin gateway region is Turku",
                    evidence=review_evidence("project:b"), risk_class="low",
                )
                self.assertFalse(attempted["committed"], attempted)
                self.assertIsNone(attempted["fact_uuid"])
                self.assertNotIn(original, repr(attempted))
            with open_in(root, "project:a") as owner:
                self.assertEqual(owner.history(KEY)["history"]["current_fact_uuid"], original)

    def test_other_project_cannot_prune_owner_with_qualified_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as owner:
                first = owner.remember(KEY, "Orrin gateway region is Oslo")
                self.assertTrue(first["committed"])
                original = first["fact_uuid"]
            with open_in(root, "project:b") as other:
                attempted = other.forget(
                    KEY, evidence=review_evidence("project:b"), risk_class="low",
                )
                self.assertFalse(attempted["committed"], attempted)
                self.assertIsNone(attempted["fact_uuid"])
                self.assertNotIn(original, repr(attempted))
            with open_in(root, "project:a") as owner:
                self.assertEqual(owner.history(KEY)["history"]["current_fact_uuid"], original)

    def test_other_project_cannot_dispute_owner_fact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as owner:
                first = owner.remember(KEY, "Orrin gateway region is Oslo")
                self.assertTrue(first["committed"])
                original = first["fact_uuid"]
            with open_in(root, "project:b") as other:
                denied = other.dispute(
                    KEY, fact_uuid=original,
                    evidence=review_evidence("project:b"), risk_class="low",
                )
                self.assertFalse(denied["committed"], denied)
                self.assertIsNone(denied["fact_uuid"])
            with open_in(root, "project:a") as owner:
                self.assertEqual(owner.history(KEY)["history"]["current_fact_uuid"], original)
                recalled = owner.recall("Orrin gateway region", logical_memory_refs=(KEY,))
                self.assertIn(original, recalled["admitted"])

    def test_same_project_keeps_existing_explicit_rewrite_behavior(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as memory:
                one = memory.remember(KEY, "Orrin gateway region is Oslo")
                two = memory.remember(KEY, "Orrin gateway region is Berlin")
                self.assertTrue(one["committed"], one)
                self.assertTrue(two["committed"], two)
                self.assertNotEqual(one["fact_uuid"], two["fact_uuid"])
                self.assertEqual(memory.history(KEY)["history"]["current_fact_uuid"],
                                 two["fact_uuid"])

    def test_owner_correction_remains_eligible_with_qualified_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as owner:
                initial = owner.remember(KEY, "Orrin gateway region is Oslo")
                self.assertTrue(initial["committed"], initial)
                corrected = owner.correct(
                    KEY, "Orrin gateway region is Berlin",
                    evidence=review_evidence("project:a"), risk_class="low",
                )
                self.assertTrue(corrected["committed"], corrected)
                self.assertEqual(
                    owner.history(KEY)["history"]["current_fact_uuid"],
                    corrected["fact_uuid"],
                )

    def test_owner_pruning_remains_eligible_with_qualified_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as owner:
                initial = owner.remember(KEY, "Orrin gateway region is Oslo")
                self.assertTrue(initial["committed"], initial)
                removed = owner.forget(
                    KEY, evidence=review_evidence("project:a"), risk_class="low",
                )
                self.assertTrue(removed["committed"], removed)
                self.assertIsNone(owner.history(KEY)["history"]["current_fact_uuid"])

    def test_second_project_can_write_its_own_distinct_memory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with open_in(root, "project:a") as owner:
                self.assertTrue(owner.remember(KEY, "Orrin gateway region is Oslo")["committed"])
            with open_in(root, "project:b") as other:
                new = other.remember("memory:other-gateway-region",
                                     "The other gateway region is Turku")
                self.assertTrue(new["committed"], new)


if __name__ == "__main__":
    unittest.main()
