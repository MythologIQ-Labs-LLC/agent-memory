"""Offline fake-product conformance for Hindsight comparator bridge (#640 H2)."""

from __future__ import annotations

import unittest
from typing import Any

from agentmem_ref.evaluation.hindsight_bridge import (
    CorpusDocument,
    HindsightBridgeError,
    HindsightRetrievalBridge,
    IdentityMappingError,
    EXPECTED_BANK_CONFIG,
)


class FakeHindsightClient:
    def __init__(self) -> None:
        self.retains: list[dict[str, Any]] = []
        self.queries: list[dict[str, Any]] = []
        self.results: list[dict[str, Any]] = []
        self.retain_success = True
        self.bank_config = dict(EXPECTED_BANK_CONFIG)
        self.config_queries: list[str] = []

    def get_bank_config(self, bank_id: str) -> dict[str, Any]:
        self.config_queries.append(bank_id)
        return {
            "bank_id": bank_id,
            "config": dict(self.bank_config),
            "overrides": dict(self.bank_config),
        }

    def retain(self, **kwargs: Any) -> dict[str, Any]:
        self.retains.append(kwargs)
        return {
            "success": self.retain_success,
            "bank_id": kwargs["bank_id"],
            "items_count": 1,
            "var_async": False,
        }

    def recall(self, **kwargs: Any) -> dict[str, Any]:
        self.queries.append(kwargs)
        return {"results": self.results}


class HindsightBridgeTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeHindsightClient()
        self.bridge = HindsightRetrievalBridge(client=self.client, bank_id="comparability-test")
        self.bridge.qualify_bank()

    def test_unqualified_bank_refuses_calls_without_product_mutation(self):
        bridge = HindsightRetrievalBridge(client=self.client, bank_id="unqualified")
        with self.assertRaisesRegex(HindsightBridgeError, "not qualified"):
            bridge.retain(CorpusDocument("doc", "text"))
        with self.assertRaisesRegex(HindsightBridgeError, "not qualified"):
            bridge.recall("q", top_k=1, max_tokens=1024)
        self.assertEqual(self.client.retains, [])
        self.assertEqual(self.client.queries, [])

    def test_configuration_mismatches_refused_before_ingest(self):
        for key, expected in EXPECTED_BANK_CONFIG.items():
            with self.subTest(setting=key):
                client = FakeHindsightClient()
                client.bank_config[key] = (not expected if isinstance(expected, bool) else "verbose")
                bridge = HindsightRetrievalBridge(client=client, bank_id="test")
                with self.assertRaisesRegex(HindsightBridgeError, key):
                    bridge.qualify_bank()
                self.assertEqual(bridge.ingest_count, 0)
                self.assertFalse(bridge.identity()["product_configuration_verified"])

    def test_config_identity_stable_and_requalification_blocked_after_ingest(self):
        digest = self.bridge.identity()["verified_bank_config_sha256"]
        self.assertEqual(len(digest), 64)
        other = HindsightRetrievalBridge(client=FakeHindsightClient(), bank_id="comparability-test")
        self.assertEqual(other.qualify_bank(), digest)
        self.bridge.retain(CorpusDocument("doc", "text"))
        with self.assertRaisesRegex(HindsightBridgeError, "after ingest"):
            self.bridge.qualify_bank()

    def test_synchronous_retain_keeps_document_text_unmodified(self):
        native = self.bridge.retain(CorpusDocument("source:0005", "Exactly the source text."))
        self.assertEqual(len(native), len("agent-memory-comparator-") + 64)
        self.assertNotIn("source:0005", native)
        self.assertEqual(self.bridge.ingest_count, 1)
        self.assertEqual(self.client.retains, [{
            "bank_id": "comparability-test",
            "content": "Exactly the source text.",
            "document_id": native,
            "retain_async": False,
        }])
        self.assertEqual(self.bridge.identity()["product_configuration_verified"], True)

    def test_recall_preserves_native_order_and_exact_identity(self):
        first = self.bridge.retain(CorpusDocument("doc-A", "alpha"))
        second = self.bridge.retain(CorpusDocument("doc-B", "beta"))
        self.client.results = [
            {"id": "native-b", "text": "beta chunk", "document_id": second},
            {"id": "native-a", "text": "alpha chunk", "document_id": first},
        ]
        got = self.bridge.recall("query", top_k=2, max_tokens=1024, budget="mid")
        self.assertEqual(got.mapped_corpus_ids, ("doc-B", "doc-A"))
        self.assertEqual(got.raw_native_results[0]["id"], "native-b")
        self.assertEqual(got.raw_native_results[0]["text"], "beta chunk")
        self.assertEqual(self.client.queries, [{
            "bank_id": "comparability-test",
            "query": "query",
            "max_tokens": 1024,
            "budget": "mid",
        }])
        self.assertEqual(got.authority_effect, "none")

    def test_multi_chunk_results_collapse_by_native_document_id_only(self):
        first = self.bridge.retain(CorpusDocument("one", "x"))
        second = self.bridge.retain(CorpusDocument("two", "y"))
        self.client.results = [
            {"id": "chunk-1", "text": "x1", "document_id": first},
            {"id": "chunk-2", "text": "x2", "document_id": first},
            {"id": "chunk-3", "text": "y", "document_id": second},
        ]
        got = self.bridge.recall("q", top_k=1, max_tokens=2048)
        self.assertEqual(got.mapped_corpus_ids, ("one",))
        self.assertEqual(got.repeated_native_document_ids, (first,))
        self.assertEqual(len(got.raw_native_results), 3)

    def test_unknown_native_document_is_error_not_miss(self):
        self.bridge.retain(CorpusDocument("one", "x"))
        self.client.results = [
            {"id": "fact-1", "text": "x", "document_id": "unknown-provider-doc"},
        ]
        with self.assertRaises(IdentityMappingError) as cm:
            self.bridge.recall("q", top_k=2, max_tokens=1000)
        self.assertEqual(cm.exception.raw_results[0]["id"], "fact-1")
        self.assertIn("outside", str(cm.exception))

    def test_missing_document_id_is_error_even_if_text_matches(self):
        self.bridge.retain(CorpusDocument("one", "same text"))
        self.client.results = [{"id": "fact-1", "text": "same text"}]
        with self.assertRaises(IdentityMappingError):
            self.bridge.recall("same text", top_k=1, max_tokens=1000)

    def test_failed_retain_does_not_create_identity(self):
        self.client.retain_success = False
        with self.assertRaisesRegex(HindsightBridgeError, "retain did not confirm"):
            self.bridge.retain(CorpusDocument("one", "x"))
        self.assertEqual(self.bridge.ingest_count, 0)

    def test_duplicate_input_cannot_silently_replace_product_document(self):
        self.bridge.retain(CorpusDocument("one", "x"))
        with self.assertRaisesRegex(HindsightBridgeError, "duplicate corpus_id"):
            self.bridge.retain(CorpusDocument("one", "changed x"))
        self.assertEqual(len(self.client.retains), 1)

    def test_empty_and_bad_budget_are_refused_without_product_calls(self):
        for query, k, tokens, budget in [
            ("", 2, 1000, "mid"),
            ("q", 0, 1000, "mid"),
            ("q", 1, 0, "mid"),
            ("q", 1, 1000, "freeform"),
        ]:
            with self.subTest(query=query, k=k, tokens=tokens, budget=budget):
                with self.assertRaises(ValueError):
                    self.bridge.recall(query, top_k=k, max_tokens=tokens, budget=budget)
        self.assertEqual(len(self.client.queries), 0)

    def test_malformed_response_is_adapter_failure(self):
        self.client.results = []  # no inserted corpus, empty results are okay
        self.assertEqual(
            self.bridge.recall("q", top_k=2, max_tokens=512).mapped_corpus_ids, ()
        )
        self.client.results = None
        with self.assertRaisesRegex(HindsightBridgeError, "no native result list"):
            self.bridge.recall("q", top_k=2, max_tokens=512)


if __name__ == "__main__":
    unittest.main()
