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

    def test_only_an_audited_template_source_blob_is_accepted(self):
        # Re-gate review 2: a change around the templates is accepted only at an audited blob.
        self.assertIn(subprocess.run(["git", "hash-object", str(checker.TEMPLATE_SOURCE)], cwd=checker.ROOT,
                                     capture_output=True, text=True, check=True).stdout.strip(),
                      checker.AUDITED_TEMPLATE_SOURCE_BLOBS)
        _, basis = checker.template_basis(self.variant(self.source))
        self.assertEqual(basis, checker.TEMPLATE_AMENDMENT_ID)
        for change in ("\n# unrelated harness change\n", "\nUNRELATED = 1\n"):
            with self.subTest(change), self.assertRaisesRegex(SystemExit, "is not an audited template source"):
                checker.template_basis(self.variant(self.source + change))

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
                # As if the editor also re-recorded the audit digest: the rule digest must still refuse.
                mutated.CHECKER_AUDIT_SHA256 = mutated.checker_audit_digest()
                with self.assertRaisesRegex(SystemExit, "contamination comparison differs from the recorded rule$"):
                    mutated.template_basis()

    def _mutated_checker(self, text: str, label: str, *, rerecord_audit: bool):
        path = Path(self.temp.name) / f"checker_{abs(hash(label))}.py"
        path.write_text(text, encoding="utf-8")
        spec = importlib.util.spec_from_file_location(f"checker_{abs(hash(label))}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.ROOT = checker.ROOT
        module.TEMPLATE_SOURCE = checker.TEMPLATE_SOURCE
        if rerecord_audit:
            module.CHECKER_AUDIT_SHA256 = module.checker_audit_digest()
        return module

    def test_review_2_n1_namespace_rewrites_are_refused(self):
        alt = '(("location", "EVIL {old}", "EVIL {new}", "EVIL?"),)'
        key = '"SETALPMET_TCILFNOC"[::-1]'
        cases = {
            "function __globals__": f"\nrun_m4.__globals__[{key}] = {alt}\n",
            "frame f_globals": f"\nimport sys as _s\n_s._getframe().f_globals[{key}] = {alt}\n",
            "constructed getattr": f"\nimport sys as _s\ngetattr(_s, 'mod' + 'ules')[__name__] = None\n",
            "builtins through __self__": f"\nprint.__self__.exec({key} + ' = ' + {alt!r})\n",
            "inspect": "\nimport inspect\n",
            "gc": "\nimport gc\n",
        }
        for label, suffix in cases.items():
            with self.subTest(label), self.assertRaisesRegex(SystemExit, "CONFLICT_TEMPLATES is rebound"):
                checker.template_basis(self.variant(self.source + suffix))

    def test_review_2_d1_checker_edits_beside_k7_are_refused(self):
        source = Path(checker.__file__).read_text(encoding="utf-8")
        basis_line = "    templates, basis = template_basis(require_frozen_blob=require_frozen_blob)\n"
        self.assertEqual(source.count(basis_line), 1)
        mutations = {
            "templates narrowed in place": source.replace(basis_line, basis_line + "    templates[:] = templates[:3]\n"),
            "K7 rejections filtered": source.replace("    rejections.sort(key=",
                                                     '    rejections = [r for r in rejections if r["rule"] != "K7"]\n'
                                                     "    rejections.sort(key=", 1),
            "overlap_rule wrapped": source + "\nimport functools\noverlap_rule = functools.wraps(overlap_rule)"
                                             "(lambda record, references, rule: None)\n",
            "THRESHOLD subclass": source.replace("THRESHOLD = 0.5\n", "class _T(float):\n    def __le__(self, other):\n"
                                                 "        return False\nTHRESHOLD = _T(0.5)\n", 1),
        }
        for label, text in mutations.items():
            with self.subTest(label):
                self.assertNotEqual(text, source)
                mutated = self._mutated_checker(text, label, rerecord_audit=False)
                with self.assertRaisesRegex(SystemExit, "not the audited checker|differs from the recorded rule"):
                    mutated.template_basis()
        # Rebinding the rule objects is refused even when the audit digest is re-recorded.
        for label in ("overlap_rule wrapped", "THRESHOLD subclass"):
            with self.subTest(f"{label}, audit re-recorded"):
                mutated = self._mutated_checker(mutations[label], label + "-rerecorded", rerecord_audit=True)
                with self.assertRaisesRegex(SystemExit, "contamination comparison differs from the recorded rule$"):
                    mutated.template_basis()

    def test_checker_audit_digest_refuses_any_unrecorded_checker_edit(self):
        source = Path(checker.__file__).read_text(encoding="utf-8")
        self.assertEqual(checker.checker_audit_digest(), checker.CHECKER_AUDIT_SHA256)
        mutated = self._mutated_checker(source + "\n_UNRELATED = 1\n", "unrelated", rerecord_audit=False)
        with self.assertRaisesRegex(SystemExit, "not the audited checker"):
            mutated.template_basis()

    def test_review_2_h1_host_shadowing_is_refused(self):
        import importlib.util as util
        import marshal
        import py_compile
        import sys

        def fresh():
            directory = Path(tempfile.mkdtemp(dir=self.temp.name))
            path = directory / "run_semantic_route_ordering_report.py"
            path.write_text(self.source, encoding="utf-8")
            return path

        cache = lambda path, tag=sys.implementation.cache_tag: path.parent / "__pycache__" / f"{path.stem}.{tag}.pyc"
        genuine = fresh()
        py_compile.compile(str(genuine), cfile=str(cache(genuine)), doraise=True)
        self.assertEqual(checker.shadowing_artifacts(genuine), [])
        self.assertEqual(checker.template_basis(genuine)[1], checker.TEMPLATE_AMENDMENT_ID)

        evil = self.source + '\nCONFLICT_TEMPLATES = (("location", "EVIL {old}", "EVIL {new}", "EVIL?"),)\n'
        unchecked = fresh()
        evil_path = unchecked.with_name("evil_source.py")
        evil_path.write_text(evil, encoding="utf-8")
        py_compile.compile(str(evil_path), cfile=str(cache(unchecked)), doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        evil_path.unlink()
        tampered = fresh()
        py_compile.compile(str(tampered), cfile=str(cache(tampered)), doraise=True)
        header = cache(tampered).read_bytes()[:16]
        cache(tampered).write_bytes(header + marshal.dumps(compile(evil, str(tampered), "exec")))
        foreign = fresh()
        py_compile.compile(str(foreign), cfile=str(cache(foreign, "cpython-399")), doraise=True)
        extension = fresh()
        extension.with_name(f"{extension.stem}.cpython-312-x86_64-linux-gnu.so").write_bytes(b"\x7fELF")
        for label, path, reason in (("unchecked hash pyc", unchecked, "unchecked hash-based bytecode"),
                                    ("tampered timestamp pyc", tampered, "differs from the source"),
                                    ("foreign interpreter pyc", foreign, "for another interpreter"),
                                    ("extension module", extension, "sibling")):
            with self.subTest(label), self.assertRaisesRegex(SystemExit, reason):
                checker.template_basis(path)
        self.assertTrue(util.MAGIC_NUMBER)

    def test_review_2_h2_crlf_and_unparsable_sources(self):
        crlf = Path(self.temp.name) / "crlf.py"
        crlf.write_bytes(self.frozen.replace("\n", "\r\n").encode("utf-8"))
        self.assertEqual(checker.python_source(crlf), self.frozen)
        with self.assertRaisesRegex(SystemExit, "does not parse"):
            checker.template_basis(self.variant("def broken(:\n"))

    def test_review_3_r1_git_filters_cannot_forge_the_blob(self):
        # Untracked host configuration can make `git hash-object` report the frozen or the audited
        # blob for any bytes; the checker hashes the bytes itself.
        import os

        evil = self.frozen + '\nCONFLICT_TEMPLATES = (("location", "EVIL {old}", "EVIL {new}", "EVIL?"),)\n'
        target = self.variant(evil)
        forged = Path(self.temp.name) / "forged-frozen.txt"
        forged.write_text(self.frozen, encoding="utf-8")
        attributes = Path(self.temp.name) / "attributes"
        attributes.write_text("run_semantic_route_ordering_report.py filter=judge\n", encoding="utf-8")
        env = {"GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "core.attributesFile", "GIT_CONFIG_VALUE_0": str(attributes),
               "GIT_CONFIG_KEY_1": "filter.judge.clean", "GIT_CONFIG_VALUE_1": f"cat {forged}"}
        with mock.patch.dict(os.environ, env):
            reported = subprocess.run(["git", "hash-object", str(target)], cwd=checker.ROOT, capture_output=True,
                                      text=True, check=True).stdout.strip()
            self.assertEqual(reported, checker.TEMPLATE_FROZEN_BLOB, "the attack precondition no longer holds")
            self.assertNotEqual(checker.source_blob(target), checker.TEMPLATE_FROZEN_BLOB)
            for strict in (False, True):
                with self.subTest(strict=strict), self.assertRaises(SystemExit):
                    checker.template_basis(target, require_frozen_blob=strict)
        self.assertEqual(checker.source_blob(checker.TEMPLATE_SOURCE),
                         subprocess.run(["git", "hash-object", "--no-filters", str(checker.TEMPLATE_SOURCE)],
                                        cwd=checker.ROOT, capture_output=True, text=True, check=True).stdout.strip())

    def test_review_3_r2_frozen_path_refuses_host_shadowing(self):
        path = self.variant(self.frozen)
        self.assertEqual(checker.template_basis(path)[1], "frozen_blob")
        path.with_suffix("").mkdir()
        (path.with_suffix("") / "__init__.py").write_text("CONFLICT_TEMPLATES = ()\n", encoding="utf-8")
        for strict in (False, True):
            with self.subTest(strict=strict), self.assertRaisesRegex(SystemExit, "would shadow the frozen"):
                checker.template_basis(path, require_frozen_blob=strict)

    def test_review_3_r3_mismatched_checked_hash_bytecode_is_refused(self):
        import py_compile
        import sys

        directory = Path(tempfile.mkdtemp(dir=self.temp.name))
        path = directory / "run_semantic_route_ordering_report.py"
        other = directory / "other.py"
        other.write_text(self.source + "\nX = ()\n", encoding="utf-8")
        cache = directory / "__pycache__" / f"{path.stem}.{sys.implementation.cache_tag}.pyc"
        py_compile.compile(str(other), cfile=str(cache), doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH)
        other.unlink()
        path.write_text(self.source, encoding="utf-8")
        with self.assertRaisesRegex(SystemExit, "does not match the source"):
            checker.template_basis(path)

    def test_review_3_attribute_access_helpers_are_refused(self):
        for label, suffix in (("attrgetter", "\nfrom operator import attrgetter as _a\n"),
                              ("from sys import modules", "\nfrom sys import modules as _m\n"),
                              ("dotted dynamic module", "\nimport importlib.util\n"),
                              ("dotted dynamic module from", "\nfrom ctypes.util import find_library\n")):
            with self.subTest(label), self.assertRaisesRegex(SystemExit, "CONFLICT_TEMPLATES is rebound"):
                checker.template_basis(self.variant(self.source + suffix))

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
