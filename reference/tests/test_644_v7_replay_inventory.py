"""Evidence inventory is deliberately not a v7 acceptance oracle."""
import json
import runpy
import tempfile
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/check_644_v7_replay_inventory.py"
inventory = runpy.run_path(str(SCRIPT))["inventory"]


class V7ReplayInventoryTests(unittest.TestCase):
    def test_declared_replays_are_missing_until_real_evidence_exists(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            declaration = root / "declaration.json"
            declaration.write_text(json.dumps({
                "baseline_id": "agent-memory-runtime-baseline-v7", "issue": 644,
                "acceptance_evidence_required": [
                    {"kind": "replay", "ref": "first"},
                    {"kind": "replay", "ref": "second"},
                    {"kind": "lane", "ref": "not-a-replay"},
                ],
            }), encoding="utf-8")
            result = inventory(declaration, root / "evidence")
            self.assertEqual(result["qualification"], "BLOCKED")
            self.assertEqual([x["status"] for x in result["replays"]], ["MISSING", "MISSING"])
            manifest = root / "evidence" / "first" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"replay_id":"first","status":"PASS"}', encoding="utf-8")
            result = inventory(declaration, root / "evidence")
            self.assertEqual([x["status"] for x in result["replays"]], ["UNVERIFIED", "MISSING"])
            self.assertEqual(result["qualification"], "BLOCKED")

    def test_duplicate_and_traversal_replay_ids_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            declaration = root / "decl.json"
            for ids in (["a", "a"], ["../escape"], []):
                declaration.write_text(json.dumps({
                    "baseline_id": "agent-memory-runtime-baseline-v7", "issue": 644,
                    "acceptance_evidence_required": [
                        {"kind": "replay", "ref": key} for key in ids
                    ],
                }), encoding="utf-8")
                with self.subTest(ids=ids), self.assertRaises(ValueError):
                    inventory(declaration, root / "evidence")


if __name__ == "__main__":
    unittest.main()
