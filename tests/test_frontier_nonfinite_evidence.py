"""Independent #768 negative controls: non-finite metrics are not rankings.

Authored before hardening the frontier parser. Both JSON permissive tokens and
floating-point overflow are rejected rather than becoming numeric evidence.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_frontier_objectives import (  # noqa: E402
    FrontierEvidenceError, observed_peer_position, read_json,
)


class FiniteBenchmarkEvidenceTests(unittest.TestCase):
    def test_nonfinite_peer_or_native_never_receives_frontier_position(self):
        base = {
            "agent_memory": 0.6,
            "same_harness_frontier": {"system": "independent-peer", "value": 0.7},
            "direction": "higher",
            "evidence_class": "same_harness_external",
        }
        self.assertEqual(observed_peer_position(base), "behind_observed_peer")
        for bad in (float("nan"), float("inf"), float("-inf")):
            native = {**base, "agent_memory": bad}
            peer = {
                **base,
                "same_harness_frontier": {"system": "independent-peer", "value": bad},
            }
            with self.subTest(bad=repr(bad)):
                self.assertEqual(
                    observed_peer_position(native), "no_comparable_numeric_peer"
                )
                self.assertEqual(
                    observed_peer_position(peer), "no_comparable_numeric_peer"
                )

    def test_reader_rejects_nan_infinity_and_overflow_numeric_json(self):
        cases = (
            '{"a": NaN}',
            '{"a": Infinity}',
            '{"a": -Infinity}',
            '{"a": {"b": [0, 1e999]}}',
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "evidence.json"
            for raw in cases:
                with self.subTest(raw=raw):
                    path.write_text(raw, encoding="utf-8")
                    with self.assertRaisesRegex(
                        FrontierEvidenceError, "non-finite"
                    ):
                        read_json(path)

    def test_finite_metrics_remain_comparable(self):
        base = {
            "agent_memory": 0.6,
            "same_harness_frontier": {"system": "peer", "value": 0.7},
            "direction": "higher",
            "evidence_class": "same_harness_external",
        }
        self.assertEqual(observed_peer_position(base), "behind_observed_peer")
        self.assertEqual(
            observed_peer_position({**base, "agent_memory": 0.8}),
            "ahead_of_observed_peer",
        )
        self.assertEqual(
            observed_peer_position({**base, "agent_memory": True}),
            "no_comparable_numeric_peer",
        )


if __name__ == "__main__":
    unittest.main()
