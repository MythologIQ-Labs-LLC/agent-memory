"""validation(#777 contract 1.7.0 @ ada418c): independent negotiation and schema checks."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from agentmem_ref.adapter import GovernedMemoryAdapter
from agentmem_ref.api import contract, surface
from agentmem_ref.core import receipts
from agentmem_ref.substrate import InMemoryTemporalGraph

REPO = Path(__file__).resolve().parents[2]
FIX = REPO / "reference" / "fixtures" / "api"
EXAMPLE = json.loads((FIX / "proposal-envelope.example.json").read_text(encoding="utf-8"))
RECALL = json.loads((FIX / "recall-context.example.json").read_text(encoding="utf-8"))
PRIOR = ("1.0.0", "1.1.0", "1.2.0", "1.3.0", "1.4.0", "1.5.0", "1.6.0", "1.7.0", "1.8.0")
SCHEMAS = ("api-action-envelope", "api-execution-observation", "api-proposal-envelope",
           "api-recall-context", "api-result-envelope", "api-target-envelope")


class Contract17Compatibility(unittest.TestCase):
    def setUp(self):
        self.memory = GovernedMemoryAdapter(InMemoryTemporalGraph(), tenant="org:example")
        self.assertTrue(surface.commit(self.memory, EXAMPLE, "release branch release")["committed"])

    def test_every_prior_version_is_served_current_with_a_1_7_0_result(self):
        for version in PRIOR:
            with self.subTest(version=version):
                out = surface.recall(self.memory, "release branch", {**RECALL, "contract_version": version})
                self.assertEqual((out["stage"], out["compatibility"], out["contract_version"]),
                                 ("recall", contract.CURRENT, "1.8.0"))
                self.assertEqual(out["public_projection"]["policy_version"], "1.0.0")
                hist = surface.history(self.memory, {"contract_version": version,
                                                     "target_reference": EXAMPLE["target_reference"]})
                self.assertEqual((hist["stage"], hist["contract_version"]), ("history", "1.8.0"))

    def test_next_minor_requires_migration_and_returns_no_data(self):
        out = surface.recall(self.memory, "release branch", {**RECALL, "contract_version": "1.9.0"})
        self.assertEqual((out["stage"], out["compatibility"]), ("none", contract.MIGRATION_REQUIRED))
        self.assertFalse({"candidates", "admitted", "admissions", "returned"} & set(out))

    def test_six_schemas_accept_exactly_the_prior_versions_through_the_current(self):
        for name in SCHEMAS:
            with self.subTest(schema=name):
                enum = json.loads((REPO / "schemas" / f"{name}.schema.json").read_text())["properties"]["contract_version"]["enum"]
                self.assertEqual(tuple(enum), PRIOR)

    def test_result_schema_rejects_an_unknown_future_contract_version(self):
        doc = {"contract_version": "1.9.0", "compatibility": contract.CURRENT, "stage": "recall"}
        with self.assertRaises(ValueError):
            receipts.validate(contract.RESULT_SCHEMA, doc)


if __name__ == "__main__":
    unittest.main()
