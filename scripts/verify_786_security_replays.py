#!/usr/bin/env python3
"""Independently verify committed #786 security replay evidence against fixtures, runner and runtime.

The same verification the #644 v7 replay evidence receives (``scripts/verify_644_v7_replays.py``),
applied to the separate #786 family: ``reference/run_786_security_replays.py``, the fixtures under
``reference/fixtures/786-security-replays/`` and the evidence under
``reports/validation/786-security-replays-v3/`` (the -v2 evidence stays under
``786-security-replays/``, verifiable with ``--evidence-root`` and a declaration naming the -v2
ids). The replays it verifies are the ones the given declaration lists with
``kind: security_replay`` (default: the prepared cumulative v6 -> v8 declaration,
``786-cumulative-v6-to-v8.PROPOSED.json``; ``security_replay`` is a first-class acceptance
evidence kind of the declaration schema since the owner's checkpoint on PR #805). The runner
used for each replay is the one its fixture's ``dsl_version`` names (DSL/1: -v1/-v2, DSL/2:
-v3), so either generation's committed evidence verifies against the runner hash it recorded.
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

import run_786_security_replays_dsl2 as runner_dsl2  # noqa: E402

v7 = runpy.run_path(str(ROOT / "scripts/verify_644_v7_replays.py"))
DECLARATION = ROOT / "reports/runtime/proposals/786-cumulative-v6-to-v8.PROPOSED.json"
EVIDENCE_ROOT = ROOT / "reports/validation/786-security-replays-v3"
RUNNERS = {runner.DSL_VERSION: runner, runner_dsl2.DSL_VERSION: runner_dsl2}


def runner_for(replay_id: str, fixture_dir: Path):
    """The runner module a fixture declares through ``dsl_version`` (DSL/1 for -v1/-v2, DSL/2 for -v3).

    Each runner is frozen with its DSL, so committed evidence of either generation keeps
    verifying against the runner hash its manifest recorded."""
    fixture_path = fixture_dir / f"{replay_id}.json"
    if not fixture_path.is_file():
        return runner
    dsl = json.loads(fixture_path.read_text(encoding="utf-8")).get("dsl_version")
    try:
        return RUNNERS[dsl]
    except KeyError as exc:
        raise ValueError(f"{replay_id}: unknown dsl_version {dsl!r}") from exc


def verify(evidence_root: Path = EVIDENCE_ROOT, declaration: Path = DECLARATION,
           fixture_dir: Path = runner.FIXTURE_DIR, reexecute: bool = False) -> dict:
    rows = [v7["verify_one"](r, evidence_root, fixture_dir, reexecute, runner_for(r, fixture_dir))
            for r in v7["declared_replays"](declaration, "security_replay")]
    complete = all(r["status"] == "VERIFIED" and r["verdict"] == "PASS" for r in rows)
    return {"replays": rows, "evidence_verified": complete,
            "acceptance": "NOT GRANTED: requires an independent reviewer's decision recorded in META_LEDGER"}


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
