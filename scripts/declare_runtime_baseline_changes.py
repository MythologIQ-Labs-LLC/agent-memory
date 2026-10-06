#!/usr/bin/env python3
"""Rewrite a successor declaration's ``declared_changes`` from the working tree (#674).

The register's ``declared_successor`` must already name the declaration. The block is
recomputed from ``git diff --name-only <frozen> -- <protected> <exclusions>`` against the
working tree and ``git hash-object`` of each listed file (``null`` for a deleted file), so
an author never computes a blob by hand. Nothing else in the declaration is touched, and
the file is written with the repository's two-space JSON layout.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_runtime_baseline_equivalence import (  # noqa: E402
    DEFAULT_REGISTER,
    current_entry,
    diff_pathspecs,
    load_boundary,
    load_register,
)

ROOT = Path(__file__).resolve().parents[1]


def working_tree_changes(root: Path, boundary: dict[str, Any]) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", str(boundary["frozen_revision"]), "--", *diff_pathspecs(boundary)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit("unable to diff the working tree against the frozen revision: " + result.stderr.strip())
    return sorted(line for line in result.stdout.splitlines() if line)


def working_tree_blob(root: Path, path: str) -> str | None:
    if not (root / path).is_file():
        return None
    result = subprocess.run(
        ["git", "hash-object", path],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit(f"unable to hash {path}: {result.stderr.strip()}")
    return result.stdout.strip()


def declared_changes(root: Path, register_path: Path | str = DEFAULT_REGISTER) -> list[dict[str, Any]]:
    register = load_register(root, register_path)
    boundary = load_boundary(root, current_entry(register)["source_boundary"])
    return [{"path": path, "blob": working_tree_blob(root, path)} for path in working_tree_changes(root, boundary)]


def rewrite(root: Path, declaration_path: str, register_path: Path | str = DEFAULT_REGISTER) -> list[dict[str, Any]]:
    register = load_register(root, register_path)
    declared = register.get("declared_successor")
    if declared is None:
        raise SystemExit("the register declares no successor; add declared_successor before declaring changes")
    if Path(declared["declaration"]) != Path(declaration_path):
        raise SystemExit(
            f"the register's declared successor is {declared['declaration']}, not {declaration_path}"
        )
    path = root / declaration_path
    try:
        declaration = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"unable to load declaration {declaration_path}: {exc}") from exc
    if not isinstance(declaration, dict):
        raise SystemExit("declaration root must be an object")
    changes = declared_changes(root, register_path)
    if not changes:
        raise SystemExit("the working tree carries no protected change; nothing to declare")
    declaration["declared_changes"] = changes
    path.write_text(json.dumps(declaration, indent=2) + "\n", encoding="utf-8")
    return changes


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--declaration", required=True, help="declaration path relative to the repository root")
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    changes = rewrite(args.root.resolve(), args.declaration, args.register)
    for item in changes:
        print(f"{item['path']} {item['blob'] or 'deleted'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
