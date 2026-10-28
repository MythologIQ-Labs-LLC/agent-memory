"""Static GitHub Actions dispatch guard for a separately frozen AMB successor.

Does not dispatch Actions, import scores, or access the external harness.
"""
from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "amb-competitive.yml"
SUCCESSOR = "amb-precisionmembench-retrieval-v7-scope-distinct-v1"


class AmbScopeDistinctWorkflowWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_successor_is_an_explicit_dispatch_choice_not_the_default(self):
        self.assertIn("          - " + SUCCESSOR + "\n", self.workflow)
        self.assertIn('default: "amb-precisionmembench-retrieval-v6"', self.workflow)

    def test_runner_selection_is_exact_and_keeps_historical_runner(self):
        self.assertIn('if [ "${{ inputs.lane_id }}" = "' + SUCCESSOR + '" ]; then', self.workflow)
        self.assertIn('runner="reference/run_amb_external_scope_distinct.py"', self.workflow)
        self.assertIn('runner="reference/run_amb_external.py"', self.workflow)
        self.assertIn('PYTHONPATH=reference python "$runner" --amb-root', self.workflow)
        self.assertIn('if [ "${{ inputs.dataset }}" != "precisionmembench" ]', self.workflow)

    def test_new_lane_records_all_source_pins_not_old_bridge_blobs(self):
        self.assertIn('if lane["lane_id"] == "' + SUCCESSOR + '":', self.workflow)
        self.assertIn('lane["harness"]["source_blobs"].items()', self.workflow)
        self.assertIn('"bridge_blobs": bridge_blobs,', self.workflow)
        self.assertIn("LANE_FILE=reports/validation/v7-integration/amb-scope-distinct-successor/amb-precisionmembench-retrieval-v7-scope-distinct-v1.json", self.workflow)
        self.assertIn('"reference/amb_agent_memory_bridge.py": blob("reference/amb_agent_memory_bridge.py")',
                      self.workflow)

    def test_successor_source_hash_bypasses_host_clean_filter(self):
        # Deliberately forge the git-filtered blob of different source bytes.
        # The successor must hash raw source, not the host-supplied filter output.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True, capture_output=True)
            (root / ".gitattributes").write_text("payload.py filter=forge" + chr(10), encoding="utf-8")
            source = root / "payload.py"
            source.write_bytes(b"untrusted" + bytes([10]))

            def git_hash(*args):
                return subprocess.run(
                    ["git", *args, "hash-object", "payload.py"], cwd=root, check=True,
                    capture_output=True, text=True,
                ).stdout.strip()

            filtered = git_hash("-c", "filter.forge.clean=sed s/untrusted/trusted/g")
            raw_git = subprocess.run(
                ["git", "hash-object", "--no-filters", "payload.py"], cwd=root,
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            data = source.read_bytes()
            actual = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data).hexdigest()
            self.assertEqual(actual, raw_git)
            self.assertNotEqual(actual, filtered)
            self.assertIn('actual = hashlib.sha1(b"blob "', self.workflow)
            self.assertIn('return hashlib.sha1(b"blob "', self.workflow)
            self.assertIn("path: raw_blob(path)", self.workflow)
            self.assertIn('if lane["lane_id"] == "' + SUCCESSOR + '":', self.workflow)

    def test_existing_workflow_remains_manual_only_and_read_only(self):
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertIn("  contents: read", self.workflow)
        self.assertIn("amb-precisionmembench-retrieval-v7\n", self.workflow)


if __name__ == "__main__":
    unittest.main()
