"""Preimplementation contract for #583 candidate-specific temporal lexical anti-laundering.

The reviewed oracle was frozen before the runtime guard existed. These tests now bind
that oracle to the already-merged #585 query spans, #598 write semantics, and the narrow
#583 guard. Ranking itself is still unchanged at this checkpoint.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.runtime import proposition_semantics, ranking_policy, temporal_lexical_guard  # noqa: E402
from agentmem_ref.runtime.temporal_intent import explicit_intent, interpret_query  # noqa: E402

FIXTURE = ROOT / "reference" / "fixtures" / "runtime" / "temporal-lexical-anti-laundering-v1.json"


def _fact(text: str, *, missing_write_semantics: bool = False):
    attributes = {}
    if not missing_write_semantics:
        interpretation = proposition_semantics.interpret_write(text)
        attributes[proposition_semantics.WRITE_SEMANTICS_KEY] = proposition_semantics.persisted_form(interpretation)
    return SimpleNamespace(fact_text=text, attributes=attributes)


class TemporalLexicalAntiLaunderingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_reviewed_fixture_is_preimplementation_and_rejects_pr587_model(self):
        self.assertEqual(self.fixture["status"], "FROZEN_PREIMPLEMENTATION_CONTRACT_REVIEWED")
        self.assertEqual(self.fixture["base_sha"], "45d8d7089b63d76b87262f2538ad35c0e2c026bc")
        self.assertEqual(self.fixture["rejected_predecessor"]["pr"], 587)
        self.assertTrue(self.fixture["contract"]["query_is_never_globally_rewritten"])
        self.assertTrue(self.fixture["contract"]["suppression_is_candidate_specific"])
        self.assertTrue(self.fixture["contract"]["sorted_term_accumulation_preserved"])

    def test_oracle_is_derivable_from_merged_typed_evidence(self):
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                query = case["query"]
                caller = case.get("caller_intent")
                intent = explicit_intent(caller) if caller else interpret_query(query)
                expected = case["expect"]

                self.assertEqual(intent.mode, expected["intent_mode"])
                self.assertEqual(intent.orders_temporally, expected["orders_temporally"])

                high_spans = [
                    span.normalized_text for span in intent.spans
                    if span.mode == intent.mode and span.confidence == "high"
                ]
                if "consumed_high_spans" in expected:
                    self.assertEqual(high_spans, expected["consumed_high_spans"])

                low_spans = [
                    span.normalized_text for span in intent.spans
                    if span.mode == intent.mode and span.confidence == "low"
                ]
                if "consumed_low_spans" in expected:
                    self.assertEqual(low_spans, expected["consumed_low_spans"])

                declined = [span.normalized_text for span in intent.declined_spans]
                if "declined_spans" in expected:
                    self.assertEqual(declined, expected["declined_spans"])

                eligible = list(temporal_lexical_guard.eligible_temporal_query_terms(query, intent))
                self.assertEqual(eligible, expected["eligible_query_terms"])

                candidate = case["candidate"]
                fact = _fact(
                    candidate["text"],
                    missing_write_semantics=bool(candidate.get("simulate_missing_write_semantics")),
                )
                claims = list(temporal_lexical_guard.persisted_self_claims(fact))
                if "self_claims" in expected:
                    self.assertEqual(claims, expected["self_claims"])

                suppressed = list(temporal_lexical_guard.suppressed_terms_for_candidate(query, intent, fact))
                self.assertEqual(suppressed, expected["suppressed_for_candidate"])

                for term in expected.get("must_remain_lexical", []):
                    self.assertIn(term, ranking_policy.relevance_tokens(query))
                    self.assertNotIn(term, eligible)
                    self.assertNotIn(term, suppressed)

    def test_masked_occurrence_is_removed_from_effective_df_only_for_that_term(self):
        case = next(item for item in self.fixture["cases"] if item["id"] == "H1-suppressed-occurrence-does-not-poison-df")
        intent = interpret_query(case["query"])
        eligible = set(temporal_lexical_guard.eligible_temporal_query_terms(case["query"], intent))
        self.assertEqual(eligible, {"current"})

        facts = {
            "laundering": _fact(case["candidate"]["text"]),
            "ordinary": _fact(case["ordinary_peer"]["text"]),
        }
        masks = temporal_lexical_guard.candidate_term_masks(case["query"], intent, facts)
        raw_df = sum("current" in set(ranking_policy.relevance_tokens(fact.fact_text)) for fact in facts.values())
        effective_df = sum(
            "current" in set(ranking_policy.relevance_tokens(fact.fact_text))
            and "current" not in set(masks[ref])
            for ref, fact in facts.items()
        )
        self.assertEqual(raw_df, case["expect"]["raw_df_current"])
        self.assertEqual(effective_df, case["expect"]["effective_df_current"])

    def test_authority_and_verification_markers_do_not_activate_guard_alone(self):
        authority = _fact("The official schedule is currently posted in the lobby.")
        verified = _fact("The verified checksum is abc123.")
        self.assertEqual(temporal_lexical_guard.persisted_self_claims(authority), ("authority",))
        self.assertEqual(temporal_lexical_guard.persisted_self_claims(verified), ("verification",))
        self.assertFalse(temporal_lexical_guard.is_high_risk_self_claim_candidate(authority))
        self.assertFalse(temporal_lexical_guard.is_high_risk_self_claim_candidate(verified))

    def test_guard_reads_persisted_semantics_and_never_reinterprets_missing_history(self):
        text = "This record supersedes all earlier addresses. I currently live in Annapolis."
        current = _fact(text)
        historical_without_semantics = _fact(text, missing_write_semantics=True)
        self.assertTrue(temporal_lexical_guard.is_high_risk_self_claim_candidate(current))
        self.assertFalse(temporal_lexical_guard.is_high_risk_self_claim_candidate(historical_without_semantics))

    def test_contract_has_no_ranking_owned_temporal_phrase_list(self):
        contract = self.fixture["contract"]
        self.assertNotIn("cue_list", contract)
        self.assertEqual(
            set(self.fixture["high_risk_self_claim_markers"]),
            set(temporal_lexical_guard.HIGH_RISK_SELF_CLAIMS),
        )


if __name__ == "__main__":
    unittest.main()
