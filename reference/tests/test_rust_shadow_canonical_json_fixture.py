from __future__ import annotations

import base64
import csv
import hashlib
import json
from pathlib import Path

from agentmem_ref.state.sqlite_substrate import _canonical_bytes

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "runtime-kernel"
    / "canonical-json-nonfloat-v1.tsv"
)


def _contains_float(value: object) -> bool:
    if isinstance(value, float):
        return True
    if isinstance(value, list):
        return any(_contains_float(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_float(item) for item in value.values())
    return False


def test_frozen_nonfloat_canonical_json_vectors_match_runtime_exactly():
    with FIXTURE.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    assert [row["case"] for row in rows] == [
        "scalars",
        "unicode",
        "nested",
        "escaping",
        "ints",
    ]

    for row in rows:
        source = base64.b64decode(row["source_json_b64"]).decode("utf-8")
        value = json.loads(source)
        assert not _contains_float(value), row["case"]

        actual = _canonical_bytes(value)
        expected = row["expected_canonical"].encode("utf-8")
        assert actual == expected, row["case"]
        assert hashlib.sha256(actual).hexdigest() == row["expected_sha256"], row["case"]
