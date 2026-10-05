"""Raw AMB lane artifacts become bound evidence records only through verified import (#640)."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "import_amb_lane_evidence.py"
LANE_FILE = "reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v1.json"


def _load_script():
    spec = importlib.util.spec_from_file_location("import_amb_lane_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _lane() -> dict:
    return json.loads((REPO_ROOT / LANE_FILE).read_text(encoding="utf-8"))


def _write_artifact(root: Path, run_id: str, memory: str, revision: str, *, results: list[dict], identity_overrides: dict | None = None) -> Path:
    lane = _lane()
    artifact = root / run_id / f"amb-precisionmembench-single-turn-{memory}-{revision}"
    (artifact / "precisionmembench" / f"{memory}-{revision[:12]}" / "retrieval").mkdir(parents=True)
    summary = {
        "dataset": "precisionmembench",
        "split": "single-turn",
        "category": None,
        "memory_provider": memory,
        "run_name": f"{memory}-{revision[:12]}",
        "mode": "retrieval",
        "oracle": False,
        "total_queries": len(results),
        "correct": sum(1 for r in results if r["correct"]),
        "accuracy": sum(1 for r in results if r["correct"]) / len(results),
        "ingestion_time_ms": 12.5,
        "ingested_docs": 35,
        "answer_llm": None,
        "judge_llm": None,
        "results": results,
    }
    identity = {
        "agent_memory_revision": revision,
        "amb_pmb_return_cap": None,
        "amb_revision": lane["harness"]["revision"],
        "answer_model": None,
        "judge_model": None,
        "authority_effect": "none",
        "dataset": "precisionmembench",
        "split": "single-turn",
        "mode": "retrieval",
        "memory": memory,
        "query_limit": "0",
        "full_selection": True,
        "lane_id": lane["lane_id"],
        "lane_file": LANE_FILE,
        "harness_constraints": {"uv_lock_git_blob": lane["execution"]["environment"]["harness_lock"]["git_blob"]},
        "resolved_packages": {"mem0ai": "2.2.1"},
        "mem0_optional_components": {"fastembed_installed": False, "spacy_installed": False},
        "workflow_run_id": run_id,
    }
    identity.update(identity_overrides or {})
    files = {
        "execution-identity.json": json.dumps(identity, indent=2, sort_keys=True).encode(),
        "amb-constraints.txt": b"torch==2.10.0\n",
        "amb-constraints-provenance.json": b"{}\n",
        "precisionmembench-selfcheck.txt": b"43/43 77/77\n",
        f"precisionmembench/{memory}-{revision[:12]}/retrieval/single-turn.json": json.dumps(summary, indent=2).encode(),
    }
    for name, payload in files.items():
        (artifact / name).write_bytes(payload)
    listing = "\n".join(f"./{name}" for name in sorted(files)) + "\n./files.txt\n"
    (artifact / "files.txt").write_text(listing, encoding="utf-8")
    inventory = "".join(f"{_sha(payload)}  ./{name}\n" for name, payload in files.items())
    inventory += f"{_sha(listing.encode())}  ./files.txt\n"
    (artifact / "sha256.txt").write_text(inventory, encoding="utf-8")
    return artifact


def _results(n_active_pass: int) -> list[dict]:
    lane = _lane()
    total = lane["dataset"]["query_count"]
    results = []
    for index in range(total):
        pass_type = "active" if index < 43 else ("structural" if index < 68 else "trivially-empty")
        correct = pass_type == "active" and index < n_active_pass
        results.append(
            {
                "query_id": f"case-{index}",
                "correct": correct,
                "retrieve_time_ms": 10.0,
                "meta": {
                    "pass_type": pass_type,
                    "active_pass": correct and pass_type == "active",
                    "retrieval_precision": 0.5 if pass_type == "active" else None,
                    "retrieval_recall": 1.0 if pass_type == "active" else None,
                    "resolution": {"source_id": 3},
                },
            }
        )
    return results


class ImportAmbLaneEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_script()

    def test_import_copies_verified_files_and_binds_the_row(self):
        with tempfile.TemporaryDirectory() as temporary:
            runs = Path(temporary) / "runs"
            out = Path(temporary) / "out"
            _write_artifact(runs, "123", "mem0-explicit", "b" * 40, results=_results(4))
            self.module.main(["--runs-dir", str(runs), "--output-root", str(out), "--no-fetch", "--lane-at-head"])
            destination = out / "amb-precisionmembench-retrieval-v1" / f"mem0-explicit-{'b' * 12}"
            record = json.loads((destination / "evidence.json").read_text(encoding="utf-8"))
            lane = _lane()
            self.assertEqual(record["input"]["sha256"], lane["dataset"]["input_sha256"])
            self.assertEqual(record["system"]["id"], "mem0-oss")
            self.assertEqual(record["system"]["revision"], "94c3fe9f238f3dbf29c9ce98643bd71eb13077cd")
            self.assertEqual(record["row"]["role"], "comparator")
            self.assertEqual(record["native_summary"]["active_passes"], 4)
            self.assertEqual(record["native_summary"]["active_total"], 43)
            self.assertEqual(record["native_summary"]["total_passes"], 4)
            self.assertEqual(record["native_summary"]["mean_precision"], 0.5)
            self.assertEqual(record["native_summary"]["id_resolution"], {"source_id": 231})
            self.assertEqual(record["authority_effect"], "none")
            for name in ("single-turn.json", "execution-identity.json", "sha256.txt", "files.txt"):
                self.assertTrue((destination / name).is_file(), name)
            self.assertEqual(record["files"]["single-turn.json"], _sha((destination / "single-turn.json").read_bytes()))

    def test_agent_memory_row_binds_the_executing_repository_revision(self):
        with tempfile.TemporaryDirectory() as temporary:
            runs = Path(temporary) / "runs"
            out = Path(temporary) / "out"
            _write_artifact(runs, "124", "agent-memory", "c" * 40, results=_results(2))
            self.module.main(["--runs-dir", str(runs), "--output-root", str(out), "--no-fetch", "--lane-at-head"])
            record = json.loads((out / "amb-precisionmembench-retrieval-v1" / f"agent-memory-{'c' * 12}" / "evidence.json").read_text())
            self.assertEqual(record["system"]["id"], "agent-memory")
            self.assertEqual(record["system"]["revision"], "c" * 40)
            self.assertEqual(record["row"]["role"], "control")

    def test_import_refuses_tampered_or_off_lane_artifacts(self):
        cases = [
            ({"full_selection": False}, "full-selection"),
            ({"amb_pmb_return_cap": "5"}, "full-selection"),
            ({"lane_id": None}, "did not execute a lane"),
            ({"amb_revision": "0" * 40}, "harness revision"),
            ({"memory": "cognee"}, "no row for provider"),
            ({"harness_constraints": {"uv_lock_git_blob": "1" * 40}}, "lock blob"),
            ({"workflow_run_id": "999"}, "workflow_run_id"),
        ]
        for overrides, message in cases:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as temporary:
                runs = Path(temporary) / "runs"
                memory = overrides.get("memory", "bm25")
                _write_artifact(runs, "125", memory, "d" * 40, results=_results(0), identity_overrides=overrides)
                with self.assertRaisesRegex(self.module.ImportError_, message):
                    self.module.main(["--runs-dir", str(runs), "--output-root", str(Path(temporary) / "out"), "--no-fetch", "--lane-at-head"])
        with tempfile.TemporaryDirectory() as temporary:
            runs = Path(temporary) / "runs"
            artifact = _write_artifact(runs, "126", "bm25", "e" * 40, results=_results(0))
            summary_path = next(artifact.glob("precisionmembench/*/retrieval/single-turn.json"))
            summary_path.write_text(summary_path.read_text() + "\n", encoding="utf-8")
            with self.assertRaisesRegex(self.module.ImportError_, "inventory"):
                self.module.main(["--runs-dir", str(runs), "--output-root", str(Path(temporary) / "out"), "--no-fetch", "--lane-at-head"])


if __name__ == "__main__":
    unittest.main()
