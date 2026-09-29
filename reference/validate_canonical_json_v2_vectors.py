from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

REQUIRED_IDS = {
    "object-codepoint-key-order",
    "int-2p53-plus1",
    "float-pos-zero",
    "float-neg-zero",
    "float-1e-6",
    "float-1e-7",
    "float-1e20",
    "float-1e21",
    "float-min-subnormal",
    "float-max-finite",
    "float-2p53",
    "float-nan",
    "float-pos-infinity",
    "float-neg-infinity",
    "invalid-lone-surrogate",
    "invalid-non-string-object-key",
    "invalid-duplicate-object-key",
}


def _binary64(bits: str) -> float:
    if len(bits) != 16:
        raise ValueError(f"binary64 hex must be 16 nybbles: {bits!r}")
    return struct.unpack(">d", bytes.fromhex(bits))[0]


def validate(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if payload.get("fixture_id") != "agent-memory-canonical-json-v2-vectors-v1":
        raise ValueError("unexpected fixture id")
    if payload.get("status") != "DRAFT_FROZEN_CANDIDATE_NOT_YET_ACCEPTED":
        raise ValueError("fixture status must remain draft before maintainer ruling")

    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("fixture cases must be a non-empty list")

    ids = [str(case.get("id")) for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("fixture case ids must be unique")
    missing = sorted(REQUIRED_IDS.difference(ids))
    if missing:
        raise ValueError(f"required edge cases missing: {missing}")

    index = {str(case["id"]): case for case in cases}
    for case in cases:
        has_bytes = "expected_utf8" in case
        has_refusal = "expected_refusal" in case
        if has_bytes == has_refusal:
            raise ValueError(f"{case['id']}: require exactly one expected result form")
        if has_bytes:
            str(case["expected_utf8"]).encode("utf-8")

        input_value = case.get("input", {})
        if isinstance(input_value, dict) and input_value.get("kind") == "binary64_bits":
            value = _binary64(str(input_value["hex"]))
            if case["category"] == "invalid_binary64":
                if math.isfinite(value):
                    raise ValueError(f"{case['id']}: invalid binary64 vector is finite")
                if case.get("expected_refusal") != "non_finite_binary64":
                    raise ValueError(f"{case['id']}: invalid binary64 refusal changed")
            elif not math.isfinite(value):
                raise ValueError(f"{case['id']}: finite binary64 vector is non-finite")

    distinctions = (
        ("int-zero", "float-pos-zero"),
        ("float-pos-zero", "float-neg-zero"),
        ("int-one", "float-one"),
        ("int-2p53", "float-2p53"),
    )
    for left, right in distinctions:
        if index[left].get("expected_utf8") == index[right].get("expected_utf8"):
            raise ValueError(f"type/sign distinction collapsed: {left} == {right}")

    if index["object-codepoint-key-order"].get("expected_utf8") != '{"":1,"𐀀":2}':
        raise ValueError("code-point key-order vector changed")

    return {
        "fixture_id": payload["fixture_id"],
        "status": payload["status"],
        "case_count": len(cases),
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "finite_binary64_cases": sum(1 for case in cases if case.get("category") == "binary64"),
        "refusal_cases": sum(1 for case in cases if "expected_refusal" in case),
        "authority_effect": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("reference/fixtures/runtime/canonical-json-v2-vectors-v1.json"),
    )
    args = parser.parse_args()
    print(json.dumps(validate(args.path), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
