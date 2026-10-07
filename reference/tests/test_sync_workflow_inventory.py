"""The workflow-estate reader: trigger shapes, concurrency kinds, the full-suite detector,
the inventory sync and the report, on synthetic workflows (#662)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sync_workflow_inventory as estate  # noqa: E402

WORKFLOW = """name: Synthetic
on:
  push:
    branches: [main]
  pull_request:
    paths:
      - 'docs/**'
  workflow_dispatch:
concurrency:
  group: %s
  cancel-in-progress: %s
permissions:
  contents: read
jobs:
  first:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - run: python -m unittest discover -s reference/tests -t reference -p 'test_x.py'
      - run: python -m unittest discover -s reference/tests -t reference
  second:
    runs-on: ubuntu-latest
    steps:
      - run: |
          python -m unittest discover -s reference/tests -p 'test_*.py'
          python -m unittest reference.tests.test_a reference.tests.test_b
"""


def synthetic(root: Path, name: str, group: str = estate.CONCURRENCY_GROUP, cancel: str = estate.CANCEL_SUPERSEDED) -> Path:
    path = root / estate.WORKFLOWS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(WORKFLOW % (group, cancel), encoding="utf-8")
    return path


class ReaderTests(unittest.TestCase):
    def test_full_suite_detector_covers_the_four_spellings(self):
        self.assertEqual(estate.full_suite_lines("python -m unittest discover -s reference/tests -t reference"), 1)
        self.assertEqual(estate.full_suite_lines("python -m unittest discover -s reference/tests -p 'test_*.py'"), 1)
        self.assertEqual(estate.full_suite_lines("python -m unittest discover -s reference/tests -t reference -p 'test_x.py'"), 0)
        self.assertEqual(estate.full_suite_lines("python -m unittest reference.tests.test_a reference.tests.test_b"), 0)
        self.assertEqual(estate.full_suite_lines("python -m unittest discover --start-directory reference/tests --pattern test_*.py"), 1)
        self.assertEqual(estate.full_suite_lines("python -m unittest discover -s integrations/x/tests"), 0)

    def test_trigger_and_concurrency_shapes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = estate.load_workflow(synthetic(root, "synthetic.yml"))
            shape = estate.workflow_policy(workflow)
            self.assertEqual((shape["pull_request"], shape["push"], shape["other_triggers"]), ("paths", "main", ["workflow_dispatch"]))
            self.assertEqual(shape["concurrency"], "cancel_superseded")
            self.assertEqual(shape["jobs"]["first"], {"timeout_minutes": 10, "full_suite_passes": 1})
            self.assertEqual(shape["jobs"]["second"], {"timeout_minutes": None, "full_suite_passes": 1})
            queued = estate.load_workflow(synthetic(root, "queued.yml", group="anything-${{ github.ref }}", cancel="false"))
            self.assertEqual(estate.concurrency_kind(queued), "complete_every_run")
            literal = estate.load_workflow(synthetic(root, "literal.yml", cancel="true"))
            self.assertEqual(estate.concurrency_kind(literal), "other")
            bare = estate.load_workflow(Path(tmp) / "bare.yml") if False else {"on": {"push": None, "pull_request": None}, "jobs": {}}
            self.assertEqual(estate.trigger_shape(bare["on"]), ("unfiltered", "unrestricted", []))

    def test_sync_check_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            synthetic(root, "synthetic.yml")
            (root / "data").mkdir()
            inventory = {"records": [{"path": ".github/workflows/synthetic.yml", "lifecycleClass": "required_hot_path", "triggers": [], "pathScope": "", "timeoutState": {}, "concurrencyState": {}}], "inventorySummary": {}}
            (root / estate.INVENTORY).write_text(json.dumps(inventory), encoding="utf-8")
            self.assertEqual(estate.main(["--root", str(root), "--check"]), 1)
            self.assertEqual(estate.main(["--root", str(root), "--write"]), 0)
            self.assertEqual(estate.main(["--root", str(root), "--check"]), 0)
            synced = json.loads((root / estate.INVENTORY).read_text(encoding="utf-8"))
            record = synced["records"][0]
            self.assertEqual(record["lifecycleClass"], "required_hot_path", "judgment fields are never rewritten")
            self.assertEqual(record["triggers"], ["pull_request", "push", "workflow_dispatch"])
            self.assertEqual(record["pathScope"], "paths")
            self.assertEqual(record["timeoutState"], {"explicit": True, "valuesMinutes": [10]})
            self.assertEqual(record["concurrencyState"], {"configured": True, "cancelInProgress": True})
            self.assertEqual(synced["inventorySummary"]["triggerCounts"], {"pull_request": 1, "push": 1, "workflow_dispatch": 1})
            self.assertEqual(synced["inventorySummary"]["missingExplicitTimeoutCount"], 0)
            self.assertEqual(synced["inventorySummary"]["supersedablePrOrPushWithoutConcurrencyCount"], 0)
            table = estate.render_report({"synthetic.yml": {"push": "unrestricted"}}, estate.report_rows(root, None))
            self.assertIn("| synthetic.yml | ", table)
            self.assertIn("unrestricted → main", table)


if __name__ == "__main__":
    unittest.main()
