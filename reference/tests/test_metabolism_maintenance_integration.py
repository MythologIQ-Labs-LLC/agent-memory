from __future__ import annotations

import unittest

from agentmem_ref import policy, receipts
from agentmem_ref.adapter import Clock, GovernedMemoryAdapter, RecallContext
from agentmem_ref.maintenance_run import (
    MetabolismMaintenanceContext,
    bind_metabolism_plan,
    plan_metabolism_maintenance,
    validate_run,
)
from agentmem_ref.metabolism import (
    ConsolidationSource,
    MetabolismConfig,
    MetabolismSnapshot,
    NativeMetabolismEstimator,
    ReinforcementObservation,
    RetentionConstraints,
    propose_consolidation,
)
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests._maintenance_run_cases import run_record


class MetabolismMaintenanceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.estimator = NativeMetabolismEstimator(MetabolismConfig())
        self.context = MetabolismMaintenanceContext(
            actor_id="agent:maintenance",
            charter_version="charter:maintenance:1",
            target_class=policy.M2,
            scope="tenant-a/project-a",
            downstream_authority=policy.A1,
            risk_class="low",
            tenant_ref="tenant-a",
            project_ref="project-a",
            purpose="memory maintenance",
            isolation_domain_refs=("tenant-a/project-a",),
            required_isolation_domain_refs=("tenant-a/project-a",),
        )

    def _evaluate(
        self,
        memory_ref: str,
        *,
        evaluated_at_ms: int = 31_536_000_000,
        last_meaningful_use_ms: int = 0,
        baseline_saturation: float = 0.0,
        contradiction_pressure: float = 0.0,
        observations: tuple[ReinforcementObservation, ...] = (),
        constraints: RetentionConstraints | None = None,
        lifecycle_state: str = "Observed",
    ):
        return self.estimator.evaluate(
            MetabolismSnapshot(
                memory_ref=memory_ref,
                lifecycle_state=lifecycle_state,
                evaluated_at_ms=evaluated_at_ms,
                last_meaningful_use_ms=last_meaningful_use_ms,
                baseline_saturation=baseline_saturation,
                contradiction_pressure=contradiction_pressure,
                reinforcement_observations=observations,
                constraints=constraints or RetentionConstraints(),
                scope_refs=("tenant-a/project-a",),
                evidence_refs=(f"evidence:{memory_ref}",),
            )
        )

    @staticmethod
    def _pama_documents(plan):
        documents = {}
        items = []
        for routed in plan.proposals:
            proposal = routed.proposal
            decision = policy.evaluate(proposal)
            selected = (
                proposal.operation
                if decision.outcome in {policy.ALLOW, policy.ALLOW_WITH_LEDGER}
                else receipts.NO_ACTION
            )
            ref = receipts.decision_ref_for(proposal.proposal_id)
            documents[ref] = receipts.build_pama_decision(
                proposal,
                decision,
                selected_action=selected,
                selection_mode="deterministic" if selected != receipts.NO_ACTION else None,
                receipt_ref=f"receipt:{proposal.proposal_id}",
            )
            items.append(
                {
                    "decision_ref": ref,
                    "operation": proposal.operation,
                    "outcome": decision.outcome,
                }
            )
        return documents, tuple(items)

    @staticmethod
    def _seed_proposal(
        *,
        proposal_id: str,
        memory_ref: str,
        evidence_refs: tuple[str, ...],
    ) -> policy.Proposal:
        return policy.Proposal(
            proposal_id=proposal_id,
            actor_id="agent:maintenance",
            charter_version="charter:maintenance:1",
            target_reference=memory_ref,
            target_class=policy.M2,
            scope="tenant-a/project-a",
            operation="promotion",
            current_strength="reinforced",
            proposed_strength="promoted",
            downstream_authority=policy.A1,
            reversibility="reversible",
            risk_class="low",
            evidence_refs=evidence_refs,
            estimator_refs=("estimator:seed",),
            estimator_versions=("1",),
            tenant_ref="tenant-a",
            purpose="memory maintenance",
            isolation_domain_refs=("tenant-a/project-a",),
            required_isolation_domain_refs=("tenant-a/project-a",),
            project_ref="project-a",
        )

    def test_plan_keeps_decay_reinforcement_consolidation_and_pruning_distinct(self) -> None:
        old = self._evaluate("memory:old")
        reinforced = self._evaluate(
            "memory:reinforced",
            evaluated_at_ms=1_000,
            last_meaningful_use_ms=900,
            baseline_saturation=0.35,
            observations=(
                ReinforcementObservation(
                    kind="verification",
                    count=1,
                    evidence_refs=("verification:independent",),
                ),
            ),
        )
        consolidation = propose_consolidation(
            (
                ConsolidationSource(
                    memory_ref="memory:source-a",
                    fact_ref="fact:a",
                    currentness="current",
                    scope_refs=("tenant-a/project-a",),
                    evidence_refs=("evidence:a",),
                    exception_refs=("exception:a",),
                ),
                ConsolidationSource(
                    memory_ref="memory:source-b",
                    fact_ref="fact:b",
                    currentness="current",
                    scope_refs=("tenant-a/project-a",),
                    evidence_refs=("evidence:b",),
                ),
            ),
            method_ref="agent-memory:test-consolidation",
            method_version="1.0.0",
        )

        plan = plan_metabolism_maintenance(
            (reinforced, old),
            context=self.context,
            consolidation_proposals=(consolidation,),
        )

        families = [item.consequence_family for item in plan.proposals]
        self.assertIn("decay_pressure", families)
        self.assertIn("reinforcement_pressure", families)
        self.assertIn("prune_archive_candidacy", families)
        self.assertEqual(plan.consolidation_proposals, (consolidation,))
        self.assertIn(consolidation.proposal_ref, plan.proposal_refs)
        self.assertNotIn("crystallization", plan.planned_operations)
        self.assertNotIn("promotion", plan.planned_operations)
        self.assertEqual(plan.authority_effect, "none")
        self.assertTrue(all(item.authority_effect == "none" for item in plan.proposals))
        self.assertTrue(
            all(item.metabolism_evidence_ref in item.proposal.evidence_refs for item in plan.proposals)
        )

    def test_high_saturation_is_not_automatically_crystallized(self) -> None:
        evaluation = self._evaluate(
            "memory:popular",
            evaluated_at_ms=10_000,
            last_meaningful_use_ms=9_999,
            baseline_saturation=0.95,
            observations=(
                ReinforcementObservation(kind="access", count=100_000),
            ),
        )
        self.assertTrue(evaluation.crystallization_candidate)

        plan = plan_metabolism_maintenance((evaluation,), context=self.context)
        self.assertNotIn("crystallization", plan.planned_operations)
        self.assertFalse(
            any(item.proposal.operation == "crystallization" for item in plan.proposals)
        )

    def test_hard_retention_hold_never_becomes_pruning_proposal(self) -> None:
        held = self._evaluate(
            "memory:held",
            constraints=RetentionConstraints(legal_or_compliance_hold=True),
        )
        plan = plan_metabolism_maintenance((held,), context=self.context)

        self.assertEqual(held.disposition, "retention_hold")
        self.assertFalse(any(item.proposal.operation == "pruning" for item in plan.proposals))
        self.assertFalse(
            any(item.proposal.operation == "permanent_deletion" for item in plan.proposals)
        )

    def test_mandatory_deletion_routes_to_existing_deletion_authority(self) -> None:
        mandatory = self._evaluate(
            "memory:mandatory",
            evaluated_at_ms=10_000,
            last_meaningful_use_ms=9_999,
            baseline_saturation=0.95,
            observations=(
                ReinforcementObservation(
                    kind="verification",
                    count=5,
                    evidence_refs=("verification:strong",),
                ),
            ),
            constraints=RetentionConstraints(
                user_pin=True,
                mandatory_deletion=True,
            ),
            lifecycle_state="Crystallized",
        )
        self.assertEqual(mandatory.disposition, "mandatory_deletion_review")
        self.assertTrue(mandatory.crystallization_candidate)

        plan = plan_metabolism_maintenance((mandatory,), context=self.context)
        deletion = [
            item.proposal
            for item in plan.proposals
            if item.proposal.operation == "permanent_deletion"
        ]
        self.assertEqual(len(deletion), 1)
        self.assertEqual(deletion[0].reversibility, "irreversible")
        self.assertNotEqual(policy.evaluate(deletion[0]).outcome, policy.ALLOW)
        self.assertNotEqual(policy.evaluate(deletion[0]).outcome, policy.ALLOW_WITH_LEDGER)

    def test_plan_is_deterministic_and_order_independent(self) -> None:
        first = self._evaluate("memory:a")
        second = self._evaluate(
            "memory:b",
            evaluated_at_ms=1_000,
            last_meaningful_use_ms=900,
            observations=(ReinforcementObservation(kind="corroboration", count=1),),
        )
        left = plan_metabolism_maintenance((first, second), context=self.context)
        right = plan_metabolism_maintenance((second, first), context=self.context)
        self.assertEqual(left, right)

    def test_bind_plan_reuses_existing_maintenance_and_pama_contracts(self) -> None:
        evaluation = self._evaluate("memory:old")
        plan = plan_metabolism_maintenance((evaluation,), context=self.context)
        documents, items = self._pama_documents(plan)
        self.assertTrue(
            all(item["outcome"] in {policy.ALLOW, policy.ALLOW_WITH_LEDGER} for item in items)
        )

        original = run_record(
            planned_operations=plan.planned_operations,
            constituent_decisions=items,
        )
        bound = bind_metabolism_plan(original, plan)

        self.assertEqual(original["estimator_evidence_refs"], [])
        self.assertEqual(bound["planned_operations"], list(plan.planned_operations))
        self.assertTrue(set(plan.proposal_refs).issubset(set(bound["proposal_refs"])))
        self.assertEqual(bound["estimator_evidence_refs"], list(plan.estimator_evidence_refs))
        validate_run(bound, documents)

    def test_bind_plan_does_not_fabricate_missing_pama_decisions(self) -> None:
        evaluation = self._evaluate("memory:old")
        plan = plan_metabolism_maintenance((evaluation,), context=self.context)
        record = run_record(
            planned_operations=plan.planned_operations,
            constituent_decisions=(),
        )
        bound = bind_metabolism_plan(record, plan)

        with self.assertRaisesRegex(ValueError, "lack PAMA decisions"):
            validate_run(bound, {})

    def test_bind_plan_refuses_scope_mismatch(self) -> None:
        evaluation = self._evaluate("memory:old")
        plan = plan_metabolism_maintenance((evaluation,), context=self.context)
        record = run_record(
            planned_operations=plan.planned_operations,
            constituent_decisions=(),
            tenant="tenant-other",
        )
        with self.assertRaisesRegex(ValueError, "tenant/purpose"):
            bind_metabolism_plan(record, plan)

    def test_metabolism_pruning_uses_governed_delete_and_invalidates_derived_recall(self) -> None:
        adapter = GovernedMemoryAdapter(
            InMemoryTemporalGraph(),
            tenant="tenant-a",
            clock=Clock(),
        )
        source = adapter.commit_proposal(
            self._seed_proposal(
                proposal_id="proposal:source",
                memory_ref="memory:old",
                evidence_refs=("evidence:source",),
            ),
            "source memory for derived rule",
        )
        self.assertTrue(source.committed)
        derived = adapter.commit_proposal(
            self._seed_proposal(
                proposal_id="proposal:derived",
                memory_ref="memory:derived",
                evidence_refs=(source.fact_uuid,),
            ),
            "derived rule from source memory",
        )
        self.assertTrue(derived.committed)

        evaluation = self._evaluate("memory:old")
        plan = plan_metabolism_maintenance((evaluation,), context=self.context)
        pruning = next(
            item.proposal
            for item in plan.proposals
            if item.proposal.operation == "pruning"
        )
        consequence = adapter.governed_delete(
            pruning,
            source.fact_uuid,
            derived_refs=(derived.fact_uuid,),
        )

        self.assertTrue(consequence.committed)
        self.assertIsNotNone(adapter.tombstone(source.fact_uuid))
        self.assertIsNotNone(adapter._substrate.get_fact(source.fact_uuid))
        recall = adapter.governed_recall(
            "derived rule",
            RecallContext(
                target_domain_refs=("tenant-a/project-a",),
                principal_ref="agent:maintenance",
                project_ref="project-a",
                purpose="memory maintenance",
            ),
        )
        self.assertIn(derived.fact_uuid, recall.candidates)
        self.assertNotIn(derived.fact_uuid, recall.admitted)
        self.assertEqual(
            recall.refusals[derived.fact_uuid],
            "derived_from_tombstoned_source",
        )
        self.assertEqual(adapter.undeclared_residue(source.fact_uuid), [])


if __name__ == "__main__":
    unittest.main()
