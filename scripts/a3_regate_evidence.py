#!/usr/bin/env python3
"""Revision-bound re-gate evidence for #732 G3b amendment A3 (#786).

Reproduces, at the committed HEAD, every check the A3 re-gate relies on, using code that is
independent of the checker wherever the checker would otherwise vouch for itself:

1. identity: HEAD, tree, and the blobs of the checker, the template source, the A3 tests and
   the frozen template blob;
2. comparison digest recomputed from git sources with a separate implementation (no import,
   no ``inspect``) at the gate-binding revisions 5555504 and 76a9e30 and at HEAD;
3. historical replay: the gate-frozen checker (76a9e30, template source at the frozen blob) and
   the HEAD checker on the recorded freeze and attempt-2 inputs, compared byte for byte, plus
   the HEAD checker in strict mode on the frozen bytes;
4. strict mode on the current template source is refused with the historical message;
5. the effective ``CONFLICT_TEMPLATES`` value an importer gets, read in a subprocess, equals the
   frozen literal; and no file in the repository rebinds or shadows it;
6. the A3 tests and the mutation-sensitivity harness, with their counts.

The record has ``authority_effect: none``; the verdict belongs to the independent reviewer.

    python scripts/a3_regate_evidence.py [--out PATH]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import textwrap
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = "scripts/check_generalization_corpus.py"
TEMPLATE_SOURCE = "reference/run_semantic_route_ordering_report.py"
A3_TESTS = "reference/tests/test_currentness_generalization_amendment_a3.py"
FROZEN_BLOB = "745f789c01b7a542f906a9034ae63ebdd6776f7c"
GATE_REVISIONS = ("5555504", "76a9e30")
FROZEN_CHECKER_REVISION = "76a9e30"
GC = "reports/benchmarks/currentness-generalization"
OUT = ROOT / GC / "amendments" / "A3" / "regate-evidence.json"


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- 2. independent digest ------------------------------------------------------------------

def _sites(tree: ast.AST) -> list[str]:
    out: list[str] = []
    stack: list[tuple[ast.AST, list[str]]] = [(tree, [])]
    while stack:
        node, path = stack.pop()
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "overlap_rule":
            out.append(" > ".join(path + [ast.dump(node)]))
        header = None
        kind = type(node).__name__
        if kind in ("For", "AsyncFor"):
            header = f"for {ast.dump(node.target)} in {ast.dump(node.iter)}"
        elif kind in ("If", "While"):
            header = f"{kind.lower()} {ast.dump(node.test)}"
        elif isinstance(node, ast.comprehension):
            header = f"comp {ast.dump(node.iter)} if " + "".join(map(ast.dump, node.ifs))
        elif kind in ("FunctionDef", "AsyncFunctionDef"):
            header = f"def {node.name}"
        for child in reversed(list(ast.iter_child_nodes(node))):
            stack.append((child, path + [header] if header else path))
    return out


def independent_digest(source: str) -> str:
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    parts = [ast.dump(ast.parse(textwrap.dedent(ast.get_source_segment(source, functions[name]))))
             for name in ("tokens", "similarity", "record_texts", "overlap_rule")]
    assigns = {node.targets[0].id: node.value for node in tree.body
               if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    token = assigns["TOKEN"]
    pattern = token.args[0].value
    flag_args = [eval(compile(ast.Expression(arg), "<flags>", "eval"), {"re": re}) for arg in token.args[1:]]
    parts += [pattern, repr(assigns["THRESHOLD"].value), f"flags={re.compile(pattern, *flag_args).flags}"]
    parts += _sites(tree)
    bindings = sum(1 for node in ast.walk(functions["check"])
                   if isinstance(node, ast.Name) and node.id == "templates" and isinstance(node.ctx, ast.Store))
    parts.append(f"templates bindings in check: {bindings}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def recorded_digest(source: str, name: str = "COMPARISON_RULE_SHA256") -> str:
    return re.search(rf'^{name} = "([0-9a-f]{{64}})"', source, re.MULTILINE).group(1)


class _UndoA3(ast.NodeTransformer):
    """Rewrite HEAD's check() into its 76a9e30 form by undoing exactly the A3 lines."""

    def visit_FunctionDef(self, node):
        if node.name == "check":
            node.args.kwonlyargs, node.args.kw_defaults = [], []
        return self.generic_visit(node)

    def visit_Assign(self, node):
        value = node.value
        if (isinstance(value, ast.Call) and getattr(value.func, "id", "") == "template_basis"
                and isinstance(node.targets[0], ast.Tuple)):
            return ast.Assign(targets=[ast.Name("templates", ast.Store())],
                              value=ast.Call(ast.Name("template_texts", ast.Load()), [], []), lineno=node.lineno)
        return self.generic_visit(node)

    def visit_Dict(self, node):
        keep = [(k, v) for k, v in zip(node.keys, node.values)
                if not (isinstance(k, ast.Constant) and k.value == "template_basis")]
        node.keys, node.values = [k for k, _ in keep], [v for _, v in keep]
        return self.generic_visit(node)


def check_body_equivalence(head_source: str) -> dict:
    """check() at HEAD equals check() at the gate-frozen checker once the A3 lines are undone."""
    def function(source):
        return next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "check")
    frozen = function(git("show", f"{FROZEN_CHECKER_REVISION}:{CHECKER}"))
    head = _UndoA3().visit(function(head_source))
    return {"against": git("rev-parse", FROZEN_CHECKER_REVISION),
            "equal_after_undoing_a3": ast.dump(head) == ast.dump(frozen),
            "a3_lines": ["keyword-only require_frozen_blob", "templates, basis = template_basis(...)",
                         "report key template_basis"]}


# --- 3./4. historical replay and strict mode -----------------------------------------------------

def _run_checker(script: Path, cwd: Path, args: list[str], out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([sys.executable, str(script), *args, "--report", str(out / "report.json"),
                             "--rejections", str(out / "rejections.json")],
                            cwd=cwd, capture_output=True, text=True)
    report = json.loads((out / "report.json").read_text()) if (out / "report.json").exists() else None
    return {"exit": result.returncode, "stdout": result.stdout, "stderr": result.stderr.strip()[-300:],
            "rejections": (out / "rejections.json").read_text() if (out / "rejections.json").exists() else None,
            "report": report}


def _comparable(report: dict | None) -> dict | None:
    if report is None:
        return None
    report = dict(report)
    report.pop("template_basis", None)
    report["inputs_sha256"] = sorted(report.get("inputs_sha256", {}).values())
    return report


def historical_replay(work: Path) -> dict:
    tree = work / "frozen-checker"
    subprocess.run(["git", "worktree", "add", "-q", "--detach", str(tree), FROZEN_CHECKER_REVISION], cwd=ROOT, check=True)
    try:
        if git("hash-object", TEMPLATE_SOURCE, cwd=tree) != FROZEN_BLOB:
            raise SystemExit("the gate-frozen worktree does not hold the frozen template blob")
        head_checker_in_frozen_tree = tree / "scripts" / "check_generalization_corpus_head.py"
        head_checker_in_frozen_tree.write_text((ROOT / CHECKER).read_text(encoding="utf-8"), encoding="utf-8")
        inputs = {
            "freeze": [f"{GC}/freeze/corpus.json", "--variants", f"{GC}/freeze/variants.json",
                       "--selection", f"{GC}/freeze/selection.json"],
            "attempt2": ["--author-dir", f"{GC}/authoring/attempt2/author-files",
                         "--selection", f"{GC}/authoring/attempt2/selection.json"],
        }
        comparisons = {}
        for name, args in inputs.items():
            absolute = [str(ROOT / a) if a.startswith(GC) else a for a in args]
            frozen = _run_checker(tree / CHECKER, tree, absolute, work / name / "frozen")
            head = _run_checker(ROOT / CHECKER, ROOT, absolute, work / name / "head")
            strict = _run_checker(head_checker_in_frozen_tree, tree, absolute + ["--require-frozen-blob"],
                                  work / name / "head-strict-frozen-bytes")
            comparisons[name] = {
                "frozen_checker_exit": frozen["exit"],
                "head_exit": head["exit"],
                "head_basis": (head["report"] or {}).get("template_basis"),
                "head_strict_on_frozen_bytes_basis": (strict["report"] or {}).get("template_basis"),
                "rejections": json.loads(frozen["rejections"]) if frozen["rejections"] else None,
                "rejections_byte_identical": frozen["rejections"] == head["rejections"] == strict["rejections"],
                "stdout_byte_identical": frozen["stdout"] == head["stdout"] == strict["stdout"],
                "report_identical_but_template_basis": _comparable(frozen["report"]) == _comparable(head["report"])
                                                       == _comparable(strict["report"]),
            }
        recorded = (ROOT / GC / "authoring" / "attempt2" / "rejections-final.json").read_text()
        comparisons["attempt2"]["equals_recorded_rejections_final"] = (
            (work / "attempt2" / "head" / "rejections.json").read_text() == recorded)
        strict_current = subprocess.run([sys.executable, str(ROOT / CHECKER), *[str(ROOT / a) if a.startswith(GC) else a
                                         for a in inputs["freeze"]], "--require-frozen-blob"],
                                        cwd=ROOT, capture_output=True, text=True)
        return {"frozen_checker_revision": git("rev-parse", FROZEN_CHECKER_REVISION),
                "comparisons": comparisons,
                "strict_mode_on_current_source": {
                    "exit": strict_current.returncode,
                    "refused_with_historical_message": f"is not the frozen {FROZEN_BLOB[:8]}" in strict_current.stderr}}
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(tree)], cwd=ROOT, check=True)


# --- 5. effective value and repository scan --------------------------------------------------------

EFFECTIVE = """
import ast, json, subprocess, sys
sys.path.insert(0, "reference")
from run_semantic_route_ordering_report import CONFLICT_TEMPLATES as direct
from run_cross_fact_currentness_report import CONFLICT_TEMPLATES as via_consumer
frozen_source = subprocess.run(["git", "cat-file", "-p", sys.argv[1]], capture_output=True, text=True, check=True).stdout
frozen = next(ast.literal_eval(n.value) for n in ast.parse(frozen_source).body
              if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "CONFLICT_TEMPLATES")
print(json.dumps({"direct_equals_frozen": tuple(direct) == tuple(frozen),
                  "consumer_equals_frozen": tuple(via_consumer) == tuple(frozen)}))
"""


def effective_value() -> dict:
    result = subprocess.run([sys.executable, "-I", "-c", EFFECTIVE, FROZEN_BLOB], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        return {"error": result.stderr.strip()[-400:]}
    return json.loads(result.stdout)


def repository_scan() -> dict:
    name = "CONFLICT_TEMPLATES"
    findings = []
    for relative in git("ls-files", "*.py").splitlines():
        path = ROOT / relative
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(path.read_bytes())
        except (SyntaxError, ValueError):
            continue
        imports_name = any(isinstance(n, ast.ImportFrom) and any(a.name == name for a in n.names) for n in ast.walk(tree))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == name and isinstance(node.ctx, (ast.Store, ast.Del)):
                findings.append(f"{relative}:{node.lineno} attribute binding")
            if imports_name and isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, (ast.Store, ast.Del)):
                findings.append(f"{relative}:{node.lineno} rebinds an imported {name}")
    shadows = [p for p in git("ls-files", "reference/run_semantic_route_ordering_report*").splitlines()
               if p != TEMPLATE_SOURCE]
    shadows += [str(p.relative_to(ROOT)) for p in (ROOT / "reference").glob("run_semantic_route_ordering_report/")]
    return {"rebinding_findings": findings, "shadowing_paths": shadows}


def _audit(head_source: str) -> dict:
    sys.path.insert(0, str(ROOT / "scripts"))
    import check_generalization_corpus as checker  # the audited checker, for its recorded constants

    blob = git("hash-object", TEMPLATE_SOURCE)
    return {
        "template_source_blob_audited": blob in checker.AUDITED_TEMPLATE_SOURCE_BLOBS,
        "audited_template_source_blobs": checker.AUDITED_TEMPLATE_SOURCE_BLOBS,
        "checker_audit_digest_recorded": recorded_digest(head_source, "CHECKER_AUDIT_SHA256"),
        "checker_audit_digest_matches": checker.checker_audit_digest() == recorded_digest(head_source, "CHECKER_AUDIT_SHA256"),
        "shadowing_artifacts": checker.shadowing_artifacts(ROOT / TEMPLATE_SOURCE),
    }


# --- 6. tests and sensitivity ----------------------------------------------------------------------

def _unittest(*modules: str) -> dict:
    result = subprocess.run([sys.executable, "-m", "unittest", *modules], cwd=ROOT / "reference",
                            capture_output=True, text=True)
    ran = re.search(r"Ran (\d+) tests?", result.stderr)
    return {"exit": result.returncode, "tests": int(ran.group(1)) if ran else None,
            "summary": result.stderr.strip().splitlines()[-1] if result.stderr.strip() else ""}


def sensitivity() -> dict:
    result = subprocess.run([sys.executable, "reference/security_falsifiers/a3_regate_sensitivity.py"], cwd=ROOT,
                            capture_output=True, text=True, env={"PYTHONPATH": "reference", "PATH": "/usr/bin:/bin"})
    lines = result.stdout.strip().splitlines()
    return {"exit": result.returncode, "killed": sum(l.startswith("KILLED") for l in lines),
            "survived": [l for l in lines if l.startswith(("SURVIVED", "STALE"))],
            "equivalent": [l.split(":")[0].removeprefix("equivalent").strip() for l in lines if l.startswith("equivalent")],
            "summary": lines[-1] if lines else ""}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    dirty = git("status", "--porcelain", "--", "scripts", "reference", GC + "/freeze", GC + "/authoring")
    head_source = (ROOT / CHECKER).read_text(encoding="utf-8")
    digests = {rev: independent_digest(git("show", f"{rev}:{CHECKER}")) for rev in GATE_REVISIONS}
    digests["HEAD"] = independent_digest(head_source)
    with tempfile.TemporaryDirectory() as temporary:
        replay = historical_replay(Path(temporary))
    record = {
        "schema_version": 1,
        "evidence_id": "plan-732-g3b-amendment-A3-786-regate-evidence",
        "amendment_id": "plan-732-g3b-amendment-A3-786",
        "identity": {
            "head": git("rev-parse", "HEAD"),
            "tree": git("rev-parse", "HEAD^{tree}"),
            "worktree_clean_for_inputs": dirty == "",
            "checker_blob": git("hash-object", CHECKER),
            "template_source_blob": git("hash-object", TEMPLATE_SOURCE),
            "a3_tests_blob": git("hash-object", A3_TESTS),
            "frozen_template_blob": FROZEN_BLOB,
            "python": sys.version.split()[0],
        },
        "comparison_digest": {
            "recorded": recorded_digest(head_source),
            "independent": digests,
            "matches_at_gate_revisions_and_head": len(set(digests.values()) | {recorded_digest(head_source)}) == 1,
        },
        "historical_replay": replay,
        "check_body": check_body_equivalence(head_source),
        "audit": _audit(head_source),
        "effective_value": effective_value(),
        "repository_scan": repository_scan(),
        "tests": _unittest("tests.test_currentness_generalization_amendment_a3", "tests.test_currentness_generalization"),
        "mutation_sensitivity": sensitivity(),
        "authority_effect": "none",
    }
    rr = replay["comparisons"]
    checks = {
        "worktree clean": dirty == "",
        "digest matches": record["comparison_digest"]["matches_at_gate_revisions_and_head"],
        "replay byte-identical": all(c["rejections_byte_identical"] and c["stdout_byte_identical"]
                                     and c["report_identical_but_template_basis"] for c in rr.values()),
        "replay bases": all(c["head_basis"] == "plan-732-g3b-amendment-A3-786"
                            and c["head_strict_on_frozen_bytes_basis"] == "frozen_blob" for c in rr.values()),
        "recorded rejections reproduced": rr["attempt2"]["equals_recorded_rejections_final"],
        "strict refuses current": replay["strict_mode_on_current_source"]["refused_with_historical_message"],
        "effective value frozen": record["effective_value"] == {"direct_equals_frozen": True, "consumer_equals_frozen": True},
        "no repository attribute or imported-name rebinding": not record["repository_scan"]["rebinding_findings"],
        "no tracked or host shadowing": not record["repository_scan"]["shadowing_paths"]
                                        and not record["audit"]["shadowing_artifacts"],
        "check body equals 76a9e30 but A3": record["check_body"]["equal_after_undoing_a3"],
        "template source is an audited blob": record["audit"]["template_source_blob_audited"],
        "checker is the audited checker": record["audit"]["checker_audit_digest_matches"],
        "tests pass": record["tests"]["exit"] == 0,
        "sensitivity complete": record["mutation_sensitivity"]["exit"] == 0 and not record["mutation_sensitivity"]["survived"],
    }
    record["checks"] = checks
    record["all_checks_hold"] = all(checks.values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for name, ok in checks.items():
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
    print(f"record: {args.out}")
    return 0 if record["all_checks_hold"] else 1


if __name__ == "__main__":
    sys.exit(main())
