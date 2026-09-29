from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical_scheme_registry_candidate import (  # noqa: E402
    CandidateSchemeRegistry,
    SchemeRegistryError,
)


class CanonicalSchemeRegistryEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = CandidateSchemeRegistry.from_frozen_fixture()

    def test_runtime_1_1_envelope_refuses_legacy_governance_mixed_with_current_substrate(self):
        substrate = self.registry.resolve(
            operation="verify",
            domain="substrate_state",
            runtime_state_schema="1.1.0",
            recorded_commitment="bmerkle-v1:" + "a" * 64,
            requested_canonicalizer="legacy-python-sorted-json-v1",
            requested_root_contract="substrate-bucketed-merkle-sha256-v1",
        )
        self.assertEqual(substrate.binding_id, "substrate-bmerkle-v1")

        with self.assertRaises(SchemeRegistryError) as caught:
            self.registry.resolve(
                operation="verify",
                domain="governance_state",
                runtime_state_schema="1.1.0",
                recorded_commitment="sha256:" + "b" * 64,
                requested_canonicalizer="legacy-python-sorted-json-v1",
                requested_root_contract="governance-full-json-sha256-v1",
            )
        self.assertEqual(caught.exception.reason, "runtime_schema_binding_mismatch")

    def test_runtime_1_0_envelope_refuses_current_gsect_mixed_with_legacy_generation(self):
        substrate = self.registry.resolve(
            operation="verify",
            domain="substrate_state",
            runtime_state_schema="1.0.0",
            recorded_commitment="sha256:" + "c" * 64,
            requested_canonicalizer="legacy-python-sorted-json-v1",
            requested_root_contract="substrate-full-json-sha256-v1",
        )
        self.assertEqual(substrate.binding_id, "substrate-full-json-v1")

        with self.assertRaises(SchemeRegistryError) as caught:
            self.registry.resolve(
                operation="verify",
                domain="governance_state",
                runtime_state_schema="1.0.0",
                recorded_commitment="gsect-v1:" + "d" * 64,
                requested_canonicalizer="legacy-python-sorted-json-v1",
                requested_root_contract="governance-sections-sha256-v1",
            )
        self.assertEqual(caught.exception.reason, "runtime_schema_binding_mismatch")


if __name__ == "__main__":
    unittest.main()
