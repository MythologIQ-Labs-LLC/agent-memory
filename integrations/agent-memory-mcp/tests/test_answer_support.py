"""The optional answer-support model must be pinned, verified and refused when it is not.

The last test runs the real pinned model only when the host names it in
AGENT_MEMORY_MCP_SUPPORT_MODEL_DIR; it is skipped otherwise, so passing here without the model
says nothing about Stage C behavior.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import answer_support


class AnswerSupportLoadingTests(unittest.TestCase):
    def test_relative_directory_is_refused(self):
        with self.assertRaises(answer_support.SupportCheckUnavailable):
            answer_support.AnswerSupport(Path("relative/model"))

    def test_missing_symlinked_or_altered_files_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(answer_support.SupportCheckUnavailable):
                answer_support._verified_bytes(root, "config.json")
            (root / "elsewhere.json").write_text("{}")
            (root / "config.json").symlink_to(root / "elsewhere.json")
            with self.assertRaises(answer_support.SupportCheckUnavailable):
                answer_support._verified_bytes(root, "config.json")
            (root / "config.json").unlink()
            (root / "config.json").write_bytes(b"x" * answer_support.PINNED_FILES["config.json"][1])
            with self.assertRaisesRegex(answer_support.SupportCheckUnavailable, "digest mismatch"):
                answer_support._verified_bytes(root, "config.json")

    def test_not_enabled_without_the_host_variable(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(answer_support.ENV_DIR, None)
            self.assertIsNone(answer_support.from_environment())


@unittest.skipUnless(os.environ.get(answer_support.ENV_DIR), "pinned support model not provided by the host")
class RealPinnedModelTests(unittest.TestCase):
    def test_span_found_only_where_the_text_answers(self):
        checker = answer_support.from_environment()
        context = "The archive room key hangs on the hook beside the copier."
        self.assertTrue(checker.span_found("Where does the archive room key hang?", context))
        self.assertFalse(checker.span_found("Who repaired the copier last spring?", context))
        outcome = checker.check("Where does the archive room key hang?",
                                ["The copier was serviced in March.", context])
        self.assertEqual(outcome, {"per_item": [False, True], "joint": True})


if __name__ == "__main__":
    unittest.main()
