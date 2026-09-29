"""Temporal query intent interpreter 1.1.0 contract (#585).

Complements the frozen adversarial oracle with the contract properties it cannot
express as cases: caller-declared vs query-language explicitness at the admission
gate, typed-span invariants, cross-process determinism, and the #583 boundary that
lexical relevance still scores every query token.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import temporal_intent as ti  # noqa: E402
from agentmem_ref.runtime.adapter import CURRENT_STATE_ADMISSION, HISTORICAL_EVIDENCE_ADMISSION  # noqa: E402
from agentmem_ref.runtime.contextual_recall_adapter import admission_mode_for_intent  # noqa: E402

FIXTURE = ROOT / "reference" / "fixtures" / "runtime" / "temporal-query-intent-v1.1-adversarial.json"
REGRESSION_CF22B7BF = "How much weight have I lost since I started going to the gym consistently?"


class InterpreterIdentityTests(unittest.TestCase):
    def test_version_and_ref(self):
        self.assertEqual(ti.INTERPRETER_VERSION, "1.1.0")
        self.assertEqual(ti.INTERPRETER_REF, "agent-memory-deterministic-temporal-cues")
        intent = ti.interpret_query("Where do I live now?")
        self.assertEqual((intent.interpreter_ref, intent.interpreter_version), (ti.INTERPRETER_REF, "1.1.0"))


class ExplicitSourceTests(unittest.TestCase):
    def test_query_language_explicit_is_inferred_high_not_caller(self):
        intent = ti.interpret_query("Where am I currently living?")
        self.assertEqual((intent.mode, intent.posture, intent.confidence), (ti.CURRENT, ti.INFERRED, ti.HIGH))
        self.assertEqual(intent.intent_basis, ti.QUERY_LANGUAGE_EXPLICIT)
        self.assertFalse(intent.caller_declared)
        caller = ti.resolve_intent("Where does the user live?", {"mode": "current"})
        self.assertEqual((caller.posture, caller.intent_basis), (ti.EXPLICIT, ti.CALLER_DECLARED))
        self.assertTrue(caller.caller_declared)
        self.assertEqual(caller.spans, ())

    def test_caller_declaration_outranks_query_language(self):
        intent = ti.resolve_intent("Where do I live right now?", {"mode": "historical"})
        self.assertEqual((intent.mode, intent.intent_basis), (ti.HISTORICAL, ti.CALLER_DECLARED))

    def test_posture_basis_invariants(self):
        with self.assertRaises(ValueError):
            ti.TemporalIntent(mode=ti.CURRENT, posture=ti.EXPLICIT, intent_basis=ti.QUERY_LANGUAGE_EXPLICIT)
        with self.assertRaises(ValueError):
            ti.TemporalIntent(mode=ti.CURRENT, posture=ti.INFERRED, confidence=ti.HIGH, intent_basis=ti.CALLER_DECLARED)
        with self.assertRaises(ValueError):
            ti.TemporalIntent(mode=ti.CURRENT, posture=ti.INFERRED, confidence=ti.LOW, intent_basis=ti.QUERY_LANGUAGE_EXPLICIT)
        with self.assertRaises(ValueError):
            ti.TemporalIntent(intent_basis="authority_grant")
        # Pre-1.1.0 constructions keep working with a derived basis.
        self.assertEqual(ti.TemporalIntent(mode=ti.CURRENT, posture=ti.EXPLICIT).intent_basis, ti.CALLER_DECLARED)
        self.assertEqual(ti.TemporalIntent().intent_basis, ti.NO_BASIS)

    def test_only_caller_declaration_widens_admission(self):
        declared = ti.resolve_intent("What was the release codename?", {"mode": "historical"})
        self.assertEqual(admission_mode_for_intent(declared)[0], HISTORICAL_EVIDENCE_ADMISSION)
        for query in ("What was the release codename previously?", "What was the codename in 2019?",
                      "What was the codename used to be, right now?"):
            with self.subTest(query=query):
                self.assertEqual(admission_mode_for_intent(ti.interpret_query(query))[0], CURRENT_STATE_ADMISSION)


class SpanContractTests(unittest.TestCase):
    def test_composites_do_not_emit_nested_contradictory_evidence(self):
        for query, text in (("Where do I live right now?", "right now"), ("As of now, where do I live?", "As of now"),
                            ("What is due as of today?", "as of today"), ("What ships next week?", "next week")):
            with self.subTest(query=query):
                intent = ti.interpret_query(query)
                self.assertEqual([span.text for span in intent.spans], [text])
                self.assertEqual(intent.declined_spans, ())
                nested = text.split()[-1].lower()
                self.assertFalse(any(e.endswith(f":{nested}") for e in intent.evidence if e != f"{e.split(':')[0]}:{e.split(':')[1]}:{text.lower()}"))

    def test_repeated_cues_are_all_spanned_in_order(self):
        query = "Where do I live now, and where do I work now?"
        intent = ti.interpret_query(query)
        self.assertEqual([(s.start, s.text) for s in intent.spans], [(16, "now"), (41, "now")])
        self.assertEqual(intent.evidence, ("current:high:now",))
        for span in intent.spans:
            self.assertEqual(query[span.start:span.end], span.text)

    def test_span_fields_serialize_stably(self):
        value = ti.interpret_query("Where am I going to stay next month?").to_dict()
        self.assertEqual(
            value["spans"][0],
            {"start": 11, "end": 19, "text": "going to", "normalized_text": "going to", "mode": "prospective",
             "confidence": "high", "basis": "query_cue", "cue_id": "prospective.going_to.future_auxiliary"},
        )
        self.assertEqual(json.loads(json.dumps(value, sort_keys=True)), value)

    def test_regression_cf22b7bf(self):
        intent = ti.interpret_query(REGRESSION_CF22B7BF)
        self.assertEqual((intent.mode, intent.posture, intent.confidence), (ti.ATEMPORAL, ti.UNSPECIFIED, None))
        self.assertFalse(intent.orders_temporally)
        self.assertEqual([(d.text, d.reason) for d in intent.declined_spans], [("going to", ti.HABITUAL_OR_MOTION)])
        self.assertNotIn("prospective:high:going to", intent.evidence)

    def test_ambiguous_uses_never_order_temporally(self):
        for query in ("Now where do I live?", "Where should I park for now?", "Where was I going home?",
                      "Show me now.", "Tell me now where I live.", "What is the word 'now' used for?",
                      "Where do I live now, and where did I live before?"):
            with self.subTest(query=query):
                self.assertFalse(ti.interpret_query(query).orders_temporally)


class CrossProcessDeterminismTests(unittest.TestCase):
    def test_interpretation_is_identical_across_processes_and_hash_seeds(self):
        script = (
            "import json,sys;sys.path.insert(0,'reference');"
            "from agentmem_ref.runtime.temporal_intent import resolve_intent;"
            f"cases=json.load(open({str(FIXTURE)!r}))['cases'];"
            "print(json.dumps([resolve_intent(c['query'],c.get('temporal_intent')).to_dict() for c in cases],sort_keys=True))"
        )
        outputs = []
        for seed in ("0", "1", "random"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            outputs.append(subprocess.run([sys.executable, "-c", script], cwd=ROOT, env=env,
                                          capture_output=True, text=True, check=True).stdout)
        self.assertEqual(len(set(outputs)), 1)
        self.assertEqual(len(json.loads(outputs[0])), len(json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]))


class LexicalRelevanceBoundaryTests(unittest.TestCase):
    """#583 boundary: consumed temporal cues still count as lexical relevance evidence."""

    def test_ranking_policy_does_not_read_spans(self):
        source = (ROOT / "reference" / "agentmem_ref" / "runtime" / "ranking_policy.py").read_text(encoding="utf-8")
        for token in ("spans", "declined_spans", "intent_basis", "normalized_text"):
            self.assertNotIn(token, source)

    def test_consumed_cue_word_still_scores_in_bm25(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = AgentMemory.open(temp, tenant="tenant:585", actor_id="agent:585", scope="project:585",
                                      purpose="585 lexical boundary")
            try:
                cue = memory.remember("memory:cue", "The user currently lives on Mallory Street.")["fact_uuid"]
                plain = memory.remember("memory:plain", "The user happily lives on Mallory Street.")["fact_uuid"]
                recalled = memory.recall("Where does the user currently live?", reference_time="2026-09-29T00:00:00Z")
                score = {ref: recalled["admissions"][ref]["ranking_evidence"]["lexical_relevance_score"] for ref in (cue, plain)}
                intent = recalled["admissions"][cue]["ranking_evidence"]["query_temporal_intent"]
            finally:
                memory.close()
        self.assertEqual(intent["intent_basis"], ti.QUERY_LANGUAGE_EXPLICIT)
        self.assertEqual([span["text"] for span in intent["spans"]], ["currently"])
        # The consumed cue is still lexical evidence: #585 does not implement #583.
        self.assertGreater(score[cue], score[plain])


if __name__ == "__main__":
    unittest.main()
