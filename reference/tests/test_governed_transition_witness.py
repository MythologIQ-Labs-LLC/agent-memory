"""#644 independent transition-witness controls, no network or benchmark gold."""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
import unittest

MODULE = Path(__file__).resolve().parents[1] / "agentmem_ref/runtime/governed_transition_witness.py"
spec = importlib.util.spec_from_file_location("governed_transition_witness", MODULE)
w = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = w
spec.loader.exec_module(w)


def candidate():
    return {
        "classification": "state_change_candidate",
        "other_fact_uuid": "fact:old",
        "slot": "typed:beacon api|region",
        "proposal": {
            "proposal_id": "proposal:change",
            "operation": "correction",
            "replacement_kind": "state_change",
            "source_fact_uuid": "fact:source",
            "target_fact_uuid": "fact:old",
            "target_reference": "memory:target",
            "applied": False,
            "authority_effect": "none",
        },
    }


def record(kind="state_change", evidence=("proposal:change",)):
    return {
        "kind": kind,
        "memory_id": "memory:target",
        "proposal_id": "proposal:governed-correction",
        "evidence_refs": list(evidence),
        "replaced_at": "2026-01-01T00:00:00Z",
    }


def evaluate(*, relation=None, replacement=None,
             source="fact:source", prior="fact:old",
             current="fact:current", slot="typed:beacon api|region"):
    return w.inspect_committed_replacement(
        source_fact_ref=source,
        prior_fact_ref=prior,
        current_target_fact_ref=current,
        source_slot=slot,
        relation=candidate() if relation is None else relation,
        replacement=record() if replacement is None else replacement,
    )


class GovernedTransitionWitnessTests(unittest.TestCase):
    def test_qualified_record_distinguishes_observation_from_successor_proof(self):
        result = evaluate()
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "applied_state_change_observed")
        self.assertEqual(result.current_target_fact_ref, "fact:current")
        self.assertFalse(result.immediate_successor_verified)
        self.assertFalse(result.answer_quality_verified)
        self.assertFalse(result.can_stop)
        self.assertFalse(result.can_mutate)
        self.assertEqual(result.authority_effect, "none")
        self.assertNotIn("replacement_text", json.dumps(result.to_dict()))

    def test_error_correction_is_not_presented_as_historically_true(self):
        result = evaluate(replacement=record("error_correction"))
        self.assertEqual(result.status, "applied_error_correction_observed")
        self.assertEqual(result.replacement_kind, "error_correction")

    def test_claimed_change_without_governed_record_does_not_count(self):
        for payload in (
            {}, record(evidence=()), record(evidence=("not-the-proposal",)),
            {**record(), "memory_id": "memory:elsewhere"},
            {**record(), "kind": "imaginary"},
            {**record(), "proposal_id": None},
        ):
            with self.subTest(payload=payload):
                self.assertIsNone(evaluate(replacement=payload))

    def test_wrong_identity_or_relation_is_not_a_transition(self):
        for modified in (
            {"classification": "coexistence"},
            {"other_fact_uuid": "fact:foreign"},
            {"slot": "typed:other|scope"},
        ):
            claim = candidate()
            claim.update(modified)
            with self.subTest(modified=modified):
                self.assertIsNone(evaluate(relation=claim))
        for change in (
            {"operation": "promotion"}, {"replacement_kind": "error_correction"},
            {"source_fact_uuid": "fact:outsider"},
            {"target_fact_uuid": "fact:outsider"},
            {"authority_effect": "allow"}, {"applied": True},
            {"target_reference": "memory:other"},
        ):
            claim = candidate()
            claim["proposal"] = {**claim["proposal"], **change}
            with self.subTest(change=change):
                self.assertIsNone(evaluate(relation=claim))

    def test_no_immediate_successor_guess_from_current_head(self):
        self.assertIsNone(evaluate(current="fact:old"))
        self.assertIsNone(evaluate(current="fact:source"))
        # A different current fact can be a later successor, NOT proof of
        # a direct edge from this correction to that fact.
        result = evaluate(current="fact:later-generation")
        self.assertIsNotNone(result)
        self.assertFalse(result.immediate_successor_verified)

    def test_caller_cannot_forge_authority_in_witness_constructor(self):
        result = evaluate()
        for change in (
            {"immediate_successor_verified": True},
            {"answer_quality_verified": True},
            {"can_stop": True},
            {"can_mutate": True},
            {"authority_effect": "grant"},
            {"observer_version": "alternate"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(result, **change)

    def test_deterministic_serialization_contains_only_references(self):
        a = evaluate()
        b = evaluate()
        self.assertEqual(a.to_dict(), b.to_dict())
        serialized = json.dumps(a.to_dict(), sort_keys=True)
        self.assertNotIn("Beacon API region is", serialized)
        self.assertNotIn("replacement_text", serialized)


if __name__ == "__main__":
    unittest.main()
