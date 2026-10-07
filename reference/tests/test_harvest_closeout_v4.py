"""Harvest closeout v4 (#644 -v4 lanes, docs/plan-644-lanes-v4.md L8).

v4 supersedes v3 without editing it (docs/CONTRIBUTOR_ARCHITECTURE.md section 11a). It must
hold every v2 rule against the repository, and differ from v3 only in jh-14-telemetry.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "reference"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_rc1_evidence_closeout import build_manifest  # noqa: E402
from test_harvest_closeout_v2 import load, violations  # noqa: E402

V3 = REPO_ROOT / "reference" / "fixtures" / "harvest-closeout-final-v3.json"
V4 = REPO_ROOT / "reference" / "fixtures" / "harvest-closeout-final-v4.json"


class HarvestCloseoutV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.v3, self.v4 = load(V3), load(V4)

    def test_record_holds_against_the_repository(self) -> None:
        self.assertEqual(violations(self.v4), [])

    def test_supersedes_v3_and_changes_only_jh_14(self) -> None:
        self.assertEqual(self.v4["supersedes"], {"artifact_id": self.v3["artifact_id"], "path": "reference/fixtures/harvest-closeout-final-v3.json"})
        self.assertEqual(self.v4["status"], self.v3["status"])
        before = {row["row_id"]: row for row in self.v3["rows"]}
        after = {row["row_id"]: row for row in self.v4["rows"]}
        self.assertEqual(set(before), set(after))
        self.assertEqual({rid for rid in after if after[rid] != before[rid]}, {"jh-14-telemetry"})
        self.assertEqual(self.v4["out_of_mechanism_scope"], self.v3["out_of_mechanism_scope"])

    def test_jh_14_is_shipped_on_the_facade_with_the_accepted_shadow_rows(self) -> None:
        row = next(row for row in self.v4["rows"] if row["row_id"] == "jh-14-telemetry")
        self.assertEqual((row["disposition"], row["reachability"]), ("shipped", "facade"))
        self.assertEqual({item["variant"] for item in row["evidence"]}, {
            "lane:longmemeval-s-retrieval-parity-v4:agent_memory_shadow:session",
            "lane:longmemeval-s-retrieval-parity-v4:agent_memory_shadow:turn",
            "lane:amb-precisionmembench-retrieval-v4:agent-memory-shadow",
        })
        for rid in ("jh-04-route-needs", "jh-06-call-deadline-budget", "jh-09-bounded-traversal"):
            self.assertEqual(next(r for r in self.v4["rows"] if r["row_id"] == rid)["tranche"]["order"], "T-controller-2", rid)

    def test_rc1_closeout_manifest_names_v4(self) -> None:
        harvest = build_manifest("0" * 40)["harvest_closeout"]
        self.assertEqual(harvest["artifact"], "reference/fixtures/harvest-closeout-final-v4.json")


if __name__ == "__main__":
    unittest.main()
