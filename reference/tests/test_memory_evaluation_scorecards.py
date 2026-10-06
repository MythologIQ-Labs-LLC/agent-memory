from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.evaluation import validate_run  # noqa: E402
from agentmem_ref.evaluation.contract import ComparisonCompatibilityError  # noqa: E402
from agentmem_ref.evaluation.normalize import normalize_agentmembench, normalize_longmemeval  # noqa: E402
from agentmem_ref.evaluation.registry import list_profiles  # noqa: E402
from agentmem_ref.evaluation.scorecard import benchmark_scorecards, build, render_markdown  # noqa: E402

LME = ROOT / "reports" / "benchmarks" / "longmemeval" / "longmemeval-s-full-f73b872.json"
AMB = ROOT / "reports" / "benchmarks" / "agentmembench"


def _lme():
    return normalize_longmemeval(json.loads(LME.read_text(encoding="utf-8")))


def _amb():
    manifests = []
    for backend in ("no_memory", "lexical_overlap", "agent_memory"):
        manifests += normalize_agentmembench(json.loads((AMB / f"memdialogue-v2-{backend}-03197cd.json").read_text(encoding="utf-8")))
    return manifests


class NormalizationTests(unittest.TestCase):
    def test_longmemeval_preserves_native_results_and_frozen_identity(self):
        manifests = _lme()
        self.assertEqual(len(manifests), 6)
        report = json.loads(LME.read_text(encoding="utf-8"))
        agent = next(m for m in manifests if m["run_id"].startswith("longmemeval:session:agent_memory"))
        self.assertEqual(agent["benchmark"]["input_sha256"], report["input"]["sha256"])
        self.assertEqual(agent["system"]["revision"], "f73b872c7f062d0b1e80b4812650b854e3bd2ac8")
        self.assertEqual(agent["native_results"]["aggregate"], report["planes"]["session"]["backends"]["agent_memory"]["aggregate"])
        recall = {m["metric_id"]: m for m in agent["dimensions"]["retrieval"]["metrics"]}
        self.assertAlmostEqual(recall["recall_all@5"]["value"], 0.675418)
        self.assertEqual(recall["recall_all@5"]["denominator"], 419)
        currentness = {m["metric_id"]: m["value"] for m in agent["dimensions"]["currentness"]["metrics"]}
        self.assertAlmostEqual(currentness["latest_gold_ranked_first"], 0.342857)
        self.assertEqual(agent["authority_effect"], "none")

    def test_unmeasured_dimensions_are_never_zero(self):
        for manifest in _lme() + _amb():
            validate_run(manifest)
            self.assertEqual(manifest["dimensions"]["reasoning"]["status"], "not_measured")
            self.assertEqual(manifest["dimensions"]["reasoning"]["metrics"], [])
            self.assertEqual(manifest["dimensions"]["evaluator_integrity"]["status"], "not_measured")
            for dimension in manifest["dimensions"].values():
                for metric in dimension["metrics"]:
                    if metric["state"] != "measured":
                        self.assertNotIn("value", metric)
        lme_baseline = next(m for m in _lme() if m["system"]["id"] == "lexical_overlap")
        self.assertEqual(lme_baseline["dimensions"]["governance"]["status"], "not_applicable")
        rss = next(m for m in lme_baseline["dimensions"]["efficiency"]["metrics"] if m["metric_id"] == "peak_rss_mb")
        self.assertEqual(rss["state"], "not_measured")
        no_memory = next(m for m in _amb() if m["system"]["id"] == "no_memory")
        deletion = next(m for m in no_memory["dimensions"]["governance"]["metrics"] if m["metric_id"] == "audited_deletion_rate")
        self.assertEqual(deletion["state"], "not_applicable")


class AmbLaneNormalizationTests(unittest.TestCase):
    LANE = ROOT / "reports" / "benchmarks" / "amb" / "amb-precisionmembench-retrieval-v1"
    RECORDS = ("agent-memory-703be5ba1c7e", "bm25-703be5ba1c7e", "mem0-explicit-b38d91631169")

    def _manifests(self):
        from agentmem_ref.evaluation.normalize import normalize_amb_precisionmembench

        manifests = []
        for name in self.RECORDS:
            manifests += normalize_amb_precisionmembench(json.loads((self.LANE / name / "evidence.json").read_text(encoding="utf-8")))
        return manifests

    def test_lane_rows_map_only_the_harness_summary_and_keep_the_record_whole(self):
        manifests = self._manifests()
        self.assertEqual([m["system"]["id"] for m in manifests], ["agent-memory", "bm25", "mem0-oss"])
        self.assertEqual([m["system"]["kind"] for m in manifests], ["agent_memory", "lexical", "external_memory"])
        for manifest, name in zip(manifests, self.RECORDS):
            record = json.loads((self.LANE / name / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["native_results"], record)
            self.assertEqual(manifest["benchmark"]["input_sha256"], record["input"]["sha256"])
            self.assertEqual(manifest["benchmark"]["source_revision"], record["execution"]["amb_revision"])
            self.assertEqual(manifest["system"]["revision"], record["system"]["revision"])
            self.assertEqual(manifest["execution"]["sample_count"], 77)
            retrieval = {m["metric_id"]: m for m in manifest["dimensions"]["retrieval"]["metrics"]}
            self.assertEqual(retrieval["active_passes"]["value"], record["native_summary"]["active_passes"])
            self.assertEqual(retrieval["active_passes"]["denominator"], 43)
            self.assertEqual(retrieval["total_passes"]["denominator"], 77)
            self.assertEqual(manifest["dimensions"]["currentness"]["status"], "not_applicable")
            self.assertEqual(manifest["dimensions"]["reasoning"]["status"], "not_applicable")
            self.assertEqual(manifest["dimensions"]["governance"]["status"], "not_measured")
            self.assertEqual(manifest["dimensions"]["evaluator_integrity"]["status"], "not_measured")
            reproducibility = {m["metric_id"]: m["value"] for m in manifest["dimensions"]["reproducibility"]["metrics"]}
            self.assertEqual(reproducibility, {"input_sha256_bound": True, "full_selection": True, "return_cap_unset": True, "harness_lock_bound": True, "self_check_recorded": True})
            summary = next(a for a in manifest["artifacts"] if a["artifact_id"] == "amb-eval-summary")
            self.assertEqual(summary["sha256"], record["files"]["single-turn.json"])
            self.assertTrue((ROOT / summary["uri"]).is_file(), summary["uri"])
            self.assertEqual(manifest["authority_effect"], "none")
        active = {m["system"]["id"]: next(x for x in m["dimensions"]["retrieval"]["metrics"] if x["metric_id"] == "active_passes")["value"] for m in manifests}
        self.assertEqual(active, {"agent-memory": 4, "bm25": 0, "mem0-oss": 0})

    def test_lane_rows_share_one_card_with_bm25_as_the_lexical_baseline(self):
        cards = benchmark_scorecards(self._manifests())
        self.assertEqual(len(cards), 1)
        card = cards[0]
        self.assertEqual(card["baseline_system"], "bm25")
        self.assertEqual([s["id"] for s in card["systems"]], ["bm25", "agent-memory", "mem0-oss"])
        row = next(r for r in card["dimensions"]["retrieval"]["rows"] if r["metric_id"] == "active_passes")
        self.assertEqual(row["vs_baseline"]["agent-memory"], {"comparison_state": "comparable", "delta_vs_baseline": 4.0, "outcome": "improved"})
        self.assertEqual(row["vs_baseline"]["mem0-oss"]["delta_vs_baseline"], 0.0)
        self.assertNotIn("score", card)
        self.assertNotIn("aggregate", card)

    def test_normalizer_refuses_a_record_that_is_not_lane_evidence(self):
        from agentmem_ref.evaluation.normalize import normalize_amb_precisionmembench

        with self.assertRaises(ValueError):
            normalize_amb_precisionmembench({"native_summary": {}})


class ScorecardTests(unittest.TestCase):
    def test_cards_group_only_comparable_runs_and_have_no_aggregate(self):
        document = build(list_profiles(), _lme() + _amb())
        self.assertEqual(document["aggregate_score"], "not_defined")
        profiles = sorted(card["comparison_identity"]["task_profile"] for card in document["benchmark_scorecards"])
        self.assertEqual(
            profiles,
            [
                "agent-memory-agentmembench-memdialogue-operational-v1",
                "agent-memory-longmemeval-retrieval-currentness-v1:session",
                "agent-memory-longmemeval-retrieval-currentness-v1:turn",
            ],
        )
        session = next(card for card in document["benchmark_scorecards"] if card["comparison_identity"]["task_profile"].endswith(":session"))
        self.assertEqual([system["id"] for system in session["systems"]], ["no_memory", "lexical_overlap", "agent_memory"])
        row = next(row for row in session["dimensions"]["retrieval"]["rows"] if row["metric_id"] == "recall_all@5")
        self.assertAlmostEqual(row["vs_baseline"]["agent_memory"]["delta_vs_baseline"], -0.054892)
        self.assertEqual(row["vs_baseline"]["agent_memory"]["outcome"], "regressed")

    def test_incompatible_inputs_never_share_a_card(self):
        manifests = _lme()
        altered = copy.deepcopy(next(m for m in manifests if m["run_id"].startswith("longmemeval:session:agent_memory")))
        altered["benchmark"]["input_sha256"] = "0" * 64
        altered["run_id"] += ":altered"
        cards = benchmark_scorecards(manifests + [altered])
        self.assertEqual(len(cards), 3)
        lonely = next(card for card in cards if card["comparison_identity"]["input_sha256"] == "0" * 64)
        self.assertIsNone(lonely["baseline_system"])
        duplicate = copy.deepcopy(manifests[0])
        duplicate["run_id"] += ":duplicate"
        with self.assertRaises(ComparisonCompatibilityError):
            benchmark_scorecards(manifests + [duplicate])

    def test_portfolio_keeps_blocked_and_not_run_visible(self):
        document = build(list_profiles(), _lme() + _amb())
        portfolio = {row["profile_id"]: row for row in document["portfolio"]}
        swe = portfolio["swe-context-bench-lite-external-retrieval-v1"]
        self.assertEqual(swe["systems_run"], [])
        self.assertEqual([item["status"] for item in swe["evidence"]], ["blocked"])
        self.assertEqual(swe["dimensions_measured"], [])
        markdown = render_markdown(document)
        self.assertIn("| upstream_model_judged_qa | not_run |", markdown)
        self.assertIn("| lite_protocol_comparable_99_query_100_edge | blocked |", markdown)
        self.assertNotIn("overall_score", markdown)
        self.assertNotIn("health score:", markdown.lower())

    def test_committed_scorecards_are_current_and_deterministic(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_benchmark_scorecards.py"), "--check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()


class LongMemEvalExternalBackendNormalizationTests(unittest.TestCase):
    """An externally registered backend (#640 lane v2) binds its own identity, never the repository's."""

    IDENTITY = {
        "backend": "ext_system",
        "system_id": "mem0-oss",
        "system_kind": "external_memory",
        "system_revision": "94c3fe9f238f3dbf29c9ce98643bd71eb13077cd",
        "adapter_id": "reference/longmemeval_mem0_explicit_bridge.py",
        "adapter_revision": "e" * 40,
        "configuration": {"inference": "none", "search": {"top_k": 50}},
        "authority_effect": "none",
    }

    def _report(self):
        report = json.loads(LME.read_text(encoding="utf-8"))
        for plane in report["planes"].values():
            external = copy.deepcopy(plane["backends"]["lexical_overlap"])
            external["external_system"] = {"system_id": "mem0-oss", "system_revision": self.IDENTITY["system_revision"], "unmapped_result_count_total": 3}
            external["timing"].update({"ingest_seconds_total": 12.5, "recall_seconds_total": 1.25, "recall_seconds_max": 0.2})
            plane["backends"]["ext_system"] = external
        report["execution"]["backends"] = list(report["execution"]["backends"]) + ["ext_system"]
        report["execution"]["external_backends"] = {"ext_system": copy.deepcopy(self.IDENTITY)}
        return report

    def test_external_backend_manifest_binds_the_recorded_identity(self):
        report = self._report()
        manifests = normalize_longmemeval(report)
        self.assertEqual(len(manifests), 8)
        external = next(m for m in manifests if m["run_id"] == "longmemeval:session:ext_system:94c3fe9f238f")
        validate_run(external)
        self.assertEqual(external["system"]["id"], "mem0-oss")
        self.assertEqual(external["system"]["kind"], "external_memory")
        self.assertEqual(external["system"]["revision"], self.IDENTITY["system_revision"])
        self.assertEqual(external["system"]["adapter_id"], self.IDENTITY["adapter_id"])
        self.assertEqual(external["system"]["adapter_revision"], "e" * 40)
        self.assertRegex(external["system"]["configuration_digest"], r"^[a-f0-9]{64}$")
        self.assertEqual(external["dimensions"]["governance"]["status"], "not_applicable")
        efficiency = {m["metric_id"]: m for m in external["dimensions"]["efficiency"]["metrics"]}
        self.assertEqual(efficiency["ingest_seconds_total"]["value"], 12.5)
        self.assertEqual(external["native_results"]["external_system"]["unmapped_result_count_total"], 3)
        self.assertEqual(external["native_results"]["external_backend_identity"], self.IDENTITY)
        self.assertTrue(any("externally registered" in item for item in external["limitations"]))
        lexical = next(m for m in manifests if m["run_id"].startswith("longmemeval:session:lexical_overlap"))
        self.assertEqual(lexical["system"]["revision"], report["execution"]["agent_memory_revision"])
        self.assertNotIn("ingest_seconds_total", {m["metric_id"] for m in lexical["dimensions"]["efficiency"]["metrics"]})
        # Same plane, same frozen input and selection: the external row lands on the same card.
        cards = benchmark_scorecards([lexical, external])
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["baseline_system"], "lexical_overlap")
        self.assertIn("mem0-oss", cards[0]["dimensions"]["retrieval"]["rows"][0]["vs_baseline"])

    def test_backend_without_any_identity_is_refused(self):
        report = self._report()
        del report["execution"]["external_backends"]["ext_system"]
        with self.assertRaisesRegex(ValueError, "neither built in nor recorded"):
            normalize_longmemeval(report)
