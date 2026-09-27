"""#580: the repository-owned temporal/currentness qualification gauntlet.

These tests check the evaluator, not Agent Memory's score:

* the gold corpus is frozen (digest-bound) and covers every #580 item;
* the evaluator fails closed on malformed fixtures;
* the scorer is sensitive: corrupting real observations moves the metric that should
  catch the corruption (scorer-level negative controls);
* evaluation-process runtime mutants are detected (runtime-level negative controls);
* the live runtime still reproduces the frozen pre-#550 baseline exactly. A deliberate
  behavior change (for example #550) must regenerate the baseline and explain the diff;
* no runtime module references the gauntlet (no benchmark-specific branch).
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.evaluation import temporal_currentness as tc  # noqa: E402

FIXTURE = ROOT / "reference" / "fixtures" / "benchmarks" / "temporal-currentness" / "temporal-currentness-gauntlet-v1.json"
FIXTURE_SHA256 = "394be82e8dfabe30ad1faf064f36a88d0b0b8e7ab8157f746ecb4cbae9e64492"
BASELINE = ROOT / "reports" / "benchmarks" / "temporal-currentness" / "baseline-0bace49" / "baseline.json"
RUNNER = ROOT / "reference" / "run_temporal_currentness_gauntlet.py"


def _metric(rows, name, level="required"):
    return tc.compute_metrics(rows)[name][level]


class GauntletTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = tc.load_suite(FIXTURE)
        # Scored exactly as the frozen baseline was (variant-backed invariance included).
        cls.rows = tc.run_suite(cls.suite, diagnostics=False)["rows"]
        # Raw executions, re-scored under deliberate corruption by the sensitivity tests.
        cls.runs = {case["case_id"]: tc.execute_case(case, restart=False) for case in cls.suite["cases"]}

    def rescore(self, mutate) -> list:
        rows = []
        for run in self.runs.values():
            run = copy.deepcopy(run)
            for probe_id, observation in run["probes"].items():
                mutate(run["case"], probe_id, observation)
            rows.extend(tc.score_case(run))
        return rows

    # ------------------------------------------------------------------ corpus

    def test_corpus_is_frozen_and_covers_every_issue_item(self):
        self.assertEqual(tc.suite_digest(FIXTURE), FIXTURE_SHA256)
        self.assertFalse(self.suite["external_validation"])
        self.assertEqual(self.suite["evidence_class"], "repository_owned_conformance")
        covered = {item for case in self.suite["cases"] for item in case["issue_items"]}
        self.assertEqual(covered, set(range(1, 31)))
        for case in self.suite["cases"]:
            self.assertTrue(case["doctrine_refs"], case["case_id"])
        levels = {a["level"] for c in self.suite["cases"] for p in c["probes"] for a in p["assertions"]}
        self.assertEqual(levels, {"required", "target"})

    def test_validation_fails_closed(self):
        broken = copy.deepcopy(self.suite)
        broken["cases"][0]["probes"][0]["assertions"][0]["metrics"] = ["aggregate_memory_score"]
        with self.assertRaises(tc.GauntletError):
            tc.validate_suite(broken)
        broken = copy.deepcopy(self.suite)
        broken["cases"][0]["probes"][0]["assertions"].append({"type": "precedes", "level": "required", "metrics": [], "a": "ghost", "b": "old"})
        with self.assertRaises(tc.GauntletError):
            tc.validate_suite(broken)
        broken = copy.deepcopy(self.suite)
        broken["external_validation"] = True
        with self.assertRaises(tc.GauntletError):
            tc.validate_suite(broken)

    def test_no_aggregate_score_is_reported(self):
        metrics = tc.compute_metrics(self.rows)
        for name in metrics:
            self.assertNotIn("aggregate", name)
            self.assertNotIn("health", name)

    # ------------------------------------------------------------------ scorer sensitivity

    def test_reversed_order_is_detected(self):
        def reverse(case, probe_id, observation):
            observation["admitted"] = list(reversed(observation["admitted"]))
            for rank, key in enumerate(observation["admitted"], start=1):
                observation["per_key"][key]["rank"] = rank
        rows = self.rescore(reverse)
        self.assertLess(_metric(rows, "current_applicability_accuracy")["value"],
                        _metric(self.rows, "current_applicability_accuracy")["value"])
        self.assertGreater(_metric(rows, "stale_as_current_rate")["value"], _metric(self.rows, "stale_as_current_rate")["value"])

    def test_invented_currency_is_detected(self):
        def invent(case, probe_id, observation):
            for obs in observation["per_key"].values():
                if obs["applicability"] == "unknown_temporal_basis":
                    obs["applicability"] = "applicable"
        rows = self.rescore(invent)
        self.assertLess(_metric(rows, "unknown_temporal_basis_honesty_rate")["value"], 1.0)

    def test_corrected_as_false_leak_is_detected(self):
        def leak(case, probe_id, observation):
            for obs in observation["per_key"].values():
                if obs["refusal"] == "corrected_as_false":
                    obs.update(admitted=True, refusal=None, rank=1, currentness="historical_evidence_not_current")
        rows = self.rescore(leak)
        self.assertEqual(_metric(self.rows, "corrected_false_as_historical_rate")["value"], 0.0)
        self.assertEqual(_metric(rows, "corrected_false_as_historical_rate")["value"], 1.0)

    def test_authority_and_mutation_are_detected(self):
        def grant(case, probe_id, observation):
            for obs in observation["per_key"].values():
                obs["authority_effects"] = ["granted"]
            for target in observation["history_current"]:
                observation["history_current"][target] = "mutated"
        rows = self.rescore(grant)
        self.assertGreater(_metric(rows, "authority_or_scope_violation_count")["value"],
                           _metric(self.rows, "authority_or_scope_violation_count")["value"] + 20)

    def test_lost_timeline_and_demoted_current_are_detected(self):
        def degrade(case, probe_id, observation):
            for obs in observation["per_key"].values():
                obs["timeline_position"] = None
                if obs["applicability"] == "applicable":
                    obs["applicability"] = "outside_target_interval"
        rows = self.rescore(degrade)
        self.assertEqual(_metric(rows, "timeline_preservation_rate")["value"], 0.0)
        self.assertGreater(_metric(rows, "current_demoted_as_stale_rate")["value"], 0.5)

    def test_honest_unknown_is_never_counted_as_pass(self):
        target = _metric(self.rows, "self_description_currentness_rate", "target")
        self.assertIsNotNone(target["value"])
        self.assertGreater(target["honest_unknown"], 0)
        self.assertEqual(target["value"], round(target["pass"] / target["units"], 4))

    def test_incidental_target_passes_are_flagged_not_hidden(self):
        incidental = tc.incidental_passes(self.rows)
        self.assertTrue(incidental)
        for item in incidental:
            self.assertLessEqual(set(item["applicability"]), {"unknown_temporal_basis", "not_evaluated", "None"})

    # ------------------------------------------------------------------ runtime mutants

    def _run(self, *args: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            subprocess.run([sys.executable, str(RUNNER), "--output", str(out), "--no-diagnostics", *args],
                           check=True, env={**os.environ, "PYTHONHASHSEED": "0"})
            return json.loads(out.read_text(encoding="utf-8"))

    def test_runtime_mutants_are_detected(self):
        baseline = tc.units(self.rows)
        for mutant in tc.MUTANTS:
            report = self._run("--mutant", mutant)
            mutated = tc.units(report["rows"])
            regressed = [key for key, status in baseline.items() if status == "pass" and mutated.get(key) == "fail"]
            self.assertTrue(regressed, mutant)

    # ------------------------------------------------------------------ frozen baseline

    def test_live_runtime_reproduces_frozen_pre_550_baseline(self):
        frozen = json.loads(BASELINE.read_text(encoding="utf-8"))
        self.assertEqual(frozen["provenance"]["fixture_sha256"], FIXTURE_SHA256)
        self.assertEqual(frozen["provenance"]["runtime_changes_since_boundary"], [])
        self.assertEqual({"/".join(k): v for k, v in tc.units(self.rows).items()},
                         {"/".join(k): v for k, v in tc.units(frozen["rows"]).items()})
        self.assertEqual(tc.order_digests(self.rows), frozen["order_digests"])

    def test_restart_reproduces_every_probe(self):
        self.assertEqual(tc.compute_metrics(self.rows)["restart_reproduction_rate"]["value"], 1.0)

    # ------------------------------------------------------------------ no benchmark branch

    def test_no_runtime_module_references_the_gauntlet(self):
        tokens = {"temporal-gauntlet", "evaluation.temporal_currentness", "temporal-currentness-gauntlet", "mallory street", "gauntlet-v1"}
        for directory in ("runtime", "memory", "core", "api"):
            for path in (ROOT / "reference" / "agentmem_ref" / directory).glob("*.py"):
                source = path.read_text(encoding="utf-8").lower()
                for token in tokens:
                    self.assertNotIn(token, source, (path.name, token))


if __name__ == "__main__":
    unittest.main()
