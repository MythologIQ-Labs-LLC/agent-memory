"""Harvest closeout v3 (#644 T-controller, docs/plan-644-t-controller.md S8).

v3 supersedes v2 without editing it (docs/CONTRIBUTOR_ARCHITECTURE.md section 11a). It must
hold every v2 rule against the repository, and differ from v2 only in the rows the plan names.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "reference"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_rc1_evidence_closeout import build_manifest  # noqa: E402
from test_harvest_closeout_v2 import V2, load, violations  # noqa: E402

V3 = REPO_ROOT / "reference" / "fixtures" / "harvest-closeout-final-v3.json"
CHANGED_ROWS = {
    "evolveai-vector-retrieval",
    "jh-04-route-needs",
    "jh-06-call-deadline-budget",
    "jh-09-bounded-traversal",
    "codegenome-graph-propagation",
    "jh-14-telemetry",
}


class HarvestCloseoutV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v2, self.v3 = load(V2), load(V3)

    def test_record_holds_against_the_repository(self) -> None:
        self.assertEqual(violations(self.v3), [])

    def test_supersedes_v2_and_changes_only_the_named_rows(self) -> None:
        self.assertEqual(self.v3["supersedes"], {"artifact_id": self.v2["artifact_id"], "path": "reference/fixtures/harvest-closeout-final-v2.json"})
        self.assertEqual(self.v3["status"], self.v2["status"])
        before = {row["row_id"]: row for row in self.v2["rows"]}
        after = {row["row_id"]: row for row in self.v3["rows"]}
        self.assertEqual(set(before), set(after))
        self.assertEqual({rid for rid in after if after[rid] != before[rid]}, CHANGED_ROWS)
        changed_scope = [b["v1_ref"].get("id") for a, b in zip(self.v2["out_of_mechanism_scope"], self.v3["out_of_mechanism_scope"]) if a != b]
        self.assertEqual(sorted(changed_scope), ["JH-11", "JH-15"])

    def test_dispositions_the_plan_records(self) -> None:
        rows = {row["row_id"]: row for row in self.v3["rows"]}
        self.assertEqual((rows["evolveai-vector-retrieval"]["disposition"], rows["evolveai-vector-retrieval"]["reachability"]), ("shipped", "facade"))
        for rid in ("jh-04-route-needs", "jh-06-call-deadline-budget", "jh-09-bounded-traversal"):
            self.assertEqual(rows[rid]["tranche"]["order"], "T-controller-2", rid)
        self.assertEqual((rows["codegenome-graph-propagation"]["tranche"]["issue"], rows["codegenome-graph-propagation"]["tranche"]["order"]), (688, "T-typed-relations"))
        self.assertEqual(rows["jh-14-telemetry"]["disposition"], "tranche")
        self.assertIn("contract 1.5.0", rows["jh-14-telemetry"]["reason"])

    def test_rc1_closeout_manifest_names_v3_or_its_successor(self) -> None:
        # v4 supersedes v3 by pointer (docs/plan-644-lanes-v4.md L8); v3 stays published unchanged.
        harvest = build_manifest("0" * 40)["harvest_closeout"]
        self.assertIn(harvest["artifact"], {"reference/fixtures/harvest-closeout-final-v3.json", "reference/fixtures/harvest-closeout-final-v4.json"})
        self.assertEqual(harvest["status"], self.v3["status"])


if __name__ == "__main__":
    unittest.main()
