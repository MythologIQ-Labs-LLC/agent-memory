#!/usr/bin/env python3
"""Run the pinned agmi Agent Memory integrity row and preserve raw evidence."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import platform
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from agmi.adapters.agent_memory import AgentMemoryAdapter
from agmi.attacks.at_rest import AT_REST_ATTACKS_WITH_SNAPSHOT

ROOT = Path(__file__).resolve().parents[1]


def git_revision(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def agmi_root() -> Path:
    import agmi

    return Path(agmi.__file__).resolve().parents[1]


def classify(result) -> tuple[str, str]:
    if result.guard is not None or result.error is not None:
        return "blocked", "insufficient"
    if result.detected:
        return "pass", "sufficient"
    return "fail", "sufficient"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        default="reports/gauntlet/agmi-agent-memory-v1/qualification.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    profile_path = ROOT / args.profile
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    adapter = AgentMemoryAdapter()
    rows = []

    for attack_type in AT_REST_ATTACKS_WITH_SNAPSHOT:
        attack = attack_type()
        result = attack.run(adapter)
        behavioral_outcome, evidence_qualification = classify(result)
        row = asdict(result)
        row.update(
            {
                "native_status": result.status,
                "behavioral_outcome": behavioral_outcome,
                "evidence_qualification": evidence_qualification,
                "detection_point": adapter.detection_point,
            }
        )
        rows.append(row)

    output = {
        "schema_version": 1,
        "qualification_id": profile["qualification_id"],
        "authority_effect": "none",
        "evidence_class": profile["external_evidence_class"],
        "agmi": {
            "repository": profile["agmi"]["repository"],
            "revision": git_revision(agmi_root()),
            "package": profile["agmi"]["package"],
            "version": metadata.version(profile["agmi"]["package"]),
            "attack_set": profile["agmi"]["attack_set"],
            "adapter": "AgentMemoryAdapter",
            "detection_point": adapter.detection_point,
        },
        "agent_memory": {
            "checkout_revision": git_revision(ROOT),
            "runtime_baseline_revision": profile["agent_memory"]["runtime_baseline_revision"],
            "runtime_baseline_merge": profile["agent_memory"]["runtime_baseline_merge"],
            "package": profile["agent_memory"]["package"],
            "version": metadata.version(profile["agent_memory"]["package"]),
            "runtime_profile": profile["agent_memory"]["runtime_profile"],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "implementation": platform.python_implementation(),
        },
        "results": rows,
    }

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
