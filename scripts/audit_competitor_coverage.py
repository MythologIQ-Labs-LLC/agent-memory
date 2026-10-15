#!/usr/bin/env python3
"""Read-only count of accepted external memory competitors.

Consumes the canonical dashboard, not upstream publications, wishlist entries,
unqualified adapters or the GitHub Pages frontend. Never estimates a missing score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

METRICS = (
    "mean_precision", "mean_recall", "recall_all@5", "recall_all@10",
    "ndcg_any@5", "ndcg_any@10", "knowledge_update_recall_all@5",
    "latest_gold_ranked_first",
)


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def stable_system_id(system: str) -> str:
    return system.strip().lower().replace("_", "-")


def coverage_report(dashboard: dict, source_blob: str, goal: int = 6) -> dict:
    if goal < 1:
        raise ValueError("external product goal must be positive")
    if dashboard.get("authority_effect") != "none":
        raise ValueError("dashboard authority effect is not none")
    lanes = dashboard.get("competitive_evidence", {}).get("frozen_lanes")
    if not isinstance(lanes, list):
        raise ValueError("missing canonical frozen lane list")

    profiles = []
    distinct_external = set()
    families = set()
    metric_contexts = 0
    for lane in lanes:
        if lane.get("status") != "accepted":
            continue
        lane_id = lane.get("lane_id")
        if not isinstance(lane_id, str) or not lane_id:
            raise ValueError("accepted lane has no ID")
        if not lane.get("input_sha256") or not lane.get("harness_revision"):
            raise ValueError("accepted lane missing frozen identity")
        plane_rows = {}
        for row in lane.get("accepted_rows", []):
            system = row.get("provider")
            role = row.get("role")
            if not isinstance(system, str) or role not in ("control", "baseline", "comparator"):
                raise ValueError("invalid accepted row identity")
            if not row.get("system_revision") or not row.get("evidence"):
                raise ValueError("accepted row missing source and run evidence")
            if not isinstance(row.get("native"), dict):
                raise ValueError("accepted row missing native metrics")
            plane_rows.setdefault(row.get("plane") or "single-turn", []).append(row)
        for plane, rows in sorted(plane_rows.items()):
            controls = [r for r in rows if r["role"] == "control"]
            if len(controls) != 1:
                raise ValueError("accepted comparison plane must have one control")
            peers = [r for r in rows if r["role"] == "comparator"]
            baselines = [r for r in rows if r["role"] == "baseline"]
            external = sorted({stable_system_id(r["provider"]) for r in peers})
            family = lane_id.split("-", 1)[0]
            families.add(family)
            contexts = []
            for metric in METRICS:
                measured = [r for r in [controls[0], *peers]
                            if type(r["native"].get(metric)) in (int, float)]
                if len(measured) < 2 or measured[0] is not controls[0]:
                    continue
                if any(not math.isfinite(r["native"][metric]) or not 0 <= r["native"][metric] <= 1
                       for r in measured):
                    raise ValueError("accepted native fractional metric outside [0,1]")
                contexts.append({
                    "metric": metric,
                    "external_systems_measured": sorted({
                        stable_system_id(r["provider"]) for r in measured if r["role"] == "comparator"
                    }),
                })
            measured_external = sorted({name for context in contexts
                                        for name in context["external_systems_measured"]})
            distinct_external.update(measured_external)
            metric_contexts += len(contexts)
            profiles.append({
                "profile_id": lane_id + (":" + plane if plane != "single-turn" else ""),
                "lane_id": lane_id,
                "plane": plane,
                "family": family,
                "accepted_on": lane.get("accepted_on"),
                "input_sha256": lane["input_sha256"],
                "harness_revision": lane["harness_revision"],
                "accepted_comparator_rows": external,
                "measured_external_products": measured_external,
                "baseline_controls": sorted({stable_system_id(r["provider"]) for r in baselines}),
                "comparable_metric_contexts": contexts,
                "unmeasured_candidates_are_not_rows": True,
            })

    return {
        "schema_version": 1,
        "kind": "competitor_coverage_audit_not_score",
        "authority_effect": "none",
        "dashboard": {
            "git_blob": source_blob,
            "as_of": dashboard.get("as_of"),
            "source": "reports/benchmarks/dashboard/current.json",
        },
        "minimum_external_product_target": goal,
        "accepted_distinct_external_products": sorted(distinct_external),
        "accepted_external_product_count": len(distinct_external),
        "external_product_gap": max(0, goal - len(distinct_external)),
        "accepted_benchmark_families": sorted(families),
        "accepted_profile_planes": len(profiles),
        "comparable_native_metric_contexts": metric_contexts,
        "profiles": profiles,
        "reading_rules": [
            "external products are distinct normalized comparator IDs, not baselines or the Agent Memory control",
            "only accepted_rows from accepted frozen lanes count; deferred and not_run systems have no numeric score",
            "multiple profile planes and metrics do not create additional distinct competitors",
            "benchmark families and native metrics are not a universal memory score",
            "raw evidence and independent review, not this projection, determine comparability",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard", type=Path, default=Path("reports/benchmarks/dashboard/current.json"))
    parser.add_argument("--out", type=Path, default=Path("reports/benchmarks/competitor-coverage/current.json"))
    parser.add_argument("--check", action="store_true", help="Reject stale committed coverage output")
    parser.add_argument("--goal", type=int, default=6)
    args = parser.parse_args()
    try:
        content = args.dashboard.read_bytes()
        report = coverage_report(json.loads(content), git_blob_sha(content), goal=args.goal)
        expected = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.check:
            if args.out.read_text(encoding="utf-8") != expected:
                raise ValueError("stale competitor-coverage projection")
            print("PASS: competitor cohort coverage matches canonical evidence")
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(expected, encoding="utf-8")
            print("Wrote source-pinned competitor cohort coverage:", args.out)
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("BLOCKED:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
