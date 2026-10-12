"""#771 v2 lifecycle runner and lifecycle-consistent gold qualification."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_served_memory_lifecycle_scenarios as lifecycle  # noqa: E402
from qualify_served_memory_run import qualify  # noqa: E402

INPUTS = {
    "schema": lifecycle.SCHEMA, "tenant": "tenant-a", "project": "proj-a", "purpose": "lifecycle-test",
    "events": [
        {"id": "db-v1", "op": "retain", "memory": "db", "text": "The primary database is MySQL 5.7"},
        {"id": "db-v2", "op": "correct", "memory": "db", "text": "The primary database is PostgreSQL 15"},
        {"id": "secret", "op": "retain", "memory": "secret", "text": "The primary database password is hunter2"},
        {"id": "secret-del", "op": "delete", "memory": "secret"},
        {"id": "beta", "op": "retain", "memory": "beta", "text": "The primary database is Oracle", "project": "proj-b"},
        {"id": "other-tenant", "op": "retain", "memory": "ot", "text": "The primary database is DB2",
         "tenant": "tenant-b"},
    ],
    "queries": [
        {"id": "cur", "query": "What is the primary database?", "intent": "current", "budget": 3},
        {"id": "hist", "query": "Which database did we use before PostgreSQL?", "intent": "historical",
         "budget": 3},
    ],
}
ALL = ("db-v1", "db-v2", "secret", "beta", "other-tenant")


def _gold():
    def case(q, rel, groups, stale):
        return {"id": q["id"], "scenario": q["query"], "intent": q["intent"], "budget": q["budget"],
                "relevance": rel, "critical_groups": groups,
                "prohibited": ["secret", "beta", "other-tenant"], "stale": stale,
                "safe_answer_exists": True}
    cur, hist = INPUTS["queries"]
    return {"schema": "served-memory-quality-v1", "cases": [
        case(cur, {"db-v1": 2, "db-v2": 3, "secret": 1, "beta": 3, "other-tenant": 3}, [["db-v2"]], ["db-v1"]),
        case(hist, {"db-v1": 3, "db-v2": 2, "secret": 0, "beta": 0, "other-tenant": 0}, [["db-v1"]], []),
    ]}


class LabelIntegrityDefects(unittest.TestCase):
    """Evaluator-qualification defects; each failed before its repair."""

    def test_R_A1_gold_cannot_credit_an_error_corrected_value(self):
        # An error correction declares the previous value was never true; the
        # runtime refuses it as corrected_as_false for every intent. Gold that
        # makes it the critical answer to a historical question measures the
        # label, not memory quality (the Halcyon v1 encoding defect).
        data = copy.deepcopy(INPUTS)
        self.assertEqual(data["events"][1]["op"], "correct")
        gold = _gold()
        hist = gold["cases"][1]
        self.assertEqual(hist["critical_groups"], [["db-v1"]])
        facts = lifecycle.lifecycle_facts(data)
        run = {"schema": "served-memory-run-v1", "runtime_revision": "t", "lane_id": "t",
               "execution_backend": "composed-multiroute",
               "input_sha256": lifecycle.canonical_input_digest(data),
               "rows": [{"id": q["id"], "returned": []} for q in data["queries"]]}
        self.assertEqual(facts["error_corrected"], ["db-v1"])
        with self.assertRaisesRegex(ValueError, "error-corrected"):
            qualify(data, gold, run)
        # The same history recorded as a STATE CHANGE is legitimate history.
        data["events"][1]["op"] = "update"
        run["input_sha256"] = lifecycle.canonical_input_digest(data)
        qualify(data, _gold(), run)


class LifecycleRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {}
        for backend in ("composed-multiroute", "governed-lexical"):
            with tempfile.TemporaryDirectory() as tmp:
                cls.runs[backend] = lifecycle.run_scenarios(
                    copy.deepcopy(INPUTS), Path(tmp), revision="test", lane_id="lifecycle", backend=backend)

    def test_lifecycle_facts_are_derived_from_inputs_only(self):
        facts = lifecycle.lifecycle_facts(copy.deepcopy(INPUTS))
        self.assertEqual(facts["fact_ids"], sorted(ALL))
        self.assertEqual(facts["superseded"], ["db-v1"])
        self.assertEqual(facts["deleted"], ["secret"])
        self.assertEqual(facts["out_of_scope"], ["beta", "other-tenant"])

    def test_deleted_and_out_of_scope_memories_are_never_served(self):
        for backend, (run, _diag) in self.runs.items():
            for row in run["rows"]:
                with self.subTest(backend=backend, query=row["id"]):
                    self.assertFalse({"secret", "beta", "other-tenant"} & set(row["returned"]))

    def test_run_qualifies_against_lifecycle_consistent_gold(self):
        for backend, (run, _diag) in self.runs.items():
            report = qualify(copy.deepcopy(INPUTS), _gold(), copy.deepcopy(run))
            self.assertEqual(report["execution_backend"], backend)
            self.assertEqual(report["P0_safety"]["cases_with_prohibited_exposure"], 0)

    def test_gold_that_does_not_prohibit_a_deleted_memory_is_refused(self):
        gold = _gold()
        gold["cases"][1]["prohibited"].remove("secret")
        with self.assertRaisesRegex(ValueError, "deleted and out-of-scope"):
            qualify(copy.deepcopy(INPUTS), gold, copy.deepcopy(self.runs["composed-multiroute"][0]))

    def test_gold_that_calls_a_superseded_value_current_is_refused(self):
        gold = _gold()
        gold["cases"][0]["stale"] = []
        with self.assertRaisesRegex(ValueError, "superseded"):
            qualify(copy.deepcopy(INPUTS), gold, copy.deepcopy(self.runs["composed-multiroute"][0]))

    def test_changed_history_breaks_input_binding(self):
        altered = copy.deepcopy(INPUTS)
        altered["events"][1]["text"] = "The primary database is SQLite"
        with self.assertRaisesRegex(ValueError, "different input corpus"):
            qualify(altered, _gold(), copy.deepcopy(self.runs["composed-multiroute"][0]))

    def test_invalid_histories_fail_before_any_write(self):
        bad = {
            "gold_field": lambda d: d["events"][0].__setitem__("relevance", 3),
            "correct_unknown": lambda d: d["events"].insert(0, {"id": "x", "op": "correct", "memory": "nope",
                                                                "text": "t"}),
            "retain_twice": lambda d: d["events"].append({"id": "x", "op": "retain", "memory": "db", "text": "t"}),
            "delete_with_text": lambda d: d["events"][3].__setitem__("text", "t"),
            "move_scope": lambda d: d["events"][1].__setitem__("project", "proj-b"),
            "correct_after_delete": lambda d: d["events"].append({"id": "x", "op": "correct", "memory": "secret",
                                                                  "text": "t"}),
        }
        for name, mutate in bad.items():
            data = copy.deepcopy(INPUTS)
            mutate(data)
            with self.subTest(name), tempfile.TemporaryDirectory() as tmp:
                store = Path(tmp) / "store"
                with self.assertRaises(ValueError):
                    lifecycle.run_scenarios(data, store, revision="t", lane_id="l")
                self.assertFalse(store.exists())

    def test_a_value_corrected_repeatedly_commits_every_step(self):
        data = copy.deepcopy(INPUTS)
        data["events"].insert(2, {"id": "db-v3", "op": "correct", "memory": "db",
                                  "text": "The primary database is PostgreSQL 16"})
        facts = lifecycle.lifecycle_facts(data)
        self.assertEqual(facts["superseded"], ["db-v1", "db-v2"])
        with tempfile.TemporaryDirectory() as tmp:
            run, _ = lifecycle.run_scenarios(data, Path(tmp), revision="t", lane_id="l")
        current = next(r for r in run["rows"] if r["id"] == "cur")["returned"]
        self.assertNotIn("db-v1", current)
        self.assertNotIn("db-v2", current)

    def test_state_change_history_is_admissible_but_error_correction_is_not(self):
        outcomes = {}
        for op in ("update", "correct"):
            data = copy.deepcopy(INPUTS)
            data["events"][1]["op"] = op
            with tempfile.TemporaryDirectory() as tmp:
                run, diag = lifecycle.run_scenarios(data, Path(tmp), revision="t", lane_id="l")
            hist = next(r for r in run["rows"] if r["id"] == "hist")["returned"]
            late = next(d for d in diag if d["id"] == "hist")["beyond_budget"]
            cur = next(r for r in run["rows"] if r["id"] == "cur")["returned"]
            outcomes[op] = ("db-v1" in hist + late, "db-v1" in cur)
        self.assertEqual(outcomes["update"], (True, False))
        self.assertEqual(outcomes["correct"], (False, False))

    def test_budget_diagnostics_report_relevant_but_late_memories(self):
        for backend, (run, diag) in self.runs.items():
            for row, extra in zip(run["rows"], diag):
                self.assertEqual(row["id"], extra["id"])
                self.assertEqual(extra["ranked_admitted_count"], len(row["returned"]) + len(extra["beyond_budget"]))


if __name__ == "__main__":
    unittest.main()
