"""#773: preregister current-time served-context applicability, not retrieval admission.

No hard-coded dataset vocabulary, model-based identity inference, or stop authority.
The old composed recall path must remain byte-for-byte unchanged.
"""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime
from tests.test_runtime_composition import _context, _plan, _proposal, TENANT


class CurrentServedContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = ConfiguredCompositionRuntime.create(
            Path(self.tmp.name), tenant=TENANT, plan=_plan(),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def retain(self, label, content, *, validity=None):
        proposal = replace(
            _proposal("proposal:773:" + label, operation="promotion"),
            target_reference="memory:773:" + label,
        )
        outcome = self.runtime.retain(proposal, content, temporal=validity)
        self.assertTrue(outcome.committed)
        return outcome.fact_uuid

    def test_elapsed_window_not_delivered_as_current_context(self):
        expired = self.retain(
            "past-freeze", "The Cedarline firmware deployment freeze is active",
            validity={"valid_from":"2025-11-01T00:00:00Z",
                      "valid_until":"2025-12-01T00:00:00Z"},
        )
        persistent = self.retain("ongoing", "Cedarline firmware deployment handbook is available")
        old = self.runtime.multi_route_recall(
            "Cedarline firmware deployment",
            _context(),
            temporal_intent={"mode":"current", "reference_time":"2026-10-12T12:00:00Z"},
        )
        self.assertIn(expired, old.admitted)
        observed = self.runtime.current_served_context(
            "Cedarline firmware deployment", _context(),
            budget=5, reference_time="2026-10-12T12:00:00Z",
        )
        self.assertNotIn(expired, observed.served_refs)
        self.assertIn(persistent, observed.served_refs)
        self.assertGreaterEqual(observed.known_inapplicable_count, 1)
        self.assertFalse(observed.complete_evidence_attested)
        self.assertEqual(observed.authority_effect, "none")

    def test_valid_during_window_may_be_delivered(self):
        freeze = self.retain(
            "freeze", "Cedarline firmware freeze is active",
            validity={"valid_from":"2025-11-01T00:00:00Z",
                      "valid_until":"2025-12-01T00:00:00Z"},
        )
        observed = self.runtime.current_served_context(
            "Cedarline firmware freeze", _context(),
            budget=3, reference_time="2025-11-15T12:00:00Z",
        )
        self.assertIn(freeze, observed.served_refs)

    def test_window_end_is_exclusive_and_start_is_inclusive(self):
        freeze = self.retain(
            "freeze", "Cedarline release freeze",
            validity={"valid_from":"2025-11-01T00:00:00Z",
                      "valid_until":"2025-12-01T00:00:00Z"},
        )
        for instant, is_valid in (
            ("2025-11-01T00:00:00Z", True),
            ("2025-12-01T00:00:00Z", False),
        ):
            with self.subTest(instant=instant):
                observed = self.runtime.current_served_context(
                    "Cedarline release freeze", _context(),
                    budget=2, reference_time=instant,
                )
                self.assertEqual(freeze in observed.served_refs, is_valid)

    def test_future_start_is_not_current(self):
        future = self.retain(
            "future-window", "Cedarline firmware maintenance is scheduled",
            validity={"valid_from":"2030-01-01T00:00:00Z"},
        )
        selected = self.runtime.current_served_context(
            "Cedarline firmware maintenance", _context(),
            budget=3, reference_time="2026-10-12T12:00:00Z",
        )
        self.assertNotIn(future, selected.served_refs)

    def test_missing_or_unzoned_reference_time_rejected_before_recall(self):
        for target in (None, "", "2026-10-12", "2026-10-12T12:00:00",
                       "not-a-date"):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    self.runtime.current_served_context(
                        "Cedarline", _context(), budget=1, reference_time=target,
                    )

    def test_invalid_budget_rejected_without_lookup(self):
        for budget in (0, -1, True, 1.5, 101):
            with self.subTest(budget=budget):
                with self.assertRaises(ValueError):
                    self.runtime.current_served_context(
                        "Cedarline", _context(),
                        budget=budget, reference_time="2026-10-12T12:00:00Z",
                    )

    def test_historical_recall_remains_able_to_admit_past_window(self):
        former = self.retain(
            "old-window", "Cedarline deployment freeze was active",
            validity={"valid_from":"2025-11-01T00:00:00Z",
                      "valid_until":"2025-12-01T00:00:00Z"},
        )
        historical = self.runtime.multi_route_recall(
            "Cedarline deployment freeze", _context(),
            temporal_intent={"mode":"historical"},
        )
        self.assertIn(former, historical.admitted)

    def test_empty_selection_not_proof_of_answer_abstention_or_global_absence(self):
        freeze = self.retain(
            "freeze", "Cedarline freeze active",
            validity={"valid_until":"2025-12-01T00:00:00Z"},
        )
        observed = self.runtime.current_served_context(
            "Cedarline freeze active", _context(),
            budget=1, reference_time="2026-10-12T12:00:00Z",
        )
        self.assertEqual(observed.served_refs, ())
        self.assertFalse(observed.complete_evidence_attested)
        self.assertEqual(observed.authority_effect, "none")
        old = self.runtime.multi_route_recall("Cedarline freeze active", _context())
        self.assertIn(freeze, old.admitted)


if __name__ == "__main__":
    unittest.main()
