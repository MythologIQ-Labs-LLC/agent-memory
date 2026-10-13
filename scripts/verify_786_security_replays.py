#!/usr/bin/env python3
"""Independently verify committed #786 security replay evidence against fixtures, runner and runtime.

The same verification the #644 v7 replay evidence receives (``scripts/verify_644_v7_replays.py``),
applied to the separate #786 family: ``reference/run_786_security_replays.py``, the fixtures under
``reference/fixtures/786-security-replays/`` and the evidence under
``reports/validation/786-security-replays/``. The replays it verifies are the ones the given
declaration lists with ``kind: security_replay`` (default: the companion acceptance file of the
prepared cumulative v8 proposal, ``786-security-replay-acceptance.PROPOSED.json``; the #674 declaration
schema enumerates only ``public_gauntlet`` / ``replay`` / ``lane``, so the family is declared beside it).
VERIFIED is reproducible, untampered evidence for a reviewer; it is not acceptance.
"""
from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference"))
import run_786_security_replays as runner  # noqa: E402

v7 = runpy.run_path(str(ROOT / "scripts/verify_644_v7_replays.py"))
DECLARATION = ROOT / "reports/runtime/proposals/786-security-replay-acceptance.PROPOSED.json"
EVIDENCE_ROOT = ROOT / "reports/validation/786-security-replays"


def verify(evidence_root: Path = EVIDENCE_ROOT, declaration: Path = DECLARATION,
           fixture_dir: Path = runner.FIXTURE_DIR, reexecute: bool = False) -> dict:
    return v7["verify"](evidence_root, declaration, fixture_dir, reexecute, runner=runner, kind="security_replay")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT)
    parser.add_argument("--declaration", type=Path, default=DECLARATION)
    parser.add_argument("--reexecute", action="store_true")
    args = parser.parse_args(argv)
    result = verify(args.evidence_root, args.declaration, reexecute=args.reexecute)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["evidence_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
