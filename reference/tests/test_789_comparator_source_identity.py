"""Independent no-provider contract tests for #789 source identity admission.

Run: python -m unittest discover -s reference/tests -t reference -p test_789_comparator_source_identity.py
No inference, credentials, CI, downloaded models, or vendor SDKs required.
"""
import unittest

from comparators.source_identity_gate import attribute_hits

MAP = {
    "provider:11": "case-a",
    "provider:12": "case-b",
    "provider:13": "case-c",
    "provider:11-alt": "case-a",
}
ALLOW = frozenset({"case-a", "case-b", "case-c"})


def map_it(hits, *, top_k=5):
    return attribute_hits(hits, source_handles=MAP, allowed_document_ids=ALLOW, top_k=top_k)


class SourceIdentityGateTests(unittest.TestCase):
    def test_one_hit_one_document(self):
        value = map_it([{"source_handles": ["provider:11"]}, {"source_handles": ["provider:12"]}])
        self.assertEqual(value.status, "attributed")
        self.assertEqual(value.ranked, ("case-a", "case-b"))

    def test_no_gold_or_text_guesses(self):
        value = map_it([{"text": "case-a", "score": 0.999}])
        self.assertEqual(value.status, "unsupported_source_identity")
        self.assertEqual(value.ranked, ())

    def test_unknown_source_handle_does_not_credit(self):
        value = map_it([{"source_handles": ["unknown"]}])
        self.assertEqual(value.status, "unsupported_source_identity")
        self.assertEqual(value.unmapped_hits, 1)

    def test_partial_unknown_provenance_never_grants_credit(self):
        value = map_it([{"source_handles": ["provider:11", "unknown"]}])
        self.assertEqual(value.ranked, ())

    def test_ambiguous_edge_does_not_credit_either_doc(self):
        value = map_it([{"source_handles": ["provider:11", "provider:12"]}])
        self.assertEqual(value.status, "unsupported_source_identity")
        self.assertEqual(value.ambiguous_hits, 1)

    def test_same_source_multiple_handles_is_valid(self):
        self.assertEqual(
            map_it([{"source_handles": ["provider:11", "provider:11-alt"]}]).ranked,
            ("case-a",),
        )

    def test_duplicate_source_is_credited_once(self):
        value = map_it([{"source_handles": ["provider:11"]}, {"source_handles": ["provider:11-alt"]}])
        self.assertEqual(value.ranked, ("case-a",))
        self.assertEqual(value.duplicate_hits, 1)

    def test_partial_traceability_is_unqualified(self):
        value = map_it([{"source_handles": ["provider:11"]}, {"source_handles": ["unknown"]}])
        self.assertEqual(value.status, "partial_source_attribution")
        self.assertEqual(value.ranked, ("case-a",))

    def test_untrusted_cross_scope_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            attribute_hits(
                [{"source_handles": ["provider:11"]}],
                source_handles={"provider:11": "foreign-scope"},
                allowed_document_ids=ALLOW,
                top_k=5,
            )

    def test_empty_provider_response_is_valid_zero_retrieval(self):
        value = map_it([])
        self.assertEqual(value.status, "attributed")
        self.assertEqual(value.ranked, ())

    def test_invalid_top_k_is_refused(self):
        for value in (0, True, -1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                map_it([], top_k=value)

    def test_provider_order_and_depth_preserved(self):
        value = map_it(
            [
                {"source_handles": ["provider:12"]},
                {"source_handles": ["provider:11"]},
                {"source_handles": ["provider:13"]},
            ],
            top_k=2,
        )
        self.assertEqual(value.ranked, ("case-b", "case-a"))
        self.assertEqual(value.raw_hits, 3)

    def test_invalid_shapes_are_excluded(self):
        value = map_it([{}, {"source_handles": "provider:11"}, 7])
        self.assertEqual(value.status, "unsupported_source_identity")
        self.assertEqual(value.unmapped_hits, 2)
        self.assertEqual(value.invalid_hits, 1)

    def test_numeric_import_refuses_partially_attributed_rows(self):
        with self.assertRaisesRegex(ValueError, "not fully attributable"):
            map_it([{"source_handles": ["provider:11"]}, {"source_handles": ["unknown"]}]).ranked_for_scoring()
        self.assertEqual(
            map_it([{"source_handles": ["provider:11"]}]).ranked_for_scoring(),
            ("case-a",),
        )

    def test_empty_ingestion_map_is_refused_not_scored_zero(self):
        # No document was ingested: an empty provider response must not become a
        # scorable zero row (README negative control 5: ingestion failure and empty
        # retrieval are distinguished; issue #789: no zeros for unsupported operations).
        with self.assertRaisesRegex(ValueError, "cover every allowed document"):
            attribute_hits([], source_handles={}, allowed_document_ids=ALLOW, top_k=5)

    def test_partial_ingestion_map_is_refused_before_attribution(self):
        partial = {"provider:11": "case-a", "provider:12": "case-b"}  # case-c never ingested
        with self.assertRaisesRegex(ValueError, "cover every allowed document"):
            attribute_hits(
                [{"source_handles": ["provider:11"]}],
                source_handles=partial, allowed_document_ids=ALLOW, top_k=5,
            )

    def test_full_ingestion_map_with_aliases_is_accepted(self):
        value = map_it([])
        self.assertEqual(value.status, "attributed")

    def test_handle_that_names_a_different_allowed_document_is_refused(self):
        # A swapped ingestion map: the native handle IS an allowed document id but is
        # mapped to another document. Crediting it would score the wrong document.
        swapped = {"case-b": "case-a", "case-a": "case-b", "provider:13": "case-c"}
        with self.assertRaisesRegex(ValueError, "must map to itself"):
            attribute_hits(
                [{"source_handles": ["case-b"]}],
                source_handles=swapped, allowed_document_ids=ALLOW, top_k=5,
            )

    def test_identity_handles_remain_valid(self):
        identity = {"case-a": "case-a", "case-b": "case-b", "case-c": "case-c"}
        value = attribute_hits(
            [{"source_handles": ["case-b"]}],
            source_handles=identity, allowed_document_ids=ALLOW, top_k=5,
        )
        self.assertEqual(value.ranked_for_scoring(), ("case-b",))


if __name__ == "__main__":
    unittest.main()
