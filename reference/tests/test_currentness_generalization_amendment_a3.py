"""#732 G3b amendment A3 (#786 candidate, pending re-gate): semantic template pin.

The historical whole-file pin (blob 745f789c) is preserved and still selectable. A3 accepts a
changed template source file only when the frozen CONFLICT_TEMPLATES and the contamination
comparison are provably unchanged. These tests show what A3 refuses.
"""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_currentness_generalization import checker


class AmendmentA3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = checker.TEMPLATE_SOURCE.read_text(encoding="utf-8")
        self.frozen = subprocess.run(["git", "cat-file", "-p", checker.TEMPLATE_FROZEN_BLOB], cwd=checker.ROOT,
                                     capture_output=True, text=True, check=True).stdout
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def variant(self, text: str) -> Path:
        path = Path(self.temp.name) / "run_semantic_route_ordering_report.py"
        path.write_text(text, encoding="utf-8")
        return path

    def test_historical_pin_is_preserved(self):
        self.assertEqual(checker.TEMPLATE_BLOB_PREFIX, "745f789c")
        self.assertTrue(checker.TEMPLATE_FROZEN_BLOB.startswith(checker.TEMPLATE_BLOB_PREFIX))
        self.assertEqual(checker.THRESHOLD, 0.5)

    def test_frozen_bytes_still_take_the_frozen_blob_path(self):
        texts, basis = checker.template_basis(self.variant(self.frozen))
        self.assertEqual(basis, "frozen_blob")
        self.assertEqual(checker.texts_digest(texts), checker.TEMPLATE_TEXTS_SHA256)

    def test_current_source_is_accepted_only_through_the_amendment(self):
        texts, basis = checker.template_basis()
        self.assertEqual(basis, checker.TEMPLATE_AMENDMENT_ID)
        frozen_texts, _ = checker.template_basis(self.variant(self.frozen))
        self.assertEqual(texts, frozen_texts)
        with self.assertRaisesRegex(SystemExit, "is not the frozen 745f789c"):
            checker.template_basis(require_frozen_blob=True)

    def test_code_change_around_the_templates_is_accepted(self):
        _, basis = checker.template_basis(self.variant(self.source + "\n# unrelated harness change\n"))
        self.assertEqual(basis, checker.TEMPLATE_AMENDMENT_ID)

    def test_altered_template_text_is_refused(self):
        rows = checker._templates_from_source(self.source)
        slot, old, new, query = rows[0]
        altered = self.source.replace(f'"{query}"', f'"{query} now"', 1)
        self.assertNotEqual(altered, self.source, "fixture failed to alter a template")
        with self.assertRaisesRegex(SystemExit, "CONFLICT_TEMPLATES differ"):
            checker.template_basis(self.variant(altered))

    def test_reordered_or_extended_templates_are_refused(self):
        rows = checker._templates_from_source(self.source)
        start = self.source.index("CONFLICT_TEMPLATES")
        end = self.source.index("\n\n", start)
        rows = list(rows)
        for label, replacement in (("reordered", list(reversed(rows))), ("extended", rows + [rows[0]])):
            with self.subTest(label):
                text = self.source[:start] + f"CONFLICT_TEMPLATES = {replacement!r}" + self.source[end:]
                with self.assertRaises(SystemExit):
                    checker.template_basis(self.variant(text))

    def test_changed_comparison_rule_is_refused(self):
        def loose_similarity(a: str, b: str) -> float:
            return 0.0

        def whitespace_tokens(text: str) -> list[str]:
            return text.lower().split()

        changes = {
            "similarity": mock.patch.object(checker, "similarity", loose_similarity),
            "tokens": mock.patch.object(checker, "tokens", whitespace_tokens),
            "lambda rule": mock.patch.object(checker, "similarity", lambda a, b: 1.0),
            "threshold": mock.patch.object(checker, "THRESHOLD", 0.9),
            "token pattern": mock.patch.object(checker, "TOKEN", checker.re.compile(r"[a-z]+")),
        }
        for label, patcher in changes.items():
            with self.subTest(label), patcher, self.assertRaisesRegex(SystemExit, "contamination comparison differs"):
                checker.template_basis()

    def test_unavailable_frozen_blob_is_refused(self):
        with mock.patch.object(checker, "TEMPLATE_FROZEN_BLOB", "0" * 40):
            with self.assertRaisesRegex(SystemExit, "is unavailable"):
                checker.template_basis()

    def test_recorded_text_digest_is_load_bearing(self):
        with mock.patch.object(checker, "TEMPLATE_TEXTS_SHA256", "0" * 64):
            with self.assertRaisesRegex(SystemExit, "recorded digest"):
                checker.template_basis()

    def test_report_names_its_template_basis(self):
        report = checker.check([], None, None, [])
        self.assertEqual(report["template_basis"], checker.TEMPLATE_AMENDMENT_ID)
        self.assertEqual(report["template_blob_prefix"], "745f789c")


if __name__ == "__main__":
    unittest.main()
