from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schemas" / "benchmark-deficit-ledger.schema.json"
LEDGER = ROOT / "reports" / "benchmarks" / "deficits" / "current.json"

OPEN_STATES = {"open", "remediating", "blocked", "awaiting_replay", "improved_not_frontier"}
CLOSED_STATES = {"frontier", "accepted_tradeoff", "deliberate_non_goal", "invalidated_evidence"}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class BenchmarkDeficitLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = _load(SCHEMA)
        cls.ledger = _load(LEDGER)
        cls.deficits = cls.ledger["deficits"]

    def test_schema_validates(self):
        errors = sorted(
            Draft202012Validator(self.schema).iter_errors(self.ledger),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual(errors, [])

    def test_deficit_ids_are_unique(self):
        ids = [item["deficit_id"] for item in self.deficits]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_active_material_deficit_has_owner_posture_and_replay(self):
        for item in self.deficits:
            if item["state"] in OPEN_STATES:
                self.assertIsNotNone(item["owning_issue"], item["deficit_id"])
                self.assertTrue(item["posture"], item["deficit_id"])
                self.assertTrue(item["evidence_refs"], item["deficit_id"])
                self.assertTrue(item["replay_requirements"], item["deficit_id"])

    def test_closed_deficits_require_closure_evidence_and_date(self):
        for item in self.deficits:
            if item["state"] in CLOSED_STATES:
                self.assertTrue(item["closed_at"], item["deficit_id"])
                self.assertTrue(item["closure_evidence"], item["deficit_id"])

    def test_published_reference_gap_cannot_masquerade_as_same_harness_frontier(self):
        for item in self.deficits:
            if item["posture"] == "published_reference_gap":
                self.assertIsNotNone(item["published_frontier"], item["deficit_id"])

    def test_frontier_but_inadequate_stays_open(self):
        for item in self.deficits:
            if item["posture"] == "frontier_but_inadequate":
                self.assertIn(item["state"], OPEN_STATES, item["deficit_id"])
                self.assertIsNotNone(item["adequacy_target"], item["deficit_id"])

    def test_frontier_closure_requires_adequacy_target(self):
        for item in self.deficits:
            if item["state"] == "frontier":
                self.assertIsNotNone(item["adequacy_target"], item["deficit_id"])
                self.assertTrue(item["closure_evidence"], item["deficit_id"])

    def test_missing_and_blocked_states_are_not_numeric_zero(self):
        for item in self.deficits:
            if item["posture"] == "blocked":
                self.assertNotEqual(item["agent_memory"], 0, item["deficit_id"])


if __name__ == "__main__":
    unittest.main()
