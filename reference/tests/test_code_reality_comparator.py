"""Unit tests for the #275 CodeGenome/Graphify comparator normalizer."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref.code_reality_comparator import run_code_reality_comparator


class CodeRealityComparatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fixture = self.root / "fixture"
        self.fixture.mkdir()
        (self.fixture / "main.rs").write_text("pub fn x() {}\n", encoding="utf-8")
        (self.fixture / "decoy.rs").write_text("pub fn y() {}\n", encoding="utf-8")

        self.main_downstream = self.root / "main-downstream.json"
        self.main_upstream = self.root / "main-upstream.json"
        self.decoy_downstream = self.root / "decoy-downstream.json"
        self.graphify = self.root / "graphify.json"

        self.main_downstream.write_text(
            json.dumps([
                {"node": "line 7:9", "confidence": 1.0},
                {"node": "line 3:5", "confidence": 0.8},
            ]),
            encoding="utf-8",
        )
        self.main_upstream.write_text(
            json.dumps([
                {"node": "line 7:9", "confidence": 1.0},
                {"node": "line 11:13", "confidence": 0.8},
            ]),
            encoding="utf-8",
        )
        self.decoy_downstream.write_text(
            json.dumps([
                {"node": "line 7:9", "confidence": 1.0},
                {"node": "line 21:23", "confidence": 0.8},
            ]),
            encoding="utf-8",
        )
        self.graphify.write_text(
            json.dumps({
                "nodes": [
                    {"id": "m", "label": "middle()", "source_file": "/tmp/main.rs"},
                    {"id": "l", "label": "leaf()", "source_file": "/tmp/main.rs"},
                    {"id": "t", "label": "top()", "source_file": "/tmp/main.rs"},
                    {"id": "dm", "label": "middle()", "source_file": "/tmp/decoy.rs"},
                    {"id": "dl", "label": "decoy_leaf()", "source_file": "/tmp/decoy.rs"},
                ],
                "edges": [
                    {"source": "m", "target": "l", "relation": "calls", "source_file": "/tmp/main.rs", "confidence": "EXTRACTED"},
                    {"source": "t", "target": "m", "relation": "calls", "source_file": "/tmp/main.rs", "confidence": "EXTRACTED"},
                    {"source": "dm", "target": "dl", "relation": "calls", "source_file": "/tmp/decoy.rs", "confidence": "EXTRACTED"},
                ],
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def run_report(self):
        return run_code_reality_comparator(
            agent_memory_commit="a" * 40,
            fixture_dir=self.fixture,
            codegenome_main_downstream=self.main_downstream,
            codegenome_main_upstream=self.main_upstream,
            codegenome_decoy_downstream=self.decoy_downstream,
            graphify_graph=self.graphify,
        )

    def test_happy_path_has_no_product_winner(self):
        report = self.run_report()
        self.assertTrue(report["matched_result"]["both_reproduce_requested_fixture_facts"])
        self.assertIsNone(report["matched_result"]["winner"])
        self.assertFalse(report["governance_observations"]["scalar_product_ranking_created"])

    def test_codegenome_direction_and_file_identity_are_separate_checks(self):
        checks = self.run_report()["implementations"]["codegenome"]["checks"]
        self.assertTrue(checks["main_downstream_contains_leaf"])
        self.assertTrue(checks["main_upstream_contains_top"])
        self.assertTrue(checks["main_downstream_excludes_decoy_leaf"])
        self.assertTrue(checks["decoy_downstream_excludes_main_leaf"])

    def test_graphify_calls_are_scoped_by_source_file(self):
        checks = self.run_report()["implementations"]["graphify"]["checks"]
        self.assertTrue(checks["main_middle_calls_leaf"])
        self.assertTrue(checks["main_top_calls_middle"])
        self.assertTrue(checks["decoy_middle_calls_decoy_leaf"])
        self.assertTrue(checks["no_unexpected_fixture_call_edges"])

    def test_exact_commit_binding_is_required(self):
        with self.assertRaises(ValueError):
            run_code_reality_comparator(
                agent_memory_commit="main",
                fixture_dir=self.fixture,
                codegenome_main_downstream=self.main_downstream,
                codegenome_main_upstream=self.main_upstream,
                codegenome_decoy_downstream=self.decoy_downstream,
                graphify_graph=self.graphify,
            )


if __name__ == "__main__":
    unittest.main()
