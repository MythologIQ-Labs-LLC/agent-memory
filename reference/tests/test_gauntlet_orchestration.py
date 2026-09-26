from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from agentmem_ref._paths import REPO_ROOT
from agentmem_ref.console import main as console_main
from agentmem_ref.evaluation.contract import load_run
from agentmem_ref.evaluation.gauntlet_orchestrator import run_gauntlet
from agentmem_ref.evaluation.gauntlet_profiles import ORCHESTRATION_PROBE_PROFILE_ID


FIXTURE_DIR = REPO_ROOT / "fixtures" / "gauntlet"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _write_manifest(root: Path, value: dict, name: str = "adapter.json") -> Path:
    path = root / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class GauntletOrchestrationTests(unittest.TestCase):
    def test_no_memory_and_lexical_baselines_share_one_orchestration_contract(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            no_memory = run_gauntlet(
                FIXTURE_DIR / "no-memory-adapter.json",
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root,
            )
            lexical = run_gauntlet(
                FIXTURE_DIR / "lexical-adapter.json",
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root,
            )

            self.assertEqual(no_memory["status"], "complete")
            self.assertEqual(lexical["status"], "complete")
            no_run = load_run(no_memory["artifacts"]["normalized_run"]["path"])
            lex_run = load_run(lexical["artifacts"]["normalized_run"]["path"])
            self.assertEqual(no_run["native_results"]["profile_kind"], "baseline_or_probe")
            self.assertEqual(no_run["dimensions"]["retrieval"]["metrics"][0]["value"], 0.0)
            self.assertEqual(lex_run["dimensions"]["retrieval"]["metrics"][0]["value"], 1.0)
            self.assertEqual(
                no_run["benchmark"]["input_sha256"],
                lex_run["benchmark"]["input_sha256"],
            )
            self.assertEqual(no_run["authority_effect"], "none")
            self.assertEqual(lex_run["authority_effect"], "none")

    def test_stdio_transport_requires_explicit_opt_in_and_then_executes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _load_fixture("lexical-adapter.json")
            manifest["system"] = dict(manifest["system"], id="gauntlet-lexical-stdio")
            manifest["adapter"] = dict(
                manifest["adapter"],
                id="gauntlet-lexical-stdio-fixture",
                revision="builtin-stdio-v1",
            )
            manifest["transport"] = {
                "kind": "stdio",
                "startup": [
                    sys.executable,
                    "-m",
                    "agentmem_ref.evaluation.gauntlet_stdio_fixture",
                ],
            }
            manifest["metadata"] = {"provenance_class": "baseline_or_probe"}
            path = _write_manifest(root, manifest)

            blocked = run_gauntlet(
                path,
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "blocked",
            )
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["failure"]["source"], "orchestrator")
            self.assertEqual(blocked["failure"]["code"], "external_process_opt_in_required")

            completed = run_gauntlet(
                path,
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "completed",
                allow_external_process=True,
            )
            self.assertEqual(completed["status"], "complete")
            run = load_run(completed["artifacts"]["normalized_run"]["path"])
            self.assertEqual(run["dimensions"]["retrieval"]["metrics"][0]["value"], 1.0)

    def test_adapter_exception_is_attributed_to_system_adapter(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _load_fixture("lexical-adapter.json")
            manifest["system"] = dict(manifest["system"], id="gauntlet-broken-fixture")
            manifest["adapter"] = dict(manifest["adapter"], id="gauntlet-broken-fixture")
            manifest["transport"] = {
                "kind": "in_process",
                "callable": "agentmem_ref.evaluation.gauntlet_baselines:broken_adapter",
            }
            path = _write_manifest(root, manifest)
            result = run_gauntlet(
                path,
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "runs",
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failure"]["source"], "system_adapter")
            self.assertEqual(result["failure"]["code"], "adapter_exception")
            run = load_run(result["artifacts"]["normalized_run"]["path"])
            self.assertEqual(run["status"], "blocked")
            self.assertEqual(run["dimensions"]["retrieval"]["status"], "blocked")

    def test_reset_probe_refuses_unproven_isolation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _load_fixture("lexical-adapter.json")
            manifest["benchmark_isolation"] = {
                "strategy": "tenant",
                "description": "declared tenant only; disposable teardown not established",
            }
            path = _write_manifest(root, manifest)
            result = run_gauntlet(
                path,
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "runs",
            )
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["failure"]["code"], "unproven_destructive_isolation")

    def test_unsupported_required_capability_is_not_execution_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _load_fixture("lexical-adapter.json")
            manifest["capabilities"]["recall"] = {"support": "unsupported"}
            path = _write_manifest(root, manifest)
            result = run_gauntlet(
                path,
                ORCHESTRATION_PROBE_PROFILE_ID,
                output_dir=root / "runs",
            )
            self.assertEqual(result["status"], "unsupported")
            self.assertEqual(result["negotiation"]["outcome"], "unsupported")
            self.assertNotIn("failure", result)
            self.assertNotIn("normalized_run", result["artifacts"])

    def test_console_routes_gauntlet_without_runtime_import_contract(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = console_main(["gauntlet", "list", "--json"])
        self.assertEqual(code, 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["command"], "gauntlet_list")
        self.assertGreaterEqual(report["profile_count"], 1)
        self.assertEqual(report["authority_effect"], "none")


if __name__ == "__main__":
    unittest.main()
