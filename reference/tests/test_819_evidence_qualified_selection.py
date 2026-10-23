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
        # the wrong subject is declined on grounded evidence; the same-subject fact about another
        # attribute is delivered but labelled uncertain (policy 0.4.0: a paraphrased predicate
        # cannot be told from a different attribute, PR #841 review comment 6350329872)
        self.assertEqual(_delivered(package), [teal, bike])
        self.assertEqual(_omitted(package), {orange: "subject_mismatch"})
        selection = package["selection"]
        self.assertEqual(selection["policy_id"], context_selection.POLICY_ID)
        self.assertEqual(selection["policy_version"], context_selection.POLICY_VERSION)
        self.assertEqual(selection["assessment"], "evidence_delivered")
        self.assertEqual(set(selection["decisions"]), set(package["recall"]["returned"]))
        self.assertEqual(selection["decisions"][teal]["matched_terms"], ["cano", "liora"])
        self.assertEqual(selection["decisions"][teal]["certainty"], "grounded")
        self.assertEqual((selection["decisions"][bike]["evidence"], selection["decisions"][bike]["certainty"]),
                         ("attribute_undetermined", "uncertain"))
        self.assertEqual(selection["uncertain_count"], 1)
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
        # Policy 0.5.2: only an observation (a conflict of named subjects) grounds a decline;
        # facts that merely share no content term are delivered as uncertain (see next block).
        self.put("memory:a", "Bastien's umbrella is yellow.")
        self.put("memory:b", "Bastien's umbrella has a bent rib.")
        package = self.context("What colour is Odile's umbrella?")
        receipts.validate(context_package.PACKAGE_SCHEMA, package)
        self.assertEqual(package["status"], "empty")
        self.assertEqual(_delivered(package), [])
        self.assertEqual(package["selection"]["assessment"], "no_relevant_evidence")
        self.assertEqual(set(_omitted(package).values()), {"subject_mismatch"})
        self.assertEqual(package["budget"]["used_chars"], 0)
        # lexical absence alone is not a negative: delivered, labelled, assessment left open
        festival = self.put("memory:c", "The autumn science festival begins Friday.")
        package = self.context("What time does the lunar eclipse committee meet?")
        if festival in package["selection"]["decisions"]:  # admitted on function words only
            self.assertIn(festival, _delivered(package))
            self.assertEqual(package["selection"]["decisions"][festival]["evidence"], "undetermined_single_statement")
            self.assertEqual(package["selection"]["assessment"], "undetermined")
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

    def test_term_absence_is_never_grounded(self):
        # Policy 0.5.0 briefly grounded term absence for a longer third-person statement whose own
        # subject the query never mentioned; the owner's review (PR #843, 5628673295) showed that a
        # paraphrase shares no token and still answers, so 0.5.1 restored the 0.3.0 contract here.
        short = self.put("memory:a", "The autumn science festival begins Friday.")
        long = self.put("memory:b", "The autumn science festival begins Friday. The committee that plans "
                                    "the eclipse viewing meets afterwards in the same hall.")
        package = self.context("What time does the lunar eclipse committee meet?")
        decisions = package["selection"]["decisions"]
        # the short fact shares no content term with the question: uncertain, not declined (0.5.2)
        if short in decisions:
            self.assertEqual(decisions[short]["outcome"], "delivered")
            self.assertEqual(decisions[short]["evidence"], "undetermined_single_statement")
            self.assertEqual(decisions[short]["certainty"], "uncertain")
            self.assertNotIn("absence_grounding", decisions[short])
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

    def test_contracted_first_person_fact_is_not_a_third_party(self):
        mine = self.put("memory:a", "I'm looking for car wax; I've been using SpeedShine's detailing kit and just got back from Rack Fest.")
        package = self.context("How many days before the Rack Fest did I participate in the Turbocharged Tuesdays event?")
        self.assertIn(mine, _delivered(package))
        self.assertNotEqual(package["selection"]["decisions"][mine]["outcome"], "omitted")

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

    def test_attribute_absence_is_uncertainty_for_any_fact_size(self):
        bike = self.put("memory:a", "Liora's bicycle is black.")
        diary = self.put("memory:b", "Liora's week was busy. She repainted the boat shed on Monday. "
                                     "The paddles were ordered on Tuesday.")
        cello = self.put("memory:c", "Liora's eldest performs on the cello.")
        package = self.context("What color is Liora's canoe?")
        decisions = package["selection"]["decisions"]
        for ref in (bike, diary, cello):
            self.assertEqual((decisions[ref]["outcome"], decisions[ref]["evidence"], decisions[ref]["certainty"]),
                             ("delivered", "attribute_undetermined", "uncertain"), ref)
        # a paraphrased predicate is the owner's counterexample: it must never be declined
        package = self.context("Which instrument does Liora's child play?")
        self.assertIn(cello, _delivered(package))
        self.assertEqual(package["selection"]["decisions"][cello]["certainty"], "uncertain")

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


class SubjectConflictWithoutSharedTerms(_Store):
    """Policy 0.5.1 (Gate 2 remediation after the owner's independent review, PR #843 review
    5628673295). Policy 0.5.0 had declined any multi-statement third-person fact whose own named
    subject the query never mentioned; the review showed that this is lexical mismatch, not evidence
    (``Where did the aircraft touch down?`` / ``Captain Nia's plane landed at Orion Field.``), and
    0.5.1 withdrew it. What survives without a shared term is a conflict of named subjects: the query
    is about one named party, the fact grounds a different one and never mentions the query's."""

    def test_zero_overlap_fact_about_a_different_named_subject_is_a_subject_mismatch(self):
        canoe = self.put("memory:a", "Liora's canoe is teal. The hull was inspected on Tuesday.")
        mara = self.put("memory:b", "Mara's eldest performs on the cello. Their next recital is in November.")
        package = self.context("What color is Liora's canoe?")
        self.assertIn(canoe, _delivered(package))
        decision = package["selection"]["decisions"][mara]
        self.assertEqual((decision["outcome"], decision["reason"], decision["certainty"]),
                         ("omitted", "subject_mismatch", "grounded"))
        self.assertEqual(decision["query_subjects"], ["liora"])
        self.assertIn("mara", decision["fact_subjects"])  # plus the persisted proposition entity terms
        self.assertEqual(decision["matched_terms"], [])

    def test_query_without_a_named_subject_keeps_a_named_third_person_fact_as_uncertain(self):
        # the fact's own subject being absent from the query grounds nothing: "Captain Nia's
        # plane landed at Orion Field" answers "Where did the aircraft touch down?"
        liora = self.put("memory:a", "Liora's canoe is teal. The hull was inspected on Tuesday.")
        self.put("memory:b", "The office printer is a Brother HL-L2400D. Its toner is TN830.")
        package = self.context("What model is the office printer?")
        decision = package["selection"]["decisions"][liora]
        self.assertEqual((decision["outcome"], decision["evidence"], decision["certainty"]),
                         ("delivered", "undetermined_multi_statement", "uncertain"))
        verdict = context_selection.qualify(
            "Where did the aircraft touch down?", "ref-landing", {"route_provenance": [{"route_id": "lexical"}]},
            "Captain Nia's plane landed at Orion Field. The passengers cheered.", None)
        self.assertEqual((verdict["outcome"], verdict["certainty"]), ("delivered", "uncertain"))

    def test_named_query_subject_keeps_a_fact_naming_nobody_as_uncertain(self):
        canoe = self.put("memory:a", "Liora's canoe is teal. The hull was inspected on Tuesday.")
        exhibit = self.put("memory:b", "The moon exhibit has a new display case. The museum catalog is updated.")
        package = self.context("What color is Liora's canoe?")
        self.assertIn(canoe, _delivered(package))
        decision = package["selection"]["decisions"][exhibit]
        self.assertEqual((decision["outcome"], decision["evidence"], decision["certainty"]),
                         ("delivered", "undetermined_multi_statement", "uncertain"))

    def test_first_person_statement_without_shared_terms_stays_uncertain(self):
        mine = self.put("memory:a", "I've been practising a lot lately. The recital is in November, which is soon.")
        package = self.context("Which instrument does Liora's child play?")
        decision = package["selection"]["decisions"][mine]
        self.assertEqual((decision["outcome"], decision["evidence"], decision["certainty"]),
                         ("delivered", "undetermined_multi_statement", "uncertain"))
        package = self.context("Which instrument is the one I play?")
        self.assertIn(mine, _delivered(package))
        self.assertNotEqual(package["selection"]["decisions"][mine]["outcome"], "omitted")

    def test_persisted_proposition_entity_grounds_the_fact_subject_for_the_conflict_test(self):
        proposition = {"status": "known", "entity": "autumn science festival", "property": "begin", "value": "friday"}
        lexical = {"route_provenance": [{"route_id": "lexical"}]}
        text = "The autumn science festival begins Friday. Registration closes on Wednesday."
        # a named query subject against a different persisted entity, no shared term: conflict
        verdict = context_selection.qualify("When is Mara's recital?", "ref-festival", lexical, text, proposition)
        self.assertEqual((verdict["outcome"], verdict["reason"]), ("omitted", "subject_mismatch"))
        self.assertEqual(verdict["fact_subjects"], ["autumn", "festival", "scienc"])
        # no named query subject: uncertain, whatever the entity
        verdict = context_selection.qualify("When does the lunar eclipse committee meet?", "ref-festival", lexical, text, proposition)
        self.assertEqual((verdict["outcome"], verdict["evidence"]), ("delivered", "undetermined_multi_statement"))

    def test_single_statement_absence_is_uncertainty_not_grounding(self):
        verdict = context_selection.qualify(
            "What model is the office printer?", "ref-short",
            {"route_provenance": [{"route_id": "lexical"}]}, "Omar uses VS Code to edit Markdown documents.", None)
        self.assertEqual((verdict["outcome"], verdict["evidence"], verdict["certainty"]),
                         ("delivered", "undetermined_single_statement", "uncertain"))
        self.assertNotIn("absence_grounding", verdict)


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

    def test_contracted_first_person_markers_are_recognised(self):
        fp = context_selection.first_person
        for text in ("I'm looking for car wax; SpeedShine's kit works.", "I've been using Netflix.", "We'll go tomorrow.",
                     "I'd rather not.", "I participated in the event."):
            self.assertTrue(fp(text), text)
        self.assertFalse(fp("Priya's car is a silver Honda Civic."))
        # a contraction of a function word is not a content term
        self.assertNotIn("i'm", context_selection.content_terms("I'm looking for recommendations"))
        self.assertEqual(context_selection.content_terms("I'm here"), frozenset())

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
        self.assertEqual((verdict["outcome"], verdict["evidence"]), ("delivered", "undetermined_single_statement"))

    def test_assessment_tells_absence_from_uncertainty(self):
        a = context_selection.assessment
        self.assertEqual(a([]), "no_returned_candidates")
        self.assertEqual(a([{"outcome": "omitted"}]), "no_relevant_evidence")
        self.assertEqual(a([{"outcome": "delivered", "certainty": "uncertain"}, {"outcome": "omitted"}]), "undetermined")
        self.assertEqual(a([{"outcome": "delivered", "certainty": "grounded"}]), "evidence_delivered")
        # a fact that could not be inspected leaves the question open (PR #841 review)
        self.assertEqual(a([{"outcome": "unavailable", "state": "unresolved"}]), "undetermined")
        self.assertEqual(a([{"outcome": "unavailable", "state": "omitted_budget"}, {"outcome": "omitted"}]), "undetermined")
        self.assertEqual(a([{"outcome": "unavailable"}, {"outcome": "delivered", "certainty": "grounded"}]), "evidence_delivered")


if __name__ == "__main__":
    unittest.main()
