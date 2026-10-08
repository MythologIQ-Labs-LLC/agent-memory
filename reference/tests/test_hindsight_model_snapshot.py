"""Offline tests for Hindsight H1 model bootstrap. Never download in CI."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentmem_ref.evaluation import hindsight_model_snapshot as snap

BYTES = {
    "onnx/model.onnx": b"synthetic-onnx-byte-stream",
    "tokenizer.json": b'{"tokenizer":"synthetic"}',
    "tokenizer_config.json": b'{"max_length":512}',
    "special_tokens_map.json": b'{"cls_token":"[CLS]"}',
    "config.json": b'{"hidden_size":384}',
}
PIN = hashlib.sha256(BYTES["onnx/model.onnx"]).hexdigest()


def synthetic_download(relative: str, target: Path, limit: int) -> None:
    assert relative in BYTES
    assert len(BYTES[relative]) <= limit
    target.write_bytes(BYTES[relative])


class HindsightSnapshotContractTests(unittest.TestCase):
    def test_revision_urls_are_exact_and_whitelisted(self):
        self.assertEqual(len(snap.MODEL_REVISION), 40)
        self.assertTrue(snap.artifact_url("onnx/model.onnx").startswith(
            f"https://huggingface.co/intfloat/multilingual-e5-small/resolve/{snap.MODEL_REVISION}/"
        ))
        self.assertIn("/onnx/model.onnx?download=true", snap.artifact_url("onnx/model.onnx"))
        with self.assertRaises(snap.SnapshotUnavailable):
            snap.artifact_url("../../refs/main/model.onnx")

    def test_bootstrap_and_identity_without_any_network(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(snap, "ONNX_SHA256", PIN):
            target = Path(tmp) / "snapshot"
            with mock.patch.object(snap.urllib.request, "urlopen", side_effect=AssertionError("network")):
                first = snap.fetch_snapshot(target, download=synthetic_download)
                second = snap.snapshot_identity(target)
                third = snap.fetch_snapshot(target, download=synthetic_download)
            self.assertEqual(first, second)
            self.assertEqual(second, third)
            self.assertEqual(first["revision"], snap.MODEL_REVISION)
            self.assertEqual(set(first["artifacts"]), set(snap.ARTIFACTS))
            self.assertEqual(first["artifacts"]["onnx/model.onnx"]["sha256"], PIN)
            self.assertEqual(json.loads((target / snap.MANIFEST_NAME).read_text())["model_id"], snap.MODEL_ID)

    def test_model_pin_must_match_before_identity_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "snapshot"
            with self.assertRaisesRegex(snap.SnapshotUnavailable, "frozen pin"):
                snap.fetch_snapshot(target, download=synthetic_download)
            self.assertFalse(target.exists(), "an invalid staging download must not become a snapshot")

    def test_tampered_tokenizer_fails_without_redownload(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(snap, "ONNX_SHA256", PIN):
            target = Path(tmp) / "snapshot"
            snap.fetch_snapshot(target, download=synthetic_download)
            (target / "tokenizer.json").write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(snap.SnapshotUnavailable, "snapshot file drift"):
                snap.verify_snapshot(target)
            with self.assertRaisesRegex(snap.SnapshotUnavailable, "snapshot file drift"):
                snap.fetch_snapshot(target, download=lambda *_: self.fail("re-download is forbidden"))

    def test_missing_manifest_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(snap, "ONNX_SHA256", PIN):
            target = Path(tmp) / "snapshot"
            target.mkdir()
            with self.assertRaisesRegex(snap.SnapshotUnavailable, "manifest missing"):
                snap.fetch_snapshot(target, download=synthetic_download)

    def test_symlink_target_or_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(snap, "ONNX_SHA256", PIN):
            base = Path(tmp)
            target = base / "snapshot"
            snap.fetch_snapshot(target, download=synthetic_download)
            path = target / "tokenizer.json"
            path.unlink()
            path.symlink_to(base / "outside.json")
            with self.assertRaisesRegex(snap.SnapshotUnavailable, "symbolic"):
                snap.verify_snapshot(target)
            link = base / "link"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(snap.SnapshotUnavailable, "symbolic"):
                snap.fetch_snapshot(link, download=synthetic_download)

    def test_artifact_set_and_manifest_are_fixed(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(snap, "ONNX_SHA256", PIN):
            target = Path(tmp) / "snapshot"
            snap.fetch_snapshot(target, download=synthetic_download)
            manifest = json.loads((target / snap.MANIFEST_NAME).read_text())
            manifest["artifacts"]["benchmark_hint.txt"] = {"sha256": "0" * 64, "bytes": 1}
            (target / snap.MANIFEST_NAME).write_text(json.dumps(manifest))
            with self.assertRaisesRegex(snap.SnapshotUnavailable, "artifact set changed"):
                snap.verify_snapshot(target)


if __name__ == "__main__":
    unittest.main()
