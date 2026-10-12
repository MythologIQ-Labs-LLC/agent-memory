"""#769 independent adversarial validation of the opt-in competition observer.

Authored by the cloud adversarial review, not by the candidate author. Every
case drives the real SQLite-backed ConfiguredCompositionRuntime and the real
ControlledRecallPlanner; none re-implements the candidate's helper logic.

``DefectRegressions`` were committed failing against candidate
9bbca2a4b01b60ec31da5d3148e02fe56032a6d7 before any repair.
"""
from __future__ import annotations

import dataclasses
import random
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agentmem_ref import policy
from agentmem_ref.recall_control import (
    ControlledRecallPlanner, RecallControlPlan, RecallRouteBudget,
)
from agentmem_ref.runtime import recall_observation_receipt as receipts
from agentmem_ref.runtime import typed_proposition as typed
from agentmem_ref.runtime.adapter import RecallContext
from agentmem_ref.runtime.competition_diagnostics import CompetitionDiagnostic
from agentmem_ref.runtime.evidence_sufficiency import CoverageNeed
from agentmem_ref.runtime.runtime_composition import (
    ConfiguredCompositionRuntime, LEXICAL_ROUTE, EXACT_IDENTITY_ROUTE,
    SHARED_EVIDENCE_ROUTE,
)
from tests.test_recall_control import _plan, _proposal, _context, TENANT, PROJECT, _FixedController

QUERY = "Aster service endpoint"
NEED = CoverageNeed(typed.typed_slot("Aster service", "endpoint"))
SECRET_PROJECT = "project-secret"
PROJECTION_KEYS = {
    "version", "diagnosis", "receipt_state", "scope_enumeration",
    "complete_enumeration_attested", "admitted_untyped_count",
    "untyped_relation_status", "typed_coverage_observed",
    "typed_value_statuses", "stop_recommendation", "authority_effect",
}


def _typed(subject, attribute, value, *, cardinality="single", **flags):
    validated = typed.validate({
        "subject": subject, "attribute": attribute, "value": value,
        "assertion": "state", "cardinality": cardinality, "flags": flags,
    })
    return {"typed_proposition": typed.typed_record(validated, typed.CALLER_DECLARED)}


def _deletion(target: str) -> policy.Proposal:
    return replace(
        _proposal(target, evidence_refs=("evidence:prune",)),
        proposal_id=f"prune:{target}", operation="pruning", target_class=policy.M1,
        proposed_strength="tentative", review_satisfied=True,
        approval_refs=("approver:fixture",),
    )


class _Store:
    """One isolated durable store plus its planner."""

    def __init__(self, testcase: unittest.TestCase, *, tenant: str = TENANT, limit: int = 20):
        temp = tempfile.TemporaryDirectory()
        testcase.addCleanup(temp.cleanup)
        self.runtime = ConfiguredCompositionRuntime.create(Path(temp.name), tenant=tenant, plan=_plan())
        self.planner = ControlledRecallPlanner(
            self.runtime.adapter,
            controller=_FixedController(RecallControlPlan(
                controller_ref="test:769-adversarial", controller_version="1",
                route_budgets=(
                    RecallRouteBudget(LEXICAL_ROUTE, limit),
                    RecallRouteBudget(EXACT_IDENTITY_ROUTE, 0),
                    RecallRouteBudget(SHARED_EVIDENCE_ROUTE, 0),
                ),
            )),
        )
        self.testcase = testcase

    def retain(self, name, text, *, typed_write=None, project_ref=PROJECT):
        args = {"typed_write": typed_write} if typed_write is not None else {}
        out = self.runtime.retain(
            _proposal(name, evidence_refs=("session:" + name,), project_ref=project_ref),
            text, **args,
        )
        self.testcase.assertTrue(out.committed)
        return out.fact_uuid

    def delete(self, name):
        out = self.runtime.delete_current(_deletion(name))
        self.testcase.assertTrue(out.committed)

    def recall(self, context=None):
        return self.planner.recall(QUERY, context or _context())

    def observe(self, result, context=None, planner=None) -> CompetitionDiagnostic:
        return (planner or self.planner).observe_competition_diagnostic(
            result, context or _context(), needs=(NEED,),
        )


def _forge(result, admitted_extra: tuple[str, ...], context: RecallContext):
    """Build a self-consistent receipt with only the public capture helper."""
    receipt = result.observation_receipt
    recall = result.recall
    for ref in admitted_extra:
        recall.candidates.append(ref)
        recall.admitted.append(ref)
        recall.ranked_admitted.append(ref)
    forged = receipts.capture_recall_observation(
        query=recall.query, reader_domain_refs=tuple(context.target_domain_refs),
        principal_ref=context.principal_ref, project_ref=context.project_ref,
        purpose=context.purpose, task_ref=context.task_ref,
        controller_ref=receipt.controller_ref, admission_policy=receipt.admission_policy,
        admission_mode=receipt.admission_mode, evaluated_at=receipt.evaluated_at,
        candidates=list(recall.candidates), admitted=list(recall.admitted),
        ranked=list(recall.ranked_admitted), route_observations=receipt.routes,
        observed_route_counts=dict(result.route_candidate_counts),
        plan=result.plan.to_dict(), refusals=dict(recall.refusals),
    )
    return replace(result, observation_receipt=forged)


class DefectRegressions(unittest.TestCase):
    """Each case failed on the unrepaired candidate."""

    def test_context_object_cannot_widen_reader_authority_after_receipt_check(self):
        # D1: the receipt check reads the context once; the governed reads
        # read it again. A RecallContext subclass answering differently on the
        # second read let a hidden project's memory change the diagnosis.
        store = _Store(self)
        store.retain("memory:typed", "Aster service endpoint is /health",
                     typed_write=_typed("Aster service", "endpoint", "/health"))
        store.retain("memory:hidden", "Aster service endpoint is /secret",
                     typed_write=_typed("Aster service", "endpoint", "/secret"),
                     project_ref=SECRET_PROJECT)
        result = store.recall()
        baseline = store.observe(result).to_dict()
        reads = {"target_domain_refs": 0, "project_ref": 0}

        @dataclasses.dataclass(frozen=True)
        class ShiftingContext(RecallContext):
            def __getattribute__(self, name):
                if name in reads:
                    reads[name] += 1
                    if reads[name] > 1:
                        return ((TENANT, PROJECT, SECRET_PROJECT)
                                if name == "target_domain_refs" else SECRET_PROJECT)
                return object.__getattribute__(self, name)

        shifting = ShiftingContext(
            target_domain_refs=(TENANT, PROJECT), principal_ref=_context().principal_ref,
            project_ref=PROJECT, purpose=_context().purpose,
        )
        out = store.observe(result, shifting).to_dict()
        self.assertIn(out, (baseline, store.observe(result, replace(_context(), purpose="x")).to_dict()))
        self.assertNotEqual(out["diagnosis"], "typed_slot_obstacles_observed")

    def test_forged_receipt_from_public_helper_is_not_a_receipt_match(self):
        # D2a: the receipt is an unkeyed digest; any caller can recompute it
        # for refs the planner never returned for this query.
        store = _Store(self)
        store.retain("memory:typed", "Aster service endpoint is /health",
                     typed_write=_typed("Aster service", "endpoint", "/health"))
        unrelated = store.retain("memory:unrelated", "Weather in Lisbon is warm")
        result = store.recall()
        self.assertNotIn(unrelated, result.admitted)
        forged = _forge(result, (unrelated,), _context())
        self.assertTrue(forged.observation_unchanged())  # digest alone cannot tell
        out = store.observe(forged)
        self.assertEqual(out.diagnosis, "recall_observation_unverified")
        self.assertEqual(out.admitted_untyped_count, 0)

    def test_cross_store_replay_with_colliding_identifiers_is_unverified(self):
        # D2b: identifiers are deterministic per store (ref-0004, ...), so a
        # result issued by store A names unrelated facts in store B.
        a, b = _Store(self), _Store(self)
        a.retain("memory:a", "Aster service endpoint is /a",
                 typed_write=_typed("Aster service", "endpoint", "/a"))
        result_a = a.recall()
        collided = b.retain("memory:b-unrelated", "Weather in Lisbon is warm")
        b.retain("memory:b", "Aster service endpoint is /b",
                 typed_write=_typed("Aster service", "endpoint", "/b"))
        self.assertEqual(result_a.admitted, [collided])
        out = b.observe(result_a)
        self.assertEqual(out.diagnosis, "recall_observation_unverified")
        self.assertEqual(out.receipt_state, "unverified")
        self.assertEqual(out.admitted_untyped_count, 0)

    def test_governed_deletion_after_recall_is_stale_not_a_cleaner_diagnosis(self):
        # D4 (frozen contract C16): a stale observation must be integrity
        # unknown. Deleting an admitted competitor previously turned
        # typed_values_unresolved into scope_enumeration_unattested while
        # still reporting a receipt match.
        store = _Store(self)
        store.retain("memory:v1", "Aster service endpoint is /v1",
                     typed_write=_typed("Aster service", "endpoint", "/v1"))
        store.retain("memory:v2", "Aster service endpoint is /v2",
                     typed_write=_typed("Aster service", "endpoint", "/v2"))
        result = store.recall()
        self.assertEqual(store.observe(result).diagnosis, "typed_values_unresolved")
        store.delete("memory:v2")
        out = store.observe(result)
        self.assertEqual(out.diagnosis, "recall_observation_unverified")
        self.assertEqual(out.typed_value_statuses, ())
        self.assertEqual(out.admitted_untyped_count, 0)


class AdversarialNonRegressions(unittest.TestCase):
    """Behaviour outside the authored fixtures that already held on the candidate."""

    def test_task_ref_substitution_is_rejected_before_reads(self):
        store = _Store(self)
        store.retain("memory:typed", "Aster service endpoint is /health",
                     typed_write=_typed("Aster service", "endpoint", "/health"))
        result = store.recall()
        out = store.observe(result, replace(_context(), task_ref="task-other"))
        self.assertEqual(out.diagnosis, "recall_observation_unverified")

    def test_domain_order_is_not_authority(self):
        store = _Store(self)
        store.retain("memory:typed", "Aster service endpoint is /health",
                     typed_write=_typed("Aster service", "endpoint", "/health"))
        result = store.recall()
        swapped = replace(_context(), target_domain_refs=(PROJECT, TENANT))
        self.assertEqual(store.observe(result, swapped).to_dict(), store.observe(result).to_dict())

    def test_hidden_memories_never_change_the_projection_metamorphic(self):
        # Seeded metamorphic property: for random visible corpora, adding any
        # mix of hidden memories (foreign project, deleted, disputed, foreign
        # tenant written to the same substrate) leaves the projection identical.
        rng = random.Random(769)
        values = ("/v1", "/v2", "/health", "/V1", "/v1 ")
        for trial in range(6):
            with self.subTest(trial=trial):
                plain, noisy = _Store(self), _Store(self)
                visible = [(f"memory:vis{i}", rng.choice(values), rng.random() < 0.6)
                           for i in range(rng.randint(1, 4))]
                hidden = [rng.choice(("project", "deleted", "disputed", "foreign"))
                          for _ in range(rng.randint(1, 5))]
                for store in (plain, noisy):
                    for name, value, is_typed in visible:
                        store.retain(
                            name, f"Aster service endpoint is {value}",
                            typed_write=(_typed("Aster service", "endpoint", value) if is_typed else None),
                        )
                for j, kind in enumerate(hidden):
                    name = f"memory:hidden{j}"
                    text = f"Aster service endpoint is /hidden{j}"
                    typed_write = _typed("Aster service", "endpoint", f"/hidden{j}")
                    if kind == "project":
                        noisy.retain(name, text, typed_write=typed_write, project_ref=SECRET_PROJECT)
                    elif kind == "deleted":
                        noisy.retain(name, text, typed_write=typed_write)
                        noisy.delete(name)
                    elif kind == "disputed":
                        uuid = noisy.retain(name, text, typed_write=typed_write)
                        # Durable adapters forbid mark_disputed(); inject the
                        # committed-dispute admission state directly.
                        noisy.runtime.adapter._disputed.add(uuid)
                    else:
                        _write_foreign_tenant_fact(noisy, name, text)
                plain_out = plain.observe(plain.recall()).to_dict()
                noisy_out = noisy.observe(noisy.recall()).to_dict()
                self.assertEqual(plain_out, noisy_out, (visible, hidden))

    def test_lexical_twin_is_untyped_presence_not_typed_conflict(self):
        store = _Store(self)
        store.retain("memory:v1", "Aster service endpoint is /v1",
                     typed_write=_typed("Aster service", "endpoint", "/v1"))
        store.retain("memory:twin", "Aster service endpoint is /v2")
        out = store.observe(store.recall())
        self.assertEqual(out.typed_value_statuses, ("same_value_observed",))
        self.assertEqual(out.diagnosis, "untyped_admitted_candidates_observed")
        self.assertEqual(out.untyped_relation_status, "identity_unverified")

    def test_lexically_similar_but_different_typed_slot_is_not_a_competitor(self):
        store = _Store(self)
        store.retain("memory:v1", "Aster service endpoint is /v1",
                     typed_write=_typed("Aster service", "endpoint", "/v1"))
        store.retain("memory:near", "Aster services endpoint is /v9",
                     typed_write=_typed("Aster services", "endpoint", "/v9"))
        out = store.observe(store.recall())
        self.assertEqual(out.typed_value_statuses, ("same_value_observed",))
        self.assertEqual(out.admitted_untyped_count, 0)

    def test_pipe_ambiguous_slots_cannot_be_requested(self):
        # typed_slot("a|b", "c") == typed_slot("a", "b|c"); the observer must
        # refuse such needs rather than merge two propositions.
        self.assertEqual(typed.typed_slot("Aster|service", "endpoint"),
                         typed.typed_slot("Aster", "service|endpoint"))
        store = _Store(self)
        store.retain("memory:p1", "Aster service endpoint is /p1",
                     typed_write=_typed("Aster|service", "endpoint", "/p1"))
        result = store.recall()
        with self.assertRaises(ValueError):
            store.planner.observe_competition_diagnostic(
                result, _context(),
                needs=(CoverageNeed(typed.typed_slot("Aster|service", "endpoint")),),
            )

    def test_truncated_route_budget_never_attests_or_stops(self):
        store = _Store(self, limit=1)
        for i in range(6):
            store.retain(f"memory:v{i}", f"Aster service endpoint is /v{i}",
                         typed_write=_typed("Aster service", "endpoint", f"/v{i}"))
        out = store.observe(store.recall())
        self.assertFalse(out.complete_enumeration_attested)
        self.assertEqual(out.stop_recommendation, "abstain")
        self.assertEqual(out.authority_effect, "none")
        self.assertEqual(out.diagnosis, "typed_slot_obstacles_observed")

    def test_projection_is_closed_and_never_echoes_identities_or_text(self):
        store = _Store(self)
        refs = [store.retain("memory:v1", "Aster service endpoint is /v1",
                             typed_write=_typed("Aster service", "endpoint", "/v1")),
                store.retain("memory:u", "Aster service endpoint unknown")]
        out = store.observe(store.recall()).to_dict()
        self.assertEqual(set(out), PROJECTION_KEYS)
        flat = repr(out)
        for secret in (*refs, "/v1", "Aster", TENANT, PROJECT, "agent:recall-control-test"):
            self.assertNotIn(secret, flat)

    def test_authoritative_diagnostic_cannot_be_constructed(self):
        base = dict(diagnosis="scope_enumeration_unattested", receipt_state="mutable_receipt_match",
                    admitted_untyped_count=0, typed_coverage_observed=True,
                    typed_value_statuses=(), untyped_relation_status="none_seen")
        for override in ({"stop_recommendation": "stop"}, {"authority_effect": "stop"},
                         {"complete_enumeration_attested": True},
                         {"scope_enumeration": "attested_complete"},
                         {"admitted_untyped_count": True}, {"admitted_untyped_count": -1}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                CompetitionDiagnostic(**{**base, **override})

    def test_default_recall_is_identical_whether_or_not_observer_ran(self):
        observed, untouched = _Store(self), _Store(self)
        script = [
            ("memory:v1", "Aster service endpoint is /v1", _typed("Aster service", "endpoint", "/v1")),
            ("memory:u", "Aster service endpoint detail is undocumented", None),
            ("memory:v2", "Aster service endpoint is /v2", _typed("Aster service", "endpoint", "/v2")),
        ]
        for name, text, typed_write in script:
            outs = []
            for store in (observed, untouched):
                store.retain(name, text, typed_write=typed_write)
                result = store.recall()
                outs.append((list(result.admitted), list(result.ranked_admitted),
                             dict(result.recall.refusals), result.observation_receipt.content_digest,
                             result.stop_reason, dict(result.route_candidate_counts)))
                if store is observed:
                    store.observe(result)
            self.assertEqual(outs[0], outs[1])


def _write_foreign_tenant_fact(store: _Store, name: str, text: str) -> None:
    """Write through a second adapter tenant sharing the same substrate."""
    from agentmem_ref.runtime.adapter import GovernedMemoryAdapter
    foreign_tenant = "tenant-foreign"
    adapter = GovernedMemoryAdapter(store.runtime.adapter.checkpoint_substrate(), tenant=foreign_tenant)
    proposal = replace(
        _proposal(name, evidence_refs=("session:" + name,)),
        scope=foreign_tenant, tenant_ref=foreign_tenant,
        isolation_domain_refs=(foreign_tenant, PROJECT),
        required_isolation_domain_refs=(PROJECT,),
    )
    out = adapter.commit_proposal(proposal, text)
    store.testcase.assertTrue(out.committed, out)


if __name__ == "__main__":
    unittest.main()
