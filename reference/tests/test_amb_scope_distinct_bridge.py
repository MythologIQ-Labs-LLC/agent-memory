"""AM B scope-distinct bridge successor: real public-facade boundary tests.

The frozen 0.4.0 bridge and v7 lane are not changed. These controls challenge the
new 0.5.0 adapter with two AMB users against one real SQLite root; they do not
constitute benchmark score or lane acceptance. Run from repository root with:
python3.12 -m unittest reference.tests.test_amb_scope_distinct_bridge -v
or through the repository's reference/ discovery convention.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import amb_agent_memory_bridge as frozen
import amb_agent_memory_bridge_scope_distinct as successor
from agentmem_ref import AgentMemory
from agentmem_ref.api.surface import STORE_PROFILE_SCOPE_DISTINCT, StoreIdentityError


@dataclass
class Document:
    id: str
    content: str
    user_id: str | None = None
    timestamp: str | None = None
    context: str | None = None
    source_ids: list[str] | None = None
    tags: list[str] | None = None


def fake_amb():
    memory_bench = types.ModuleType("memory_bench")
    memory = types.ModuleType("memory_bench.memory")
    base = types.ModuleType("memory_bench.memory.base")
    models = types.ModuleType("memory_bench.models")
    memory.REGISTRY = {}
    base.MemoryProvider = type("MemoryProvider", (), {})
    models.Document = Document
    return {
        "memory_bench": memory_bench,
        "memory_bench.memory": memory,
        "memory_bench.memory.base": base,
        "memory_bench.models": models,
    }, memory.REGISTRY


class ScopeDistinctAmbBridgeTests(unittest.TestCase):
    REVISION = "a" * 40
    ALICE = "user:alice"
    BOB = "user:bob"

    def setUp(self):
        modules, self.registry = fake_amb()
        self.modules = mock.patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.env = mock.patch.dict(os.environ, {})
        self.env.start()
        self.addCleanup(self.env.stop)
        os.environ.pop(successor.SIDECAR_ENV, None)
        os.environ.pop(successor.CROSS_FACT_SIDECAR_ENV, None)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = self.root / "benchmark"
        self.provider_class = successor.install_amb_agent_memory_provider(
            self.root, agent_memory_revision=self.REVISION
        )

    @staticmethod
    def docs():
        return [
            Document("doc:alice", "Alice's gateway city is Oslo.", "user:alice"),
            Document("doc:bob", "Bob's gateway city is Turku.", "user:bob"),
        ]

    def prepare(self, *, reset=True):
        provider = self.provider_class()
        provider.prepare(self.store, reset=reset)
        return provider

    def test_frozen_bridge_remains_blocked_for_two_projects(self):
        old_type = frozen.install_amb_agent_memory_provider(
            self.root, agent_memory_revision=self.REVISION
        )
        old = old_type()
        old.prepare(self.root / "old")
        with self.assertRaises(StoreIdentityError):
            old.ingest(self.docs())

    def test_two_projects_share_one_explicit_scope_distinct_root(self):
        provider = self.prepare()
        provider.ingest(self.docs())
        runtime_root = self.store / "agent-memory-runtime"
        with AgentMemory.open(
            runtime_root,
            tenant=successor._TENANT,
            actor_id=successor._ACTOR,
            scope=successor._scope(self.ALICE),
            store_profile=STORE_PROFILE_SCOPE_DISTINCT,
        ) as handle:
            self.assertEqual(handle.store_profile, STORE_PROFILE_SCOPE_DISTINCT)
        alice, meta_a = provider.retrieve("Alice's gateway city Oslo", k=5, user_id=self.ALICE)
        bob, meta_b = provider.retrieve("Bob's gateway city Turku", k=5, user_id=self.BOB)
        self.assertEqual([d.id for d in alice], ["doc:alice"])
        self.assertEqual([d.id for d in bob], ["doc:bob"])
        self.assertEqual((meta_a["bridge_version"], meta_b["bridge_version"]), ("0.5.0", "0.5.0"))

    def test_same_document_id_in_two_projects_has_unique_fact_identity(self):
        provider = self.prepare()
        provider.ingest([
            Document("doc:shared", "Alice stores her red guitar in Oslo.", self.ALICE),
            Document("doc:shared", "Bob stores his blue guitar in Turku.", self.BOB),
        ])
        self.assertEqual(len(provider._by_fact), 2)
        self.assertEqual({entry["user_id"] for entry in provider._by_fact.values()},
                         {self.ALICE, self.BOB})
        for user, expected in ((self.ALICE, "red"), (self.BOB, "blue")):
            results, _ = provider.retrieve(expected + " guitar", k=5, user_id=user)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].user_id, user)

    def test_reopening_without_reset_preserves_index_and_project_isolation(self):
        first = self.prepare()
        first.ingest(self.docs())
        saved_ids = set(first._by_fact)
        second = self.prepare(reset=False)
        self.assertEqual(set(second._by_fact), saved_ids)
        for user, expected in ((self.ALICE, "doc:alice"), (self.BOB, "doc:bob")):
            results, _ = second.retrieve("gateway city", k=5, user_id=user)
            self.assertEqual([d.id for d in results], [expected])

    def test_both_ingest_and_retrieve_explicitly_request_the_profile(self):
        original = AgentMemory.open
        calls = []

        def recorded_open(*args, **kwargs):
            calls.append(kwargs.copy())
            return original(*args, **kwargs)

        with mock.patch.object(successor.AgentMemory, "open", side_effect=recorded_open):
            provider = self.prepare()
            provider.ingest(self.docs())
            provider.retrieve("Oslo gateway", k=5, user_id=self.ALICE)
            provider.retrieve("Turku gateway", k=5, user_id=self.BOB)
        self.assertGreaterEqual(len(calls), 4)
        self.assertTrue(all(call.get("store_profile") == STORE_PROFILE_SCOPE_DISTINCT for call in calls))
        self.assertEqual(
            {call["scope"] for call in calls},
            {successor._scope(self.ALICE), successor._scope(self.BOB)}
        )

    def test_sidecar_keeps_order_and_scope_without_cross_project_ids(self):
        provider = self.prepare()
        provider.ingest(self.docs())
        sidecar = self.root / "records" / "cross-fact.jsonl"
        os.environ[successor.CROSS_FACT_SIDECAR_ENV] = str(sidecar)
        provider.retrieve("Oslo gateway", k=5, user_id=self.ALICE)
        provider.retrieve("Turku gateway", k=5, user_id=self.BOB)
        lines = [json.loads(line) for line in sidecar.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual([x["call_index"] for x in lines], [0, 1])
        self.assertEqual([x["scope"] for x in lines],
                         [successor._scope(self.ALICE), successor._scope(self.BOB)])
        self.assertEqual(lines[0]["returned_document_ids"], ["doc:alice"])
        self.assertEqual(lines[1]["returned_document_ids"], ["doc:bob"])
        self.assertEqual([x["limited_count"] for x in lines], [0, 0])

    def test_default_store_profile_still_refuses_rebinding(self):
        directory = self.root / "single"
        with AgentMemory.open(directory, tenant="tenant:test", actor_id="agent:test",
                              scope="project:alice"):
            pass
        with self.assertRaises(StoreIdentityError):
            AgentMemory.open(directory, tenant="tenant:test", actor_id="agent:test",
                             scope="project:bob")


if __name__ == "__main__":
    unittest.main()
