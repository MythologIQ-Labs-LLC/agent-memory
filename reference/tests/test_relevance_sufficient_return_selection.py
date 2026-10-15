"""Relevance-sufficient return selection (#819, contract 1.9.0).

The architectural weakness under test: before 1.9.0 ``returned`` was the ranked admitted
prefix, and the lexical route admits any fact sharing any token with the query, so a recall
returned ``min(k, admitted)`` facts however weak the match. These tests pin the repair through
the public facade and the selection function, and pin that it leaves governance alone:
admission, ``admitted``, ranking, isolation, forgetting and correction behave as before.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from agentmem_ref import AgentMemory
from agentmem_ref.api import contract
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.runtime.return_selection import (
    FUNCTION_WORDS,
    RELATIVE_FLOOR,
    informative_terms,
    select_relevance_sufficient,
)
from agentmem_ref.runtime.temporal_intent import TemporalIntent

TENANT = "tenant:selection"
SCOPE = "project:selection"
ACTOR = "agent:selection"


def _evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:selection-correction",
        version=1,
        purpose="correct retained test memory",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the correction against the current source.",
        provenance_refs=("evidence:selection-source",),
    )
    return pm.evidence_for(skill)


class _Facade(unittest.TestCase):
    def setUp(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.memory = self.open()

    def tearDown(self) -> None:
        self.memory.close()
        self._dir.cleanup()

    def open(self, scope: str = SCOPE) -> AgentMemory:
        return AgentMemory.open(self.root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="selection test")


class InformativeTerms(unittest.TestCase):
    def test_function_words_and_single_letters_are_not_evidence(self):
        self.assertEqual(informative_terms("What's my k8s deploy story?"), ("deploy", "k8s", "story"))
        self.assertEqual(informative_terms("how do I want you to respond to me?"), ("respond", "want"))
        self.assertEqual(informative_terms("is it the one?"), ("one",))
        self.assertEqual(informative_terms("is it the?"), ())

    def test_digits_survive_and_order_is_canonical(self):
        self.assertEqual(informative_terms("rules for chapter 7, chapter 7"), ("7", "chapter", "rules"))

    def test_list_is_grammar_only(self):
        # Content words that carry topic must never be function words (no tuning by stoplist).
        for word in ("deploy", "budget", "database", "redis", "chapter", "pattern", "use", "want", "project",
                     "like", "one", "past", "near", "mine", "won", "don"):
            self.assertNotIn(word, FUNCTION_WORDS)

    def test_contractions_do_not_leak_fragments(self):
        # 1.1.0: "don't" is "do not", not the name "don"; clitics vanish; single letters stay.
        self.assertEqual(informative_terms("I don't want class hierarchies"), ("class", "hierarchies", "want"))
        self.assertEqual(informative_terms("what's Mara's backstory? I'm curious"), ("backstory", "curious", "mara"))
        self.assertEqual(informative_terms("won't they take Vitamin D or plan B"), ("b", "d", "plan", "take", "vitamin"))

    def test_function_words_written_as_names_are_evidence(self):
        self.assertEqual(informative_terms("Who is Will?"), ("will",))
        self.assertEqual(informative_terms("Will it rain tomorrow?"), ("rain", "tomorrow"))
        self.assertEqual(informative_terms("What happened in May?"), ("happened", "may"))
        self.assertEqual(informative_terms("When did I move to the US?"), ("move", "us"))
        # Title case and all capitals say nothing about names.
        self.assertEqual(informative_terms("How Should I Structure My Repository Layer?"),
                         ("layer", "repository", "structure"))
        self.assertEqual(informative_terms("WHO IS IT"), ())


class SelectionFunction(unittest.TestCase):
    def _facts(self, texts):
        return {ref: SimpleNamespace(fact_text=text, attributes={}) for ref, text in texts.items()}

    def _select(self, texts, routes, query, ranked=None, **kwargs):
        facts = self._facts(texts)
        return select_relevance_sufficient(
            ranked or list(texts), routes, facts.get, query=query, intent=TemporalIntent(),
            lexical_route="lexical", exact_identity_route="exact_logical_identity",
            subordinate_routes=("semantic_vector",), **kwargs)

    def test_relative_floor_withholds_weak_partial_matches(self):
        texts = {
            "strong": "kubernetes cluster deploys with helm charts on kubernetes",
            "weak": "the deploy goes to staging after merge",
            "noise": "what is the plan for this one",
        }
        routes = {ref: ["lexical"] for ref in texts}
        selected, records, summary = self._select(texts, routes, "what is our kubernetes helm setup")
        self.assertEqual(selected, ["strong"])
        self.assertEqual(records["noise"]["basis"], "no_informative_term_match")
        self.assertEqual(records["strong"]["basis"], "content_relevance")
        self.assertFalse(summary["abstained"])
        self.assertEqual(summary["relative_floor"], RELATIVE_FLOOR)

    def test_abstains_when_only_function_words_match(self):
        texts = {"a": "what is the plan", "b": "how should we do this"}
        selected, records, summary = self._select(texts, {r: ["lexical"] for r in texts}, "what should we do")
        self.assertEqual(selected, [])
        self.assertTrue(summary["abstained"])
        self.assertEqual(summary["withheld_insufficient_count"], 2)
        self.assertTrue(all(not record["sufficient"] for record in records.values()))

    def test_exact_identity_and_non_lexical_routes_are_not_withheld(self):
        texts = {"exact": "nothing in common", "relational": "also unrelated", "lexical": "kubernetes helm"}
        routes = {"exact": ["exact_logical_identity"], "relational": ["shared_evidence_neighbor"],
                  "lexical": ["lexical"]}
        selected, records, _ = self._select(texts, routes, "kubernetes")
        self.assertEqual(selected, ["exact", "relational", "lexical"])
        self.assertEqual(records["exact"]["basis"], "exact_identity")
        self.assertEqual(records["relational"]["basis"], "non_lexical_route_evidence")

    def test_selection_preserves_ranked_order(self):
        texts = {"x": "alpha beta", "y": "alpha beta gamma", "z": "delta"}
        selected, _, _ = self._select(texts, {r: ["lexical"] for r in texts}, "alpha beta", ranked=["y", "z", "x"])
        self.assertEqual(selected, ["y", "x"])

    def test_selection_never_drops_a_topical_fact_ranked_above_a_selected_one(self):
        # 1.1.0 (independent review finding 1): a query-term-stuffed fact may be the content
        # best, but the fact ranking put above it keeps its place if it has topical evidence.
        texts = {"canonical": "the production database is postgres", "stuffed": "production database database team"}
        selected, records, _ = self._select(texts, {r: ["lexical"] for r in texts},
                                            "production database team", ranked=["canonical", "stuffed"])
        self.assertEqual(selected, ["canonical", "stuffed"])
        self.assertEqual(records["canonical"]["basis"], "ranked_above_sufficient")
        noise = {"noise": "what is this", "topic": "kubernetes helm"}
        selected, records, _ = self._select(noise, {r: ["lexical"] for r in noise}, "what is kubernetes",
                                            ranked=["noise", "topic"])
        self.assertEqual(selected, ["topic"])
        self.assertEqual(records["noise"]["basis"], "no_informative_term_match")

    def test_floor_must_be_a_fraction(self):
        with self.assertRaises(ValueError):
            self._select({"a": "x"}, {"a": ["lexical"]}, "x", relative_floor=0.0)

    def test_contract_rejects_a_selection_that_is_not_a_ranked_subsequence(self):
        summary = {"withheld_insufficient_count": 0, "abstained": False, "informative_query_term_count": 1,
                   "relative_floor": 0.5}
        with self.assertRaises(ValueError):
            contract.apply_return_selection(["a", "b"], ["b", "a"], None, summary)
        with self.assertRaises(ValueError):
            contract.apply_return_selection(["a", "b"], ["c"], None, summary)


class FacadeSelection(_Facade):
    def test_default_withholds_function_word_noise_but_admits_it(self):
        topical = self.memory.remember("memory:k8s", "Deploys services to a Kubernetes cluster on EKS with Helm.")
        self.memory.remember("memory:style", "Prefers how options are presented: one recommendation.")
        self.memory.remember("memory:deploy", "Merge to main triggers a deploy to staging.")
        result = self.memory.recall("how do we run Kubernetes with Helm?", budget=20)
        legacy = self.memory.recall("how do we run Kubernetes with Helm?", budget=20, return_selection="ranked_prefix")
        self.assertEqual(result["returned"], [topical["fact_uuid"]])
        self.assertEqual(result["admitted"], legacy["admitted"])
        self.assertEqual(result["candidates"], legacy["candidates"])
        self.assertGreater(len(legacy["returned"]), 1)
        policy = result["return_policy"]
        self.assertEqual(policy["policy_id"], contract.RETURN_SELECTION_POLICY_ID)
        self.assertEqual(policy["authority_effect"], "none")
        self.assertEqual(policy["withheld_insufficient_count"], len(result["admitted"]) - 1)
        for ref in result["admitted"]:
            self.assertIn("return_selection", result["admissions"][ref])
            self.assertEqual(result["admissions"][ref]["return_selection"]["authority_effect"], "none")

    def test_stuffed_fact_cannot_displace_the_top_ranked_fact(self):
        # Independent review repro (finding 1), through the facade.
        canonical = self.memory.remember("memory:db", "The production database is Postgres 15.")
        self.memory.remember("memory:stuffed",
                             "Production database database team staging backup migration schema replica: ask Bob.")
        query = "What production database does the team use?"
        legacy = self.memory.recall(query, budget=1, return_selection="ranked_prefix")
        result = self.memory.recall(query, budget=1)
        self.assertEqual(legacy["returned"], [canonical["fact_uuid"]])
        self.assertEqual(result["returned"], [canonical["fact_uuid"]])

    def test_names_that_are_function_words_are_recalled(self):
        # Independent review repro (finding 2): these abstained under policy 1.0.0.
        will = self.memory.remember("memory:will", "Will is my brother.")
        may = self.memory.remember("memory:move", "I moved to the US in May.")
        like = self.memory.remember("memory:music", "I like jazz and blues.")
        self.assertEqual(self.memory.recall("Who is Will?")["returned"], [will["fact_uuid"]])
        self.assertIn(may["fact_uuid"], self.memory.recall("What happened in May?")["returned"])
        self.assertEqual(self.memory.recall("What do I like?")["returned"], [like["fact_uuid"]])

    def test_abstains_on_unrelated_query(self):
        self.memory.remember("memory:a", "The team uses a weekly planning meeting on Monday.")
        result = self.memory.recall("what is a good way to grade an old coin?", budget=5)
        self.assertEqual(result["returned"], [])
        self.assertTrue(result["return_policy"]["abstained"] or not result["admitted"])

    def test_ranked_prefix_reproduces_contract_1_4_0(self):
        for index in range(4):
            self.memory.remember(f"memory:n{index}", f"release branch note {index} for the team")
        legacy = self.memory.recall("what is the release branch for the team?", budget=2, return_selection="ranked_prefix")
        self.assertEqual(legacy["returned"], legacy["admitted"][:2])
        self.assertEqual(legacy["return_policy"]["policy_id"], contract.RETURN_POLICY_ID)
        self.assertEqual(legacy["return_policy"]["policy_version"], "1.0.0")
        for ref in legacy["admitted"]:
            self.assertNotIn("return_selection", legacy["admissions"][ref])

    def test_budget_applies_after_selection_and_returned_is_ranked_subsequence(self):
        for index in range(5):
            self.memory.remember(f"memory:r{index}", f"redis cache eviction policy variant {index}")
        result = self.memory.recall("redis cache eviction", budget=3)
        self.assertEqual(len(result["returned"]), 3)
        positions = [result["admitted"].index(ref) for ref in result["returned"]]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(result["return_policy"]["applied"])
        self.assertEqual(result["return_policy"]["sufficient_count"], 5)

    def test_exact_identity_is_returned_without_lexical_evidence(self):
        retained = self.memory.remember("memory:deadline", "Quarterly filing deadline is April 15.")
        result = self.memory.recall("what should I do?", logical_memory_refs=("memory:deadline",))
        self.assertEqual(result["returned"], [retained["fact_uuid"]])
        self.assertEqual(result["admissions"][retained["fact_uuid"]]["return_selection"]["basis"], "exact_identity")

    def test_invalid_selection_is_refused(self):
        with self.assertRaises(ValueError):
            self.memory.recall("anything", return_selection="top_one")

    def test_recall_is_deterministic(self):
        for index in range(6):
            self.memory.remember(f"memory:d{index}", f"vitest testing preference {index} replaced jest")
        first = self.memory.recall("should I configure jest for this project?", budget=4)
        second = self.memory.recall("should I configure jest for this project?", budget=4)
        self.assertEqual(first["returned"], second["returned"])
        self.assertEqual(first["return_policy"], second["return_policy"])


class SelectionPreservesGovernance(_Facade):
    def test_other_scope_is_never_returned(self):
        self.memory.close()
        other = self.open(scope="project:other")
        hidden = other.remember("memory:secret", "Other user uses Haskell exclusively for kubernetes tooling.")
        other.close()
        self.memory = self.open()
        mine = self.memory.remember("memory:mine", "We deploy kubernetes with helm charts.")
        for selection in ("relevance_sufficient", "ranked_prefix"):
            result = self.memory.recall("haskell kubernetes tooling", return_selection=selection)
            self.assertNotIn(hidden["fact_uuid"], result["candidates"])
            self.assertNotIn(hidden["fact_uuid"], result["returned"])
        self.assertIn(mine["fact_uuid"], self.memory.recall("kubernetes helm")["returned"])

    def test_forgotten_fact_is_not_returned(self):
        seed = self.memory.remember("memory:temp", "temporary staging credentials rotation detail")
        self.assertTrue(self.memory.forget("memory:temp", evidence=_evidence())["committed"])
        result = self.memory.recall("staging credentials rotation", logical_memory_refs=("memory:temp",))
        self.assertNotIn(seed["fact_uuid"], result["admitted"])
        self.assertNotIn(seed["fact_uuid"], result["returned"])

    def test_corrected_value_replaces_the_superseded_one(self):
        old = self.memory.remember("memory:db", "Database choice is Postgres with SQLAlchemy.")
        new = self.memory.correct("memory:db", "Database choice is MongoDB with the raw driver.",
                                  evidence=_evidence())
        self.assertTrue(new["committed"])
        result = self.memory.recall("which database choice did we make: Postgres or MongoDB?")
        self.assertIn(new["fact_uuid"], result["returned"])
        self.assertNotIn(old["fact_uuid"], result["admitted"])
        self.assertNotIn(old["fact_uuid"], result["returned"])


if __name__ == "__main__":
    unittest.main()
