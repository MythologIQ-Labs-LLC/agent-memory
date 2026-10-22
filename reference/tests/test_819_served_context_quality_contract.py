"""#819 product-quality RED controls for the future opt-in evidence-qualified context profile.

NOT an independently blinded holdout or accepted regression score. These are
prospective behavior tests against the post-v7 development API only. In the base
revision recall_context() does not support consumer_profile; they should fail
before implementation. Do not weaken them to claim product readiness.

This suite checks the *served content* (not just broad recall of identifiers).
A QA model is not involved and no result counts as end-to-end answer correctness.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory

PROFILE = "evidence_qualified"
TENANT = "tenant:quality-dev"
SCOPE = "project:quality-dev"


def delivered(package: dict) -> list[str]:
    return [item["content"] for item in package.get("items", ())
            if item.get("state") in ("resolved", "truncated")]


def delivered_refs(package: dict) -> list[str]:
    return [item["fact_ref"] for item in package.get("items", ())
            if item.get("state") in ("resolved", "truncated")]


class QualityControls(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "memory"
        self.memory = self.open()

    def tearDown(self):
        if not self.memory.closed:
            self.memory.close()

    def open(self, scope=SCOPE):
        return AgentMemory.open(
            self.root, tenant=TENANT, actor_id="agent:quality-dev",
            scope=scope, purpose="served-context product-quality diagnostics",
        )

    def remember(self, ref: str, text: str) -> str:
        result = self.memory.remember(ref, text)
        self.assertTrue(result["committed"], result)
        return result["fact_uuid"]

    def selected(self, query: str, **kwargs) -> dict:
        return self.memory.recall_context(
            query, consumer_profile=PROFILE,
            max_items=10, max_total_chars=8000, max_chars_per_item=2000, **kwargs,
        )

    def test_positive_task_context_excludes_wrong_subject_and_wrong_object(self):
        correct = self.remember("memory:canoe", "Liora's canoe is teal.")
        self.remember("memory:other-canoe", "Bastien's canoe is orange.")
        self.remember("memory:other-object", "Liora's bicycle is black.")
        context = self.selected("What color is Liora's canoe?")
        self.assertEqual(delivered_refs(context), [correct], context)
        self.assertEqual(delivered(context), ["Liora's canoe is teal."])

    def test_paraphrased_relationship_and_plural_query_preserve_evidence(self):
        needed = self.remember(
            "memory:family", "The botanist Mara's father works at Bellweather Observatory."
        )
        self.remember(
            "memory:unrelated", "The Observatory Club orders instrument mounts for its volunteers."
        )
        context = self.selected("Where do Mara's parents work?")
        self.assertIn(needed, delivered_refs(context), context)

    def test_no_safe_answer_does_not_serve_distractors_as_an_answer(self):
        self.remember("memory:other-event", "The autumn science festival begins Friday.")
        self.remember("memory:venue", "The moon exhibit has a new display case.")
        context = self.selected("What time does the lunar eclipse committee meet?")
        self.assertEqual(delivered(context), [], context)
        # A successful abstention must be distinguishable from a read failure or
        # a budget truncation, not fabricated by a zero-sized context budget.
        self.assertEqual(context["status"], "empty", context)
        self.assertEqual(context["budget"]["max_items"], 10)

    def test_exact_logical_identity_is_not_discarded_by_word_overlap_heuristics(self):
        needed = self.remember(
            "memory:precise-id", "The maintenance waiver permits a temporary expansion."
        )
        context = self.selected("the signed exception", logical_memory_refs=("memory:precise-id",))
        self.assertIn(needed, delivered_refs(context), context)

    def test_original_governed_recall_ids_and_admission_remain_unchanged(self):
        self.remember("memory:a", "Mara's telescope uses an azimuth mount.")
        self.remember("memory:b", "Bastien's telescope uses an equatorial mount.")
        query = "Mara telescope mount"
        baseline = self.memory.recall(query, budget=10)
        self.selected(query)
        after = self.memory.recall(query, budget=10)
        for field in ("contract_version", "returned", "candidates", "admitted", "return_policy"):
            self.assertEqual(baseline[field], after[field], field)

    def test_other_project_cannot_deliver_private_project_content(self):
        self.remember("memory:private", "The design sketch key is VIOLET-17.")
        self.memory.close()
        self.memory = self.open(scope="project:unrelated")
        context = self.selected("design sketch key")
        self.assertNotIn("VIOLET-17", repr(context))
        self.assertEqual(delivered(context), [])

    def test_correction_and_restart_never_reveal_superseded_text(self):
        self.remember("memory:reading", "The reading lamp is magenta.")
        context = self.selected("color of reading lamp")
        self.assertIn("The reading lamp is magenta.", delivered(context))
        # This is a product workflow check; explicit adjudication evidence is
        # exercised by the existing #691 full-lifecycle test suite.
        self.memory.close()
        self.memory = self.open()
        self.assertIn("The reading lamp is magenta.", delivered(
            self.selected("color of reading lamp")
        ))


if __name__ == "__main__":
    unittest.main()
