from __future__ import annotations

import csv
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path

import rfc8785

from agentmem_ref.runtime.ranking_policy import admitted_set_bm25, relevance_tokens

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "runtime-kernel"
BM25_FIXTURE = FIXTURE_ROOT / "bm25-v1.tsv"
SHA256_FIXTURE = FIXTURE_ROOT / "sha256-v1.tsv"
JCS_FIXTURE = FIXTURE_ROOT / "jcs-rfc8785-v1.json"


def _bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _rows():
    with BM25_FIXTURE.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_frozen_bm25_vectors_match_python_runtime_exactly():
    grouped = defaultdict(list)
    for row in _rows():
        grouped[row["case"]].append(row)

    assert set(grouped) == {"simple", "near", "unicode"}

    for case, rows in grouped.items():
        query = rows[0]["query"]
        expected_query_tokens = rows[0]["query_tokens"].split(",")
        assert relevance_tokens(query) == expected_query_tokens, case

        texts = {row["ref"]: row["text"] for row in rows}
        scores = admitted_set_bm25(query, texts)
        assert set(scores) == set(texts)

        for row in rows:
            assert relevance_tokens(row["text"]) == row["expected_tokens"].split(","), (case, row["ref"])
            assert _bits(scores[row["ref"]]) == int(row["expected_score_bits"]), (case, row["ref"])


def test_near_tie_fixture_really_contains_an_exact_python_score_tie():
    rows = [row for row in _rows() if row["case"] == "near"]
    scores = admitted_set_bm25(rows[0]["query"], {row["ref"]: row["text"] for row in rows})
    assert _bits(scores["a"]) == _bits(scores["b"])
    assert scores["a"] > scores["c"]


def test_frozen_sha256_vectors_match_python_hashlib_exactly():
    with SHA256_FIXTURE.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rows) == 5
    for row in rows:
        actual = hashlib.sha256(row["input"].encode("utf-8")).hexdigest()
        assert actual == row["expected_sha256"], row["input"]


def test_frozen_jcs_vectors_match_python_rfc8785_exactly():
    fixture = json.loads(JCS_FIXTURE.read_text(encoding="utf-8"))
    assert fixture["profile"] == "agent-memory-rfc8785-jcs-v1"
    assert fixture["oracle"] == "python rfc8785==0.1.4"
    assert fixture["status"] == "frozen-before-rust-jcs-execution"
    assert len(fixture["cases"]) == 5

    for case in fixture["cases"]:
        canonical = rfc8785.dumps(case["value"])
        assert canonical.hex() == case["expected_utf8_hex"], case["name"]
        assert hashlib.sha256(canonical).hexdigest() == case["expected_sha256"], case["name"]
