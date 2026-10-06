from __future__ import annotations

import sys
import types
from dataclasses import dataclass

import amb_agent_memory_bridge as bridge


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


def _install_fake_amb(monkeypatch):
    memory_bench = types.ModuleType("memory_bench")
    memory = types.ModuleType("memory_bench.memory")
    base = types.ModuleType("memory_bench.memory.base")
    models = types.ModuleType("memory_bench.models")
    memory.REGISTRY = {}
    base.MemoryProvider = FakeMemoryProvider
    models.Document = FakeDocument
    monkeypatch.setitem(sys.modules, "memory_bench", memory_bench)
    monkeypatch.setitem(sys.modules, "memory_bench.memory", memory)
    monkeypatch.setitem(sys.modules, "memory_bench.memory.base", base)
    monkeypatch.setitem(sys.modules, "memory_bench.models", models)
    return memory.REGISTRY


def test_scope_and_logical_id_are_stable_and_separate():
    assert bridge._scope("user:a") == bridge._scope("user:a")
    assert bridge._scope("user:a") != bridge._scope("user:b")
    assert bridge._logical_id("doc:1", "user:a") == bridge._logical_id("doc:1", "user:a")
    assert bridge._logical_id("doc:1", "user:a") != bridge._logical_id("doc:1", "user:b")


def test_provider_registers_and_round_trips_through_public_agent_memory(tmp_path, monkeypatch):
    registry = _install_fake_amb(monkeypatch)
    provider_type = bridge.install_amb_agent_memory_provider(
        tmp_path,
        agent_memory_revision="a" * 40,
    )
    assert registry[bridge.AMB_PROVIDER_KEY] is provider_type
    assert provider_type.concurrency == 1

    provider = provider_type()
    provider.prepare(tmp_path / "store")
    provider.ingest(
        [
            FakeDocument(id="doc:a", content="The launch code name is aurora", user_id="user:a"),
            FakeDocument(id="doc:b", content="The garden has lavender", user_id="user:b"),
        ]
    )

    found, raw = provider.retrieve("launch code name aurora", k=5, user_id="user:a")
    assert [item.id for item in found] == ["doc:a"]
    assert raw["agent_memory_revision"] == "a" * 40
    assert raw["amb_revision"] == bridge.AMB_REVISION
    assert raw["query_timestamp_used_as_memory_authority"] is False

    isolated, _ = provider.retrieve("lavender", k=5, user_id="user:a")
    assert all(item.id != "doc:b" for item in isolated)


def test_retrieve_returns_the_facade_prefix_under_the_case_budget(tmp_path, monkeypatch):
    # Bridge 0.2.0 (contract 1.4.0, #670): truncation is the facade's ranked-prefix policy.
    _install_fake_amb(monkeypatch)
    provider_type = bridge.install_amb_agent_memory_provider(tmp_path, agent_memory_revision="b" * 40)
    provider = provider_type()
    provider.prepare(tmp_path / "store")
    provider.ingest(
        [
            FakeDocument(id=f"doc:{index}", content=f"release branch note {index}", user_id="user:k")
            for index in range(4)
        ]
    )
    found, raw = provider.retrieve("release branch note", k=3, user_id="user:k")
    assert bridge.BRIDGE_VERSION == "0.2.0"
    assert raw["bridge_version"] == "0.2.0"
    assert len(found) == 3
    assert raw["admitted_count"] == 4
    assert raw["returned_count"] == 3
    assert raw["return_policy"]["requested_k"] == 3
    assert raw["return_policy"]["applied"] is True
    assert raw["return_policy"]["authority_effect"] == "none"
    assert raw["return_policy"]["admitted_count"] == 4
    try:
        provider.retrieve("release branch note", k=0, user_id="user:k")
    except ValueError:
        pass
    else:  # pragma: no cover - the refusal is the contract (#670)
        raise AssertionError("k=0 must be refused before recall")


def test_provider_resume_reuses_revision_bound_sidecar(tmp_path, monkeypatch):
    registry = _install_fake_amb(monkeypatch)
    provider_type = bridge.install_amb_agent_memory_provider(tmp_path, agent_memory_revision="b" * 40)
    provider = provider_type()
    store = tmp_path / "store"
    provider.prepare(store)
    provider.ingest([FakeDocument(id="doc:1", content="remember the blue lantern", user_id="user:1")])

    resumed = registry[bridge.AMB_PROVIDER_KEY]()
    resumed.prepare(store, reset=False)
    found, _ = resumed.retrieve("blue lantern", k=3, user_id="user:1")
    assert [item.id for item in found] == ["doc:1"]
