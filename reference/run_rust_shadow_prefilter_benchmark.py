from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import struct
import time
from pathlib import Path

from agentmem_ref.state import sqlite_substrate

CONTRACT = "591_identity_first_prefilter_compute_v1"
TOPICS = (
    "deploy",
    "memory",
    "agent",
    "policy",
    "tool",
    "project",
    "user",
    "current",
    "history",
    "graph",
)
QUERIES = (
    "deploy memory project",
    "agent policy current",
    "tool user project 7",
    "history graph item 42",
    "memory memory agent",
    "current project 17",
    "unrelated missing",
    "deploy, graph!",
)


def build_rows(count: int) -> list[tuple[str, bool, bool, str]]:
    rows = []
    for index in range(count):
        first = TOPICS[index % len(TOPICS)]
        second = TOPICS[(index * 3 + 1) % len(TOPICS)]
        rows.append(
            (
                f"ref-{index:06d}",
                index % 5 != 0,
                index % 7 != 0,
                f"The {first} {second} item {index % 97} belongs to project {index % 41}.",
            )
        )
    return rows


def prefilter(query: str, rows: list[tuple[str, bool, bool, str]]) -> list[tuple[str, float]]:
    terms = sqlite_substrate._tokens(query)
    denominator = max(len(terms), 1)
    survivors: list[tuple[str, float]] = []
    for uuid, group_selected, identity_eligible, fact_text in rows:
        if not group_selected or not identity_eligible:
            continue
        overlap = terms & sqlite_substrate._tokens(fact_text)
        if not overlap:
            continue
        survivors.append((uuid, len(overlap) / denominator))
    survivors.sort(key=lambda pair: (-pair[1], pair[0]))
    return survivors


def score_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def signature(rows: list[tuple[str, bool, bool, str]]) -> str:
    digest = hashlib.sha256()
    for query_index, query in enumerate(QUERIES):
        for uuid, score in prefilter(query, rows):
            digest.update(f"{query_index}|{uuid}|{score_bits(score)}\n".encode("utf-8"))
    return digest.hexdigest()


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    rank = max(1, int((len(ordered) * percentile) + 0.999999999))
    return ordered[min(rank - 1, len(ordered) - 1)]


def run(count: int, iterations: int) -> dict:
    rows = build_rows(count)
    expected_signature = signature(rows)

    # Warm every query before collecting timing evidence.
    checksum = 0
    for query in QUERIES:
        result = prefilter(query, rows)
        checksum ^= len(result)
        if result:
            checksum ^= score_bits(result[0][1]) & 0xFFFF

    samples_ms: list[float] = []
    started = time.perf_counter_ns()
    for _ in range(iterations):
        for query in QUERIES:
            query_started = time.perf_counter_ns()
            result = prefilter(query, rows)
            samples_ms.append((time.perf_counter_ns() - query_started) / 1_000_000)
            checksum ^= len(result)
            if result:
                checksum ^= score_bits(result[0][1]) & 0xFFFF
    elapsed_ns = time.perf_counter_ns() - started
    elapsed_seconds = elapsed_ns / 1_000_000_000
    examined = count * len(QUERIES) * iterations

    return {
        "schema_version": 1,
        "contract": CONTRACT,
        "implementation": "python",
        "rows": count,
        "queries": len(QUERIES),
        "iterations": iterations,
        "sample_count": len(samples_ms),
        "result_signature_sha256": expected_signature,
        "total_ms": elapsed_ns / 1_000_000,
        "p50_query_ms": statistics.median(samples_ms),
        "p95_query_ms": percentile_nearest_rank(samples_ms, 0.95),
        "projected_rows_examined_per_second": examined / elapsed_seconds if elapsed_seconds else 0.0,
        "checksum": checksum,
        "timing_scope": "prefilter_compute_only_rows_prebuilt",
        "authority_effect": "none",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=20_000)
    parser.add_argument("--iterations", type=int, default=8)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.rows <= 0 or args.iterations <= 0:
        raise SystemExit("rows and iterations must be positive")
    payload = run(args.rows, args.iterations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
