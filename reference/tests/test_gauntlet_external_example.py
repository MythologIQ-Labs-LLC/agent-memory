from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.evaluation.contract import load_run
from agentmem_ref.evaluation.gauntlet_contract import load_manifest
from agentmem_ref.evaluation.gauntlet_orchestrator import run_gauntlet
from agentmem_ref.evaluation.gauntlet_profiles import ORCHESTRATION_PROBE_PROFILE_ID


EXAMPLE_DIR = REPO_ROOT / "examples" / "gauntlet"
MANIFEST = EXAMPLE_DIR / "minimal-stdio-adapter.json"
ADAPTER = EXAMPLE_DIR / "minimal_stdio_adapter.py"


class ExternalGauntletExampleTests(unittest.TestCase):
    def test_manifest_is_valid_and_example_is_runtime_independent(self):
        manifest = load_manifest(MANIFEST)
        self.assertEqual(manifest["transport"]["kind"], "stdio")
        self.assertEqual(manifest["system"]["kind"], "external_memory")
        self.assertNotIn("trusted_fixture", manifest.get("metadata", {}))

        source = ADAPTER.read_text(encoding="utf-8")
        self.assertNotIn("agentmem_ref", source)
        self.assertNotIn("agent_memory", source)

    def test_external_example_requires_opt_in_and_completes_probe(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            blocked_process = run_gauntlet(
                MANIFEST,
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "blocked-process",
            )
            self.assertEqual(blocked_process["status"], "blocked")
            self.assertEqual(
                blocked_process["failure"]["code"],
                "external_process_opt_in_required",
            )

            blocked_reset = run_gauntlet(
                MANIFEST,
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "blocked-reset",
                allow_external_process=True,
            )
            self.assertEqual(blocked_reset["status"], "blocked")
            self.assertEqual(
                blocked_reset["failure"]["code"],
                "destructive_operation_opt_in_required",
            )

            completed = run_gauntlet(
                MANIFEST,
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "completed",
                allow_external_process=True,
                allow_destructive_reset=True,
            )
            self.assertEqual(completed["status"], "complete")
            normalized = load_run(completed["artifacts"]["normalized_run"]["path"])
            self.assertEqual(normalized["authority_effect"], "none")
            self.assertEqual(
                normalized["dimensions"]["retrieval"]["metrics"][0]["value"],
                1.0,
            )
            self.assertEqual(
                normalized["native_results"]["profile_kind"],
                "baseline_or_probe",
            )


if __name__ == "__main__":
    unittest.main()
