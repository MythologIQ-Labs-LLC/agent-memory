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
from agentmem_ref.memory import procedural_memory as pm

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
        # Corrected after the owner's PR #841 review (comment 6350329872): a same-subject fact
        # whose predicate shares no term with the question cannot be told from a paraphrase
        # ("Mara's eldest performs on the cello" for "which instrument does Mara's child play"),
        # so a selector without a verified relation parser must deliver it labelled uncertain
        # rather than decline it. The wrong subject is still declined on grounded evidence, the
        # correct fact is still delivered as grounded evidence, and the wrong-object fact is
        # delivered only as uncertain. Original assertion preserved at blob e8c2e9aa.
        decisions = context["selection"]["decisions"]
        self.assertIn(correct, delivered_refs(context), context)
        self.assertEqual(decisions[correct]["certainty"], "grounded", context)
        self.assertEqual(decisions[correct]["evidence"], "subject_and_attribute_evidence", context)
        self.assertNotIn("Bastien's canoe is orange.", delivered(context))
        self.assertEqual(delivered(context)[0], "Liora's canoe is teal.")
        for ref in delivered_refs(context):
            if ref != correct:
                self.assertEqual(decisions[ref]["certainty"], "uncertain", decisions[ref])
                self.assertEqual(decisions[ref]["evidence"], "attribute_undetermined", decisions[ref])

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

    def test_correction_forget_and_restart_obey_lifecycle(self):
        self.remember("memory:reading", "The reading lamp is magenta.")
        self.assertIn("The reading lamp is magenta.", delivered(
            self.selected("color of reading lamp")
        ))
        skill = pm.SkillArtifact(
            skill_id="skill:quality-lifecycle", version=1,
            purpose="explicit correction and forgetting", scope=SCOPE,
            isolation_domain_refs=(TENANT, SCOPE),
            required_isolation_domain_refs=(TENANT, SCOPE),
            procedure_markdown="# Verify\nConfirm the source's updated state.",
            provenance_refs=("evidence:quality-dev",),
        )
        evidence = pm.evidence_for(skill)
        changed = self.memory.correct(
            "memory:reading", "The reading lamp is now jade green.", evidence=evidence
        )
        self.assertTrue(changed["committed"], changed)
        context = self.selected("color of reading lamp")
        self.assertIn("The reading lamp is now jade green.", delivered(context))
        self.assertNotIn("magenta", repr(context))
        self.memory.close()
        self.memory = self.open()
        self.assertIn("The reading lamp is now jade green.", delivered(
            self.selected("color of reading lamp")
        ))
        removed = self.memory.forget("memory:reading", evidence=evidence)
        self.assertTrue(removed["committed"], removed)
        self.memory.close()
        self.memory = self.open()
        after = self.selected("color of reading lamp")
        self.assertNotIn("jade green", repr(after))
        self.assertNotIn("magenta", repr(after))

if __name__ == "__main__":
    unittest.main()
