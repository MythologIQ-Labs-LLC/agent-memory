"""Issue #417: governed schema/profile migration over checkpoint generations."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.qualified_fixtures import corpus_for, registry_for, rule

from agentmem_ref import policy
from agentmem_ref.checkpoint_migration import (
    CheckpointMigrationError,
    MigrationState,
    build_migration_plan,
    execute_migration,
    recover_interrupted_migration,
    rollback_migration,
)
from agentmem_ref.restart_runtime import (
    CapabilityBinding,
    RestartSafeRuntime,
    RuntimeCheckpointConflict,
    RuntimeProfile,
    RuntimeRecoveryError,
)
from agentmem_ref.structural_mutation import (
    AUTHORIZED,
    S2,
    SUPERSEDED,
    SchemaRef,
    StructuralProposal,
    authorize_lifecycle,
    classify,
    evaluate_pama_v13,
)
from agentmem_ref import domain_schema_mutation as dsm
import agentmem_ref.runtime.restart_runtime as rr


def _digest(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _binding(*, component_version: str = "1.0.0", maturity: str = "reference_qualified",
             evidence_ref: str = "evidence:reference-runtime-core-v1") -> CapabilityBinding:
    return CapabilityBinding(
        component_id="reference-governed-memory",
        component_version=component_version,
        capability_id="governed-memory-core",
        capability_version="1.0.0",
        maturity=maturity,
        evidence_ref=evidence_ref,
    )


def _source_profile(*, maturity: str = "reference_qualified") -> RuntimeProfile:
    return RuntimeProfile(
        runtime_version="0.1.0-reference",
        profile_id="reference-project-memory",
        profile_version="1.0.0",
        bindings=(_binding(maturity=maturity),),
    )


def _target_profile(*, maturity: str = "reference_qualified",
                    evidence_ref: str = "evidence:reference-runtime-core-v2") -> RuntimeProfile:
    return RuntimeProfile(
        runtime_version="0.1.0-reference",
        profile_id="reference-project-memory",
        profile_version="2.0.0",
        bindings=(
            _binding(component_version="1.1.0", maturity=maturity, evidence_ref=evidence_ref),
        ),
    )


def _proposal(pid: str, target: str, *, operation: str = "runtime_assembly",
              target_class: str = policy.M1, state_snapshot: str = "") -> policy.Proposal:
    return policy.Proposal(
        proposal_id=pid,
        actor_id="agent:migration-test",
        charter_version="charter-v1",
        target_reference=target,
        target_class=target_class,
        scope="tenant-acme",
        operation=operation,
        current_strength="observed",
        proposed_strength="promoted" if operation == "correction" else "tentative",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=(f"evidence:{pid}",),
        state_snapshot=state_snapshot,
        tenant_ref="tenant-acme",
        isolation_domain_refs=("tenant-acme", "project-alpha"),
        required_isolation_domain_refs=("project-alpha",),
        project_ref="project-alpha",
        purpose="migration-test",
    )


def _structural_authority():
    structural = StructuralProposal(
        proposal_id="schema:migrate-project-v2",
        current_schema=SchemaRef("domain:project", "1.0.0", "project"),
        proposed_schema=SchemaRef("domain:project", "2.0.0", "project"),
        layer="domain",
        change_kind="semantic_change",
        semantic_diff=("represent status as a versioned structured attribute",),
        tenant_ref="tenant-acme",
        isolation_domain_refs=("tenant-acme/project-alpha",),
        preserves_semantics=False,
        optional_additive=False,
        migration_required=True,
        information_loss="possible",
        historical_interpretation_preserved=False,
        scope_posture="unchanged",
        authority_posture="unchanged",
        isolation_posture="preserved",
        affected_memory_count=12,
        dependent_refs=("consumer:project-memory",),
        incompatible_dependency_refs=(),
        live_dependency_refs=(),
        reversibility="compensatable",
        rollback_ref="rollback:domain-project:1.0.0",
        rebuild_obligations=("projection:project-memory",),
        residue_obligations=(),
        state_digest=_digest("domain-state-v1"),
        dependency_digest=_digest("domain-deps-v1"),
        evidence_refs=("evidence:schema-diff", "evidence:dependency-scan"),
    )
    impact = classify(structural)
    assert impact.classification.structural_class == S2
    pama = policy.Proposal(
        proposal_id=structural.proposal_id,
        actor_id="agent:schema-observer",
        charter_version="charter-v1",
        target_reference="domain-model:project-alpha",
        target_class=policy.M3,
        scope="tenant-acme/project-alpha",
        operation=dsm.DOMAIN_SCHEMA_MUTATION,
        current_strength="promoted",
        proposed_strength="canonical",
        downstream_authority=policy.A3,
        reversibility=structural.reversibility,
        risk_class="low",
        evidence_refs=structural.evidence_refs,
        state_snapshot=structural.state_digest,
        tenant_ref=structural.tenant_ref,
        isolation_domain_refs=structural.isolation_domain_refs,
        required_isolation_domain_refs=structural.isolation_domain_refs,
        project_ref="project-alpha",
        purpose="domain schema migration",
    )
    corpus = corpus_for(
        rule(
            rule_id="rule:project-schema-migration-v2",
            target=pama.target_reference,
            criterion="schema-migration",
            from_state="v1",
            to_values=("v2",),
        )
    )
    decision = evaluate_pama_v13(
        pama,
        impact,
        current_state_digest=structural.state_digest,
        current_dependency_digest=structural.dependency_digest,
        evidence=corpus.evidence_for(
            target_reference=pama.target_reference,
            criterion="schema-migration",
            pre_state="v1",
            proposed_value="v2",
        ),
        verifier_registry=registry_for(corpus),
    )
    lifecycle = authorize_lifecycle(
        impact,
        decision,
        current_state_digest=structural.state_digest,
        current_dependency_digest=structural.dependency_digest,
        decision_ref="decision:schema:migrate-project-v2",
        approval_refs=("approval:human:migration-42",),
    )
    assert lifecycle.lifecycle_state == AUTHORIZED
    return impact, lifecycle


def _semantic_transform(state: MigrationState) -> MigrationState:
    target = state.detached_copy()
    facts = []
    for fact in target.substrate["facts"]:
        row = dict(fact)
        attributes = dict(row.get("attributes", {}))
        attributes["domain_schema_version"] = "2.0.0"
        row["attributes"] = attributes
        facts.append(row)
    target.substrate["facts"] = facts
    return target


class CheckpointMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source_profile = _source_profile()
        self.target_profile = _target_profile()
        self.runtime = RestartSafeRuntime.create(
            self.root, tenant="tenant-acme", profile=self.source_profile
        )
        self.committed = self.runtime.commit_proposal(
            _proposal("p-item", "memory:item"), "status = legacy"
        )
        self.runtime.persist_visibility_snapshot(
            "visibility:migration", {"pending": ["projection:project-memory"]}
        )
        self.impact, self.lifecycle = _structural_authority()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _plan(self, **overrides):
        values = dict(
            target_profile=self.target_profile,
            impact=self.impact,
            lifecycle=self.lifecycle,
            migration_id="migration:project-v2",
            transformer_id="transformer:project-v2",
            transformer_version="1.0.0",
            compatibility_evidence_refs=("compat:runtime-core-1-to-1.1",),
            validation_refs=("validation:project-v2",),
        )
        values.update(overrides)
        return build_migration_plan(self.runtime, **values)

    def test_incompatible_profile_refuses_without_explicit_migration(self):
        with self.assertRaisesRegex(RuntimeRecoveryError, "interpretation changed"):
            RestartSafeRuntime.recover(self.root, profile=self.target_profile)

    def test_authorized_schema_and_profile_migration_commits_exactly_one_generation(self):
        source_generation = self.runtime.recovery_evidence.generation
        migrated, execution = execute_migration(
            self.runtime,
            target_profile=self.target_profile,
            impact=self.impact,
            lifecycle=self.lifecycle,
            plan=self._plan(),
            transformer_id="transformer:project-v2",
            transformer_version="1.0.0",
            transform=_semantic_transform,
        )
        self.assertEqual(execution.source_generation, source_generation)
        self.assertEqual(execution.target_generation, source_generation + 1)
        self.assertEqual(migrated.recovery_evidence.generation, source_generation + 1)
        self.assertEqual(migrated.profile.to_dict(), self.target_profile.to_dict())
        fact = migrated.adapter.checkpoint_substrate().get_fact(self.committed.fact_uuid)
        self.assertEqual(fact.attributes["domain_schema_version"], "2.0.0")
        self.assertEqual(
            migrated.visibility_snapshots["visibility:migration"],
            {"pending": ["projection:project-memory"]},
        )
        self.assertTrue((self.root / execution.backup_ref).exists())
        self.assertTrue((self.root / execution.record_ref).exists())

    def test_stale_migration_plan_is_rejected_after_source_generation_advances(self):
        plan = self._plan()
        self.runtime.checkpoint()
        with self.assertRaisesRegex(RuntimeCheckpointConflict, "stale"):
            execute_migration(
                self.runtime,
                target_profile=self.target_profile,
                impact=self.impact,
                lifecycle=self.lifecycle,
                plan=plan,
                transformer_id=plan.transformer_id,
                transformer_version=plan.transformer_version,
                transform=_semantic_transform,
            )

    def test_migration_cannot_erase_scope_or_pending_visibility(self):
        plan = self._plan()

        def erase_scope(state: MigrationState) -> MigrationState:
            target = state.detached_copy()
            target.adapter["fact_scope"] = {}
            return target

        with self.assertRaisesRegex(CheckpointMigrationError, "fact_scope"):
            execute_migration(
                self.runtime,
                target_profile=self.target_profile,
                impact=self.impact,
                lifecycle=self.lifecycle,
                plan=plan,
                transformer_id=plan.transformer_id,
                transformer_version=plan.transformer_version,
                transform=erase_scope,
            )

        def erase_visibility(state: MigrationState) -> MigrationState:
            target = state.detached_copy()
            target.visibility_snapshots = {}
            return target

        with self.assertRaisesRegex(CheckpointMigrationError, "visibility"):
            execute_migration(
                self.runtime,
                target_profile=self.target_profile,
                impact=self.impact,
                lifecycle=self.lifecycle,
                plan=plan,
                transformer_id=plan.transformer_id,
                transformer_version=plan.transformer_version,
                transform=erase_visibility,
            )

    def test_migration_cannot_erase_tombstones_or_rejected_value_history(self):
        # Populate both governance records through their normal governed paths.
        tombstoned = self.runtime.commit_proposal(
            _proposal("p-delete-source", "memory:delete-me"), "delete me"
        )
        deleted = self.runtime.governed_delete(
            _proposal("p-delete", "memory:delete-me", operation="pruning"),
            tombstoned.fact_uuid,
        )
        self.assertTrue(deleted.committed)

        corpus = corpus_for(
            rule(
                rule_id="rule:correction",
                target="memory:corrected",
                criterion="value-correction",
                from_state="status = old",
                to_values=("status = current",),
            )
        )
        # Recovered verifier trust is host-owned, so create a fresh isolated
        # runtime for the correction record rather than mutating trust per call.
        correction_root = self.root / "correction-fixture"
        correction_runtime = RestartSafeRuntime.create(
            correction_root,
            tenant="tenant-acme",
            profile=self.source_profile,
            verifier_registry=registry_for(corpus),
        )
        correction_runtime.commit_proposal(
            _proposal("p-old", "memory:corrected"), "status = old"
        )
        correction_runtime.commit_proposal(
            _proposal("p-current", "memory:corrected", operation="correction", target_class=policy.M2, state_snapshot="v1"),
            "status = current",
            evidence=corpus.evidence_for(
                target_reference="memory:corrected",
                criterion="value-correction",
                pre_state="status = old",
                proposed_value="status = current",
            ),
        )
        correction_state = correction_runtime.adapter.export_checkpoint_state()
        self.assertTrue(correction_state["rejected_values"])

        plan = self._plan()
        self.assertTrue(self.runtime.adapter.export_checkpoint_state()["tombstones"])

        def erase_tombstones(state: MigrationState) -> MigrationState:
            target = state.detached_copy()
            target.adapter["tombstones"] = {}
            return target

        with self.assertRaisesRegex(CheckpointMigrationError, "tombstones"):
            execute_migration(
                self.runtime,
                target_profile=self.target_profile,
                impact=self.impact,
                lifecycle=self.lifecycle,
                plan=plan,
                transformer_id=plan.transformer_id,
                transformer_version=plan.transformer_version,
                transform=erase_tombstones,
            )

        # Directly validate the invariant checker through a transformer on the
        # fixture state by transplanting the non-empty registry into a detached
        # migration state. This is checkpoint data owned by the registry, not a
        # fabricated private object.
        original_export = self.runtime.adapter.export_checkpoint_state
        with mock.patch.object(
            self.runtime.adapter,
            "export_checkpoint_state",
            side_effect=lambda: {
                **original_export(),
                "rejected_values": correction_state["rejected_values"],
                "rejected_values_descriptor": correction_state["rejected_values_descriptor"],
            },
        ):
            plan = self._plan()

            def erase_rejections(state: MigrationState) -> MigrationState:
                target = state.detached_copy()
                target.adapter["rejected_values"] = []
                return target

            with self.assertRaisesRegex(CheckpointMigrationError, "rejected_values"):
                execute_migration(
                    self.runtime,
                    target_profile=self.target_profile,
                    impact=self.impact,
                    lifecycle=self.lifecycle,
                    plan=plan,
                    transformer_id=plan.transformer_id,
                    transformer_version=plan.transformer_version,
                    transform=erase_rejections,
                )

    def test_profile_maturity_cannot_be_promoted_with_reused_qualification_evidence(self):
        root = self.root / "maturity"
        low_profile = _source_profile(maturity="implemented")
        low_runtime = RestartSafeRuntime.create(root, tenant="tenant-acme", profile=low_profile)
        target = RuntimeProfile(
            runtime_version="0.1.0-reference",
            profile_id=low_profile.profile_id,
            profile_version="2.0.0",
            bindings=(
                _binding(
                    component_version="1.1.0",
                    maturity="reference_qualified",
                    evidence_ref="evidence:reference-runtime-core-v1",
                ),
            ),
        )
        with self.assertRaisesRegex(CheckpointMigrationError, "distinct qualification evidence"):
            build_migration_plan(
                low_runtime,
                target_profile=target,
                impact=self.impact,
                lifecycle=self.lifecycle,
                migration_id="migration:bad-promotion",
                transformer_id="transformer:bad-promotion",
                transformer_version="1.0.0",
                compatibility_evidence_refs=("compat:claims-promotion",),
                validation_refs=("validation:promotion",),
            )

    def test_crash_between_migration_payload_writes_restores_source_generation(self):
        plan = self._plan()
        source_generation = self.runtime.recovery_evidence.generation
        real_write = rr._atomic_json_write

        def fail_governance(path, value):
            if path.name == "governance.json":
                raise OSError("simulated migration crash")
            return real_write(path, value)

        with mock.patch("agentmem_ref.runtime.restart_runtime._atomic_json_write", side_effect=fail_governance):
            with self.assertRaisesRegex(OSError, "simulated migration crash"):
                execute_migration(
                    self.runtime,
                    target_profile=self.target_profile,
                    impact=self.impact,
                    lifecycle=self.lifecycle,
                    plan=plan,
                    transformer_id=plan.transformer_id,
                    transformer_version=plan.transformer_version,
                    transform=_semantic_transform,
                )

        self.assertIsNone(recover_interrupted_migration(self.root))
        restored = RestartSafeRuntime.recover(self.root, profile=self.source_profile)
        self.assertEqual(restored.recovery_evidence.generation, source_generation)
        fact = restored.adapter.checkpoint_substrate().get_fact(self.committed.fact_uuid)
        self.assertNotIn("domain_schema_version", fact.attributes)

    def test_governed_rollback_publishes_new_generation_and_marks_lifecycle_superseded(self):
        migrated, execution = execute_migration(
            self.runtime,
            target_profile=self.target_profile,
            impact=self.impact,
            lifecycle=self.lifecycle,
            plan=self._plan(),
            transformer_id="transformer:project-v2",
            transformer_version="1.0.0",
            transform=_semantic_transform,
        )
        rolled, lifecycle, rollback = rollback_migration(
            migrated,
            source_profile=self.source_profile,
            lifecycle=self.lifecycle,
            execution=execution,
        )
        self.assertEqual(rollback.rollback_generation, execution.target_generation + 1)
        self.assertEqual(rolled.profile.to_dict(), self.source_profile.to_dict())
        self.assertEqual(lifecycle.lifecycle_state, SUPERSEDED)
        fact = rolled.adapter.checkpoint_substrate().get_fact(self.committed.fact_uuid)
        self.assertNotIn("domain_schema_version", fact.attributes)

    def test_rollback_refuses_after_any_later_durable_generation(self):
        migrated, execution = execute_migration(
            self.runtime,
            target_profile=self.target_profile,
            impact=self.impact,
            lifecycle=self.lifecycle,
            plan=self._plan(),
            transformer_id="transformer:project-v2",
            transformer_version="1.0.0",
            transform=_semantic_transform,
        )
        migrated.checkpoint()
        with self.assertRaisesRegex(CheckpointMigrationError, "later durable state exists"):
            rollback_migration(
                migrated,
                source_profile=self.source_profile,
                lifecycle=self.lifecycle,
                execution=execution,
            )

    def test_direct_downgrade_plan_is_refused(self):
        plan = replace(self._plan(), direction="downgrade")
        with self.assertRaisesRegex(CheckpointMigrationError, "downgrade"):
            execute_migration(
                self.runtime,
                target_profile=self.target_profile,
                impact=self.impact,
                lifecycle=self.lifecycle,
                plan=plan,
                transformer_id=plan.transformer_id,
                transformer_version=plan.transformer_version,
                transform=_semantic_transform,
            )


if __name__ == "__main__":
    unittest.main()
