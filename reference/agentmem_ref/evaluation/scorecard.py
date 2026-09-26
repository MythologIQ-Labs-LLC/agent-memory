"""Deterministic side-by-side scorecards and portfolio status (#534).

Scorecards are derived only from validated common run manifests. Systems share a table
only when their comparison identity (benchmark, frozen input, task profile, selection)
matches, and every delta comes from the fail-closed ``compare_runs`` contract. There is
no aggregate score; missing, blocked, and not-applicable states stay visible.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from .contract import DIMENSIONS, ComparisonCompatibilityError, compare_runs, comparison_identity, validate_run

SCORECARD_SCHEMA_VERSION = "1.0.0"
_KIND_ORDER = {"no_memory": 0, "lexical": 1, "vector": 2, "agent_memory": 3, "external_memory": 4, "other": 5}


def _identity_key(identity: Mapping[str, Any]) -> str:
    return json.dumps(identity, sort_keys=True)


def _system_order(manifest: Mapping[str, Any]) -> tuple[int, str]:
    return (_KIND_ORDER.get(manifest["system"]["kind"], 9), manifest["system"]["id"])


def _cell(metric: Mapping[str, Any] | None) -> dict[str, Any]:
    if metric is None:
        return {"state": "absent"}
    cell = {"state": metric["state"]}
    for key in ("value", "denominator", "unit", "population", "direction"):
        if key in metric:
            cell[key] = metric[key]
    return cell


def benchmark_scorecards(manifests: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Group validated manifests by comparison identity and render side-by-side cards."""

    groups: dict[str, list[dict[str, Any]]] = {}
    for manifest in manifests:
        validated = validate_run(manifest)
        groups.setdefault(_identity_key(comparison_identity(validated)), []).append(validated)
    cards = []
    for key in sorted(groups):
        members = sorted(groups[key], key=_system_order)
        system_ids = [member["system"]["id"] for member in members]
        if len(set(system_ids)) != len(system_ids):
            raise ComparisonCompatibilityError(f"duplicate system in one comparison group: {system_ids}")
        baseline = next((member for member in members if member["system"]["kind"] == "lexical"), None)
        comparisons: dict[str, dict[str, Any]] = {}
        if baseline is not None:
            for member in members:
                if member is not baseline:
                    comparisons[member["system"]["id"]] = compare_runs(baseline, member)
        dimensions: dict[str, Any] = {}
        for dimension_id in DIMENSIONS:
            by_system = {member["system"]["id"]: member["dimensions"][dimension_id] for member in members}
            metric_ids = sorted({metric["metric_id"] for dim in by_system.values() for metric in dim["metrics"]})
            rows = []
            for metric_id in metric_ids:
                row: dict[str, Any] = {"metric_id": metric_id, "systems": {}}
                for system_id, dim in by_system.items():
                    metric = next((item for item in dim["metrics"] if item["metric_id"] == metric_id), None)
                    row["systems"][system_id] = _cell(metric)
                deltas = {}
                for system_id, comparison in comparisons.items():
                    match = next(
                        (item for item in comparison["dimensions"][dimension_id] if item["metric_id"] == metric_id),
                        {"comparison_state": "metric_missing"},
                    )
                    delta = {"comparison_state": match["comparison_state"]}
                    if "delta" in match:
                        delta["delta_vs_baseline"] = round(match["delta"], 6)
                    if "outcome" in match:
                        delta["outcome"] = match["outcome"]
                    deltas[system_id] = delta
                if deltas:
                    row["vs_baseline"] = deltas
                rows.append(row)
            dimensions[dimension_id] = {
                "status": {system_id: dim["status"] for system_id, dim in by_system.items()},
                "notes": {system_id: dim["notes"] for system_id, dim in by_system.items() if dim["notes"]},
                "rows": rows,
            }
        first = members[0]
        cards.append(
            {
                "comparison_identity": comparison_identity(first),
                "systems": [
                    {"id": member["system"]["id"], "kind": member["system"]["kind"], "revision": member["system"]["revision"], "run_status": member["status"], "run_id": member["run_id"]}
                    for member in members
                ],
                "baseline_system": None if baseline is None else baseline["system"]["id"],
                "dimensions": dimensions,
                "authority_effect": "none",
            }
        )
    return cards


def portfolio(profiles: Iterable[Mapping[str, Any]], manifests: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Portfolio status card per registered profile."""

    by_benchmark: dict[str, list[dict[str, Any]]] = {}
    for manifest in manifests:
        validated = validate_run(manifest)
        by_benchmark.setdefault(validated["benchmark"]["id"], []).append(validated)
    rows = []
    for profile in sorted(profiles, key=lambda item: item["profile_id"]):
        runs = by_benchmark.get(profile["benchmark_id"], [])
        measured = sorted(
            {
                dimension_id
                for run in runs
                for dimension_id, dimension in run["dimensions"].items()
                if dimension["status"] in {"measured", "partial"}
            }
        )
        rows.append(
            {
                "profile_id": profile["profile_id"],
                "benchmark_id": profile["benchmark_id"],
                "owning_issue": profile["owning_issue"],
                "evidence": [dict(item) for item in profile.get("external_evidence", ())],
                "systems_run": sorted({run["system"]["id"] for run in runs}),
                "normalized_run_count": len(runs),
                "dimensions_measured": measured,
                "dimensions_not_measured": [dimension for dimension in DIMENSIONS if dimension not in measured],
                "product_findings": [dict(item) for item in profile.get("product_findings", ())],
            }
        )
    return rows


def build(profiles: Iterable[Mapping[str, Any]], manifests: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    manifests = list(manifests)
    return {
        "schema_version": SCORECARD_SCHEMA_VERSION,
        "portfolio": portfolio(profiles, manifests),
        "benchmark_scorecards": benchmark_scorecards(manifests),
        "aggregate_score": "not_defined",
        "authority_effect": "none",
    }


def _format_cell(cell: Mapping[str, Any]) -> str:
    if cell["state"] != "measured":
        return cell["state"]
    value = cell["value"]
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.3f}" if abs(value) < 1000 else f"{value:,.1f}"
    return str(value)


def _format_delta(delta: Mapping[str, Any] | None) -> str:
    if delta is None:
        return ""
    if "delta_vs_baseline" in delta:
        return f"{delta['delta_vs_baseline']:+.3f} ({delta['outcome']})"
    return delta["comparison_state"]


def render_markdown(document: Mapping[str, Any]) -> str:
    lines = [
        "# Memory Evaluation scorecards",
        "",
        "Generated deterministically from normalized run manifests by `scripts/build_benchmark_scorecards.py`. "
        "No aggregate score is defined; `authority_effect: none`.",
        "",
        "Reading rules: each Δ outcome applies one metric's own direction and says nothing about the system overall. "
        "Read related metrics together; for example, a no-memory system's zero staleness comes with a zero new-fact rate. "
        "Systems share a table only when benchmark, frozen input, task profile, and selection match. "
        "`not_measured`, `not_applicable`, `blocked`, and `not_run` are never zero.",
        "",
    ]
    lines += ["## Portfolio status", "", "| profile | issue | evidence variant | status | systems run | dimensions measured | findings |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in document["portfolio"]:
        findings = ", ".join(f"#{item['issue']}" for item in row["product_findings"]) or "none"
        for index, item in enumerate(row["evidence"] or [{"variant": "none", "status": "not_run"}]):
            lead = (f"`{row['profile_id']}`", f"#{row['owning_issue']}") if index == 0 else ("", "")
            tail = (", ".join(row["systems_run"]) or "none", ", ".join(row["dimensions_measured"]) or "none", findings) if index == 0 else ("", "", "")
            lines.append(f"| {lead[0]} | {lead[1]} | {item['variant']} | {item['status']} | {tail[0]} | {tail[1]} | {tail[2]} |")
    lines.append("")
    for card in document["benchmark_scorecards"]:
        identity = card["comparison_identity"]
        systems = [system["id"] for system in card["systems"]]
        others = [system for system in systems if system != card["baseline_system"]]
        lines += [
            f"## {identity['benchmark_id']} — {identity['task_profile']}",
            "",
            f"Input sha256 `{identity['input_sha256']}` · source `{identity['source_revision']}` · selection `{identity['selection_method']}` (n={identity['sample_count']}) · baseline for deltas: `{card['baseline_system']}`",
            "",
        ]
        for dimension_id in DIMENSIONS:
            dimension = card["dimensions"][dimension_id]
            status = ", ".join(f"{system}={dimension['status'][system]}" for system in systems)
            lines.append(f"### {dimension_id} ({status})")
            lines.append("")
            if not dimension["rows"]:
                for system, notes in sorted(dimension["notes"].items()):
                    lines.append(f"- {system}: {'; '.join(notes)}")
                lines.append("")
                continue
            delta_columns = [f"Δ {system} vs {card['baseline_system']}" for system in others] if card["baseline_system"] else []
            lines.append("| metric | " + " | ".join(systems + delta_columns) + " |")
            lines.append("| --- |" + " ---: |" * len(systems) + " --- |" * len(delta_columns))
            for row in dimension["rows"]:
                cells = [_format_cell(row["systems"][system]) for system in systems]
                deltas = [_format_delta(row.get("vs_baseline", {}).get(system)) for system in others] if card["baseline_system"] else []
                lines.append(f"| {row['metric_id']} | " + " | ".join(cells + deltas) + " |")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
