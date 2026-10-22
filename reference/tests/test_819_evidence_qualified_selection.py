"""#819 evidence-qualified context selection: contract of the opt-in consumer profile.

These complement the owner's product controls in ``test_819_served_context_quality_contract.py``
with the mechanism's own guarantees: the default profile stays byte-compatible, every declined
fact is inspectable, the selector preserves authorised, corroborated and historical evidence
whatever its wording, uncertainty is reported rather than converted into exclusion, the
delivery receipt records the selection, and declined content spends no budget. None of this is
benchmark evidence; a passing suite is not a usefulness claim.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.api import context_package, context_selection
from agentmem_ref.core import receipts
from agentmem_ref.memory import procedural_memory as pm

PROFILE = "evidence_qualified"
TENANT = "tenant:eq"
SCOPE = "project:eq"


def _delivered(package):
    return [i["fact_ref"] for i in package["items"] if i["state"] in ("resolved", "truncated")]


def _omitted(package):
    return {i["fact_ref"]: i["reason"] for i in package["items"] if i["state"] == "omitted_selection"}


class _Store(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.root = Path(self._dir.name) / "m"
        self.memory = self.open()

    def tearDown(self):
        if not self.memory.closed:
            self.memory.close()

    def open(self, scope=SCOPE, **kwargs):
        return AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:eq", scope=scope,
                                purpose="evidence-qualified selection tests", **kwargs)

    def put(self, ref, text, **kwargs):
        out = self.memory.remember(ref, text, **kwargs)
        self.assertTrue(out["committed"], out)
        return out["fact_uuid"]

    def context(self, query, profile=PROFILE, **kwargs):
        return self.memory.recall_context(query, consumer_profile=profile, max_items=10, **kwargs)


class ProfileContract(_Store):
    def test_default_profile_is_byte_identical_with_and_without_the_keyword(self):
        self.put("memory:a", "Liora's canoe is teal.")
        self.put("memory:b", "Liora's bicycle is black.")
        implicit = self.memory.recall_context("What color is Liora's canoe?", max_items=10)
        explicit = self.memory.recall_context("What color is Liora's canoe?", max_items=10, consumer_profile="all_returned")
        for package in (implicit, explicit):
            self.assertEqual(package["package_version"], "agent-memory-context/0.1.0")
            self.assertNotIn("selection", package)
            self.assertEqual(len(_delivered(package)), 2)
        def strip(package):  # only the receipt ids and the per-call admission decision ids differ
            body = {k: v for k, v in package.items() if k != "audit"}
            for item in body["items"]:
                item.get("provenance", {}).pop("admission_decision_id", None)
            return json.dumps(body, sort_keys=True)
        self.assertEqual(strip(implicit), strip(explicit))

    def test_unknown_profile_is_refused_before_any_recall(self):
        self.put("memory:a", "Liora's canoe is teal.")
        before = len(self.memory.runtime.adapter.events)
        for bad in ("lexical_content", "", None, 3):
            with self.assertRaises(ValueError, msg=bad):
                self.memory.recall_context("canoe", consumer_profile=bad)
        self.assertEqual(len(self.memory.runtime.adapter.events), before)

    def test_selective_package_validates_and_records_every_decision(self):
        teal = self.put("memory:a", "Liora's canoe is teal.")
        orange = self.put("memory:b", "Bastien's canoe is orange.")
        bike = self.put("memory:c", "Liora's bicycle is black.")
        package = self.context("What color is Liora's canoe?")
        receipts.validate(context_package.PACKAGE_SCHEMA, package)
        self.assertEqual(package["package_version"], "agent-memory-context/0.2.0")
        self.assertEqual(package["status"], "complete")
        self.assertEqual(_delivered(package), [teal])
        self.assertEqual(_omitted(package), {orange: "subject_mismatch", bike: "attribute_unevidenced"})
        selection = package["selection"]
        self.assertEqual(selection["policy_id"], context_selection.POLICY_ID)
        self.assertEqual(selection["policy_version"], context_selection.POLICY_VERSION)
        self.assertEqual(selection["assessment"], "evidence_delivered")
        self.assertEqual(set(selection["decisions"]), set(package["recall"]["returned"]))
        self.assertEqual(selection["decisions"][teal]["matched_terms"], ["cano", "liora"])
        self.assertEqual(selection["decisions"][orange]["fact_subjects"], ["bastien"])
        self.assertEqual(selection["query_subjects"], ["liora"])
        self.assertEqual(selection["authority_effect"], "none")
        # the recall inside the package is the unchanged governed recall
        self.assertEqual(package["recall"]["returned"], [teal, orange, bike])
        # a declined item never carries content or provenance
        for item in package["items"]:
            if item["state"] == "omitted_selection":
                self.assertNotIn("content", item)
                self.assertNotIn("provenance", item)

    def test_no_relevant_evidence_is_an_explicit_assessment_not_a_bare_empty_status(self):
        self.put("memory:a", "The autumn science festival begins Friday.")
        self.put("memory:b", "The moon exhibit has a new display case.")
        package = self.context("What time does the lunar eclipse committee meet?")
        receipts.validate(context_package.PACKAGE_SCHEMA, package)
        self.assertEqual(package["status"], "empty")
        self.assertEqual(_delivered(package), [])
        self.assertEqual(package["selection"]["assessment"], "no_relevant_evidence")
        self.assertEqual(set(_omitted(package).values()), {"no_query_term_evidence"})
        self.assertEqual(package["budget"]["used_chars"], 0)
        # distinct from a recall that returned nothing
        nothing = self.context("zxqv")
        self.assertEqual(nothing["status"], "empty")
        self.assertEqual(nothing["selection"]["assessment"], "no_returned_candidates")

    def test_uncertainty_is_delivered_and_labelled_rather_than_excluded(self):
        self.put("memory:a", "Liora's canoe is teal.")
        unowned = self.put("memory:b", "The canoe was repainted last spring.")
        package = self.context("What color is Liora's canoe?")
        decisions = package["selection"]["decisions"]
        self.assertIn(unowned, _delivered(package))
        self.assertEqual(decisions[unowned]["evidence"], "ungrounded_subject")
        self.assertEqual(decisions[unowned]["certainty"], "uncertain")
        self.assertEqual(package["selection"]["uncertain_count"], 1)
        # a query with no content terms cannot ground any exclusion
        only_function_words = self.context("what is it")
        for decision in only_function_words["selection"]["decisions"].values():
            self.assertEqual(decision["outcome"], "delivered")
            self.assertEqual(decision["evidence"], "undetermined_query")
        self.assertEqual(only_function_words["selection"]["assessment"], "undetermined")

    def test_first_person_query_declines_a_third_party_possessive_fact(self):
        ours = self.put("memory:a", "Our family car is a blue Kia Niro.")
        theirs = self.put("memory:b", "Priya's car is a silver Honda Civic.")
        unowned = self.put("memory:c", "The car wash on Elm Street closes at six.")
        package = self.context("Which car does our family drive?")
        self.assertIn(ours, _delivered(package))
        self.assertIn(unowned, _delivered(package))  # no grounded subject: delivered, not guessed away
        self.assertEqual(_omitted(package), {theirs: "subject_mismatch"})
        decisions = package["selection"]["decisions"]
        self.assertEqual(decisions[ours]["evidence"], "subject_and_attribute_evidence")
        self.assertEqual(decisions[theirs]["query_subjects"], ["speaker"])
        self.assertEqual(decisions[theirs]["fact_subjects"], ["priya"])
        # a third party mentioned in a first-person fact stays: the fact is still about the caller
        mine_too = self.put("memory:d", "My brother borrowed Priya's car for our trip.")
        package = self.context("Which car does our family drive?")
        self.assertIn(mine_too, _delivered(package))

    def test_term_absence_is_grounded_only_for_a_single_statement(self):
        short = self.put("memory:a", "The autumn science festival begins Friday.")
        long = self.put("memory:b", "The autumn science festival begins Friday. The committee that plans "
                                    "the eclipse viewing meets afterwards in the same hall.")
        package = self.context("What time does the lunar eclipse committee meet?")
        decisions = package["selection"]["decisions"]
        # the short fact shares no content term with the question: declined
        if short in decisions:
            self.assertEqual(decisions[short]["outcome"], "omitted")
            self.assertEqual(decisions[short]["reason"], "no_query_term_evidence")
        # the longer one matches ("committee", "eclipse", "meet"); now make one that does not
        unrelated_long = self.put("memory:c", "The moon exhibit has a new display case. Tickets are sold at the "
                                              "door. Visitors may bring cameras.")
        package = self.context("What time does the lunar eclipse committee meet?")
        decisions = package["selection"]["decisions"]
        self.assertEqual(decisions[unrelated_long]["outcome"], "delivered")
        self.assertEqual(decisions[unrelated_long]["evidence"], "undetermined_multi_statement")
        self.assertEqual(decisions[unrelated_long]["certainty"], "uncertain")
        self.assertFalse(decisions[unrelated_long]["single_statement"])
        self.assertIn(long, _delivered(package))

    def test_lowercase_possessive_is_not_a_subject_anchor(self):
        self.assertEqual(context_selection.possessive_subjects("Which composer's tunes does Tim play?"), frozenset())
        self.assertEqual(context_selection.possessive_subjects("Which of Tim's tunes does the composer play?"),
                         frozenset({"tim"}))
        tim = self.put("memory:a", "Tim loves playing film scores on the piano after work.")
        package = self.context("Which composer's tunes does Tim enjoy playing on the piano?")
        self.assertIn(tim, _delivered(package))
        self.assertEqual(package["selection"]["decisions"][tim]["evidence"], "query_term_evidence")

    def test_first_person_fact_never_mismatches_a_first_person_query(self):
        mine = self.put("memory:a", "I bought a gift for my brother's graduation at Sarah's shop.")
        package = self.context("How many days passed between my brother's graduation and the Sunday mass at St. Mary's Church?")
        self.assertIn(mine, _delivered(package))
        decision = package["selection"]["decisions"][mine]
        self.assertNotEqual(decision["outcome"], "omitted")

    def test_first_person_fact_is_about_its_speaker_whatever_names_it_mentions(self):
        # a third-person question anchored on a proper noun must not decline a first-person
        # memory that mentions another proper noun by possessive: the speaker is its subject
        mine = self.put("memory:a", "I just came from the Ash Wednesday service at the cathedral; God's grace was the theme.")
        package = self.context("How many days passed between the Sunday mass at St. Mary's Church and the Ash Wednesday service?")
        self.assertIn(mine, _delivered(package))
        self.assertNotEqual(package["selection"]["decisions"][mine]["outcome"], "omitted")
        # whereas a third-person fact grounded on another subject is still declined
        theirs = self.put("memory:b", "Bastien's Ash Wednesday service was at the chapel.")
        package = self.context("Where was Mary's Ash Wednesday service?")
        self.assertEqual(_omitted(package).get(theirs), "subject_mismatch")

    def test_attribute_absence_is_grounded_only_for_a_single_statement(self):
        bike = self.put("memory:a", "Liora's bicycle is black.")
        diary = self.put("memory:b", "Liora's week was busy. She repainted the boat shed on Monday. "
                                     "The paddles were ordered on Tuesday.")
        package = self.context("What color is Liora's canoe?")
        decisions = package["selection"]["decisions"]
        self.assertEqual((decisions[bike]["outcome"], decisions[bike]["reason"]), ("omitted", "attribute_unevidenced"))
        self.assertEqual((decisions[diary]["outcome"], decisions[diary]["evidence"], decisions[diary]["certainty"]),
                         ("delivered", "attribute_undetermined", "uncertain"))

    def test_subject_only_query_keeps_subject_evidence(self):
        canoe = self.put("memory:a", "Liora's canoe is teal.")
        bike = self.put("memory:b", "Liora's bicycle is black.")
        self.put("memory:c", "Bastien's canoe is orange.")
        package = self.context("Liora's")
        self.assertEqual(sorted(_delivered(package)), sorted([canoe, bike]))
        for ref in (canoe, bike):
            self.assertEqual(package["selection"]["decisions"][ref]["evidence"], "subject_only_evidence")

    def test_morphology_and_paraphrase_keep_required_evidence(self):
        needed = self.put("memory:a", "I graduated with a degree in Business Administration last spring.")
        self.put("memory:b", "The spring festival committee ordered new banners.")
        package = self.context("What degrees did my friends graduate with?")
        self.assertIn(needed, _delivered(package))
        self.assertEqual(sorted(package["selection"]["decisions"][needed]["matched_terms"]), ["degre", "graduat"])

    def test_exact_logical_identity_is_delivered_whatever_the_wording(self):
        needed = self.put("memory:precise", "The maintenance waiver permits a temporary expansion.")
        package = self.context("the signed exception", logical_memory_refs=("memory:precise",))
        self.assertEqual(_delivered(package), [needed])
        self.assertEqual(package["selection"]["decisions"][needed]["evidence"], "preserved_exact_identity")

    def test_historical_admission_is_delivered_for_a_historical_query(self):
        self.put("memory:lamp", "The reading lamp is magenta.")
        evidence = pm.evidence_for(pm.SkillArtifact(
            skill_id="skill:eq", version=1, purpose="correction", scope=SCOPE,
            isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
            procedure_markdown="# verify", provenance_refs=("evidence:eq",)))
        changed = self.memory.correct("memory:lamp", "The reading lamp is now jade green.", evidence=evidence)
        self.assertTrue(changed["committed"], changed)
        current = self.context("color of reading lamp")
        self.assertNotIn("magenta", json.dumps(current))
        historical = self.context("what colour did the lamp use to be",
                                  temporal_intent={"mode": "historical", "expected_recall_shape": "timeline"})
        texts = [i.get("content") for i in historical["items"] if i["state"] == "resolved"]
        if any("magenta" in (t or "") for t in texts):
            ref = next(i["fact_ref"] for i in historical["items"] if "magenta" in (i.get("content") or ""))
            self.assertEqual(historical["selection"]["decisions"][ref]["evidence"], "preserved_historical_admission")
        else:  # the runtime did not admit the superseded version: nothing for the selector to decide
            self.assertNotIn("magenta", json.dumps(historical))

    def test_declined_content_spends_no_budget_and_the_receipt_records_the_selection(self):
        teal = self.put("memory:a", "Liora's canoe is teal.")
        self.put("memory:b", "Bastien's canoe is orange and very long " * 20)
        package = self.memory.recall_context("What color is Liora's canoe?", consumer_profile=PROFILE,
                                             max_items=10, max_total_chars=80, max_chars_per_item=80)
        self.assertEqual(_delivered(package), [teal])
        self.assertEqual(package["budget"]["used_chars"], len("Liora's canoe is teal."))
        self.assertEqual(package["status"], "complete")
        event = next(e for e in reversed(self.memory.runtime.adapter.events)
                     if e.get("event_type") == "memory.context_delivery")
        self.assertEqual(event["event_id"], package["audit"]["delivery_event_id"])
        payload = event["payload"]
        self.assertEqual(payload["package_version"], "agent-memory-context/0.2.0")
        self.assertEqual(payload["selection"]["policy_id"], context_selection.POLICY_ID)
        self.assertEqual(payload["selection"]["omitted_reasons"], {"subject_mismatch": 1})
        self.assertEqual(payload["selection"]["assessment"], "evidence_delivered")
        self.assertEqual(set(payload["outcomes"]), set(package["recall"]["returned"]))
        omitted = [o for o in payload["outcomes"].values() if o["state"] == "omitted_selection"]
        self.assertEqual(omitted, [{"state": "omitted_selection", "reason": "subject_mismatch"}])
        self.assertNotIn("canoe", json.dumps(event))  # the receipt carries no text and no terms

    def test_raw_recall_and_audit_order_are_unchanged_by_the_profile(self):
        self.put("memory:a", "Liora's canoe is teal.")
        self.put("memory:b", "Bastien's canoe is orange.")
        before = self.memory.recall("Liora's canoe", budget=10)
        events_before = len(self.memory.runtime.adapter.events)
        package = self.context("Liora's canoe")
        after = self.memory.recall("Liora's canoe", budget=10)
        for key in ("candidates", "admitted", "returned", "return_policy"):
            self.assertEqual(before[key], after[key], key)
        volatile = ("decision_id", "evaluated_at")  # admissions differ only by per-call id and clock
        for ref in before["admitted"]:
            self.assertEqual({k: v for k, v in before["admissions"][ref].items() if k not in volatile},
                             {k: v for k, v in after["admissions"][ref].items() if k not in volatile}, ref)
        types = [e.get("event_type") for e in self.memory.runtime.adapter.events[events_before:]]
        self.assertEqual(types[:2], ["memory.recall", "memory.context_delivery"])
        self.assertEqual(package["recall"]["returned"], before["returned"])

    def test_restart_keeps_the_selection_decisions_stable(self):
        teal = self.put("memory:a", "Liora's canoe is teal.")
        orange = self.put("memory:b", "Bastien's canoe is orange.")
        first = self.context("What color is Liora's canoe?")
        self.memory.close()
        self.memory = self.open()
        second = self.context("What color is Liora's canoe?")
        self.assertEqual(_delivered(first), _delivered(second), [teal])
        self.assertEqual(_omitted(first), _omitted(second), {orange: "subject_mismatch"})


class SelectorUnit(unittest.TestCase):
    def test_fold_is_bounded_and_symmetric(self):
        fold = context_selection.content_terms
        for a, b in (("parents", "parent"), ("works", "work"), ("graduated", "graduate"), ("Mara's", "Mara"),
                     ("canoes", "canoe"), ("observatories", "observatory"), ("running", "run"), ("sisters'", "sister"),
                     ("moved", "move"), ("buses", "bus"), ("VIOLET-17", "violet-17")):
            self.assertEqual(fold(a), fold(b), (a, b))
        self.assertEqual(fold("what is it"), frozenset())
        self.assertEqual(fold("Liora's"), frozenset({"liora"}))
        self.assertEqual(context_selection.possessive_subjects("Where do Mara's parents work?"), frozenset({"mara"}))

    def test_grounded_subject_uses_only_persisted_proposition_and_possessive(self):
        subject = context_selection.grounded_subject
        self.assertEqual(subject("The reading lamp is magenta.", {"status": "known", "entity": "reading lamp"}),
                         frozenset({"read", "lamp"}))  # folded like every other term
        self.assertEqual(subject("I moved to Denver.", {"status": "known", "entity": "speaker"}), frozenset())
        self.assertEqual(subject("The canoe was repainted.", {"status": "unknown"}), frozenset())
        self.assertEqual(subject("Bastien's canoe is orange.", None), frozenset({"bastien"}))

    def test_single_statement_is_bounded_sentence_counting(self):
        single = context_selection.single_statement
        self.assertTrue(single("Liora's canoe is teal."))
        self.assertTrue(single("The design sketch key is VIOLET-17"))
        self.assertFalse(single("One. Two."))
        self.assertFalse(single("Really? Yes! Fine."))

    def test_corroborated_route_is_preserved_without_any_word_overlap(self):
        decision = {"route_provenance": [{"route_id": "lexical"}, {"route_id": "shared_evidence"}],
                    "admission_basis": {"currentness": "current_state"}}
        verdict = context_selection.qualify("lunar eclipse", "ref-1", decision, "unrelated words entirely", None)
        self.assertEqual((verdict["outcome"], verdict["evidence"]), ("delivered", "preserved_corroborated_route"))
        lexical_only = {"route_provenance": [{"route_id": "lexical"}], "admission_basis": {"currentness": "current_state"}}
        verdict = context_selection.qualify("lunar eclipse", "ref-1", lexical_only, "unrelated words entirely", None)
        self.assertEqual((verdict["outcome"], verdict["reason"]), ("omitted", "no_query_term_evidence"))

    def test_assessment_tells_absence_from_uncertainty(self):
        a = context_selection.assessment
        self.assertEqual(a([]), "no_returned_candidates")
        self.assertEqual(a([{"outcome": "omitted"}]), "no_relevant_evidence")
        self.assertEqual(a([{"outcome": "delivered", "certainty": "uncertain"}, {"outcome": "omitted"}]), "undetermined")
        self.assertEqual(a([{"outcome": "delivered", "certainty": "grounded"}]), "evidence_delivered")
        self.assertEqual(a([{"outcome": "unavailable"}]), "no_relevant_evidence")


if __name__ == "__main__":
    unittest.main()
