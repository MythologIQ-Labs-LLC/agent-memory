"""#819 Gate 2 bounded runtime candidate: content-term lexical admission (experiment branch only).

``AGENT_MEMORY_EXPERIMENTAL_LEXICAL_ADMISSION=content_term`` keeps a lexical candidate only when it
shares a content term (``core.content_terms``) with the query. Unset, the default, recall is
unchanged. These tests pin both sides, including the recall the flag gives up.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentmem_ref import AgentMemory
from agentmem_ref.runtime import adapter

FLAG = {adapter.EXPERIMENTAL_LEXICAL_ADMISSION_ENV: "content_term"}
TENANT, SCOPE = "tenant:admission", "project:admission"


class _Store(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.memory = AgentMemory.open(Path(self._dir.name) / "m", tenant=TENANT, actor_id="agent:admission",
                                       scope=SCOPE, purpose="admission experiment")
        self.addCleanup(self.memory.close)

    def put(self, ref, text):
        out = self.memory.remember(ref, text)
        self.assertTrue(out["committed"], out)
        return out["fact_uuid"]

    def returned(self, query, **kwargs):
        return self.memory.recall_context(query, max_items=10, **kwargs)["recall"]["returned"]


class DefaultIsUnchanged(_Store):
    def test_unset_flag_still_admits_on_function_words(self):
        festival = self.put("memory:a", "The autumn science festival begins Friday.")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(adapter.EXPERIMENTAL_LEXICAL_ADMISSION_ENV, None)
            self.assertIn(festival, self.returned("What time does the lunar eclipse committee meet?"))

    def test_off_and_empty_mean_unset(self):
        for value in ("", "off"):
            with mock.patch.dict(os.environ, {adapter.EXPERIMENTAL_LEXICAL_ADMISSION_ENV: value}):
                self.assertIsNone(adapter.experimental_lexical_admission())

    def test_unknown_value_is_refused(self):
        with mock.patch.dict(os.environ, {adapter.EXPERIMENTAL_LEXICAL_ADMISSION_ENV: "stopwords"}):
            with self.assertRaises(ValueError):
                adapter.experimental_lexical_admission()


class ContentTermAdmission(_Store):
    def test_function_word_only_candidates_are_not_admitted(self):
        self.put("memory:a", "The autumn science festival begins Friday.")
        self.put("memory:b", "The moon exhibit has a new display case.")
        with mock.patch.dict(os.environ, FLAG):
            package = self.memory.recall_context("What time does the lunar eclipse committee meet?",
                                                 consumer_profile="evidence_qualified", max_items=10)
        self.assertEqual(package["recall"]["returned"], [])
        self.assertEqual(package["status"], "empty")
        self.assertEqual(package["selection"]["assessment"], "no_returned_candidates")

    def test_morphological_variants_still_admit(self):
        needed = self.put("memory:a", "I graduated with a degree in Business Administration last spring.")
        with mock.patch.dict(os.environ, FLAG):
            self.assertIn(needed, self.returned("What degrees did my friends graduate with?"))

    def test_a_possessive_clitic_is_not_a_shared_term(self):
        canoe = self.put("memory:a", "Liora's canoe is teal.")
        dog = self.put("memory:b", "Mara's dog is asleep.")
        with mock.patch.dict(os.environ, FLAG):
            returned = self.returned("What color is Liora's canoe?")
        self.assertIn(canoe, returned)
        self.assertNotIn(dog, returned)

    def test_known_cost_a_paraphrase_sharing_no_content_term_is_not_retrieved(self):
        # The flag's recall cost, pinned rather than hidden: today this fact reaches the caller
        # only because it shares "the"/"is" with the question; under the flag the lexical route
        # cannot see it (as FTS5 cannot). A non-lexical route would be needed to find it.
        practice = self.put("memory:a", "I've been practising a lot lately. The recital is in November.")
        query = "Which instrument is the one I play?"
        with mock.patch.dict(os.environ, {}):  # restores the caller's environment afterwards
            os.environ.pop(adapter.EXPERIMENTAL_LEXICAL_ADMISSION_ENV, None)
            self.assertIn(practice, self.returned(query))
        with mock.patch.dict(os.environ, FLAG):
            self.assertNotIn(practice, self.returned(query))


if __name__ == "__main__":
    unittest.main()
