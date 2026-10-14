"""#770: frozen v7 lanes must not inherit accepted v6 evidence."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
LANES = ROOT / "reference/agentmem_ref/evaluation/lanes"
DECL = ROOT / "reports/runtime/baseline-v7-declaration.json"
IDS = ("amb-precisionmembench-retrieval", "longmemeval-s-retrieval-parity")


class V7LaneFreezeGuards(unittest.TestCase):
    def test_candidate_has_new_identity_and_unaccepted_rows(self):
        declaration = json.loads(DECL.read_text(encoding="utf-8"))
        required = {e["ref"] for e in declaration["acceptance_evidence_required"] if e["kind"] == "lane"}
        self.assertEqual(required, {name + "-v7" for name in IDS})
        declaration_blob = subprocess.check_output(
            ["git", "hash-object", str(DECL)], cwd=ROOT, text=True).strip()
        for name in IDS:
            with self.subTest(lane=name):
                old_path = LANES / (name + "-v6.json")
                new_path = LANES / (name + "-v7.json")
                old = json.loads(old_path.read_text(encoding="utf-8"))
                new = json.loads(new_path.read_text(encoding="utf-8"))
                self.assertEqual(old["status"], "accepted")
                self.assertEqual(new["status"], "frozen")
                self.assertTrue(new["frozen_before_any_score"])
                self.assertEqual(new["owning_issue"], 770)
                self.assertEqual(new["lane_id"], name + "-v7")
                self.assertEqual(old["dataset"], new["dataset"])
                self.assertEqual(old["gold_identity"], new["gold_identity"])
                self.assertEqual(old["selection"], new["selection"])
                self.assertEqual(old["budget"], new["budget"])
                self.assertEqual(old["evaluator"], new["evaluator"])
                self.assertEqual(old["harness"], new["harness"])
                controls = [row for row in new["systems"] if row["role"] == "control"]
                self.assertEqual(len(controls), 1)
                p = controls[0]["configuration"]["runtime_baseline_posture"]
                self.assertEqual(p["declaration_blob"], declaration_blob)
                self.assertEqual(p["declared_successor"], "agent-memory-runtime-baseline-v7")
                self.assertFalse(any(row["status"] == "accepted" for row in new["systems"]))

    def test_v6_lane_blobs_unchanged_from_published_main(self):
        for name in IDS:
            path = "reference/agentmem_ref/evaluation/lanes/" + name + "-v6.json"
            current = subprocess.check_output(["git", "hash-object", path], cwd=ROOT, text=True).strip()
            baseline = subprocess.check_output(
                ["git", "rev-parse", "3eebb6d:" + path], cwd=ROOT, text=True).strip()
            self.assertEqual(current, baseline, path)


if __name__ == "__main__":
    unittest.main()
