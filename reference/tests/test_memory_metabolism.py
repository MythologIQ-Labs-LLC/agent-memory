from __future__ import annotations

import unittest

from agentmem_ref.metabolism import (
    ACCESS,
    ARCHIVE_CANDIDATE,
    CORROBORATION,
    KEEP_ACTIVE,
    MANDATORY_DELETION_REVIEW,
    PRUNE_CANDIDATE,
    REQUIRE_REVIEW,
    RETENTION_HOLD,
    VERIFICATION,
    ConsolidationSource,
    MetabolismConfig,
    MetabolismSnapshot,
    NativeMetabolismEstimator,
    ReinforcementObservation,
    RetentionConstraints,
    propose_consolidation,
)


DAY_MS = 86_400_000


def _snapshot(
    memory_ref: str = "memory:test",
    *,
    evaluated_at_ms: int = 30 * DAY_MS,
    last_meaningful_use_ms: int = 0,
    baseline_saturation: float = 0.0,
    contradiction_pressure: float = 0.0,
    observations: tuple[ReinforcementObservation, ...] = (),
    constraints: RetentionConstraints | None = None,
    lifecycle_state: str = "Observed",
    prior_prune_candidate: bool = False,
) -> MetabolismSnapshot:
    return MetabolismSnapshot(
        memory_ref=memory_ref,
        lifecycle_state=lifecycle_state,
        evaluated_at_ms=evaluated_at_ms,
        last_meaningful_use_ms=last_meaningful_use_ms,
        baseline_saturation=baseline_saturation,
        contradiction_pressure=contradiction_pressure,
        reinforcement_observations=observations,
        constraints=constraints or RetentionConstraints(),
        prior_prune_candidate=prior_prune_candidate,
        scope_refs=("tenant:test", "project:test"),
        evidence_refs=(f"evidence:{memory_ref}",),
    )


class NativeMetabolismEstimatorTests(unittest.TestCase):
    def test_access_spam_is_capped_below_one_verification_signal(self) -> None:
        estimator = NativeMetabolismEstimator()
        access = estimator.reinforcement(
            _snapshot(
                observations=(
                    ReinforcementObservation(ACCESS, count=100_000),
                )
            )
        )
        verified = estimator.reinforcement(
            _snapshot(
                observations=(
                    ReinforcementObservation(
                        VERIFICATION,
                        count=1,
                        evidence_refs=("verification:1",),
                    ),
                )
            )
        )

        access_pressure = dict(access.contributions)[ACCESS]
        verification_pressure = dict(verified.contributions)[VERIFICATION]
        self.assertEqual(access_pressure, estimator.config.max_access_contribution)
        self.assertGreater(verification_pressure, access_pressure)
        self.assertFalse(estimator.evaluate(_snapshot(observations=(ReinforcementObservation(ACCESS, count=100_000),))).crystallization_candidate)
        self.assertEqual(access.authority_effect, "none")
        self.assertEqual(verified.authority_effect, "none")

    def test_independent_support_accumulates_without_becoming_authority(self) -> None:
        estimator = NativeMetabolismEstimator()
        result = estimator.evaluate(
            _snapshot(
                evaluated_at_ms=DAY_MS,
                observations=(
                    ReinforcementObservation(CORROBORATION, count=2, evidence_refs=("source:a", "source:b")),
                    ReinforcementObservation(VERIFICATION, count=1, evidence_refs=("verification:1",)),
                ),
            )
        )
        self.assertGreater(result.reinforcement.effective_saturation, 0.0)
        self.assertEqual(
            result.evidence_refs,
            ("evidence:memory:test", "source:a", "source:b", "verification:1"),
        )
        self.assertEqual(result.authority_effect, "none")

    def test_contradiction_pressure_reduces_reinforcement_and_dispute_requires_review(self) -> None:
        estimator = NativeMetabolismEstimator()
        observations = (ReinforcementObservation(VERIFICATION, count=5),)
        clear = estimator.evaluate(
            _snapshot(
                observations=observations,
                lifecycle_state="Observed",
                contradiction_pressure=0.0,
            )
        )
        disputed = estimator.evaluate(
            _snapshot(
                observations=observations,
                lifecycle_state="Disputed",
                contradiction_pressure=0.9,
            )
        )
        self.assertLess(
            disputed.reinforcement.effective_saturation,
            clear.reinforcement.effective_saturation,
        )
        self.assertEqual(disputed.disposition, REQUIRE_REVIEW)
        self.assertEqual(disputed.authority_effect, "none")

    def test_hard_retention_blocks_ordinary_pruning_even_when_decay_is_low(self) -> None:
        estimator = NativeMetabolismEstimator()
        result = estimator.evaluate(
            _snapshot(
                evaluated_at_ms=365 * DAY_MS,
                constraints=RetentionConstraints(legal_or_compliance_hold=True),
            )
        )
        self.assertLess(result.decay_weight, estimator.config.prune_enter_weight)
        self.assertEqual(result.disposition, RETENTION_HOLD)
        self.assertIn("legal_or_compliance_hold", result.disposition_reasons)

    def test_mandatory_deletion_is_not_overridden_by_high_reinforcement(self) -> None:
        estimator = NativeMetabolismEstimator()
        result = estimator.evaluate(
            _snapshot(
                evaluated_at_ms=DAY_MS,
                baseline_saturation=0.95,
                observations=(ReinforcementObservation(VERIFICATION, count=5),),
                constraints=RetentionConstraints(
                    mandatory_deletion=True,
                    user_pin=True,
                ),
            )
        )
        self.assertEqual(result.disposition, MANDATORY_DELETION_REVIEW)
        self.assertEqual(
            result.disposition_reasons,
            ("mandatory_deletion_requires_governed_consequence",),
        )
        self.assertEqual(result.authority_effect, "none")

    def test_prune_hysteresis_uses_exit_threshold_for_existing_candidate(self) -> None:
        config = MetabolismConfig(
            half_life_ms=1_000,
            prune_enter_weight=0.20,
            prune_exit_weight=0.30,
            archive_weight=0.45,
        )
        estimator = NativeMetabolismEstimator(config)
        # With zero reinforcement, this produces a weight between 0.20 and 0.30.
        fresh = estimator.evaluate(
            _snapshot(
                evaluated_at_ms=2_900,
                last_meaningful_use_ms=0,
                prior_prune_candidate=False,
            )
        )
        existing = estimator.evaluate(
            _snapshot(
                evaluated_at_ms=2_900,
                last_meaningful_use_ms=0,
                prior_prune_candidate=True,
            )
        )
        self.assertGreater(fresh.decay_weight, config.prune_enter_weight)
        self.assertLess(fresh.decay_weight, config.prune_exit_weight)
        self.assertEqual(fresh.disposition, ARCHIVE_CANDIDATE)
        self.assertEqual(existing.disposition, PRUNE_CANDIDATE)
        self.assertEqual(fresh.prune_threshold_used, config.prune_enter_weight)
        self.assertEqual(existing.prune_threshold_used, config.prune_exit_weight)

    def test_batch_is_order_independent_and_evidence_is_stable(self) -> None:
        estimator = NativeMetabolismEstimator()
        a = _snapshot("memory:a", evaluated_at_ms=20 * DAY_MS)
        b = _snapshot(
            "memory:b",
            evaluated_at_ms=DAY_MS,
            observations=(ReinforcementObservation(VERIFICATION, count=1),),
        )
        first = estimator.evaluate_batch((b, a))
        second = estimator.evaluate_batch((a, b))
        self.assertEqual(first, second)
        self.assertEqual(first.evidence_ref, second.evidence_ref)
        self.assertEqual(
            tuple(item.memory_ref for item in first.evaluations),
            ("memory:a", "memory:b"),
        )
        self.assertEqual(first.authority_effect, "none")

    def test_duplicate_memory_in_batch_fails_closed(self) -> None:
        estimator = NativeMetabolismEstimator()
        item = _snapshot("memory:duplicate")
        with self.assertRaises(ValueError):
            estimator.evaluate_batch((item, item))

    def test_recent_healthy_memory_remains_active(self) -> None:
        estimator = NativeMetabolismEstimator()
        result = estimator.evaluate(
            _snapshot(
                evaluated_at_ms=DAY_MS,
                last_meaningful_use_ms=DAY_MS - 1_000,
                baseline_saturation=0.5,
            )
        )
        self.assertEqual(result.disposition, KEEP_ACTIVE)


class ConsolidationProposalTests(unittest.TestCase):
    @staticmethod
    def _source(
        memory_ref: str,
        *,
        currentness: str = "current",
        scopes: tuple[str, ...] = ("tenant:test", "project:test"),
        disputed: bool = False,
        evidence_refs: tuple[str, ...] = (),
        exception_refs: tuple[str, ...] = (),
    ) -> ConsolidationSource:
        return ConsolidationSource(
            memory_ref=memory_ref,
            fact_ref=f"fact:{memory_ref}",
            currentness=currentness,
            scope_refs=scopes,
            evidence_refs=evidence_refs,
            exception_refs=exception_refs,
            disputed=disputed,
        )

    def test_current_same_scope_sources_produce_deterministic_derived_proposal(self) -> None:
        first = self._source(
            "memory:a",
            evidence_refs=("evidence:a",),
            exception_refs=("exception:rare-a",),
        )
        second = self._source(
            "memory:b",
            evidence_refs=("evidence:b",),
            exception_refs=("exception:rare-b",),
        )
        proposal = propose_consolidation(
            (second, first),
            method_ref="agent-memory:deterministic-consolidation-fixture",
            method_version="1.0.0",
        )
        repeated = propose_consolidation(
            (first, second),
            method_ref="agent-memory:deterministic-consolidation-fixture",
            method_version="1.0.0",
        )

        self.assertEqual(proposal, repeated)
        self.assertTrue(proposal.eligible)
        self.assertEqual(proposal.reasons, ())
        self.assertEqual(proposal.source_memory_refs, ("memory:a", "memory:b"))
        self.assertEqual(proposal.evidence_refs, ("evidence:a", "evidence:b"))
        self.assertEqual(
            proposal.exception_refs,
            ("exception:rare-a", "exception:rare-b"),
        )
        self.assertEqual(proposal.derived_posture, "proposed_derived")
        self.assertEqual(proposal.certification_status, "not_established")
        self.assertEqual(proposal.authority_effect, "none")

    def test_mixed_scope_sources_fail_closed_in_first_profile(self) -> None:
        proposal = propose_consolidation(
            (
                self._source("memory:a"),
                self._source(
                    "memory:b",
                    scopes=("tenant:test", "project:other"),
                ),
            ),
            method_ref="agent-memory:consolidation",
            method_version="1.0.0",
        )
        self.assertFalse(proposal.eligible)
        self.assertIn("scope_mismatch", proposal.reasons)
        self.assertEqual(proposal.authority_effect, "none")

    def test_stale_or_disputed_sources_cannot_be_silently_consolidated(self) -> None:
        proposal = propose_consolidation(
            (
                self._source("memory:a", currentness="superseded"),
                self._source("memory:b", disputed=True),
            ),
            method_ref="agent-memory:consolidation",
            method_version="1.0.0",
        )
        self.assertFalse(proposal.eligible)
        self.assertIn("non_current_source", proposal.reasons)
        self.assertIn("disputed_source", proposal.reasons)
        self.assertEqual(proposal.certification_status, "not_established")


if __name__ == "__main__":
    unittest.main()
