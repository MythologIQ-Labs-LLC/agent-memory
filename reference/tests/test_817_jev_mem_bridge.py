"""Offline, dependency-free contract checks for the Jev-Mem comparator adapter."""
from __future__ import annotations

import importlib
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

bridge = importlib.import_module("longmemeval_jev_mem_bridge")


class IdMappingTests(unittest.TestCase):
    def node(self, **attributes):
        return types.SimpleNamespace(attributes=attributes)

    def test_rank_keeps_native_node_order(self):
        nodes = [self.node(doc_id="s2"), self.node(doc_id="s1"),
                 self.node(doc_id="s2"), self.node(doc_id="s3")]
        ids, unmapped = bridge.ranked_doc_ids(nodes, {"s1", "s2", "s3"})
        self.assertEqual(ids, ["s2", "s1", "s3"])
        self.assertEqual(unmapped, 0)

    def test_unknown_or_unmapped_never_fabricates_gold(self):
        nodes = [self.node(doc_id="not-in-corpus"), self.node(content="s1"), self.node(doc_id=42)]
        ids, unmapped = bridge.ranked_doc_ids(nodes, {"s1"})
        self.assertEqual(ids, [])
        self.assertEqual(unmapped, 3)

    def test_metadata_id_mapping_not_text_guessing(self):
        node = self.node(doc_id="s2", raw_content="answer is s1")
        ids, unmapped = bridge.ranked_doc_ids([node], {"s1", "s2"})
        self.assertEqual((ids, unmapped), (["s2"], 0))

    def test_depth_limit(self):
        nodes = [self.node(doc_id=str(i)) for i in range(64)]
        ids, unmapped = bridge.ranked_doc_ids(nodes, {str(i) for i in range(64)})
        self.assertEqual(len(ids), bridge.MAX_DEPTH)
        self.assertEqual(unmapped, 0)


class SourcePinTests(unittest.TestCase):
    def test_exact_source_and_config_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/"config").mkdir()
            (path/"config"/"laya_mem.json").write_text("{}", encoding="utf-8")
            with patch.object(bridge, "_git", side_effect=[
                bridge.UPSTREAM_SHA, "", bridge.CONFIG_BLOB_SHA
            ]) as git:
                self.assertEqual(bridge.verify_upstream(path)["source_revision"], bridge.UPSTREAM_SHA)
                self.assertEqual(git.call_count, 3)

    def test_modified_checkout_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(bridge, "_git", side_effect=[bridge.UPSTREAM_SHA, " M memory/query_engine.py"]):
                with self.assertRaisesRegex(RuntimeError, "local modifications"):
                    bridge.verify_upstream(Path(tmp))

    def test_wrong_revision_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(bridge, "_git", return_value="0" * 40):
                with self.assertRaisesRegex(RuntimeError, "revision mismatch"):
                    bridge.verify_upstream(Path(tmp))

    def test_wrong_config_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/"config").mkdir()
            (path/"config"/"laya_mem.json").write_text("{}", encoding="utf-8")
            with patch.object(bridge, "_git", side_effect=[bridge.UPSTREAM_SHA, "", "0" * 40]):
                with self.assertRaisesRegex(RuntimeError, "configuration"):
                    bridge.verify_upstream(path)

    def test_no_source_root_refuses_install(self):
        with patch.dict("os.environ", {"JEV_MEM_SOURCE_ROOT": ""}):
            with self.assertRaisesRegex(RuntimeError, "JEV_MEM_SOURCE_ROOT"):
                bridge.install_longmemeval_jev_mem_backend(lambda *a, **kw: None)

    def test_valid_registered_identity(self):
        identity = bridge.identity()
        self.assertEqual(identity["system_kind"], "external_memory")
        self.assertEqual(identity["system_revision"], bridge.UPSTREAM_SHA)
        self.assertEqual(identity["configuration"]["qualification"], "candidate until real model+dataset evidence and independent review")


class InstrumentationTests(unittest.TestCase):
    def test_decision_counter_separates_model_calls_cache_and_fallback(self):
        log = bridge.DecisionCounter()
        log.emit("jev_decision", operation="typing", source="laya", usage={"input_tokens": 7})
        log.emit("jev_decision", operation="typing", source="cache", usage={})
        log.emit("jev_decision", operation="relation", source="laya", usage={"output_tokens": 2})
        log.emit("jev_fallback", operation="routing", reason="laya_deadline")
        log.emit("memory_constructed", memory_id="m1")
        snap = log.snapshot()
        self.assertEqual(snap["model_decisions"], 2)
        self.assertEqual(snap["decisions_by_operation"]["typing"], {"laya": 1, "cache": 1})
        self.assertEqual(snap["fallback_events"], [{"operation": "routing", "reason": "laya_deadline"}])
        self.assertEqual(snap["usage"], {"input_tokens": 7, "output_tokens": 2})
        self.assertEqual(snap["events"], {"memory_constructed": 1})

    def test_shared_laya_weights_load_once_per_checkpoint(self):
        calls = []
        fake = types.ModuleType("laya")
        fake.load = lambda model_id_or_path="m", device=None, token=None, subfolder=None: (
            calls.append((model_id_or_path, device, subfolder)) or object())
        with patch.dict("sys.modules", {"laya": fake}), patch.dict(bridge._LAYA_AGENTS, clear=True):
            bridge.share_laya_weights()
            bridge.share_laya_weights()  # idempotent: never wraps twice
            first = fake.load("m", device="cpu")
            self.assertIs(fake.load("m", device="cpu"), first)
            self.assertIsNot(fake.load("m", device="cpu", subfolder="multilingual"), first)
        self.assertEqual(calls, [("m", "cpu", None), ("m", "cpu", "multilingual")])


if __name__ == "__main__":
    unittest.main()
