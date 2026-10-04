#!/usr/bin/env python3
"""Compare two Gauntlet external-contestant dogfood runs for semantic equivalence.

Each Gauntlet execution intentionally receives a unique UUID-derived run id. Timing and
artifact paths/hashes derived from that execution identity are measured evidence, so
byte-identical artifacts are neither expected nor required. This checker canonicalizes
only those explicitly volatile fields, preserves request correlation sequence, and then
requires system, adapter, profile, negotiation, retrieval, coverage, and evaluator
semantics to remain identical.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

_RUN_SUFFIX = re.compile(r"^[0-9a-f]{12}$")


def _single_run(root: Path) -> dict[str, Any]:
    directories = sorted(path for path in root.iterdir() if path.is_dir())
    if len(directories) != 1:
        raise SystemExit(f"expected exactly one Gauntlet run beneath {root}, found {len(directories)}")
    run_dir = directories[0]

    def load(name: str) -> dict[str, Any]:
        with (run_dir / name).open("r", encoding="utf-8") as handle:
            return json.load(handle)

    return {
        "directory": run_dir.name,
        "manifest": load("adapter-manifest.json"),
        "native": load("native-results.json"),
        "normalized": load("normalized-run.json"),
        "qualification": load("qualification.json"),
    }


def _run_id_valid(value: str | None, qualification: dict[str, Any]) -> bool:
    if not isinstance(value, str):
        return False
    profile_id = qualification.get("profile", {}).get("profile_id")
    system_id = qualification.get("system", {}).get("id")
    if not isinstance(profile_id, str) or not isinstance(system_id, str):
        return False
    prefix = f"gauntlet-{profile_id}-{system_id}-"
    if not value.startswith(prefix):
        return False
    return bool(_RUN_SUFFIX.fullmatch(value[len(prefix) :]))


def _canonical_request_id(value: Any) -> Any:
    """Preserve request sequence while removing only the per-execution run-id prefix."""

    if not isinstance(value, str):
        return value
    prefix, separator, sequence = value.rpartition(":")
    if not separator or not prefix or not sequence.isdigit():
        return value
    return f"<execution>:{sequence}"


def _stable_native(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop("elapsed_ms", None)
    result.pop("operation_elapsed_ms_p50", None)
    transcript = result.get("transcript")
    if isinstance(transcript, list):
        for event in transcript:
            if isinstance(event, dict) and "request_id" in event:
                event["request_id"] = _canonical_request_id(event["request_id"])
    return result


def _stable_normalized(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop("run_id", None)
    execution = result.get("execution")
    if isinstance(execution, dict):
        execution.pop("started_at", None)
        execution.pop("elapsed_ms", None)
    native = result.get("native_results")
    if isinstance(native, dict):
        result["native_results"] = _stable_native(native)
    result.get("dimensions", {}).pop("efficiency", None)
    result["artifacts"] = [
        {"artifact_id": item.get("artifact_id"), "kind": item.get("kind")}
        for item in result.get("artifacts", [])
        if isinstance(item, dict)
    ]
    return result


def _stable_qualification(value: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "schema_version",
        "status",
        "system",
        "adapter",
        "profile",
        "authority_effect",
        "coverage",
        "negotiation",
        "manifest_digest_sha256",
    )
    return {key: copy.deepcopy(value.get(key)) for key in keys}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    first = _single_run(args.first)
    second = _single_run(args.second)
    first_id = first["qualification"].get("run_id")
    second_id = second["qualification"].get("run_id")

    checks = {
        "execution_ids_distinct": first_id != second_id,
        "first_execution_id_valid": _run_id_valid(first_id, first["qualification"]),
        "second_execution_id_valid": _run_id_valid(second_id, second["qualification"]),
        "manifest_equal": first["manifest"] == second["manifest"],
        "native_semantics_equal": _stable_native(first["native"]) == _stable_native(second["native"]),
        "normalized_semantics_equal": _stable_normalized(first["normalized"]) == _stable_normalized(second["normalized"]),
        "qualification_semantics_equal": _stable_qualification(first["qualification"]) == _stable_qualification(second["qualification"]),
    }
    passed = all(checks.values())
    report = {
        "schema_version": "1.0.0",
        "qualification": "gauntlet_external_contestant_semantic_replay",
        "status": "pass" if passed else "fail",
        "first_run_id": first_id,
        "second_run_id": second_id,
        "checks": checks,
        "canonicalized_as_execution_volatile": [
            "Gauntlet run_id (UUID-derived execution identity; required to differ)",
            "native-results.transcript[*].request_id run-id prefix (sequence preserved)",
            "native-results.elapsed_ms",
            "native-results.operation_elapsed_ms_p50",
            "normalized-run.run_id",
            "normalized-run.execution.started_at",
            "normalized-run.execution.elapsed_ms",
            "normalized-run.dimensions.efficiency",
            "normalized-run artifact sha256/uri values derived from timing or output root",
            "qualification run_id and artifact paths/hashes derived from execution identity/timing",
        ],
        "semantic_fields_required_equal": [
            "adapter manifest",
            "system and adapter identity/revision",
            "profile identity and provenance class",
            "capability negotiation",
            "coverage states",
            "retrieval rows and exact-top1 result",
            "fixture and manifest digests",
            "operation ordering/status/result payloads",
            "normalized non-efficiency dimensions",
            "authority effect",
        ],
        "authority_effect": "none",
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    if not passed:
        failed = [name for name, ok in checks.items() if not ok]
        raise SystemExit("Gauntlet dogfood semantic replay mismatch: " + ", ".join(failed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
