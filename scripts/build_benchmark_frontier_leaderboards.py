#!/usr/bin/env python3
"""Build the read-only benchmark frontier projection (#779).

Default: JSON on stdout. An explicit output path is restricted to the
canonical generated UI artifact or a location outside this source checkout.
No benchmark is run, no raw evidence is modified, and no authority is granted.

Frontier objectives (PR #768 registry shape) are optional ownership context:

* no registry: the projection says ``absent`` and keeps all nine families;
* ``--objectives PATH``: read from an explicit path and labelled ``draft``
  unless ``--objectives-status canonical`` is passed deliberately;
* the committed path ``data/benchmark-frontier-objectives.json`` is used
  automatically as ``canonical`` once it exists in this checkout.
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
CANONICAL_OBJECTIVES = ROOT / "data/benchmark-frontier-objectives.json"


def _output_target(raw: Path) -> Path:
    """Guard committed evidence from accidental overwrite."""
    target = raw.resolve()
    root = ROOT.resolve()
    if (target == root or root in target.parents) and target != GENERATED.resolve():
        raise ValueError(
            "output within repository is restricted to derived UI frontier-leaderboards.json"
        )
    return target


def resolve_objectives(path: Path | None, status: str | None) -> tuple[dict | None, str, str | None]:
    """Return (registry, status, source) without inventing a registry."""
    if path is None:
        if CANONICAL_OBJECTIVES.exists():
            registry = json.loads(CANONICAL_OBJECTIVES.read_text(encoding="utf-8"))
            return registry, "canonical", str(CANONICAL_OBJECTIVES.relative_to(ROOT))
        return None, "absent", None
    registry = json.loads(path.read_text(encoding="utf-8"))
    return registry, status or "draft", str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write", action="store_true",
                        help="write canonical generated frontier-leaderboards.json")
    parser.add_argument("--check", action="store_true",
                        help="verify canonical generated artifact against exact F1 catalog")
    parser.add_argument("--objectives", type=Path, default=None,
                        help="optional frontier objectives registry (draft unless stated)")
    parser.add_argument("--objectives-status", choices=("draft", "canonical"), default=None,
                        help="label for an explicitly supplied registry (default draft)")
    args = parser.parse_args()
    if sum(bool(v) for v in (args.check, args.write, args.output is not None)) > 1:
        parser.error("--check, --write and --output are mutually exclusive")
    if args.objectives_status and args.objectives is None:
        parser.error("--objectives-status requires --objectives")
    if (args.write or args.check) and args.objectives is not None:
        parser.error("the canonical artifact never embeds an explicitly supplied registry")
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    registry, status, source = resolve_objectives(args.objectives, args.objectives_status)
    result = build_frontier_leaderboard(
        catalog, objectives=registry, objectives_status=status, objectives_source=source,
    )
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
