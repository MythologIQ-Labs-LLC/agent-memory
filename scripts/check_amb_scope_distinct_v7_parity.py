#!/usr/bin/env python3
"""Fail-closed AMB scope-distinct successor parity against the accepted v6 control.

The historical attribution checker permits ATTRIBUTED differences. This v7
successor does not: it must reproduce every frozen v6 case field AND every
cross-fact sidecar record exactly. No score or evidence is accepted here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_V6 = (
    ROOT / "reports/benchmarks/amb/amb-precisionmembench-retrieval-v6/"
    "agent-memory-24048d55e26d"
)
SUCCESSOR_LANE = (
    ROOT / "reports/validation/v7-integration/amb-scope-distinct-successor/"
    "amb-precisionmembench-retrieval-v7-scope-distinct-v1.json"
)
OLD_LANE_ID = "amb-precisionmembench-retrieval-v6"
NEW_LANE_ID = "amb-precisionmembench-retrieval-v7-scope-distinct-v1"
CASE_FIELDS = ("correct", "context")
META_FIELDS = (
    "relevant_beliefs",
    "pinned_beliefs",
    "retrieved_questions",
    "retrieval_precision",
    "retrieval_recall",
    "pinned_coverage",
    "resolution",
    "failures",
    "retrieved_count",
)
SIDECAR_FIELDS = (
    "call_index",
    "scope",
    "query_sha256",
    "budget",
    "limited_count",
    "limited_document_ids",
    "refusal_counts",
    "returned_document_ids",
    "returned_document_ids_mechanism_off",
)
HARNESS_SHA = "03c1d0f1d27da63034f0931121c858faba512383"


class ParityBlocked(RuntimeError):
    """No parity claim: a source, selection, sidecar or identity is incorrect."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ParityBlocked(f"required JSON unavailable or malformed: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ParityBlocked(f"expected a JSON object: {path}")
    return value


def _raw_git_blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + bytes([0]) + data).hexdigest()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lane_digest(lane: dict[str, Any]) -> str:
    raw = (json.dumps(lane, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ParityBlocked(message)


def _cases(summary: dict[str, Any], label: str) -> list[dict[str, Any]]:
    _require(summary.get("memory_provider") == "agent-memory" and summary.get("mode") == "retrieval",
             f"{label}: not a model-free Agent Memory retrieval control")
    items = summary.get("results")
    _require(isinstance(items, list) and len(items) == 77 and summary.get("total_queries") == 77,
             f"{label}: exactly 77 raw cases required, not a subset or an aggregate")
    ids: list[str] = []
    for item in items:
        _require(isinstance(item, dict) and isinstance(item.get("query_id"), str),
                 f"{label}: missing string query_id")
        _require(isinstance(item.get("query"), str), f"{label}: missing query text")
        _require(isinstance(item.get("meta"), dict), f"{label}: missing case metadata")
        for field in CASE_FIELDS:
            _require(field in item, f"{label}: {item['query_id']} lacks {field}")
        for field in META_FIELDS:
            _require(field in item["meta"], f"{label}: {item['query_id']} lacks meta.{field}")
        ids.append(item["query_id"])
    _require(len(set(ids)) == 77, f"{label}: duplicate query IDs")
    return items


def _sidecar(path: Path, cases: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError) as exc:
        raise ParityBlocked(f"{label}: missing or malformed cross-fact sidecar: {exc}") from exc
    asked = [case for case in cases if case["query"].strip()]
    _require(len(rows) == len(asked) == 73, f"{label}: expected 73 ordered sidecar records and four blanks")
    for index, (row, case) in enumerate(zip(rows, asked)):
        _require(isinstance(row, dict) and set(row) == set(SIDECAR_FIELDS),
                 f"{label}: cross-fact record {index} has the wrong field set")
        _require(type(row["call_index"]) is int and row["call_index"] == index,
                 f"{label}: non-contiguous call_index at {index}")
        _require(row["query_sha256"] == hashlib.sha256(case["query"].encode("utf-8")).hexdigest(),
                 f"{label}: record {index} is not bound to query {case['query_id']}")
        _require(type(row["limited_count"]) is int and row["limited_count"] >= 0,
                 f"{label}: malformed limited_count at {index}")
        _require(isinstance(row["limited_document_ids"], list)
                 and len(row["limited_document_ids"]) == row["limited_count"],
                 f"{label}: wrong limited_document_ids at {index}")
        _require(isinstance(row["refusal_counts"], dict)
                 and isinstance(row["returned_document_ids"], list),
                 f"{label}: malformed sidecar fields at {index}")
        _require((row["returned_document_ids_mechanism_off"] is None)
                 == (row["limited_count"] == 0),
                 f"{label}: mechanism-off record inconsistent at {index}")
    return rows


def verify(baseline_dir: Path, candidate_dir: Path, *, root: Path = ROOT) -> dict[str, Any]:
    """Compare already recorded artifacts; preserve every input and result byte."""
    lane = _read_json(root / SUCCESSOR_LANE.relative_to(ROOT))
    _require(lane.get("lane_id") == NEW_LANE_ID and lane.get("status") == "frozen",
             "candidate lane is not the frozen scope-distinct successor")
    blobs = lane["harness"]["source_blobs"]
    for source, expected in blobs.items():
        if source.startswith("reference/"):
            _require(_raw_git_blob(root / source) == expected, f"candidate source blob drift: {source}")

    before_evidence = _read_json(baseline_dir / "evidence.json")
    _require(before_evidence.get("lane_id") == OLD_LANE_ID,
             "baseline is not the accepted v6 control evidence")
    _require(before_evidence.get("authority_effect") == "none", "baseline evidence authority mismatch")
    before_identity = _read_json(baseline_dir / "execution-identity.json")
    after_identity = _read_json(candidate_dir / "execution-identity.json")
    _require(before_identity.get("lane_id") == OLD_LANE_ID, "v6 execution identity mismatch")
    _require(after_identity.get("lane_id") == NEW_LANE_ID, "successor execution lane mismatch")
    _require(after_identity.get("memory") == "agent-memory"
             and after_identity.get("mode") == "retrieval"
             and after_identity.get("dataset") == "precisionmembench"
             and after_identity.get("split") == "single-turn",
             "successor execution is not the full PrecisionMemBench retrieval control")
    _require(after_identity.get("amb_revision") == HARNESS_SHA
             and before_identity.get("amb_revision") == HARNESS_SHA,
             "external AMB revision changed")
    _require(after_identity.get("full_selection") is True
             and after_identity.get("query_limit") == "0"
             and after_identity.get("amb_pmb_return_cap") is None,
             "successor execution must select all 77 queries with no return cap")
    _require(after_identity.get("answer_model") is None and after_identity.get("judge_model") is None,
             "successor execution unexpectedly used a model")
    _require(after_identity.get("declaration_blob") == (
        next(item for item in lane["systems"] if item["role"] == "control")
        ["configuration"]["runtime_baseline_posture"]["declaration_blob"]
    ), "successor declaration identity mismatch")
    _require(after_identity.get("runtime_baseline_state") in ("PASS", "TRANSITION"),
             "successor runtime baseline checker did not permit this declared transition")
    _require(after_identity.get("workflow_run_id") is not None
             and isinstance(after_identity.get("agent_memory_revision"), str)
             and len(after_identity["agent_memory_revision"]) == 40,
             "successor run/revision identity is missing")
    _require(after_identity.get("lane_digest_sha256") == _lane_digest(lane),
             "successor lane digest mismatch")
    _require(after_identity.get("bridge_blobs") == {
        source: blob for source, blob in blobs.items() if source.startswith("reference/")
    }, "successor bridge or runner identity differs from the freeze")

    before = _cases(_read_json(baseline_dir / "single-turn.json"), "v6")
    after = _cases(_read_json(candidate_dir / "single-turn.json"), "successor")
    _require([row["query_id"] for row in before] == [row["query_id"] for row in after],
             "query ID order/selection changed")
    for old, new in zip(before, after):
        _require(old["query"] == new["query"], f"{old['query_id']}: query text changed")
        for field in CASE_FIELDS:
            _require(old[field] == new[field], f"{old['query_id']}: case.{field} not equal")
        for field in META_FIELDS:
            _require(old["meta"][field] == new["meta"][field],
                     f"{old['query_id']}: meta.{field} not equal")

    before_sidecar = baseline_dir / "cross-fact.jsonl"
    after_sidecar = candidate_dir / "cross-fact.jsonl"
    recorded_digest = (before_evidence.get("cross_fact_sidecar") or {}).get("sha256")
    _require(recorded_digest == _sha(before_sidecar),
             "accepted-v6 sidecar no longer matches its committed evidence digest")
    old_records = _sidecar(before_sidecar, before, "v6")
    new_records = _sidecar(after_sidecar, after, "successor")
    for old, new in zip(old_records, new_records):
        _require(old == new, f"cross-fact sidecar differs at call_index {old['call_index']}")
    _require(all(item["limited_count"] == 0 for item in new_records),
             "scope-distinct control introduced cross-fact limitations")
    return {
        "verdict": "EQUAL",
        "authority_effect": "none",
        "baseline_lane": OLD_LANE_ID,
        "candidate_lane": NEW_LANE_ID,
        "cases_equal": 77,
        "cross_fact_records_equal": 73,
        "no_recall_cases": 4,
        "limited_count": 0,
        "acceptance": "not_granted",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline-dir", type=Path, default=ACCEPTED_V6)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        report = verify(args.baseline_dir, args.candidate_dir, root=args.repo_root)
    except (ParityBlocked, KeyError, TypeError, IndexError, OSError) as exc:
        print(json.dumps({"verdict": "BLOCKED", "reason": str(exc), "authority_effect": "none"}, sort_keys=True))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
