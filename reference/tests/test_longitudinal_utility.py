from __future__ import annotations

import json
import unittest

from agentmem_ref.evaluation import longitudinal_utility as lu


def _result(returned, admissions):
    return {"returned": list(returned), "admissions": admissions}


def _admission(label="not_evaluated", currentness="current_state", refusal=None):
    record = {"ranking_evidence": {"temporal_applicability": label}, "admission_basis": {"currentness": currentness}}
    if refusal:
        record["refusal"] = refusal
    return record


class Scoring(unittest.TestCase):
    LEDGER = {"w1": "f-old", "w2": "f-new", "w3": "f-dep", "w4": "f-other"}

    def _score(self, probe, result):
        return lu.score_probe({"id": "p", "session": 2, "_write_session": {"w1": 1, "w2": 1}, **probe}, result, self.LEDGER)

    def test_unlabelled_stale_is_stale_use_even_when_ranked_below_current(self):
        result = _result(["f-new", "f-old"], {"f-new": _admission(), "f-old": _admission()})
        self.assertEqual(self._score({"current": ["w2"], "stale": ["w1"]}, result)["classes"], ["stale_used"])

    def test_labelled_stale_below_current_is_preserved_history_not_stale_use(self):
        result = _result(["f-new", "f-old"], {"f-new": _admission(),
                                              "f-old": _admission("limited_by_cross_fact_state_change")})
        outcome = self._score({"current": ["w2"], "stale": ["w1"]}, result)
        self.assertTrue(outcome["success"])
        self.assertEqual(outcome["cross_session_recalled"], 1)

    def test_labelled_stale_above_current_is_still_stale_use(self):
        result = _result(["f-old", "f-new"], {"f-new": _admission(),
                                              "f-old": _admission("limited_by_cross_fact_state_change")})
        self.assertIn("stale_used", self._score({"current": ["w2"], "stale": ["w1"]}, result)["classes"])

    def test_current_labelled_non_current_is_incorrect_supersession(self):
        result = _result(["f-new"], {"f-new": _admission("limited_by_cross_fact_state_change")})
        self.assertIn("incorrect_supersession", self._score({"current": ["w2"]}, result)["classes"])

    def test_missing_dependency_isolation_and_abstention(self):
        result = _result(["f-other"], {"f-other": _admission()})
        classes = self._score({"current": ["w2"], "dependency": ["w3"], "forbidden": ["w4"]}, result)["classes"]
        self.assertEqual(classes, ["missing_current", "missing_dependency", "isolation_violation"])
        empty = self._score({"current": ["w2"]}, _result([], {}))["classes"]
        self.assertIn("unnecessary_abstention", empty)


class FixtureRun(unittest.TestCase):
    def test_fixture_expectations_never_reach_the_runtime(self):
        fixture = lu.load_fixture()
        runtime_keys = {"id", "op", "ref", "text", "proposition", "source_ref", "scope", "replacement_kind",
                        "evidence", "expect_committed", "valid_from", "valid_until", "observed_at"}
        for scenario in fixture["scenarios"]:
            for session in scenario["sessions"]:
                for write in session.get("writes", ()):
                    self.assertLessEqual(set(write), runtime_keys, write["id"])

    def test_baseline_run_is_deterministic_and_matches_frozen_report(self):
        first = lu.run_fixture()
        second = lu.run_fixture()
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        overall = first["summary"]["overall"]
        self.assertEqual(overall["probes"], 40)
        self.assertEqual(overall["isolation_violation"], 0)
        self.assertEqual(overall["incorrect_supersession"], 0)


if __name__ == "__main__":
    unittest.main()
