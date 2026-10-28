"""#732 G3b amendment A3 (#786 candidate, pending re-gate): semantic template pin.

The historical whole-file pin (blob 745f789c) is preserved and still selectable. A3 accepts a
changed template source file only when the frozen CONFLICT_TEMPLATES and the contamination
comparison are provably unchanged. These tests show what A3 refuses.
"""
from __future__ import annotations

import importlib.util
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

    def test_rebinding_the_templates_after_the_frozen_literal_is_refused(self):
        # Consumers read the module's runtime value, not its first literal (re-gate finding).
        rebinds = {
            "reassigned": "\nCONFLICT_TEMPLATES = CONFLICT_TEMPLATES[:4]\n",
            "augmented": '\nCONFLICT_TEMPLATES += (("x", "a {old}", "b {new}", "q"),)\n',
            "annotated": "\nCONFLICT_TEMPLATES: tuple = ()\n",
            "conditional": "\nif True:\n    CONFLICT_TEMPLATES = ()\n",
            "deleted": "\ndel CONFLICT_TEMPLATES\n",
            "loop target": "\nfor CONFLICT_TEMPLATES in [()]:\n    pass\n",
            "walrus": "\n(CONFLICT_TEMPLATES := ())\n",
            "global in function": "\ndef reset():\n    global CONFLICT_TEMPLATES\n    CONFLICT_TEMPLATES = ()\n",
            "globals() string": "\nglobals()['CONFLICT_TEMPLATES'] = ()\n",
            "module attribute": "\nimport sys\nsys.modules[__name__].CONFLICT_TEMPLATES = ()\n",
            "import alias": "\nfrom os import sep as CONFLICT_TEMPLATES\n",
            "star import": "\nfrom os.path import *\n",
            "function": "\ndef CONFLICT_TEMPLATES():\n    return ()\n",
            "except name": "\ntry:\n    pass\nexcept Exception as CONFLICT_TEMPLATES:\n    pass\n",
            "match capture": "\nmatch 1:\n    case CONFLICT_TEMPLATES:\n        pass\n",
        }
        for label, suffix in rebinds.items():
            with self.subTest(label), self.assertRaisesRegex(SystemExit, "CONFLICT_TEMPLATES is rebound"):
                checker.template_basis(self.variant(self.source + suffix))

    def test_review_1_blocking_bypasses_are_refused(self):
        # Re-gate review 1 (VETO at 0173adf7), findings B2 and B3, plus the binding forms it
        # showed were untested.
        alt = '(("location", "EVIL {old}", "EVIL {new}", "EVIL?"),)'
        signature = "def run_m4(pairs: int = 50) -> dict:"
        self.assertIn(signature, self.source)
        cases = {
            "B2 globals().update keyword": f"\nglobals().update(CONFLICT_TEMPLATES={alt})\n",
            "B2 vars().update keyword": f"\nvars().update(CONFLICT_TEMPLATES={alt})\n",
            "A1 constructed globals key": f"\nglobals()['CONFLICT_' + 'TEMPLATES'] = {alt}\n",
            "A1 setattr on sys.modules": f"\nimport sys as _s\nsetattr(_s.modules[__name__], 'X', {alt})\n",
            "A1 exec of bytes": f"\nexec(b'X = 1')\n",
            "A2 module class swap": "\nimport sys as _s, types as _t\nclass _M(_t.ModuleType):\n    pass\n"
                                    "_s.modules[__name__].__class__ = _M\n",
            "module __getattr__": "\ndef __getattr__(name):\n    return ()\n",
            "lambda parameter": f"\n_f = lambda CONFLICT_TEMPLATES={alt}: CONFLICT_TEMPLATES\n",
            "keyword-only parameter": "\ndef _g(*, CONFLICT_TEMPLATES=()):\n    return CONFLICT_TEMPLATES\n",
            "class definition": "\nclass CONFLICT_TEMPLATES:\n    pass\n",
            "async definition": "\nasync def CONFLICT_TEMPLATES():\n    return ()\n",
            "match star": "\nmatch [1]:\n    case [*CONFLICT_TEMPLATES]:\n        pass\n",
            "match mapping rest": "\nmatch {}:\n    case {**CONFLICT_TEMPLATES}:\n        pass\n",
            "type parameter": "\ndef _h[CONFLICT_TEMPLATES](x):\n    return x\n",
            "bytes literal of the name": "\n_b = b'CONFLICT_TEMPLATES'\n",
            "importlib": "\nimport importlib\n",
            # Each clause on its own, without a dynamic primitive that would also refuse it.
            "self-import attribute store": "\nimport run_semantic_route_ordering_report as _self\n"
                                           "_self.CONFLICT_TEMPLATES = ()\n",
            "keyword name alone": "\n_d = dict(CONFLICT_TEMPLATES=())\n",
        }
        for label, suffix in cases.items():
            with self.subTest(label), self.assertRaisesRegex(SystemExit, "CONFLICT_TEMPLATES is rebound"):
                checker.template_basis(self.variant(self.source + suffix))
        b3 = self.source.replace(signature, f"def run_m4(pairs: int = 50, CONFLICT_TEMPLATES={alt}) -> dict:")
        with self.assertRaisesRegex(SystemExit, "parameter binding"):
            checker.template_basis(self.variant(b3))

    def test_review_1_b1_encoding_cookie_is_refused(self):
        # B1: under a utf-7 cookie Python decodes "+AAo-" as a newline, so a UTF-8 comment is code.
        inject = '\nCONFLICT_TEMPLATES = (("location", "EVIL {old}", "EVIL {new}", "EVIL?"),)\n'
        body = ("# -*- coding: utf-7 -*-\n" + self.source).encode("utf-7") + b"# " + \
            inject.encode("utf-7").replace(b"\n", b"+AAo-", 1) + b"\n"
        path = Path(self.temp.name) / "run_semantic_route_ordering_report.py"
        path.write_bytes(body)
        with self.assertRaisesRegex(SystemExit, "decodes differently under Python"):
            checker.template_basis(path)
        path.write_bytes(b"\xef\xbb\xbf" + self.source.encode("utf-8"))  # BOM
        with self.assertRaisesRegex(SystemExit, "decodes differently under Python"):
            checker.template_basis(path)

    def test_review_1_a3_shadowing_package_is_refused(self):
        path = self.variant(self.source)
        path.with_suffix("").mkdir()
        (path.with_suffix("") / "__init__.py").write_text("CONFLICT_TEMPLATES = ()\n", encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "would shadow"):
            checker.template_basis(path)

    def test_review_1_a4_prefix_collision_is_refused_on_every_path(self):
        # A file with an altered template whose blob shares the frozen 32-bit prefix (found by the
        # reviewer's brute force). The historical prefix check would have accepted it.
        collision = Path(__file__).with_name("fixtures") / "currentness_a3" / "prefix-collision.txt"
        blob = subprocess.run(["git", "hash-object", str(collision)], cwd=checker.ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
        self.assertTrue(blob.startswith(checker.TEMPLATE_BLOB_PREFIX))
        self.assertNotEqual(blob, checker.TEMPLATE_FROZEN_BLOB)
        path = self.variant(collision.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(SystemExit, "shares the frozen prefix"):
            checker.template_basis(path)
        with self.assertRaisesRegex(SystemExit, "is not the frozen 745f789c"):
            checker.template_basis(path, require_frozen_blob=True)

    def test_strict_mode_reports_the_blob_before_parsing(self):
        for text in ("x = 1\n", "def broken(:\n"):
            with self.subTest(text), self.assertRaisesRegex(SystemExit, "is not the frozen 745f789c"):
                checker.template_basis(self.variant(text), require_frozen_blob=True)

    def test_review_1_uncovered_comparison_changes_are_refused(self):
        source = Path(checker.__file__).read_text(encoding="utf-8")
        k7_variants = (
            '                overlap_rule(record, templates, "K7_g3b_overlap")\n'
            '                if prior_texts:\n'
        )
        self.assertEqual(source.count(k7_variants), 1)
        mutations = {
            "TOKEN flags": source.replace('TOKEN = re.compile(r"[a-z0-9]+")', 'TOKEN = re.compile(r"[a-z0-9]+", re.I)'),
            "K7 dropped for variants": source.replace(k7_variants, "                if prior_texts:\n"),
            "K7 narrowed references": source.replace('overlap_rule(record, templates, "K7_g3b_overlap")',
                                                     'overlap_rule(record, templates[:3], "K7_g3b_overlap")', 1),
            "templates rebound in check": source.replace(
                "    rejections: list[dict] = []\n", "    templates = templates[:3]\n    rejections: list[dict] = []\n", 1),
        }
        for label, text in mutations.items():
            with self.subTest(label):
                self.assertNotEqual(text, source, "fixture failed to mutate the checker")
                module_path = Path(self.temp.name) / f"mutated_{len(label)}.py"
                module_path.write_text(text, encoding="utf-8")
                spec = importlib.util.spec_from_file_location(f"mutated_checker_{len(label)}", module_path)
                mutated = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mutated)
                mutated.ROOT = checker.ROOT
                mutated.TEMPLATE_SOURCE = checker.TEMPLATE_SOURCE
                with self.assertRaisesRegex(SystemExit, "contamination comparison differs"):
                    mutated.template_basis()

    def test_frozen_path_checks_the_recorded_texts(self):
        with mock.patch.object(checker, "TEMPLATE_TEXTS_SHA256", "0" * 64):
            with self.assertRaisesRegex(SystemExit, "frozen blob differ from the recorded digest"):
                checker.template_basis(self.variant(self.frozen))

    def test_binding_rule_accepts_the_frozen_blob_and_the_current_source(self):
        self.assertEqual(checker.template_binding_violations(self.frozen), [])
        self.assertEqual(checker.template_binding_violations(self.source), [])

    def test_changed_rule_application_is_refused(self):
        def strict_overlap(record, references, rule):
            for text in checker.record_texts(record):
                for reference in references:
                    if checker.similarity(text, reference) > checker.THRESHOLD:
                        raise checker.Reject(rule)

        def queries_only(record):
            return [record["query"]]

        for label, patcher in (("strict inequality", mock.patch.object(checker, "overlap_rule", strict_overlap)),
                               ("fewer texts compared", mock.patch.object(checker, "record_texts", queries_only))):
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
