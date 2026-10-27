"""Real SQLite security regression tests for #786. No fake memory backends."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.api import contract
from agentmem_ref.state.substrate import Episode


TENANT = "tenant:786-runtime-boundary"
ACTOR = "agent:786-runtime-boundary"
KEY = "memory:786-shared-logical-name"


class RuntimeIdentityBoundaryTests(unittest.TestCase):
    def test_caller_cannot_impersonate_another_project_during_recall(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a") as owner:
                first = owner.remember(KEY, "Private gateway region is Oslo")
                self.assertTrue(first["committed"], first)

            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:b") as outsider:
                ordinary = outsider.recall("Private gateway region")
                self.assertNotIn(first["fact_uuid"], ordinary["admitted"])
                with self.assertRaisesRegex(ValueError, "project"):
                    outsider.recall("Private gateway region", project_ref="project:a")
                with self.assertRaisesRegex(ValueError, "domains"):
                    outsider.recall(
                        "Private gateway region",
                        target_domain_refs=(TENANT, "project:a"),
                    )
                with self.assertRaisesRegex(ValueError, "principal"):
                    outsider.recall("Private gateway region", principal_ref="agent:impersonated")

            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a") as owner:
                own = owner.recall("Private gateway region")
                self.assertIn(first["fact_uuid"], own["admitted"])

    def test_history_is_unknown_for_foreign_scope_before_and_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a") as owner:
                first = owner.remember(KEY, "History belongs to project A")
                self.assertTrue(first["committed"], first)
                own = owner.history(KEY)["history"]
                self.assertEqual(own["current_fact_uuid"], first["fact_uuid"])

            for _ in range(2):
                with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:b") as outsider:
                    shown = outsider.history(KEY)["history"]
                    self.assertIsNone(shown["current_fact_uuid"])
                    self.assertEqual(shown["state_version"], 0)
                    self.assertFalse(shown["tombstoned"])
                    self.assertEqual(shown["events"], [])
                    self.assertEqual(outsider.history(KEY, fact_text="History belongs to project A")["history"]["rejected_values"], [])

            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a") as owner:
                own = owner.history(KEY)["history"]
                self.assertEqual(own["current_fact_uuid"], first["fact_uuid"])

    def test_foreign_mutations_return_consistent_refusals_and_preserve_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a") as owner:
                first = owner.remember(KEY, "Owner's canonical gateway is Oslo")
                self.assertTrue(first["committed"], first)
                original_ref = first["fact_uuid"]
                original_version = owner.history(KEY)["history"]["state_version"]

            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:b") as outsider:
                outcomes = (
                    outsider.remember(KEY, "Foreign replacement is Turku"),
                    outsider.correct(KEY, "Foreign correction"),
                    outsider.forget(KEY),
                    outsider.dispute(KEY),
                )
                for outcome in outcomes:
                    self.assertFalse(outcome["committed"], outcome)
                    self.assertEqual(outcome["outcome"], "block", outcome)
                    self.assertEqual(outcome["receipt"]["selected_action"], "none", outcome)
                    self.assertEqual(outcome["receipt"]["before_state"], "v0", outcome)
                    self.assertEqual(outcome["receipt"]["after_state"], "v0", outcome)
                    self.assertNotIn(
                        original_ref, repr(outcome),
                        "A blocked mutation leaked its owner's canonical fact reference",
                    )
                unknown = outsider.history(KEY)["history"]
                self.assertIsNone(unknown["current_fact_uuid"])
                self.assertEqual(unknown["events"], [])

            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a") as owner:
                current = owner.history(KEY)["history"]
                self.assertEqual(current["current_fact_uuid"], original_ref)
                self.assertEqual(current["state_version"], original_version)


    def test_rejected_foreign_write_cannot_persist_unapproved_episode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a") as owner:
                first = owner.remember(KEY, "Project A private state")
                self.assertTrue(first["committed"], first)

            with AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:b") as outsider:
                episode = Episode(
                    uuid="episode:786-foreign-write",
                    content="Unapproved foreign raw episode",
                    source_description="adversarial fixture",
                    valid_at="2026-10-26T12:00:00Z",
                    group_id=TENANT,
                )
                proposal = contract.proposal_from_envelope(
                    outsider._proposal(
                        target_reference=KEY,
                        fact_text="Overwrite project A",
                        operation="promotion",
                    )
                )
                with outsider.runtime.serialization_lock:
                    outcome = outsider.runtime.adapter.commit_proposal(
                        proposal, "Overwrite project A", episode=episode
                    )
                    stored = outsider.runtime.adapter.checkpoint_substrate().get_episode(
                        episode.uuid
                    )
                self.assertFalse(outcome.committed, outcome)
                self.assertEqual(outcome.refusal, "write_target_unavailable")
                self.assertIsNone(
                    stored,
                    "A blocked write inserted its episode before governance authorized it",
                )


if __name__ == "__main__":
    unittest.main()
