#!/usr/bin/env python3
"""Validate the pinned agmi Agent Memory result against the frozen evidence contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(message)


def validate_identity(profile: dict, evidence: dict, *, label: str) -> None:
    if evidence.get("qualification_id") != profile["qualification_id"]:
        fail(f"{label}: qualification identity mismatch")
    if evidence.get("authority_effect") != "none":
        fail(f"{label}: external integrity evidence must have authority_effect none")
    if evidence.get("evidence_class") != "independent_external_benchmark":
        fail(f"{label}: agmi result must remain independent_external_benchmark evidence")

    agmi = evidence.get("agmi") or {}
    if agmi.get("revision") != profile["agmi"]["revision"]:
        fail(f"{label}: agmi revision mismatch: {agmi.get('revision')!r}")
    if agmi.get("version") != profile["agmi"]["version"]:
        fail(f"{label}: agmi package version mismatch: {agmi.get('version')!r}")
    if agmi.get("detection_point") != "read":
        fail(f"{label}: Agent Memory agmi detection point moved: {agmi.get('detection_point')!r}")

    agent_memory = evidence.get("agent_memory") or {}
    if agent_memory.get("runtime_baseline_revision") != profile["agent_memory"]["runtime_baseline_revision"]:
        fail(f"{label}: frozen Agent Memory runtime revision mismatch")
    if agent_memory.get("version") != profile["agent_memory"]["version"]:
        fail(f"{label}: Agent Memory package version mismatch: {agent_memory.get('version')!r}")


def validate_rows(profile: dict, evidence: dict, *, label: str) -> None:
    expected = profile["expected_external_observation"]["attacks"]
    rows = evidence.get("results")
    if not isinstance(rows, list):
        fail(f"{label}: evidence.results must be a list")
    by_attack = {row.get("attack"): row for row in rows}
    if set(by_attack) != set(expected):
        fail(f"{label}: attack set mismatch: observed={sorted(by_attack)} expected={sorted(expected)}")

    for attack, expected_status in expected.items():
        row = by_attack[attack]
        if row.get("native_status") != expected_status:
            fail(
                f"{label}: {attack} external observation changed: "
                f"observed={row.get('native_status')!r} expected={expected_status!r}"
            )
        if row.get("error") is not None or row.get("guard") is not None:
            fail(f"{label}: {attack} is not evaluable: error={row.get('error')!r} guard={row.get('guard')!r}")
        if row.get("evidence_qualification") != "sufficient":
            fail(f"{label}: {attack} lacks sufficient evaluator evidence")
        if row.get("detection_point") != "read":
            fail(f"{label}: {attack} detection point is not read")
        version = row.get("version", row.get("attack_version"))
        if version != 1:
            fail(f"{label}: {attack} attack definition version moved: {version!r}")
        expected_behavior = "pass" if expected_status == "safe" else "fail"
        if row.get("behavioral_outcome") != expected_behavior:
            fail(
                f"{label}: {attack} normalized behavioral outcome mismatch: "
                f"{row.get('behavioral_outcome')!r} != {expected_behavior!r}"
            )

    # The known T9 weakness is part of the accepted evidence contract. A pipeline that
    # silently converts it to green would be less trustworthy, not more.
    if by_attack["snapshot_rollback"]["native_status"] != "VULNERABLE":
        fail(f"{label}: T9 whole-state snapshot rollback finding was not preserved")


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

    if profile.get("status") != "accepted_partial_reuse":
        fail(f"qualification profile is not accepted: {profile.get('status')!r}")
    if profile.get("integration_ruling") != "partial_reuse":
        fail("agmi integration ruling must remain partial_reuse")

    validate_identity(profile, evidence, label="fresh reproduction")
    validate_rows(profile, evidence, label="fresh reproduction")

    accepted = profile.get("accepted_evidence") or {}
    committed_path = accepted.get("committed_result")
    if not committed_path:
        fail("accepted qualification must bind a committed result")
    committed = json.loads((ROOT / committed_path).read_text(encoding="utf-8"))
    validate_identity(profile, committed, label="committed accepted result")
    validate_rows(profile, committed, label="committed accepted result")

    source_workflow = committed.get("source_workflow") or {}
    for key in ("workflow_run", "artifact_id", "artifact_digest", "head_sha"):
        if not source_workflow.get(key):
            fail(f"committed accepted result is missing source_workflow.{key}")
    if source_workflow["workflow_run"] != accepted.get("workflow_run"):
        fail("accepted workflow run drifted between profile and committed result")
    if source_workflow["artifact_id"] != accepted.get("artifact_id"):
        fail("accepted artifact id drifted between profile and committed result")
    if source_workflow["artifact_digest"] != accepted.get("artifact_digest"):
        fail("accepted artifact digest drifted between profile and committed result")
    if source_workflow["head_sha"] != accepted.get("workflow_head"):
        fail("accepted workflow head drifted between profile and committed result")

    print(
        "agmi Agent Memory integrity evidence is qualified: "
        "T1-T8 safe/read-detected; T9 snapshot rollback remains VULNERABLE; "
        "accepted external row is durably bound"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
