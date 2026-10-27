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
                unrelated = memory.remember(
                    "memory:other", "Unrelated Denver city archive audit."
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


if __name__ == "__main__":
    unittest.main()
