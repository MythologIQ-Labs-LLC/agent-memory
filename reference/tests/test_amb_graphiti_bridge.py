import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from amb_graphiti_bridge import (  # noqa: E402
    episode_name,
    expand_edges,
    frozen_configuration,
    group_id_for,
    parse_reference_time,
)


def edge(uuid, *episodes):
    return SimpleNamespace(uuid=uuid, fact=f"fact {uuid}", episodes=list(episodes))


class ExpandEdgesTest(unittest.TestCase):
    def test_one_document_per_supporting_episode_in_graphiti_order(self):
        docs = {"ep1": "b1", "ep2": "b2", "ep3": "b3"}
        pairs, unmapped = expand_edges([edge("e1", "ep2", "ep1"), edge("e2", "ep3")], docs, k=10)
        self.assertEqual([(p[0].uuid, p[1]) for p in pairs], [("e1", "b2"), ("e1", "b1"), ("e2", "b3")])
        self.assertEqual(unmapped, 0)

    def test_cut_to_budget_after_expansion(self):
        docs = {"ep1": "b1", "ep2": "b2"}
        pairs, _ = expand_edges([edge("e1", "ep1", "ep2"), edge("e2", "ep2")], docs, k=2)
        self.assertEqual([p[1] for p in pairs], ["b1", "b2"])

    def test_zero_budget_returns_nothing(self):
        self.assertEqual(expand_edges([edge("e1", "ep1")], {"ep1": "b1"}, k=0)[0], [])

    def test_unmapped_edge_is_counted_and_passed_through_without_a_belief(self):
        pairs, unmapped = expand_edges([edge("e1", "unknown")], {"ep1": "b1"}, k=5)
        self.assertEqual(unmapped, 1)
        self.assertEqual(pairs[0][1], None)

    def test_duplicate_episode_on_one_edge_maps_once(self):
        pairs, _ = expand_edges([edge("e1", "ep1", "ep1")], {"ep1": "b1"}, k=5)
        self.assertEqual(len(pairs), 1)


class IdentityTest(unittest.TestCase):
    def test_episode_name_is_opaque_and_stable(self):
        name = episode_name("belief-123")
        self.assertNotIn("belief", name)
        self.assertEqual(name, episode_name("belief-123"))
        self.assertNotEqual(name, episode_name("belief-124"))

    def test_group_id_sanitised(self):
        self.assertEqual(group_id_for("test-user"), "test-user")
        self.assertEqual(group_id_for("a b/c"), "a_b_c")
        self.assertEqual(group_id_for(None), "default-user")

    def test_reference_time_parsing(self):
        self.assertEqual(parse_reference_time("2025-01-10T09:00:00Z"), datetime(2025, 1, 10, 9, tzinfo=timezone.utc))
        self.assertEqual(parse_reference_time("2025-01-10T09:00:00").tzinfo, timezone.utc)
        with self.assertRaises(ValueError):
            parse_reference_time(None)

    def test_configuration_declares_what_graphiti_is_not_given(self):
        config = frozen_configuration("http://127.0.0.1:8089/v1")
        self.assertIn("belief ids", config["not_supplied_to_graphiti"])
        self.assertEqual(config["llm"]["temperature"], 0.0)


if __name__ == "__main__":
    unittest.main()
