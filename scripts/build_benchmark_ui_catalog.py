#!/usr/bin/env python3
"""Build the deterministic Benchmark Evidence Console catalog (#698).

    python scripts/build_benchmark_ui_catalog.py
    python scripts/build_benchmark_ui_catalog.py --check

The catalog is a read-only projection over committed benchmark evidence. It never
executes a benchmark and never grants runtime authority.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.evaluation.ui_catalog import build_catalog  # noqa: E402

DASHBOARD = ROOT / "reports" / "benchmarks" / "dashboard" / "current.json"
SCORECARDS = ROOT / "reports" / "benchmarks" / "scorecards" / "scorecards.json"
NORMALIZED = ROOT / "reports" / "benchmarks" / "normalized"
OUTPUT = ROOT / "reports" / "benchmarks" / "ui" / "catalog.json"
SCHEMA = ROOT / "schemas" / "benchmark-ui-catalog.schema.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_revision(spec: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", spec],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return value or None


def _source_identity() -> dict[str, str] | None:
    values = {
        "dashboard": _git_revision("HEAD:reports/benchmarks/dashboard/current.json"),
        "scorecards": _git_revision("HEAD:reports/benchmarks/scorecards/scorecards.json"),
        "normalized": _git_revision("HEAD:reports/benchmarks/normalized"),
    }
    return None if any(value is None for value in values.values()) else {key: str(value) for key, value in values.items()}


def build() -> dict:
    normalized = {
        str(path.relative_to(ROOT)): _load(path)
        for path in sorted(NORMALIZED.glob("*.json"))
    }
    catalog = build_catalog(
        dashboard=_load(DASHBOARD),
        scorecards=_load(SCORECARDS),
        normalized_runs=normalized,
        repository_head=_git_revision("HEAD"),
        source_identity=_source_identity(),
    )
    schema = _load(SCHEMA)
    errors = sorted(Draft202012Validator(schema).iter_errors(catalog), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        path = "$" + "".join(f"[{part!r}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path)
        raise ValueError(f"benchmark UI catalog schema violation at {path}: {error.message}")
    return catalog


def payload() -> bytes:
    return (json.dumps(build(), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    catalog = build()
    expected = (json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    if args.check:
        if not OUTPUT.is_file():
            print(f"stale or missing: {OUTPUT.relative_to(ROOT)}")
            return 1
        try:
            committed = _load(OUTPUT)
        except (OSError, json.JSONDecodeError):
            print(f"stale or invalid: {OUTPUT.relative_to(ROOT)}")
            return 1
        if committed != catalog:
            print(f"stale: {OUTPUT.relative_to(ROOT)}")
            return 1
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(expected)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
