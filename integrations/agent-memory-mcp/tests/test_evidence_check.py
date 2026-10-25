"""Host-side output check of the restricted alpha pilot (no model, no MCP)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("evidence_check", Path(__file__).resolve().parents[1] / "pilot" / "evidence_check.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

DELIVERED = ["Harriet waters plot 12 on Monday and Thursday mornings."]


def flags(text, *, named=("Which days does Harriet water plot 12?",)):
    return [f["flag"] for f in module.check(text, delivered_contents=DELIVERED,
                                            delivered_keys=["memory:pilot:harriet-watering"], named=named)]


class EvidenceCheckTests(unittest.TestCase):
    def test_compliant_answer_passes(self):
        text = ('- [key: memory:pilot:harriet-watering | state: resolved | latest for key: True] '
                '"Harriet waters plot 12 on Monday and Thursday mornings."\nFrom memory: Monday and Thursday mornings.')
        self.assertEqual(flags(text), [])

    def test_invented_key_and_quote_are_flagged(self):
        self.assertEqual(flags('- [key: memory:pilot:harriet-schedule] "Harriet waters every day of the week."'),
                         ["uncited_key", "unsourced_quote"])

    def test_curly_quotes_are_normalised(self):
        self.assertEqual(flags("“Harriet waters plot 12 on Monday and Thursday mornings.”"), [])

    def test_verification_and_absence_claims_are_flagged(self):
        self.assertEqual(flags("This answer was verified by the memory system."), ["verification_claim"])
        self.assertEqual(flags("The retrieval validated it."), ["verification_claim"])
        self.assertEqual(flags("That information does not exist."), ["absence_claim"])

    def test_honest_wording_is_not_flagged(self):
        self.assertEqual(flags("This was not verified by the memory system. I could not find this in the retrieved memory."), [])
        self.assertEqual(flags("The save was confirmed: committed is true."), [])

    def test_keys_named_by_the_user_or_a_tool_call_are_allowed(self):
        self.assertEqual(flags("I saved memory:pilot:bench.", named=("save under memory:pilot:bench",)), [])

    def test_display_withholds_flagged_text_and_shows_the_evidence(self):
        shown = module.displayed("The garden is closed.", [{"flag": "absence_claim", "detail": "x"}],
                                 [{"memory_ref": "memory:pilot:a", "state": "resolved", "latest_for_key": True,
                                   "content": "A note."}])
        self.assertIn("[Withheld by the host evidence check: absence_claim]", shown)
        self.assertIn('"A note."', shown)
        self.assertEqual(module.displayed("Fine.", [], []), "Fine.")


if __name__ == "__main__":
    unittest.main()
