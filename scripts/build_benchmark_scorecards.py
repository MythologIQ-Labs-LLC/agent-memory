#!/usr/bin/env python3
"""Regenerate normalized benchmark manifests and scorecards from committed evidence (#534).

    python scripts/build_benchmark_scorecards.py          # write outputs
    python scripts/build_benchmark_scorecards.py --check  # fail if committed outputs are stale

Inputs are the committed benchmark-native reports listed below; outputs are
reports/benchmarks/normalized/*.json and reports/benchmarks/scorecards/scorecards.{json,md}.
Pre-remediation evidence is read, never rewritten.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.evaluation.contract import canonical_json_bytes  # noqa: E402
from agentmem_ref.evaluation.normalize import normalize_agentmembench, normalize_longmemeval  # noqa: E402
from agentmem_ref.evaluation.registry import list_profiles  # noqa: E402
from agentmem_ref.evaluation.scorecard import build, render_markdown  # noqa: E402

SOURCES = (
    (normalize_longmemeval, "reports/benchmarks/longmemeval/longmemeval-s-full-f73b872.json"),
    (normalize_agentmembench, "reports/benchmarks/agentmembench/memdialogue-v2-no_memory-03197cd.json"),
    (normalize_agentmembench, "reports/benchmarks/agentmembench/memdialogue-v2-lexical_overlap-03197cd.json"),
    (normalize_agentmembench, "reports/benchmarks/agentmembench/memdialogue-v2-agent_memory-03197cd.json"),
)
NORMALIZED = ROOT / "reports" / "benchmarks" / "normalized"
SCORECARDS = ROOT / "reports" / "benchmarks" / "scorecards"


def outputs() -> dict[Path, bytes]:
    manifests = []
    for normalize, source in SOURCES:
        manifests.extend(normalize(json.loads((ROOT / source).read_text(encoding="utf-8"))))
    files: dict[Path, bytes] = {}
    for manifest in manifests:
        name = re.sub(r"[^a-z0-9_.-]+", "-", manifest["run_id"].lower())
        files[NORMALIZED / f"{name}.json"] = canonical_json_bytes(manifest)
    document = build(list_profiles(), manifests)
    files[SCORECARDS / "scorecards.json"] = (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    files[SCORECARDS / "scorecards.md"] = render_markdown(document).encode("utf-8")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = outputs()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, payload in files.items() if not path.is_file() or path.read_bytes() != payload]
        extra = [
            str(path.relative_to(ROOT))
            for folder in (NORMALIZED,)
            if folder.is_dir()
            for path in folder.glob("*.json")
            if path not in files
        ]
        for item in stale + extra:
            print(f"stale or unexpected: {item}")
        return 1 if stale or extra else 0
    for path, payload in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    print(f"wrote {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
