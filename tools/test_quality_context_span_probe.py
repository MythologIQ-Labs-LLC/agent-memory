"""Stdlib-only controls for the evaluation-only #819 statement span probe."""
from __future__ import annotations

import unittest

from tools.quality_context_span_probe import _ranges, inspect_package


def document(*items):
    return {"recall": {"returned": [item["fact_ref"] for item in items]},
            "items": list(items)}


class LosslessSpanDiagnostics(unittest.TestCase):
    def test_boundaries_reconstruct_exact_unicode_and_whitespace(self):
        for text in ("Alpha.  Beta!\nGamma?  Last", "Single statement",
                     "Hey 👋. ✅ Done.", "3.14 units and a line. Next"):
            spans = _ranges(text)
            self.assertEqual("".join(text[a:b] for a, b in spans), text)
            self.assertEqual(spans[0][0], 0)
            self.assertEqual(spans[-1][1], len(text))

    def test_large_punctuation_input_remains_bounded_and_lossless(self):
        text = ("Now. " * 800) + "Later."
        spans = _ranges(text)
        self.assertLessEqual(len(spans), 512)
        self.assertEqual("".join(text[a:b] for a, b in spans), text)

    def test_multi_statement_locates_overlap_without_exclusion(self):
        text = "The festival is on Friday. The canoe was painted teal. The telescope was repaired."
        result = inspect_package(document({
            "fact_ref": "ref-1", "state": "resolved", "content": text,
        }), "canoe painted")
        item = result["items"][0]
        self.assertEqual(item["span_count"], 3)
        self.assertEqual(item["fronting_suggestion"], [1])
        self.assertEqual(item["literal_overlap_chars"] + item["uncertain_chars"], len(text))
        self.assertFalse(result["plaintext_included"])
        self.assertNotIn("painted teal", repr(result))
        self.assertEqual(result["status"], "observational_only_not_relevance_or_answerability")

    def test_paraphrase_is_uncertain_never_a_negative(self):
        text = "Her eldest performs on the cello."
        result = inspect_package(document({
            "fact_ref": "ref-2", "state": "resolved", "content": text,
        }), "Which instrument does the child play?")
        item = result["items"][0]
        self.assertEqual(item["fronting_suggestion"], [])
        self.assertEqual(item["assessment"], "insufficient_lexical_signal")
        self.assertEqual(item["uncertain_chars"], len(text))

    def test_omitted_and_unresolved_content_is_never_resurrected(self):
        result = inspect_package(document(
            {"fact_ref": "ref-secret", "state": "unresolved"},
            {"fact_ref": "ref-other", "state": "omitted_selection"},
        ), "secret")
        self.assertEqual(result["delivered_count"], 0)
        self.assertEqual(result["incomplete_or_omitted_count"], 2)
        self.assertTrue(all("spans" not in item for item in result["items"]))

    def test_foreign_or_duplicate_returned_ref_is_rejected(self):
        incorrect = document({"fact_ref": "a", "state": "resolved", "content": "okay"})
        incorrect["recall"]["returned"] = ["other"]
        with self.assertRaises(ValueError):
            inspect_package(incorrect, "okay")
        repeated = {"recall": {"returned": ["a", "a"]},
                    "items": [{"fact_ref": "a", "state": "resolved", "content": "okay"}]}
        with self.assertRaises(ValueError):
            inspect_package(repeated, "okay")

    def test_truncated_source_is_marked_incomplete(self):
        result = inspect_package(document({
            "fact_ref": "ref-3", "state": "truncated", "content": "Canoe",
        }), "canoe")
        self.assertTrue(result["items"][0]["source_is_partial"])

    def test_plaintext_requires_explicit_opt_in(self):
        packet = document({
            "fact_ref": "ref-5", "state": "resolved", "content": "Private note. Other words.",
        })
        safe = inspect_package(packet, "private")
        rich = inspect_package(packet, "private", include_previews=True)
        self.assertNotIn("Private note", repr(safe))
        self.assertEqual(
            "".join(span["text"] for span in rich["items"][0]["spans"]),
            "Private note. Other words.",
        )


if __name__ == "__main__":
    unittest.main()
