"""Evidence-set construction (#819 C3 slice 1, selection policy 2.0.0).

The weakness under test: C2 treated every memory as an independent candidate against one
relative floor. Questions that need several pieces of evidence lost the weaker ones, and
question-frame words ("how many", "total", "months") counted as topical evidence, so incidental
matches set the scale. These tests pin the repair through the public facade and attack it:
frame-only matches, set cues with no topical evidence, keyword-stuffed facts, entity coverage
choosing the right fact, and governance (scope, forgetting, correction) left unchanged.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.runtime.query_interpretation import AGGREGATE, RELATIONAL, SINGLE
from agentmem_ref.runtime.return_selection import interpret_query, select_relevance_sufficient
from agentmem_ref.runtime.temporal_intent import TemporalIntent

TENANT = "tenant:evidence-set"
SCOPE = "project:evidence-set"


def _evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:evidence-set-lifecycle", version=1, purpose="lifecycle test", scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the lifecycle change.", provenance_refs=("evidence:test",),
    )
    return pm.evidence_for(skill)


class Interpretation(unittest.TestCase):
    def test_frame_words_are_not_topic(self):
        reading = interpret_query("How many magazine subscriptions do I currently have?")
        self.assertEqual(reading.topical_terms, ("magazine", "subscriptions"))
        self.assertIn("many", reading.frame_terms)
        self.assertEqual(reading.shape, AGGREGATE)

    def test_shapes(self):
        self.assertEqual(interpret_query("How much did I spend in total on flights?").shape, AGGREGATE)
        self.assertEqual(interpret_query("Did the move happen before the wedding?").shape, RELATIONAL)
        self.assertEqual(interpret_query("What is my dentist's name?").shape, SINGLE)

    def test_entities(self):
        reading = interpret_query("Should the Kubernetes pods report to GitHub Actions or to k8s logs?")
        self.assertEqual(set(reading.entity_mentions), {("kubernetes",), ("github",), ("actions",), ("k8s",)})
        self.assertEqual(interpret_query("I do NOT want Express here").entity_mentions, (("express",),))
        self.assertEqual(interpret_query("HOW MANY DOGS DO I HAVE").entity_mentions, ())

    def test_all_frame_query_keeps_its_words(self):
        reading = interpret_query("what did I do last week?")
        self.assertEqual(reading.topical_terms, ())
        self.assertEqual(set(reading.frame_terms), {"last", "week"})


class _Facade(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.memory = AgentMemory.open(Path(self._dir.name), tenant=TENANT, actor_id="agent:t", scope=SCOPE,
                                       purpose="evidence set test")

    def tearDown(self):
        self.memory.close()
        self._dir.cleanup()

    def put(self, ref, text):
        return self.memory.remember(ref, text)["fact_uuid"]


class EvidenceSets(_Facade):
    def test_aggregate_question_keeps_weaker_evidence_items(self):
        a = self.put("memory:c1", "I ran the charity bake sale for the animal shelter and we raised 400 dollars.")
        b = self.put("memory:c2", "At the charity gala in spring I helped at the auction table for most of the "
                                  "evening; the event went late and the food was great, and my feet hurt after.")
        c = self.put("memory:c3", "We did a long charity walk along the river; afterwards there was a picnic and a "
                                  "raffle, and I talked with old friends from school about their kids and jobs.")
        self.put("memory:noise1", "I had many meetings this month and the total was exhausting.")
        self.put("memory:noise2", "My sister has many cats.")
        result = self.memory.recall("How many charity events did I take part in in total?")
        self.assertEqual(set(result["returned"]), {a, b, c})
        self.assertEqual(result["return_policy"]["information_requirement"]["shape"], AGGREGATE)

    def test_single_answer_question_does_not_use_the_set_floor(self):
        # The same weaker partial match is set evidence for an aggregate question and withheld
        # for a single-answer one.
        dentist = self.put("memory:d", "My dentist Dr. Alvarez has the office on Pine Street near the clinic.")
        partial = self.put("memory:x", "The farmers market moved to a new spot this spring; it is now on Pine "
                                       "Street, next to the bakery with the blue awning.")
        single = self.memory.recall("Who is my dentist on Pine Street?")
        self.assertEqual(single["returned"], [dentist])
        self.assertEqual(single["admissions"][partial]["return_selection"]["basis"], "below_relative_floor")
        many = self.memory.recall("How many places on Pine Street do I go to?")
        self.assertIn(partial, many["returned"])

    def test_frame_only_matches_are_not_evidence(self):
        dogs = self.put("memory:dogs", "We have two dogs, Pepper and Juno.")
        self.put("memory:frame", "Many months ago we had many plans; in total it was a busy year.")
        result = self.memory.recall("How many dogs do we have in total?")
        self.assertEqual(result["returned"], [dogs])

    def test_set_cue_without_topical_evidence_abstains(self):
        self.put("memory:frame", "I have many meetings every week and several projects in total.")
        result = self.memory.recall("How many unicorns do I own in total?")
        self.assertEqual(result["returned"], [])
        self.assertTrue(result["return_policy"]["abstained"])

    def test_all_frame_query_uses_frame_words(self):
        last_week = self.put("memory:lw", "Last week I repainted the fence.")
        result = self.memory.recall("what did I do last week?")
        self.assertIn(last_week, result["returned"])
        self.assertTrue(result["return_policy"]["frame_fallback"])

    def test_every_named_entity_is_covered_by_the_fact_about_it(self):
        react = self.put("memory:react", "The frontend is React 18 with React Query; React components are typed.")
        mongo = self.put("memory:mongo", "MongoDB raw driver with typed MongoDB collections; MongoDB is the database.")
        self.put("memory:dlq", "Failed messages go to a dead letter queue, which is stored in MongoDB, with "
                               "manual replay from the admin console and alerting on the replay backlog.")
        errors = self.put("memory:errors", "Error handling uses explicit error returns; error values, not "
                                           "exceptions, carry error handling across the React and API layers.")
        result = self.memory.recall("How should React error handling work with MongoDB?")
        # 2.3.0 (#819 C4): the error-handling fact names React with enough relevance to cover it,
        # so the React fact is no longer added for the name alone; MongoDB, which no selected fact
        # covers, is still covered by the fact most about it.
        self.assertTrue({mongo, errors} <= set(result["returned"]))
        decisions = {r: result["admissions"][r]["return_selection"]["basis"] for r in result["returned"]}
        self.assertNotIn("entity_coverage", [decisions.get(r) for r in result["returned"] if r not in {react, mongo, errors}])

    def test_stuffed_fact_cannot_claim_every_entity(self):
        mongo = self.put("memory:mongo", "MongoDB raw driver with typed MongoDB collections.")
        self.put("memory:stuff", "react mongodb kubernetes typescript react mongodb kubernetes typescript")
        result = self.memory.recall("What MongoDB pattern do we use?")
        self.assertIn(mongo, result["returned"])

    def test_selection_is_deterministic_and_a_ranked_subsequence(self):
        for i in range(8):
            self.put(f"memory:t{i}", f"Trip {i}: we flew to city {i} and the flight cost {100 + i} dollars in total.")
        first = self.memory.recall("How much did all my flights cost in total?", budget=5)
        second = self.memory.recall("How much did all my flights cost in total?", budget=5)
        self.assertEqual(first["returned"], second["returned"])
        positions = [first["admitted"].index(r) for r in first["returned"]]
        self.assertEqual(positions, sorted(positions))
        self.assertLessEqual(len(first["returned"]), 5)


class SetEvidenceDoesNotAnchorRanking(unittest.TestCase):
    def test_weak_fact_ranked_above_set_evidence_stays_withheld(self):
        # 2.1.0: ranking consistency extends only from primary evidence. A set member ranked low
        # must not pull in a fact above it whose only evidence is a passing topical trace.
        texts = {
            "strong": "Charity runs: the spring charity run and the autumn charity run for the shelter.",
            "trace": "We went for runs along the river most weekends, then had brunch with my cousins, walked "
                     "the dog, cleaned the flat, called my parents and watched a film.",
            "set": "I volunteered at the charity book fair in town on Saturday afternoon.",
            "other": "Bought new shoes.",
        }
        facts = {ref: SimpleNamespace(fact_text=text, attributes={}) for ref, text in texts.items()}
        selected, records, _ = select_relevance_sufficient(
            list(texts), {ref: ("lexical",) for ref in texts}, facts.get, query="How many charity runs did I do?",
            intent=TemporalIntent(), lexical_route="lexical", exact_identity_route="exact_logical_identity")
        self.assertEqual(selected, ["strong", "set"])
        self.assertEqual(records["set"]["basis"], "set_evidence")
        self.assertEqual(records["trace"]["basis"], "below_relative_floor")


class GovernanceUnchanged(_Facade):
    def test_set_evidence_never_includes_forgotten_or_superseded_or_other_scope(self):
        kept = self.put("memory:w1", "I went to Ana's wedding in May.")
        gone = self.put("memory:w2", "I went to a wedding in Lisbon in June.")
        old = self.put("memory:w3", "I went to Tom's wedding in July.")
        self.assertTrue(self.memory.forget("memory:w2", evidence=_evidence())["committed"])
        new = self.memory.correct("memory:w3", "I went to Tom's wedding in August, not July.", evidence=_evidence())
        self.assertTrue(new["committed"])
        self.memory.close()  # one handle at a time on a store
        other = AgentMemory.open(Path(self._dir.name), tenant=TENANT, actor_id="agent:t", scope="project:other",
                                 purpose="other scope")
        hidden = other.remember("memory:w4", "Private: I went to a secret wedding.")["fact_uuid"]
        other.close()
        self.memory = AgentMemory.open(Path(self._dir.name), tenant=TENANT, actor_id="agent:t", scope=SCOPE,
                                       purpose="evidence set test")
        result = self.memory.recall("How many times did I attend a wedding?")
        self.assertIn(kept, result["returned"])
        self.assertIn(new["fact_uuid"], result["returned"])
        for ref in (gone, old, hidden):
            self.assertNotIn(ref, result["returned"])
            self.assertNotIn(ref, result["admitted"])


if __name__ == "__main__":
    unittest.main()
