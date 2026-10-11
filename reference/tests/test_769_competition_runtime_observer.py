"""#769: integration gates for opt-in, non-authoritative competition diagnostics.

Fresh project-local cases. The prior #769 fixture remains independent and
unchanged. This suite does not qualify positive stopping or publication.
"""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from unittest.mock import patch
from pathlib import Path

from agentmem_ref.recall_control import (
    ControlledRecallPlanner, RecallControlPlan, RecallRouteBudget,
)
from agentmem_ref.runtime import typed_proposition as typed
from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed
from agentmem_ref.runtime.runtime_composition import (
    ConfiguredCompositionRuntime, LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE,
    SHARED_EVIDENCE_ROUTE,
)
from tests.test_recall_control import _plan, _proposal, _context, TENANT, PROJECT, _FixedController


def _typed(subject, attribute, value):
    validated = typed.validate({
        "subject": subject, "attribute": attribute, "value": value,
        "assertion": "state", "cardinality": "single", "flags": {},
    })
    return {"typed_proposition": typed.typed_record(validated, typed.CALLER_DECLARED)}


class CompetitionRuntimeObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = ConfiguredCompositionRuntime.create(
            Path(self.temp.name), tenant=TENANT, plan=_plan(),
        )
        self.planner = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=_FixedController(RecallControlPlan(
                controller_ref="test:769", controller_version="1",
                route_budgets=(
                    RecallRouteBudget(LEXICAL_ROUTE, 20),
                    RecallRouteBudget(EXACT_IDENTITY_ROUTE, 0),
                    RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0),
                ),
            )),
        )
        self.need = CoverageNeed(typed.typed_slot("Aster service", "endpoint"))

    def tearDown(self):
        self.temp.cleanup()

    def retain(self, name, text, *, typed_write=None, project_ref=PROJECT):
        args = {"typed_write": typed_write} if typed_write is not None else {}
        out = self.runtime.retain(
            _proposal(name, evidence_refs=("session:" + name,), project_ref=project_ref),
            text, **args,
        )
        self.assertTrue(out.committed)
        return out.fact_uuid

    def observe(self):
        result = self.planner.recall("Aster service endpoint", _context())
        return result, self.planner.observe_competition_diagnostic(
            result, _context(), needs=(self.need,),
        )

    def test_typed_coverage_with_no_competitor_is_still_unattested(self):
        self.retain("memory:typed", "Aster service endpoint is /health",
                    typed_write=_typed("Aster service", "endpoint", "/health"))
        result, diagnostic = self.observe()
        self.assertEqual(diagnostic.diagnosis, "scope_enumeration_unattested")
        self.assertEqual(diagnostic.admitted_untyped_count, 0)
        self.assertTrue(diagnostic.typed_coverage_observed)
        self.assertFalse(diagnostic.complete_enumeration_attested)
        self.assertEqual(diagnostic.stop_recommendation, "abstain")
        self.assertEqual(diagnostic.authority_effect, "none")
        self.assertEqual(result.ranked_admitted, result.recall.ranked_admitted)

    def test_current_visible_untyped_fact_is_presence_not_proven_conflict(self):
        self.retain("memory:typed", "Aster service endpoint is /health",
                    typed_write=_typed("Aster service", "endpoint", "/health"))
        self.retain("memory:untyped", "Aster service endpoint detail is undocumented")
        _, diagnostic = self.observe()
        self.assertEqual(diagnostic.diagnosis, "untyped_admitted_candidates_observed")
        self.assertGreaterEqual(diagnostic.admitted_untyped_count, 1)
        self.assertEqual(diagnostic.untyped_relation_status, "identity_unverified")
        projection = diagnostic.to_dict()
        self.assertFalse({"candidate_refs", "raw_text", "fact_uuid", "tenant"} & set(projection))
        self.assertTrue(projection["admitted_untyped_count"] >= 1)

    def test_verified_typed_competing_values_are_unresolved_not_superseded(self):
        self.retain("memory:alice", "Aster service endpoint is /v1",
                    typed_write=_typed("Aster service", "endpoint", "/v1"))
        self.retain("memory:bob", "Aster service endpoint is /v2",
                    typed_write=_typed("Aster service", "endpoint", "/v2"))
        _, diagnostic = self.observe()
        self.assertEqual(diagnostic.diagnosis, "typed_values_unresolved")
        self.assertFalse(diagnostic.complete_enumeration_attested)
        self.assertEqual(diagnostic.stop_recommendation, "abstain")

    def test_tampered_result_fail_closed_before_any_fact_reads(self):
        self.retain("memory:typed", "Aster service endpoint is /health",
                    typed_write=_typed("Aster service", "endpoint", "/health"))
        result = self.planner.recall("Aster service endpoint", _context())
        result.recall.admitted.clear()
        diagnostic = self.planner.observe_competition_diagnostic(
            result, _context(), needs=(self.need,),
        )
        self.assertEqual(diagnostic.diagnosis, "recall_observation_unverified")
        self.assertEqual(diagnostic.admitted_untyped_count, 0)
        self.assertFalse(diagnostic.typed_coverage_observed)
        self.assertEqual(diagnostic.stop_recommendation, "abstain")

    def test_reader_context_must_match_receipt_before_lookup(self):
        self.retain("memory:typed", "Aster service endpoint is /health",
                    typed_write=_typed("Aster service", "endpoint", "/health"))
        result = self.planner.recall("Aster service endpoint", _context())
        contexts = (
            replace(_context(), project_ref="project-other"),
            replace(_context(), principal_ref="agent:other"),
            replace(_context(), purpose="other-purpose"),
            replace(_context(), target_domain_refs=(TENANT, "project-other")),
        )
        for invalid_context in contexts:
            with self.subTest(context=invalid_context):
                with patch.object(self.runtime.adapter, "current_governed_typed_claim",
                                  side_effect=AssertionError("no lookup after context mismatch")):
                    out = self.planner.observe_competition_diagnostic(
                        result, invalid_context, needs=(self.need,),
                    )
                self.assertEqual(out.diagnosis, "recall_observation_unverified")
                self.assertEqual(out.admitted_untyped_count, 0)
                self.assertFalse(out.typed_coverage_observed)

    def test_hidden_project_memory_does_not_enter_visible_admitted_count(self):
        self.retain("memory:typed", "Aster service endpoint is /health",
                    typed_write=_typed("Aster service", "endpoint", "/health"))
        _, before = self.observe()
        self.retain("memory:foreign", "Aster service endpoint is hidden",
                    project_ref="project-other")
        _, after = self.observe()
        self.assertEqual(before.to_dict(), after.to_dict())

    def test_no_coverage_does_not_imply_empty_competition(self):
        self.retain("memory:untyped", "Aster service endpoint currently unknown")
        _, diagnostic = self.observe()
        self.assertFalse(diagnostic.typed_coverage_observed)
        self.assertEqual(diagnostic.diagnosis, "untyped_admitted_candidates_observed")
        self.assertEqual(diagnostic.stop_recommendation, "abstain")

    def test_observer_is_opt_in_and_default_recall_never_calls_it(self):
        self.retain("memory:typed", "Aster service endpoint is /health",
                    typed_write=_typed("Aster service", "endpoint", "/health"))
        with patch.object(ControlledRecallPlanner, "observe_competition_diagnostic",
                          side_effect=AssertionError("observer used without opting in")):
            result = self.planner.recall("Aster service endpoint", _context())
        self.assertTrue(result.observation_unchanged())
        self.assertGreaterEqual(len(result.admitted), 1)

    def test_never_mutates_original_recall_membership(self):
        self.retain("memory:typed", "Aster service endpoint is /health",
                    typed_write=_typed("Aster service", "endpoint", "/health"))
        result = self.planner.recall("Aster service endpoint", _context())
        before = (list(result.admitted), list(result.ranked_admitted),
                  dict(result.recall.refusals), result.observation_receipt)
        self.planner.observe_competition_diagnostic(
            result, _context(), needs=(self.need,),
        )
        after = (list(result.admitted), list(result.ranked_admitted),
                 dict(result.recall.refusals), result.observation_receipt)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
