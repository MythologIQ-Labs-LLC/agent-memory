"""Provider-neutral code-graph qualification tests for #300."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref.code_graph_qualification import build_qualification_report  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "reference" / "fixtures" / "component-qualification"


def _cg(path: Path, lines: list[int]) -> None:
    path.write_text(
        json.dumps([{"node": f"line {line}:{line + 2}"} for line in lines]),
        encoding="utf-8",
    )


def _graph(path: Path, calls: list[tuple[str, str, str]]) -> None:
    nodes = []
    edges = []
    seen = set()
    for file_name, source, target in calls:
        for label in (source, target):
            key = (file_name, label)
            if key not in seen:
                seen.add(key)
                nodes.append({"id": f"{file_name}:{label}", "label": label, "source_file": file_name})
        edges.append(
            {
                "source": f"{file_name}:{source}",
                "target": f"{file_name}:{target}",
                "relation": "calls",
                "source_file": file_name,
                "provenance": "EXTRACTED",
            }
        )
    path.write_text(json.dumps({"nodes": nodes, "edges": edges}), encoding="utf-8")


class CodeGraphQualificationTests(unittest.TestCase):
    def test_matched_v1_v2_report_preserves_currentness_and_no_winner(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {name: root / name for name in (
                "cg-v1-down.json", "cg-v1-up.json", "cg-v1-decoy.json",
                "cg-v2-down.json", "cg-v2-up.json", "cg-v2-decoy.json",
                "graph-v1.json", "graph-v2.json",
            )}
            _cg(paths["cg-v1-down.json"], [5, 1])
            _cg(paths["cg-v1-up.json"], [5, 9])
            _cg(paths["cg-v1-decoy.json"], [5, 12])
            _cg(paths["cg-v2-down.json"], [5, 13])
            _cg(paths["cg-v2-up.json"], [5, 9])
            _cg(paths["cg-v2-decoy.json"], [5, 12])
            _graph(
                paths["graph-v1.json"],
                [
                    ("main.rs", "middle", "leaf"),
                    ("main.rs", "top", "middle"),
                    ("decoy.rs", "middle", "decoy_leaf"),
                ],
            )
            _graph(
                paths["graph-v2.json"],
                [
                    ("main.rs", "middle", "replacement_leaf"),
                    ("main.rs", "top", "middle"),
                    ("decoy.rs", "middle", "decoy_leaf"),
                ],
            )
            report = build_qualification_report(
                agent_memory_commit="a" * 40,
                fixture_paths=sorted(FIXTURE_ROOT.glob("v*/*.rs")),
                codegenome_v1_main_downstream=paths["cg-v1-down.json"],
                codegenome_v1_main_upstream=paths["cg-v1-up.json"],
                codegenome_v1_decoy_downstream=paths["cg-v1-decoy.json"],
                codegenome_v2_main_downstream=paths["cg-v2-down.json"],
                codegenome_v2_main_upstream=paths["cg-v2-up.json"],
                codegenome_v2_decoy_downstream=paths["cg-v2-decoy.json"],
                graphify_v1=paths["graph-v1.json"],
                graphify_v2=paths["graph-v2.json"],
            )
            self.assertTrue(report["matched_result"]["both_passed"])
            self.assertIsNone(report["matched_result"]["winner"])
            self.assertEqual(report["matched_result"]["authority_effect"], "none")
            self.assertEqual(report["matched_result"]["unrelated_capabilities_promoted"], [])
            self.assertTrue(report["providers"]["codegenome"]["checks"]["full_rebuild_currentness"])
            self.assertTrue(report["providers"]["graphify"]["checks"]["full_rebuild_currentness"])

            schema = json.loads((ROOT / "schemas" / "component-capability-qualification.schema.json").read_text())
            validator = jsonschema.Draft202012Validator(schema)
            for provider in ("codegenome", "graphify"):
                qualification = report["providers"][provider]["qualification"]
                errors = list(validator.iter_errors(qualification))
                self.assertEqual(errors, [], [error.message for error in errors])
                self.assertEqual(qualification["result"]["earned_maturity"], "evidence_proven")
                self.assertEqual(qualification["result"]["authority_effect"], "none")

    def test_stale_v1_relationship_fails_currentness(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            names = [
                "cg-v1-down.json", "cg-v1-up.json", "cg-v1-decoy.json",
                "cg-v2-down.json", "cg-v2-up.json", "cg-v2-decoy.json",
                "graph-v1.json", "graph-v2.json",
            ]
            paths = {name: root / name for name in names}
            _cg(paths["cg-v1-down.json"], [5, 1])
            _cg(paths["cg-v1-up.json"], [5, 9])
            _cg(paths["cg-v1-decoy.json"], [5, 12])
            _cg(paths["cg-v2-down.json"], [5, 1, 13])
            _cg(paths["cg-v2-up.json"], [5, 9])
            _cg(paths["cg-v2-decoy.json"], [5, 12])
            _graph(paths["graph-v1.json"], [("main.rs", "middle", "leaf")])
            _graph(
                paths["graph-v2.json"],
                [("main.rs", "middle", "leaf"), ("main.rs", "middle", "replacement_leaf")],
            )
            report = build_qualification_report(
                agent_memory_commit="a" * 40,
                fixture_paths=sorted(FIXTURE_ROOT.glob("v*/*.rs")),
                codegenome_v1_main_downstream=paths["cg-v1-down.json"],
                codegenome_v1_main_upstream=paths["cg-v1-up.json"],
                codegenome_v1_decoy_downstream=paths["cg-v1-decoy.json"],
                codegenome_v2_main_downstream=paths["cg-v2-down.json"],
                codegenome_v2_main_upstream=paths["cg-v2-up.json"],
                codegenome_v2_decoy_downstream=paths["cg-v2-decoy.json"],
                graphify_v1=paths["graph-v1.json"],
                graphify_v2=paths["graph-v2.json"],
            )
            self.assertFalse(report["matched_result"]["both_passed"])
            self.assertFalse(report["providers"]["codegenome"]["checks"]["full_rebuild_currentness"])
            self.assertFalse(report["providers"]["graphify"]["checks"]["full_rebuild_currentness"])


if __name__ == "__main__":
    unittest.main()
