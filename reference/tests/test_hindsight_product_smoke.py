"""Network-free H3 smoke contract tests; Hindsight product is never installed/called."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from agentmem_ref.evaluation.hindsight_bridge import EXPECTED_BANK_CONFIG
from agentmem_ref.evaluation.hindsight_product_smoke import (
    QUERY,
    SmokeQualificationError,
    _semantic_probe,
    run_smoke,
)


ATTESTATION = {
    "product_release": "0.10.2",
    "product_source_revision": "5fc4ce20917b916240cef27c212c387a177f115b",
    "llm_provider": "none",
    "embedding_provider": "onnx",
    "model_revision": "03415a4be176a1620747c692ed433219fabc3def",
    "paid_llm_credentials_present": False,
}


class FakeProduct:
    def __init__(self):
        self.bank_id = None
        self.bank_config = dict(EXPECTED_BANK_CONFIG)
        self.docs = []
        self.created_with = None
        self.return_empty = False
        self.change_config_after = False

    def create_bank(self, *, bank_id, **kwargs):
        self.bank_id = bank_id
        self.created_with = dict(kwargs)
        return {"bank_id": bank_id}

    def get_bank_config(self, bank_id):
        assert bank_id == self.bank_id
        config = dict(self.bank_config)
        if self.change_config_after and len(self.docs) >= 2:
            config["enable_reranking"] = True
        return {"bank_id": bank_id, "config": config, "overrides": config}

    def retain(self, *, bank_id, content, document_id, retain_async):
        assert bank_id == self.bank_id
        assert retain_async is False
        self.docs.append((document_id, content))
        return {"success": True, "bank_id": bank_id, "items_count": 1, "var_async": False}

    def recall(self, *, bank_id, query, max_tokens, budget):
        assert bank_id == self.bank_id
        assert query == QUERY
        assert max_tokens == 4096
        assert budget == "mid"
        results = [] if self.return_empty else [
            {"id": "chunk-b", "text": self.docs[1][1], "document_id": self.docs[1][0]},
            {"id": "chunk-a", "text": self.docs[0][1], "document_id": self.docs[0][0]},
        ]
        return {"results": results}


class HindsightH3Tests(unittest.TestCase):
    def test_records_synthetic_probe_without_any_scoring(self):
        fake = FakeProduct()
        with patch(
            "agentmem_ref.evaluation.hindsight_product_smoke.snapshot_identity",
            return_value={"revision": ATTESTATION["model_revision"], "manifest_sha256": "d" * 64},
        ):
            record = run_smoke(
                client=fake,
                bank_id="synthetic-test",
                model_dir=Path("/not-a-model"),
                deployment_attestation=ATTESTATION,
            )
        self.assertEqual(fake.created_with, EXPECTED_BANK_CONFIG)
        self.assertIsNone(record["benchmark_score"])
        self.assertIsNone(record["benchmark_lane"])
        self.assertEqual(record["probe"]["ingest_count"], 2)
        self.assertEqual(record["probe"]["returned_corpus_ids"], ["smoke-doc-b", "smoke-doc-a"])
        self.assertEqual(record["probe"]["unmapped_result_count"], 0)
        self.assertEqual(record["status"], "connectivity_pass_attestation_pending")
        self.assertIn("operator-provided", record["product"]["attestation_verification"])
        self.assertEqual(record["probe"]["pre_post_config_sha256_equal"], True)

    def test_missing_llm_provider_attestation_fails_before_product_call(self):
        fake = FakeProduct()
        forged = dict(ATTESTATION, llm_provider="anthropic")
        with self.assertRaisesRegex(SmokeQualificationError, "llm_provider"):
            run_smoke(
                client=fake,
                bank_id="synthetic-test",
                model_dir=Path("/not-a-model"),
                deployment_attestation=forged,
            )
        self.assertIsNone(fake.created_with)

    def test_paid_credentials_attestation_fails_closed(self):
        fake = FakeProduct()
        forged = dict(ATTESTATION, paid_llm_credentials_present=True)
        with self.assertRaisesRegex(SmokeQualificationError, "paid_llm_credentials_present"):
            run_smoke(
                client=fake,
                bank_id="synthetic-test",
                model_dir=Path("/not-a-model"),
                deployment_attestation=forged,
            )
        self.assertIsNone(fake.created_with)

    def test_bank_drift_fails_smoke(self):
        fake = FakeProduct()
        fake.change_config_after = True
        with self.assertRaisesRegex(SmokeQualificationError, "drifted"):
            _semantic_probe(fake, "synthetic-test")

    def test_no_results_is_smoke_failure_not_zero_score(self):
        fake = FakeProduct()
        fake.return_empty = True
        with self.assertRaisesRegex(SmokeQualificationError, "no document identities"):
            _semantic_probe(fake, "synthetic-test")

    def test_wrong_effective_bank_config_refused(self):
        fake = FakeProduct()
        fake.bank_config["enable_graph_retrieval"] = True
        with self.assertRaisesRegex(Exception, "enable_graph_retrieval"):
            _semantic_probe(fake, "synthetic-test")
        self.assertEqual(fake.docs, [])


if __name__ == "__main__":
    unittest.main()
