from __future__ import annotations

import csv
import struct
from collections import defaultdict
from pathlib import Path

from agentmem_ref.state import sqlite_substrate

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "runtime-kernel"
    / "candidate-prefilter-v1.tsv"
)


def _bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def test_frozen_candidate_prefilter_vectors_match_python_runtime_semantics():
    with FIXTURE.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["case"]].append(row)

    assert set(grouped) == {"domain", "tie", "punctuation", "empty", "set-query"}

    for case, case_rows in grouped.items():
        terms = sqlite_substrate._tokens(case_rows[0]["query"])
        survivors: list[tuple[str, float]] = []
        for row in case_rows:
            if row["group_selected"] != "1" or row["identity_eligible"] != "1":
                continue
            overlap = terms & sqlite_substrate._tokens(row["fact_text"])
            if not overlap:
                continue
            survivors.append((row["uuid"], len(overlap) / max(len(terms), 1)))

        survivors.sort(key=lambda pair: (-pair[1], pair[0]))
        expected = sorted(
            (
                (row["uuid"], int(row["expected_score_bits"]), int(row["expected_rank"]))
                for row in case_rows
                if row["expected_rank"]
            ),
            key=lambda item: item[2],
        )

        assert [uuid for uuid, _ in survivors] == [uuid for uuid, _, _ in expected], case
        assert [_bits(score) for _, score in survivors] == [bits for _, bits, _ in expected], case
