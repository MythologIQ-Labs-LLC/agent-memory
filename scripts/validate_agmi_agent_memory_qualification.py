#!/usr/bin/env python3
"""Validate the pinned agmi Agent Memory result against the frozen evidence contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        default="reports/gauntlet/agmi-agent-memory-v1/qualification.json",
    )
    parser.add_argument("evidence")
    args = parser.parse_args()

    profile = json.loads((ROOT / args.profile).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))

    if evidence.get("qualification_id") != profile["qualification_id"]:
        fail("qualification identity mismatch")
    if evidence.get("authority_effect") != "none":
        fail("external integrity evidence must have authority_effect none")
    if evidence.get("evidence_class") != "independent_external_benchmark":
        fail("agmi raw result must remain independent_external_benchmark evidence")

    agmi = evidence.get("agmi") or {}
    if agmi.get("revision") != profile["agmi"]["revision"]:
        fail(f"agmi revision mismatch: {agmi.get('revision')!r}")
    if agmi.get("version") != profile["agmi"]["version"]:
        fail(f"agmi package version mismatch: {agmi.get('version')!r}")
    if agmi.get("detection_point") != "read":
        fail(f"Agent Memory agmi detection point moved: {agmi.get('detection_point')!r}")

    agent_memory = evidence.get("agent_memory") or {}
    if agent_memory.get("runtime_baseline_revision") != profile["agent_memory"]["runtime_baseline_revision"]:
        fail("frozen Agent Memory runtime revision mismatch")
    if agent_memory.get("version") != profile["agent_memory"]["version"]:
        fail(f"Agent Memory package version mismatch: {agent_memory.get('version')!r}")

    expected = profile["expected_external_observation"]["attacks"]
    rows = evidence.get("results")
    if not isinstance(rows, list):
        fail("evidence.results must be a list")
    by_attack = {row.get("attack"): row for row in rows}
    if set(by_attack) != set(expected):
        fail(f"attack set mismatch: observed={sorted(by_attack)} expected={sorted(expected)}")

    for attack, expected_status in expected.items():
        row = by_attack[attack]
        if row.get("native_status") != expected_status:
            fail(
                f"{attack} external observation changed: "
                f"observed={row.get('native_status')!r} expected={expected_status!r}"
            )
        if row.get("error") is not None or row.get("guard") is not None:
            fail(f"{attack} is not evaluable: error={row.get('error')!r} guard={row.get('guard')!r}")
        if row.get("evidence_qualification") != "sufficient":
            fail(f"{attack} lacks sufficient evaluator evidence")
        if row.get("detection_point") != "read":
            fail(f"{attack} detection point is not read")
        expected_behavior = "pass" if expected_status == "safe" else "fail"
        if row.get("behavioral_outcome") != expected_behavior:
            fail(
                f"{attack} normalized behavioral outcome mismatch: "
                f"{row.get('behavioral_outcome')!r} != {expected_behavior!r}"
            )

    # The known T9 weakness is part of the accepted evidence contract. A pipeline that
    # silently converts it to green would be less trustworthy, not more.
    if by_attack["snapshot_rollback"]["native_status"] != "VULNERABLE":
        fail("T9 whole-state snapshot rollback finding was not preserved")

    print(
        "agmi Agent Memory integrity evidence is qualified: "
        "T1-T8 safe/read-detected; T9 snapshot rollback remains VULNERABLE"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
