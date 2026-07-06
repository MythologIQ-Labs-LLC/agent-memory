#!/usr/bin/env python3
"""Validate agent-memory conformance fixtures.

This script intentionally uses only the Python standard library so the repo can
run basic fixture validation without dependency ceremony, because even schemas
deserve fewer excuses.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = {
    "fixture_id",
    "class",
    "description",
    "expected_behavior",
    "memory_unit",
}

REQUIRED_MEMORY_UNIT = {
    "id",
    "type",
    "state",
    "provenance",
    "evidence",
    "saturation",
    "authority",
    "created_at",
}

REQUIRED_PROVENANCE = {"origin", "observer", "method", "timestamp"}
REQUIRED_SATURATION = {"sigma", "calibrated", "durability_dimensions"}
REQUIRED_AUTHORITY = {"pama_outcome", "risk_class"}

VALID_STATES = {
    "transient",
    "observed",
    "linked",
    "reinforced",
    "candidate",
    "pending_verification",
    "crystallized",
    "operationally_reused",
    "stale",
    "disputed",
    "corrected",
    "reconciled",
    "pruned",
}

VALID_PAMA_OUTCOMES = {
    "allow",
    "allow_with_ledger",
    "require_review",
    "require_external_verification",
    "block",
}

VALID_RISK_CLASSES = {"low", "medium", "high", "critical"}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def require_keys(obj: dict[str, Any], keys: set[str], path: str) -> list[str]:
    return [f"{path}: missing required key '{key}'" for key in sorted(keys - obj.keys())]


def validate_fixture(path: Path) -> list[str]:
    errors: list[str] = []
    data = load_json(path)

    if not isinstance(data, dict):
        return [f"{path}: fixture must be a JSON object"]

    errors.extend(require_keys(data, REQUIRED_TOP_LEVEL, str(path)))
    if errors:
        return errors

    memory = data["memory_unit"]
    if not isinstance(memory, dict):
        return [f"{path}: memory_unit must be an object"]

    errors.extend(require_keys(memory, REQUIRED_MEMORY_UNIT, f"{path}:memory_unit"))

    state = memory.get("state")
    if state not in VALID_STATES:
        errors.append(f"{path}:memory_unit.state invalid: {state!r}")

    provenance = memory.get("provenance")
    if not isinstance(provenance, dict):
        errors.append(f"{path}:memory_unit.provenance must be an object")
    else:
        errors.extend(require_keys(provenance, REQUIRED_PROVENANCE, f"{path}:memory_unit.provenance"))

    evidence = memory.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{path}:memory_unit.evidence must be a non-empty list")
    else:
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                errors.append(f"{path}:memory_unit.evidence[{index}] must be an object")
                continue
            for key in ("id", "kind", "ref", "confidence"):
                if key not in item:
                    errors.append(f"{path}:memory_unit.evidence[{index}] missing {key!r}")
            confidence = item.get("confidence")
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                errors.append(f"{path}:memory_unit.evidence[{index}].confidence must be 0..1")

    saturation = memory.get("saturation")
    if not isinstance(saturation, dict):
        errors.append(f"{path}:memory_unit.saturation must be an object")
    else:
        errors.extend(require_keys(saturation, REQUIRED_SATURATION, f"{path}:memory_unit.saturation"))
        sigma = saturation.get("sigma")
        if not isinstance(sigma, (int, float)) or not 0 <= sigma <= 1:
            errors.append(f"{path}:memory_unit.saturation.sigma must be 0..1")
        dims = saturation.get("durability_dimensions")
        if not isinstance(dims, list) or not dims:
            errors.append(f"{path}:memory_unit.saturation.durability_dimensions must be a non-empty list")

    authority = memory.get("authority")
    if not isinstance(authority, dict):
        errors.append(f"{path}:memory_unit.authority must be an object")
    else:
        errors.extend(require_keys(authority, REQUIRED_AUTHORITY, f"{path}:memory_unit.authority"))
        outcome = authority.get("pama_outcome")
        if outcome not in VALID_PAMA_OUTCOMES:
            errors.append(f"{path}:memory_unit.authority.pama_outcome invalid: {outcome!r}")
        risk = authority.get("risk_class")
        if risk not in VALID_RISK_CLASSES:
            errors.append(f"{path}:memory_unit.authority.risk_class invalid: {risk!r}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate conformance fixture JSON files.")
    parser.add_argument("paths", nargs="*", default=["fixtures"], help="Fixture files or directories to validate.")
    args = parser.parse_args()

    files: list[Path] = []
    for raw in args.paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.glob("*.json")))
        else:
            files.append(path)

    if not files:
        print("No fixture files found.", file=sys.stderr)
        return 1

    all_errors: list[str] = []
    for file_path in files:
        try:
            all_errors.extend(validate_fixture(file_path))
        except Exception as exc:  # intentionally broad for CLI diagnostics
            all_errors.append(f"{file_path}: {exc}")

    if all_errors:
        print("Fixture validation failed:", file=sys.stderr)
        for error in all_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(files)} fixture(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
