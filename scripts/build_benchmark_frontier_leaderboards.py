#!/usr/bin/env python3
"""Build the read-only benchmark frontier projection (#779).

Default: JSON on stdout. An explicit output path is restricted to the
canonical generated UI artifact or a location outside this source checkout.
No benchmark is run, no raw evidence is modified, and no authority is granted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.evaluation.ui_frontier_leaderboard import (  # noqa: E402
    build_frontier_leaderboard,
)

CATALOG = ROOT / "reports/benchmarks/ui/catalog.json"
GENERATED = ROOT / "reports/benchmarks/ui/frontier-leaderboards.json"


def _output_target(raw: Path) -> Path:
    """Guard committed evidence from accidental overwrite."""
    target = raw.resolve()
    root = ROOT.resolve()
    if (target == root or root in target.parents) and target != GENERATED.resolve():
        raise ValueError(
            "output within repository is restricted to derived UI frontier-leaderboards.json"
        )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write", action="store_true",
                        help="write canonical generated frontier-leaderboards.json")
    parser.add_argument("--check", action="store_true",
                        help="verify canonical generated artifact against exact F1 catalog")
    args = parser.parse_args()
    if sum(bool(v) for v in (args.check, args.write, args.output is not None)) > 1:
        parser.error("--check, --write and --output are mutually exclusive")
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    result = build_frontier_leaderboard(catalog)
    serialized = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if args.check:
        if not GENERATED.exists():
            parser.error(f"frontier projection does not exist yet: {GENERATED}")
        if json.loads(GENERATED.read_text(encoding="utf-8")) != result:
            parser.error("frontier projection is stale for this accepted evidence snapshot")
        print("frontier projection is current")
    elif args.write or args.output is not None:
        target = _output_target(GENERATED if args.write else args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8")
        print(target)
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
