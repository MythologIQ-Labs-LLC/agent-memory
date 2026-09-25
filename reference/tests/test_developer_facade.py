from __future__ import annotations

import importlib.resources
import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory, policy
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.runtime.restart_runtime import RuntimeRecoveryError


TARGET = "memory:release-branch"
TENANT = "tenant:test"
SCOPE = "project:test"
ACTOR = "agent:test"


def _skill_evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:facade-correction",
        version=1,
        purpose="correct retained test memory",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the correction against the current source.",
        provenance_refs=("evidence:test-correction-source",),
    )
    return pm.evidence_for(skill)


class DeveloperFacade(unittest.TestCase):
    def _open(self, root: Path) -> AgentMemory:
        return AgentMemory.open(
            root,
            tenant=TENANT,
            actor_id=ACTOR,
            scope=SCOPE,
            purpose="facade test",
        )

    def test_packaged_profile_is_available(self):
        resource = importlib.resources.files("agentmem_ref") / "_profiles" / "rc1-local.json"
        profile = json.loads(resource.read_text(encoding="utf-8"))
        self.assertEqual(profile["runtime"]["profile_id"], "rc1-local-sqlite-composition")
        self.assertEqual(profile["durable_governance"]["profile_id"], "sqlite_transactional_runtime_v1")

    def test_open_remember_close_reopen_recall_and_posture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            memory = self._open(root)
            self.assertEqual(memory.contract_version, "1.2.0")
            retained = memory.remember(TARGET, "release branch main")
            self.assertTrue(retained["committed"])
            self.assertEqual(retained["stage"], "commit")
            fact_uuid = retained["fact_uuid"]
            self.assertTrue((root / "agent-memory.sqlite3").is_file())
            self.assertTrue((root / "configuration-binding.json").is_file())
            self.assertTrue((root / "runtime-config.json").is_file())

            first = memory.recall("release branch", logical_memory_refs=(TARGET,))
            self.assertIn(fact_uuid, first["admitted"])
            route_ids = {
                item["route_id"]
                for item in first["admissions"][fact_uuid]["route_provenance"]
            }
            self.assertIn("lexical", route_ids)
            self.assertIn("exact_logical_identity", route_ids)

            posture = memory.posture()["posture"]
            self.assertEqual(posture["durable_state"]["status"], "recovered")
            self.assertEqual(posture["durable_state"]["profile"], "sqlite_single_host_v1")
            self.assertEqual(
                posture["recovery"]["base_durability_profile"],
                "sqlite_transactional_runtime_v1",
            )
            memory.close()
            self.assertTrue(memory.closed)
            memory.close()

            recovered = self._open(root)
            after_restart = recovered.recall("release branch", logical_memory_refs=(TARGET,))
            self.assertIn(fact_uuid, after_restart["admitted"])
            recovered.close()

    def test_correction_parks_without_evidence_then_commits_with_qualified_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            memory = self._open(root)
            seed = memory.remember(TARGET, "release branch release")
            self.assertTrue(seed["committed"])

            parked = memory.correct(TARGET, "release branch main")
            self.assertFalse(parked["committed"])
            self.assertEqual(parked["outcome"], policy.REQUIRE_REVIEW)
            self.assertEqual(memory.runtime.adapter.state_version(TARGET), 1)

            corrected = memory.correct(
                TARGET,
                "release branch main",
                evidence=_skill_evidence(),
            )
            self.assertTrue(corrected["committed"])
            self.assertEqual(corrected["outcome"], policy.ALLOW_WITH_LEDGER)
            self.assertEqual(memory.runtime.adapter.state_version(TARGET), 2)
            history = memory.history(TARGET)["history"]
            self.assertEqual(history["state_version"], 2)
            self.assertGreaterEqual(len(history["events"]), 2)
            current = corrected["fact_uuid"]
            memory.close()

            recovered = self._open(root)
            recalled = recovered.recall("release branch main", logical_memory_refs=(TARGET,))
            self.assertIn(current, recalled["admitted"])
            self.assertNotIn(seed["fact_uuid"], recalled["admitted"])
            recovered.close()

    def test_wrong_scope_is_discoverable_but_not_admitted(self):
        with tempfile.TemporaryDirectory() as temporary:
            memory = self._open(Path(temporary))
            retained = memory.remember(TARGET, "shared release detail")
            candidate = retained["fact_uuid"]
            result = memory.recall(
                "shared release detail",
                logical_memory_refs=(TARGET,),
                target_domain_refs=("tenant:other", "project:other"),
                project_ref="project:other",
            )
            self.assertIn(candidate, result["candidates"])
            self.assertNotIn(candidate, result["admitted"])
            self.assertIn("refusal", result["admissions"][candidate])
            memory.close()

    def test_confidence_does_not_change_mutation_authority(self):
        with tempfile.TemporaryDirectory() as temporary:
            memory = self._open(Path(temporary))
            low = memory.remember("memory:confidence-low", "same authority", confidence=0.01)
            high = memory.remember("memory:confidence-high", "same authority", confidence=0.99)
            self.assertEqual(low["outcome"], high["outcome"])
            self.assertEqual(low["decision"]["permitted_actions"], high["decision"]["permitted_actions"])
            self.assertEqual(low["decision"]["prohibited_actions"], high["decision"]["prohibited_actions"])
            memory.close()

    def test_pruning_tombstones_and_restart_does_not_restore_current_influence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            memory = self._open(root)
            seed = memory.remember(TARGET, "temporary release detail")
            forgotten = memory.forget(TARGET, evidence=_skill_evidence())
            self.assertTrue(forgotten["committed"])
            history = memory.history(TARGET)["history"]
            self.assertTrue(history["tombstoned"])
            memory.close()

            recovered = self._open(root)
            recalled = recovered.recall("temporary release detail", logical_memory_refs=(TARGET,))
            self.assertNotIn(seed["fact_uuid"], recalled["admitted"])
            self.assertTrue(recovered.history(TARGET)["history"]["tombstoned"])
            recovered.close()

    def test_permanent_delete_is_not_convenience_authorized(self):
        with tempfile.TemporaryDirectory() as temporary:
            memory = self._open(Path(temporary))
            memory.remember(TARGET, "retain audit history")
            result = memory.forget(TARGET, permanent=True)
            self.assertFalse(result["committed"])
            self.assertIn(
                result["outcome"],
                {policy.REQUIRE_REVIEW, policy.REQUIRE_EXTERNAL_VERIFICATION, policy.BLOCK},
            )
            self.assertIsNotNone(memory.runtime.adapter.current_fact_uuid(TARGET))
            memory.close()

    def test_incomplete_binding_never_becomes_silent_fresh_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "configuration-binding.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(RuntimeRecoveryError):
                self._open(root)
            self.assertFalse((root / "agent-memory.sqlite3").exists())

    def test_context_manager_closes_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self._open(Path(temporary)) as memory:
                memory.remember("memory:context-manager", "bounded runtime")
            self.assertTrue(memory.closed)
            with self.assertRaises(RuntimeError):
                memory.recall("bounded runtime")


if __name__ == "__main__":
    unittest.main()
