"""Offline contract checks for the MemPalace LongMemEval comparator adapter.

The adapter module imports only the standard library, so the id-mapping, repeat and
refusal checks run anywhere. Checks that need the pinned product install or the pinned
model cache skip when either is absent.
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

bridge = importlib.import_module("longmemeval_mempalace_bridge")

ITEMS = [{"id": "answer_a_1", "text": "x", "date": "d"}, {"id": "b", "text": "y", "date": "d"},
         {"id": "answer_a_1", "text": "x", "date": "d"}]
MODEL_DIR = os.environ.get("MEMPALACE_BENCH_MODEL_DIR")


def hit(drawer_id, source_path, **extra):
    return {"drawer_id": drawer_id, "source_path": source_path, "text": "t", **extra}


class CorpusIdTests(unittest.TestCase):
    def test_identical_repeats_are_accepted(self):
        self.assertEqual(bridge.validate_corpus_ids(ITEMS), ["answer_a_1", "b", "answer_a_1"])

    def test_conflicting_repeat_or_bad_id_is_refused(self):
        with self.assertRaisesRegex(ValueError, "different text"):
            bridge.validate_corpus_ids([{"id": "a", "text": "x"}, {"id": "a", "text": "z"}])
        for bad in ([{"id": "", "text": "x"}], [{"id": 3, "text": "x"}], [{"id": "a", "text": None}]):
            with self.assertRaises(ValueError):
                bridge.validate_corpus_ids(bad)

    def test_occurrences_get_distinct_opaque_keys_without_the_benchmark_id(self):
        keys = bridge.occurrence_keys(["answer_a_1", "b", "answer_a_1"])
        self.assertEqual(len(set(keys)), 3)
        self.assertEqual(keys[0], bridge.opaque_key("answer_a_1"))
        self.assertEqual(keys, bridge.occurrence_keys(["answer_a_1", "b", "answer_a_1"]))  # deterministic
        for key in keys:
            self.assertNotIn("answer", key)
            self.assertNotIn("noans", key)
            self.assertRegex(key, r"^lme-[0-9a-f]{32}$")


class RankMappingTests(unittest.TestCase):
    def setUp(self):
        self.keys = bridge.occurrence_keys(["s1", "s2", "s1", "s3"])
        self.drawers = bridge.DrawerMap()
        self.drawers.record("d1", "s1", self.keys[0])
        self.drawers.record("d2", "s2", self.keys[1])
        self.drawers.record("d1", "s1", self.keys[2])  # repeat occurrence: already_exists, same drawer
        self.drawers.record("d1", "s3", self.keys[3])  # distinct id, identical content: same drawer

    def test_native_order_and_chunk_hits_collapse(self):
        hits = [hit("d2", self.keys[1]), hit("d2", self.keys[1]), hit("d1", self.keys[0])]
        ranked, unmapped, stats = bridge.ranked_doc_ids(hits, self.drawers)
        self.assertEqual(ranked, ["s2", "s1", "s3"])
        self.assertEqual(unmapped, 0)
        self.assertEqual(stats["duplicate_hit_count"], 1)

    def test_unknown_drawer_or_foreign_source_is_unmapped_never_guessed(self):
        hits = [hit("unknown", self.keys[0]), hit("d2", "lme-not-filed"), {"text": "s2"}, "junk",
                hit("d2", self.keys[1])]
        ranked, unmapped, _ = bridge.ranked_doc_ids(hits, self.drawers)
        self.assertEqual((ranked, unmapped), (["s2"], 4))

    def test_also_in_refs_follow_their_hit(self):
        drawers = bridge.DrawerMap()
        drawers.record("d1", "s1", "k1")
        drawers.record("d9", "s9", "k9")
        hits = [hit("d1", "k1", also_in=[{"drawer_id": "d9", "source_path": "k9"}, {"drawer_id": "x"}])]
        ranked, unmapped, stats = bridge.ranked_doc_ids(hits, drawers)
        self.assertEqual((ranked, unmapped, stats["also_in_ref_count"]), (["s1", "s9"], 1, 2))

    def test_depth_is_capped(self):
        drawers = bridge.DrawerMap()
        for i in range(80):
            drawers.record(f"d{i}", f"s{i}", f"k{i}")
        ranked, _, _ = bridge.ranked_doc_ids([hit(f"d{i}", f"k{i}") for i in range(80)], drawers)
        self.assertEqual(len(ranked), bridge.MAX_DEPTH)

    def test_tool_payload_unwraps_and_surfaces_errors(self):
        payload, is_error = bridge.tool_payload(
            {"result": {"content": [{"type": "text", "text": '{"success": true}'}], "isError": False}})
        self.assertEqual((payload, is_error), ({"success": True}, False))
        with self.assertRaisesRegex(RuntimeError, "MCP error"):
            bridge.tool_payload({"error": {"code": -32005, "message": "stale"}})
        with self.assertRaises(RuntimeError):
            bridge.tool_payload({"result": {"content": []}})


class RefusalTests(unittest.TestCase):
    def test_credentials_and_non_default_embedder_are_refused(self):
        for env in ({"OPENAI_API_KEY": "sk-x"}, {"ANTHROPIC_API_KEY": "x"},
                    {"MEMPALACE_EMBEDDING_API_URL": "http://h"}, {"MEMPALACE_EMBEDDING_MODEL": "embeddinggemma"}):
            with self.assertRaisesRegex(RuntimeError, "refusing"):
                bridge.refuse_credentials(env)
        bridge.refuse_credentials({"MEMPALACE_EMBEDDING_MODEL": "minilm", "PATH": "/bin"})

    def test_adapter_refuses_credentials_before_touching_the_product(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-x"}), \
                patch.object(bridge, "verify_installed_package", side_effect=AssertionError("reached")):
            with self.assertRaisesRegex(RuntimeError, "refusing"):
                bridge.MemPalaceLongMemEval(Path(tempfile.gettempdir()), Path(tempfile.gettempdir()))

    def test_install_entry_requires_disposable_root_and_model_dir(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "MEMPALACE_BENCH_ROOT"):
                bridge.install_longmemeval_mempalace_backend(lambda *a, **k: None)

    def test_unpinned_package_tree_or_version_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "__init__.py").write_text("x = 1\n")
            with patch.object(bridge.importlib.metadata, "version", return_value=bridge.MEMPALACE_VERSION):
                with self.assertRaisesRegex(RuntimeError, "not the pinned"):
                    bridge.verify_installed_package(Path(tmp))
            with patch.object(bridge.importlib.metadata, "version", return_value="3.10.9"):
                with self.assertRaisesRegex(RuntimeError, "pinned 3.11.0"):
                    bridge.verify_installed_package(Path(tmp))

    def test_tampered_model_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            for rel in bridge.MODEL_FILE_SHA256:
                (Path(tmp) / rel).parent.mkdir(parents=True, exist_ok=True)
                (Path(tmp) / rel).write_bytes(b"tampered")
            with self.assertRaisesRegex(RuntimeError, "sha256"):
                bridge.verify_model_dir(Path(tmp))

    def test_child_environment_is_clean(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-x", "MEMPALACE_BACKEND": "qdrant"}):
            env = bridge.child_environment(Path("/q"), "1", "0")
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("MEMPALACE_BACKEND", env)
        self.assertEqual(env["MEMPALACE_CONFIG_DIR"], "/q/config")
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")

    def test_identity_satisfies_runner_contract(self):
        ident = bridge.identity()
        for field in ("system_id", "system_kind", "system_revision", "adapter_id", "adapter_revision", "configuration"):
            self.assertIn(field, ident)
        self.assertEqual(ident["system_revision"], f"3.11.0@{bridge.MEMPALACE_TAG_COMMIT}")
        self.assertEqual(ident["adapter_revision"], "0.1.0-candidate")


@unittest.skipUnless(importlib.util.find_spec("mempalace") is not None, "mempalace not installed")
class InstalledProductTests(unittest.TestCase):
    def test_installed_package_is_the_pinned_tree(self):
        info = bridge.verify_installed_package()
        self.assertEqual(info["package_tree_sha256"], bridge.MEMPALACE_PACKAGE_TREE_SHA256)

    @unittest.skipUnless(MODEL_DIR, "MEMPALACE_BENCH_MODEL_DIR not set")
    def test_pinned_model_cache_and_one_question_round_trip(self):
        bridge.verify_model_dir(Path(MODEL_DIR))
        with tempfile.TemporaryDirectory() as tmp:
            adapter = bridge.MemPalaceLongMemEval(Path(tmp), Path(MODEL_DIR))
            items = [{"id": "answer_e_1", "text": "For Python work I prefer VS Code for its debugger.", "date": "d"},
                     {"id": "f_1", "text": "We had pizza for lunch and talked about the weather.", "date": "d"},
                     {"id": "answer_e_1", "text": "For Python work I prefer VS Code for its debugger.", "date": "d"},
                     {"id": "g_1", "text": "   ", "date": "d"}]
            out = adapter("Which editor does the user prefer for Python?", items, 0)
            self.assertEqual(out["ranked"][0], "answer_e_1")
            self.assertEqual(set(out["ranked"]), {"answer_e_1", "f_1"})
            self.assertEqual((out["unmapped_result_count"], out["already_exists_count"], out["skipped_blank_items"]),
                             (0, 1, 1))
            self.assertEqual(out["ingestion_failures"], [])
            self.assertEqual(list(Path(tmp).iterdir()), [])  # per-question directory removed


if __name__ == "__main__":
    unittest.main()
