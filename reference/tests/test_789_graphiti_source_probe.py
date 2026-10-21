"""Graphiti source provenance contract tests: native edge.episodes surface.

Run: python -m unittest discover -s reference/tests -t reference -p test_789_graphiti_source_probe.py -v
No Graphiti SDK, graph DB, paid model, or CI needed.
"""
import unittest
from dataclasses import dataclass

from comparators.graphiti_source_probe import attribute_graphiti_edges


@dataclass
class Edge:
    episodes: object


class GraphitiSourceProbeTests(unittest.TestCase):
    def setUp(self):
        self.mapping = {"episode:a": "doc:a", "episode:b": "doc:b"}
        self.allowed = frozenset({"doc:a", "doc:b"})

    def test_single_episode_mapping(self):
        value = attribute_graphiti_edges(
            [Edge(["episode:a"]), Edge(["episode:b"])],
            episode_to_doc=self.mapping, allowed_doc_ids=self.allowed, top_k=5
        )
        self.assertEqual(value.ranked_for_scoring(), ("doc:a", "doc:b"))

    def test_multi_episode_edge_fails(self):
        value = attribute_graphiti_edges(
            [Edge(["episode:a", "episode:b"])],
            episode_to_doc=self.mapping, allowed_doc_ids=self.allowed, top_k=5
        )
        with self.assertRaises(ValueError):
            value.ranked_for_scoring()
        self.assertEqual(value.ambiguous_hits, 1)

    def test_missing_episode_attribute_fails(self):
        value = attribute_graphiti_edges(
            [object()], episode_to_doc=self.mapping,
            allowed_doc_ids=self.allowed, top_k=5
        )
        self.assertEqual(value.status, "unsupported_source_identity")

    def test_cross_scope_episode_handle_fails(self):
        value = attribute_graphiti_edges(
            [Edge(["episode:foreign"])], episode_to_doc=self.mapping,
            allowed_doc_ids=self.allowed, top_k=5
        )
        self.assertEqual(value.status, "unsupported_source_identity")

    def test_repeat_same_doc_across_edges(self):
        value = attribute_graphiti_edges(
            [Edge(["episode:a"]), Edge(["episode:a"])],
            episode_to_doc=self.mapping, allowed_doc_ids=self.allowed, top_k=5
        )
        self.assertEqual(value.ranked_for_scoring(), ("doc:a",))
        self.assertEqual(value.duplicate_hits, 1)


if __name__ == "__main__":
    unittest.main()
