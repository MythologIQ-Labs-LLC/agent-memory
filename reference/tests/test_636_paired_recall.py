"""Pure #636 paired retrieval evidence checks, not accepted benchmark results."""
import unittest
from dataclasses import FrozenInstanceError, replace

from agentmem_ref.evaluation.paired_recall import (
    RunIdentity, CaseLabels, compare_public_profiles,
)


def run(profile="baseline", **changes):
    initial = RunIdentity(profile, "abc123", "corpus:sha", "queries:sha", "labels:sha", "harness:sha", "scope:sha", "query:1", "input:sha", 3)
    return replace(initial, **changes)


def recall(*refs):
    return {
        "returned": list(refs),
        "admitted": list(refs),
        "admissions": {ref: {"route_provenance": [{"route_id": "lexical"}]} for ref in refs},
        "candidates": list(refs) + ["refused_private"],
    }


class Trap(dict):
    def get(self, key, default=None):
        if key == "refused_private":
            raise AssertionError("private candidate receipt read")
        return super().get(key, default)


class PairedPublicRecallTests(unittest.TestCase):
    def compare(self, a, b, needed=("needed",), forbidden=("noise",), **kwargs):
        return compare_public_profiles(a, b,
            original_run=kwargs.get("left", run()),
            candidate_run=kwargs.get("right", run("candidate")),
            labels=kwargs.get("labels", CaseLabels(frozenset(needed), frozenset(forbidden))))

    def test_selective_gain_preserves_evidence(self):
        p = self.compare(recall("needed", "noise"), recall("needed"))
        self.assertEqual((p.required_lost, p.forbidden_removed, p.forbidden_newly_returned), (0, 1, 0))
        self.assertFalse(p.regression)
        self.assertTrue(p.candidate.evidence_success)

    def test_loss_of_required_evidence_vetoes_precise_candidate(self):
        p = self.compare(recall("needed", "noise"), recall())
        self.assertEqual(p.required_lost, 1)
        self.assertEqual(p.candidate.required_missing, 1)
        self.assertTrue(p.regression)

    def test_new_forbidden_return_is_regression(self):
        p = self.compare(recall("needed"), recall("needed", "noise"))
        self.assertEqual(p.forbidden_newly_returned, 1)
        self.assertTrue(p.regression)

    def test_unlabelled_is_not_inferred_forbidden(self):
        p = self.compare(recall("needed", "uncertain"), recall("needed"))
        self.assertFalse(p.regression)
        self.assertEqual(p.original.unlabelled_returned, 1)
        self.assertEqual(p.forbidden_removed, 0)

    def test_no_answer_is_not_implied_to_be_downstream_abstention(self):
        gold = CaseLabels(frozenset(), frozenset(), no_safe_answer=True)
        p = self.compare(recall("unknown"), recall(), labels=gold)
        self.assertIs(p.candidate.no_answer_context_empty, True)
        self.assertFalse(p.candidate.evidence_success)
        self.assertIn("not_answer_quality", p.interpretation)
        q = self.compare(recall(), recall("unknown"), labels=gold)
        self.assertTrue(q.regression)

    def test_incomparable_corpus_labels_scope_and_budget_rejected(self):
        for field, value in (
            ("corpus_digest", "different"), ("questions_digest", "different"),
            ("labels_digest", "different"), ("harness_digest", "different"),
            ("scope_digest", "different"), ("case_ref", "different"),
            ("case_input_digest", "different"), ("budget_k", 2),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                self.compare(recall("needed"), recall("needed"), right=run("x", **{field: value}))

    def test_public_admission_and_budget_checked(self):
        d = recall("needed")
        d["returned"].append("hidden")
        with self.assertRaisesRegex(ValueError, "admission"):
            self.compare(d, recall("needed"))
        d = recall("a", "b", "c", "d")
        with self.assertRaisesRegex(ValueError, "budget"):
            self.compare(d, recall())

    def test_private_candidates_not_observed(self):
        d = recall("needed")
        d["admissions"] = Trap(d["admissions"])
        before = repr(d)
        p = self.compare(d, recall("needed"))
        self.assertFalse(p.regression)
        self.assertEqual(before, repr(d))

    def test_missing_receipt_duplicate_and_bad_labels_rejected(self):
        d = recall("needed")
        d["admissions"] = {}
        with self.assertRaisesRegex(ValueError, "admission receipt"):
            self.compare(d, recall())
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.compare(recall("needed", "needed"), recall())
        with self.assertRaisesRegex(ValueError, "disjoint"):
            CaseLabels(frozenset({"needed"}), frozenset({"needed"}))
        with self.assertRaisesRegex(ValueError, "no-safe-answer"):
            CaseLabels(frozenset({"needed"}), frozenset(), True)

    def test_deterministic_and_immutable(self):
        a, b = recall("needed", "noise"), recall("needed")
        p = self.compare(a, b)
        self.assertEqual(p, self.compare(a, b))
        self.assertEqual(p.authority_effect, "none")
        with self.assertRaises(FrozenInstanceError):
            p.regression = False


if __name__ == "__main__":
    unittest.main()
