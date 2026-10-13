"""No-CI orchestration: source fingerprint, pending evidence and fail-closed checks."""
from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.refresh_benchmark_pages import RefreshError, compute_status, source_inventory, refresh


def fixture(root: Path):
    inputs = [
        "reports/benchmarks/dashboard/current.json",
        "reports/benchmarks/replays/594-post-550-semantic-qualification/phase-b-score-v1.json",
        "reports/benchmarks/amb/v7/new-native/evidence.json",
    ]
    for name in inputs:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"test":true}', encoding="utf-8")
    (root / "reports/benchmarks/normalized").mkdir(parents=True)
    files = {
        "reports/benchmarks/scorecards/scorecards.json": {},
        "reports/benchmarks/scorecards/scorecards.md": "scorecard",
        "reports/benchmarks/ui/catalog.json": {"authority_effect":"none","snapshot":{"id":"snapshot:1"}},
        "reports/benchmarks/ui/frontier-leaderboards.json": {"authority_effect":"none","aggregate_score":None,
                         "snapshot_id":"snapshot:1","external_competitors":{"same_harness_measured":["mem0-oss"]}},
        "reports/benchmarks/ui/historical-amb-v6.json": {"evidence_status":"historical_source_bound_not_promoted",
                         "eligible_for_frontier_rankings":False},
    }
    for name, value in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value) if not isinstance(value,str) else value,encoding="utf-8")


class RefreshGovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        fixture(self.root)

    def test_inventory_detects_changed_source(self):
        before=source_inventory(self.root)
        p=self.root/"reports/benchmarks/amb/v7/new-native/evidence.json"
        p.write_text('{"different":true}',encoding="utf-8")
        after=source_inventory(self.root)
        self.assertNotEqual(before,after)

    def test_unregistered_evidence_visible_without_ranking(self):
        result=compute_status(self.root,registered=set())
        self.assertEqual(result["unregistered_source_count"],1)
        self.assertEqual(result["measured_external_system_ids"],["mem0-oss"])
        self.assertTrue(result["accepted_evidence_only_in_rankings"])

    def test_registration_removes_pending_only(self):
        path="reports/benchmarks/amb/v7/new-native/evidence.json"
        result=compute_status(self.root,registered={path})
        self.assertEqual(result["unregistered_source_count"],0)
        self.assertEqual(result["measured_external_system_ids"],["mem0-oss"])

    def test_refuses_historical_auto_promotion(self):
        p=self.root/"reports/benchmarks/ui/historical-amb-v6.json"
        p.write_text(json.dumps({"evidence_status":"historical_source_bound_not_promoted",
                                 "eligible_for_frontier_rankings":True}),encoding="utf-8")
        with self.assertRaisesRegex(RefreshError,"promoted"):
            compute_status(self.root,registered=set())

    def test_refuses_snapshot_mismatch(self):
        p=self.root/"reports/benchmarks/ui/frontier-leaderboards.json"
        doc=json.loads(p.read_text(encoding="utf-8"))
        doc["snapshot_id"]="wrong"
        p.write_text(json.dumps(doc),encoding="utf-8")
        with self.assertRaisesRegex(RefreshError,"catalog snapshot"):
            compute_status(self.root,registered=set())

    @patch("scripts.refresh_benchmark_pages._run")
    def test_check_never_rewrites_stale_manifest(self,mock_run):
        status=self.root/"reports/benchmarks/ui/refresh-status.json"
        status.write_text("{}",encoding="utf-8")
        with self.assertRaisesRegex(RefreshError,"stale"):
            refresh(self.root,check=True,registered=set())
        self.assertEqual(status.read_text(encoding="utf-8"),"{}")
        self.assertEqual(mock_run.call_count,4)

    @patch("scripts.refresh_benchmark_pages._run")
    def test_write_then_check_is_idempotent(self,mock_run):
        one=refresh(self.root,registered=set())
        two=refresh(self.root,check=True,registered=set())
        self.assertEqual(one,two)
        self.assertEqual(mock_run.call_count,8)

    @patch("scripts.refresh_benchmark_pages._run")
    def test_failed_generator_refuses_publish(self,mock_run):
        mock_run.side_effect=RuntimeError("generator failed")
        with self.assertRaisesRegex(RuntimeError,"generator failed"):
            refresh(self.root,registered=set())
        self.assertFalse((self.root/"reports/benchmarks/ui/refresh-status.json").exists())

if __name__=="__main__":
    unittest.main()
