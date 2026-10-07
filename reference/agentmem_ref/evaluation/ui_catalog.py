"""Deterministic projection for the Benchmark Evidence Console (#698).

This module projects accepted benchmark evidence into a presentation-safe catalog.
It does not create benchmark authority, reinterpret native metrics, or decide runtime
behavior. Numeric comparison groups come only from the existing scorecard contract,
which already groups runs by the fail-closed comparison identity.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any, Mapping

CATALOG_SCHEMA_VERSION = "1.0.0"
MISSING_STATES = (
    "not_run",
    "not_measured",
    "evidence_gap",
    "blocked",
    "unsupported",
    "not_applicable",
    "non_comparable",
    "absent",
)


def _stable_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_stable_json(value)).hexdigest()


def _comparison_set_id(identity: Mapping[str, Any]) -> str:
    return "comparison:" + _digest(identity)[:20]


def _profile_id(run: Mapping[str, Any]) -> str:
    benchmark = run["benchmark"]
    return f"{benchmark['id']}:{benchmark.get('task_profile') or 'default'}"


def _metric_key(run: Mapping[str, Any], dimension_id: str, metric_id: str) -> str:
    return f"{_profile_id(run)}:{dimension_id}:{metric_id}"


def _run_projection(path: str, run: Mapping[str, Any]) -> dict[str, Any]:
    metrics = []
    for dimension_id, dimension in sorted(run["dimensions"].items()):
        for metric in sorted(dimension["metrics"], key=lambda item: item["metric_id"]):
            projected = {
                "metric_key": _metric_key(run, dimension_id, metric["metric_id"]),
                "metric_id": metric["metric_id"],
                "dimension": dimension_id,
                "state": metric["state"],
                "direction": metric["direction"],
            }
            for key in ("value", "unit", "denominator", "population", "note"):
                if key in metric:
                    projected[key] = metric[key]
            metrics.append(projected)
    evidence = [{"kind": "normalized_run", "uri": path}]
    for artifact in run.get("artifacts", []):
        item = {"kind": "artifact", "uri": artifact.get("uri"), "artifact_id": artifact.get("artifact_id")}
        if artifact.get("sha256"):
            item["sha256"] = artifact["sha256"]
        evidence.append(item)
    return {
        "run_id": run["run_id"],
        "status": run["status"],
        "benchmark_profile_id": _profile_id(run),
        "benchmark": dict(run["benchmark"]),
        "system": dict(run["system"]),
        "execution": dict(run["execution"]),
        "dimensions": {
            dimension_id: {
                "status": dimension["status"],
                "notes": list(dimension.get("notes", [])),
            }
            for dimension_id, dimension in sorted(run["dimensions"].items())
        },
        "metrics": metrics,
        "limitations": list(run.get("limitations", [])),
        "evidence": evidence,
        "authority_effect": "none",
    }


def _benchmark_registry(runs: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    for run in runs:
        benchmark = run["benchmark"]
        profile_id = _profile_id(run)
        entry = profiles.setdefault(
            profile_id,
            {
                "benchmark_profile_id": profile_id,
                "benchmark_id": benchmark["id"],
                "task_profile": benchmark.get("task_profile"),
                "source_url": benchmark.get("source_url"),
                "source_revisions": set(),
                "dataset_ids": set(),
                "dataset_revisions": set(),
                "input_sha256": set(),
                "run_ids": [],
                "system_ids": set(),
            },
        )
        for key, target in (
            ("source_revision", "source_revisions"),
            ("dataset_id", "dataset_ids"),
            ("dataset_revision", "dataset_revisions"),
            ("input_sha256", "input_sha256"),
        ):
            value = benchmark.get(key)
            if value is not None:
                entry[target].add(value)
        entry["run_ids"].append(run["run_id"])
        entry["system_ids"].add(run["system"]["id"])
    result = []
    for profile_id in sorted(profiles):
        entry = profiles[profile_id]
        result.append(
            {
                **{key: value for key, value in entry.items() if not isinstance(value, set)},
                "source_revisions": sorted(entry["source_revisions"]),
                "dataset_ids": sorted(entry["dataset_ids"]),
                "dataset_revisions": sorted(entry["dataset_revisions"]),
                "input_sha256": sorted(entry["input_sha256"]),
                "run_ids": sorted(entry["run_ids"]),
                "system_ids": sorted(entry["system_ids"]),
            }
        )
    return result


def _metric_registry(runs: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for run in runs:
        for dimension_id, dimension in sorted(run["dimensions"].items()):
            for metric in dimension["metrics"]:
                key = _metric_key(run, dimension_id, metric["metric_id"])
                entry = metrics.setdefault(
                    key,
                    {
                        "metric_key": key,
                        "metric_id": metric["metric_id"],
                        "native_label": metric["metric_id"],
                        "benchmark_profile_id": _profile_id(run),
                        "dimension": dimension_id,
                        "directions": set(),
                        "units": set(),
                        "states_seen": set(),
                        "notes": set(),
                    },
                )
                entry["directions"].add(metric["direction"])
                if metric.get("unit") is not None:
                    entry["units"].add(metric["unit"])
                entry["states_seen"].add(metric["state"])
                if metric.get("note"):
                    entry["notes"].add(metric["note"])
    result = []
    for key in sorted(metrics):
        entry = metrics[key]
        result.append(
            {
                "metric_key": entry["metric_key"],
                "metric_id": entry["metric_id"],
                "native_label": entry["native_label"],
                "benchmark_profile_id": entry["benchmark_profile_id"],
                "dimension": entry["dimension"],
                "directions": sorted(entry["directions"]),
                "units": sorted(entry["units"]),
                "states_seen": sorted(entry["states_seen"]),
                "notes": sorted(entry["notes"]),
            }
        )
    return result


def _system_registry(runs: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    systems: dict[str, dict[str, Any]] = {}
    for run in runs:
        system = run["system"]
        entry = systems.setdefault(
            system["id"],
            {
                "system_id": system["id"],
                "kinds": set(),
                "revisions": set(),
                "adapter_ids": set(),
                "adapter_revisions": set(),
                "run_ids": [],
            },
        )
        entry["kinds"].add(system["kind"])
        entry["revisions"].add(system["revision"])
        if system.get("adapter_id"):
            entry["adapter_ids"].add(system["adapter_id"])
        if system.get("adapter_revision"):
            entry["adapter_revisions"].add(system["adapter_revision"])
        entry["run_ids"].append(run["run_id"])
    result = []
    for system_id in sorted(systems):
        entry = systems[system_id]
        result.append(
            {
                "system_id": system_id,
                "kinds": sorted(entry["kinds"]),
                "revisions": sorted(entry["revisions"]),
                "adapter_ids": sorted(entry["adapter_ids"]),
                "adapter_revisions": sorted(entry["adapter_revisions"]),
                "run_ids": sorted(entry["run_ids"]),
            }
        )
    return result


def _same_harness_lane_ids(dashboard: Mapping[str, Any]) -> set[str]:
    return {
        lane["lane_id"]
        for lane in dashboard.get("competitive_evidence", {}).get("frozen_lanes", [])
        if lane.get("status") == "accepted"
    }


def _comparison_sets(scorecards: Mapping[str, Any], dashboard: Mapping[str, Any]) -> list[dict[str, Any]]:
    lane_ids = _same_harness_lane_ids(dashboard)
    result = []
    for card in scorecards.get("benchmark_scorecards", []):
        identity = dict(card["comparison_identity"])
        task_profile = identity.get("task_profile") or ""
        evidence_class = "same_harness" if any(lane_id in task_profile for lane_id in lane_ids) else "same_profile"
        result.append(
            {
                "comparison_set_id": _comparison_set_id(identity),
                "comparison_state": "exact",
                "evidence_class": evidence_class,
                "comparison_identity": identity,
                "systems": [dict(item) for item in card["systems"]],
                "baseline_system": card.get("baseline_system"),
                "dimensions": card["dimensions"],
                "eligible_for_numeric_delta": True,
                "authority_effect": "none",
            }
        )
    return sorted(result, key=lambda item: item["comparison_set_id"])


def _published_references(dashboard: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for item in dashboard.get("published_reference", []):
        result.append(
            {
                **dict(item),
                "evidence_class": "published_reference",
                "comparison_state": "published_reference",
                "eligible_for_numeric_delta": False,
                "authority_effect": "none",
            }
        )
    return sorted(result, key=lambda item: item["system"].lower())


def _coverage(scorecards: Mapping[str, Any], dashboard: Mapping[str, Any]) -> dict[str, Any]:
    profiles = []
    for item in scorecards.get("portfolio", []):
        profiles.append(
            {
                "profile_id": item["profile_id"],
                "benchmark_id": item["benchmark_id"],
                "owning_issue": item["owning_issue"],
                "dimensions_measured": list(item.get("dimensions_measured", [])),
                "dimensions_not_measured": list(item.get("dimensions_not_measured", [])),
                "systems_run": list(item.get("systems_run", [])),
                "evidence": [dict(entry) for entry in item.get("evidence", [])],
                "product_findings": [dict(entry) for entry in item.get("product_findings", [])],
            }
        )
    judged = dashboard.get("competitive_evidence", {}).get("llm_judged_profile", {})
    explicit_states = []
    if judged:
        explicit_states.append(
            {
                "capability": "reasoning_qa",
                "state": "blocked" if str(judged.get("status", "")).startswith("blocked") else judged.get("status", "not_run"),
                "source": "competitive_evidence.llm_judged_profile",
                "detail": dict(judged),
            }
        )
    return {
        "profiles": sorted(profiles, key=lambda item: item["profile_id"]),
        "explicit_states": explicit_states,
        "missing_state_vocabulary": list(MISSING_STATES),
    }


def _evidence_index(runs: list[dict[str, Any]], published: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for run in runs:
        result.append(
            {
                "evidence_id": f"run:{run['run_id']}",
                "kind": "run",
                "run_id": run["run_id"],
                "pointers": list(run["evidence"]),
            }
        )
    for item in published:
        result.append(
            {
                "evidence_id": f"published:{item['system']}",
                "kind": "published_reference",
                "system": item["system"],
                "pointers": [{"kind": "external_source", "uri": item["source"]}],
            }
        )
    return sorted(result, key=lambda item: item["evidence_id"])


def _snapshot_material(
    dashboard: Mapping[str, Any],
    scorecards: Mapping[str, Any],
    normalized_runs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "dashboard": dashboard,
        "scorecards": scorecards,
        "normalized_runs": {path: normalized_runs[path] for path in sorted(normalized_runs)},
    }


def build_catalog(
    *,
    dashboard: Mapping[str, Any],
    scorecards: Mapping[str, Any],
    normalized_runs: Mapping[str, Mapping[str, Any]],
    repository_head: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, presentation-safe benchmark catalog.

    The snapshot digest is based only on projection-relevant evidence inputs. Repository
    head is descriptive staleness context and deliberately excluded from the digest so
    unrelated repository commits do not create a false benchmark snapshot.
    """

    run_docs = [normalized_runs[path] for path in sorted(normalized_runs)]
    runs = [_run_projection(path, normalized_runs[path]) for path in sorted(normalized_runs)]
    published = _published_references(dashboard)
    material = _snapshot_material(dashboard, scorecards, normalized_runs)
    snapshot_digest = _digest(material)
    evidence_revision = dashboard.get("main_head")
    repository_is_newer = repository_head is not None and repository_head != evidence_revision
    catalog = {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "authority_effect": "none",
        "aggregate_score": "not_defined",
        "snapshot": {
            "id": f"sha256:{snapshot_digest}",
            "as_of": dashboard.get("as_of"),
            "dashboard_id": dashboard.get("dashboard"),
            "evidence_revision": evidence_revision,
            "repository_head": repository_head,
            "repository_is_newer": repository_is_newer,
            "source_digests": {
                "dashboard": _digest(dashboard),
                "scorecards": _digest(scorecards),
                "normalized_runs": _digest({path: normalized_runs[path] for path in sorted(normalized_runs)}),
            },
        },
        "reading_rules": list(dashboard.get("reading_rules", [])),
        "comparison_classes": dict(dashboard.get("comparison_classes", {})),
        "benchmarks": _benchmark_registry(run_docs),
        "metrics": _metric_registry(run_docs),
        "systems": _system_registry(run_docs),
        "runs": runs,
        "comparison_sets": _comparison_sets(scorecards, dashboard),
        "longitudinal_tracks": {
            key: [dict(item) for item in value]
            for key, value in sorted(dashboard.get("tracks", {}).items())
        },
        "coverage": _coverage(scorecards, dashboard),
        "published_references": published,
        "evidence_index": _evidence_index(runs, published),
    }
    return catalog
