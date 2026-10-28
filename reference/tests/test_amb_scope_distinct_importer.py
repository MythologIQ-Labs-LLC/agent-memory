"""Successor AMB importer guards: v7 protocol, not trailing adapter revision v1.

These checks must run before a successor score is accepted. The legacy v1-v7
lanes are unchanged.
"""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANES = ROOT / "reference" / "agentmem_ref" / "evaluation" / "lanes"


def _importer():
    source = ROOT / "scripts" / "import_amb_lane_evidence.py"
    spec = importlib.util.spec_from_file_location("scope_distinct_amb_importer", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lane(lane_id):
    return json.loads((LANES / (lane_id + ".json")).read_text(encoding="utf-8"))


class ScopeDistinctAmbImporterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.importer = _importer()
        cls.control_id = "amb-precisionmembench-retrieval-v7-scope-distinct-v1"
        cls.control = _lane(cls.control_id)
        cls.row = next(row for row in cls.control["systems"] if row["role"] == "control")

    def test_generation_is_v7_not_the_store_profile_revision_v1(self):
        self.assertEqual(self.importer.lane_generation(self.control), 7)
        for generation in range(1, 8):
            lane = _lane(f"amb-precisionmembench-retrieval-v{generation}")
            self.assertEqual(self.importer.lane_generation(lane), generation)

    def test_successor_control_requires_cross_fact_sidecar(self):
        self.assertTrue(self.importer.requires_cross_fact_sidecar(self.control, self.row))
        bm25 = next(row for row in self.control["systems"] if row["provider_key"] == "bm25")
        self.assertFalse(self.importer.requires_cross_fact_sidecar(self.control, bm25))

    def test_successor_identity_requires_new_bridge_and_runner(self):
        expected = self.importer.lane_reference_blobs(self.control)
        self.assertEqual(set(expected), {
            "reference/amb_agent_memory_bridge_scope_distinct.py",
            "reference/run_amb_external_scope_distinct.py",
            "reference/amb_mem0_explicit_bridge.py",
        })
        identity = {
            "bridge_blobs": expected.copy(),
            "lane_digest_sha256": self.importer.lane_digest(self.control),
        }
        self.importer.check_lane_pins(identity, self.control)
        for missing in expected:
            corrupted = {**identity, "bridge_blobs": {
                path: sha for path, sha in expected.items() if path != missing
            }}
            with self.subTest(missing=missing), self.assertRaises(self.importer.ImportError_):
                self.importer.check_lane_pins(corrupted, self.control)

    def test_frozen_original_v7_keeps_original_bridge_pin(self):
        old = _lane("amb-precisionmembench-retrieval-v7")
        self.assertEqual(self.importer.lane_generation(old), 7)
        self.assertEqual(
            self.importer.lane_reference_blobs(old)["reference/amb_agent_memory_bridge.py"],
            "3d9ccb31587b55edf4ddb714d6e8ff41d5b03228",
        )


if __name__ == "__main__":
    unittest.main()
