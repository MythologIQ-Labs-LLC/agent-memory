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
                        # #777 (contract 1.7.0): the public projection withholds a deleted lineage's ids
                        # entirely; the refusal itself is asserted on the canonical record.
                        public = memory.recall("canonical city Denver", temporal_intent=intent)
                        self.assertNotIn(old["fact_uuid"], repr(public))
                        after = memory._canonical_recall("canonical city Denver", temporal_intent=intent)
                        self.assertNotIn(old["fact_uuid"], after["admitted"], after)
                        self.assertEqual(
                            after["admissions"][old["fact_uuid"]]["refusal"],
                            "logical_memory_deleted",  # #776 canonical code for a deleted lineage's prior version
                        )

            with _open(root) as recovered:
                self.assertNotIn(old["fact_uuid"], repr(recovered.recall(
                    "canonical city Denver", temporal_intent={"mode": "historical"})))
                after_restart = recovered._canonical_recall(
                    "canonical city Denver", temporal_intent={"mode": "historical"}
                )
                self.assertNotIn(old["fact_uuid"], after_restart["admitted"])
                self.assertEqual(
                    after_restart["admissions"][old["fact_uuid"]]["refusal"],
                    "logical_memory_deleted",  # #776 canonical code for a deleted lineage's prior version
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
                recalled = memory._canonical_recall(  # #777: canonical record
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
                    "derived_from_deleted_logical_memory",
                )

            with _open(root) as recovered:
                recalled = recovered.recall(
                    "Denver city archive audit", temporal_intent={"mode": "historical"}
                )
                self.assertNotIn(first["fact_uuid"], recalled["admitted"])
                self.assertNotIn(second["fact_uuid"], recalled["admitted"])
                self.assertNotIn(derived["fact_uuid"], recalled["admitted"])
                self.assertIn(unrelated["fact_uuid"], recalled["admitted"])


    def test_deleted_key_is_re_created_as_a_servable_fresh_generation_after_restart(self):
        # Integration (#674 x #786): contract 1.8.0 re-creates a governed-deleted id as a fresh,
        # generation-relative lineage. The security lineage's concern -- a commit canonical recall
        # would never serve -- is asserted directly: the new generation is served, the deleted one
        # is not, before and after a restart.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with _open(root) as owner:
                first = owner.remember("memory:closed", "The original state was A.")
                self.assertTrue(first["committed"], first)
                erased = owner.forget("memory:closed")
                self.assertTrue(erased["committed"], erased)
                again = owner.remember("memory:closed", "New state after deletion.")
                self.assertTrue(again["committed"], again)
                self.assertEqual((again["receipt"]["before_state"], again["receipt"]["after_state"]), ("v0", "v1"))
                independent = owner.remember("memory:fresh", "Unrelated memory survives.")
                self.assertTrue(independent["committed"], independent)

            with _open(root) as owner:
                state = owner.history("memory:closed")["history"]
                self.assertEqual(state["current_fact_uuid"], again["fact_uuid"])
                self.assertEqual(state["state_version"], 1)
                after = owner.recall("New state after deletion", temporal_intent={"mode": "historical"})
                self.assertIn(again["fact_uuid"], after["admitted"], "a re-created generation must be servable")
                self.assertNotIn(first["fact_uuid"], repr(after))
                self.assertIn(independent["fact_uuid"], owner.recall("Unrelated memory survives")["admitted"])
                self.assertNotIn(first["fact_uuid"], repr(owner.recall("The original state was A",
                                                                       temporal_intent={"mode": "historical"})))


    def test_another_projects_re_creation_is_an_isolated_generation_the_owner_cannot_see(self):
        # Integration (#674 x #786): under contract 1.8.0 another project may re-create a deleted id
        # as its own isolated generation; the owner's deleted generation stays deleted and closed,
        # and neither side sees the other's content.
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
                rebinding = outsider.remember("memory:shared-name", "Foreign generation content.")
                self.assertTrue(rebinding["committed"], rebinding)
                self.assertEqual((rebinding["receipt"]["before_state"], rebinding["receipt"]["after_state"]), ("v0", "v1"))
                self.assertNotIn(old["fact_uuid"], repr(outsider.recall("Scope owner original",
                                                                      temporal_intent={"mode": "historical"})))

            # The store now holds two projects, so the public opener refuses it (#786: its
            # single-project record no longer matches canonical state). The owner is checked through
            # the same tenant-wide test construction.
            with self.assertRaises(StoreIdentityError):
                _open(root)
            with open_tenant_wide(
                root, tenant=TENANT, actor_id="agent:776", scope=SCOPE, purpose="logical deletion regression",
            ) as owner:
                state = owner.history("memory:shared-name")["history"]
                self.assertIsNone(state["current_fact_uuid"])
                self.assertTrue(state["tombstoned"])
                recalled = owner.recall("Scope owner original", temporal_intent={"mode": "historical"})
                self.assertNotIn(old["fact_uuid"], recalled["admitted"])
                self.assertNotIn(rebinding["fact_uuid"], repr(owner.recall("Foreign generation content")))


if __name__ == "__main__":
    unittest.main()
