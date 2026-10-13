"""Invariants of reference/comparators/source_qualification_789.json.

Verified 2026-10-13 against upstream by anonymous git fetch and the PyPI wheels:
- getzep/graphiti tag v0.29.3 = 021d3a57d511f21b10adaf7fa923bd5c1fce5e9d; the PyPI wheel
  graphiti_core-0.29.3 is tree-identical to that commit (159/159 files). The earlier pin
  b2ff2ead differs from the wheel in graphiti_core/search/search.py.
- topoteretes/cognee tag v1.4.2 = b0ea53e95caa7bfebf373ffabfbafb44f9fff922; the cognee/
  package tree at 4b9dd362 and at the tag are identical to the PyPI wheel (1973/1973 files).
No network access is needed to run this test.
"""
import json
import re
import unittest
from pathlib import Path

REGISTRY = Path(__file__).resolve().parents[1] / "comparators" / "source_qualification_789.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TYPED_STATES = {
    "not_started", "source_qualified", "install_qualified", "protocol_qualified",
    "executed_unaccepted", "accepted_same_harness", "unsupported_profile",
    "blocked_cost", "blocked_dependency", "rejected_noncomparable",
}


class SourceQualificationRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.systems = {s["system_id"]: s for s in cls.doc["systems"]}

    def test_no_scores_and_no_authority(self):
        self.assertEqual(self.doc["same_harness_results"], [])
        self.assertTrue(self.doc["no_metric_scores"])
        self.assertEqual(self.doc["authority_effect"], "none")
        for system in self.doc["systems"]:
            self.assertNotIn("accepted", system["compatibility_status"])
            self.assertNotEqual(system["typed_state_789"], "accepted_same_harness")
            for key in ("metrics", "scores", "recall", "ndcg", "ranked_top"):
                self.assertNotIn(key, system, system["system_id"])

    def test_revisions_are_exact_and_blobs_are_hex(self):
        for system in self.doc["systems"]:
            self.assertRegex(system["exact_source_revision"], HEX40)
            for key, value in system.items():
                if key.endswith("_git_blob") and value is not None:
                    self.assertRegex(value, HEX40, key)

    def test_graphiti_pin_is_the_wheel_source(self):
        graphiti = self.systems["graphiti-oss"]
        self.assertEqual(graphiti["observed_package_version"], "0.29.3")
        self.assertEqual(graphiti["exact_source_revision"], "021d3a57d511f21b10adaf7fa923bd5c1fce5e9d")
        self.assertEqual(graphiti["release_tag"], "v0.29.3")

    def test_cognee_pin_matches_release_tag_tree(self):
        cognee = self.systems["cognee-oss"]
        self.assertEqual(cognee["observed_package_version"], "1.4.2")
        self.assertEqual(cognee["exact_source_revision"], "4b9dd362625dfd3621c344e571a86f5bc7a55ee8")
        self.assertEqual(cognee["release_tag"], "v1.4.2")
        self.assertEqual(cognee["release_tag_commit"], "b0ea53e95caa7bfebf373ffabfbafb44f9fff922")

    def test_typed_state_is_one_of_the_issue_states(self):
        for system in self.doc["systems"]:
            self.assertIn(system["typed_state_789"], TYPED_STATES, system["system_id"])


if __name__ == "__main__":
    unittest.main()
