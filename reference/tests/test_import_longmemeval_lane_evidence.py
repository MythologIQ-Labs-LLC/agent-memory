"""Raw LongMemEval lane artifacts become bound evidence records only through verified import (#640)."""

from __future__ import annotations

import copy
import gzip
import hashlib
import importlib.util
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "import_longmemeval_lane_evidence.py"
LANE_FILE = "reference/agentmem_ref/evaluation/lanes/longmemeval-s-retrieval-parity-v1.json"
REVISION = "0b0449a8aa2beca216563486dcbd2325673214e6"


def _load_script():
    spec = importlib.util.spec_from_file_location("import_longmemeval_lane_evidence", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


M = _load_script()


def _lane() -> dict:
    return json.loads((REPO_ROOT / LANE_FILE).read_text(encoding="utf-8"))


def _blob(path: str) -> str:
    return subprocess.run(["git", "hash-object", str(REPO_ROOT / path)], capture_output=True, text=True, check=True).stdout.strip()


def _report(lane: dict, backend: str, plane: str, *, external: dict | None = None) -> dict:
    count = lane["dataset"]["query_count"]
    rows = [
        {"question_id": f"q{i}", "question_type": "multi-session", "status": "scored", "corpus_size": 40, "gold": [f"answer_{i}"], "returned_count": 3, "ranked_top": [f"answer_{i}", "x", "y"], "metrics": {"recall_all@5": 1.0}, "runtime_error": None}
        for i in range(count)
    ]
    native = {
        "aggregate": {"evaluated_question_count": 419, "headline": {"recall_all@5": 0.5, "ndcg_any@5": 0.4, "recall_all@10": 0.6, "ndcg_any@10": 0.45}},
        "by_question_type": {},
        "currentness": {"knowledge_update": {"evaluated_question_count": 72, "headline": {"recall_all@5": 0.7}}, "latest_gold_ranked_first": {"rate": 0.3, "applicable_question_count": 35}},
        "failures": {"runtime_failure_count": 0, "ingestion_failure_count": 0, "out_of_corpus_returned_count": 0},
        "timing": {"wall_seconds": 12.0},
        "authority_effect": "none",
        "rows": rows,
    }
    if external is not None:
        native["external_system"] = {"system_id": external["system_id"], "system_revision": external["system_revision"], "unmapped_result_count_total": 0}
        native["timing"].update({"ingest_seconds_total": 9.0, "recall_seconds_total": 1.0, "recall_seconds_max": 0.1})
    return {
        "schema_version": "2.1.0",
        "profile_id": "agent-memory-longmemeval-retrieval-currentness-v1",
        "upstream": {"repository": "xiaowu0162/LongMemEval", "revision": lane["harness"]["revision"]},
        "input": {
            "path_name": "longmemeval_s_cleaned.json",
            "sha256": lane["dataset"]["input_sha256"],
            "corpus_class": "external_frozen",
            "source_question_count": count,
            "question_count": count,
            "selection": {"method": "all", "size": count, "question_ids_sha256": M.frozen_selection_digest(lane)},
        },
        "execution": {
            "agent_memory_revision": REVISION,
            "agent_memory_worktree_dirty": False,
            "python": "3.12.0",
            "platform": "Linux",
            "started_at": "2026-10-06T06:00:00+00:00",
            "backends": [backend],
            "external_backends": {backend: external} if external is not None else {},
            "granularities": [plane],
            "agent_memory_configuration": {"temporal_metadata": "none", "ranking_variant": "default"},
        },
        "planes": {plane: {"backends": {backend: native}}},
        "comparability": {"official_longmemeval_qa_score": "not_computed"},
        "claim_boundary": {"benchmark_score_is_authority": False},
    }


def _mem0_external(lane: dict) -> dict:
    row = next(item for item in lane["systems"] if item["provider_key"] == "mem0_explicit")
    return {
        "backend": "mem0_explicit",
        "system_id": "mem0-oss",
        "system_kind": "external_memory",
        "system_revision": row["source"]["revision"],
        "adapter_id": row["adapter"]["module"],
        "adapter_revision": lane["harness"]["source_blobs"][row["adapter"]["module"]],
        "configuration": {"inference": "none"},
        "install_posture": {"mem0ai": "2.2.1", "fastembed_installed": False, "spacy_installed": False},
        "authority_effect": "none",
    }


def _write_artifact(root: Path, run_id: str, backend: str, plane: str, *, report: dict | None = None, identity_overrides: dict | None = None, tamper_inventory: bool = False) -> Path:
    lane = _lane()
    external = _mem0_external(lane) if backend == "mem0_explicit" else None
    report = report if report is not None else _report(lane, backend, plane, external=external)
    artifact = root / run_id / f"longmemeval-lane-{backend}-{plane}-{REVISION}"
    artifact.mkdir(parents=True)
    identity = {
        "evidence_class": "same_harness_external_candidate",
        "agent_memory_revision": REVISION,
        "lane_id": lane["lane_id"],
        "lane_file": LANE_FILE,
        "lane_digest_sha256": M.lane_digest(M.validate_lane(lane)),
        "upstream_revision": lane["harness"]["revision"],
        "backend": backend,
        "granularity": plane,
        "subset_size": "0",
        "full_selection": True,
        "input_sha256": lane["dataset"]["input_sha256"],
        "source_blobs": M.lane_reference_blobs(lane),
        "resolved_packages": {"agent-memory-reference": "0.1.0", "mem0ai": "2.2.1", "qdrant-client": "1.17.0", "sentence-transformers": "5.2.3", "torch": "2.10.0"},
        "mem0_optional_components": {"fastembed_installed": False, "spacy_installed": False},
        "workflow_run_id": run_id,
        "authority_effect": "none",
    }
    identity.update(identity_overrides or {})
    files = {
        f"{plane}-{backend}.json": (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "execution-identity.json": (json.dumps(identity, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        "lane-validation.json": b'{"valid": true}\n',
    }
    for name, payload in files.items():
        (artifact / name).write_bytes(payload)
    names = sorted(list(files) + ["files.txt", "sha256.txt"])
    (artifact / "files.txt").write_text("".join(f"./{name}\n" for name in names), encoding="utf-8")
    inventory = {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()}
    inventory["files.txt"] = hashlib.sha256((artifact / "files.txt").read_bytes()).hexdigest()
    if tamper_inventory:
        inventory[f"{plane}-{backend}.json"] = "0" * 64
    (artifact / "sha256.txt").write_text("".join(f"{digest}  ./{name}\n" for name, digest in inventory.items()), encoding="utf-8")
    return artifact


class ImportLongMemEvalLaneEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.runs = Path(self.temporary.name) / "runs"
        self.output = Path(self.temporary.name) / "out"
        lane = _lane()
        for path, blob in M.lane_reference_blobs(lane).items():
            if _blob(path) != blob:
                self.skipTest(f"{path} differs from the frozen lane blob; the lane test reports that")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _import(self, run_id: str) -> Path:
        artifact = next((self.runs / run_id).iterdir())
        return M.import_artifact(run_id, artifact, repo_root=REPO_ROOT, output_root=self.output, fetch=False, lane_at_head=True)

    def test_built_in_and_external_rows_are_bound_and_recomposable(self) -> None:
        _write_artifact(self.runs, "1001", "lexical_overlap", "session")
        _write_artifact(self.runs, "1002", "mem0_explicit", "turn")
        lane = _lane()
        for run_id, backend, plane in (("1001", "lexical_overlap", "session"), ("1002", "mem0_explicit", "turn")):
            destination = self._import(run_id)
            self.assertEqual(destination.name, f"{backend}-{plane}-{REVISION[:12]}")
            record = json.loads((destination / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(record["contract_family"], M.CONTRACT_FAMILY)
            self.assertEqual(record["lane_id"], lane["lane_id"])
            self.assertEqual(record["lane_digest_at_execution"], M.lane_digest(M.validate_lane(lane)))
            self.assertEqual(record["input"]["sha256"], lane["dataset"]["input_sha256"])
            self.assertEqual(record["input"]["corpus_class"], "external_frozen")
            self.assertEqual(record["row"]["plane"], plane)
            self.assertEqual(record["authority_effect"], "none")
            self.assertEqual(record["native_summary"]["headline"]["recall_all@5"], 0.5)
            row = next(item for item in lane["systems"] if item["provider_key"] == backend)
            expected_revision = row["source"]["revision"] if row["source"]["kind"] == "python_package" else REVISION
            self.assertEqual(record["system"]["revision"], expected_revision)
            report = json.loads((destination / "report.json").read_text(encoding="utf-8"))
            self.assertNotIn("rows", report["planes"][plane]["backends"][backend])
            rows = json.loads(gzip.open(destination / "report.rows.json.gz", "rt", encoding="utf-8").read())
            self.assertEqual(len(rows[plane][backend]), lane["dataset"]["query_count"])
            report["planes"][plane]["backends"][backend]["rows"] = rows[plane][backend]
            recomposed = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
            self.assertEqual(hashlib.sha256(recomposed).hexdigest(), record["raw_report"]["sha256"])
            for name, digest in record["files"].items():
                self.assertEqual(hashlib.sha256((destination / name).read_bytes()).hexdigest(), digest)
            if backend == "mem0_explicit":
                self.assertEqual(record["system"]["external_backend_identity"]["system_revision"], row["source"]["revision"])
                self.assertEqual(record["native_summary"]["external_system"]["system_id"], "mem0-oss")

    def test_refusals(self) -> None:
        lane = _lane()
        cases = [
            ("2001", {"subset_size": "50", "full_selection": False}, "not a full-selection"),
            ("2002", {"lane_digest_sha256": "f" * 64}, "lane digest"),
            ("2003", {"source_blobs": {**M.lane_reference_blobs(lane), "reference/run_longmemeval.py": "e" * 40}}, "source blobs"),
            ("2004", {"input_sha256": "1" * 64}, "input digest"),
            ("2005", {"backend": "no_memory"}, "no row for backend"),
            ("2006", {"granularity": "paragraph"}, "not a lane plane"),
            ("2007", {"workflow_run_id": "9999"}, "workflow_run_id"),
        ]
        for run_id, overrides, message in cases:
            _write_artifact(self.runs, run_id, "lexical_overlap", "session", identity_overrides=overrides)
            with self.assertRaisesRegex(M.ImportError_, message, msg=run_id):
                self._import(run_id)

        def broken(mutate, message, run_id, backend="lexical_overlap", plane="session"):
            external = _mem0_external(lane) if backend == "mem0_explicit" else None
            report = _report(lane, backend, plane, external=external)
            mutate(report)
            _write_artifact(self.runs, run_id, backend, plane, report=report)
            with self.assertRaisesRegex(M.ImportError_, message, msg=run_id):
                self._import(run_id)

        broken(lambda r: r["input"].__setitem__("corpus_class", "synthetic"), "not external_frozen", "3001")
        broken(lambda r: r["input"]["selection"].__setitem__("question_ids_sha256", "2" * 64), "frozen full selection", "3002")
        broken(lambda r: r["execution"].__setitem__("agent_memory_worktree_dirty", True), "dirty or unknown worktree", "3003")
        broken(lambda r: r["execution"].__setitem__("agent_memory_configuration", {"temporal_metadata": "host_declared", "ranking_variant": "default"}), "frozen comparability posture", "3004")
        broken(lambda r: r["planes"]["session"]["backends"]["lexical_overlap"]["rows"].pop(), "one row per frozen question", "3005")
        broken(lambda r: r["execution"]["external_backends"]["mem0_explicit"]["install_posture"].__setitem__("fastembed_installed", True), "extras posture", "3006", "mem0_explicit", "turn")
        broken(lambda r: r["execution"]["external_backends"]["mem0_explicit"].__setitem__("adapter_revision", "d" * 40), "frozen bridge blob", "3007", "mem0_explicit", "turn")
        broken(lambda r: r["execution"]["external_backends"]["mem0_explicit"].__setitem__("system_revision", "c" * 40), "external system revision", "3008", "mem0_explicit", "turn")
        broken(lambda r: r["execution"].__setitem__("external_backends", {}), "no execution.external_backends identity", "3009", "mem0_explicit", "turn")

        _write_artifact(self.runs, "4001", "mem0_explicit", "session", identity_overrides={"resolved_packages": {"mem0ai": "2.2.1", "qdrant-client": "1.16.0", "sentence-transformers": "5.2.3", "torch": "2.10.0"}})
        with self.assertRaisesRegex(M.ImportError_, "frozen pin qdrant-client==1.17.0"):
            self._import("4001")

    def test_inventory_tamper_is_refused(self) -> None:
        _write_artifact(self.runs, "5001", "lexical_overlap", "turn", tamper_inventory=True)
        with self.assertRaisesRegex(M.ImportError_, "!= inventory"):
            self._import("5001")

    def test_frozen_selection_digest_is_read_from_the_lane(self) -> None:
        lane = _lane()
        self.assertRegex(M.frozen_selection_digest(lane), r"^[0-9a-f]{64}$")
        self.assertTrue(lane["selection"]["selection_id"].endswith(M.frozen_selection_digest(lane)[:16]))
        lane["selection"]["selection_method"] = "all 500 questions"
        with self.assertRaisesRegex(M.ImportError_, "exactly one frozen question_ids_sha256"):
            M.frozen_selection_digest(lane)


if __name__ == "__main__":
    unittest.main()
