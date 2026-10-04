"""Temporal query intent interpreter 1.1.0 contract (#585).

Complements the frozen adversarial oracle with the contract properties it cannot
express as cases: caller-declared vs query-language explicitness at the admission
gate, typed-span invariants, cross-process determinism, and the #583 boundary that
ordinary memories keep consumed temporal terms as lexical relevance evidence while a
candidate-specific anti-laundering guard may consume the typed spans without globally
rewriting the query.
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
    def test_query_language_explicit_is_explicit_posture_not_caller(self):
        intent = ti.interpret_query("Where am I currently living?")
        self.assertEqual((intent.mode, intent.posture, intent.confidence), (ti.CURRENT, ti.EXPLICIT, None))
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
        # explicit <- {caller_declared, query_language_explicit}; inferred <- query_cue_inference;
        # unspecified <- none.
        ti.TemporalIntent(mode=ti.CURRENT, posture=ti.EXPLICIT, intent_basis=ti.QUERY_LANGUAGE_EXPLICIT)
        for posture, confidence, basis in (
            (ti.INFERRED, ti.HIGH, ti.CALLER_DECLARED),
            (ti.INFERRED, ti.HIGH, ti.QUERY_LANGUAGE_EXPLICIT),
            (ti.EXPLICIT, None, ti.QUERY_CUE_INFERENCE),
            (ti.EXPLICIT, None, ti.NO_BASIS),
            (ti.UNSPECIFIED, None, ti.QUERY_LANGUAGE_EXPLICIT),
            (ti.UNSPECIFIED, None, ti.CALLER_DECLARED),
        ):
            with self.subTest(posture=posture, basis=basis), self.assertRaises(ValueError):
                ti.TemporalIntent(mode=ti.CURRENT, posture=posture, confidence=confidence, intent_basis=basis)
        with self.assertRaises(ValueError):
            ti.TemporalIntent(intent_basis="authority_grant")
        # Pre-1.1.0 constructions keep working with a derived basis.
        self.assertEqual(ti.TemporalIntent(mode=ti.CURRENT, posture=ti.EXPLICIT).intent_basis, ti.CALLER_DECLARED)
        self.assertEqual(ti.TemporalIntent().intent_basis, ti.NO_BASIS)

    def test_only_caller_declaration_widens_admission(self):
        declared = ti.resolve_intent("What was the release codename?", {"mode": "historical"})
        self.assertEqual(admission_mode_for_intent(declared)[0], HISTORICAL_EVIDENCE_ADMISSION)
        # Explicit posture from query language never widens, whatever its mode: the gate
        # reads intent_basis, not posture alone.
        for mode, extra in ((ti.HISTORICAL, {}), (ti.AS_OF, {"target_start": "2019-01-01", "target_end": "2020-01-01"})):
            with self.subTest(mode=mode):
                stated = ti.TemporalIntent(mode=mode, posture=ti.EXPLICIT, intent_basis=ti.QUERY_LANGUAGE_EXPLICIT, **extra)
                self.assertFalse(stated.caller_declared)
                self.assertEqual(admission_mode_for_intent(stated)[0], CURRENT_STATE_ADMISSION)
                caller = ti.TemporalIntent(mode=mode, posture=ti.EXPLICIT, intent_basis=ti.CALLER_DECLARED, **extra)
                self.assertEqual(admission_mode_for_intent(caller)[0], HISTORICAL_EVIDENCE_ADMISSION)
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

    def test_referent_current_only_after_temporal_connective(self):
        # Interrogative "when" is not a connective: current stays the query's own intent.
        for query in ("When does the current staging database password rotation happen?",
                      "While I wait, what is my current address?", "What is my current job?"):
            with self.subTest(query=query):
                intent = ti.interpret_query(query)
                self.assertEqual((intent.mode, intent.intent_basis), (ti.CURRENT, ti.QUERY_LANGUAGE_EXPLICIT))
                self.assertEqual(intent.declined_spans, ())
        intent = ti.interpret_query("What did I earn after I took my current job?")
        self.assertEqual([(d.text, d.reason) for d in intent.declined_spans], [("current", ti.REFERENT_MODIFIER)])

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
    """#583 boundary: typed spans may guard one candidate; ordinary lexical relevance is preserved."""

    def test_ranking_uses_typed_spans_without_owning_a_temporal_cue_list_or_global_rewrite(self):
        source = (ROOT / "reference" / "agentmem_ref" / "runtime" / "ranking_policy.py").read_text(encoding="utf-8")
        self.assertIn("intent.spans", source)
        self.assertIn('span.confidence == "high"', source)
        self.assertIn("persisted_self_claims", source)
        self.assertNotIn("relevance_query_for_intent", source)
        self.assertNotIn("TEMPORAL_PHRASES", source)
        self.assertNotIn("declined_spans", source)
        self.assertNotIn("normalized_text", source)

    def test_consumed_cue_word_still_scores_in_bm25_for_ordinary_memory(self):
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
        # #583 does not globally remove the consumed cue. The ordinary memory still
        # receives lexical credit for it because it carries no high-risk self-claim.
        self.assertGreater(score[cue], score[plain])


if __name__ == "__main__":
    unittest.main()
