from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical_scheme_registry_candidate import (  # noqa: E402
    CandidateSchemeRegistry,
    SchemeRegistryError,
    run_fixture_case,
)

FIXTURE = ROOT / "fixtures" / "runtime" / "canonicalization-scheme-registry-v1.json"


class CanonicalSchemeRegistryCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.registry = CandidateSchemeRegistry(cls.fixture)

    def test_fixture_is_frozen_before_runtime_integration(self):
        self.assertEqual(
            self.fixture["status"],
            "FROZEN_PREIMPLEMENTATION_QUALIFICATION_CONTRACT",
        )
        self.assertEqual(self.fixture["authority_effect"], "none")
        self.assertEqual(self.fixture["owner_issue"], 620)
        self.assertEqual(len(self.fixture["bindings"]), 6)
        self.assertIn("rfc8785_jcs_identity", {row["domain"] for row in self.fixture["excluded_domains"]})

    def test_every_frozen_case_resolves_or_refuses_exactly_as_declared(self):
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                actual = run_fixture_case(case, self.registry)
                if "expected_binding" in case:
                    self.assertEqual(
                        actual,
                        {"outcome": "resolved", "binding_id": case["expected_binding"]},
                    )
                else:
                    self.assertEqual(
                        actual,
                        {"outcome": "refused", "reason": case["expected_refusal"]},
                    )

    def test_sha256_prefix_is_domain_scoped_not_global_scheme_identity(self):
        substrate = self.registry.resolve(
            operation="verify",
            domain="substrate_state",
            runtime_state_schema="1.0.0",
            recorded_commitment="sha256:" + "a" * 64,
            requested_canonicalizer="legacy-python-sorted-json-v1",
            requested_root_contract="substrate-full-json-sha256-v1",
        )
        governance = self.registry.resolve(
            operation="verify",
            domain="governance_state",
            runtime_state_schema="1.0.0",
            recorded_commitment="sha256:" + "b" * 64,
            requested_canonicalizer="legacy-python-sorted-json-v1",
            requested_root_contract="governance-full-json-sha256-v1",
        )
        self.assertNotEqual(substrate.binding_id, governance.binding_id)
        self.assertEqual(substrate.recorded_prefix, governance.recorded_prefix)
        self.assertNotEqual(substrate.root_contract, governance.root_contract)

    def test_prefix_correct_but_wrong_domain_refuses_before_root_trust(self):
        with self.assertRaises(SchemeRegistryError) as caught:
            self.registry.resolve(
                operation="verify",
                domain="governance_state",
                runtime_state_schema="1.1.0",
                recorded_commitment="bmerkle-v1:" + "c" * 64,
                requested_canonicalizer="legacy-python-sorted-json-v1",
                requested_root_contract="substrate-bucketed-merkle-sha256-v1",
            )
        self.assertEqual(caught.exception.reason, "unknown_scheme_for_domain")

    def test_candidate_successor_can_be_inspected_but_not_emitted(self):
        binding = self.registry.resolve(
            operation="inspect",
            domain="substrate_state",
            runtime_state_schema=None,
            recorded_commitment="bmerkle-v2:" + "d" * 64,
            requested_canonicalizer="agent-memory-canonical-json-v2",
            requested_root_contract="substrate-bucketed-merkle-sha256-v2-candidate",
        )
        self.assertEqual(binding.binding_id, "substrate-bmerkle-v2-candidate")
        self.assertEqual(binding.activation, "candidate_not_emittable")

        with self.assertRaises(SchemeRegistryError) as caught:
            self.registry.resolve(
                operation="emit",
                domain="substrate_state",
                runtime_state_schema=None,
                recorded_commitment="bmerkle-v2:" + "d" * 64,
                requested_canonicalizer="agent-memory-canonical-json-v2",
                requested_root_contract="substrate-bucketed-merkle-sha256-v2-candidate",
            )
        self.assertEqual(caught.exception.reason, "candidate_activation_forbidden")

    def test_invalid_commitment_shape_refuses_after_known_binding_selection(self):
        with self.assertRaises(SchemeRegistryError) as caught:
            self.registry.resolve(
                operation="verify",
                domain="substrate_state",
                runtime_state_schema="1.1.0",
                recorded_commitment="bmerkle-v1:not-hex",
                requested_canonicalizer="legacy-python-sorted-json-v1",
                requested_root_contract="substrate-bucketed-merkle-sha256-v1",
            )
        self.assertEqual(caught.exception.reason, "invalid_commitment_shape")


if __name__ == "__main__":
    unittest.main()
