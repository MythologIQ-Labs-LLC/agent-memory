"""Cognee source-only CHUNKS attribution tests, no SDK or model required."""
import unittest

from comparators.cognee_source_probe import attribute_cognee_chunks


MAP = {"data:aa": "doc-a", "data:bb": "doc-b"}
ALLOWED = frozenset({"doc-a", "doc-b"})


def check(rows, **kwargs):
    return attribute_cognee_chunks(
        rows, cognee_data_id_to_doc=MAP,
        allowed_doc_ids=ALLOWED, top_k=kwargs.get("top_k", 5),
    )


class CogneeNativeChunkAttributionTests(unittest.TestCase):
    def test_native_document_ids(self):
        rows = [{"document_id": "data:bb", "text": "x"}, {"document_id": "data:aa", "text": "y"}]
        self.assertEqual(check(rows).ranked_for_scoring(), ("doc-b", "doc-a"))

    def test_multi_chunk_same_original_source_counts_once(self):
        rows = [{"document_id": "data:aa", "text": "part 1"}, {"document_id": "data:aa", "text": "part 2"}]
        result = check(rows)
        self.assertEqual(result.ranked_for_scoring(), ("doc-a",))
        self.assertEqual(result.duplicate_hits, 1)

    def test_missing_original_document_id_is_not_guessed_from_name(self):
        result = check([{"document_name": "doc-a", "text": "doc-a"}])
        self.assertEqual(result.status, "unsupported_source_identity")
        with self.assertRaises(ValueError):
            result.ranked_for_scoring()

    def test_dataset_only_is_not_item_provenance(self):
        result = check([{"dataset_id": "data:aa", "document_name": "doc-a"}])
        self.assertEqual(result.status, "unsupported_source_identity")

    def test_graph_completion_text_is_not_a_chunk_result(self):
        with self.assertRaises(TypeError):
            check("doc-a is the answer")

    def test_unknown_native_data_id_refused(self):
        result = check([{"document_id": "data:other"}])
        self.assertEqual(result.status, "unsupported_source_identity")

    def test_partial_mapping_aborts_import(self):
        result = check([{"document_id": "data:aa"}, {"document_id": "data:other"}])
        self.assertEqual(result.ranked, ("doc-a",))
        self.assertEqual(result.status, "partial_source_attribution")
        with self.assertRaises(ValueError):
            result.ranked_for_scoring()

    def test_bad_chunk_payload_shape_is_not_accepted(self):
        result = check([1, {}, {"document_id": None}])
        self.assertEqual(result.status, "unsupported_source_identity")
        self.assertEqual(result.unmapped_hits, 3)

    def test_wrong_scope_cognee_ingest_map_fails(self):
        with self.assertRaises(ValueError):
            attribute_cognee_chunks(
                [{"document_id": "data:aa"}],
                cognee_data_id_to_doc={"data:aa": "foreign-doc"},
                allowed_doc_ids=ALLOWED, top_k=5,
            )

    def test_empty_retrieval_is_distinct_from_unattributed_result(self):
        result = check([])
        self.assertEqual(result.status, "attributed")
        self.assertEqual(result.ranked_for_scoring(), ())

    def test_top_k_preserves_native_rank_order(self):
        rows = [{"document_id": "data:bb"}, {"document_id": "data:aa"}]
        self.assertEqual(check(rows, top_k=1).ranked_for_scoring(), ("doc-b",))


if __name__ == "__main__":
    unittest.main()
