"""#777 contract 1.7.0 successor controls. Tests committed before the bump.

This is an isolated post-v7 candidate, NOT the published contract or an
approved successor baseline. Old 1.6 readers remain compatibility CURRENT.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from agentmem_ref.api import contract

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"
VERSIONED = (
    "api-action-envelope.schema.json",
    "api-execution-observation.schema.json",
    "api-proposal-envelope.schema.json",
    "api-recall-context.schema.json",
    "api-result-envelope.schema.json",
    "api-target-envelope.schema.json",
)


class Contract17Successor(unittest.TestCase):
    def test_public_contract_identity_moved_past_1_7_0(self):
        # 1.7.0 was the #777 successor; #786 (owner decision on PR #805) moved the identity to 1.8.0.
        self.assertEqual(contract.CONTRACT_VERSION, "1.8.0")

    def test_all_versioned_schemas_accept_1_7_0_and_keep_prior_1_6_0(self):
        for name in VERSIONED:
            with self.subTest(schema=name):
                data = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
                versions = data["properties"]["contract_version"]["enum"]
                self.assertIn("1.7.0", versions)
                self.assertIn("1.6.0", versions)
                self.assertEqual(len(versions), len(set(versions)))
                self.assertEqual(versions[-2], "1.7.0")

    def test_older_minor_is_current_and_next_minor_requires_migration(self):
        self.assertEqual(
            contract.compatibility({"contract_version": "1.6.0"}),
            contract.CURRENT,
        )
        self.assertEqual(
            contract.compatibility({"contract_version": "1.7.0"}),
            contract.CURRENT,
        )
        self.assertEqual(
            contract.compatibility({"contract_version": "1.8.0"}),
            contract.CURRENT,
        )
        self.assertEqual(
            contract.compatibility({"contract_version": "1.9.0"}),
            contract.MIGRATION_REQUIRED,
        )
        self.assertEqual(
            contract.compatibility({"contract_version": "2.0.0"}),
            contract.INCOMPATIBLE,
        )

    def test_result_version_is_the_current_contract_without_invented_authority(self):
        output = contract.result("recall", contract.CURRENT)
        self.assertEqual(output["contract_version"], "1.8.0")
        self.assertEqual(output["stage"], "recall")
        self.assertEqual(output["compatibility"], contract.CURRENT)


if __name__ == "__main__":
    unittest.main()
