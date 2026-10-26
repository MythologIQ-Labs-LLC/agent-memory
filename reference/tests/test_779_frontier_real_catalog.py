"""#779 qualification against the committed accepted F1 catalog.

Synthetic fixtures cannot prove that the real evidence contract projects
safely. These checks read ``reports/benchmarks/ui/catalog.json`` as committed
and assert the observable consequences of the fail-closed rules on real
accepted evidence. They do not run a benchmark and never alter evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from agentmem_ref.evaluation.ui_frontier_leaderboard import (
    COMPETITIVE_STATES,
    CURRENCY_STATES,
    RANKING_STATES,
    build_frontier_leaderboard,
)

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "reports/benchmarks/ui/catalog.json"
GENERATED = ROOT / "reports/benchmarks/ui/frontier-leaderboards.json"


@unittest.skipUnless(CATALOG.exists(), "accepted F1 catalog is not present")
class RealCatalogFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.out = build_frontier_leaderboard(cls.catalog)
        cls.rows = cls.out["leaderboards"]
        cls.ranked = [r for r in cls.rows if r["ranking_state"] == "ranked"]

    def _row(self, fragment, metric_id):
        hits = [r for r in self.rows if fragment in r["task_profile"] and r["metric_id"] == metric_id]
        self.assertEqual(len(hits), 1, (fragment, metric_id, len(hits)))
        return hits[0]

    def test_snapshot_identity_is_the_f1_snapshot(self):
        self.assertEqual(self.out["snapshot_id"], self.catalog["snapshot"]["id"])
        self.assertTrue(self.out["snapshot_id"].startswith("git-evidence-v1:"))
        self.assertEqual(self.out["snapshot"]["evidence_revision"],
                         self.catalog["snapshot"]["evidence_revision"])
        self.assertIs(self.out["snapshot"]["repository_is_newer"], True)
        self.assertIsNone(self.out["aggregate_score"])
        self.assertEqual(self.out["authority_effect"], "none")

    def test_every_catalog_row_and_metric_is_represented(self):
        expected_rows = sum(
            len(content["rows"])
            for comparison in self.catalog["comparison_sets"]
            for content in comparison["dimensions"].values()
        )
        self.assertEqual(len(self.rows), expected_rows)
        self.assertEqual(len(self.out["metric_coverage"]), len(self.catalog["metrics"]))
        summary = self.out["summary"]
        self.assertEqual(sum(summary["ranking_states"].values()), len(self.rows))
        self.assertEqual(sum(summary["currency_states"].values()), len(self.rows))
        self.assertEqual(sum(summary["competitive_states"].values()), len(self.ranked))
        for row in self.rows:
            self.assertIn(row["ranking_state"], RANKING_STATES)
            self.assertIn(row["currency"]["state"], CURRENCY_STATES)
            if row["competitive_state"] is not None:
                self.assertIn(row["competitive_state"], COMPETITIVE_STATES)

    def test_only_accepted_same_harness_sets_rank(self):
        same_harness = {c["comparison_set_id"] for c in self.catalog["comparison_sets"]
                        if c["evidence_class"] == "same_harness"}
        self.assertEqual(len(same_harness), 6)
        self.assertTrue(self.ranked)
        for row in self.ranked:
            self.assertIn(row["comparison_set_id"], same_harness)
            self.assertEqual(row["evidence_class"], "same_harness")
            self.assertEqual(row["reasons"], [])
        for row in self.rows:
            if row["comparison_set_id"] not in same_harness:
                self.assertEqual(row["ranking_state"], "non_comparable")
                self.assertIsNone(row["leader"])
                self.assertIsNone(row["gap_to_leader_native"])
                self.assertIsNone(row["competitive_state"])
                self.assertIn("evidence_class:same_profile", row["reasons"])

    def test_every_ranked_value_has_verified_run_provenance(self):
        runs = {r["run_id"] for r in self.catalog["runs"]}
        for row in self.ranked:
            self.assertEqual(len(row["ranking"]), 3, row["metric_key"])
            for entry in row["ranking"]:
                self.assertIn(entry["run_id"], runs)
                self.assertTrue(entry["provenance"]["verified"], (row["metric_key"], entry["system_id"]))
                self.assertTrue(entry["evidence"], (row["metric_key"], entry["system_id"]))
                self.assertTrue(entry["revision"])
            roles = {entry["role"] for entry in row["ranking"]}
            self.assertEqual(roles, {"subject", "external_competitor", "control"})
            self.assertTrue(row["peer_population"]["external_competitor_ranked"])
            self.assertEqual(row["peer_population"]["external_competitors"], ["mem0-oss"])

    def test_external_competitor_registry_separates_market_from_published(self):
        self.assertEqual(self.out["external_competitors"]["same_harness_measured"], ["mem0-oss"])
        published = self.out["published_references"]
        self.assertEqual(len(published), 5)
        for ref in published:
            self.assertFalse(ref["ranked"])
            self.assertFalse(ref["eligible_for_numeric_delta"])
            self.assertIn(ref["system"], self.out["external_competitors"]["published_only"])
            self.assertNotIn(ref["system"], self.out["external_competitors"]["same_harness_measured"])
        self.assertEqual(self.out["summary"]["competitive_states"]["leading_vs_controls_only"], 0)

    def test_known_real_rows_project_to_defensible_states(self):
        row = self._row("parity-v2:turn", "recall_all@50")
        self.assertEqual(row["ranking_state"], "ranked")
        self.assertEqual(row["direction"], "higher_better")
        self.assertEqual(row["unit"], "ratio")
        self.assertEqual(row["leader"]["system_id"], "mem0-oss")
        self.assertEqual(row["leader"]["role"], "external_competitor")
        self.assertEqual(row["agent_memory"]["rank"], 2)
        self.assertAlmostEqual(row["leader"]["value"], 0.894988, places=6)
        self.assertAlmostEqual(row["agent_memory"]["value"], 0.859189, places=6)
        self.assertAlmostEqual(row["gap_to_leader_native"], 0.035799, places=6)
        self.assertAlmostEqual(row["gap_percentage_points"], 3.5799, places=4)
        self.assertEqual(row["competitive_state"], "behind_external")
        self.assertEqual([e["rank"] for e in row["ranking"]], [1, 2, 3])

        row = self._row("parity-v2:turn", "latest_gold_ranked_first")
        self.assertEqual(row["competitive_state"], "behind_control")
        self.assertEqual(row["leader"]["system_id"], "lexical_overlap")
        self.assertEqual(row["leader"]["role"], "control")
        self.assertAlmostEqual(row["gap_percentage_points"], 5.7143, places=4)

        row = self._row("parity-v2:session", "latest_gold_ranked_first")
        self.assertEqual(row["leader_state"], "tied")
        self.assertEqual(row["co_leaders"], ["agent-memory", "lexical_overlap"])
        self.assertEqual(row["competitive_state"], "tied_leader")
        self.assertEqual(row["gap_to_leader_native"], 0.0)
        self.assertEqual([e["rank"] for e in row["ranking"]], [1, 1, 3])

        row = self._row("parity-v2:session", "recall_all@5")
        self.assertEqual(row["competitive_state"], "leading_vs_external")
        self.assertAlmostEqual(row["agent_memory"]["value"], 0.823389, places=6)
        self.assertEqual(row["gap_to_leader_native"], 0.0)

        row = self._row("parity-v2:turn", "backend_wall_seconds")
        self.assertEqual(row["direction"], "lower_better")
        self.assertEqual(row["unit"], "seconds")
        self.assertIsNone(row["gap_percentage_points"])
        self.assertEqual(row["leader"]["system_id"], "lexical_overlap")
        self.assertEqual(row["competitive_state"], "behind_control")
        self.assertGreater(row["gap_to_leader_native"], 0)

        row = self._row("retrieval-v2:single-turn", "structural_passes")
        self.assertEqual(row["unit"], "count")
        self.assertEqual(row["leader"]["system_id"], "mem0-oss")
        self.assertEqual(row["gap_to_leader_native"], 1.0)
        self.assertIsNone(row["gap_percentage_points"])

    def test_boolean_reproducibility_rows_are_not_rankable_and_not_unmeasured(self):
        row = self._row("retrieval-v2:single-turn", "input_sha256_bound")
        self.assertEqual(row["ranking_state"], "not_rankable")
        self.assertIn("measured_values_are_not_ordinal_numbers", row["reasons"])
        self.assertIsNone(row["leader"])
        self.assertEqual(self.out["summary"]["ranking_states"]["not_measured"],
                         len([r for r in self.rows if r["ranking_state"] == "not_measured"]))
        for row in self.rows:
            if row["ranking_state"] == "not_measured":
                self.assertTrue(all(s["state"] != "measured" or s["value"] is None
                                    for s in row["systems_observed"]), row["metric_key"])

    def test_metrics_without_shared_population_do_not_rank(self):
        row = self._row("retrieval-v2:single-turn", "mean_precision")
        self.assertEqual(row["ranking_state"], "non_comparable")
        self.assertIn("denominator_missing_or_invalid", row["reasons"])
        self.assertIsNone(row["leader"])
        row = self._row("parity-v2:turn", "ingest_seconds_total")
        self.assertEqual(row["ranking_state"], "non_comparable")
        self.assertIsNone(row["gap_to_leader_native"])

    def test_repeated_lane_generations_are_ordered_or_undetermined(self):
        for metric_id in ("recall_all@5", "ndcg_any@10"):
            for plane in ("session", "turn"):
                v1 = self._row(f"parity-v1:{plane}", metric_id)
                v2 = self._row(f"parity-v2:{plane}", metric_id)
                self.assertEqual(v1["currency"]["state"], "superseded")
                self.assertEqual(v1["currency"]["superseded_by"], v2["comparison_set_id"])
                self.assertEqual(v1["currency"]["lineage_id"], v2["currency"]["lineage_id"])
                self.assertEqual(v2["currency"]["state"], "newer_unaccepted_evidence")
                self.assertEqual(len(v2["currency"]["unaccepted_sibling_revisions"]), 4)
                self.assertEqual(v2["currency"]["agent_memory_revision"],
                                 self.out["snapshot"]["evidence_revision"])
        session = self._row("parity-v2:session", "recall_all@5")
        turn = self._row("parity-v2:turn", "recall_all@5")
        self.assertNotEqual(session["currency"]["lineage_id"], turn["currency"]["lineage_id"])
        amb = self._row("retrieval-v2:single-turn", "active_passes")
        self.assertEqual(amb["currency"]["state"], "undetermined")
        self.assertIsNone(amb["currency"]["agent_memory_started_at"])
        self.assertEqual(len(amb["currency"]["unaccepted_sibling_revisions"]), 4)

    def test_unaccepted_newer_generations_never_rank(self):
        for generation in ("v3", "v4", "v5", "v6"):
            rows = [r for r in self.rows if f"-{generation}:" in r["task_profile"]]
            self.assertTrue(rows, generation)
            for row in rows:
                self.assertEqual(row["ranking_state"], "non_comparable")
                self.assertIsNone(row["leader"])

    def test_coverage_counts_only_ranked_metrics(self):
        ranked_keys = {r["metric_key"] for r in self.ranked}
        for item in self.out["metric_coverage"]:
            self.assertIsNone(item["gap_to_leader_native"])
            if item["state"] == "has_accepted_comparison":
                self.assertIn(item["metric_key"], ranked_keys)
                self.assertEqual(item["best_ranking_state"], "ranked")
            else:
                self.assertNotIn(item["metric_key"], ranked_keys)

    def test_objectives_registry_absent_in_this_checkout_degrades_cleanly(self):
        self.assertEqual(self.out["objectives"]["state"], "absent")
        self.assertEqual(sorted(self.out["objectives"]["families"]), list("ABCDEFGHI"))
        self.assertTrue(all(row["objectives"] == [] for row in self.rows))

    @unittest.skipUnless(GENERATED.exists(), "generated projection not written yet")
    def test_committed_projection_is_current_for_this_catalog(self):
        committed = json.loads(GENERATED.read_text(encoding="utf-8"))
        self.assertEqual(committed, self.out)


if __name__ == "__main__":
    unittest.main()
