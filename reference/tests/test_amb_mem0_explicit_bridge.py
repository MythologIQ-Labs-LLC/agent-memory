"""Mem0 OSS explicit-memory AMB provider bridge tests (#640).

The real ``mem0`` package is optional; these tests install a fake ``mem0`` module that
exposes the Mem0 2.2.1 public API shape (``Memory.from_config``, ``add(..., infer=)``,
``search(query, *, top_k, filters)``) so the translation contract, version gate, and
no-inference guard are proven without model weights or network.
"""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import amb_mem0_explicit_bridge as bridge  # noqa: E402


@dataclass
class FakeDocument:
    id: str
    content: str
    user_id: str | None = None
    messages: list[dict] | None = None
    timestamp: str | None = None
    context: str | None = None
    source_ids: list[str] | None = None
    tags: list[str] | None = None


class FakeMemoryProvider:
    pass


class FakeLLM:
    def generate_response(self, *args, **kwargs):
        return "should never be reached"


class FakeMemory:
    """Mem0 2.2.1-shaped double: top-level entity kwargs on search are rejected."""

    instances: list["FakeMemory"] = []

    def __init__(self, config):
        self.config = config
        self.rows: list[dict] = []
        self.llm = FakeLLM()
        self.calls: list[tuple] = []
        FakeMemory.instances.append(self)

    @classmethod
    def from_config(cls, config):
        return cls(config)

    def add(self, messages, *, user_id=None, agent_id=None, run_id=None, metadata=None, infer=True, **kwargs):
        self.calls.append(("add", infer))
        if infer:
            raise AssertionError("explicit-memory lane must pass infer=False")
        results = []
        for message in messages:
            mem_id = f"mem-{len(self.rows)}"
            self.rows.append({"id": mem_id, "memory": message["content"], "user_id": user_id, "metadata": dict(metadata or {})})
            results.append({"id": mem_id, "memory": message["content"], "event": "ADD"})
        return {"results": results}

    def search(self, query, *, top_k=20, filters=None, threshold=0.1, rerank=False, **kwargs):
        if any(key in kwargs for key in ("user_id", "agent_id", "run_id", "limit")):
            raise ValueError("Mem0 2.2.1 rejects top-level entity params; use filters")
        if not filters or "user_id" not in filters:
            raise ValueError("filters must contain user_id")
        self.calls.append(("search", top_k, dict(filters)))
        tokens = set(query.lower().split())
        scored = []
        for row in self.rows:
            if row["user_id"] != filters["user_id"]:
                continue
            overlap = len(tokens & set(row["memory"].lower().split()))
            if overlap:
                scored.append((overlap, row))
        scored.sort(key=lambda item: -item[0])
        return {"results": [dict(row, score=float(overlap)) for overlap, row in scored[:top_k]]}


def _install_fakes(version: str = bridge.MEM0_VERSION):
    memory_bench = types.ModuleType("memory_bench")
    memory = types.ModuleType("memory_bench.memory")
    base = types.ModuleType("memory_bench.memory.base")
    models = types.ModuleType("memory_bench.models")
    memory.REGISTRY = {}
    base.MemoryProvider = FakeMemoryProvider
    models.Document = FakeDocument
    mem0 = types.ModuleType("mem0")
    mem0.__version__ = version
    mem0.Memory = FakeMemory
    for name, module in (
        ("memory_bench", memory_bench),
        ("memory_bench.memory", memory),
        ("memory_bench.memory.base", base),
        ("memory_bench.models", models),
        ("mem0", mem0),
    ):
        sys.modules[name] = module
    return memory.REGISTRY


class Mem0ExplicitBridgeTests(unittest.TestCase):
    def setUp(self):
        self._saved = {name: sys.modules.get(name) for name in ("memory_bench", "memory_bench.memory", "memory_bench.memory.base", "memory_bench.models", "mem0")}
        FakeMemory.instances.clear()

    def tearDown(self):
        for name, module in self._saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def test_provider_registers_and_round_trips_with_explicit_memory_and_native_user_scoping(self):
        registry = _install_fakes()
        with tempfile.TemporaryDirectory() as temporary:
            provider_type = bridge.install_amb_mem0_explicit_provider(temporary)
            self.assertIs(registry[bridge.AMB_PROVIDER_KEY], provider_type)
            self.assertEqual(provider_type.concurrency, 1)
            self.assertFalse(provider_type.supports_filters)
            provider = provider_type()
            provider.prepare(Path(temporary) / "store")
            provider.ingest(
                [
                    FakeDocument(id="b-db-decision", content="postgres is the primary database", user_id="test-user", timestamp="2026-01-01T00:00:00Z"),
                    FakeDocument(id="b-cache", content="redis is the cache", user_id="test-user"),
                    FakeDocument(id="b-other", content="postgres secret of the other user", user_id="other-user"),
                ]
            )
            memory = FakeMemory.instances[-1]
            self.assertTrue(all(infer is False for kind, infer in memory.calls if kind == "add"))
            self.assertEqual(memory.rows[0]["metadata"]["doc_id"], "b-db-decision")
            self.assertEqual(memory.rows[0]["metadata"]["source_timestamp"], "2026-01-01T00:00:00Z")

            found, raw = provider.retrieve("which postgres database", k=20, user_id="test-user")
            self.assertEqual([item.id for item in found], ["b-db-decision"])
            self.assertEqual(found[0].source_ids, ["b-db-decision"])
            self.assertEqual(memory.calls[-1], ("search", 20, {"user_id": "test-user"}))
            self.assertEqual(raw["mem0_version"], bridge.MEM0_VERSION)
            self.assertEqual(raw["inference"], "none")
            self.assertIs(raw["query_timestamp_used_as_memory_authority"], False)
            self.assertEqual(raw["unmapped_results"], 0)

    def test_frozen_config_is_disposable_and_pinned(self):
        config = bridge.frozen_mem0_config("/tmp/lane-store")
        self.assertEqual(config["embedder"]["config"]["model"], bridge.EMBEDDER_HF_REPO)
        self.assertEqual(config["embedder"]["config"]["model_kwargs"]["revision"], bridge.EMBEDDER_HF_REVISION)
        self.assertEqual(config["embedder"]["config"]["embedding_dims"], bridge.EMBEDDING_DIMS)
        self.assertEqual(config["vector_store"]["config"]["embedding_model_dims"], bridge.EMBEDDING_DIMS)
        self.assertTrue(config["vector_store"]["config"]["path"].startswith("/tmp/lane-store"))
        self.assertTrue(config["history_db_path"].startswith("/tmp/lane-store"))
        self.assertIs(config["vector_store"]["config"]["on_disk"], True)
        self.assertNotIn("gemini", repr(config).lower())
        frozen = bridge.frozen_configuration()
        self.assertEqual(frozen["package"], "mem0ai==2.2.1")
        self.assertEqual(frozen["tag_commit"], "94c3fe9f238f3dbf29c9ce98643bd71eb13077cd")

    def test_llm_guard_fails_closed_after_preparation(self):
        _install_fakes()
        with tempfile.TemporaryDirectory() as temporary:
            provider = bridge.install_amb_mem0_explicit_provider(temporary)()
            provider.prepare(Path(temporary) / "store")
            with self.assertRaisesRegex(RuntimeError, "forbids inference"):
                provider._memory.llm.generate_response(messages=[])

    def test_version_mismatch_refuses_before_any_memory_is_built(self):
        _install_fakes(version="2.0.18")
        with tempfile.TemporaryDirectory() as temporary:
            provider = bridge.install_amb_mem0_explicit_provider(temporary)()
            with self.assertRaisesRegex(RuntimeError, "Mem0 version mismatch"):
                provider.prepare(Path(temporary) / "store")
            self.assertEqual(FakeMemory.instances, [])

    def test_rejected_add_is_an_error_not_a_silent_miss(self):
        _install_fakes()

        class RejectingMemory(FakeMemory):
            def add(self, messages, **kwargs):
                return {"results": []}

        sys.modules["mem0"].Memory = RejectingMemory
        with tempfile.TemporaryDirectory() as temporary:
            provider = bridge.install_amb_mem0_explicit_provider(temporary)()
            provider.prepare(Path(temporary) / "store")
            with self.assertRaisesRegex(RuntimeError, "did not store"):
                provider.ingest([FakeDocument(id="b-x", content="x", user_id="u")])

    def test_bridge_is_benchmark_agnostic(self):
        source = Path(bridge.__file__).read_text(encoding="utf-8")
        for forbidden in ("precisionmembench", "gold", "expect", "beliefId", "retrieval.cases", "mission"):
            self.assertNotIn(forbidden, source.lower().replace("explicit-memory", ""), forbidden)
        self.assertNotIn("agentmem_ref", source)


if __name__ == "__main__":
    unittest.main()
