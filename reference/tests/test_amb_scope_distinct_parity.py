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
                "gold_answers": [f"belief:{i}"], "retrieve_time_ms": 10.0 + i,
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
                            "total_queries": 77, "ingested_docs": 35, "run_name": "agent-memory-24048d55e26d",
                            "avg_retrieve_time_ms": 28.1, "results": copy.deepcopy(self.cases)}
        # A real re-execution differs from v6 only in wall-clock timing and the run name.
        self.new_summary = copy.deepcopy(self.old_summary)
        self.new_summary.update(run_name="agent-memory-aaaaaaaaaaaa", avg_retrieve_time_ms=31.4)
        for case in self.new_summary["results"]:
            case["retrieve_time_ms"] += 3.5
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
        self.write_candidate_evidence()

    def write_candidate_evidence(self):
        files = {
            name: hashlib.sha256((self.candidate / name).read_bytes()).hexdigest()
            for name in ("single-turn.json", "cross-fact.jsonl", "execution-identity.json")
        }
        write_json(self.candidate / "evidence.json", {
            "lane_id": self.module.NEW_LANE_ID,
            "authority_effect": "none",
            "row": {"row_id": "agent-memory-public-facade", "provider_key": "agent-memory"},
            "lane_digest_at_execution": self.module._lane_digest(self.lane),
            "files": files,
            "cross_fact_sidecar": {
                "sha256": files["cross-fact.jsonl"],
                "records": 73,
                "limited_total": 0,
                "no_recall_executed_cases": 4,
            },
            "workflow_run": {"id": "12345"},
            "execution": {"lane_id": self.module.NEW_LANE_ID},
        })

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
        ), mock.patch.object(self.module, "_runtime_tree", side_effect=self.runtime_tree):
            return self.module.verify(self.baseline, self.candidate, root=self.root)

    def runtime_tree(self, root, revision):
        return self.module.RUNTIME_TREE if revision == "a" * 40 else "f" * 40

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
        self.write_candidate_evidence()
        with self.assertRaisesRegex(self.module.ParityBlocked, "sidecar differs"):
            self.check()

    def test_refusal_count_change_blocks_even_if_cases_equal(self):
        changed = copy.deepcopy(self.sidecar)
        changed[12]["refusal_counts"] = {"unreadable": 1}
        self.write_files()
        (self.candidate / "cross-fact.jsonl").write_text(
            self._sidecar_content(changed), encoding="utf-8"
        )
        self.write_candidate_evidence()
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
        with self.assertRaisesRegex(self.module.ParityBlocked, "cross-fact.jsonl differs"):
            self.check()

    def test_missing_query_refuses_partial_selection(self):
        self.new_summary["results"].pop()
        self.new_summary["total_queries"] = 76
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "exactly 77"):
            self.check()

    def test_missing_candidate_imported_evidence_refuses(self):
        (self.candidate / "evidence.json").unlink()
        with self.assertRaisesRegex(self.module.ParityBlocked, "required JSON unavailable"):
            self.check()

    def test_candidate_summary_tamper_after_import_refuses(self):
        (self.candidate / "single-turn.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(self.module.ParityBlocked, "candidate single-turn.json differs"):
            self.check()

    def test_candidate_sidecar_tamper_after_import_refuses(self):
        (self.candidate / "cross-fact.jsonl").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(self.module.ParityBlocked, "candidate cross-fact.jsonl differs"):
            self.check()

    def test_candidate_control_evidence_relabel_refuses(self):
        p = self.candidate / "evidence.json"
        manifest = json.loads(p.read_text(encoding="utf-8"))
        manifest["row"]["row_id"] = "bm25-harness-baseline"
        write_json(p, manifest)
        with self.assertRaisesRegex(self.module.ParityBlocked, "no imported Agent Memory control evidence"):
            self.check()

    def test_candidate_imported_execution_must_match_workflow_run(self):
        p = self.candidate / "evidence.json"
        manifest = json.loads(p.read_text(encoding="utf-8"))
        manifest["workflow_run"]["id"] = "54321"
        write_json(p, manifest)
        with self.assertRaisesRegex(self.module.ParityBlocked, "importer and run identity disagree"):
            self.check()

    def test_candidate_imported_lane_digest_must_match_freeze(self):
        p = self.candidate / "evidence.json"
        manifest = json.loads(p.read_text(encoding="utf-8"))
        manifest["lane_digest_at_execution"] = "0" * 64
        write_json(p, manifest)
        with self.assertRaisesRegex(self.module.ParityBlocked, "different frozen lane digest"):
            self.check()

    def test_malformed_importer_row_and_workflow_refuse(self):
        p = self.candidate / "evidence.json"
        for corruption in ({"row": None}, {"workflow_run": None}):
            manifest = json.loads(p.read_text(encoding="utf-8"))
            manifest.update(corruption)
            write_json(p, manifest)
            with self.subTest(corruption=corruption), self.assertRaises(self.module.ParityBlocked):
                self.check()
            self.write_candidate_evidence()

    def test_candidate_manifest_recomputed_but_different_sidecar_refuses(self):
        changed = copy.deepcopy(self.sidecar)
        changed[12]["returned_document_ids"] = ["other-user-document"]
        (self.candidate / "cross-fact.jsonl").write_text(
            self._sidecar_content(changed), encoding="utf-8"
        )
        self.write_candidate_evidence()
        with self.assertRaisesRegex(self.module.ParityBlocked, "sidecar differs"):
            self.check()

    def test_no_hosted_baseline_state_refuses(self):
        self.new_identity["runtime_baseline_state"] = "NO-GO"
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "baseline checker"):
            self.check()

    # Review findings on the successor gate: relabelled v6 bytes, type-loose equality, fields outside
    # the preregistered list, self-referential lane and runtime anchors, and unguarded identity checks.

    def test_relabelled_v6_summary_bytes_refuse(self):
        self.new_summary = copy.deepcopy(self.old_summary)
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "byte-identical to the accepted v6"):
            self.check()

    def test_reserialised_v6_summary_with_v6_timings_refuses(self):
        self.new_summary = copy.deepcopy(self.old_summary)
        self.new_summary["run_name"] = "agent-memory-aaaaaaaaaaaa"
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "timings are identical"):
            self.check()

    def test_type_change_with_equal_python_value_blocks(self):
        self.new_summary["results"][3]["correct"] = 1
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "case.correct"):
            self.check()

    def test_field_outside_the_preregistered_list_blocks(self):
        self.new_summary["results"][5]["gold_answers"] = ["forged"]
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "case.gold_answers"):
            self.check()

    def test_meta_field_outside_the_preregistered_list_blocks(self):
        self.new_summary["results"][5]["meta"]["retrieval_limit"] = 99
        self.old_summary["results"][5]["meta"]["retrieval_limit"] = 20
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "meta.retrieval_limit"):
            self.check()

    def test_summary_field_change_blocks(self):
        self.new_summary["ingested_docs"] = 34
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "summary.ingested_docs"):
            self.check()

    def test_added_case_field_blocks(self):
        self.new_summary["results"][7]["extra"] = True
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "case field set changed"):
            self.check()

    def test_lane_under_repo_root_must_match_the_constant_digest(self):
        # The candidate colludes: identity and imported evidence carry the rewritten lane's digest.
        lane = copy.deepcopy(self.lane)
        lane["notes"] = "rewritten pins"
        write_json(self.root / LANE.relative_to(ROOT), lane)
        self.new_identity["lane_digest_sha256"] = self.module._lane_digest(lane)
        self.write_files()
        p = self.candidate / "evidence.json"
        manifest = json.loads(p.read_text(encoding="utf-8"))
        manifest["lane_digest_at_execution"] = self.module._lane_digest(lane)
        write_json(p, manifest)
        with self.assertRaisesRegex(self.module.ParityBlocked, "differs from the frozen lane digest"):
            self.check()

    def test_constant_lane_digest_is_the_committed_lane(self):
        self.assertEqual(self.module._lane_digest(self.lane), self.module.SUCCESSOR_LANE_DIGEST)

    def test_executed_revision_must_carry_the_frozen_runtime_tree(self):
        self.new_identity["agent_memory_revision"] = "b" * 40
        self.write_files()
        with self.assertRaisesRegex(self.module.ParityBlocked, "protected runtime tree"):
            self.check()

    def test_runtime_tree_lookup_reads_the_real_repository(self):
        head = self.module.subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                          text=True, check=True).stdout.strip()
        tree = self.module.subprocess.run(["git", "rev-parse", "HEAD:reference/agentmem_ref"], cwd=ROOT,
                                          capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(self.module._runtime_tree(ROOT, head), tree)
        self.assertIsNone(self.module._runtime_tree(ROOT, "0" * 40))

    def test_identity_fields_each_block(self):
        cases = {
            "memory": ("bm25", "full PrecisionMemBench retrieval control"),
            "mode": ("answer", "full PrecisionMemBench retrieval control"),
            "split": ("multi-turn", "full PrecisionMemBench retrieval control"),
            "amb_revision": ("0" * 40, "external AMB revision changed"),
            "amb_pmb_return_cap": ("10", "all 77 queries with no return cap"),
            "query_limit": ("20", "all 77 queries with no return cap"),
            "declaration_blob": ("0" * 40, "declaration identity mismatch"),
            "lane_digest_sha256": ("0" * 64, "successor lane digest mismatch"),
            "answer_model": ("gemini:x", "unexpectedly used a model"),
        }
        original = copy.deepcopy(self.new_identity)
        for field, (value, message) in cases.items():
            with self.subTest(field=field):
                self.new_identity = copy.deepcopy(original)
                self.new_identity[field] = value
                self.write_files()
                with self.assertRaisesRegex(self.module.ParityBlocked, message):
                    self.check()

    def test_query_text_change_blocks(self):
        self.new_summary["results"][9]["query"] = "Query 9 altered"
        self.write_files()
        with self.assertRaises(self.module.ParityBlocked):
            self.check()

    def test_truncated_candidate_sidecar_blocks(self):
        self.write_files()
        (self.candidate / "cross-fact.jsonl").write_text(self._sidecar_content(self.sidecar[:72]), encoding="utf-8")
        self.write_candidate_evidence()
        with self.assertRaisesRegex(self.module.ParityBlocked, "73 ordered sidecar records"):
            self.check()

    def test_candidate_sidecar_summary_must_be_consistent(self):
        p = self.candidate / "evidence.json"
        manifest = json.loads(p.read_text(encoding="utf-8"))
        manifest["cross_fact_sidecar"]["limited_total"] = 1
        write_json(p, manifest)
        with self.assertRaisesRegex(self.module.ParityBlocked, "cross-fact evidence summary"):
            self.check()

    def test_candidate_source_blob_drift_blocks(self):
        with mock.patch.object(self.module, "_raw_git_blob", side_effect=lambda path: (
            self.module.ACCEPTED_V6_EVIDENCE_BLOB if path.name == "evidence.json" else "0" * 40
        )), mock.patch.object(self.module, "_runtime_tree", side_effect=self.runtime_tree):
            with self.assertRaisesRegex(self.module.ParityBlocked, "candidate source blob drift"):
                self.module.verify(self.baseline, self.candidate, root=self.root)


if __name__ == "__main__":
    unittest.main()
