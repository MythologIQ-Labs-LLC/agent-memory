"""Synthetic falsifiers for the strict v7 AMB successor parity verifier.

No external AMB score is produced. The real accepted v6 control is only read
by the production CLI; synthetic copies here exercise the refusal conditions.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
CHECKER = ROOT / "scripts/check_amb_scope_distinct_v7_parity.py"
LANE = ROOT / ("reports/validation/v7-integration/amb-scope-distinct-successor/"
               "amb-precisionmembench-retrieval-v7-scope-distinct-v1.json")
CASE_FIELDS = ("correct", "context")
META_FIELDS = (
    "relevant_beliefs", "pinned_beliefs", "retrieved_questions",
    "retrieval_precision", "retrieval_recall", "pinned_coverage",
    "resolution", "failures", "retrieved_count",
)


def load_checker():
    spec = importlib.util.spec_from_file_location("amb_scope_distinct_parity_test", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class ScopeDistinctParitySensitivityTests(unittest.TestCase):
    def setUp(self):
        self.module = load_checker()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        self.baseline = self.root / "v6"
        self.candidate = self.root / "candidate"
        self.baseline.mkdir(parents=True)
        self.candidate.mkdir()
        self.lane = json.loads(LANE.read_text(encoding="utf-8"))
        write_json(self.root / LANE.relative_to(ROOT), self.lane)

        self.cases = []
        self.sidecar = []
        for i in range(77):
            query = f"Query {i}" if i < 73 else ""
            meta = {
                "relevant_beliefs": [f"belief:{i}"] if query else [],
                "pinned_beliefs": [],
                "retrieved_questions": [],
                "retrieval_precision": 1.0 if query else None,
                "retrieval_recall": 1.0 if query else None,
                "pinned_coverage": None,
                "resolution": {} if not query else {"id": f"belief:{i}"},
                "failures": [],
                "retrieved_count": 1 if query else 0,
            }
            self.cases.append({
                "query_id": f"question:{i}", "query": query, "correct": bool(query),
                "context": f"belief:{i}" if query else "", "meta": meta,
            })
            if query:
                self.sidecar.append({
                    "call_index": i,
                    "scope": "amb:scope:abc123",
                    "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
                    "budget": 20,
                    "limited_count": 0,
                    "limited_document_ids": [],
                    "refusal_counts": {},
                    "returned_document_ids": [f"belief:{i}"],
                    "returned_document_ids_mechanism_off": None,
                })
        self.old_summary = {"memory_provider": "agent-memory", "mode": "retrieval",
                            "total_queries": 77, "results": copy.deepcopy(self.cases)}
        self.new_summary = copy.deepcopy(self.old_summary)
        self.old_identity = {"lane_id": self.module.OLD_LANE_ID,
                             "amb_revision": self.module.HARNESS_SHA}
        self.new_identity = {
            "lane_id": self.module.NEW_LANE_ID, "amb_revision": self.module.HARNESS_SHA,
            "memory": "agent-memory", "mode": "retrieval",
            "dataset": "precisionmembench", "split": "single-turn",
            "full_selection": True, "query_limit": "0", "amb_pmb_return_cap": None,
            "answer_model": None, "judge_model": None,
            "runtime_baseline_state": "TRANSITION", "workflow_run_id": "12345",
            "agent_memory_revision": "a" * 40,
            "lane_digest_sha256": self.module._lane_digest(self.lane),
            "bridge_blobs": {
                source: sha for source, sha in self.lane["harness"]["source_blobs"].items()
                if source.startswith("reference/")
            },
            "declaration_blob": next(
                row for row in self.lane["systems"] if row["role"] == "control"
            )["configuration"]["runtime_baseline_posture"]["declaration_blob"],
        }
        self.write_files()

    def write_files(self):
        write_json(self.baseline / "single-turn.json", self.old_summary)
        write_json(self.candidate / "single-turn.json", self.new_summary)
        write_json(self.baseline / "execution-identity.json", self.old_identity)
        write_json(self.candidate / "execution-identity.json", self.new_identity)
        sidecar = self._sidecar_content(self.sidecar)
        (self.baseline / "cross-fact.jsonl").write_text(sidecar, encoding="utf-8")
        (self.candidate / "cross-fact.jsonl").write_text(sidecar, encoding="utf-8")
        files = {
            name: hashlib.sha256((self.baseline / name).read_bytes()).hexdigest()
            for name in ("single-turn.json", "cross-fact.jsonl", "execution-identity.json")
        }
        write_json(self.baseline / "evidence.json",
                   {"lane_id": self.module.OLD_LANE_ID, "authority_effect": "none",
                    "files": files,
                    "cross_fact_sidecar": {"sha256": files["cross-fact.jsonl"]}})

    @staticmethod
    def _sidecar_content(rows):
        return "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)

    def check(self):
        # The separate tests check source pins and their real file bytes. This
        # synthetic fixture has no copy of the whole source checkout.
        blobs = self.lane["harness"]["source_blobs"]
        with mock.patch.object(
            self.module, "_raw_git_blob",
            side_effect=lambda path: (
                self.module.ACCEPTED_V6_EVIDENCE_BLOB
                if path.name == "evidence.json" else blobs["reference/" + path.name]
            ),
        ):
            return self.module.verify(self.baseline, self.candidate, root=self.root)

    def test_tampered_accepted_v6_summary_refuses_even_when_candidate_colludes(self):
        # A forged baseline can no longer be made "equal" to a forged candidate.
        self.old_summary["results"][42]["context"] += " forged"
        self.new_summary["results"][42]["context"] += " forged"
        self.write_files()
        with mock.patch.object(self.module, "_raw_git_blob", side_effect=lambda path: (
            "0" * 40 if path.name == "evidence.json"
            else self.lane["harness"]["source_blobs"]["reference/" + path.name]
        )):
            with self.assertRaisesRegex(self.module.ParityBlocked, "evidence blob differs"):
                self.module.verify(self.baseline, self.candidate, root=self.root)

    def test_accepted_v6_summary_digest_refuses(self):
        self.write_files()
        with (self.baseline / "single-turn.json").open("ab") as stream:
            stream.write(b" ")
        with self.assertRaisesRegex(self.module.ParityBlocked, "single-turn.json differs"):
            self.check()

    def test_accepted_v6_identity_digest_refuses(self):
        self.write_files()
        with (self.baseline / "execution-identity.json").open("ab") as stream:
            stream.write(b" ")
        with self.assertRaisesRegex(self.module.ParityBlocked, "execution-identity.json differs"):
            self.check()

    def test_accepted_v6_evidence_pin_is_mandatory(self):
        self.write_files()
        blobs = self.lane["harness"]["source_blobs"]
        with mock.patch.object(self.module, "_raw_git_blob", side_effect=lambda path: (
            "0" * 40 if path.name == "evidence.json" else blobs["reference/" + path.name]
        )):
            with self.assertRaisesRegex(self.module.ParityBlocked, "evidence blob differs"):
                self.module.verify(self.baseline, self.candidate, root=self.root)

    def test_all_77_cases_and_73_sidecar_records_must_match(self):
        report = self.check()
        self.assertEqual(report["verdict"], "EQUAL")
        self.assertEqual((report["cases_equal"], report["cross_fact_records_equal"]), (77, 73))
        self.assertEqual(report["acceptance"], "not_granted")

    def test_one_case_field_change_blocks(self):
        self.new_summary["results"][42]["context"] += " forged"
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "case.context"):
            self.check()

    def test_one_meta_field_change_blocks(self):
        self.new_summary["results"][21]["meta"]["retrieval_recall"] = 0.5
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "meta.retrieval_recall"):
            self.check()

    def test_cross_fact_limited_count_change_blocks_even_if_cases_equal(self):
        changed = copy.deepcopy(self.sidecar)
        changed[12]["limited_count"] = 1
        changed[12]["limited_document_ids"] = ["belief:12"]
        changed[12]["returned_document_ids_mechanism_off"] = ["belief:12"]
        self.write_files()
        (self.candidate / "cross-fact.jsonl").write_text(
            self._sidecar_content(changed), encoding="utf-8"
        )
        with self.assertRaisesRegex(self.module.ParityBlocked, "sidecar differs"):
            self.check()

    def test_refusal_count_change_blocks_even_if_cases_equal(self):
        changed = copy.deepcopy(self.sidecar)
        changed[12]["refusal_counts"] = {"unreadable": 1}
        self.write_files()
        (self.candidate / "cross-fact.jsonl").write_text(
            self._sidecar_content(changed), encoding="utf-8"
        )
        with self.assertRaisesRegex(self.module.ParityBlocked, "sidecar differs"):
            self.check()

    def test_shuffled_query_ids_block(self):
        self.new_summary["results"][0], self.new_summary["results"][1] = (
            self.new_summary["results"][1], self.new_summary["results"][0]
        )
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "order/selection"):
            self.check()

    def test_wrong_lane_identity_blocks(self):
        self.new_identity["lane_id"] = self.module.OLD_LANE_ID
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "lane mismatch"):
            self.check()

    def test_changed_bridge_source_pin_blocks(self):
        self.new_identity["bridge_blobs"]["reference/amb_agent_memory_bridge_scope_distinct.py"] = "0" * 40
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "bridge or runner identity"):
            self.check()

    def test_old_baseline_sidecar_digest_tamper_blocks(self):
        self.write_files()
        (self.baseline / "cross-fact.jsonl").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(self.module.ParityBlocked, "no longer matches"):
            self.check()

    def test_missing_query_refuses_partial_selection(self):
        self.new_summary["results"].pop()
        self.new_summary["total_queries"] = 76
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "exactly 77"):
            self.check()

    def test_no_hosted_baseline_state_refuses(self):
        self.new_identity["runtime_baseline_state"] = "NO-GO"
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "baseline checker"):
            self.check()


if __name__ == "__main__":
    unittest.main()
