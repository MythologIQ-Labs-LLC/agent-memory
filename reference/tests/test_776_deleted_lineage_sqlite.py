"""#776 regression: deletion fences the entire logical lineage in real SQLite.

These checks are intentionally substantive: a version superseded by a governed
state change may be valid historical evidence BEFORE deletion, but must not
resurface through historical/as-of/derived recall AFTER deleting its logical
memory. No fake adapters or direct tombstone insertion.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.api.surface import StoreIdentityError
from tests._tenant_wide_fixture import open_tenant_wide  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm

TENANT = "tenant:776-lineage"
SCOPE = "project:776-lineage"


def _evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:776-governed-correction",
        version=1,
        purpose="check governed state change",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# Verify\nConfirm the earlier fact against its source.",
        provenance_refs=("evidence:776-source",),
    )
    return pm.evidence_for(skill)


def _open(root):
    return AgentMemory.open(
        root, tenant=TENANT, actor_id="agent:776", scope=SCOPE,
        purpose="logical deletion regression",
    )


class DeletedLineageSQLiteTests(unittest.TestCase):
    def test_deleted_head_blocks_superseded_state_change_in_history_and_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _open(root) as memory:
                old = memory.remember(
                    "memory:city", "The canonical city was Denver.",
                    valid_from="2020-01-01",
                )
                self.assertTrue(old["committed"], old)
                new = memory.correct(
                    "memory:city", "The canonical city became Boston.",
                    evidence=_evidence(), risk_class="low",
                    replacement_kind="state_change", valid_from="2024-01-01",
                )
                self.assertTrue(new["committed"], new)
                before = memory.recall(
                    "canonical city Denver",
                    temporal_intent={"mode": "historical"},
                )
                self.assertIn(old["fact_uuid"], before["admitted"], before)
                deleted = memory.forget("memory:city")
                self.assertTrue(deleted["committed"], deleted)

                for intent in (
                    {"mode": "historical"},
                    {"mode": "as_of", "target_start": "2022-01-01", "target_end": "2022-01-02"},
                ):
                    with self.subTest(intent=intent):
                        after = memory.recall("canonical city Denver", temporal_intent=intent)
                        self.assertNotIn(old["fact_uuid"], after["admitted"], after)
                        self.assertEqual(
                            after["admissions"][old["fact_uuid"]]["refusal"],
                            "tombstoned",
                        )

            with _open(root) as recovered:
                after_restart = recovered.recall(
                    "canonical city Denver", temporal_intent={"mode": "historical"}
                )
                self.assertNotIn(old["fact_uuid"], after_restart["admitted"])
                self.assertEqual(
                    after_restart["admissions"][old["fact_uuid"]]["refusal"],
                    "tombstoned",
                )

    def test_multiversion_delete_blocks_derived_prior_versions_but_not_unrelated_fact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _open(root) as memory:
                first = memory.remember("memory:city", "The city archive was Denver.")
                self.assertTrue(first["committed"], first)
                second = memory.correct(
                    "memory:city", "The city archive became Boston.",
                    evidence=_evidence(), risk_class="low",
                    replacement_kind="state_change", valid_from="2024-01-01",
                )
                self.assertTrue(second["committed"], second)
                third = memory.correct(
                    "memory:city", "The city archive became Oslo.",
                    evidence=_evidence(), risk_class="low",
                    replacement_kind="state_change", valid_from="2025-01-01",
                )
                self.assertTrue(third["committed"], third)
                derived = memory.remember(
                    "memory:derived", "Derived Denver city archive audit.",
                    evidence_refs=(first["fact_uuid"],),
                )
                self.assertTrue(derived["committed"], derived)
                # Identical text must remain visible when its logical-memory
                # binding is independent of the deleted source lineage.
                unrelated = memory.remember(
                    "memory:other", "Derived Denver city archive audit."
                )
                self.assertTrue(unrelated["committed"], unrelated)

                removed = memory.forget("memory:city")
                self.assertTrue(removed["committed"], removed)
                recalled = memory.recall(
                    "Denver city archive audit",
                    temporal_intent={"mode": "historical"},
                )
                for version in (first["fact_uuid"], second["fact_uuid"], third["fact_uuid"]):
                    with self.subTest(version=version):
                        self.assertNotIn(version, recalled["admitted"])
                self.assertNotIn(derived["fact_uuid"], recalled["admitted"])
                self.assertIn(unrelated["fact_uuid"], recalled["admitted"])
                self.assertEqual(
                    recalled["admissions"][derived["fact_uuid"]]["refusal"],
                    "derived_from_tombstoned_source",
                )

            with _open(root) as recovered:
                recalled = recovered.recall(
                    "Denver city archive audit", temporal_intent={"mode": "historical"}
                )
                self.assertNotIn(first["fact_uuid"], recalled["admitted"])
                self.assertNotIn(second["fact_uuid"], recalled["admitted"])
                self.assertNotIn(derived["fact_uuid"], recalled["admitted"])
                self.assertIn(unrelated["fact_uuid"], recalled["admitted"])


    def test_deleted_key_cannot_commit_invisible_recreation_after_restart(self):
        # Existing contract has no governed restore. Failing closed is safer
        # than committing a fact that canonical recall will never serve.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _open(root) as owner:
                first = owner.remember("memory:closed", "The original state was A.")
                self.assertTrue(first["committed"], first)
                erased = owner.forget("memory:closed")
                self.assertTrue(erased["committed"], erased)
                refused = owner.remember("memory:closed", "New state after deletion.")
                self.assertFalse(refused["committed"], refused)
                self.assertEqual(refused["outcome"], "block")
                self.assertEqual(refused["receipt"]["selected_action"], "none")
                independent = owner.remember("memory:fresh", "Unrelated memory survives.")
                self.assertTrue(independent["committed"], independent)

            with _open(root) as owner:
                state = owner.history("memory:closed")["history"]
                self.assertTrue(state["tombstoned"])
                self.assertIsNone(state["current_fact_uuid"])
                after = owner.recall(
                    "New state after deletion", temporal_intent={"mode": "historical"},
                )
                self.assertNotIn(first["fact_uuid"], after["admitted"])
                self.assertIn(
                    independent["fact_uuid"],
                    owner.recall("Unrelated memory survives")["admitted"],
                )
                repeat = owner.remember("memory:closed", "Another blocked recreation.")
                self.assertFalse(repeat["committed"], repeat)
                self.assertEqual(repeat["outcome"], "block")


    def test_deleted_id_cannot_be_reallocated_by_another_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _open(root) as owner:
                old = owner.remember("memory:shared-name", "Scope owner original.")
                self.assertTrue(old["committed"], old)
                deletion = owner.forget("memory:shared-name")
                self.assertTrue(deletion["committed"], deletion)

            with open_tenant_wide(
                root, tenant=TENANT, actor_id="agent:elsewhere",
                scope="project:elsewhere", purpose="foreign recreation probe",
            ) as outsider:
                rebinding = outsider.remember(
                    "memory:shared-name", "Foreign replacement should not exist."
                )
                self.assertFalse(rebinding["committed"], rebinding)
                self.assertEqual(rebinding["outcome"], "block")
                self.assertEqual(rebinding["receipt"]["selected_action"], "none")
                self.assertEqual(rebinding["receipt"]["before_state"], "v0")
                self.assertEqual(rebinding["receipt"]["after_state"], "v0")
                fresh = outsider.remember("memory:foreign-own", "Fresh project B state.")
                self.assertTrue(fresh["committed"], fresh)

            # The store now holds two projects, so the public opener correctly refuses it
            # (#786: its single-project record no longer matches canonical state). The owner
            # is checked through the same tenant-wide test construction.
            with self.assertRaises(StoreIdentityError):
                _open(root)
            with open_tenant_wide(
                root, tenant=TENANT, actor_id="agent:776", scope=SCOPE, purpose="logical deletion regression",
            ) as owner:
                state = owner.history("memory:shared-name")["history"]
                self.assertIsNone(state["current_fact_uuid"])
                self.assertTrue(state["tombstoned"])
                recalled = owner.recall(
                    "Scope owner original",
                    temporal_intent={"mode": "historical"},
                )
                self.assertNotIn(old["fact_uuid"], recalled["admitted"])


if __name__ == "__main__":
    unittest.main()
