"""Selection precision without losing evidence completeness (#819 C4, selection policy 2.3.0).

C3 recovered multi-evidence recall but returned facts no requirement asked for:

* **Entity coverage** added "the fact most about" an entity the selected evidence already
  covered ("What's Mom's mailing address?" also returned "Mom loves knitting...").
* **Ranking consistency** promoted any weak fact ranked above the *lowest* primary fact, so
  ordinary ordering noise among similar facts became returned evidence.
* **Redundant single answers**: for a one-answer question, a fact that matches only part of
  what an already-selected, higher-ranked fact matches was returned beside it.

These cases are newly authored ordinary memories (no benchmark text). They pin the repair and
the completeness C3 recovered: aggregate questions keep every item, an uncovered entity is still
covered, a fact ranking places above the best match keeps its place, and governance holds.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.runtime.return_selection import select_relevance_sufficient
from agentmem_ref.runtime.temporal_intent import TemporalIntent

TENANT = "tenant:c4"
SCOPE = "project:c4"


def _evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:c4-lifecycle", version=1, purpose="lifecycle test", scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the lifecycle change.", provenance_refs=("evidence:test",),
    )
    return pm.evidence_for(skill)


def _select(texts, query, ranked=None):
    facts = {ref: SimpleNamespace(fact_text=text, attributes={}) for ref, text in texts.items()}
    return select_relevance_sufficient(
        ranked or list(texts), {ref: ("lexical",) for ref in texts}, facts.get, query=query,
        intent=TemporalIntent(), lexical_route="lexical", exact_identity_route="exact_logical_identity")


class _Facade(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.memory = AgentMemory.open(Path(self._dir.name), tenant=TENANT, actor_id="agent:t", scope=SCOPE,
                                       purpose="c4 test")

    def tearDown(self):
        self.memory.close()
        self._dir.cleanup()

    def put(self, ref, text):
        return self.memory.remember(ref, text)["fact_uuid"]


class CoveredEntitiesAddNothing(_Facade):
    def test_entity_already_covered_by_the_answer(self):
        address = self.put("memory:addr", "Mom's new mailing address is 41 Alder Lane, Ridgefield.")
        self.put("memory:knit", "Mom loves knitting; Mom's cat Pickles sleeps on Mom's yarn basket.")
        self.put("memory:dad", "Dad's address is 9 Birch Road.")
        result = self.memory.recall("What's Mom's mailing address?")
        self.assertEqual(result["returned"], [address])

    def test_uncovered_entity_is_still_covered(self):
        flask = self.put("memory:flask", "The Flask app deploys through a Procfile; every deploy runs migrations first.")
        heroku = self.put("memory:heroku", "Heroku account is on the team plan; Heroku dynos are standard-2x.")
        self.put("memory:other", "Lunch with the design team on Friday.")
        result = self.memory.recall("How do we deploy the Flask app to Heroku?")
        self.assertTrue({flask, heroku} <= set(result["returned"]))

    def test_passing_mention_does_not_count_as_coverage(self):
        # The answer mentions Rex only in passing; the fact about Rex is still needed.
        vet = self.put("memory:vet", "Booked the vet for Saturday at 10; bring the vaccination card and Rex.")
        rex = self.put("memory:rex", "Rex is allergic to chicken; Rex takes Apoquel daily and Rex hates baths.")
        result = self.memory.recall("What should I tell the vet about Rex?")
        self.assertTrue({vet, rex} <= set(result["returned"]))


class RedundantSingleAnswers(_Facade):
    def test_partial_match_beside_a_full_answer_is_withheld(self):
        phone = self.put("memory:phone", "My sister Ava's phone number is 07700 900123.")
        self.put("memory:case", "I need to buy a new phone case.")
        self.put("memory:visit", "My sister is visiting in June.")
        result = self.memory.recall("What's my sister's phone number?")
        self.assertEqual(result["returned"], [phone])

    def test_equal_matches_are_both_kept(self):
        # Two facts that answer equally well (possibly conflicting) are not collapsed.
        old = self.put("memory:old", "Gate code for the garage is 4471.")
        new = self.put("memory:new", "New gate code for the garage is 9032.")
        result = self.memory.recall("What is the garage gate code?")
        self.assertEqual(set(result["returned"]), {old, new})

    def test_aggregate_question_keeps_every_item(self):
        refs = [self.put(f"memory:c{i}", text) for i, text in enumerate((
            "Went to the Arctic Monkeys concert in March with Leo.",
            "The jazz concert at the Blue Room in May was packed.",
            "Saw a small folk concert at the library in July."))]
        self.put("memory:noise", "The concert hall parking costs ten dollars.")
        result = self.memory.recall("How many concerts did I go to this year?")
        self.assertTrue(set(refs) <= set(result["returned"]))


class RankingConsistency(unittest.TestCase):
    def test_noise_between_primary_facts_is_not_promoted(self):
        texts = {
            "first": "the staging cluster runs postgres 15 for billing",
            "weak": "billing meeting moved to thursday afternoon in room four",
            "second": "the staging cluster backup runs postgres dumps nightly",
        }
        selected, records, _ = _select(texts, "staging cluster postgres billing", ranked=["first", "weak", "second"])
        self.assertNotIn("weak", selected)
        self.assertEqual(records["weak"]["basis"], "below_relative_floor")

    def test_fact_ranked_above_the_best_match_keeps_its_place(self):
        texts = {"canonical": "the production database is postgres", "stuffed": "production database database team"}
        selected, records, _ = _select(texts, "production database team", ranked=["canonical", "stuffed"])
        self.assertEqual(selected, ["canonical", "stuffed"])
        self.assertEqual(records["canonical"]["basis"], "ranked_above_sufficient")


class Diagnostics(_Facade):
    def test_every_admitted_fact_says_why(self):
        phone = self.put("memory:phone", "My sister Ava's phone number is 07700 900123.")
        visit = self.put("memory:visit", "My sister is visiting in June.")
        result = self.memory.recall("What's my sister's phone number?")
        chosen = result["admissions"][phone]["return_selection"]
        withheld = result["admissions"][visit]["return_selection"]
        self.assertEqual(chosen["requirement"], "single")
        self.assertEqual(chosen["query_terms_matched"], 3)
        self.assertEqual(chosen["query_terms_added"], 3)
        self.assertFalse(withheld["sufficient"])
        self.assertEqual(withheld["basis"], "dominated_by_selected")
        self.assertEqual(withheld["dominated_by"], phone)  # an admitted, returned fact only
        self.assertEqual(withheld["query_terms_added"], 0)


class GovernanceUnchanged(_Facade):
    def test_corrected_answer_only(self):
        self.put("memory:mom", "Mom's mailing address is 12 Elm Street.")
        self.put("memory:card", "Mom's birthday card is in the hall drawer.")
        corrected = self.memory.correct("memory:mom", "Mom's mailing address is now 41 Alder Lane.", evidence=_evidence())
        self.assertTrue(corrected["committed"])
        result = self.memory.recall("What's Mom's mailing address?")
        self.assertEqual(result["returned"], [corrected["fact_uuid"]])

    def test_forgotten_fact_never_dominates_or_is_named(self):
        gone = self.put("memory:gone", "My sister Ava's phone number is 07700 900123.")
        visit = self.put("memory:visit", "My sister is visiting in June.")
        self.assertTrue(self.memory.forget("memory:gone", evidence=_evidence())["committed"])
        result = self.memory.recall("What's my sister's phone number?")
        self.assertNotIn(gone, result["admitted"])
        # Selection diagnostics never name a non-admitted fact. (Refused candidates' own
        # admission records are pre-existing behaviour; public deleted-lineage redaction is #777,
        # on the security stack.)
        selection = [record.get("return_selection") for record in result["admissions"].values()]
        self.assertNotIn(gone, str([record for record in selection if record]))
        self.assertIn(visit, result["returned"])

    def test_ranked_prefix_unchanged(self):
        for i in range(3):
            self.put(f"memory:{i}", f"My sister note {i} about phone plans")
        result = self.memory.recall("What's my sister's phone number?", return_selection="ranked_prefix")
        self.assertEqual(result["returned"], result["admitted"])
        self.assertNotIn("return_selection", str(result["admissions"]))


if __name__ == "__main__":
    unittest.main()
