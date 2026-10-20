"""#636 development counterexamples, not an unseen benchmark cohort."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import unittest

from agentmem_ref.evaluation.route_attribution import attribute_returned_routes


class Trap(dict):
    def get(self, key, default=None):
        if key in ("refused_private", "budget_private"):
            raise AssertionError("must not access a nonreturned candidate receipt")
        return super().get(key, default)


def document():
    return {
        "returned": ["identity", "graph", "overlap", "distractor"],
        "admitted": ["identity", "graph", "overlap", "distractor", "budget_private"],
        "candidates": ["identity", "graph", "overlap", "distractor", "budget_private", "refused_private"],
        "admissions": Trap({
            "identity": {"outcome": "admit", "route_provenance": [{"route_id": "exact_identity"}]},
            "graph": {"outcome": "admit", "route_provenance": [{"route_id": "typed_graph"}]},
            "overlap": {"outcome": "admit", "route_provenance": [{"route_id": "lexical"}, {"route_id": "vector"}]},
            "distractor": {"outcome": "admit", "route_provenance": [{"route_id": "lexical"}]},
            "budget_private": {"outcome": "admit", "route_provenance": [{"route_id": "typed_graph"}]},
            "refused_private": {"refusal": "out_of_scope", "route_provenance": []},
        }),
    }


class RouteAttributionTests(unittest.TestCase):
    def test_nonadmitting_receipt_is_rejected_before_attribution(self):
        for outcome in ("block", None, True):
            doc = document()
            doc["admissions"]["identity"]["outcome"] = outcome
            with self.subTest(outcome=outcome), self.assertRaisesRegex(ValueError, "admit"):
                self.score(doc)

    def score(self, doc=None, *, required=None, forbidden=None):
        return attribute_returned_routes(
            doc if doc is not None else document(),
            required_refs=frozenset(required if required is not None else ("identity", "graph", "overlap", "missed")),
            forbidden_refs=frozenset(forbidden if forbidden is not None else ("distractor",)),
        )

    def test_required_vs_forbidden_with_distinct_routes(self):
        report = self.score()
        self.assertEqual((report.returned, report.required_returned, report.required_missing,
                          report.forbidden_returned, report.unlabelled_returned), (4, 3, 1, 1, 0))
        by_route = {entry.route_id: entry for entry in report.routes}
        self.assertEqual((by_route["typed_graph"].required,
                          by_route["typed_graph"].uniquely_required), (1, 1))
        self.assertEqual((by_route["exact_identity"].required,
                          by_route["exact_identity"].uniquely_required), (1, 1))
        self.assertEqual((by_route["lexical"].required,
                          by_route["lexical"].forbidden,
                          by_route["lexical"].shared_required), (1, 1, 1))
        self.assertEqual(by_route["vector"].uniquely_required, 0)

    def test_gold_only_changes_evaluator_not_recall(self):
        doc = document()
        before = repr(doc)
        self.assertNotEqual(self.score(doc, required=("identity",), forbidden=("graph",)),
                            self.score(doc, required=("graph",), forbidden=("identity",)))
        self.assertEqual(repr(doc), before)

    def test_cannot_infer_backend_disabled_counterfactual(self):
        report = self.score()
        self.assertIn("not_counterfactual", report.interpretation)
        self.assertEqual(report.authority_effect, "none")
        self.assertEqual(report.required_missing, 1)
        with self.assertRaises(FrozenInstanceError):
            report.authority_effect = "grant"

    def test_unlabelled_not_conflated_with_forbidden(self):
        report = self.score(required=("identity",), forbidden=())
        self.assertEqual(report.forbidden_returned, 0)
        self.assertEqual(report.unlabelled_returned, 3)

    def test_deduplicates_route_hits_not_facts(self):
        doc = document()
        doc["admissions"]["overlap"]["route_provenance"].append({"route_id": "lexical"})
        self.assertEqual(self.score(doc).routes, self.score().routes)

    def test_refused_and_budget_private_are_never_read(self):
        doc = document()
        report = self.score(doc)
        self.assertEqual(report.returned, 4)
        self.assertNotIn("private", repr(report))

    def test_reports_missing_route_provenance_honestly(self):
        doc = document()
        doc["admissions"]["graph"]["route_provenance"] = []
        report = self.score(doc)
        self.assertEqual(report.unattributed_returned, 1)
        self.assertEqual(report.required_returned, 3)
        self.assertNotIn("typed_graph", [entry.route_id for entry in report.routes])

    def test_invalid_inputs_rejected(self):
        bad = document()
        bad["returned"].append("refused_private")
        with self.assertRaises(ValueError):
            self.score(bad)
        bad = document()
        bad["returned"].append("identity")
        with self.assertRaises(ValueError):
            self.score(bad)
        bad = document()
        bad["admissions"]["identity"]["route_provenance"] = "lexical"
        with self.assertRaises(ValueError):
            self.score(bad)
        with self.assertRaises(ValueError):
            self.score(required=("identity",), forbidden=("identity",))

    def test_empty_return_is_not_success_claim(self):
        doc = {"returned": [], "admitted": ["missed"], "admissions": {}}
        r = self.score(doc)
        self.assertEqual((r.returned, r.required_missing), (0, 4))
        self.assertEqual(r.routes, ())


if __name__ == "__main__":
    unittest.main()
