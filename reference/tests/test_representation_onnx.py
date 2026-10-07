"""Pinned ONNX representation provider (#669).

Model-dependent tests need the optional extra ``semantic`` and the pinned model in
``$AGENT_MEMORY_REPRESENTATION_DIR`` (see ``python -m agentmem_ref.runtime.representation_onnx
fetch``). They skip when either is absent, unless ``AGENT_MEMORY_REQUIRE_REPRESENTATION=1``,
which turns the skip into a failure. The semantic-representation workflow sets it.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref.runtime import representation_onnx as ro  # noqa: E402

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "runtime" / "semantic-representation-golden-v1.json"
REQUIRED = os.environ.get("AGENT_MEMORY_REQUIRE_REPRESENTATION") == "1"


def _model_available() -> tuple[bool, str]:
    for name in ("onnxruntime", "tokenizers", "numpy"):
        if importlib.util.find_spec(name) is None:
            return False, f"optional extra 'semantic' not installed ({name})"
    try:
        ro.verify_model_dir(ro.resolve_model_dir())
    except ro.RepresentationUnavailable as exc:
        return False, str(exc)
    return True, ""


AVAILABLE, REASON = _model_available()


def requires_model(test):
    if AVAILABLE:
        return test
    if REQUIRED:
        def failing(self):
            self.fail(f"AGENT_MEMORY_REQUIRE_REPRESENTATION=1 but the provider is unavailable: {REASON}")
        failing.__name__ = test.__name__
        return failing
    return unittest.skip(f"pinned representation unavailable: {REASON}")(test)


class ManifestTests(unittest.TestCase):
    def test_manifest_pins_revision_and_every_file(self):
        self.assertEqual(ro.MODEL_REVISION, "b207367332321f8e44f96e224ef15bc607f4dbf0")
        self.assertEqual(
            set(ro.PINNED_FILES),
            {"onnx/model.onnx", "tokenizer.json", "config.json", "modules.json",
             "1_Pooling/config.json", "sentence_bert_config.json"},
        )
        for digest, _size in ro.PINNED_FILES.values():
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(ro.NUMERICS["truncation_max_length"], 512)
        self.assertEqual(ro.NUMERICS["output_canonicalisation"], "float32")

    def test_config_digest_binds_library_versions(self):
        a = ro.config_digest({"onnxruntime": "1.30.0", "tokenizers": "0.23.2", "numpy": "2.4.6"})
        b = ro.config_digest({"onnxruntime": "1.30.0", "tokenizers": "0.23.2", "numpy": "2.4.7"})
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith("sha256:"))

    def test_missing_model_dir_is_unavailable(self):
        with self.assertRaises(ro.RepresentationUnavailable):
            ro.verify_model_dir(Path(tempfile.mkdtemp()))

    def test_fetch_refuses_symlinked_target(self):
        base = Path(tempfile.mkdtemp())
        (base / "real").mkdir()
        (base / "link").symlink_to(base / "real")
        with self.assertRaises(ro.RepresentationUnavailable):
            ro.fetch(base / "link")


class ProviderTests(unittest.TestCase):
    @requires_model
    def test_tampered_model_file_is_refused(self):
        source = ro.resolve_model_dir()
        copy = Path(tempfile.mkdtemp()) / "model"
        shutil.copytree(source, copy)
        (copy / "config.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(ro.RepresentationUnavailable):
            ro.OnnxSentenceEmbeddingProvider(copy)

    @requires_model
    def test_spec_and_unit_norm_float32(self):
        provider = ro.OnnxSentenceEmbeddingProvider()
        self.assertEqual(provider.spec.dimensions, 384)
        self.assertTrue(provider.spec.deterministic_rebuild)
        vector = provider.embed("The user prefers concise technical explanations.")
        self.assertEqual(len(vector), 384)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in vector)), 1.0, places=5)
        self.assertEqual(vector, provider.embed("The user prefers concise technical explanations."))

    @requires_model
    def test_truncation_at_512_tokens(self):
        provider = ro.OnnxSentenceEmbeddingProvider()
        encoding = provider._state.tokenizer.encode("word " * 2000)
        self.assertEqual(len(encoding.ids), 512)

    @requires_model
    def test_golden_vectors_and_topk_order(self):
        golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
        provider = ro.OnnxSentenceEmbeddingProvider()
        self.assertEqual(provider.spec.representation_version, golden["representation_version"])
        for text, expected in golden["vectors"].items():
            observed = provider.embed(text)
            self.assertLessEqual(max(abs(a - b) for a, b in zip(observed, expected)), golden["tolerance_max_abs"], text)
        corpus = [provider.embed(text) for text in golden["corpus"]]
        for query, expected_top in golden["queries"].items():
            q = provider.embed(query)
            scores = [sum(a * b for a, b in zip(q, v)) for v in corpus]
            top = sorted(range(len(corpus)), key=lambda i: (-scores[i], i))[:3]
            self.assertEqual(top, expected_top, query)


if __name__ == "__main__":
    unittest.main()
