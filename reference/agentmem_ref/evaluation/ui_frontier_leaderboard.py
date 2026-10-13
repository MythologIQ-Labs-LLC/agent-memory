"""#779: deterministic per-metric benchmark frontiers over the accepted UI catalog.

Read only. Comparison sets originate exclusively from F1's fail-closed scorecard
projection. This is not an answer to "who is globally best?" and not a memory
governance or lifecycle authority.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

SCHEMA_VERSION = "0.1.0"
RANKABLE = frozenset({"higher_better", "lower_better", "zero_target"})
AGENT_KINDS = frozenset({"agent_memory"})


class FrontierProjectionError(ValueError):
    """The catalog is malformed or cannot safely describe a metric frontier."""


def _number(v: Any) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def _identity_ready(comp: Mapping[str, Any]) -> bool:
    keys = ("benchmark_id", "task_profile", "input_sha256",
            "selection_id", "sample_count")
    return all(comp.get(key) is not None and comp.get(key) != "" for key in keys)


def _result(
    comp: Mapping[str, Any],
    dimension_id: str,
    metric: Mapping[str, Any],
    run_evidence: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    ident = comp["comparison_identity"]
    systems = comp["systems"]
    if not isinstance(systems, list) or not all(isinstance(s, dict) for s in systems):
        raise FrontierProjectionError("comparison system registry must be a list")
    lookup: dict[str, dict[str, Any]] = {}
    for system in systems:
        system_id = system.get("id")
        if not isinstance(system_id, str) or not system_id or system_id in lookup:
            raise FrontierProjectionError("missing or duplicate exact system identity")
        lookup[system_id] = system
    agent_ids = [
        key for key, val in lookup.items()
        if val.get("kind") in AGENT_KINDS or key in ("agent-memory", "agent_memory")
    ]
    if len(agent_ids) > 1:
        raise FrontierProjectionError("multiple Agent Memory rows in one comparison set")
    agent_id = agent_ids[0] if agent_ids else None

    observed = metric.get("systems", {})
    if not isinstance(observed, dict) or any(k not in lookup for k in observed):
        raise FrontierProjectionError("scorecard contains unknown system identity")
    eligible = []
    for system_id, observation in observed.items():
        if not isinstance(observation, dict):
            raise FrontierProjectionError("malformed native metric observation")
        if observation.get("state") != "measured" or not _number(observation.get("value")):
            continue
        config = lookup[system_id]
        run = run_evidence.get(config.get("run_id"), {})
        eligible.append({
            "system_id": system_id,
            "system_kind": config.get("kind"),
            "revision": config.get("revision"),
            "run_id": config.get("run_id"),
            "value": observation["value"],
            "direction": observation.get("direction"),
            "unit": observation.get("unit"),
            "denominator": observation.get("denominator"),
            "population": observation.get("population"),
            "evidence": list(run.get("evidence", [])),
        })

    # No score can silently become a winner merely by being the only
    # available measurement. Known omissions are distinct from ties.
    ranking_state = "non_comparable"
    leader = None
    agent_memory = None
    ranking = []
    gap = None
    metric_dir = None
    native_unit = None

    accepted = (
        comp.get("evidence_class") == "same_harness"
        and comp.get("comparison_state") == "exact"
        and comp.get("eligible_for_numeric_delta") is True
        and _identity_ready(ident)
    )
    if accepted:
        if not eligible:
            ranking_state = "not_measured"
        else:
            directions = {row["direction"] for row in eligible}
            units = {row["unit"] for row in eligible}
            populations = {row["population"] for row in eligible}
            denominators = {row["denominator"] for row in eligible}
            if (len(directions) != 1 or len(units) != 1
                    or len(populations) != 1 or len(denominators) != 1):
                ranking_state = "non_comparable"
            else:
                metric_dir = next(iter(directions))
                native_unit = next(iter(units))
                am = next((row for row in eligible if row["system_id"] == agent_id), None)
                if metric_dir not in RANKABLE:
                    ranking_state = "not_rankable"
                elif am is None:
                    ranking_state = "agent_memory_missing"
                elif len(eligible) < 2:
                    ranking_state = "no_peer"
                    agent_memory = {**am, "rank": None}
                else:
                    ranking_state = "ranked"
                    sign = -1 if metric_dir == "higher_better" else 1
                    ordered = sorted(
                        eligible, key=lambda row: (sign * row["value"], row["system_id"])
                    )
                    last = None
                    rank = 0
                    for index, row in enumerate(ordered, start=1):
                        if last is None or row["value"] != last:
                            rank = index
                        last = row["value"]
                        ranking.append({**row, "rank": rank})
                    leader = dict(ranking[0])
                    agent_memory = next(
                        dict(row) for row in ranking if row["system_id"] == agent_id
                    )
                    gap = (leader["value"] - agent_memory["value"]) if sign == -1 else (
                        agent_memory["value"] - leader["value"]
                    )
                    gap = max(0.0, float(gap))

    return {
        "comparison_set_id": comp["comparison_set_id"],
        "benchmark_id": ident.get("benchmark_id"),
        "task_profile": ident.get("task_profile"),
        "input_sha256": ident.get("input_sha256"),
        "selection_id": ident.get("selection_id"),
        "sample_count": ident.get("sample_count"),
        "dimension": dimension_id,
        "metric_id": metric["metric_id"],
        "metric_key": (
            str(ident.get("benchmark_id")) + ":" + str(ident.get("task_profile"))
            + ":" + dimension_id + ":" + metric["metric_id"]
        ),
        "evidence_class": comp.get("evidence_class"),
        "direction": metric_dir,
        "unit": native_unit,
        "ranking_state": ranking_state,
        "ranking": ranking,
        "leader": leader,
        "agent_memory": agent_memory,
        "gap_to_leader_native": gap,
        "adequacy": {"state": "threshold_not_established", "target": None},
        "authority_effect": "none",
    }


def build_frontier_leaderboard(catalog: Mapping[str, Any]) -> dict[str, Any]:
    """Project all F1 metric definitions plus exact accepted comparison rows.

    Rows outside same-harness evidence remain visible but ineligible. The F1
    catalog snapshot remains the sole identity of this projection.
    """
    if not isinstance(catalog, dict) or not isinstance(catalog.get("snapshot"), dict):
        raise FrontierProjectionError("missing versioned F1 catalog snapshot")
    snapshot = catalog["snapshot"].get("id")
    if not isinstance(snapshot, str) or not snapshot:
        raise FrontierProjectionError("snapshot identity is required")
    runs = {
        r["run_id"]: r for r in catalog.get("runs", [])
        if isinstance(r, dict) and isinstance(r.get("run_id"), str)
    }
    rows = []
    for comparison in sorted(
        catalog.get("comparison_sets", []),
        key=lambda item: item["comparison_set_id"],
    ):
        identity = comparison.get("comparison_identity")
        if not isinstance(identity, dict):
            raise FrontierProjectionError("comparison identity missing")
        for dimension, content in sorted(comparison.get("dimensions", {}).items()):
            if not isinstance(content, dict):
                raise FrontierProjectionError("malformed scorecard dimension")
            for metric in sorted(content.get("rows", []), key=lambda x: x["metric_id"]):
                rows.append(_result(comparison, dimension, metric, runs))
    represented = {
        row["metric_key"] for row in rows if row["evidence_class"] == "same_harness"
    }
    coverage = []
    for metric in sorted(catalog.get("metrics", []), key=lambda x: x["metric_key"]):
        key = metric["metric_key"]
        coverage.append({
            "metric_key": key,
            "benchmark_profile_id": metric["benchmark_profile_id"],
            "dimension": metric["dimension"],
            "metric_id": metric["metric_id"],
            "state": "has_accepted_comparison" if key in represented else "no_accepted_comparison",
            "gap_to_leader_native": None,
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot,
        "authority_effect": "none",
        "aggregate_score": None,
        "leaderboards": rows,
        "metric_coverage": coverage,
        "published_reference_count_unranked": len(catalog.get("published_references", [])),
    }
