"""#779 metric-native leaderboard falsifiers: no score laundering.

Preregistered before the read-only projection implementation. Synthetic
fixtures are not a claim about Agent Memory benchmark performance.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from agentmem_ref.evaluation.ui_frontier_leaderboard import build_frontier_leaderboard, FrontierProjectionError


def fixture(*, evidence="same_harness", direction="higher_better", am=0.7,
            peer=0.9, extra=None):
    observations = {
        "agent-memory": {"state": "measured", "value": am,
                         "direction": direction, "unit": "ratio",
                         "denominator": 20, "population": "twenty frozen trials"},
        "mem0-oss": {"state": "measured", "value": peer,
                     "direction": direction, "unit": "ratio",
                     "denominator": 20, "population": "twenty frozen trials"},
    }
    if extra:
        observations.update(extra)
    return {
        "schema_version": "1.0.0",
        "snapshot": {"id": "immutable:snapshot-01"},
        "metrics": [{"metric_key": "bench:profile:retrieval:recall_at_5",
                     "benchmark_profile_id": "bench:profile",
                     "dimension": "retrieval", "metric_id": "recall_at_5"}],
        "published_references": [{"system": "vendor", "value": 0.999,
                                  "eligible_for_numeric_delta": False}],
        "comparison_sets": [{
            "comparison_set_id": "comparison:exact-frozen-20",
            "evidence_class": evidence, "comparison_state": "exact",
            "eligible_for_numeric_delta": True,
            "comparison_identity": {
                "benchmark_id": "bench", "task_profile": "profile",
                "input_sha256": "abc123", "selection_id": "fixed",
                "sample_count": 20,
            },
            "systems": [
                {"id": "agent-memory", "kind": "agent_memory",
                 "revision": "am:sha", "run_id": "r-am", "run_status": "complete"},
                {"id": "mem0-oss", "kind": "external_memory",
                 "revision": "mem0:sha", "run_id": "r-mem0", "run_status": "complete"},
            ],
            "dimensions": {"retrieval": {"rows": [{
                "metric_id": "recall_at_5", "systems": observations,
            }]}}
        }],
    }


class FrontierProjectionTests(unittest.TestCase):
    def test_higher_is_better_and_gap_to_peer(self):
        row = build_frontier_leaderboard(fixture())["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "ranked")
        self.assertEqual(row["leader"]["system_id"], "mem0-oss")
        self.assertAlmostEqual(row["gap_to_leader_native"], 0.2)
        self.assertEqual(row["agent_memory"]["rank"], 2)
        self.assertEqual([x["system_id"] for x in row["ranking"]], ["mem0-oss", "agent-memory"])
        self.assertEqual(row["authority_effect"], "none")
        self.assertIsNone(row["adequacy"]["target"])

    def test_lower_is_better_and_zero_target(self):
        for direction in ("lower_better", "zero_target"):
            with self.subTest(direction=direction):
                row = build_frontier_leaderboard(
                    fixture(direction=direction, am=0.8, peer=0.4)
                )["leaderboards"][0]
                self.assertEqual(row["leader"]["system_id"], "mem0-oss")
                self.assertAlmostEqual(row["gap_to_leader_native"], 0.4)

    def test_tie_receives_shared_rank_and_zero_measured_gap(self):
        row = build_frontier_leaderboard(fixture(am=0.7, peer=0.7))["leaderboards"][0]
        self.assertEqual(row["agent_memory"]["rank"], 1)
        self.assertEqual([x["rank"] for x in row["ranking"]], [1, 1])
        self.assertEqual(row["gap_to_leader_native"], 0.0)

    def test_published_reference_cannot_join_numeric_frontier(self):
        obj = fixture()
        obj["published_references"].append({
            "system": "fantastic-vendor", "value": 0.9999,
            "eligible_for_numeric_delta": False
        })
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["leader"]["system_id"], "mem0-oss")
        obj["comparison_sets"][0]["evidence_class"] = "published_reference"
        result = build_frontier_leaderboard(obj)
        self.assertEqual(result["leaderboards"][0]["ranking_state"], "non_comparable")
        self.assertIsNone(result["leaderboards"][0]["gap_to_leader_native"])

    def test_same_profile_alone_is_not_an_accepted_comparison(self):
        row = build_frontier_leaderboard(fixture(evidence="same_profile"))["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "non_comparable")
        self.assertIsNone(row["leader"])

    def test_missing_peer_is_not_zero_gap_or_certified_lead(self):
        obj = fixture()
        del obj["comparison_sets"][0]["dimensions"]["retrieval"]["rows"][0]["systems"]["mem0-oss"]
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "no_peer")
        self.assertIsNone(row["gap_to_leader_native"])
        self.assertIsNone(row["leader"])
        self.assertAlmostEqual(row["agent_memory"]["value"], 0.7)

    def test_absent_agent_memory_is_unknown_not_deficit(self):
        obj = fixture()
        del obj["comparison_sets"][0]["dimensions"]["retrieval"]["rows"][0]["systems"]["agent-memory"]
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "agent_memory_missing")
        self.assertIsNone(row["gap_to_leader_native"])

    def test_boolean_infinity_nan_and_blocked_are_not_scores(self):
        for bad in (True, float("inf"), float("-inf"), float("nan")):
            with self.subTest(bad=repr(bad)):
                row = build_frontier_leaderboard(fixture(am=bad))["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "agent_memory_missing")
                self.assertIsNone(row["gap_to_leader_native"])
        obj = fixture()
        obj["comparison_sets"][0]["dimensions"]["retrieval"]["rows"][0]["systems"]["agent-memory"] = {
            "state": "blocked", "direction": "higher_better"
        }
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "agent_memory_missing")
        self.assertIsNone(row["gap_to_leader_native"])

    def test_direction_and_units_mismatch_refuse_ranking(self):
        for change in (
            {"direction": "lower_better"}, {"unit": "ms"},
            {"denominator": 99}, {"population": "different trial selection"},
        ):
            with self.subTest(change=change):
                obj = fixture()
                obs = obj["comparison_sets"][0]["dimensions"]["retrieval"]["rows"][0]["systems"]
                obs["mem0-oss"].update(change)
                row = build_frontier_leaderboard(obj)["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "non_comparable")
                self.assertIsNone(row["gap_to_leader_native"])

    def test_missing_native_metadata_refuses_ranking(self):
        for change in (
            {"unit": None}, {"unit": ""}, {"population": None},
            {"population": ""}, {"denominator": None},
            {"denominator": 0}, {"denominator": -1},
            {"denominator": True}, {"denominator": float("nan")},
        ):
            with self.subTest(change=change):
                obj = fixture()
                observations = obj["comparison_sets"][0]["dimensions"]["retrieval"]["rows"][0]["systems"]
                observations["mem0-oss"].update(change)
                row = build_frontier_leaderboard(obj)["leaderboards"][0]
                self.assertEqual(row["ranking_state"], "non_comparable")
                self.assertIsNone(row["gap_to_leader_native"])
                self.assertIsNone(row["leader"])

    def test_descriptive_metric_never_ranks(self):
        row = build_frontier_leaderboard(
            fixture(direction="descriptive", am=1, peer=0)
        )["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "not_rankable")
        self.assertIsNone(row["leader"])

    def test_metric_without_comparison_set_remains_in_coverage(self):
        obj = fixture()
        obj["metrics"].append({
            "metric_key": "other:task:governance:no_leak",
            "benchmark_profile_id": "other:task",
            "dimension": "governance", "metric_id": "no_leak",
        })
        out = build_frontier_leaderboard(obj)
        unranked = [x for x in out["metric_coverage"] if x["metric_key"].startswith("other:")]
        self.assertEqual(len(unranked), 1)
        self.assertEqual(unranked[0]["state"], "no_accepted_comparison")
        self.assertIsNone(unranked[0]["gap_to_leader_native"])
        self.assertEqual(out["aggregate_score"], None)

    def test_deterministic_and_does_not_change_catalog(self):
        obj = fixture()
        before = deepcopy(obj)
        a = build_frontier_leaderboard(obj)
        self.assertEqual(a, build_frontier_leaderboard(obj))
        self.assertEqual(obj, before)
        self.assertEqual(a["snapshot_id"], "immutable:snapshot-01")

    def test_repeated_system_run_in_same_set_refused(self):
        obj = fixture()
        obj["comparison_sets"][0]["systems"].append(deepcopy(obj["comparison_sets"][0]["systems"][0]))
        with self.assertRaises(FrontierProjectionError):
            build_frontier_leaderboard(obj)

    def test_missing_comparison_identity_never_fabricates_ranking(self):
        obj = fixture()
        obj["comparison_sets"][0]["comparison_identity"]["input_sha256"] = None
        row = build_frontier_leaderboard(obj)["leaderboards"][0]
        self.assertEqual(row["ranking_state"], "non_comparable")


if __name__ == "__main__":
    unittest.main()
