"""Frozen adversarial contract for write-time temporal aspect, interpreter 1.1.0 (#598).

The fixture was committed before the 1.1.0 implementation. It states, for natural
counterexamples around every mechanism in the #598 failure inventory, which temporal
regime (if any) describes the principal memory proposition, and which cue matches were
deliberately declined and why. Aspect is evidence only: it never grants currentness,
authority, or a validity window.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.runtime import proposition_semantics as ps  # noqa: E402

FIXTURE = ROOT / "reference" / "fixtures" / "runtime" / "write-temporal-aspect-v1.1-adversarial.json"
CONTRACT = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _aspect(interpretation: dict) -> str:
    regimes = sorted((interpretation.get("markers") or {}).get("aspect") or {})
    return regimes[0] if len(regimes) == 1 else ("none_unknown" if not regimes else "multiple:" + ",".join(regimes))


class WriteTemporalAspectContractTests(unittest.TestCase):
    def test_interpreter_identity(self):
        self.assertEqual(ps.INTERPRETER_REF, CONTRACT["interpreter_ref"])
        self.assertEqual(ps.INTERPRETER_VERSION, CONTRACT["target_interpreter_version"])

    def test_every_frozen_case(self):
        for case in CONTRACT["cases"]:
            with self.subTest(case=case["id"]):
                out = ps.interpret_write(case["text"])
                expect = case["expect"]
                self.assertEqual(_aspect(out), expect["aspect"])
                scope = out["aspect_scope"]
                self.assertEqual(scope["status"], expect["status"])
                self.assertEqual([[d["cue"], d["reason"]] for d in scope.get("declined", [])], expect["declined"])
                for declined in scope.get("declined", []):
                    self.assertIn(declined["reason"], CONTRACT["contract"]["declined_reasons"])
                self.assertEqual(out["authority_effect"], "none")

    def test_markers_aspect_never_carries_more_than_one_regime(self):
        for case in CONTRACT["cases"]:
            with self.subTest(case=case["id"]):
                self.assertLessEqual(len(ps.interpret_write(case["text"]).get("markers", {}).get("aspect", {})), 1)


if __name__ == "__main__":
    unittest.main()
