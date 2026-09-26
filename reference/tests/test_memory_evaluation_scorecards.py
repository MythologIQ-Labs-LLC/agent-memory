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
        self.assertIn("| longmemeval_m_cleaned | not_run |", markdown)
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
