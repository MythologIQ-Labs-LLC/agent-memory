"""Pure local tests for the non-authoritative bounded-feedback orchestrator."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_runtime_fast_feedback.py"
SPEC = importlib.util.spec_from_file_location("fast_feedback", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimeFastFeedbackTests(unittest.TestCase):
    def _root(self, suites: tuple[str, ...] | None = None) -> Path:
        root = Path(self.temp.name)
        target = root / "reference" / "tests"
        target.mkdir(parents=True, exist_ok=True)
        (target / "__init__.py").write_text("", encoding="utf-8")
        for name in suites or MODULE.selected_suites("retrieval"):
            (target / name).write_text("", encoding="utf-8")
        return root

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_focus_and_all_are_disjoint_source_paths(self):
        all_names = MODULE.selected_suites("all")
        self.assertEqual(len(all_names), len(set(all_names)))
        self.assertEqual(len(all_names), 6)
        self.assertEqual(len(MODULE.selected_suites("retrieval")), 2)

    def test_all_selected_suites_pass_but_never_qualify(self):
        root = self._root()
        with patch.object(MODULE, "_git", side_effect=["a" * 40, ""]), \
             patch.object(MODULE, "_record_suite", side_effect=lambda _r, n, _t: {"suite": n, "status": "passed"}):
            r = MODULE.run(root, "retrieval", 30, 10)
        self.assertEqual(r["status"], "passed")
        self.assertTrue(r["git_clean"])
        self.assertFalse(r["comparison_eligible"])
        self.assertFalse(r["runtime_baseline_activated"])
        self.assertEqual(r["qualification_effect"], "none")

    def test_dirty_worktree_pass_is_nonqualifying(self):
        root = self._root()
        with patch.object(MODULE, "_git", side_effect=["a" * 40, " M core.py"]), \
             patch.object(MODULE, "_record_suite", side_effect=lambda _r, n, _t: {"suite": n, "status": "passed"}):
            r = MODULE.run(root, "retrieval", 30, 10)
        self.assertEqual(r["status"], "passed")
        self.assertFalse(r["git_clean"])
        self.assertFalse(r["comparison_eligible"])

    def test_one_failure_is_not_hidden(self):
        root = self._root()
        statuses = iter(["passed", "failed"])
        with patch.object(MODULE, "_git", side_effect=["a" * 40, ""]), \
             patch.object(MODULE, "_record_suite", side_effect=lambda _r, n, _t: {"suite": n, "status": next(statuses)}):
            r = MODULE.run(root, "retrieval", 30, 10)
        self.assertEqual(r["status"], "failed_or_incomplete")
        self.assertEqual(r["passed_suites"], 1)

    def test_budget_exhaustion_preserves_unrun_suites(self):
        root = self._root()
        with patch.object(MODULE, "_git", side_effect=["a" * 40, ""]), \
             patch.object(MODULE, "_record_suite", return_value={"status": "passed"}), \
             patch.object(MODULE.time, "monotonic", side_effect=[0, 0, 6, 6, 7]):
            r = MODULE.run(root, "retrieval", 5, 5)
        self.assertEqual(r["status"], "failed_or_incomplete")
        self.assertEqual(r["suites"][1]["status"], "budget_exhausted")

    def test_missing_selected_suite_fails_closed(self):
        root = self._root()
        (root / "reference/tests/test_multi_route_recall.py").unlink()
        with self.assertRaisesRegex(ValueError, "modules absent"):
            MODULE.run(root, "retrieval", 20, 10)

    def test_invalid_budgets_fail_closed(self):
        root = self._root()
        with self.assertRaisesRegex(ValueError, "budgets must be positive"):
            MODULE.run(root, "retrieval", 0, 10)

    def test_real_subprocess_receipt_surfaces_failure(self):
        root = self._root()
        (root / "reference/tests/test_query_driven_recall.py").write_text(
            "import unittest\nclass Probe(unittest.TestCase):\n def test_failure(self):\n  self.fail('intentional')\n",
            encoding="utf-8",
        )
        res = MODULE._record_suite(root, "test_query_driven_recall.py", 10)
        self.assertEqual(res["status"], "failed")
        self.assertNotEqual(res["exit_code"], 0)
        self.assertIn("intentional", res["stderr_tail"])


if __name__ == "__main__":
    unittest.main()
