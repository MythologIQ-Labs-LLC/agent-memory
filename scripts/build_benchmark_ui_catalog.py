#!/usr/bin/env python3
"""Build the deterministic Benchmark Evidence Console catalog (#698).

    python scripts/build_benchmark_ui_catalog.py
    python scripts/build_benchmark_ui_catalog.py --check

The catalog is a read-only projection over committed benchmark evidence. It never
executes a benchmark and never grants runtime authority.
"""

from __future__ import annotations

import argparse
import hashlib
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
DIAGNOSTIC_SOURCES = (
    ROOT / "reports" / "benchmarks" / "replays" / "594-post-550-semantic-qualification" / "phase-b-score-v1.json",
)


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


def _git_blob_from_bytes(payload: bytes) -> str:
    """Git blob object ID of actual working-tree bytes, not stale HEAD."""
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def _working_tree_identity(folder: Path) -> str:
    """Flat normalized JSON tree, with the same Git tree identity as a commit.

    The normalized scorecard output is a flat directory of generated *.json
    blobs. Refuse other children instead of silently losing their provenance.
    """
    children = sorted(folder.iterdir(), key=lambda p: p.name.encode("utf-8"))
    if not children or any(not p.is_file() or not p.name.endswith(".json") for p in children):
        raise ValueError("normalized evidence tree must contain only JSON files")
    entries = bytearray()
    for p in children:
        entries.extend(b"100644 " + p.name.encode("utf-8") + b"\0")
        entries.extend(bytes.fromhex(_git_blob_from_bytes(p.read_bytes())))
    data = bytes(entries)
    return hashlib.sha1(b"tree " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _source_identity() -> dict[str, str]:
    """Bind projections to current source bytes even before companion commit.

    Using HEAD:<path> here silently pins a pre-refresh scorecard/normalized
    tree during post-commit regeneration. Once the companion commit lands,
    --check would find different source identities and report false staleness.
    """
    values = {
        "dashboard": _git_blob_from_bytes(DASHBOARD.read_bytes()),
        "diagnostics": _git_blob_from_bytes(DIAGNOSTIC_SOURCES[0].read_bytes()),
        "scorecards": _git_blob_from_bytes(SCORECARDS.read_bytes()),
        "normalized": _working_tree_identity(NORMALIZED),
    }
    return values


def build() -> dict:
    normalized = {
        str(path.relative_to(ROOT)): _load(path)
        for path in sorted(NORMALIZED.glob("*.json"))
    }
    catalog = build_catalog(
        dashboard=_load(DASHBOARD),
        scorecards=_load(SCORECARDS),
        normalized_runs=normalized,
        diagnostic_sources={str(path.relative_to(ROOT)): _load(path) for path in DIAGNOSTIC_SOURCES},
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
