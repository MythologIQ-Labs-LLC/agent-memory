"""#775 public-recall probe safety tests. No runtime selector is enabled."""
from __future__ import annotations

import unittest

from agentmem_ref.evaluation.subject_relevance_challenge import ChallengeInput
from agentmem_ref.evaluation.public_recall_relevance_probe import inspect_returned


def document():
    return {
        "returned": ["allowed"],
        "admitted": ["allowed", "budget_withheld"],
        "candidates": ["allowed", "budget_withheld", "scope_refused"],
        "admissions": {
            "allowed": {"rank_position": 1, "route_provenance": [
                {"route_id": "lexical", "raw_score": 1.0},
                {"route_id": "shared_evidence_neighbor", "raw_score": 0.9},
            ]},
            "budget_withheld": {"rank_position": 2, "route_provenance": [
                {"route_id": "lexical", "raw_score": 0.5}]},
            "scope_refused": {"refusal": "out_of_scope", "route_provenance": []},
        },
    }


class RefusingPrivateMap(dict):
    def get(self, key, default=None):
        if key in {"budget_withheld", "scope_refused"}:
            raise AssertionError("attempted to access nonreturned content")
        return super().get(key, default)


class PublicRecallRelevanceTests(unittest.TestCase):
    def test_only_returned_admitted_uses_content(self):
        d = document()
        contents = RefusingPrivateMap({
            "allowed": "Mara owns the codebase.",
            "budget_withheld": "private information",
            "scope_refused": "foreign project content",
        })
        notes = RefusingPrivateMap({
            "allowed": ChallengeInput("Who maintains the repository?", "",
                ("subject:repo",), ("subject:repo",), identity_binding_checked=True),
            "scope_refused": ChallengeInput("query", "private"),
        })
        original = repr(d)
        result = inspect_returned(d, contents, notes)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].fact_ref, "allowed")
        self.assertEqual(result[0].route_ids,
                         ("lexical", "shared_evidence_neighbor"))
        self.assertFalse(result[0].relevance.lexical_overlap)
        self.assertEqual(result[0].relevance.structured_signal, "direct_subject_claim")
        self.assertFalse(result[0].relevance.may_withhold_content)
        self.assertEqual(repr(d), original)

    def test_unresolved_content_returns_no_text(self):
        result = inspect_returned(document(), {}, {})
        self.assertEqual(result[0].status, "unresolved")
        self.assertIsNone(result[0].relevance)
        self.assertNotIn("content", repr(result))

    def test_cannot_inspect_refused_or_budget_withheld_ids(self):
        d = document()
        d["returned"].append("scope_refused")
        with self.assertRaisesRegex(ValueError, "not admitted"):
            inspect_returned(d, {}, {})
        d = document()
        d["returned"].append("budget_withheld")
        result = inspect_returned(d, {}, {})
        self.assertEqual(result[-1].fact_ref, "budget_withheld")
        self.assertEqual(result[-1].status, "unresolved")

    def test_duplicate_returned_ids_rejected(self):
        d = document()
        d["returned"].append("allowed")
        with self.assertRaisesRegex(ValueError, "unique"):
            inspect_returned(d, {}, {})

    def test_missing_admission_receipt_rejected(self):
        d = document()
        del d["admissions"]["allowed"]
        with self.assertRaisesRegex(ValueError, "admission receipt"):
            inspect_returned(d, {}, {})

    def test_observation_is_deterministic_and_claims_not_authority(self):
        d = document()
        notes = {"allowed": ChallengeInput(
            "Deployment date", "outdated", ("subject:a",), ("subject:b",),
            identity_binding_checked=True)}
        items = {"allowed": "The deployment date was Friday."}
        first = inspect_returned(d, items, notes)
        self.assertEqual(first, inspect_returned(d, items, notes))
        self.assertEqual(first[0].relevance.structured_signal, "different_subject_claim")
        self.assertEqual(first[0].authority_effect, "none")
        self.assertFalse(first[0].relevance.may_withhold_content)

    def test_invalid_public_envelope_fails_closed(self):
        for mutation in (
            lambda d: d.update(returned="allowed"),
            lambda d: d.update(admitted="allowed"),
            lambda d: d.update(admissions=[]),
            lambda d: d.update(returned=[None]),
        ):
            d = document()
            mutation(d)
            with self.subTest(d=d), self.assertRaises(ValueError):
                inspect_returned(d, {}, {})


if __name__ == "__main__":
    unittest.main()
