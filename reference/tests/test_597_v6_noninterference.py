"""#597: check a new write-boundary version against the exact published v6 parser.

The v6 source is loaded without changing the current working tree or rewriting
the frozen #594 gold. Comparisons are from fresh, pre-specified generic inputs.
"""
from __future__ import annotations

import copy
import subprocess
import unittest

from agentmem_ref.runtime import proposition_semantics as candidate

V6_SHA = "3eebb6d54e2a218c4fd10cf53c52acac8384c3e6"
SOURCE_PATH = "reference/agentmem_ref/runtime/proposition_semantics.py"
UNCHANGED_CASES = (
    "I prefer green tea.",
    "Our project status is active.",
    "We also enjoy hiking.",
    "The monitor is blue.",
    "My inventory has 24 units.",
    "I currently work in research.",
    "I prefer green tea and I like strong coffee.",
    'I enjoy the song "Hello, can you hear me?"',
    "Could you recommend an infusion?",
    "I might prefer an herbal infusion.",
)


def _load_v6_interpreter():
    source = subprocess.check_output(
        ["git", "show", f"{V6_SHA}:{SOURCE_PATH}"], text=True
    )
    namespace = {
        "__package__": "agentmem_ref.runtime",
        "__name__": "agentmem_ref.runtime._frozen_v6_semantics_for_597",
        "__file__": SOURCE_PATH,
    }
    exec(compile(source, f"{V6_SHA}:{SOURCE_PATH}", "exec"), namespace)
    return namespace


def _without_interpreter_revision(result):
    result = copy.deepcopy(result)
    result["interpreter"].pop("version", None)
    return result


class V6BoundaryNoninterferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = _load_v6_interpreter()
        if cls.legacy["INTERPRETER_VERSION"] != "1.1.0":
            raise AssertionError("source is not the frozen v6 write interpreter")

    def test_unrelated_write_interpretations_match_v6(self):
        for text in UNCHANGED_CASES:
            with self.subTest(text=text):
                old = self.legacy["interpret_write"](text)
                new = candidate.interpret_write(text)
                self.assertEqual(_without_interpreter_revision(new),
                                 _without_interpreter_revision(old))

    def test_new_version_is_visible_but_legacy_persistence_stays_old(self):
        self.assertEqual(candidate.INTERPRETER_VERSION, "1.2.0")
        new = candidate.persisted_form(candidate.interpret_write("I prefer green tea"))
        self.assertTrue(new["version"].startswith("1.2.0/"))
        old = self.legacy["persisted_form"](
            self.legacy["interpret_write"]("I prefer green tea")
        )
        self.assertTrue(old["version"].startswith("1.1.0/"))
        expanded = candidate.expanded_form(old)
        self.assertEqual(expanded["interpreter"]["version"], "1.1.0")
        self.assertEqual(expanded["proposition"],
                         self.legacy["expanded_form"](old)["proposition"])

    def test_compound_request_repairs_general_value_boundary(self):
        text = "I prefer green tea, can you recommend a book?"
        old = self.legacy["interpret_write"](text)["proposition"]
        new = candidate.interpret_write(text)["proposition"]
        simple = candidate.interpret_write("I prefer green tea")["proposition"]
        self.assertNotEqual(old, simple)
        self.assertEqual(new, simple)
        self.assertEqual(candidate.interpret_write(text)["authority_effect"], "none")


if __name__ == "__main__":
    unittest.main()
