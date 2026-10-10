"""Candidate-only #644 v7 Gauntlet manifest provenance guards."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "examples/gauntlet/agent-memory-runtime-baseline-v7.json"
ADAPTER = ROOT / "examples/gauntlet/agent_memory_runtime_baseline_v7_stdio.py"
EXPECTED_RUNTIME = "16a248b1e28f455fbf19217114175f0c20df2a01"


class V7GauntletCandidateTests(unittest.TestCase):
    def test_adapter_manifest_pins_exact_candidate_not_v6(self):
        record = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(record["system"]["revision"], "git-commit:" + EXPECTED_RUNTIME)
        self.assertEqual(record["metadata"]["provenance_class"], "unqualified_transition_probe")
        self.assertEqual(record["metadata"]["baseline_id"], "agent-memory-runtime-baseline-v7")
        self.assertEqual(record["authority_effect"], "none")
        self.assertEqual(record["transport"]["startup"][1], str(ADAPTER.relative_to(ROOT)))
        blob = subprocess.check_output(["git", "hash-object", str(ADAPTER)], cwd=ROOT, text=True).strip()
        self.assertEqual(record["adapter"]["revision"], "git-blob:" + blob)
        source = ADAPTER.read_text(encoding="utf-8")
        self.assertIn("FROZEN_RUNTIME_REVISION = \"" + EXPECTED_RUNTIME + "\"", source)
        self.assertNotIn("tenant:gauntlet-runtime-baseline-v6", source)

    def test_configuration_digest_is_reproducible_and_non_authoritative(self):
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        config = {
            "adapter_blob": m["adapter"]["revision"].removeprefix("git-blob:"),
            "runtime_commit": m["system"]["revision"].removeprefix("git-commit:"),
            "tenant": "tenant:gauntlet-runtime-baseline-v7",
            "scope": "scope:gauntlet-runtime-baseline-v7",
            "public_contract": "1.6.0",
            "transport": "stdio",
        }
        digest = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(m["system"]["configuration_digest"], "sha256:" + digest)


if __name__ == "__main__":
    unittest.main()
