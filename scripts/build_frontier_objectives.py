#!/usr/bin/env python3
"""Read-only best-in-class frontier obligations from accepted repository evidence.

Do not conflate benchmark families, metric definitions, system populations,
published references, unavailable evidence, adequacy or runtime authority.
Nothing in this file selects runtime tuning constants or mutates the ledger.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
OBJECTIVES = Path("data/benchmark-frontier-objectives.json")
DEFICITS = Path("reports/benchmarks/deficits/current.json")
DASHBOARD = Path("reports/benchmarks/dashboard/current.json")

_GROUPS = tuple("ABCDEFGHI")
_SOURCE_KINDS = frozenset({"ledger", "ledger_family", "external_only",
                            "native_gap", "blocked", "not_run"})
_UNMEASURED = frozenset({"not_run", "blocked_credential", "blocked_provenance",
                          "blocked_external", "evidence_gap", "needs_comparison"})
_RANK_STATES = frozenset({"ahead_of_observed_peer", "behind_observed_peer",
                           "tied_with_observed_peer", "self_frontier_only",
                           "no_comparable_numeric_peer"})


class FrontierEvidenceError(ValueError):
    """Object identity, comparability or coverage invariants were violated."""


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict:
        raise FrontierEvidenceError(f"{path}: expected JSON object")
    return data


def _number(value: object) -> bool:
    return type(value) in (int, float)


def observed_peer_position(row: Mapping[str, Any]) -> str:
    """Relative to one reproduced frontier, NOT a global rank or adequacy."""
    comparator = row.get("same_harness_frontier")
    if not isinstance(comparator, dict) or not str(
        row.get("evidence_class", "")
    ).startswith("same_harness"):
        return "no_comparable_numeric_peer"
    system = comparator.get("system")
    if isinstance(system, str) and system.strip().lower().replace("_", " ").startswith(
        "agent memory"
    ):
        return "self_frontier_only"
    current = row.get("agent_memory")
    peer = comparator.get("value")
    direction = row.get("direction")
    if not (_number(current) and _number(peer) and direction in ("higher", "lower")):
        return "no_comparable_numeric_peer"
    if current == peer:
        return "tied_with_observed_peer"
    advantage = current > peer if direction == "higher" else current < peer
    return "ahead_of_observed_peer" if advantage else "behind_observed_peer"


def validate_inputs(config: Mapping[str, Any], ledger: Mapping[str, Any]) -> None:
    if config.get("schema_version") != "1.0.0":
        raise FrontierEvidenceError("unsupported objective schema version")
    groups = config.get("capability_groups")
    if type(groups) is not dict or tuple(sorted(groups)) != _GROUPS:
        raise FrontierEvidenceError("all nine Coverage Atlas capability families are mandatory")
    policy = config.get("claims_policy")
    if (type(policy) is not dict or policy.get("universal_score", "absent") is not None
            or policy.get("authority_effect") != "none"
            or not all(policy.get(key) is True for key in (
                "same_harness_ranking_only", "benchmark_winning_not_adequacy",
                "published_not_comparable", "blocked_not_zero",
            ))):
        raise FrontierEvidenceError("missing frontier/safety distinction")
    items = config.get("objectives")
    deficits = ledger.get("deficits")
    if type(items) is not list or type(deficits) is not list:
        raise FrontierEvidenceError("objectives and deficits must be lists")
    seen: set[str] = set()
    for item in items:
        if type(item) is not dict:
            raise FrontierEvidenceError("noncanonical objective")
        id_ = item.get("id")
        group = item.get("group")
        source = item.get("source_kind")
        if (type(id_) is not str or len(id_) != 3 or id_[0] != group
                or id_ in seen or group not in groups
                or source not in _SOURCE_KINDS):
            raise FrontierEvidenceError("duplicate/invalid objective id, group or source")
        seen.add(id_)
        if (type(item.get("owners")) is not list
                or not item["owners"]
                or any(type(owner) is not int or owner < 1 for owner in item["owners"])):
            raise FrontierEvidenceError(f"{id_}: must name accountable issue owners")
        for field in ("capability", "benchmark", "metric", "architecture", "release_gate"):
            if type(item.get(field)) is not str or not item[field].strip():
                raise FrontierEvidenceError(f"{id_}: missing {field}")
        if source in ("ledger", "ledger_family"):
            if type(item.get("deficit_selector")) is not str:
                raise FrontierEvidenceError(f"{id_}: missing ledger selector")
            if "unmeasured_state" in item:
                raise FrontierEvidenceError(f"{id_}: ledger metric cannot be unmeasured")
        elif item.get("unmeasured_state") not in _UNMEASURED:
            raise FrontierEvidenceError(f"{id_}: unmeasured state cannot become zero")
    if not items:
        raise FrontierEvidenceError("no frontier objectives")
    raw_ids = [row.get("deficit_id") for row in deficits if type(row) is dict]
    if len(raw_ids) != len(set(raw_ids)) or any(type(x) is not str for x in raw_ids):
        raise FrontierEvidenceError("invalid or repeated deficit id")


def _rows_for(item: Mapping[str, Any], deficits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selector = item["deficit_selector"]
    if item["source_kind"] == "ledger":
        matched = [r for r in deficits if r["deficit_id"] == selector]
        if len(matched) == 1 and matched[0].get("metric") != item["metric"]:
            raise FrontierEvidenceError(f'{item["id"]}: metric identity drift in ledger')
    else:
        matched = [
            r for r in deficits
            if r["deficit_id"] == selector or r["deficit_id"].startswith(selector + ":")
        ]
    if not matched:
        raise FrontierEvidenceError(f'{item["id"]}: accepted ledger row unavailable')
    return matched


def build_frontier_report(
    config: Mapping[str, Any],
    ledger: Mapping[str, Any],
    dashboard: Mapping[str, Any],
) -> dict[str, Any]:
    """Project accepted evidence without assigning new authority or truth."""
    validate_inputs(config, ledger)
    if type(dashboard.get("formal_mesa_baseline")) is not dict:
        raise FrontierEvidenceError("expected canonical dashboard identity")
    deficits = ledger["deficits"]
    covered: set[str] = set()
    records = []
    for item in config["objectives"]:
        evidence = []
        if item["source_kind"] in ("ledger", "ledger_family"):
            rows = _rows_for(item, deficits)
            for row in rows:
                if row.get("owning_issue") not in item["owners"]:
                    raise FrontierEvidenceError(
                        f'{item["id"]}: original deficit owner not represented for '
                        + row["deficit_id"]
                    )
                covered.add(row["deficit_id"])
                state = row.get("state")
                if state not in ("frontier", "open", "blocked", "deferred", "closed"):
                    raise FrontierEvidenceError(f'unsupported ledger state: {state}')
                evidence.append({
                    "deficit_id": row["deficit_id"],
                    "profile": row["benchmark_profile"],
                    "metric": row["metric"],
                    "native_value": row["agent_memory"],
                    "direction": row["direction"],
                    "posture": row["posture"],
                    "ledger_state": state,
                    "adequacy_target": row.get("adequacy_target"),
                    "same_harness_frontier": row.get("same_harness_frontier"),
                    "published_frontier": row.get("published_frontier"),
                    "known_peer_position": observed_peer_position(row),
                    "owning_issue": row.get("owning_issue"),
                    "priority": row.get("priority"),
                    "primary_stage": row.get("primary_stage", "unclassified"),
                    "secondary_stages": row.get("secondary_stages", []),
                    "replay_requirements": row.get("replay_requirements", []),
                    "negative_control_refs": row.get("negative_control_refs", []),
                    "closure_evidence": row.get("closure_evidence", []),
                    "evidence_refs": row.get("evidence_refs", []),
                })
        records.append({
            "id": item["id"],
            "group": item["group"],
            "capability": item["capability"],
            "benchmark": item["benchmark"],
            "metric": item["metric"],
            "source_kind": item["source_kind"],
            "owners": item["owners"],
            "architecture": item["architecture"],
            "release_gate": item["release_gate"],
            "unmeasured_state": item.get("unmeasured_state"),
            "evidence": evidence,
            # Never infer lifecycle completion from an external score or
            # from reaching the best result among two weak local systems.
            "completion_decision": "not_automated",
            "benchmark_specific_implementation_allowed": False,
            "mutation_authority": False,
        })
    absent = sorted(set(r["deficit_id"] for r in deficits) - covered)
    if absent:
        raise FrontierEvidenceError("material accepted deficits lack goals: " + ", ".join(absent))
    return {
        "schema_version": "1.0.0",
        "projection_kind": "read_only_per_capability_frontier",
        "source_refs": list(config["source_of_truth"]),
        "source_dashboard_as_of": dashboard.get("as_of"),
        "universal_score": None,
        "best_in_class_claim": False,
        "authority_effect": "none",
        "objective_count": len(records),
        "deficit_coverage": {"covered": len(covered), "total": len(deficits), "unowned": []},
        "group_counts": dict(sorted(Counter(r["group"] for r in records).items())),
        "goals": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=None,
                        help="optional separate output, never mutate evidence sources")
    args = parser.parse_args()
    root = args.root
    report = build_frontier_report(
        read_json(root / OBJECTIVES),
        read_json(root / DEFICITS),
        read_json(root / DASHBOARD),
    )
    result = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output is None:
        print(result, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
