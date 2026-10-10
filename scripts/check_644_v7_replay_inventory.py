#!/usr/bin/env python3
"""Fail-closed inventory of declared #644 v7 replay evidence.

Inventory is NOT replay execution or qualification. No PASS is inferred from
existing generic tests, documents, or unverified report filenames.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DECLARATION = ROOT / "reports/runtime/baseline-v7-declaration.json"
EVIDENCE_ROOT = ROOT / "reports/validation/644-v7-replays"


def inventory(declaration: Path = DECLARATION, evidence_root: Path = EVIDENCE_ROOT) -> dict:
    record = json.loads(declaration.read_text(encoding="utf-8"))
    if record.get("baseline_id") != "agent-memory-runtime-baseline-v7" or record.get("issue") != 644:
        raise ValueError("unexpected baseline or issue in v7 declaration")
    required = [x["ref"] for x in record.get("acceptance_evidence_required", [])
                if x.get("kind") == "replay"]
    if not required or len(required) != len(set(required)):
        raise ValueError("replay declarations missing or duplicated")
    rows = []
    for replay_id in required:
        if "/" in replay_id or ".." in replay_id or not replay_id:
            raise ValueError("unsafe replay identity")
        manifest_path = evidence_root / replay_id / "manifest.json"
        if not manifest_path.is_file():
            rows.append({"replay": replay_id, "status": "MISSING", "reason": "no replay manifest"})
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            rows.append({"replay": replay_id, "status": "INVALID", "reason": type(exc).__name__})
            continue
        # A manifest can describe evidence, but cannot independently attest
        # its origin, completeness, trusted runner, or acceptance.
        if manifest.get("replay_id") != replay_id:
            rows.append({"replay": replay_id, "status": "INVALID", "reason": "identity mismatch"})
        else:
            rows.append({"replay": replay_id, "status": "UNVERIFIED",
                         "reason": "manifest exists; independent execution and validation required"})
    return {"baseline": record["baseline_id"], "replays": rows,
            "qualification": "BLOCKED"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--declaration", type=Path, default=DECLARATION)
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE_ROOT)
    args = parser.parse_args()
    result = inventory(args.declaration, args.evidence_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    # Intentionally never green as a qualification gate.
    return 2


if __name__ == "__main__":
    sys.exit(main())
