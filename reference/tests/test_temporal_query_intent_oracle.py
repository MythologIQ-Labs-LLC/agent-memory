"""Frozen adversarial oracle for query temporal intent interpreter 1.1.0 (#585).

The fixture was committed before the 1.1.0 implementation. Every case states the
resolved mode/posture/confidence/intent basis and the exact source spans the
interpreter must consume or deliberately decline. Offsets are checked against the
original query string, so spans can never be reconstructed from evidence strings.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.runtime import temporal_intent as ti  # noqa: E402

FIXTURE = ROOT / "reference" / "fixtures" / "runtime" / "temporal-query-intent-v1.1-adversarial.json"
ORACLE = json.loads(FIXTURE.read_text(encoding="utf-8"))


def _resolve(case: dict) -> ti.TemporalIntent:
    return ti.resolve_intent(case["query"], case.get("temporal_intent"))


class TemporalQueryIntentOracleTests(unittest.TestCase):
    def test_interpreter_identity(self):
        self.assertEqual(ti.INTERPRETER_REF, ORACLE["interpreter_ref"])
        self.assertEqual(ti.INTERPRETER_VERSION, ORACLE["target_interpreter_version"])

    def test_every_frozen_case(self):
        for case in ORACLE["cases"]:
            with self.subTest(case=case["id"]):
                expect = case["expect"]
                intent = _resolve(case)
                value = intent.to_dict()
                for key in ("mode", "posture", "confidence", "intent_basis", "orders_temporally"):
                    self.assertEqual(value[key], expect[key], f"{case['id']} {key}")
                for key in ("target_start", "target_end", "expected_recall_shape"):
                    if key in expect:
                        self.assertEqual(value[key], expect[key], f"{case['id']} {key}")
                self.assertEqual([[s["text"], s["mode"]] for s in value["spans"]], expect["consumed"])
                self.assertEqual([[s["text"], s["reason"]] for s in value["declined_spans"]], expect["declined"])
                self.assertEqual(expect.get("conflict", False), "ambiguous:conflicting_cues" in value["evidence"])
                self.assertEqual(value["authority_effect"], "none")
                self.assertEqual(value["interpreter_version"], ORACLE["target_interpreter_version"])

    def test_span_offsets_reproduce_source_text_and_are_ordered(self):
        for case in ORACLE["cases"]:
            with self.subTest(case=case["id"]):
                value = _resolve(case).to_dict()
                query = case["query"]
                for group in ("spans", "declined_spans"):
                    spans = value[group]
                    for span in spans:
                        self.assertEqual(query[span["start"]:span["end"]], span["text"])
                        self.assertEqual(span["normalized_text"], span["text"].lower())
                    starts = [(span["start"], span["end"]) for span in spans]
                    self.assertEqual(starts, sorted(starts))
                consumed = [(span["start"], span["end"]) for span in value["spans"]]
                for (_, end), (start, _) in zip(consumed, consumed[1:]):
                    self.assertLessEqual(end, start, "consumed spans must not overlap")

    def test_query_language_explicit_is_never_caller_authority(self):
        for case in ORACLE["cases"]:
            with self.subTest(case=case["id"]):
                intent = _resolve(case)
                if intent.intent_basis == ti.CALLER_DECLARED:
                    self.assertEqual(intent.posture, ti.EXPLICIT)
                    self.assertIn("temporal_intent", case)
                else:
                    self.assertNotEqual(intent.posture, ti.EXPLICIT)

    def test_serialization_is_stable(self):
        for case in ORACLE["cases"]:
            with self.subTest(case=case["id"]):
                first = json.dumps(_resolve(case).to_dict(), sort_keys=True)
                second = json.dumps(_resolve(case).to_dict(), sort_keys=True)
                self.assertEqual(first, second)
                json.loads(first)

    def test_original_query_is_never_rewritten(self):
        for case in ORACLE["cases"]:
            with self.subTest(case=case["id"]):
                query = case["query"]
                snapshot = str(query)
                _resolve(case)
                self.assertEqual(query, snapshot)


if __name__ == "__main__":
    unittest.main()
