from __future__ import annotations

import unittest

from run_rc1_evidence_closeout import build_manifest


class RC1EvidenceCloseoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.revision = "0123456789abcdef0123456789abcdef01234567"
        self.manifest = build_manifest(self.revision)

    def test_revision_and_contract_are_explicit(self) -> None:
        self.assertEqual(self.manifest["agent_memory_revision"], self.revision)
        self.assertEqual(self.manifest["contract_version"], "1.2.0")
        self.assertEqual(self.manifest["runtime_profile"], "sqlite_single_host_v1")
        self.assertEqual(self.manifest["schema_version"], "1.0.1")

    def test_evidence_dimensions_remain_separate(self) -> None:
        for key in (
            "product_usability",
            "quality",
            "performance",
            "governance",
            "runtime_recovery",
        ):
            self.assertIn(key, self.manifest)
            self.assertIn(self.manifest[key]["status"], self.manifest["status_model"])

    def test_external_benchmark_is_not_falsely_completed(self) -> None:
        external = self.manifest["external_benchmark"]
        self.assertEqual(external["status"], "external_blocked")
        self.assertTrue(external["protocol_runner_ready"])
        self.assertEqual(external["comparability"], "not_yet_protocol_comparable")
        self.assertEqual(external["issue"], 467)

    def test_harvest_closeout_remains_active_and_independent(self) -> None:
        harvest = self.manifest["harvest_closeout"]
        self.assertEqual(harvest["issue"], 470)
        self.assertEqual(harvest["status"], "active_open")
        self.assertFalse(harvest["external_dependency_required"])
        self.assertEqual(
            harvest["dependency_effect"],
            "does_not_block_repository_owned_rc_evidence_packaging",
        )

    def test_no_aggregate_health_score(self) -> None:
        rendered_keys = set()

        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    rendered_keys.add(key)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.manifest)
        self.assertNotIn("health_score", rendered_keys)
        self.assertNotIn("aggregate_score", rendered_keys)
        self.assertIn("aggregate_memory_health_score", self.manifest["non_claims"])

    def test_bad_revision_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_manifest("main")


if __name__ == "__main__":
    unittest.main()
