"""Run the deterministic multi-session agent-utility scenarios (#819 longitudinal lane).

Usage::

    PYTHONPATH=. python run_longitudinal_utility.py --arm baseline --out report.json
    PYTHONPATH=. python run_longitudinal_utility.py --arm typed_replacement --out report.json

``--arm baseline`` opens every handle with defaults. ``--arm typed_replacement`` opens with
``unspecified_intent_currentness="typed_replacement"`` (only on a runtime that has the option).
Local only; no network, model, or hosted CI.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from agentmem_ref.evaluation import longitudinal_utility as lu

ARMS = {
    "baseline": {},
    "typed_replacement": {"unspecified_intent_currentness": "typed_replacement"},
}


def _source_revision() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
                              cwd=Path(__file__).resolve().parent).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", choices=sorted(ARMS), default="baseline")
    parser.add_argument("--fixture", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    report = {"arm": args.arm, "source_revision": _source_revision(),
              **lu.run_fixture(args.fixture, open_kwargs=ARMS[args.arm])}
    text = json.dumps(report, indent=1, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    overall = report["summary"]["overall"]
    print(f"{args.arm}: {overall['success']}/{overall['probes']} probes succeed; "
          f"stale_used={overall['stale_used']} incorrect_supersession={overall['incorrect_supersession']}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
