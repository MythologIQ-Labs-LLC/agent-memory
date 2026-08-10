#!/usr/bin/env python3
"""Validate Agent Memory JSON Schemas and fixture memory units.

Requires the `jsonschema` package. This complements `validate_fixtures.py` by
checking JSON Schema correctness and validating each fixture's `memory_unit`
against the doctrine-level memory-unit schema.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("validate_schemas.py requires the 'jsonschema' package", file=sys.stderr)
    raise SystemExit(2)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    schema_dir = root / "schemas"
    fixture_dir = root / "fixtures"

    schema_errors: list[str] = []
    for path in sorted(schema_dir.glob("*.json")):
        try:
            schema = load(path)
            jsonschema.Draft202012Validator.check_schema(schema)
        except Exception as exc:
            schema_errors.append(f"{path.relative_to(root)}: {exc}")

    if schema_errors:
        print("Schema validation failed:", file=sys.stderr)
        for error in schema_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    memory_schema = load(schema_dir / "memory-unit.schema.json")
    memory_validator = jsonschema.Draft202012Validator(memory_schema)

    fixture_errors: list[str] = []
    fixture_count = 0
    for path in sorted(fixture_dir.glob("*.json")):
        fixture_count += 1
        try:
            fixture = load(path)
        except Exception as exc:
            fixture_errors.append(f"{path.relative_to(root)}: invalid JSON: {exc}")
            continue

        memory = fixture.get("memory_unit")
        if not isinstance(memory, dict):
            fixture_errors.append(f"{path.relative_to(root)}: missing object memory_unit")
            continue

        for error in sorted(memory_validator.iter_errors(memory), key=lambda e: list(e.path)):
            location = ".".join(str(part) for part in error.path)
            suffix = f" at memory_unit.{location}" if location else " at memory_unit"
            fixture_errors.append(f"{path.relative_to(root)}{suffix}: {error.message}")

    if fixture_errors:
        print("Fixture/schema validation failed:", file=sys.stderr)
        for error in fixture_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Validated {len(list(schema_dir.glob('*.json')))} schema(s) and {fixture_count} fixture memory unit(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
