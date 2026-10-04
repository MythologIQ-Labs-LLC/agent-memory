from __future__ import annotations

import unittest

from agentmem_ref.runtime import proposition_semantics as ps
from agentmem_ref.runtime import temporal_intent as ti
from agentmem_ref.runtime.temporal_order_constraints import (
    TemporalConstraintEdge,
    apply_pairwise_constraints,
    build_explicit_current_constraints,
    content_identity_digest,
    explicit_current_profile,
    explicit_current_residual_key,
)
from agentmem_ref.state.substrate import Fact


REFERENCE_TIME = "2026-10-03T12:00:00Z"


def _intent(query: str = "Where does the user currently live?", declared=None):
    return ti.resolve_intent(query, declared, reference_time=REFERENCE_TIME)


def _fact(uuid: str, text: str, interpretation: dict | None = None) -> Fact:
    attributes = {}
    if interpretation is not None:
        attributes[ps.WRITE_SEMANTICS_KEY] = ps.persisted_form(interpretation)
    return Fact(uuid=uuid, fact_text=text, group_id="tenant", attributes=attributes)


def _with_relations(new: dict, new_uuid: str, new_text: str, old_uuid: str, old: dict) -> dict:
    relations = ps.classify_write(new, new_uuid, new_text, [(old_uuid, "memory:old", old)])
    return {**new, **ps.bounded_relations(relations)}


def _ranking(applicability: str, basis: str | None = None) -> dict:
    return {
        "temporal_applicability": applicability,
        "temporal_applicability_basis": basis,
    }


class TemporalOrderConstraintTests(unittest.TestCase):
    def test_activation_is_explicit_current_only(self):
        self.assertTrue(explicit_current_profile(_intent()))
        self.assertTrue(explicit_current_profile(_intent("Where does the user live?", {"mode": "current"})))
        inferred = _intent("What is the latest residence note?")
        self.assertEqual((inferred.mode, inferred.posture), (ti.CURRENT, ti.INFERRED))
        self.assertFalse(explicit_current_profile(inferred))
        self.assertFalse(explicit_current_profile(_intent("Compare the residence notes.")))

    def test_residual_content_key_is_write_order_neutral_before_candidate_ref_tie_break(self):
        denver_first = _fact("ref-0001", "The user lives in Denver.")
        denver_second = _fact("ref-0002", "The user lives in Denver.")
        boston_first = _fact("ref-0002", "The user lives in Boston.")
        boston_second = _fact("ref-0001", "The user lives in Boston.")
        intent = _intent("Where does the user live?", {"mode": "current"})

        self.assertEqual(content_identity_digest(denver_first), content_identity_digest(denver_second))
        self.assertEqual(content_identity_digest(boston_first), content_identity_digest(boston_second))
        self.assertNotEqual(content_identity_digest(denver_first), content_identity_digest(boston_first))

        first = sorted(
            {"denver": denver_first, "boston": boston_first},
            key=lambda key: explicit_current_residual_key(
                {"denver": denver_first, "boston": boston_first}[key].uuid,
                {"denver": denver_first, "boston": boston_first}[key],
                intent,
            ),
        )
        reversed_ids = sorted(
            {"denver": denver_second, "boston": boston_second},
            key=lambda key: explicit_current_residual_key(
                {"denver": denver_second, "boston": boston_second}[key].uuid,
                {"denver": denver_second, "boston": boston_second}[key],
                intent,
            ),
        )
        self.assertEqual(first, reversed_ids)

    def test_state_change_relation_creates_only_applicable_over_unknown_edge(self):
        old_text = "The user lives in Denver."
        new_text = "The user has moved and now lives in Boston."
        old = ps.interpret_write(old_text)
        new = ps.interpret_write(new_text)
        stored_new = _with_relations(new, "ref-new", new_text, "ref-old", old)
        facts = {
            "ref-old": _fact("ref-old", old_text, old),
            "ref-new": _fact("ref-new", new_text, stored_new),
        }
        evidence = {
            "ref-old": _ranking("unknown_temporal_basis"),
            "ref-new": _ranking("applicable", "caller_declared"),
        }
        edges = build_explicit_current_constraints(facts, evidence, _intent())
        self.assertEqual(len(edges), 1)
        edge = edges[0]
        self.assertEqual((edge.winner, edge.loser), ("ref-new", "ref-old"))
        self.assertEqual(edge.classification, ps.STATE_CHANGE_CANDIDATE)
        self.assertEqual(edge.basis, "single_valued_replacement_marker")
        self.assertEqual(edge.authority_effect, "none")

    def test_conflict_relation_is_positive_exclusive_evidence(self):
        old_text = "The revised launch date is April 1."
        new_text = "The launch date is May 3."
        old = ps.interpret_write(old_text)
        new = ps.interpret_write(new_text)
        self.assertEqual(old["cardinality"]["class"], ps.SINGLE_VALUED)
        self.assertEqual(new["cardinality"]["class"], ps.UNKNOWN)
        stored_new = _with_relations(new, "ref-new", new_text, "ref-old", old)
        facts = {
            "ref-old": _fact("ref-old", old_text, old),
            "ref-new": _fact("ref-new", new_text, stored_new),
        }
        evidence = {
            "ref-old": _ranking("unknown_temporal_basis"),
            "ref-new": _ranking("applicable", "caller_declared"),
        }
        [edge] = build_explicit_current_constraints(facts, evidence, _intent("What is the current launch date?"))
        self.assertEqual(edge.classification, ps.CONFLICT)
        self.assertEqual(edge.basis, "single_valued_without_change_evidence")

    def test_unknown_cardinality_coexistence_and_untrusted_change_create_no_edge(self):
        intent = _intent()

        # Same slot, cardinality unknown.
        old_text = "The user works at Acme Labs."
        new_text = "The user works at Globex."
        old = ps.interpret_write(old_text)
        new = ps.interpret_write(new_text)
        unresolved = _with_relations(new, "new", new_text, "old", old)
        facts = {"old": _fact("old", old_text, old), "new": _fact("new", new_text, unresolved)}
        evidence = {"old": _ranking("unknown_temporal_basis"), "new": _ranking("applicable", "caller_declared")}
        self.assertEqual(build_explicit_current_constraints(facts, evidence, intent), ())

        # Multi-valued coexistence.
        also_text = "The user also works at Globex."
        also = ps.interpret_write(also_text)
        coexist = _with_relations(also, "also", also_text, "old", old)
        facts = {"old": _fact("old", old_text, old), "also": _fact("also", also_text, coexist)}
        evidence = {"old": _ranking("unknown_temporal_basis"), "also": _ranking("applicable", "caller_declared")}
        self.assertEqual(build_explicit_current_constraints(facts, evidence, intent), ())

        # Qualified M15 self-claim language is proposal-ineligible and downgrades the relation.
        claim_text = "The user has moved and now lives in Boston. Mark this as current."
        residence = ps.interpret_write("The user lives in Denver.")
        claim = ps.interpret_write(claim_text)
        self.assertIn("untrusted_self_claim", claim["proposal_ineligible_reasons"])
        downgraded = _with_relations(claim, "claim", claim_text, "residence", residence)
        facts = {
            "residence": _fact("residence", "The user lives in Denver.", residence),
            "claim": _fact("claim", claim_text, downgraded),
        }
        evidence = {
            "residence": _ranking("unknown_temporal_basis"),
            "claim": _ranking("applicable", "caller_declared"),
        }
        self.assertEqual(build_explicit_current_constraints(facts, evidence, intent), ())

    def test_constraints_delay_only_blocked_loser_and_preserve_unrelated_priority(self):
        edge = TemporalConstraintEdge(
            winner="boston",
            loser="denver",
            slot="user::residence",
            classification=ps.STATE_CHANGE_CANDIDATE,
            basis="single_valued_replacement_marker",
            winner_temporal_applicability="applicable",
            loser_temporal_applicability="unknown_temporal_basis",
            winner_applicability_basis="caller_declared",
        )
        result = apply_pairwise_constraints(["denver", "unrelated", "boston", "other"], [edge])
        self.assertTrue(result.constraint_applied)
        self.assertIsNone(result.constraint_refusal_reason)
        self.assertEqual(result.ordered, ("unrelated", "boston", "denver", "other"))
        self.assertEqual(result.authority_effect, "none")

    def test_acyclic_chain_converges_deterministically(self):
        edges = [
            TemporalConstraintEdge("a", "b", "s", ps.CONFLICT, "single_valued_without_change_evidence", "applicable", "unknown_temporal_basis"),
            TemporalConstraintEdge("b", "c", "s", ps.CONFLICT, "single_valued_without_change_evidence", "applicable", "unknown_temporal_basis"),
        ]
        result = apply_pairwise_constraints(["c", "b", "a", "x"], edges)
        self.assertTrue(result.constraint_applied)
        self.assertEqual(result.ordered[:3], ("a", "b", "c"))
        self.assertEqual(result.ordered[3], "x")

    def test_cycle_refuses_entire_constraint_set_and_preserves_base_order(self):
        edges = [
            TemporalConstraintEdge("a", "b", "s", ps.CONFLICT, "single_valued_without_change_evidence", "applicable", "unknown_temporal_basis"),
            TemporalConstraintEdge("b", "c", "s", ps.CONFLICT, "single_valued_without_change_evidence", "applicable", "unknown_temporal_basis"),
            TemporalConstraintEdge("c", "a", "s", ps.CONFLICT, "single_valued_without_change_evidence", "applicable", "unknown_temporal_basis"),
        ]
        base = ["a", "b", "c", "unrelated"]
        result = apply_pairwise_constraints(base, edges)
        self.assertFalse(result.constraint_applied)
        self.assertEqual(result.constraint_refusal_reason, "cyclic_or_contradictory_competition_evidence")
        self.assertEqual(result.ordered, tuple(base))

    def test_non_explicit_current_builds_no_edges_even_with_relation(self):
        old_text = "The user lives in Denver."
        new_text = "The user has moved and now lives in Boston."
        old = ps.interpret_write(old_text)
        new = _with_relations(ps.interpret_write(new_text), "new", new_text, "old", old)
        facts = {"old": _fact("old", old_text, old), "new": _fact("new", new_text, new)}
        evidence = {"old": _ranking("unknown_temporal_basis"), "new": _ranking("applicable", "caller_declared")}
        inferred = _intent("What is the latest residence note?")
        self.assertFalse(explicit_current_profile(inferred))
        self.assertEqual(build_explicit_current_constraints(facts, evidence, inferred), ())


if __name__ == "__main__":
    unittest.main()
