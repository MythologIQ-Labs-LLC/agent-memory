from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.evaluation.gauntlet_orchestrator import run_gauntlet
from agentmem_ref.evaluation.gauntlet_profiles import (
    ORCHESTRATION_PROBE_PROFILE_ID,
    get_gauntlet_profile,
)


EXAMPLE_MANIFEST = REPO_ROOT / "examples" / "gauntlet" / "minimal-stdio-adapter.json"
FIXTURE_MANIFEST = REPO_ROOT / "fixtures" / "gauntlet" / "lexical-adapter.json"


def _manifest() -> dict:
    return json.loads(EXAMPLE_MANIFEST.read_text(encoding="utf-8"))


def _write_manifest(root: Path, value: dict, *, name: str = "adapter.json") -> Path:
    path = root / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_script(root: Path, source: str, *, name: str = "adapter.py") -> Path:
    path = root / name
    path.write_text(source, encoding="utf-8")
    return path


class GauntletExternalAdversarialTests(unittest.TestCase):
    def test_stdio_startup_failure_is_attributed_to_system_adapter(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _manifest()
            manifest["transport"] = {
                "kind": "stdio",
                "startup": [str(root / "does-not-exist")],
            }
            result = run_gauntlet(
                _write_manifest(root, manifest),
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "runs",
                allow_external_process=True,
                allow_destructive_reset=True,
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failure"]["source"], "system_adapter")
            self.assertEqual(result["failure"]["code"], "startup_failed")

    def test_invalid_stdio_json_is_attributed_to_system_adapter(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = _write_script(
                root,
                "import sys\nfor _line in sys.stdin:\n    print('not-json', flush=True)\n",
            )
            manifest = _manifest()
            manifest["transport"] = {"kind": "stdio", "startup": [sys.executable, str(script)]}
            result = run_gauntlet(
                _write_manifest(root, manifest),
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "runs",
                allow_external_process=True,
                allow_destructive_reset=True,
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failure"]["source"], "system_adapter")
            self.assertEqual(result["failure"]["code"], "invalid_adapter_json")

    def test_valid_system_error_remains_attributed_to_system_under_test(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            script = _write_script(
                root,
                """import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    response = {
        "contract_family": "agent-memory-gauntlet-operation",
        "contract_version": "0.1.0",
        "direction": "response",
        "operation": request["operation"],
        "request_id": request["request_id"],
        "status": "system_error",
        "result": None,
        "error": {
            "source": "system_under_test",
            "code": "sut_failure",
            "message": "synthetic SUT failure",
        },
        "timing": {"elapsed_ms": 0.0},
        "adapter_evidence": {},
        "authority_effect": "none",
    }
    print(json.dumps(response, sort_keys=True), flush=True)
""",
            )
            manifest = _manifest()
            manifest["transport"] = {"kind": "stdio", "startup": [sys.executable, str(script)]}
            result = run_gauntlet(
                _write_manifest(root, manifest),
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "runs",
                allow_external_process=True,
                allow_destructive_reset=True,
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failure"]["source"], "system_under_test")
            self.assertEqual(result["failure"]["code"], "sut_failure")

    def test_missing_profile_runner_is_attributed_to_benchmark_adapter(self):
        profile = get_gauntlet_profile(ORCHESTRATION_PROBE_PROFILE_ID)
        profile["runner"] = "missing.gauntlet.runner:run"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch(
                "agentmem_ref.evaluation.gauntlet_orchestrator.get_gauntlet_profile",
                return_value=profile,
            ):
                result = run_gauntlet(
                    FIXTURE_MANIFEST,
                    ORCHESTRATION_PROBE_PROFILE_ID,
                    output_dir=root / "runs",
                )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failure"]["source"], "benchmark_adapter")
            self.assertEqual(result["failure"]["code"], "runner_unavailable")


if __name__ == "__main__":
    unittest.main()
