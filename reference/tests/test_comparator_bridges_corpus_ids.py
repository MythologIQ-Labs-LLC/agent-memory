"""Offline checks for repeated-session handling in the #811/#640/#817 comparator bridges."""
from __future__ import annotations

import importlib
import types
import unittest

jev = importlib.import_module("longmemeval_jev_mem_bridge")
cognee_bridge = importlib.import_module("longmemeval_cognee_bridge")
hindsight_bridge = importlib.import_module("longmemeval_hindsight_bridge")

ITEMS = [{"id": "a", "text": "x", "date": "d"}, {"id": "b", "text": "y", "date": "d"},
         {"id": "a", "text": "x", "date": "d"}]


class CorpusIdTests(unittest.TestCase):
    def test_identical_repeats_are_accepted_by_every_bridge(self):
        for module in (jev, cognee_bridge, hindsight_bridge):
            self.assertEqual(module.validate_corpus_ids(ITEMS), ["a", "b", "a"])

    def test_conflicting_repeat_or_bad_id_is_refused(self):
        for module in (jev, cognee_bridge, hindsight_bridge):
            with self.assertRaisesRegex(ValueError, "different text"):
                module.validate_corpus_ids([{"id": "a", "text": "x"}, {"id": "a", "text": "z"}])
            with self.assertRaises(ValueError):
                module.validate_corpus_ids([{"id": "", "text": "x"}])

    def test_cognee_occurrences_get_distinct_opaque_ids_that_map_back(self):
        native = cognee_bridge.occurrence_ids(["a", "b", "a"])
        self.assertEqual(len(set(native)), 3)
        self.assertEqual(native[0], cognee_bridge.opaque_id("a"))
        by_uuid = {str(n): [d] for n, d in zip(native, ["a", "b", "a"])}
        entries = [types.SimpleNamespace(search_type="CHUNKS", kind="chunk", metadata={"data_id": str(native[2])}),
                   types.SimpleNamespace(search_type="CHUNKS", kind="chunk", metadata={"data_id": str(native[0])}),
                   types.SimpleNamespace(search_type="CHUNKS", kind="chunk", metadata={"data_id": "unknown"})]
        ranked, unmapped, kinds = cognee_bridge.ranked_doc_ids(entries, by_uuid)
        self.assertEqual((ranked, unmapped), (["a"], 1))
        gold_bearing = cognee_bridge.occurrence_ids(["answer_4be1b6b4_2"])[0]
        self.assertNotIn("answer", str(gold_bearing))  # the benchmark id never appears in the native id


if __name__ == "__main__":
    unittest.main()
