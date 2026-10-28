"""Independent v7 integration review, findings 1 and 2: preregistered fail-first tests.

RF1 (medium). A facade handle's host-bound identity is fixed by ``AgentMemory.open``. A caller
holding the handle must not re-bind it, by assigning ``scope``, ``tenant``, ``actor_id``,
``purpose``, ``task_ref``, ``store_profile``, ``charter_version``, ``runtime`` or ``root``:

- on a ``scope_distinct_v1`` store that reached another project's memory;
- on a ``single_project_v1`` store, one write through a re-bound handle bricked the store for
  every project.

A directly constructed handle must name its store profile; there is no silent legacy default.

RF2 (low). The ownership fence on a deleted owned id must not answer a writer from another
scope differently than a never-written id does. It consults only deleted generations that writer
is scope-eligible for.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.adapter import Clock, RecallContext
from agentmem_ref.api import surface
from agentmem_ref.capabilities import ComponentRegistry
from agentmem_ref.procedural_memory import ProceduralMemoryRuntime, SkillArtifact, reference_procedural_component
from agentmem_ref.runtime.adapter import OWNERSHIP_CREATOR_PRINCIPAL
from agentmem_ref.runtime.restart_runtime import CheckpointableGovernedMemoryAdapter
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests.qualified_fixtures import corpus_for, registry_for, rule

TENANT, ACTOR = "tenant:review", "agent:review"
IDENTITY = ("scope", "tenant", "actor_id", "purpose", "task_ref", "store_profile", "charter_version", "runtime", "root")


def _open(root, scope, profile=None):
    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="review", store_profile=profile)


class HandleIdentityIsFixedTests(unittest.TestCase):
    def test_rf1a_identity_attributes_cannot_be_reassigned(self):
        with tempfile.TemporaryDirectory() as root:
            with _open(root, "project:b", surface.STORE_PROFILE_SCOPE_DISTINCT) as handle:
                for name in IDENTITY:
                    with self.subTest(attribute=name), self.assertRaises(AttributeError):
                        setattr(handle, name, getattr(handle, name))

    def test_rf1b_scope_distinct_handle_cannot_be_rebound_to_another_project(self):
        with tempfile.TemporaryDirectory() as root:
            with _open(root, "project:a", surface.STORE_PROFILE_SCOPE_DISTINCT) as a:
                a.remember("memory:k", "project a's gateway is Oslo")
            with _open(root, "project:b", surface.STORE_PROFILE_SCOPE_DISTINCT) as b:
                unknown = b.history("memory:never")["history"]
                with self.assertRaises(AttributeError):
                    b.scope = "project:a"
                self.assertEqual(b.scope, "project:b")
                self.assertEqual(b.history("memory:k")["history"]["current_fact_uuid"], unknown["current_fact_uuid"])
                self.assertFalse(b.forget("memory:k")["committed"])
            with _open(root, "project:a") as a:
                self.assertFalse(a.history("memory:k")["history"]["tombstoned"])

    def test_rf1c_single_project_store_cannot_be_bricked_through_a_handle(self):
        with tempfile.TemporaryDirectory() as root:
            with _open(root, "project:a") as a:
                a.remember("memory:k", "bound to project a")
                with self.assertRaises(AttributeError):
                    a.scope = "project:b"
                a.remember("memory:k2", "still project a")
            with _open(root, "project:a") as reopened:
                self.assertIsNotNone(reopened.history("memory:k2")["history"]["current_fact_uuid"])
            with self.assertRaises(surface.StoreIdentityError):
                _open(root, "project:b")

    def test_rf1d_direct_construction_must_name_its_store_profile(self):
        with tempfile.TemporaryDirectory() as root:
            with _open(root, "project:a") as a:
                kwargs = dict(root=Path(root), config_path=a.config_path, qualification_path=None, tenant=TENANT,
                              actor_id=ACTOR, charter_version=a.charter_version, scope="project:a", purpose="review",
                              runtime=a.runtime)
                with self.assertRaises(TypeError):
                    AgentMemory(**kwargs)


def _artifact(skill, project):
    return SkillArtifact(skill_id=skill, version=1, purpose="release_planning", scope=TENANT,
                         isolation_domain_refs=(TENANT, project), required_isolation_domain_refs=(TENANT, project),
                         procedure_markdown=f"# {skill}\n- step", provenance_refs=(f"ep:{skill}",),
                         validation_refs=(f"val:{skill}",))


class OwnershipFenceDisclosureTests(unittest.TestCase):
    OWNER_PROJECT, OTHER_PROJECT = "project:o", "project:other"

    def setUp(self):
        self.substrate = InMemoryTemporalGraph()
        corpus = corpus_for(rule(rule_id="r", target="skill:s", criterion="c", from_state="v1", to_values=("v2",)))
        self.adapter = CheckpointableGovernedMemoryAdapter(self.substrate, tenant=TENANT, clock=Clock(),
                                                           verifier_registry=registry_for(corpus))
        self.registry = ComponentRegistry()
        self.registry.register(reference_procedural_component())

    def runtime(self, principal, project, ownership=None):
        return ProceduralMemoryRuntime(
            substrate=self.substrate, adapter=self.adapter, registry=self.registry, ownership=ownership,
            revocation_context=RecallContext(target_domain_refs=(TENANT, project), principal_ref=principal,
                                             project_ref=project, purpose="release_planning"))

    def write(self, runtime, principal, skill, project):
        commit = runtime.commit_skill(runtime.propose_skill(_artifact(skill, project), actor_id=principal)).commit
        return commit.committed, commit.refusal

    def test_rf2_foreign_writer_reads_a_deleted_owned_id_as_a_never_written_one(self):
        owner = self.runtime("agent:owner", self.OWNER_PROJECT, OWNERSHIP_CREATOR_PRINCIPAL)
        self.assertEqual(self.write(owner, "agent:owner", "s", self.OWNER_PROJECT), (True, None))
        self.assertTrue(owner.revoke_skill("s", actor_id="agent:owner", evidence_refs=("e",)).commit.committed)
        foreign = self.runtime("agent:foreign", self.OTHER_PROJECT)
        deleted_owned = self.write(foreign, "agent:foreign", "s", self.OTHER_PROJECT)
        never_written = self.write(foreign, "agent:foreign", "t", self.OTHER_PROJECT)
        self.assertEqual(deleted_owned, never_written)

    def test_rf2_control_a_same_project_non_owner_still_cannot_recreate_the_owned_id(self):
        owner = self.runtime("agent:owner", self.OWNER_PROJECT, OWNERSHIP_CREATOR_PRINCIPAL)
        self.write(owner, "agent:owner", "s", self.OWNER_PROJECT)
        owner.revoke_skill("s", actor_id="agent:owner", evidence_refs=("e",))
        peer = self.runtime("agent:peer", self.OWNER_PROJECT, OWNERSHIP_CREATOR_PRINCIPAL)
        self.assertEqual(self.write(peer, "agent:peer", "s", self.OWNER_PROJECT), (False, "target_unavailable"))
        self.assertEqual(self.write(owner, "agent:owner", "s", self.OWNER_PROJECT), (True, None))


if __name__ == "__main__":
    unittest.main()
