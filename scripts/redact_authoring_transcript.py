#!/usr/bin/env python3
"""Redact harness session context from a #732 authoring transcript (plan-732 amendment A2).

The harness records session context as ``type:"attachment"`` lines: the user's email
(``session_context``), the system prompt (``prompt_snapshot``) and session links
(``remote_session_change``), among others. The orchestrator writes none of these, and the
author's channel audit (G1) does not depend on their content.

For every attachment line, the redaction replaces the values of ``attachment`` and ``rendered``,
when present, with ``{"type": <attachment type>, "redacted_sha256": <sha256 of the canonical JSON
of the original value>}``. Every other line is copied byte for byte. Canonical JSON means
``json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`` encoded as UTF-8.

``verify(original, redacted)`` re-derives the redaction and checks each line:

* every non-attachment line is byte-equal;
* every attachment line equals the original except for the two replaced keys;
* every hash matches.

A tribunal holding the unredacted live file can therefore confirm that the committed copy hides
nothing but harness context. The script has ``authority_effect: none``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REDACTED_KEYS = ("attachment", "rendered")


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _redact_record(record: dict) -> dict:
    atype = (record.get("attachment") or {}).get("type") if isinstance(record.get("attachment"), dict) else None
    out = dict(record)
    for key in REDACTED_KEYS:
        if key in record:
            out[key] = {"type": atype, "redacted_sha256": hashlib.sha256(canonical(record[key])).hexdigest()}
    return out


def redact_lines(lines: list[bytes]) -> list[bytes]:
    out = []
    for line in lines:
        stripped = line.rstrip(b"\n")
        if not stripped.strip():
            out.append(line)
            continue
        record = json.loads(stripped)
        if record.get("type") == "attachment":
            out.append(json.dumps(_redact_record(record), ensure_ascii=False).encode("utf-8") + b"\n")
        else:
            out.append(line)
    return out


def verify(original: bytes, redacted: bytes) -> list[str]:
    problems = []
    a, b = original.splitlines(keepends=True), redacted.splitlines(keepends=True)
    if len(a) != len(b):
        return [f"line count differs: {len(a)} vs {len(b)}"]
    for index, (x, y) in enumerate(zip(a, b)):
        if not x.strip():
            if x != y:
                problems.append(f"line {index}: blank line changed")
            continue
        record = json.loads(x)
        if record.get("type") != "attachment":
            if x != y:
                problems.append(f"line {index}: non-attachment line changed")
            continue
        if json.loads(y) != _redact_record(record):
            problems.append(f"line {index}: attachment redaction does not match the rule")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("redact")
    r.add_argument("original", type=Path)
    r.add_argument("out", type=Path)
    v = sub.add_parser("verify")
    v.add_argument("original", type=Path)
    v.add_argument("redacted", type=Path)
    args = parser.parse_args(argv)
    original = args.original.read_bytes()
    if args.command == "redact":
        redacted = b"".join(redact_lines(original.splitlines(keepends=True)))
        args.out.write_bytes(redacted)
    else:
        redacted = args.redacted.read_bytes()
    problems = verify(original, redacted)
    result = {
        "original_sha256": hashlib.sha256(original).hexdigest(),
        "redacted_sha256": hashlib.sha256(redacted).hexdigest(),
        "problems": problems,
        "verdict": "PASS" if not problems else "FAIL",
        "authority_effect": "none",
    }
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
