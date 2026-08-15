#!/usr/bin/env python3
"""Validate snapshot-bound Atlas research records against their local schemas."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
PROGRAM = ROOT / "docs/programs/atlas-research"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator(schema_path: Path) -> Draft202012Validator:
    return Draft202012Validator(load_json(schema_path), format_checker=FormatChecker())


def validate_jsonl(path: Path, record_validator: Draft202012Validator) -> int:
    count = 0
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        errors = sorted(record_validator.iter_errors(record), key=lambda error: list(error.path))
        if errors:
            messages = "; ".join(error.message for error in errors)
            raise SystemExit(f"{path}:{line_number}: schema validation failed: {messages}")
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inventory",
        type=Path,
        default=PROGRAM / "report-inventory.jsonl",
        help="report inventory to validate; may be a generated temporary file",
    )
    parser.add_argument(
        "--allow-missing-inventory",
        action="store_true",
        help="validate the scaffold before the first pinned inventory is committed",
    )
    args = parser.parse_args()

    manifest_path = PROGRAM / "snapshot-manifest.json"
    manifest_schema = PROGRAM / "schemas/snapshot-manifest.schema.json"
    report_schema = PROGRAM / "schemas/report-inventory-record.schema.json"
    claim_schema = PROGRAM / "schemas/claim-verification-record.schema.json"
    claim_ledger = PROGRAM / "claim-ledger.jsonl"
    dedup_path = PROGRAM / "deduplication-map.json"

    manifest_errors = sorted(
        validator(manifest_schema).iter_errors(load_json(manifest_path)),
        key=lambda error: list(error.path),
    )
    if manifest_errors:
        raise SystemExit(
            "snapshot manifest schema validation failed: "
            + "; ".join(error.message for error in manifest_errors)
        )

    claim_count = validate_jsonl(claim_ledger, validator(claim_schema))

    dedup = load_json(dedup_path)
    if dedup.get("schema_version") != "1.0.0":
        raise SystemExit("deduplication-map.json must declare schema_version 1.0.0")
    entries = dedup.get("entries")
    if not isinstance(entries, list) or not entries:
        raise SystemExit("deduplication-map.json must contain at least one entry")
    allowed_dispositions = set(dedup.get("dispositions", []))
    for index, entry in enumerate(entries):
        if entry.get("default_disposition") not in allowed_dispositions:
            raise SystemExit(
                f"deduplication-map.json entry {index} uses an undeclared disposition"
            )
        if not entry.get("agent_memory_owners"):
            raise SystemExit(
                f"deduplication-map.json entry {index} must identify an Agent Memory owner"
            )

    inventory_count = 0
    if args.inventory.exists():
        inventory_count = validate_jsonl(args.inventory, validator(report_schema))
        expected = load_json(manifest_path)["system_report_count"]["value"]
        if inventory_count != expected:
            raise SystemExit(
                f"inventory contains {inventory_count} records; expected {expected}"
            )
    elif not args.allow_missing_inventory:
        raise SystemExit(f"inventory missing: {args.inventory}")

    print(
        "atlas-research: valid "
        f"manifest=1 claims={claim_count} dedup_entries={len(entries)} "
        f"inventory={inventory_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
