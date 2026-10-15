"""Morphology and typo tolerance in recall (#819 C3 slice 2, selection policy 2.1.0).

The weakness under test: exact-token matching missed "weddings" for "wedding", "attended" for
"attend" and any typo, both at candidate discovery and in relevance. The tests pin the repair
and attack it: the discovery vocabulary must never include forgotten, superseded or out-of-scope
text, typo correction must not override a word the memory actually contains, short words are
never "corrected", and ranking of exact matches is unchanged.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.runtime.lexical_normalization import (
    MAX_EXPANSIONS_PER_TERM,
    damerau_within_one,
    expansion_terms,
    normal_form,
    typo_matches,
)

TENANT = "tenant:lexical"
SCOPE = "project:lexical"


def _evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:lexical-lifecycle", version=1, purpose="lifecycle test", scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the lifecycle change.", provenance_refs=("evidence:test",),
    )
    return pm.evidence_for(skill)


class PureFunctions(unittest.TestCase):
    def test_inflectional_normal_forms(self):
        # Porter (1980) step-1 examples: plurals, -ed/-ing, terminal y.
        for word, stem in {"caresses": "caress", "ponies": "poni", "cats": "cat", "plastered": "plaster",
                           "motoring": "motor", "hopping": "hop", "filing": "file", "agreed": "agree",
                           "happy": "happi", "running": "run"}.items():
            self.assertEqual(normal_form(word), stem, word)

    def test_derivational_families_stay_apart(self):
        # Merging these would make morphology false evidence.
        self.assertNotEqual(normal_form("observability"), normal_form("observer"))
        self.assertNotEqual(normal_form("preferences"), normal_form("prefers"))
        self.assertNotEqual(normal_form("relational"), normal_form("relate"))
        self.assertEqual(normal_form("weddings"), normal_form("wedding"))
        self.assertEqual(normal_form("k8s"), "k8s")

    def test_typo_tolerance_is_one_edit_and_length_gated(self):
        self.assertTrue(damerau_within_one("typsecript", "typescript"))  # adjacent transposition
        self.assertFalse(damerau_within_one("typsecrpit", "typescript"))
        self.assertEqual(typo_matches("reedis", ["redis", "reeds", "radish"]), ("redis", "reeds"))
        self.assertEqual(typo_matches("eror", ["error"]), ())  # under five letters: never corrected

    def test_expansion_prefers_real_words_and_is_capped(self):
        vocab = {"mango", "mongo", "mangoes"}
        self.assertEqual(expansion_terms(["mango"], vocab)["typo"], ())  # the word exists: no correction
        many = {f"wedding{'s' * i}" for i in range(1, 2)} | {"wedded", "weddings", "wed"}
        out = expansion_terms(["wedding"], many)
        self.assertLessEqual(len(out["morphological"]), MAX_EXPANSIONS_PER_TERM)
        self.assertIn("weddings", out["morphological"])


class _Facade(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.memory = self.open(SCOPE)

    def tearDown(self):
        self.memory.close()
        self._dir.cleanup()

    def open(self, scope):
        return AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:t", scope=scope, purpose="lexical test")

    def put(self, ref, text):
        return self.memory.remember(ref, text)["fact_uuid"]


class Recall(_Facade):
    def test_inflections_meet(self):
        a = self.put("memory:a", "I attended Ana's wedding in May.")
        b = self.put("memory:b", "Tom's weddings are always outdoors.")
        self.put("memory:x", "Weekly planning call on Monday.")
        self.assertEqual(set(self.memory.recall("weddings?")["returned"]), {a, b})
        self.assertIn(a, self.memory.recall("which events did I attend?")["returned"])

    def test_typo_reaches_the_intended_memory(self):
        ts = self.put("memory:ts", "Writes TypeScript with strict mode.")
        result = self.memory.recall("typsecript compilation config")
        self.assertEqual(result["returned"], [ts])
        self.assertEqual(result["return_policy"]["query_expansion"]["typo_variant_count"], 1)

    def test_exact_ranking_is_unchanged_for_exact_matches(self):
        for i in range(4):
            self.put(f"memory:r{i}", f"redis cache eviction note {i}")
        ranked = self.memory.recall("redis cache eviction", return_selection="ranked_prefix")["admitted"]
        again = self.memory.recall("redis cache eviction", return_selection="ranked_prefix")["admitted"]
        self.assertEqual(ranked, again)


class TypoGuard(_Facade):
    def test_absent_topic_is_not_typo_corrected_into_noise(self):
        # "sending" is one edit from "spending"; the question is about something never remembered.
        self.put("memory:s", "Monthly spending on groceries was 400 dollars.")
        result = self.memory.recall("what is a good way to grade an old penny without sending it away?")
        self.assertEqual(result["returned"], [])

    def test_no_correction_when_the_topic_already_matched(self):
        ts = self.put("memory:ts", "Writes TypeScript with strict mode.")
        self.put("memory:s", "Spending report due Friday.")
        result = self.memory.recall("strict mode when sending code")
        self.assertEqual(result["returned"], [ts])
        self.assertEqual(result["return_policy"]["query_expansion"]["typo_variant_count"], 0)


class VocabularyNeverLeaks(_Facade):
    def test_forgotten_text_does_not_shape_discovery(self):
        secret = self.put("memory:secret", "Lisbon trip with Marguerite in May.")
        # Recall first, so the fact's tokens are resident in the planner's vocabulary memo.
        self.assertEqual(self.memory.recall("Marguerrite")["returned"], [secret])
        self.assertTrue(self.memory.forget("memory:secret", evidence=_evidence())["committed"])
        self.put("memory:other", "Book club meets on Thursdays.")
        result = self.memory.recall("Marguerrite")
        self.assertEqual(result.get("return_policy", {}).get("query_expansion", {}).get("typo_variant_count", 0), 0)
        self.assertEqual(result["returned"], [])

    def test_superseded_text_does_not_shape_discovery(self):
        old = self.put("memory:wine", "Porto wine tasting with Bernadette.")
        self.assertEqual(self.memory.recall("Bernadete")["returned"], [old])
        self.assertTrue(self.memory.correct("memory:wine", "Douro valley wine tasting.", evidence=_evidence())["committed"])
        result = self.memory.recall("Bernadete")
        self.assertEqual(result["return_policy"]["query_expansion"]["typo_variant_count"], 0)
        self.assertEqual(result["returned"], [])

    def test_other_scope_text_does_not_shape_discovery(self):
        self.memory.close()
        other = self.open("project:other")
        other.remember("memory:hidden", "Confidential acquisition codename Zephyrine.")
        other.close()
        self.memory = self.open(SCOPE)
        self.put("memory:mine", "Gardening on Saturday.")
        result = self.memory.recall("Zephyrinne")
        self.assertEqual(result["return_policy"]["query_expansion"]["typo_variant_count"], 0)
        self.assertEqual(result["returned"], [])


if __name__ == "__main__":
    unittest.main()
