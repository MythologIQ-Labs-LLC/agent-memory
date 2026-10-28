#!/usr/bin/env python3
"""Mechanical checks K1-K8 for the #732 generalization corpus (plan-732-generalization-gate G3).

This script never reads the runtime and never runs a case. It checks the author's
``corpus.json`` and, optionally, ``variants.json`` against the frozen schema and structural
rules. It then emits one rejection per failing record, as compact JSON ``[{id, file, rule}]``.
That JSON is the ``{REJECTIONS}`` value interpolated into the frozen ``replace.txt``. A record
is reported once, under the first rule it fails, in the order K1..K8.

The rules:

* ``K1_fields``: the exact field set and types, ids unique across both files, ``target_reference``
  unique within a record, indices in range, and no non-null ``source_ref`` beginning with
  ``actor:``.
* ``K2_expected``: P and R families expect ``engage``, N families expect ``refrain``. A variant's
  ``expected`` matches its kind.
* ``K3_order``: ``older_write < newer_write``.
* ``K4_recall_as_wrote``: ``recall_as`` is the ``(handle, scope)`` of at least one write.
* ``K5_structure_<family>``: base cases only. Sources are compared as effective sources, where
  null means ``actor:<handle>``; N9 compares declared sources instead.
* ``K6_variant_<type>``: a variant is compared with its base. The rule also covers
  ``n/a`` on a must-change type, a missing (base, type) pair (id ``<base>:<type>``) and a
  duplicate pair (``K6_variant_set_*``).
* ``K7_g3b_overlap``: any write text or query whose similarity with any of the 15 MESA
  ``CONFLICT_TEMPLATES`` texts is at least 0.5. The templates come from
  ``reference/run_semantic_route_ordering_report.py`` at blob ``745f789c``.
* ``K8_holdout_overlap``: holdouts only (``--prior``). Any text with similarity of at least 0.5
  against any text of a prior corpus fails.

Split files (amendment A1): ``assemble`` reads ``<stem>.json``, then ``<stem>_part2.json``,
``<stem>_part3.json`` and so on, until the first missing index. The attempt is invalid (exit 2) if:

* a part exists without the base file;
* a part lies beyond a gap;
* a part is not a JSON array.

Each rejection names the file that holds the record. When a selection is given but no variants
exist, every (base, type) pair is reported missing.

Exit codes: 0 for no rejections, 1 for rejections, 2 for an invalid attempt.

Similarity: text is lower-cased and tokenised with ``[a-z0-9]+``. If both texts have at least 3
tokens, similarity is the Jaccard of their token trigrams. Otherwise it is the Jaccard of their
token sets. Two empty sets score 0.

The script has ``authority_effect: none``.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import marshal
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_SOURCE = ROOT / "reference" / "run_semantic_route_ordering_report.py"
TEMPLATE_BLOB_PREFIX = "745f789c"
THRESHOLD = 0.5

# --- amendment A3 (#786 candidate, pending re-gate) ---------------------------------------------
# The G3b pin above is the frozen whole-file blob and is never edited. #786 changed code in the
# template source file *around* CONFLICT_TEMPLATES, which the whole-file pin cannot distinguish
# from a change to the templates themselves. A3 adds a narrower, stronger proof used only when
# the file no longer has the frozen blob: the frozen blob object must still resolve; the
# CONFLICT_TEMPLATES literal parsed from it and from the current file must be identical; the 15
# derived texts must hash to the recorded digest; and the contamination comparison (tokeniser,
# similarity, threshold) must hash to the recorded digest. Any difference is refused. Strict
# historical behaviour stays available with --require-frozen-blob.
# Re-gate (#786): consumers read the module's runtime value, so the frozen literal must also be
# the file's only binding of the name, the file must decode identically under Python and as
# UTF-8, and dynamic-namespace primitives are refused. The recorded comparison digest also covers
# how K7 and K8 apply the rule (record_texts, overlap_rule, every call site with its loop and
# branch path, TOKEN flags). Both the frozen path and strict mode require the full frozen blob,
# not its 32-bit prefix, and the frozen path checks the recorded template texts.
TEMPLATE_AMENDMENT_ID = "plan-732-g3b-amendment-A3-786"
TEMPLATE_FROZEN_BLOB = "745f789c01b7a542f906a9034ae63ebdd6776f7c"
TEMPLATE_TEXTS_SHA256 = "bb4d4da3d02b41a7602d43e85977ef69f091864b5feb42df29e7977d62666fdc"
# Identical at the gate-binding checker revisions 5555504 (A1 PASS) and 76a9e30 (freeze PASS). At
# 7b5f7a1 the K7 loops iterate ``corpus`` instead of ``enumerate(corpus)`` (A1 L3): the same records
# in the same order, but a different syntax tree, so that revision has another digest.
COMPARISON_RULE_SHA256 = "0bcc7365667fe14a64ec355d5ee6c9e0d35b2aa432e52b53f574fce8761d1f03"
TEMPLATE_NAME = "CONFLICT_TEMPLATES"
# Re-gate review 2 (#786): a deny-list of dynamic primitives cannot be complete (function
# __globals__, frame f_globals, constructed getattr names, builtins reached through attributes).
# A3 therefore accepts a changed template source only at an audited full blob: one whose effective
# templates were verified by scripts/a3_regate_evidence.py and an independent review. The static
# rules below are the audit's mechanical part and must still hold for an audited blob. A new blob
# is a new audit, recorded here by the gate that passes it.
AUDITED_TEMPLATE_SOURCE_BLOBS = {
    "7cb9535695dd5bc760831eba50aefd5622fc1fa5":
        "#786 run_m4 host binding (scope_distinct_v1, serial host-bound handles); templates unchanged",
}
# The checker cannot vouch for itself against edits to itself; the gate binds its blob. In band,
# any change to this module's syntax tree (outside this assignment) refuses the amendment path
# until a gate records the new digest (re-gate review 2, D1).
CHECKER_AUDIT_SHA256 = "ac622bc3565f14eb0fedb1e8e46fd38845fc718328ea4682a82dbbe6ef02a14a"

P_FAMILIES = [f"P{i}" for i in range(1, 14)]
R_FAMILIES = [f"R{i}" for i in range(1, 8)]
N_FAMILIES = [f"N{i}" for i in range(1, 14)]
FAMILIES = P_FAMILIES + R_FAMILIES + N_FAMILIES
EXACT_SIZE = {**{f: 12 for f in P_FAMILIES}, **{f: 8 for f in R_FAMILIES + N_FAMILIES}}
INVARIANCE = ["punctuation", "apostrophe", "adverb_placement", "subject_wording", "value_case", "unit_spelling"]
MUST_CHANGE = ["hedge", "attribution", "conditional", "coexistent", "change_source_ref", "change_actor", "change_scope", "dispute"]
TEXT_ONLY = {"hedge", "attribution", "conditional", "coexistent"}

CASE_FIELDS = {"case_id", "family", "expected", "writes", "older_write", "newer_write", "actions", "recall_as", "query", "rationale"}
VARIANT_FIELDS = {"variant_id", "base_case_id", "variant_type", "kind", "expected", "writes", "older_write", "newer_write", "actions", "recall_as", "query", "rationale"}
NA_FIELDS = {"variant_id", "base_case_id", "variant_type", "kind", "na_reason"}
WRITE_FIELDS = {"handle", "scope", "target_reference", "text", "source_ref"}
BODY_FIELDS = ["writes", "older_write", "newer_write", "actions", "recall_as", "query"]
TOKEN = re.compile(r"[a-z0-9]+")


class Reject(Exception):
    def __init__(self, rule: str):
        super().__init__(rule)
        self.rule = rule


# --- similarity -------------------------------------------------------------------------------

def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def similarity(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if len(ta) >= 3 and len(tb) >= 3:
        sa = {tuple(ta[i:i + 3]) for i in range(len(ta) - 2)}
        sb = {tuple(tb[i:i + 3]) for i in range(len(tb) - 2)}
    else:
        sa, sb = set(ta), set(tb)
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


def _templates_from_source(text: str) -> list:
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "CONFLICT_TEMPLATES" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit("CONFLICT_TEMPLATES not found")


# Names and attributes through which a module can read or rewrite its own namespace without a
# syntactic binding of TEMPLATE_NAME (globals().update(...), setattr(sys.modules[...]), exec,
# a module __class__ swap, a module __getattr__). Neither the frozen blob nor the current file
# uses any of them, so the rule refuses them outright (re-gate review 1, B2/A1/A2).
_DYNAMIC_NAMES = frozenset({
    "globals", "vars", "locals", "setattr", "delattr", "getattr", "exec", "eval", "compile",
    "__import__", "__builtins__", "builtins", "importlib", "inspect", "ctypes", "gc",
    "operator", "attrgetter", "methodcaller", "itemgetter",
})
# Every dunder attribute (function __globals__, __self__, __dict__, __class__, ...), frame and
# code attributes, sys._getframe and sys.modules, and the dynamic names reached as attributes.
_DYNAMIC_ATTRIBUTES = frozenset({"modules", "_getframe", "f_globals", "f_locals", "f_back", "gi_frame", "cr_frame",
                                 "tb_frame", "co_consts"}) | _DYNAMIC_NAMES
_DYNAMIC_DEFINITIONS = frozenset({"__getattr__", "__getattribute__", "__dir__", "__setattr__"})


def template_binding_violations(text: str) -> list[str]:
    """Every way ``text`` could bind CONFLICT_TEMPLATES other than one top-level literal assignment.

    Static and conservative. Besides every syntactic binding form (assignment targets of any
    kind, ``del``, ``global``/``nonlocal``, imports, definitions, parameters, keyword names,
    patterns, type parameters, attribute stores, the name as a string or bytes literal), it
    refuses the dynamic-namespace primitives in ``_DYNAMIC_NAMES`` and ``_DYNAMIC_ATTRIBUTES``.
    Rebinding from other modules and shadowing by another file are outside one file's syntax;
    ``template_basis`` refuses a shadowing package and the re-gate evidence scans the repository.
    """
    tree = ast.parse(text)
    violations, stores = [], []
    type_params = tuple(getattr(ast, name) for name in ("TypeVar", "ParamSpec", "TypeVarTuple") if hasattr(ast, name))
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Name):
            if node.id == TEMPLATE_NAME and isinstance(node.ctx, (ast.Store, ast.Del)):
                stores.append(node)
            elif node.id in _DYNAMIC_NAMES:
                violations.append(f"dynamic namespace primitive {node.id!r} at line {line}")
        elif isinstance(node, ast.Attribute):
            if node.attr == TEMPLATE_NAME and isinstance(node.ctx, (ast.Store, ast.Del)):
                violations.append(f"attribute binding at line {line}")
            elif node.attr in _DYNAMIC_ATTRIBUTES or (node.attr.startswith("__") and node.attr.endswith("__")):
                violations.append(f"dynamic namespace attribute {node.attr!r} at line {line}")
        elif isinstance(node, (ast.Global, ast.Nonlocal)) and TEMPLATE_NAME in node.names:
            violations.append(f"{type(node).__name__.lower()} declaration at line {line}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and (
                node.name == TEMPLATE_NAME or node.name in _DYNAMIC_DEFINITIONS):
            violations.append(f"definition of {node.name!r} at line {line}")
        elif isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
            violations.append(f"star import at line {line}")
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in _DYNAMIC_NAMES:
            violations.append(f"import from {node.module!r} at line {line}")
        elif isinstance(node, ast.alias) and (
                (node.asname or node.name.split(".")[0]) == TEMPLATE_NAME or node.name.split(".")[0] in _DYNAMIC_NAMES
                or node.name in _DYNAMIC_ATTRIBUTES):
            violations.append(f"import binding {node.name!r}")
        elif isinstance(node, ast.ExceptHandler) and node.name == TEMPLATE_NAME:
            violations.append(f"exception binding at line {line}")
        elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name == TEMPLATE_NAME:
            violations.append(f"pattern binding at line {line}")
        elif isinstance(node, ast.MatchMapping) and node.rest == TEMPLATE_NAME:
            violations.append(f"pattern binding at line {line}")
        elif isinstance(node, ast.arg) and node.arg == TEMPLATE_NAME:
            violations.append(f"parameter binding at line {line}")
        elif isinstance(node, ast.keyword) and node.arg == TEMPLATE_NAME:
            violations.append(f"keyword name at line {line}")
        elif type_params and isinstance(node, type_params) and node.name == TEMPLATE_NAME:
            violations.append(f"type parameter at line {line}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)) and (
                TEMPLATE_NAME in (node.value if isinstance(node.value, str) else node.value.decode("latin-1"))):
            violations.append(f"name used as a literal at line {line}")
    top = [node for node in tree.body if isinstance(node, ast.Assign) and len(node.targets) == 1
           and isinstance(node.targets[0], ast.Name) and node.targets[0].id == TEMPLATE_NAME]
    if len(stores) != 1 or len(top) != 1 or stores[0] is not top[0].targets[0]:
        violations.append(f"{len(stores)} name bindings; exactly one top-level assignment is required")
    return violations


def python_source(path: Path) -> str:
    """The source text exactly as the interpreter decodes it (PEP 263 cookie, BOM).

    The checker reads UTF-8; a file Python would decode differently (for example a utf-7
    cookie, where a UTF-8 comment becomes code) is refused (re-gate review 1, B1).
    """
    raw = path.read_bytes()
    try:
        as_python = importlib.util.decode_source(raw)
        as_utf8 = raw.decode("utf-8")
    except (UnicodeDecodeError, SyntaxError, LookupError) as exc:
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: template source is not decodable: {exc}") from exc
    # decode_source applies universal newlines; a CRLF working copy is not a different program.
    if as_python != as_utf8.replace("\r\n", "\n").replace("\r", "\n"):
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: template source decodes differently under Python than as UTF-8")
    try:
        ast.parse(as_python)
    except (SyntaxError, ValueError) as exc:
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: template source does not parse: {exc}") from exc
    return as_python


def shadowing_artifacts(source: Path) -> list[str]:
    """Host files an importer could load instead of ``source`` (re-gate review 1 A3, review 2 H1).

    A package directory or a sibling module file with the same name (an extension module,
    a sourceless .pyc) is refused. A bytecode cache entry is refused when an interpreter would
    load it in place of the source and it cannot be verified: an unchecked hash-based .pyc always;
    a timestamp or checked-hash .pyc that validates against the source only if it is this
    interpreter's and its code equals the source compiled here.
    """
    import importlib.util as util
    import sys as _sys

    findings = []
    stem = source.stem
    if source.with_suffix("").is_dir():
        findings.append(f"package {stem}/")
    findings += [f"sibling {other.name}" for other in sorted(source.parent.glob(f"{stem}.*")) if other != source]
    raw = source.read_bytes()
    stat = source.stat()
    for cached in sorted((source.parent / "__pycache__").glob(f"{stem}.*.pyc")):
        data = cached.read_bytes()
        if len(data) < 16:
            continue
        flags = int.from_bytes(data[4:8], "little")
        if flags & 0b1:
            if not flags & 0b10:
                findings.append(f"unchecked hash-based bytecode {cached.name}")
                continue
            if data[8:16] != util.source_hash(raw):
                # Normally recompiled, but loaded as-is under --check-hash-based-pycs never.
                findings.append(f"hash-based bytecode {cached.name} that does not match the source")
                continue
            would_load = True
        else:
            would_load = (int.from_bytes(data[8:12], "little") == int(stat.st_mtime) & 0xFFFFFFFF
                          and int.from_bytes(data[12:16], "little") == stat.st_size & 0xFFFFFFFF)
        if not would_load:
            continue  # stale: every interpreter recompiles from the source
        tag = cached.name[len(stem) + 1:].split(".")[0]
        if tag != _sys.implementation.cache_tag or data[:4] != util.MAGIC_NUMBER:
            findings.append(f"unverifiable bytecode {cached.name} for another interpreter")
            continue
        optimize = {"opt-1": 1, "opt-2": 2}.get(cached.name.split(".")[-2], 0)
        try:
            same = marshal.loads(data[16:]) == compile(raw, str(source), "exec", dont_inherit=True, optimize=optimize)
        except (ValueError, EOFError, TypeError, SyntaxError):
            same = False
        if not same:
            findings.append(f"bytecode {cached.name} differs from the source")
    return findings


def source_blob(path: Path) -> str:
    """The git blob id of ``path``'s bytes, computed here, not by ``git hash-object``.

    ``git hash-object`` applies clean filters and attributes that untracked host state (a
    .git/config, an attributes file, GIT_CONFIG_* environment variables) can supply, so it can be
    made to report the frozen or an audited blob for any bytes (re-gate review 3, R3-1). The one
    normalisation is the repository's own ``eol=lf``: CRLF becomes LF.
    """
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def checker_audit_digest() -> str:
    """Digest of this module's syntax tree, without the assignment that records it."""
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body
                 if not (isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "CHECKER_AUDIT_SHA256"
                                                              for t in node.targets))]
    return hashlib.sha256(ast.dump(tree).encode("utf-8")).hexdigest()


def _rule_objects_intact() -> bool:
    """The bound rule objects are this module's own definitions, unwrapped, of their exact types."""
    module_file = Path(__file__).resolve()
    functions = (tokens, similarity, record_texts, overlap_rule, check)
    return (type(THRESHOLD) is float and type(TOKEN) is re.Pattern
            and all(type(function).__name__ == "function" and not hasattr(function, "__wrapped__")
                    and Path(function.__code__.co_filename).resolve() == module_file
                    and function.__globals__ is globals() for function in functions))


def _texts_from_templates(rows) -> list[str]:
    texts = []
    for _slot, old, new, query in rows:
        texts += [old.replace("{old}", ""), new.replace("{new}", ""), query]
    if len(texts) != 15:
        raise SystemExit(f"expected 15 template texts, found {len(texts)}")
    return texts


def texts_digest(texts: list[str]) -> str:
    return hashlib.sha256(json.dumps(texts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _application_sites(tree: ast.Module) -> list[str]:
    """How K7 and K8 apply the rule: each overlap_rule call with every enclosing loop and branch header.

    Dropping a call, narrowing its references, iterating fewer records or adding a condition on the
    path changes the result; so does rebinding ``templates`` inside ``check``.
    """
    sites: list[str] = []

    def visit(node, path):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "overlap_rule":
            sites.append(" > ".join(path + [ast.dump(node)]))
        header = None
        if isinstance(node, (ast.For, ast.AsyncFor)):
            header = "for " + ast.dump(node.target) + " in " + ast.dump(node.iter)
        elif isinstance(node, (ast.If, ast.While)):
            header = type(node).__name__.lower() + " " + ast.dump(node.test)
        elif isinstance(node, ast.comprehension):
            header = "comp " + ast.dump(node.iter) + " if " + "".join(ast.dump(test) for test in node.ifs)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            header = "def " + node.name
        for child in ast.iter_child_nodes(node):
            visit(child, path + [header] if header else path)

    visit(tree, [])
    check_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "check")
    bindings = sum(1 for node in ast.walk(check_function)
                   if isinstance(node, ast.Name) and node.id == "templates" and isinstance(node.ctx, ast.Store))
    return sites + [f"templates bindings in check: {bindings}"]


def comparison_rule_digest() -> str:
    """Digest of the contamination comparison exactly as this checker executes it."""
    import inspect
    import textwrap

    try:
        parts = [ast.dump(ast.parse(textwrap.dedent(inspect.getsource(function))))
                 for function in (tokens, similarity, record_texts, overlap_rule)]
        parts += [TOKEN.pattern, repr(THRESHOLD), f"flags={TOKEN.flags}"]
        parts += _application_sites(ast.parse(Path(__file__).read_text(encoding="utf-8")))
    except (OSError, TypeError, SyntaxError, AttributeError, StopIteration):
        return "unverifiable"  # an unreadable rule is a changed rule
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def template_basis(source: Path = None, *, require_frozen_blob: bool = False) -> tuple[list[str], str]:
    """Return the 15 G3b template texts and the basis on which they were accepted."""
    source = TEMPLATE_SOURCE if source is None else source
    blob = source_blob(source)
    # The historical rule pins the blob by its prefix; a 32-bit prefix is forgeable (re-gate review 1,
    # A4), so both paths require the full frozen blob and, on the frozen path, the recorded texts.
    if blob == TEMPLATE_FROZEN_BLOB:
        # Host shadowing defeats the frozen bytes as much as changed ones (re-gate review 3, R3-2).
        shadows = shadowing_artifacts(source)
        if shadows:
            raise SystemExit(f"host files would shadow the frozen template source: {'; '.join(shadows)}")
        frozen = _texts_from_templates(_templates_from_source(python_source(source)))
        if texts_digest(frozen) != TEMPLATE_TEXTS_SHA256:
            raise SystemExit(f"template texts at the frozen blob differ from the recorded digest")
        return frozen, "frozen_blob"
    if require_frozen_blob:
        raise SystemExit(f"template source blob {blob} is not the frozen {TEMPLATE_BLOB_PREFIX}")
    if blob.startswith(TEMPLATE_BLOB_PREFIX):
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: template source blob {blob} shares the frozen prefix but is not "
                         f"the frozen blob {TEMPLATE_FROZEN_BLOB}")
    shadows = shadowing_artifacts(source)
    if shadows:
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: host files would shadow the template source: {'; '.join(shadows)}")
    frozen_source = subprocess.run(
        ["git", "cat-file", "-p", TEMPLATE_FROZEN_BLOB], cwd=ROOT, capture_output=True, text=True,
    )
    if frozen_source.returncode != 0:
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: frozen template blob {TEMPLATE_FROZEN_BLOB} is unavailable")
    frozen_rows = _templates_from_source(frozen_source.stdout)
    current_source = python_source(source)
    current = _texts_from_templates(_templates_from_source(current_source))
    if _templates_from_source(current_source) != frozen_rows:
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: CONFLICT_TEMPLATES differ from frozen blob {TEMPLATE_FROZEN_BLOB}")
    if template_binding_violations(frozen_source.stdout):
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: frozen blob {TEMPLATE_FROZEN_BLOB} fails the binding rule")
    violations = template_binding_violations(current_source)
    if violations:
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: CONFLICT_TEMPLATES is rebound: {'; '.join(violations)}")
    frozen = _texts_from_templates(frozen_rows)
    if current != frozen or texts_digest(current) != TEMPLATE_TEXTS_SHA256:
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: template texts differ from the recorded digest")
    if blob not in AUDITED_TEMPLATE_SOURCE_BLOBS:
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: template source blob {blob} is not an audited template source")
    if comparison_rule_digest() != COMPARISON_RULE_SHA256 or not _rule_objects_intact():
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: contamination comparison differs from the recorded rule")
    if checker_audit_digest() != CHECKER_AUDIT_SHA256:
        raise SystemExit(f"{TEMPLATE_AMENDMENT_ID}: contamination comparison differs from the recorded rule "
                         "(the checker is not the audited checker)")
    return current, TEMPLATE_AMENDMENT_ID


def template_texts(*, require_frozen_blob: bool = False) -> list[str]:
    return template_basis(require_frozen_blob=require_frozen_blob)[0]


def record_texts(record: dict) -> list[str]:
    return [w["text"] for w in record.get("writes", [])] + [record.get("query", "")]


# --- K1 -----------------------------------------------------------------------------------------

def _nonempty_str(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _index(value, n: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < n


def check_body(record: dict) -> None:
    writes = record["writes"]
    if not isinstance(writes, list) or len(writes) < 2:
        raise Reject("K1_fields")
    refs = []
    for write in writes:
        if not isinstance(write, dict) or set(write) != WRITE_FIELDS:
            raise Reject("K1_fields")
        if write["handle"] not in ("A", "B") or write["scope"] not in ("S1", "S2"):
            raise Reject("K1_fields")
        if not _nonempty_str(write["target_reference"]) or not _nonempty_str(write["text"]):
            raise Reject("K1_fields")
        source = write["source_ref"]
        if source is not None and (not _nonempty_str(source) or source.startswith("actor:")):
            raise Reject("K1_fields")
        refs.append(write["target_reference"])
    if len(set(refs)) != len(refs):
        raise Reject("K1_fields")
    n = len(writes)
    if not _index(record["older_write"], n) or not _index(record["newer_write"], n):
        raise Reject("K1_fields")
    if record["older_write"] == record["newer_write"]:
        raise Reject("K1_fields")
    actions = record["actions"]
    if not isinstance(actions, list):
        raise Reject("K1_fields")
    for action in actions:
        if not isinstance(action, dict) or set(action) != {"action", "write"}:
            raise Reject("K1_fields")
        if action["action"] not in ("dispute", "forget") or not _index(action["write"], n):
            raise Reject("K1_fields")
    recall_as = record["recall_as"]
    if not isinstance(recall_as, dict) or set(recall_as) != {"handle", "scope"}:
        raise Reject("K1_fields")
    if recall_as["handle"] not in ("A", "B") or recall_as["scope"] not in ("S1", "S2"):
        raise Reject("K1_fields")
    if not _nonempty_str(record["query"]) or not _nonempty_str(record["rationale"]):
        raise Reject("K1_fields")


def check_order_and_recall(record: dict) -> None:
    if not record["older_write"] < record["newer_write"]:
        raise Reject("K3_order")
    wrote = {(w["handle"], w["scope"]) for w in record["writes"]}
    if (record["recall_as"]["handle"], record["recall_as"]["scope"]) not in wrote:
        raise Reject("K4_recall_as_wrote")


# --- K5 -----------------------------------------------------------------------------------------

def effective_source(write: dict) -> str:
    return write["source_ref"] if write["source_ref"] is not None else f"actor:{write['handle']}"


def check_structure(case: dict) -> None:
    family = case["family"]
    old, new = case["writes"][case["older_write"]], case["writes"][case["newer_write"]]
    actions = case["actions"]
    same_handle = old["handle"] == new["handle"]
    same_scope = old["scope"] == new["scope"]
    same_source = effective_source(old) == effective_source(new)
    recall_is_old = case["recall_as"] == {"handle": old["handle"], "scope": old["scope"]}
    rule = f"K5_structure_{family}"
    if family in ("N7",):
        ok = same_scope and old["source_ref"] is not None and new["source_ref"] is not None and not same_source and not actions
    elif family == "N8":
        ok = same_handle and same_scope and not same_source and not actions
    elif family == "N9":
        ok = not same_handle and same_scope and old["source_ref"] == new["source_ref"] and not actions
    elif family == "N10":
        ok = not same_scope and same_handle and same_source and not actions
    elif family == "N13":
        ok = same_handle and same_scope and same_source and any(a["write"] == case["newer_write"] for a in actions)
    else:
        ok = same_handle and same_scope and same_source and not actions and recall_is_old
    if not ok:
        raise Reject(rule)


# --- K6 -----------------------------------------------------------------------------------------

def _body(record: dict) -> dict:
    return {key: copy.deepcopy(record[key]) for key in BODY_FIELDS}


def check_variant(variant: dict, base: dict) -> None:
    vtype = variant["variant_type"]
    rule = f"K6_variant_{vtype}"
    vb, bb = _body(variant), _body(base)
    if vtype in INVARIANCE:
        if len(vb["writes"]) != len(bb["writes"]):
            raise Reject(rule)
        stripped_v = copy.deepcopy(vb)
        stripped_b = copy.deepcopy(bb)
        for record in (stripped_v, stripped_b):
            record["query"] = ""
            for write in record["writes"]:
                write["text"] = ""
        if stripped_v != stripped_b:
            raise Reject(rule)
        if all(v["text"] == b["text"] for v, b in zip(vb["writes"], bb["writes"])):
            raise Reject(rule)
        return
    if vb["older_write"] != bb["older_write"] or vb["newer_write"] != bb["newer_write"]:
        raise Reject(rule)
    if len(vb["writes"]) != len(bb["writes"]):
        raise Reject(rule)
    newer, older = bb["newer_write"], bb["older_write"]
    restored = copy.deepcopy(vb)
    vnew = vb["writes"][newer]
    if vtype in TEXT_ONLY:
        if vnew["text"] == bb["writes"][newer]["text"]:
            raise Reject(rule)
        restored["writes"][newer]["text"] = bb["writes"][newer]["text"]
    elif vtype == "change_source_ref":
        if vnew["source_ref"] == vb["writes"][older]["source_ref"]:
            raise Reject(rule)
        restored["writes"][newer]["source_ref"] = bb["writes"][newer]["source_ref"]
    elif vtype == "change_actor":
        if vnew["handle"] == vb["writes"][older]["handle"]:
            raise Reject(rule)
        restored["writes"][newer]["handle"] = bb["writes"][newer]["handle"]
    elif vtype == "change_scope":
        if vnew["scope"] == vb["writes"][older]["scope"]:
            raise Reject(rule)
        restored["writes"][newer]["scope"] = bb["writes"][newer]["scope"]
    elif vtype == "dispute":
        if vb["actions"] != bb["actions"] + [{"action": "dispute", "write": newer}]:
            raise Reject(rule)
        restored["actions"] = bb["actions"]
    if restored != bb:
        raise Reject(rule)


# --- driver -------------------------------------------------------------------------------------

def overlap_rule(record: dict, references: list[str], rule: str) -> None:
    for text in record_texts(record):
        for reference in references:
            if similarity(text, reference) >= THRESHOLD:
                raise Reject(rule)


def check(
    corpus: list,
    variants: list | None,
    selection: list | None,
    prior_texts: list[str],
    corpus_files: list | None = None,
    variant_files: list | None = None,
    *,
    require_frozen_blob: bool = False,
) -> dict:
    def file_of(files: list | None, index: int, default: str) -> str:
        return files[index] if files else default

    templates, basis = template_basis(require_frozen_blob=require_frozen_blob)
    rejections: list[dict] = []
    seen_ids: set = set()
    valid_cases: dict = {}

    if not isinstance(corpus, list):
        raise SystemExit("corpus.json must be a JSON array")
    for index, record in enumerate(corpus):
        rid = record.get("case_id") if isinstance(record, dict) else None
        try:
            if not isinstance(record, dict) or set(record) != CASE_FIELDS or not _nonempty_str(rid):
                raise Reject("K1_fields")
            if rid in seen_ids or record["family"] not in FAMILIES:
                raise Reject("K1_fields")
            check_body(record)
            if record["expected"] != ("refrain" if record["family"].startswith("N") else "engage"):
                raise Reject("K2_expected")
            check_order_and_recall(record)
            check_structure(record)
            overlap_rule(record, templates, "K7_g3b_overlap")
            if prior_texts:
                overlap_rule(record, prior_texts, "K8_holdout_overlap")
            valid_cases[rid] = record
        except Reject as exc:
            rejections.append({"id": rid if isinstance(rid, str) else "<missing>", "file": file_of(corpus_files, index, "corpus.json"), "rule": exc.rule})
        if isinstance(rid, str):
            seen_ids.add(rid)

    family_counts = Counter(case["family"] for case in valid_cases.values())
    report = {
        "family_valid_counts": {f: family_counts.get(f, 0) for f in FAMILIES},
        "family_short": {f: EXACT_SIZE[f] - family_counts.get(f, 0) for f in FAMILIES if family_counts.get(f, 0) < EXACT_SIZE[f]},
        "family_over": {f: family_counts[f] - EXACT_SIZE[f] for f in FAMILIES if family_counts.get(f, 0) > EXACT_SIZE[f]},
    }

    if variants is not None:
        selected = set(selection or [])
        pairs: set = set()
        for index, record in enumerate(variants):
            rid = record.get("variant_id") if isinstance(record, dict) else None
            try:
                if not isinstance(record, dict) or not _nonempty_str(rid) or rid in seen_ids:
                    raise Reject("K1_fields")
                vtype, kind = record.get("variant_type"), record.get("kind")
                if vtype not in INVARIANCE + MUST_CHANGE or record.get("base_case_id") not in selected:
                    raise Reject("K1_fields")
                if kind != ("invariance" if vtype in INVARIANCE else "must_change"):
                    raise Reject("K1_fields")
                pair = (record["base_case_id"], vtype)
                if pair in pairs:
                    raise Reject("K6_variant_set_duplicate")
                if set(record) == NA_FIELDS:
                    if vtype not in INVARIANCE:
                        raise Reject(f"K6_variant_{vtype}")
                    if not _nonempty_str(record["na_reason"]):
                        raise Reject("K1_fields")
                    pairs.add(pair)
                    continue
                if set(record) != VARIANT_FIELDS:
                    raise Reject("K1_fields")
                check_body(record)
                if record["expected"] != ("same_as_base" if kind == "invariance" else "refrain"):
                    raise Reject("K2_expected")
                check_order_and_recall(record)
                base = valid_cases.get(record["base_case_id"])
                if base is None:
                    raise Reject("K1_fields")
                check_variant(record, base)
                overlap_rule(record, templates, "K7_g3b_overlap")
                if prior_texts:
                    overlap_rule(record, prior_texts, "K8_holdout_overlap")
                pairs.add(pair)
            except Reject as exc:
                rejections.append({"id": rid if isinstance(rid, str) else "<missing>", "file": file_of(variant_files, index, "variants.json"), "rule": exc.rule})
            if isinstance(rid, str):
                seen_ids.add(rid)
        for base_id in sorted(selected):
            for vtype in INVARIANCE + MUST_CHANGE:
                if (base_id, vtype) not in pairs and not any(
                    r["file"].startswith("variants") and r["id"] in _ids_for(variants, base_id, vtype) for r in rejections
                ):
                    rejections.append({"id": f"{base_id}:{vtype}", "file": "variants.json", "rule": "K6_variant_set_complete"})

    rejections.sort(key=lambda r: (r["file"], r["id"], r["rule"]))
    report.update({
        "rejections": rejections,
        "valid_case_ids": sorted(valid_cases),
        "template_blob_prefix": TEMPLATE_BLOB_PREFIX,
        "template_basis": basis,
        "authority_effect": "none",
    })
    return report


def _ids_for(variants: list, base_id: str, vtype: str) -> set:
    return {
        r.get("variant_id")
        for r in variants
        if isinstance(r, dict) and r.get("base_case_id") == base_id and r.get("variant_type") == vtype
    }


class InvalidAttempt(Exception):
    """The author's files cannot be assembled mechanically; the attempt is invalid (exit 2)."""


def assemble(directory: Path, stem: str) -> tuple[list, list, list] | None:
    """Assemble ``stem.json`` and its consecutive parts.

    Returns ``(records, record_files, names)``, where ``record_files[i]`` is the file holding
    ``records[i]``. It returns None only when neither the base file nor any part exists. A part
    without the base file, a part beyond a gap, or a part that is not a JSON array raises
    ``InvalidAttempt``.
    """

    parts = sorted(p.name for p in directory.glob(f"{stem}_part*.json"))
    if not (directory / f"{stem}.json").exists():
        if parts:
            raise InvalidAttempt(f"{stem}.json is missing but part file(s) exist: {parts}")
        return None
    names = [f"{stem}.json"]
    k = 2
    while (directory / f"{stem}_part{k}.json").exists():
        names.append(f"{stem}_part{k}.json")
        k += 1
    stray = [name for name in parts if name not in names]
    if stray:
        raise InvalidAttempt(f"part file(s) beyond a gap: {stray}")
    records: list = []
    record_files: list = []
    for name in names:
        try:
            data = json.loads((directory / name).read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise InvalidAttempt(f"{name} is not valid JSON: {exc}") from exc
        if not isinstance(data, list):
            raise InvalidAttempt(f"{name} is not a JSON array")
        records += data
        record_files += [name] * len(data)
    return records, record_files, names


def compact(value) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("corpus", type=Path, nargs="?")
    parser.add_argument("--author-dir", type=Path, help="assemble corpus (and variants, if present) from split files")
    parser.add_argument("--assembled-out", type=Path, help="with --author-dir: write assembled arrays to this directory")
    parser.add_argument("--variants", type=Path)
    parser.add_argument("--selection", type=Path, help="compact JSON list from select_metamorphic_bases.py")
    parser.add_argument("--prior", type=Path, action="append", default=[], help="prior corpus or variants file (holdouts)")
    parser.add_argument("--report", type=Path, help="write the full report here")
    parser.add_argument("--rejections", type=Path, help="write the compact {REJECTIONS} JSON here")
    parser.add_argument("--require-frozen-blob", action="store_true",
                        help="strict historical G3b: refuse unless the template source has the frozen blob")
    args = parser.parse_args(argv)

    corpus_files = variant_files = None
    assembled_files: dict = {}
    if args.author_dir:
        try:
            assembled = assemble(args.author_dir, "corpus")
            if assembled is None:
                raise InvalidAttempt("corpus.json is missing")
            corpus, corpus_files, assembled_files["corpus"] = assembled
            assembled_variants = assemble(args.author_dir, "variants")
        except InvalidAttempt as exc:
            sys.stderr.write(f"INVALID ATTEMPT: {exc}\n")
            return 2
        variants = None
        if assembled_variants is not None:
            variants, variant_files, assembled_files["variants"] = assembled_variants
        if args.assembled_out:
            args.assembled_out.mkdir(parents=True, exist_ok=True)
            (args.assembled_out / "corpus.json").write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            if variants is not None:
                (args.assembled_out / "variants.json").write_text(json.dumps(variants, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    else:
        corpus = json.loads(args.corpus.read_text(encoding="utf-8"))
        variants = json.loads(args.variants.read_text(encoding="utf-8")) if args.variants else None
    selection = json.loads(args.selection.read_text(encoding="utf-8")) if args.selection else None
    prior_texts: list[str] = []
    for path in args.prior:
        for record in json.loads(path.read_text(encoding="utf-8")):
            if isinstance(record, dict) and "writes" in record:
                prior_texts += record_texts(record)
    if selection is not None and variants is None:
        # A selection without variants: every (base, type) pair is missing (K6_variant_set_complete).
        variants = []
    report = check(corpus, variants, selection, prior_texts, corpus_files, variant_files,
                   require_frozen_blob=args.require_frozen_blob)
    inputs = [args.corpus, args.variants, args.selection, *args.prior]
    if args.author_dir:
        inputs += [args.author_dir / name for names in assembled_files.values() for name in names]
        report["assembled_files"] = assembled_files
    report["inputs_sha256"] = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs if path is not None
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.rejections:
        args.rejections.write_text(compact(report["rejections"]), encoding="utf-8")
    sys.stdout.write(json.dumps({k: report[k] for k in ("family_short", "family_over")}, sort_keys=True) + "\n")
    sys.stdout.write(f"rejections: {len(report['rejections'])}\n")
    return 0 if not report["rejections"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
