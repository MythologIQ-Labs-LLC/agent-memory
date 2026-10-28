"""Mutation sensitivity of the #732 G3b amendment A3 tests (re-gate, #786).

Each mutation removes or weakens one A3 defence in a private copy of
``scripts/check_generalization_corpus.py``; the A3 tests are then run against that copy and
must fail for every mutation marked ``must_detect``. Mutations that are equivalent by
construction (another clause already refuses every input they admit) are reported, not
counted.

    PYTHONPATH=reference python reference/security_falsifiers/a3_regate_sensitivity.py
"""
from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

from tests import test_currentness_generalization as base_tests
from tests import test_currentness_generalization_amendment_a3 as a3_tests

CHECKER = base_tests.checker
SOURCE = Path(CHECKER.__file__).read_text(encoding="utf-8")

MUTATIONS = [
    # name, old, new, must_detect
    ("binding rule disabled", "    tree = ast.parse(text)\n    violations, stores = [], []",
     "    return []\n    tree = ast.parse(text)\n    violations, stores = [], []", True),
    ("binding check skipped on the current file", "    if violations:\n        raise SystemExit(f\"{TEMPLATE_AMENDMENT_ID}: CONFLICT_TEMPLATES is rebound",
     "    if False:\n        raise SystemExit(f\"{TEMPLATE_AMENDMENT_ID}: CONFLICT_TEMPLATES is rebound", True),
    ("sole top-level assignment not required", "    if len(stores) != 1 or len(top) != 1 or stores[0] is not top[0].targets[0]:",
     "    if False:", True),
    ("attribute store clause removed", "            if node.attr == TEMPLATE_NAME and isinstance(node.ctx, (ast.Store, ast.Del)):",
     "            if False:", True),
    ("dynamic namespace names allowed", "            elif node.id in _DYNAMIC_NAMES:", "            elif False:", True),
    ("dynamic namespace attributes allowed",
     '            elif node.attr in _DYNAMIC_ATTRIBUTES or (node.attr.startswith("__") and node.attr.endswith("__")):',
     "            elif False:", True),
    ("dunder attributes allowed", ' or (node.attr.startswith("__") and node.attr.endswith("__")):', ":", True),
    ("frame attributes allowed", '"modules", "_getframe", "f_globals",', '"modules",', True),
    ("getattr allowed", '"globals", "vars", "locals", "setattr", "delattr", "getattr",',
     '"globals", "vars", "locals", "setattr", "delattr",', True),
    ("audited template blob list ignored", "    if blob not in AUDITED_TEMPLATE_SOURCE_BLOBS:", "    if False:", True),
    ("checker audit digest ignored", "    if checker_audit_digest() != CHECKER_AUDIT_SHA256:", "    if False:", True),
    ("rule object identity ignored", " or not _rule_objects_intact():", ":", True),
    ("threshold type not checked", "type(THRESHOLD) is float and ", "", True),
    ("wrapped functions allowed", ' and not hasattr(function, "__wrapped__")', "", True),
    ("sibling modules allowed", '    findings += [f"sibling {other.name}"', '    findings += [] and [f"sibling {other.name}"', True),
    ("unchecked bytecode allowed", '                findings.append(f"unchecked hash-based bytecode {cached.name}")\n                continue',
     "                continue", True),
    ("foreign bytecode allowed", '            findings.append(f"unverifiable bytecode {cached.name} for another interpreter")\n            continue',
     "            continue", True),
    ("bytecode contents not compared", '        if not same:\n            findings.append', '        if False:\n            findings.append', True),
    ("CRLF not normalised", '    if as_python != as_utf8.replace("\\r\\n", "\\n").replace("\\r", "\\n"):',
     "    if as_python != as_utf8:", True),
    ("parse failure not reported", "        ast.parse(as_python)\n    except (SyntaxError, ValueError) as exc:",
     "        pass\n    except (SyntaxError, ValueError) as exc:", True),
    ("dynamic definitions allowed", "node.name == TEMPLATE_NAME or node.name in _DYNAMIC_DEFINITIONS):",
     "node.name == TEMPLATE_NAME):", True),
    ("class and async definitions allowed", "(ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and (",
     "ast.FunctionDef) and (", True),
    ("star import allowed", 'elif isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):',
     "elif False:", True),
    ("import of dynamic modules allowed", " or node.name.split(\".\")[0] in _DYNAMIC_NAMES):", "):", True),
    ("parameters allowed", "elif isinstance(node, ast.arg) and node.arg == TEMPLATE_NAME:", "elif False:", True),
    ("keyword names allowed", "elif isinstance(node, ast.keyword) and node.arg == TEMPLATE_NAME:", "elif False:", True),
    ("type parameters allowed", "elif type_params and isinstance(node, type_params) and node.name == TEMPLATE_NAME:",
     "elif False:", True),
    ("match star allowed", "(ast.MatchAs, ast.MatchStar)) and node.name", "ast.MatchAs) and node.name", True),
    ("match mapping rest allowed", "elif isinstance(node, ast.MatchMapping) and node.rest == TEMPLATE_NAME:", "elif False:", True),
    ("name literals allowed", "isinstance(node.value, (str, bytes)) and (", "False and (", True),
    ("del allowed", "if node.id == TEMPLATE_NAME and isinstance(node.ctx, (ast.Store, ast.Del)):",
     "if node.id == TEMPLATE_NAME and isinstance(node.ctx, ast.Store):", True),
    ("decode check disabled", '    if as_python != as_utf8.replace("\\r\\n", "\\n").replace("\\r", "\\n"):', "    if False:", True),
    ("shadowing package allowed", "    if source.with_suffix(\"\").is_dir():", "    if False:", True),
    ("prefix collision accepted on the amendment path", "    if blob.startswith(TEMPLATE_BLOB_PREFIX):\n        raise",
     "    if False:\n        raise", True),
    ("frozen path trusts the 32-bit prefix", "    if blob == TEMPLATE_FROZEN_BLOB:", "    if blob.startswith(TEMPLATE_BLOB_PREFIX):", True),
    ("frozen path skips the recorded texts", "        if texts_digest(frozen) != TEMPLATE_TEXTS_SHA256:", "        if False:", True),
    ("strict flag ignored", "    if require_frozen_blob:\n", "    if False:\n", True),
    ("literal comparison removed", "    if _templates_from_source(current_source) != frozen_rows:", "    if False:", True),
    ("text digest removed", "    if current != frozen or texts_digest(current) != TEMPLATE_TEXTS_SHA256:", "    if False:", True),
    ("rule digest removed", "    if comparison_rule_digest() != COMPARISON_RULE_SHA256 or not _rule_objects_intact():",
     "    if not _rule_objects_intact():", True),
    ("rule digest without TOKEN flags", '        parts += [TOKEN.pattern, repr(THRESHOLD), f"flags={TOKEN.flags}"]',
     "        parts += [TOKEN.pattern, repr(THRESHOLD), \"flags=32\"]", True),
    ("rule digest without application sites",
     '        parts += _application_sites(ast.parse(Path(__file__).read_text(encoding="utf-8")))',
     "        parts += []", True),

    ("frozen blob unavailability ignored", "    if frozen_source.returncode != 0:", "    if False:", True),
    # Equivalent by construction.
    ("global clause removed", "elif isinstance(node, (ast.Global, ast.Nonlocal)) and TEMPLATE_NAME in node.names:",
     "elif False:", False),
    ("binding identity clause removed", " or stores[0] is not top[0].targets[0]:", ":", False),
    # getsource fails only for rule objects not defined in the checker file, which
    # _rule_objects_intact refuses on its own.
    ("unreadable rule accepted", '        return "unverifiable"', "        return COMPARISON_RULE_SHA256", False),
    ("frozen blob binding check removed", "    if template_binding_violations(frozen_source.stdout):", "    if False:", False),
]


def _load(text: str, directory: Path, index: int):
    path = directory / f"check_generalization_corpus_m{index}.py"
    path.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"a3_mutant_{index}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = CHECKER.ROOT
    module.TEMPLATE_SOURCE = CHECKER.TEMPLATE_SOURCE
    # As if the editor also re-recorded the audit digest, so each remaining defence is exercised on
    # its own; the audit digest itself has its own mutation.
    module.CHECKER_AUDIT_SHA256 = module.checker_audit_digest()
    return module


def _run(module) -> unittest.TestResult:
    previous = a3_tests.checker
    a3_tests.checker = module
    try:
        suite = unittest.defaultTestLoader.loadTestsFromModule(a3_tests)
        return unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    finally:
        a3_tests.checker = previous


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        baseline = _run(_load(SOURCE, directory, 0))
        print(f"baseline (unmutated copy): {baseline.testsRun} tests, "
              f"{len(baseline.failures)} failures, {len(baseline.errors)} errors")
        if not baseline.wasSuccessful():
            print("A3 tests are not green on the unmutated checker; sensitivity is meaningless")
            return 2
        missed, killed = [], 0
        for index, (name, old, new, must_detect) in enumerate(MUTATIONS, start=1):
            if SOURCE.count(old) != 1:
                print(f"STALE    {name}: mutation anchor not found exactly once")
                missed.append(name)
                continue
            result = _run(_load(SOURCE.replace(old, new), directory, index))
            detected = not result.wasSuccessful()
            killed += detected
            status = "KILLED" if detected else ("SURVIVED" if must_detect else "equivalent")
            print(f"{status:10} {name}: {len(result.failures)}F/{len(result.errors)}E")
            if must_detect and not detected:
                missed.append(name)
    required = sum(1 for item in MUTATIONS if item[3])
    if missed:
        print(f"missed: {missed}")
        return 1
    print(f"every must-detect mutation was killed ({required}/{required}); {killed} killed in total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
