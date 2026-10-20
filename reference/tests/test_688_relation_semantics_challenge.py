"""Synthetic development falsifiers, never an independent held-out benchmark."""
import unittest
from dataclasses import FrozenInstanceError

from agentmem_ref.evaluation.relation_semantics_challenge import (
    RelationObservation, RelationQuestion, RelationRuleClaim, inspect_relation_claims,
)


class RelationSemanticChallengeTests(unittest.TestCase):
    def setUp(self):
        self.q = RelationQuestion("alice", "managed_by", "project:a")
        self.edge = RelationObservation("fact:1", "bob", "manages", "alice", "project:a", "source:1")
        self.inverse = RelationRuleClaim("rule:1", "inverse", "manages", "managed_by", "project:a", "rule-source:1")

    def run_case(self, *, edges=None, rules=None, returned=None, ops=frozenset({"direct"}), q=None, limit=64):
        return inspect_relation_claims(q or self.q, edges if edges is not None else (self.edge,),
            rules if rules is not None else (self.inverse,),
            public_returned_refs=returned if returned is not None else frozenset({"fact:1"}),
            requested_operations=ops, max_returned_edges=limit)

    def test_no_automatic_inverse_reasoning(self):
        self.assertEqual(self.run_case().hints, ())

    def test_explicit_inverse_remains_a_hypothesis(self):
        x = self.run_case(ops=frozenset({"inverse"}))
        self.assertEqual((x.hints[0].object_ref, x.hints[0].rule_claim_ref), ("bob", "rule:1"))
        self.assertEqual(x.claim_verification, "not_performed")
        self.assertEqual(x.authority_effect, "none")
        self.assertFalse(x.may_withhold_content)

    def test_direct_claim_does_not_need_ontology(self):
        edge = RelationObservation("fact:1", "alice", "managed_by", "bob", "project:a", "source:1")
        self.assertEqual(self.run_case(edges=(edge,), rules=()).hints[0].object_ref, "bob")

    def test_implication_is_opt_in_and_not_a_causal_claim(self):
        rule = RelationRuleClaim("rule:2", "implies", "manages", "works_with", "project:a", "src:2")
        q = RelationQuestion("bob", "works_with", "project:a")
        self.assertEqual(self.run_case(rules=(rule,), q=q).hints, ())
        x = self.run_case(rules=(rule,), q=q, ops=frozenset({"implication"}))
        self.assertEqual(x.hints[0].explanation_kind, "implication_rule_claim")
        self.assertEqual(x.hints[0].authority_effect, "none")

    def test_private_and_cross_domain_cannot_supply_hints(self):
        self.assertEqual(self.run_case(returned=frozenset(), ops=frozenset({"inverse"})).hints, ())
        q = RelationQuestion("alice", "managed_by", "project:b")
        self.assertEqual(self.run_case(q=q, ops=frozenset({"inverse"})).hints, ())

    def test_unverified_absence_not_negative_evidence(self):
        x = self.run_case(rules=(), ops=frozenset({"inverse"}))
        self.assertEqual(x.hints, ())
        self.assertFalse(x.may_withhold_content)

    def test_inactive_and_wrong_domain_rules_do_not_expand(self):
        inactive = RelationRuleClaim("r", "inverse", "manages", "managed_by", "project:a", "src", active=False)
        wrong = RelationRuleClaim("r:other", "inverse", "manages", "managed_by", "project:b", "src")
        self.assertEqual(self.run_case(rules=(inactive, wrong), ops=frozenset({"inverse"})).hints, ())

    def test_disjoint_and_subclass_rules_are_explicitly_unsupported(self):
        rules = (RelationRuleClaim("d", "disjoint", "person", "project", "project:a", "src"),
                 RelationRuleClaim("s", "subclass", "person", "actor", "project:a", "src"))
        x = self.run_case(rules=rules, ops=frozenset({"inverse", "implication"}))
        self.assertEqual(x.unsupported_rule_claims, 2)
        self.assertEqual(x.hints, ())
        self.assertFalse(x.may_withhold_content)

    def test_budget_truncation_observable_not_silent(self):
        edge2 = RelationObservation("fact:2", "carol", "manages", "alice", "project:a", "source:2")
        x = self.run_case(edges=(self.edge, edge2), returned=frozenset({"fact:1", "fact:2"}),
                          ops=frozenset({"inverse"}), limit=1)
        self.assertEqual(len(x.hints), 1)
        self.assertTrue(x.truncated)
        self.assertFalse(x.may_withhold_content)

    def test_deterministic_and_immutable(self):
        x = self.run_case(ops=frozenset({"inverse"}))
        self.assertEqual(x, self.run_case(ops=frozenset({"inverse"})))
        with self.assertRaises(FrozenInstanceError):
            x.authority_effect = "grant"

    def test_unbounded_and_duplicate_rule_claims_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "budget"):
            inspect_relation_claims(self.q, (self.edge,), (self.inverse, self.inverse),
                public_returned_refs=frozenset({"fact:1"}), max_rule_claims=1)
        with self.assertRaisesRegex(ValueError, "duplicate rule"):
            self.run_case(rules=(self.inverse, self.inverse), ops=frozenset({"inverse"}))

    def test_empty_provenance_rule_is_rejected(self):
        bad = RelationRuleClaim("rule:1", "inverse", "manages", "managed_by", "project:a", "")
        with self.assertRaisesRegex(ValueError, "provenance"):
            self.run_case(rules=(bad,), ops=frozenset({"inverse"}))

    def test_invalid_operation_and_bad_budget_refused(self):
        with self.assertRaises(ValueError):
            self.run_case(ops=frozenset({"unbounded"}))
        with self.assertRaises(ValueError):
            self.run_case(limit=0)


if __name__ == "__main__":
    unittest.main()
