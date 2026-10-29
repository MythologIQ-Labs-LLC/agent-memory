#!/usr/bin/env python3
"""Separate immutable BM25 parity gate for AMB v7 scope-distinct successor.

The original -v7 lane requires exact BM25 parity with accepted v6; its frozen
successor accidentally omitted that explicit acceptance rule. Because the
successor has already been scored, DO NOT change the frozen lane to repair
the omission. This independent checker is a post-execution release gate only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import check_amb_scope_distinct_v7_parity as control  # noqa: E402

ROOT = SCRIPTS.parent
BASELINE = ROOT / "reports/benchmarks/amb/amb-precisionmembench-retrieval-v6/bm25-24048d55e26d"
BASELINE_EVIDENCE_BLOB = "3ad46579237f683526fab9eabc622790ed3ff67d"
BM25_ROW = "bm25-harness-baseline"
# Only these exact fields at their documented positions are non-authoritative.
# A similarly named nested field is not silently ignored.
SUMMARY_VOLATILE = frozenset({"run_name", "avg_retrieve_time_ms", "ingestion_time_ms"})
CASE_VOLATILE = frozenset({"retrieve_time_ms"})


def compare_strict(a: object, b: object, path: str = "summary") -> None:
    """Identity- and type-sensitive equality, with only pinned timing exclusions."""
    if type(a) is not type(b):
        raise control.ParityBlocked(f"{path}: type changed")
    if isinstance(a, dict):
        ignore = (SUMMARY_VOLATILE if path == "summary" else
                  CASE_VOLATILE if path.startswith("summary.results[") and path.endswith("]") else
                  frozenset())
        old = {k for k in a if k not in ignore}
        new = {k for k in b if k not in ignore}
        if old != new:
            raise control.ParityBlocked(f"{path}: keys changed")
        for name in sorted(old):
            compare_strict(a[name], b[name], f"{path}.{name}")
    elif isinstance(a, list):
        if len(a) != len(b):
            raise control.ParityBlocked(f"{path}: length changed")
        for i, (left, right) in enumerate(zip(a, b)):
            compare_strict(left, right, f"{path}[{i}]")
    elif a != b:
        raise control.ParityBlocked(f"{path}: value changed")


def verify(baseline_dir: Path, candidate_dir: Path, *, root: Path = ROOT) -> dict:
    lane = control._read_json(root / control.SUCCESSOR_LANE.relative_to(control.ROOT))
    control._require(lane["lane_id"] == control.NEW_LANE_ID
                     and control._lane_digest(lane) == control.SUCCESSOR_LANE_DIGEST,
                     "BM25 successor lane freeze drift")
    for source, blob in lane["harness"]["source_blobs"].items():
        if source.startswith("reference/"):
            control._require(control._raw_git_blob(root / source) == blob,
                             f"BM25 successor pinned source drift: {source}")

    control._require(control._raw_git_blob(baseline_dir / "evidence.json") == BASELINE_EVIDENCE_BLOB,
                     "accepted BM25 v6 evidence blob drift")
    old_record = control._read_json(baseline_dir / "evidence.json")
    new_record = control._read_json(candidate_dir / "evidence.json")
    for name, rec, root_dir, lane_id in (
        ("v6", old_record, baseline_dir, control.OLD_LANE_ID),
        ("successor", new_record, candidate_dir, control.NEW_LANE_ID),
    ):
        row = rec.get("row")
        control._require(rec.get("lane_id") == lane_id and rec.get("authority_effect") == "none"
                         and isinstance(row, dict) and row.get("row_id") == BM25_ROW
                         and row.get("provider_key") == "bm25",
                         f"{name}: BM25 imported evidence identity mismatch")
        digests = rec.get("files")
        control._require(isinstance(digests, dict), f"{name}: file digest map missing")
        for filename in ("single-turn.json", "execution-identity.json"):
            control._require(digests.get(filename) == control._sha(root_dir / filename),
                             f"{name}: {filename} digest mismatch")

    before_id = control._read_json(baseline_dir / "execution-identity.json")
    after_id = control._read_json(candidate_dir / "execution-identity.json")
    control._require(before_id.get("amb_revision") == control.HARNESS_SHA
                     and after_id.get("amb_revision") == control.HARNESS_SHA,
                     "BM25 external harness pin differs")
    control._require(after_id.get("lane_id") == control.NEW_LANE_ID
                     and after_id.get("memory") == "bm25"
                     and after_id.get("mode") == "retrieval"
                     and after_id.get("dataset") == "precisionmembench"
                     and after_id.get("split") == "single-turn"
                     and after_id.get("full_selection") is True
                     and after_id.get("query_limit") == "0"
                     and after_id.get("amb_pmb_return_cap") is None
                     and after_id.get("answer_model") is None
                     and after_id.get("judge_model") is None,
                     "BM25 successor execution identity mismatch")
    control._require(after_id.get("lane_digest_sha256") == control.SUCCESSOR_LANE_DIGEST
                     and new_record.get("lane_digest_at_execution") == control.SUCCESSOR_LANE_DIGEST,
                     "BM25 successor lane execution digest mismatch")
    control._require(after_id.get("bridge_blobs") == {
        source: blob for source, blob in lane["harness"]["source_blobs"].items()
        if source.startswith("reference/")
    }, "BM25 successor bridge/runner blobs mismatch")
    control._require(new_record.get("execution") == after_id
                     and str((new_record.get("workflow_run") or {}).get("id"))
                         == str(after_id.get("workflow_run_id")),
                     "BM25 importer / run identity mismatch")
    control._require(after_id.get("declaration_blob") == (
        next(row for row in lane["systems"] if row["role"] == "control")
        ["configuration"]["runtime_baseline_posture"]["declaration_blob"]
    ), "BM25 declaration identity mismatch")
    control._require(after_id.get("runtime_baseline_state") in ("PASS", "TRANSITION"),
                     "BM25 runtime checker refused the successor")
    control._require(control._runtime_tree(root, after_id["agent_memory_revision"]) == control.RUNTIME_TREE,
                     "BM25 execution not bound to the frozen runtime tree")

    old = control._read_json(baseline_dir / "single-turn.json")
    new = control._read_json(candidate_dir / "single-turn.json")
    control._require(old.get("memory_provider") == "bm25"
                     and new.get("memory_provider") == "bm25"
                     and old.get("total_queries") == new.get("total_queries") == 77
                     and len(old.get("results", [])) == len(new.get("results", [])) == 77,
                     "BM25 77-case control is incomplete")
    compare_strict(old, new)
    control._require(any(old.get(field) != new.get(field) for field in SUMMARY_VOLATILE
                         if field != "run_name"),
                     "BM25 successor timings are identical to v6; check genuine re-execution")
    return {
        "verdict": "EQUAL", "authority_effect": "none",
        "baseline_lane": control.OLD_LANE_ID,
        "candidate_lane": control.NEW_LANE_ID,
        "row": BM25_ROW, "cases_equal": 77, "acceptance": "not_granted",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE)
    parser.add_argument("--candidate-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = verify(args.baseline_dir, args.candidate_dir, root=args.repo_root)
    except (control.ParityBlocked, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"verdict": "BLOCKED", "reason": str(exc),
                          "authority_effect": "none"}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
