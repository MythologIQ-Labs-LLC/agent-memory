"""#668/#719: frontier targets must remain evidence-bound and non-authoritative."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_frontier_objectives import (  # noqa: E402
    FrontierEvidenceError, build_frontier_report, observed_peer_position,
    read_json,
)

DATA = ROOT / "data" / "benchmark-frontier-objectives.json"
LEDGER = ROOT / "reports" / "benchmarks" / "deficits" / "current.json"
DASH = ROOT / "reports" / "benchmarks" / "dashboard" / "current.json"


class BenchmarkFrontierObjectiveTests(unittest.TestCase):
    def setUp(self):
        self.config = read_json(DATA)
        self.ledger = read_json(LEDGER)
        self.dashboard = read_json(DASH)

    def report(self, config=None, ledger=None, dashboard=None):
        return build_frontier_report(
            config if config is not None else self.config,
            ledger if ledger is not None else self.ledger,
            dashboard if dashboard is not None else self.dashboard,
        )

    def test_all_nine_capability_families_have_owned_goals(self):
        result = self.report()
        self.assertEqual(set(result["group_counts"]), set("ABCDEFGHI"))
        self.assertEqual(result["objective_count"], 29)
        self.assertTrue(all(result["group_counts"][x] > 0 for x in "ABCDEFGHI"))

    def test_all_accepted_deficits_are_accounted_for_not_closed(self):
        result = self.report()
        self.assertEqual(result["deficit_coverage"]["covered"],
                         result["deficit_coverage"]["total"])
        self.assertEqual(result["deficit_coverage"]["unowned"], [])
        self.assertEqual(result["deficit_coverage"]["covered"], 25)
        self.assertTrue(all(goal["completion_decision"] == "not_automated"
                            for goal in result["goals"]))

    def test_comparable_longmemeval_deep_recall_gap_is_visible(self):
        item = next(g for g in self.report()["goals"] if g["id"] == "B01")
        self.assertEqual(len(item["evidence"]), 1)
        entry = item["evidence"][0]
        self.assertEqual(entry["known_peer_position"], "behind_observed_peer")
        self.assertEqual(entry["posture"], "competitive_deficit")
        self.assertEqual(entry["native_value"], 0.859189)
        self.assertEqual(entry["same_harness_frontier"]["value"], 0.894988)

    def test_precision_frontier_is_self_only_not_adequacy(self):
        item = next(g for g in self.report()["goals"] if g["id"] == "B02")
        entry = item["evidence"][0]
        self.assertEqual(entry["known_peer_position"], "self_frontier_only")
        self.assertEqual(entry["posture"], "frontier_but_inadequate")
        self.assertEqual(entry["native_value"]["active_passes"], "4/43")
        self.assertFalse(self.report()["best_in_class_claim"])

    def test_formal_mesa_does_not_confer_cross_family_currentness(self):
        out = self.report()["goals"]
        local_mesa = next(g for g in out if g["id"] == "C01")["evidence"][0]
        cross_family = next(g for g in out if g["id"] == "C02")["evidence"]
        self.assertEqual(local_mesa["posture"], "frontier")
        self.assertEqual(local_mesa["known_peer_position"],
                         "no_comparable_numeric_peer")
        self.assertGreater(len(cross_family), 1)
        self.assertTrue(any(row["posture"] == "architecture_gap" for row in cross_family))
        self.assertTrue(any(row["native_value"] == 0 for row in cross_family))
        self.assertFalse(self.report()["best_in_class_claim"])

    def test_natural_proposition_recognition_remains_owned(self):
        row = next(g for g in self.report()["goals"] if g["id"] == "A03")
        self.assertIn(596, row["owners"])
        self.assertEqual(row["evidence"][0]["native_value"], 0.148148)
        self.assertEqual(row["evidence"][0]["primary_stage"],
                         "write_interpretation_proposition_extraction")

    def test_blocked_not_run_and_gap_never_become_zero(self):
        for item in self.report()["goals"]:
            if item["source_kind"] not in ("ledger", "ledger_family"):
                self.assertEqual(item["evidence"], [])
                self.assertIsNotNone(item["unmeasured_state"])
                self.assertNotEqual(item["unmeasured_state"], 0)
        blocked = next(x for x in self.report()["goals"] if x["id"] == "G01")
        self.assertEqual(blocked["unmeasured_state"], "blocked_credential")

    def test_published_reference_not_promoted_to_comparable_peer(self):
        row = {
            "agent_memory": 0.90,
            "published_frontier": {"system": "published vendor", "value": 0.99},
            "same_harness_frontier": None,
            "direction": "higher",
            "evidence_class": "external efficacy",
        }
        self.assertEqual(observed_peer_position(row), "no_comparable_numeric_peer")
        row["same_harness_frontier"] = row.pop("published_frontier")
        self.assertEqual(observed_peer_position(row), "no_comparable_numeric_peer")

    def test_comparator_direction_and_unrelated_systems(self):
        row = {
            "agent_memory": 7.0, "same_harness_frontier": {"system": "peer", "value": 5.0},
            "direction": "lower", "evidence_class": "same_harness_external",
        }
        self.assertEqual(observed_peer_position(row), "behind_observed_peer")
        row["agent_memory"] = 3.0
        self.assertEqual(observed_peer_position(row), "ahead_of_observed_peer")
        row["agent_memory"] = 5.0
        self.assertEqual(observed_peer_position(row), "tied_with_observed_peer")
        row["same_harness_frontier"]["system"] = "Agent Memory"
        self.assertEqual(observed_peer_position(row), "self_frontier_only")
        row["same_harness_frontier"]["system"] = "Agent Memory (control)"
        self.assertEqual(observed_peer_position(row), "self_frontier_only")
        row["same_harness_frontier"]["system"] = "Agent Memory Competitor"
        self.assertEqual(observed_peer_position(row), "tied_with_observed_peer")

    def test_missing_material_deficit_must_fail_not_silently_drop(self):
        ledger = deepcopy(self.ledger)
        ledger["deficits"].append({
            "deficit_id": "independent-new-material-deficit",
            "metric": "opaque",
        })
        with self.assertRaisesRegex(FrontierEvidenceError, "lack goals"):
            self.report(ledger=ledger)

    def test_unknown_or_duplicate_goal_identifiers_refuse(self):
        config = deepcopy(self.config)
        config["objectives"].append(deepcopy(config["objectives"][0]))
        with self.assertRaisesRegex(FrontierEvidenceError, "duplicate/invalid"):
            self.report(config=config)
        config = deepcopy(self.config)
        config["objectives"][0]["group"] = "Z"
        with self.assertRaises(FrontierEvidenceError):
            self.report(config=config)

    def test_unsafe_authority_or_aggregate_claim_refused(self):
        for patch in (
            {"universal_score": 0.99},
            {"authority_effect": "reviewed"},
            {"published_not_comparable": False},
            {"same_harness_ranking_only": False},
        ):
            config = deepcopy(self.config)
            config["claims_policy"].update(patch)
            with self.assertRaisesRegex(FrontierEvidenceError, "missing frontier"):
                self.report(config=config)

    def test_false_numeric_missing_state_refused(self):
        config = deepcopy(self.config)
        next(g for g in config["objectives"] if g["id"] == "G03")[
            "unmeasured_state"
        ] = 0
        with self.assertRaisesRegex(FrontierEvidenceError, "unmeasured state"):
            self.report(config=config)

    def test_source_metric_identity_drift_fail_closed(self):
        config = deepcopy(self.config)
        next(g for g in config["objectives"] if g["id"] == "B01")[
            "metric"
        ] = "recall_all@5"
        with self.assertRaisesRegex(FrontierEvidenceError, "metric identity drift"):
            self.report(config=config)

    def test_removed_goal_cannot_leave_deficit_ownerless(self):
        config = deepcopy(self.config)
        config["objectives"] = [
            g for g in config["objectives"] if g["id"] not in ("A03",)
        ]
        with self.assertRaisesRegex(FrontierEvidenceError, "lack goals"):
            self.report(config=config)

    def test_unsupported_dashboard_or_ledger_state_refused(self):
        d = deepcopy(self.dashboard)
        d.pop("formal_mesa_baseline")
        with self.assertRaisesRegex(FrontierEvidenceError, "dashboard"):
            self.report(dashboard=d)
        ledger = deepcopy(self.ledger)
        ledger["deficits"][0]["state"] = "secretly_solved"
        with self.assertRaisesRegex(FrontierEvidenceError, "unsupported ledger"):
            self.report(ledger=ledger)

    def test_projection_deterministic_and_inputs_unchanged(self):
        before = json.dumps([self.config, self.ledger, self.dashboard], sort_keys=True)
        first = self.report()
        second = self.report()
        self.assertEqual(first, second)
        self.assertEqual(before, json.dumps(
            [self.config, self.ledger, self.dashboard], sort_keys=True
        ))
        self.assertEqual(first["universal_score"], None)
        self.assertEqual(first["authority_effect"], "none")
        self.assertTrue(all(not x["mutation_authority"] for x in first["goals"]))
        self.assertTrue(all(not x["benchmark_specific_implementation_allowed"]
                            for x in first["goals"]))

    def test_original_deficit_issue_must_remain_accountable(self):
        config = deepcopy(self.config)
        row = next(x for x in config["objectives"] if x["id"] == "B02")
        row["owners"].remove(719)
        with self.assertRaisesRegex(FrontierEvidenceError, "original deficit owner"):
            self.report(config=config)

    def test_priority_and_replay_obligations_survive_projection(self):
        deep = next(x for x in self.report()["goals"] if x["id"] == "B01")
        row = deep["evidence"][0]
        self.assertEqual(row["owning_issue"], 673)
        self.assertIn(673, deep["owners"])
        self.assertEqual(row["priority"], "P1")
        self.assertIn("LongMemEval_S successor same-harness lane",
                      row["replay_requirements"])
        self.assertEqual(row["closure_evidence"], [])



if __name__ == "__main__":
    unittest.main()
