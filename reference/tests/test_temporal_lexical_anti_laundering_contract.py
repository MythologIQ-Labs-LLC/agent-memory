"""Preimplementation contract for #583 candidate-specific temporal lexical anti-laundering.

This test deliberately does not alter ranking. It proves that the reviewed #583 oracle can
be derived from the already-merged #585 query spans and #598 persisted write semantics.
The runtime implementation must consume this typed evidence rather than recreating a
ranking-owned temporal phrase table.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.runtime import proposition_semantics, ranking_policy  # noqa: E402
from agentmem_ref.runtime.temporal_intent import explicit_intent, interpret_query  # noqa: E402

FIXTURE = ROOT / "reference" / "fixtures" / "runtime" / "temporal-lexical-anti-laundering-v1.json"
_TOKEN = re.compile(r"[a-z0-9]+")
_HIGH_RISK_SELF_CLAIMS = frozenset({"currentness", "instruction", "supersession"})


def _eligible_query_terms(query: str, intent) -> list[str]:
    """Terms whose every query occurrence is a high-confidence consumed span for the resolved mode."""

    if not intent.orders_temporally:
        return []
    eligible_spans = [
        span for span in intent.spans
        if span.mode == intent.mode and span.confidence == "high"
    ]
    if not eligible_spans:
        return []

    occurrences: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for match in _TOKEN.finditer(query.lower()):
        occurrences[match.group(0)].append((match.start(), match.end()))

    eligible = []
    for term, ranges in occurrences.items():
        if all(
            any(span.start <= start and end <= span.end for span in eligible_spans)
            for start, end in ranges
        ):
            eligible.append(term)
    return sorted(eligible)


def _self_claims(text: str) -> list[str]:
    return list(proposition_semantics.interpret_write(text)["markers"].get("self_claims") or ())


def _suppressed_terms(text: str, self_claims: list[str] | None, eligible_terms: list[str]) -> list[str]:
    if not self_claims or not (_HIGH_RISK_SELF_CLAIMS & set(self_claims)):
        return []
    document_terms = set(ranking_policy.relevance_tokens(text))
    return sorted(term for term in eligible_terms if term in document_terms)


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

                eligible = _eligible_query_terms(query, intent)
                self.assertEqual(eligible, expected["eligible_query_terms"])

                candidate = case["candidate"]
                if candidate.get("simulate_missing_write_semantics"):
                    claims = None
                else:
                    claims = _self_claims(candidate["text"])
                    self.assertEqual(claims, expected.get("self_claims", []))

                suppressed = _suppressed_terms(candidate["text"], claims, eligible)
                self.assertEqual(suppressed, expected["suppressed_for_candidate"])

                for term in expected.get("must_remain_lexical", []):
                    self.assertIn(term, ranking_policy.relevance_tokens(query))
                    self.assertNotIn(term, eligible)
                    self.assertNotIn(term, suppressed)

    def test_masked_occurrence_is_removed_from_effective_df_only_for_that_term(self):
        case = next(item for item in self.fixture["cases"] if item["id"] == "H1-suppressed-occurrence-does-not-poison-df")
        intent = interpret_query(case["query"])
        eligible = set(_eligible_query_terms(case["query"], intent))
        self.assertEqual(eligible, {"current"})

        texts = {
            "laundering": case["candidate"]["text"],
            "ordinary": case["ordinary_peer"]["text"],
        }
        masks = {
            "laundering": set(_suppressed_terms(texts["laundering"], _self_claims(texts["laundering"]), sorted(eligible))),
            "ordinary": set(),
        }
        raw_df = sum("current" in set(ranking_policy.relevance_tokens(text)) for text in texts.values())
        effective_df = sum(
            "current" in set(ranking_policy.relevance_tokens(text)) and "current" not in masks[ref]
            for ref, text in texts.items()
        )
        self.assertEqual(raw_df, case["expect"]["raw_df_current"])
        self.assertEqual(effective_df, case["expect"]["effective_df_current"])

    def test_contract_has_no_ranking_owned_temporal_phrase_list(self):
        # The fixture may name expected surface spans in individual cases, but the policy
        # itself is structural: source offsets + confidence + persisted self-claim class.
        contract = self.fixture["contract"]
        self.assertNotIn("cue_list", contract)
        self.assertEqual(
            set(self.fixture["high_risk_self_claim_markers"]),
            _HIGH_RISK_SELF_CLAIMS,
        )


if __name__ == "__main__":
    unittest.main()
