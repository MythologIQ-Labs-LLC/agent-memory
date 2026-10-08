"""Offline tests for H3's self-hosted, credential-free product bootstrap."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentmem_ref.evaluation.hindsight_selfhosted_smoke import (
    SelfHostedSmokeError,
    isolated_environment,
    run_selfhosted_smoke,
)
from agentmem_ref.evaluation.hindsight_bridge import EXPECTED_BANK_CONFIG


class FakeServer:
    def __init__(self, **kwargs):
        self.arguments = kwargs
        self.llm_provider = kwargs["llm_provider"]
        self.llm_api_key = kwargs["llm_api_key"]
        self.url = "http://127.0.0.1:18888"
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


class FakeClient:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.bank = None
        self.docs = []
        self.closed = False

    def create_bank(self, *, bank_id, **kwargs):
        self.bank = {"id": bank_id, "config": dict(kwargs)}
        return {"bank_id": bank_id}

    def get_bank_config(self, bank_id):
        return {"bank_id": bank_id, "config": self.bank["config"]}

    def retain(self, **kwargs):
        self.docs.append(kwargs)
        return {
            "success": True, "bank_id": kwargs["bank_id"],
            "items_count": 1, "var_async": False,
        }

    def recall(self, **kwargs):
        return {"results": [
            {"id": "chunk-1", "text": self.docs[1]["content"],
             "document_id": self.docs[1]["document_id"]},
        ]}

    def close(self):
        self.closed = True


class H3SelfhostedTests(unittest.TestCase):
    def test_routing_environment_contains_no_paid_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {}, clear=True):
                env = isolated_environment(Path(tmp))
        self.assertEqual(env["HINDSIGHT_API_LLM_PROVIDER"], "none")
        self.assertEqual(env["HINDSIGHT_API_LLM_API_KEY"], "")
        self.assertEqual(env["HINDSIGHT_API_EMBEDDINGS_PROVIDER"], "onnx")

    def test_ambient_paid_credential_fails_before_any_model_use(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic"}, clear=True):
            with self.assertRaisesRegex(SelfHostedSmokeError, "ambient paid"):
                isolated_environment(Path("/synthetic"))

    def test_selfhosted_probe_starts_local_server_and_stops(self):
        holder = {}

        def server_factory(**kwargs):
            obj = FakeServer(**kwargs)
            holder["server"] = obj
            return obj

        def client_factory(**kwargs):
            obj = FakeClient(**kwargs)
            holder["client"] = obj
            return obj

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "agentmem_ref.evaluation.hindsight_selfhosted_smoke.verify_pinned_checkout",
                return_value=root,
            ), patch(
                "agentmem_ref.evaluation.hindsight_selfhosted_smoke.snapshot_identity",
                return_value={
                    "revision": "03415a4be176a1620747c692ed433219fabc3def",
                    "manifest_sha256": "d" * 64,
                },
            ), patch(
                "agentmem_ref.evaluation.hindsight_product_smoke.snapshot_identity",
                return_value={
                    "revision": "03415a4be176a1620747c692ed433219fabc3def",
                    "manifest_sha256": "d" * 64,
                },
            ), patch.dict(os.environ, {}, clear=True):
                record = run_selfhosted_smoke(
                    model_dir=root, source_dir=root,
                    server_factory=server_factory, client_factory=client_factory,
                )
                self.assertNotIn("HINDSIGHT_API_LLM_PROVIDER", os.environ)

        self.assertTrue(holder["server"].started)
        self.assertTrue(holder["server"].stopped)
        self.assertTrue(holder["client"].closed)
        self.assertEqual(holder["server"].arguments["llm_provider"], "none")
        self.assertEqual(holder["server"].arguments["llm_api_key"], "")
        self.assertEqual(holder["client"].options["max_attempts"], 1)
        self.assertEqual(record["status"], "selfhosted_product_smoke_pass")
        self.assertIsNone(record["benchmark_score"])
        self.assertEqual(record["product"]["network_model_calls"], 0)
        self.assertEqual(record["probe"]["ingest_count"], 2)

    def test_server_stops_if_client_factory_fails(self):
        holder = {}

        def server_factory(**kwargs):
            obj = FakeServer(**kwargs)
            holder["server"] = obj
            return obj

        def fail_client(**kwargs):
            raise RuntimeError("synthetic client failure")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "agentmem_ref.evaluation.hindsight_selfhosted_smoke.verify_pinned_checkout",
                return_value=root,
            ), patch(
                "agentmem_ref.evaluation.hindsight_selfhosted_smoke.snapshot_identity",
                return_value={"revision": "03415a4be176a1620747c692ed433219fabc3def"},
            ), patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "synthetic client failure"):
                    run_selfhosted_smoke(
                        model_dir=root, source_dir=root,
                        server_factory=server_factory, client_factory=fail_client,
                    )
                self.assertNotIn("HINDSIGHT_API_LLM_PROVIDER", os.environ)
        self.assertTrue(holder["server"].stopped)


if __name__ == "__main__":
    unittest.main()
