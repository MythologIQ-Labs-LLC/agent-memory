from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.qualified_fixtures import corpus_for, registry_for, rule

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.restart_runtime import CapabilityBinding, RuntimeCheckpointConflict, RuntimeProfile
from agentmem_ref.runtime_config import validate_runtime_configuration
from agentmem_ref.sqlite_composition import SQLiteConfiguredCompositionRuntime
from agentmem_ref.sqlite_runtime import SQLiteRestartSafeRuntime
from agentmem_ref.sqlite_substrate import SQLiteTemporalGraph
from agentmem_ref.substrate import Episode, Fact


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "reference" / "fixtures" / "runtime-configuration" / "reference-composed-runtime.json"
TENANT = "tenant-acme"
PROJECT = "project-alpha"
MEMORY = "memory:deploy-window"


def _binding() -> CapabilityBinding:
    return CapabilityBinding(
        component_id="reference-governed-memory",
        component_version="1.0.0",
        capability_id="governed-memory-core",
        capability_version="1.0.0",
        maturity="reference_qualified",
        evidence_ref="evidence:reference-runtime-core-v1",
    )


def _profile() -> RuntimeProfile:
    return RuntimeProfile(
        runtime_version="0.1.0-reference",
        profile_id="reference-project-memory",
        profile_version="1.0.0",
        bindings=(_binding(),),
    )


def _plan():
    return validate_runtime_configuration(json.loads(CONFIG.read_text(encoding="utf-8")))


def _proposal(
    proposal_id: str,
    *,
    operation: str,
    state_snapshot: str = "",
    target_reference: str = MEMORY,
    project_ref: str = PROJECT,
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:sqlite-test",
        charter_version="charter-v1",
        target_reference=target_reference,
        target_class=policy.M2,
        scope=TENANT,
        operation=operation,
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=(f"evidence:{proposal_id}",),
        state_snapshot=state_snapshot,
        tenant_ref=TENANT,
        isolation_domain_refs=(TENANT, project_ref),
        required_isolation_domain_refs=(project_ref,),
        project_ref=project_ref,
        purpose="deployment-planning",
    )


def _context(project_ref: str = PROJECT) -> RecallContext:
    return RecallContext(
        target_domain_refs=(TENANT, project_ref),
        principal_ref="agent:sqlite-test",
        project_ref=project_ref,
        purpose="deployment-planning",
    )


def _corpus():
    return corpus_for(
        rule(
            rule_id="rule:sqlite-correction",
            target=MEMORY,
            criterion="value-correction",
            from_state="deploy window is Thursday",
            to_values=("deploy window is Friday",),
        )
    )


class SQLiteTemporalGraphTests(unittest.TestCase):
    def test_database_is_canonical_state_and_identifier_progress_survives_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.sqlite3"
            first = SQLiteTemporalGraph(path)
            try:
                first_id = first._ids.next()
                first.add_episode(
                    Episode(
                        uuid="episode:1",
                        content="source observation",
                        source_description="test",
                        valid_at="2026-09-23T12:00:00Z",
                        group_id=TENANT,
                    )
                )
                first.write_fact(
                    Fact(
                        uuid=first_id,
                        fact_text="deploy window is Thursday",
                        group_id=TENANT,
                        episode_uuids=("episode:1",),
                    )
                )
                digest = first.state_digest()
            finally:
                first.close()

            second = SQLiteTemporalGraph(path)
            try:
                restored = second.get_fact(first_id)
                self.assertIsNotNone(restored)
                self.assertEqual(restored.fact_text, "deploy window is Thursday")
                self.assertEqual(second.get_episode("episode:1").content, "source observation")
                self.assertEqual(second.state_digest(), digest)
                self.assertNotEqual(second._ids.next(), first_id)
                second.integrity_check()
                identity = second.operational_identity()
                self.assertEqual(identity["substrate_profile"], "sqlite_single_host_v1")
                self.assertEqual(identity["journal_mode"], "wal")
            finally:
                second.close()

    def test_interrupted_transaction_rolls_back_canonical_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "memory.sqlite3"
            graph = SQLiteTemporalGraph(path)
            try:
                with self.assertRaisesRegex(RuntimeError, "simulated interruption"):
                    with graph.transaction():
                        graph.write_fact(
                            Fact(
                                uuid="fact:interrupted",
                                fact_text="must not commit",
                                group_id=TENANT,
                            )
                        )
                        raise RuntimeError("simulated interruption")
                self.assertIsNone(graph.get_fact("fact:interrupted"))
            finally:
                graph.close()

            reopened = SQLiteTemporalGraph(path)
            try:
                self.assertIsNone(reopened.get_fact("fact:interrupted"))
                reopened.integrity_check()
            finally:
                reopened.close()

    def test_online_backup_restores_canonical_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = SQLiteTemporalGraph(Path(temp) / "source.sqlite3")
            backup_path = Path(temp) / "backup.sqlite3"
            try:
                source.write_fact(
                    Fact(uuid="fact:backup", fact_text="backup value", group_id=TENANT)
                )
                source.backup_to(backup_path)
            finally:
                source.close()

            backup = SQLiteTemporalGraph(backup_path)
            try:
                self.assertEqual(backup.get_fact("fact:backup").fact_text, "backup value")
                backup.integrity_check()
            finally:
                backup.close()


class SQLiteRestartRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.profile = _profile()
        self.corpus = _corpus()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _create(self) -> SQLiteRestartSafeRuntime:
        return SQLiteRestartSafeRuntime.create(
            self.root,
            tenant=TENANT,
            profile=self.profile,
            verifier_registry=registry_for(self.corpus),
        )

    def _recover(self) -> SQLiteRestartSafeRuntime:
        return SQLiteRestartSafeRuntime.recover(
            self.root,
            profile=self.profile,
            verifier_registry=registry_for(self.corpus),
        )

    def test_retain_stop_restart_recall_and_scope(self) -> None:
        runtime = self._create()
        retained = runtime.commit_proposal(
            _proposal("proposal:initial", operation="promotion"),
            "deploy window is Thursday",
        )
        self.assertTrue(retained.committed)
        fact_uuid = retained.fact_uuid
        runtime.close()

        recovered = self._recover()
        try:
            same = recovered.adapter.governed_recall("deploy window", _context())
            self.assertEqual(same.admitted, [fact_uuid])
            foreign = recovered.adapter.governed_recall("deploy window", _context("project-beta"))
            self.assertNotIn(fact_uuid, foreign.admitted)
            self.assertEqual(foreign.refusals[fact_uuid], "required_isolation_domain_missing")
        finally:
            recovered.close()

    def test_correction_restart_preserves_currentness_history_and_identifier_progress(self) -> None:
        runtime = self._create()
        initial = runtime.commit_proposal(
            _proposal("proposal:initial", operation="promotion"),
            "deploy window is Thursday",
        )
        correction = runtime.commit_proposal(
            _proposal("proposal:correct", operation="correction", state_snapshot="v1"),
            "deploy window is Friday",
            evidence=self.corpus.evidence_for(
                target_reference=MEMORY,
                criterion="value-correction",
                pre_state="deploy window is Thursday",
                proposed_value="deploy window is Friday",
            ),
        )
        self.assertTrue(correction.committed)
        self.assertNotEqual(initial.fact_uuid, correction.fact_uuid)
        runtime.close()

        recovered = self._recover()
        try:
            current = recovered.adapter.governed_recall("deploy window", _context())
            self.assertEqual(current.admitted, [correction.fact_uuid])
            self.assertEqual(current.refusals[initial.fact_uuid], "superseded_not_current")
            history = recovered.adapter.rejected_value_history(MEMORY, "deploy window is Thursday")
            self.assertEqual(len(history), 1)
            later = recovered.commit_proposal(
                _proposal(
                    "proposal:second-memory",
                    operation="promotion",
                    target_reference="memory:second",
                ),
                "second durable value",
            )
            self.assertTrue(later.committed)
            self.assertNotIn(later.fact_uuid, {initial.fact_uuid, correction.fact_uuid})
        finally:
            recovered.close()

    def test_pruning_restart_keeps_tombstone_and_blocks_current_influence(self) -> None:
        runtime = self._create()
        retained = runtime.commit_proposal(
            _proposal("proposal:initial", operation="promotion"),
            "deploy window is Thursday",
        )
        deleted = runtime.governed_delete(
            _proposal("proposal:prune", operation="pruning"),
            retained.fact_uuid,
        )
        self.assertTrue(deleted.committed)
        self.assertIsNotNone(runtime.adapter.tombstone(retained.fact_uuid))
        runtime.close()

        recovered = self._recover()
        try:
            result = recovered.adapter.governed_recall("deploy window", _context())
            self.assertNotIn(retained.fact_uuid, result.admitted)
            self.assertEqual(result.refusals[retained.fact_uuid], "tombstoned")
            self.assertIsNotNone(recovered.adapter.tombstone(retained.fact_uuid))
            self.assertIsNone(recovered.adapter.current_fact_uuid(MEMORY))
        finally:
            recovered.close()

    def test_stale_writer_cannot_overwrite_newer_generation(self) -> None:
        writer_a = self._create()
        writer_b = self._recover()
        try:
            first = writer_a.commit_proposal(
                _proposal("proposal:a", operation="promotion"),
                "deploy window is Thursday",
            )
            self.assertTrue(first.committed)
            with self.assertRaises(RuntimeCheckpointConflict):
                writer_b.commit_proposal(
                    _proposal(
                        "proposal:b",
                        operation="promotion",
                        target_reference="memory:stale-writer",
                    ),
                    "must not overwrite",
                )
        finally:
            writer_a.close()
            writer_b.close()

        recovered = self._recover()
        try:
            self.assertIsNone(recovered.adapter.current_fact_uuid("memory:stale-writer"))
            self.assertEqual(recovered.adapter.current_fact_uuid(MEMORY), first.fact_uuid)
        finally:
            recovered.close()


class SQLiteConfiguredCompositionTests(unittest.TestCase):
    def test_active_rc_composition_recovers_over_sqlite_and_routes_remain_non_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = SQLiteConfiguredCompositionRuntime.create(
                root,
                tenant=TENANT,
                plan=_plan(),
                verifier_registry=registry_for(_corpus()),
            )
            retained = runtime.retain(
                _proposal("proposal:composition", operation="promotion"),
                "deploy window is Thursday",
            )
            self.assertTrue(retained.committed)
            first_generation = runtime.durable_runtime.base.recovery_evidence.generation
            runtime.close()

            recovered = SQLiteConfiguredCompositionRuntime.recover(
                root,
                plan=_plan(),
                verifier_registry=registry_for(_corpus()),
            )
            try:
                self.assertGreaterEqual(
                    recovered.durable_runtime.base.recovery_evidence.generation,
                    first_generation,
                )
                result = recovered.multi_route_recall(
                    "deploy window",
                    _context(),
                    logical_memory_refs=(MEMORY,),
                )
                self.assertIn(retained.fact_uuid, result.admitted)
                self.assertEqual(result.authority_effect, "none")
                self.assertTrue(
                    all(hit.authority_effect == "none" for hits in result.route_hits.values() for hit in hits)
                )
            finally:
                recovered.close()


if __name__ == "__main__":
    unittest.main()
