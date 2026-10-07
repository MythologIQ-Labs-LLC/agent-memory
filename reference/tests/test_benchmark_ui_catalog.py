from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from agentmem_ref.evaluation.ui_catalog import MISSING_STATES, build_catalog

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "reports" / "benchmarks" / "dashboard" / "current.json"
SCORECARDS = ROOT / "reports" / "benchmarks" / "scorecards" / "scorecards.json"
NORMALIZED = ROOT / "reports" / "benchmarks" / "normalized"
SCHEMA = ROOT / "schemas" / "benchmark-ui-catalog.schema.json"
FRAME_FIXTURES = ROOT / "docs" / "prd" / "PRD-002-wireframe-fixtures.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _inputs():
    return (
        _load(DASHBOARD),
        _load(SCORECARDS),
        {str(path.relative_to(ROOT)): _load(path) for path in sorted(NORMALIZED.glob("*.json"))},
    )


class BenchmarkUiCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dashboard, cls.scorecards, cls.normalized = _inputs()
        cls.catalog = build_catalog(
            dashboard=cls.dashboard,
            scorecards=cls.scorecards,
            normalized_runs=cls.normalized,
            repository_head="261c6a66f739b5e45e306a69195392edbc800175",
        )

    def test_catalog_validates_against_schema(self):
        errors = sorted(
            Draft202012Validator(_load(SCHEMA)).iter_errors(self.catalog),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual(errors, [])

    def test_catalog_is_deterministic_and_repository_head_is_not_snapshot_identity(self):
        again = build_catalog(
            dashboard=self.dashboard,
            scorecards=self.scorecards,
            normalized_runs=self.normalized,
            repository_head="f" * 40,
        )
        self.assertEqual(self.catalog["snapshot"]["id"], again["snapshot"]["id"])
        self.assertTrue(again["snapshot"]["repository_is_newer"])

    def test_projection_relevant_evidence_changes_snapshot_identity(self):
        changed = copy.deepcopy(self.normalized)
        path = next(
            path
            for path, run in changed.items()
            if run["run_id"] == "longmemeval:longmemeval-s-retrieval-parity-v2:session:agent_memory:ca0f9a748b3b"
        )
        metric = next(
            metric
            for metric in changed[path]["dimensions"]["retrieval"]["metrics"]
            if metric["metric_id"] == "recall_all@5"
        )
        metric["value"] = 0.823388
        rebuilt = build_catalog(
            dashboard=self.dashboard,
            scorecards=self.scorecards,
            normalized_runs=changed,
            repository_head="261c6a66f739b5e45e306a69195392edbc800175",
        )
        self.assertNotEqual(self.catalog["snapshot"]["id"], rebuilt["snapshot"]["id"])

    def test_real_longmemeval_same_harness_comparison_is_projected(self):
        card = next(
            item
            for item in self.catalog["comparison_sets"]
            if item["comparison_identity"]["task_profile"] == "longmemeval-s-retrieval-parity-v2:session"
        )
        self.assertEqual(card["comparison_state"], "exact")
        self.assertEqual(card["evidence_class"], "same_harness")
        self.assertTrue(card["eligible_for_numeric_delta"])
        self.assertEqual(
            {item["id"] for item in card["systems"]},
            {"agent-memory", "lexical_overlap", "mem0-oss"},
        )
        retrieval = card["dimensions"]["retrieval"]["rows"]
        recall = next(row for row in retrieval if row["metric_id"] == "recall_all@5")
        self.assertEqual(recall["systems"]["agent-memory"]["value"], 0.823389)
        self.assertEqual(recall["systems"]["mem0-oss"]["value"], 0.809069)

    def test_published_hindsight_is_context_not_numeric_comparison(self):
        hindsight = next(
            item for item in self.catalog["published_references"]
            if item["system"] == "Hindsight v0.4.19"
        )
        self.assertEqual(hindsight["signals"]["LongMemEval_accuracy"], 0.946)
        self.assertEqual(hindsight["comparison_state"], "published_reference")
        self.assertFalse(hindsight["eligible_for_numeric_delta"])
        comparison_systems = {
            system["id"]
            for comparison in self.catalog["comparison_sets"]
            for system in comparison["systems"]
        }
        self.assertNotIn("Hindsight v0.4.19", comparison_systems)

    def test_missing_states_are_explicit_and_never_an_aggregate_score(self):
        self.assertEqual(self.catalog["aggregate_score"], "not_defined")
        self.assertEqual(
            set(self.catalog["coverage"]["missing_state_vocabulary"]),
            set(MISSING_STATES),
        )
        blocked = self.catalog["coverage"]["explicit_states"]
        self.assertTrue(any(item["state"] == "blocked" for item in blocked))

    def test_every_wireframe_has_a_supported_catalog_seed_class(self):
        fixture = _load(FRAME_FIXTURES)
        expected_ids = {f"F{index:02d}" for index in range(25)} | {f"R{index:02d}" for index in range(1, 5)}
        frames = {item["id"]: item for item in fixture["frames"]}
        self.assertEqual(set(frames), expected_ids)

        supported = {
            "accepted_evidence": bool(self.catalog["runs"] or self.catalog["longitudinal_tracks"]),
            "same_harness_evidence": any(
                item["evidence_class"] == "same_harness" for item in self.catalog["comparison_sets"]
            ),
            "published_reference": bool(self.catalog["published_references"]),
            "typed_missing_state": bool(self.catalog["coverage"]["missing_state_vocabulary"]),
            "schema_only_placeholder": SCHEMA.is_file(),
        }
        self.assertTrue(all(supported.values()))
        for frame in frames.values():
            self.assertTrue(frame["seed_classes"])
            for seed_class in frame["seed_classes"]:
                self.assertIn(seed_class, fixture["allowed_seed_classes"])
                self.assertTrue(supported[seed_class], f"{frame['id']} lacks catalog support for {seed_class}")

    def test_every_projected_numeric_metric_has_evidence_via_its_run(self):
        evidence_ids = {item["evidence_id"] for item in self.catalog["evidence_index"]}
        for run in self.catalog["runs"]:
            if any(metric["state"] == "measured" for metric in run["metrics"]):
                self.assertIn(f"run:{run['run_id']}", evidence_ids)
                self.assertTrue(run["evidence"])

    def test_metric_registry_preserves_native_identity(self):
        key = (
            "longmemeval:longmemeval-s-retrieval-parity-v2:session:"
            "retrieval:recall_all@5"
        )
        metric = next(item for item in self.catalog["metrics"] if item["metric_key"] == key)
        self.assertEqual(metric["native_label"], "recall_all@5")
        self.assertEqual(metric["directions"], ["higher_better"])
        self.assertEqual(metric["units"], ["ratio"])


if __name__ == "__main__":
    unittest.main()
