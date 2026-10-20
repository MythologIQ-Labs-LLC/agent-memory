"""#775 integration contract: probe actual public SQLite facade recall only.

These tests require the complete reference runtime and are not replaceable by
the isolated evaluation-unit tests. No candidate content is fetched by probe.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.evaluation.public_recall_relevance_probe import inspect_returned
from agentmem_ref.evaluation.subject_relevance_challenge import ChallengeInput


class PublicRecallProbeFacadeTests(unittest.TestCase):
    def test_real_sqlite_public_recall_honors_return_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            with AgentMemory.open(
                Path(tmp), tenant="tenant:probe", actor_id="agent:probe",
                scope="project:probe", purpose="probe",
            ) as memory:
                first = memory.remember("memory:release", "Release is Friday.")
                second = memory.remember("memory:backup", "Backup runs Saturday.")
                self.assertTrue(first["committed"])
                self.assertTrue(second["committed"])
                raw = memory.recall("release backup", budget=1)
                self.assertEqual(len(raw["returned"]), 1)
                all_content = {
                    first["fact_uuid"]: "Release is Friday.",
                    second["fact_uuid"]: "Backup runs Saturday.",
                }
                annotations = {
                    ref: ChallengeInput("release backup", "", ("subject:service",),
                        ("subject:service",), identity_binding_checked=False)
                    for ref in all_content
                }
                before = repr(raw)
                observed = inspect_returned(raw, all_content, annotations)
                self.assertEqual(tuple(x.fact_ref for x in observed),
                                 tuple(raw["returned"]))
                self.assertEqual(len(observed), 1)
                self.assertEqual(observed[0].status, "inspected")
                self.assertEqual(observed[0].relevance.structured_signal,
                                 "unverified_claims")
                self.assertFalse(observed[0].relevance.may_withhold_content)
                self.assertEqual(before, repr(raw))

    def test_foreign_project_not_inspectable_after_governed_prefilter(self):
        with tempfile.TemporaryDirectory() as tmp:
            with AgentMemory.open(
                Path(tmp), tenant="tenant:probe", actor_id="agent:probe",
                scope="project:probe", purpose="probe",
            ) as memory:
                fact = memory.remember("memory:release", "Release is Friday.")
                self.assertTrue(fact["committed"])
                foreign = memory.recall(
                    "Release Friday", logical_memory_refs=("memory:release",),
                    target_domain_refs=("tenant:other", "project:other"),
                    project_ref="project:other",
                )
                self.assertNotIn(fact["fact_uuid"], foreign["candidates"])
                observed = inspect_returned(
                    foreign, {fact["fact_uuid"]: "Release is Friday."},
                    {fact["fact_uuid"]: ChallengeInput("Release Friday", "")},
                )
                self.assertEqual(observed, ())


if __name__ == "__main__":
    unittest.main()
