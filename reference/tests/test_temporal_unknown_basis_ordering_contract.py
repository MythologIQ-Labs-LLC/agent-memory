from __future__ import annotations

import json
import unittest
from pathlib import Path

from agentmem_ref.runtime import proposition_semantics as ps
from agentmem_ref.runtime import runtime_composition
from agentmem_ref.runtime import temporal_intent as ti


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "reference" / "fixtures" / "runtime" / "temporal-unknown-basis-ordering-v1.json"
EXPECTED_CASES = [f"M{i}" for i in range(1, 14)]


class TemporalUnknownBasisOrderingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.by_id = {case["id"].split("-", 1)[0]: case for case in cls.fixture["cases"]}

    def test_preimplementation_oracle_identity_and_boundary(self):
        self.assertEqual(self.fixture["status"], "FROZEN_PREIMPLEMENTATION_ORACLE")
        self.assertEqual(self.fixture["issue"], 584)
        self.assertEqual(self.fixture["base_sha"], "5f0e85e67a170cc633396a195a9bc4e6d2728bff")
        self.assertEqual(list(self.by_id), EXPECTED_CASES)
        self.assertEqual(len(self.fixture["cases"]), 13)

        deps = self.fixture["dependencies"]
        self.assertEqual(deps["ranking_policy"], "agent-memory-post-admission-ranking/3.1.1")
        self.assertEqual(deps["temporal_interpreter"], "agent-memory-deterministic-temporal-cues/1.1.0")
        self.assertEqual(deps["write_semantics"], "agent-memory-deterministic-write-semantics/1.1.0")

        policy = runtime_composition.MULTI_ROUTE_RANKING_POLICY.identity()
        self.assertEqual(policy["policy_version"], "3.1.1")
        self.assertEqual(ti.INTERPRETER_VERSION, "1.1.0")
        self.assertEqual(ps.INTERPRETER_VERSION, "1.1.0")

    def test_ruling_invariants_are_explicit_and_non_authoritative(self):
        contract = self.fixture["contract"]
        self.assertTrue(contract["pairwise_not_global"])
        self.assertTrue(contract["global_applicable_over_unknown_tier_forbidden"])
        self.assertTrue(contract["exclusive_competition_required"])
        self.assertEqual(self.fixture["authority_effect"], "none")
        self.assertEqual(
            set(contract["activation"]["intent_basis"]),
            {ti.CALLER_DECLARED, ti.QUERY_LANGUAGE_EXPLICIT},
        )
        self.assertEqual(
            contract["forbidden_currentness_clocks"],
            ["transaction_time", "observation_time_without_validity_contract"],
        )
        self.assertTrue(
            {
                "ranking != admission",
                "ranking != truth",
                "relevance != currentness",
                "unknown != stale",
                "unknown != current",
                "newer != current",
                "newer != superseding",
                "interpretation != authority",
                "conflict detection != mutation",
            }
            <= set(contract["preserved_invariants"])
        )

    def test_m1_is_real_same_slot_single_valued_change_pressure(self):
        case = self.by_id["M1"]
        intent = ti.resolve_intent(case["query"], reference_time=case["reference_time"])
        self.assertEqual(
            (intent.mode, intent.posture, intent.intent_basis, intent.orders_temporally),
            (ti.CURRENT, ti.EXPLICIT, ti.QUERY_LANGUAGE_EXPLICIT, True),
        )

        unknown = ps.interpret_write(case["memories"][0]["text"])
        applicable = ps.interpret_write(case["memories"][1]["text"])
        self.assertEqual(unknown["proposition"]["status"], ps.KNOWN)
        self.assertEqual(applicable["proposition"]["status"], ps.KNOWN)
        self.assertEqual(ps.write_slot(unknown), ps.write_slot(applicable))
        self.assertEqual(applicable["cardinality"]["class"], ps.SINGLE_VALUED)
        self.assertEqual(case["expect"]["precedes"], ["applicable", "unknown"])
        self.assertTrue(case["expect"]["unknown_label_preserved"])

    def test_m3_same_slot_unknown_cardinality_cannot_invent_exclusivity(self):
        case = self.by_id["M3"]
        first = ps.interpret_write(case["memories"][0]["text"])
        second = ps.interpret_write(case["memories"][1]["text"])
        self.assertEqual(first["proposition"]["status"], ps.KNOWN)
        self.assertEqual(second["proposition"]["status"], ps.KNOWN)
        self.assertEqual(ps.write_slot(first), ps.write_slot(second))
        self.assertEqual(first["cardinality"]["class"], ps.UNKNOWN)
        self.assertEqual(second["cardinality"]["class"], ps.UNKNOWN)
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertEqual(case["expect"]["constraint_refusal_reason"], "exclusive_cardinality_not_established")

    def test_m4_multivalued_evidence_is_a_hard_negative_control(self):
        case = self.by_id["M4"]
        existing = ps.interpret_write(case["memories"][0]["text"])
        added = ps.interpret_write(case["memories"][1]["text"])
        self.assertEqual(ps.write_slot(existing), ps.write_slot(added))
        self.assertEqual(added["cardinality"]["class"], ps.MULTI_VALUED)
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertEqual(case["expect"]["constraint_refusal_reason"], "coexistence_or_multivalued")

    def test_m5_refuses_hierarchy_claim_when_positive_evidence_is_not_established(self):
        case = self.by_id["M5"]
        self.assertTrue(case["preconditions"]["positive_hierarchical_evidence_required"])
        self.assertTrue(case["preconditions"]["current_interpreter_positive_hierarchy_not_assumed"])
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertTrue(case["expect"]["no_invented_single_valued_semantics"])
        self.assertIn(ps.HIERARCHICAL, ps.CARDINALITIES)

    def test_m10_is_atemporal_and_therefore_outside_584_activation(self):
        case = self.by_id["M10"]
        intent = ti.resolve_intent(case["query"], reference_time=case["reference_time"])
        self.assertEqual((intent.mode, intent.posture, intent.intent_basis), (ti.ATEMPORAL, ti.UNSPECIFIED, ti.NO_BASIS))
        self.assertFalse(intent.orders_temporally)
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertTrue(case["expect"]["byte_identical_to_base_ranking_policy"])

    def test_m11_binds_both_explicit_bases_without_equating_authority(self):
        case = self.by_id["M11"]
        query_variant = case["query_language_variant"]
        caller_variant = case["caller_declared_variant"]
        query_intent = ti.resolve_intent(query_variant["query"], reference_time=case["reference_time"])
        caller_intent = ti.resolve_intent(
            caller_variant["query"],
            caller_variant["temporal_intent"],
            reference_time=case["reference_time"],
        )
        self.assertEqual((query_intent.posture, query_intent.intent_basis), (ti.EXPLICIT, ti.QUERY_LANGUAGE_EXPLICIT))
        self.assertEqual((caller_intent.posture, caller_intent.intent_basis), (ti.EXPLICIT, ti.CALLER_DECLARED))
        self.assertTrue(case["expect"]["same_pairwise_ranking_semantics"])
        self.assertFalse(case["expect"]["admission_authority_equivalence"])

    def test_m12_pins_high_confidence_inferred_current_outside_first_profile(self):
        case = self.by_id["M12"]
        intent = ti.resolve_intent(case["query"], reference_time=case["reference_time"])
        self.assertEqual(
            (intent.mode, intent.posture, intent.confidence, intent.intent_basis, intent.orders_temporally),
            (ti.CURRENT, ti.INFERRED, ti.HIGH, ti.QUERY_CUE_INFERENCE, True),
        )
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertEqual(case["expect"]["constraint_refusal_reason"], "current_intent_not_explicit")

    def test_m13_is_explicit_cycle_refusal_not_a_natural_language_claim(self):
        case = self.by_id["M13"]
        self.assertEqual(case["fixture_kind"], "policy_graph_negative_control")
        constraints = {tuple(edge) for edge in case["proposed_constraints"]}
        self.assertEqual(constraints, {("a", "b"), ("b", "c"), ("c", "a")})
        self.assertFalse(case["expect"]["constraint_applied"])
        self.assertTrue(case["expect"]["preserve_base_order"])
        self.assertTrue(case["expect"]["recency_cycle_break_forbidden"])


if __name__ == "__main__":
    unittest.main()
