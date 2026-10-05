#!/usr/bin/env python3
"""Check whether a candidate checkout preserves the frozen Runtime Baseline v1 source surface.

The baseline itself is immutable. This checker reads the separately reviewable source
boundary companion so benchmark/evaluation code can evolve without being mistaken for a
runtime behavior change, while every unclassified package path remains frozen by default.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOUNDARY = ROOT / "reports" / "runtime" / "baseline-v1-source-boundary.json"


def _load_boundary(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"unable to load runtime source boundary {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("runtime source boundary root must be an object")
    if value.get("baseline_mutation") is not False:
        raise SystemExit("runtime source boundary must explicitly state baseline_mutation=false")
    if value.get("authority_effect") != "none":
        raise SystemExit("runtime source boundary must retain authority_effect=none")
    frozen = value.get("frozen_revision")
    if not isinstance(frozen, str) or len(frozen) != 40 or any(ch not in "0123456789abcdef" for ch in frozen):
        raise SystemExit("runtime source boundary frozen_revision must be exact lowercase 40-hex")
    protected = value.get("protected_paths")
    if not isinstance(protected, list) or not protected or not all(isinstance(item, str) and item for item in protected):
        raise SystemExit("runtime source boundary protected_paths must be a non-empty string list")
    excluded = value.get("excluded_non_runtime_paths")
    if not isinstance(excluded, list):
        raise SystemExit("runtime source boundary excluded_non_runtime_paths must be a list")
    for item in excluded:
        if not isinstance(item, dict) or not isinstance(item.get("pathspec"), str):
            raise SystemExit("each excluded_non_runtime_paths entry requires a pathspec")
        pathspec = item["pathspec"]
        if not pathspec.startswith(":(exclude)"):
            raise SystemExit(f"excluded pathspec must be a Git exclude pathspec: {pathspec}")
    return value


def _require_commit(revision: str, label: str) -> None:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise SystemExit(f"{label} commit is unavailable: {revision}: {result.stderr.strip()}")


def _diff_args(boundary: dict[str, Any], candidate: str) -> list[str]:
    pathspecs = [str(item) for item in boundary["protected_paths"]]
    pathspecs.extend(str(item["pathspec"]) for item in boundary["excluded_non_runtime_paths"])
    return [
        "git",
        "diff",
        "--exit-code",
        str(boundary["frozen_revision"]),
        candidate,
        "--",
        *pathspecs,
    ]


def check(boundary_path: Path, candidate: str) -> int:
    boundary = _load_boundary(boundary_path)
    frozen = str(boundary["frozen_revision"])
    _require_commit(frozen, "frozen runtime")
    _require_commit(candidate, "candidate")

    result = subprocess.run(_diff_args(boundary, candidate), cwd=ROOT, check=False)
    if result.returncode == 1:
        raise SystemExit(
            f"candidate {candidate} changes the protected Runtime Baseline v1 source surface "
            f"relative to {frozen}"
        )
    if result.returncode != 0:
        raise SystemExit("unable to compare candidate checkout with Runtime Baseline v1")

    exclusions = ", ".join(
        str(item["path"]) for item in boundary["excluded_non_runtime_paths"]
    ) or "none"
    print(
        f"Runtime Baseline v1 source equivalence: PASS; frozen={frozen}; "
        f"candidate={candidate}; explicit non-runtime exclusions={exclusions}"
    )
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate",
        default="HEAD",
        help="candidate commit/ref to compare with the frozen baseline (default: HEAD)",
    )
    parser.add_argument(
        "--boundary",
        type=Path,
        default=DEFAULT_BOUNDARY,
        help="source-boundary JSON companion",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    boundary = args.boundary if args.boundary.is_absolute() else ROOT / args.boundary
    return check(boundary, args.candidate)


if __name__ == "__main__":
    raise SystemExit(main())
