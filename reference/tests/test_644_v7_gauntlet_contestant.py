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
        # validation(#644): the basis the v5/v6 records state (baseline-v6.json
        # qualification_evidence.public_gauntlet_baseline_qualification.configuration_digest_basis).
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        source = ADAPTER.read_text(encoding="utf-8")
        constant = lambda name: source.split(f'\n{name} = "', 1)[1].split('"', 1)[0]  # noqa: E731
        config = {
            "runtime_profile": m["metadata"]["runtime_profile"],
            "public_contract": constant("PUBLIC_CONTRACT_VERSION"),
            "frozen_runtime_revision": constant("FROZEN_RUNTIME_REVISION"),
            "tenant": constant("TENANT"),
            "actor": constant("ACTOR"),
            "scope": constant("SCOPE"),
            "purpose": constant("PURPOSE"),
        }
        self.assertEqual(config["frozen_runtime_revision"], EXPECTED_RUNTIME)
        digest = hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(m["system"]["configuration_digest"], "sha256:" + digest)

if __name__ == "__main__":
    unittest.main()
