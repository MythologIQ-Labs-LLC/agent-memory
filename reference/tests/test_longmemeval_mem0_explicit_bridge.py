"""Mem0 OSS explicit-memory backend for the LongMemEval parity lane (#640, lane v2).

Runs the runner's full protocol against a stub ``mem0`` module so the bridge's contract
(explicit memory, per-call namespaces, metadata identity mapping, fail-closed posture)
is proven offline. The real stack is exercised by the manual lane workflow only.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference"
RUNNER = REFERENCE / "run_longmemeval.py"
FIXTURE = REFERENCE / "fixtures" / "benchmarks" / "longmemeval" / "synthetic.json"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

import amb_mem0_explicit_bridge as amb_bridge  # noqa: E402
import longmemeval_mem0_explicit_bridge as bridge  # noqa: E402


def _runner():
    spec = importlib.util.spec_from_file_location("run_longmemeval", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tokens(text: str) -> set[str]:
    return {token.lower().strip(".,?!") for token in text.split()}


class _StubMemory:
    """Enough of ``mem0.Memory`` to prove the bridge's calls; no embeddings, no LLM."""

    instances: list["_StubMemory"] = []

    def __init__(self, config: dict) -> None:
        self.config = config
        self.store: dict[str, list[tuple[str, dict]]] = {}
        self.adds: list[dict] = []
        self.searches: list[dict] = []
        self.llm = object()
        self.vector_store = types.SimpleNamespace(client=types.SimpleNamespace(close=lambda: None))
        _StubMemory.instances.append(self)

    @classmethod
    def from_config(cls, config: dict) -> "_StubMemory":
        return cls(config)

    def add(self, messages, *, user_id, metadata, infer):
        self.adds.append({"messages": messages, "user_id": user_id, "metadata": metadata, "infer": infer})
        text = messages[0]["content"]
        self.store.setdefault(user_id, []).append((text, dict(metadata)))
        if not text.strip():
            return {"results": []}
        return {"results": [{"id": f"m{len(self.adds)}", "memory": text, "event": "ADD"}]}

    def search(self, query, *, top_k, filters):
        self.searches.append({"query": query, "top_k": top_k, "filters": filters})
        query_tokens = _tokens(query)
        scored = []
        for text, metadata in self.store.get(filters["user_id"], []):
            overlap = len(query_tokens & _tokens(text))
            if overlap:
                scored.append((overlap, text, metadata))
        scored.sort(key=lambda entry: (-entry[0], entry[2].get("doc_id", "")))
        results = [{"id": f"r{i}", "memory": text, "score": overlap / 10, "metadata": metadata} for i, (overlap, text, metadata) in enumerate(scored[:top_k])]
        # One product-shaped result without benchmark identity: must be counted, never ranked.
        results.append({"id": "orphan", "memory": "unrelated", "score": 0.11, "metadata": {}})
        return {"results": results}


def _stub_mem0(version: str = "2.2.1") -> types.ModuleType:
    module = types.ModuleType("mem0")
    module.__version__ = version
    module.Memory = _StubMemory
    return module


class FrozenConfigurationTests(unittest.TestCase):
    def test_lane_v2_reuses_lane_v1_mem0_configuration_except_the_collection(self) -> None:
        self.assertEqual(bridge.MEM0_VERSION, amb_bridge.MEM0_VERSION)
        self.assertEqual(bridge.MEM0_TAG_COMMIT, amb_bridge.MEM0_TAG_COMMIT)
        self.assertEqual(bridge.EMBEDDER_HF_REVISION, amb_bridge.EMBEDDER_HF_REVISION)
        with tempfile.TemporaryDirectory() as temporary:
            lane = bridge.frozen_mem0_lane_config(temporary)
            amb = amb_bridge.frozen_mem0_config(temporary)
        self.assertEqual(lane["vector_store"]["config"]["collection_name"], bridge.VECTOR_STORE_COLLECTION)
        self.assertNotEqual(lane["vector_store"]["config"]["collection_name"], amb["vector_store"]["config"]["collection_name"])
        lane["vector_store"]["config"]["collection_name"] = amb["vector_store"]["config"]["collection_name"]
        self.assertEqual(lane, amb)
        frozen = bridge.frozen_configuration()
        self.assertEqual(frozen["embedder"], amb_bridge.frozen_configuration()["embedder"])
        self.assertEqual(frozen["optional_components"], amb_bridge.OPTIONAL_COMPONENTS)
        self.assertEqual(frozen["search"]["top_k"], 50)
        self.assertIn("mem0ai==2.2.1", bridge.DEPENDENCY_PINS)
        self.assertEqual(frozen["dependency_pins"], list(bridge.DEPENDENCY_PINS))
        self.assertEqual(frozen["concurrency"], 1)

    def test_identity_binds_system_adapter_and_posture(self) -> None:
        identity = bridge.identity({"mem0ai": "2.2.1", "fastembed_installed": False, "spacy_installed": False})
        self.assertEqual(identity["system_id"], bridge.SYSTEM_ID)
        self.assertEqual(identity["system_kind"], "external_memory")
        self.assertEqual(identity["system_revision"], amb_bridge.MEM0_TAG_COMMIT)
        self.assertEqual(identity["adapter_id"], "reference/longmemeval_mem0_explicit_bridge.py")
        self.assertTrue(len(identity["adapter_revision"]) == 40 or identity["adapter_revision"].startswith("sha256:"))
        self.assertEqual(identity["configuration"], bridge.frozen_configuration())
        self.assertEqual(identity["install_posture"]["mem0ai"], "2.2.1")
        self.assertEqual(identity["authority_effect"], "none")
        self.assertEqual(identity["lane_id"], "longmemeval-s-retrieval-parity-v1")


class StubbedProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        _StubMemory.instances.clear()
        self.M = _runner()
        self.temporary = tempfile.TemporaryDirectory()
        self.patcher = mock.patch.dict(sys.modules, {"mem0": _stub_mem0()})
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()
        self.temporary.cleanup()

    def test_version_and_extras_posture_fail_closed(self) -> None:
        with mock.patch.dict(sys.modules, {"mem0": _stub_mem0("2.2.0")}):
            with self.assertRaisesRegex(RuntimeError, "version mismatch"):
                bridge.Mem0ExplicitLongMemEvalBackend(self.temporary.name).open()
        with mock.patch.object(bridge, "optional_component_posture", return_value={"fastembed_installed": True, "spacy_installed": False}):
            with self.assertRaisesRegex(RuntimeError, "forbids the fastembed extra"):
                bridge.Mem0ExplicitLongMemEvalBackend(self.temporary.name).open()
        with mock.patch.object(bridge, "optional_component_posture", return_value={"fastembed_installed": False, "spacy_installed": True}):
            with self.assertRaisesRegex(RuntimeError, "forbids the spaCy extra"):
                bridge.Mem0ExplicitLongMemEvalBackend(self.temporary.name).open()
        with self.assertRaisesRegex(RuntimeError, "must be opened"):
            bridge.Mem0ExplicitLongMemEvalBackend(self.temporary.name).retrieve("q", [], 0)

    def test_runner_scores_mem0_through_the_registered_backend(self) -> None:
        M = self.M
        name = bridge.install_longmemeval_mem0_explicit_backend(M.register_external_backend, store_dir=self.temporary.name)
        self.assertEqual(name, "mem0_explicit")
        memory = _StubMemory.instances[-1]
        self.assertEqual(memory.config["vector_store"]["config"]["collection_name"], bridge.VECTOR_STORE_COLLECTION)
        with self.assertRaisesRegex(RuntimeError, "forbids inference"):
            memory.llm.generate_response(messages=[])

        report = M.run(FIXTURE, corpus_class="synthetic", backends=("lexical_overlap", "mem0_explicit"), granularities=("session", "turn"))
        identity = report["execution"]["external_backends"]["mem0_explicit"]
        self.assertEqual(identity["system_id"], "mem0-oss")
        self.assertEqual(identity["system_revision"], amb_bridge.MEM0_TAG_COMMIT)
        self.assertEqual(identity["install_posture"], {"mem0ai": "2.2.1", "fastembed_installed": False, "spacy_installed": False})
        self.assertEqual(identity["configuration"]["search"]["top_k"], 50)

        corpus_ids: set[str] = set()
        rows_seen: list[dict] = []
        for plane in ("session", "turn"):
            backend = report["planes"][plane]["backends"]["mem0_explicit"]
            self.assertEqual(backend["failures"]["runtime_failure_count"], 0)
            self.assertEqual(backend["failures"]["out_of_corpus_returned_count"], 0)
            self.assertEqual(backend["external_system"]["unmapped_result_count_total"], len(backend["rows"]))
            self.assertIn("ingest_seconds_total", backend["timing"])
            self.assertGreater(backend["aggregate"]["headline"]["recall_all@5"], 0.0)
            for row in json.loads(FIXTURE.read_text(encoding="utf-8")):
                corpus_ids.update(item["id"] for item in M.corpus(row, plane)[0])
            rows_seen.extend(backend["rows"])
        namespaces = [row["mem0_namespace"] for row in rows_seen]
        self.assertEqual(len(namespaces), len(set(namespaces)), "one Mem0 namespace per question and plane")
        for row in rows_seen:
            self.assertEqual(row["search_top_k"], 50)
            self.assertEqual(row["unmapped_result_count"], 1)
            self.assertTrue(set(row["ranked_top"]).issubset(corpus_ids))

        for add in memory.adds:
            self.assertIs(add["infer"], False, "explicit memory only")
            self.assertIn(add["metadata"]["doc_id"], corpus_ids)
            text = add["messages"][0]["content"]
            self.assertFalse(any(item_id in text for item_id in corpus_ids), "benchmark ids never enter memory text")
            self.assertTrue(add["user_id"].startswith("lme-"))
        for search in memory.searches:
            self.assertEqual(search["top_k"], 50)
            self.assertIn(search["filters"]["user_id"], namespaces)
        self.assertEqual({add["user_id"] for add in memory.adds}, set(namespaces))

    def test_ingestion_refusals_are_counted_not_hidden(self) -> None:
        M = self.M
        bridge.install_longmemeval_mem0_explicit_backend(M.register_external_backend, store_dir=self.temporary.name)
        retrieve = M.RETRIEVERS["mem0_explicit"]
        outcome = retrieve("which editor", [{"id": "a_1", "text": "", "date": ""}, {"id": "b_1", "text": "VS Code editor", "date": ""}], 0)
        self.assertEqual(len(outcome["ingestion_failures"]), 1)
        self.assertEqual(outcome["ranked"], ["b_1"])
        self.assertEqual(outcome["unmapped_result_count"], 1)


if __name__ == "__main__":
    unittest.main()
