#!/usr/bin/env python3
"""Compare two Gauntlet external-contestant dogfood runs for semantic equivalence.

Timing is measured evidence, so byte-identical artifacts are neither expected nor required.
This checker removes only explicitly volatile timing/hash/path fields, then requires the
system, adapter, profile, negotiation, retrieval result, coverage, and evidence semantics
to remain identical.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any


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


def _stable_native(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result.pop("elapsed_ms", None)
    result.pop("operation_elapsed_ms_p50", None)
    return result


def _stable_normalized(value: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(value)
    result["native_results"] = _stable_native(result["native_results"])
    result.get("dimensions", {}).pop("efficiency", None)
    result["artifacts"] = [
        {"artifact_id": item.get("artifact_id"), "kind": item.get("kind")}
        for item in result.get("artifacts", [])
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
        "run_id",
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

    checks = {
        "run_id_equal": first["qualification"].get("run_id") == second["qualification"].get("run_id"),
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
        "first_run_id": first["qualification"].get("run_id"),
        "second_run_id": second["qualification"].get("run_id"),
        "checks": checks,
        "ignored_as_volatile": [
            "native-results.elapsed_ms",
            "native-results.operation_elapsed_ms_p50",
            "normalized-run.dimensions.efficiency",
            "normalized-run artifact sha256/uri values derived from timing or output root",
            "qualification artifact paths/hashes derived from timing or output root",
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
