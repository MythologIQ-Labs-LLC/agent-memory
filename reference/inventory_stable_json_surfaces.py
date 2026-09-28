from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

DEFAULT_ROOTS = (
    Path("reference"),
    Path("scripts"),
    Path("reports/benchmarks/replays"),
)


def _literal(node: ast.AST | None) -> Any:
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return "<dynamic>"


def _qualname(stack: list[str]) -> str:
    return ".".join(stack) if stack else "<module>"


def _risk_hint(path: Path) -> str:
    text = path.as_posix()
    if any(
        marker in text
        for marker in (
            "agentmem_ref/state/",
            "agentmem_ref/runtime/restart_runtime.py",
            "agentmem_ref/runtime/sqlite_runtime.py",
            "agentmem_ref/runtime/configured_restart.py",
            "agentmem_ref/runtime/checkpoint_transactions.py",
            "agentmem_ref/runtime/runtime_config.py",
            "agentmem_ref/memory/checkpoint_migration.py",
            "agentmem_ref/api/surface.py",
        )
    ):
        return "runtime_or_persistence_candidate"
    if "/harness/" in text or "/evaluation/" in text or path.name.startswith("run_"):
        return "evaluation_or_evidence_candidate"
    if text.startswith("reports/benchmarks/replays/"):
        return "historical_replay_candidate"
    return "unclassified_candidate"


class Visitor(ast.NodeVisitor):
    def __init__(self, path: Path, source: str) -> None:
        self.path = path
        self.source = source
        self.stack: list[str] = []
        self.rows: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> Any:
        if not self._is_json_dumps(node.func):
            self.generic_visit(node)
            return

        keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
        sort_keys = _literal(keywords.get("sort_keys"))
        if sort_keys is not True:
            self.generic_visit(node)
            return

        separators = _literal(keywords.get("separators"))
        ensure_ascii = _literal(keywords.get("ensure_ascii")) if "ensure_ascii" in keywords else "<default_true>"
        allow_nan = _literal(keywords.get("allow_nan")) if "allow_nan" in keywords else "<default_true>"
        segment = ast.get_source_segment(self.source, node) or ""
        segment = " ".join(segment.split())
        if len(segment) > 300:
            segment = segment[:297] + "..."

        self.rows.append(
            {
                "path": self.path.as_posix(),
                "line": node.lineno,
                "scope": _qualname(self.stack),
                "sort_keys": True,
                "separators": separators,
                "ensure_ascii": ensure_ascii,
                "allow_nan": allow_nan,
                "risk_hint": _risk_hint(self.path),
                "source": segment,
            }
        )
        self.generic_visit(node)

    @staticmethod
    def _is_json_dumps(node: ast.AST) -> bool:
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "dumps"
            and isinstance(node.value, ast.Name)
            and node.value.id in {"json", "_json"}
        )


def inventory(root: Path, roots: tuple[Path, ...]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    parsed_files = 0
    parse_errors: list[dict[str, str]] = []

    for relative_root in roots:
        candidate_root = root / relative_root
        if not candidate_root.exists():
            continue
        for path in sorted(candidate_root.rglob("*.py")):
            relative = path.relative_to(root)
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=relative.as_posix())
            except (OSError, SyntaxError, UnicodeError) as exc:
                parse_errors.append({"path": relative.as_posix(), "error": str(exc)})
                continue
            parsed_files += 1
            visitor = Visitor(relative, source)
            visitor.visit(tree)
            rows.extend(visitor.rows)

    rows.sort(key=lambda row: (row["path"], row["line"], row["scope"]))
    serialized_rows = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["risk_hint"]] = counts.get(row["risk_hint"], 0) + 1

    return {
        "schema_version": 1,
        "inventory_kind": "stable_json_dumps_sort_keys_candidates",
        "roots": [item.as_posix() for item in roots],
        "parsed_python_files": parsed_files,
        "candidate_count": len(rows),
        "risk_hint_counts": dict(sorted(counts.items())),
        "candidate_rows_sha256": hashlib.sha256(serialized_rows).hexdigest(),
        "parse_errors": parse_errors,
        "candidates": rows,
        "qualification": [
            "AST inventory only; risk_hint is non-normative and requires manual consequence classification",
            "captures json/_json.dumps calls with literal sort_keys=True",
            "does not prove that a candidate feeds a digest or persisted identity",
            "does not capture custom serializers or dynamically aliased json.dumps without separate review",
        ],
        "authority_effect": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = inventory(args.repo_root.resolve(), DEFAULT_ROOTS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("candidate_count", "risk_hint_counts", "candidate_rows_sha256", "parse_errors")}, indent=2, sort_keys=True))
    return 1 if payload["parse_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
