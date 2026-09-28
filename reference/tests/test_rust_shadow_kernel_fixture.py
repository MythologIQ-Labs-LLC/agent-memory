from __future__ import annotations

import csv
import struct
from collections import defaultdict
from pathlib import Path

from agentmem_ref.runtime.ranking_policy import admitted_set_bm25, relevance_tokens

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "runtime-kernel" / "bm25-v1.tsv"


def _bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _rows():
    with FIXTURE.open("r", encoding="utf-8", newline="") as handle:
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
