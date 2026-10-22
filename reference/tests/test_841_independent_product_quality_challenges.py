"""Independent developmental counterexamples for PR #841 policy 0.3.1.

These are *not* unseen benchmark/holdout cases or acceptance-lane evidence.
They exercise the selector's plain Python API without runtime, private data or
benchmarks. Commit on a review branch, not on Claude's active implementation.

Expected RED at the branch base; a change cannot be accepted by weakening
the required-evidence assertions or by admitting benchmark-specific words.
"""
from __future__ import annotations

import unittest

from agentmem_ref.api import context_selection


LEXICAL_ONLY = {
    "route_provenance": [{"route_id": "lexical"}],
    "admission_basis": {"currentness": "current_state"},
}


class MeaningPreservation(unittest.TestCase):
    def test_paraphrased_single_statement_family_relationship_is_not_proven_irrelevant(self):
        # A natural paraphrase of BOTH the subject relation and the predicate.
        # The fact is the required answer. Lack of a literal attribute token
        # cannot prove irrelevance when there is no verified relationship parser.
        verdict = context_selection.qualify(
            "Which instrument does Mara's child play?",
            "ref-family-instrument",
            LEXICAL_ONLY,
            "Mara's eldest performs on the cello.",
            None,
        )
        self.assertEqual(verdict["outcome"], "delivered", verdict)
        self.assertNotEqual(verdict.get("certainty"), "grounded", verdict)

    def test_paraphrased_single_statement_residence_is_not_proven_irrelevant(self):
        verdict = context_selection.qualify(
            "Where does Liora's brother live?",
            "ref-residence",
            LEXICAL_ONLY,
            "Liora's sibling resides in Oslo.",
            None,
        )
        self.assertEqual(verdict["outcome"], "delivered", verdict)
        self.assertNotEqual(verdict.get("certainty"), "grounded", verdict)

    def test_only_unresolved_content_must_not_claim_no_relevant_evidence(self):
        # The admission layer can return a fact whose content resolution then
        # fails. That is insufficient data, not an evidence-qualified negative.
        record = {"fact_ref": "ref-unreadable", "outcome": "unavailable", "state": "unresolved"}
        assessment = context_selection.assessment([record])
        self.assertNotEqual(assessment, "no_relevant_evidence", assessment)
        self.assertNotEqual(assessment, "no_returned_candidates", assessment)

    def test_only_budget_omitted_content_must_not_claim_no_relevant_evidence(self):
        # An authorized returned fact might contain the needed answer but be
        # unavailable for selection solely because its delivery budget ran out.
        record = {"fact_ref": "ref-unseen", "outcome": "unavailable", "state": "omitted_budget"}
        assessment = context_selection.assessment([record])
        self.assertNotEqual(assessment, "no_relevant_evidence", assessment)
        self.assertNotEqual(assessment, "no_returned_candidates", assessment)


if __name__ == "__main__":
    unittest.main()
