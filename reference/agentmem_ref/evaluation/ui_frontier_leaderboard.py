"""#779: deterministic per-metric benchmark frontiers over the accepted UI catalog.

Read only. Comparison sets originate exclusively from F1's fail-closed scorecard
projection. This is not an answer to "who is globally best?" and not a memory
governance or lifecycle authority.

Every numeric competitive claim in the output is traceable to one accepted
same-harness comparison set, one exact run per system, and the F1 snapshot
identity. Anything that cannot be traced is emitted as a typed state with a
reason, never as a number, a rank or a win.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import math
from typing import Any, Mapping

SCHEMA_VERSION = "0.2.0"
RANKABLE = frozenset({"higher_better", "lower_better", "zero_target"})
AGENT_KINDS = frozenset({"agent_memory"})
AGENT_IDS = frozenset({"agent-memory", "agent_memory"})
CONTROL_KINDS = frozenset({"lexical", "no_memory"})
EXTERNAL_KINDS = frozenset({"external_memory"})
KNOWN_EVIDENCE_CLASSES = frozenset({
    "same_harness", "same_profile", "agent_memory_longitudinal",
    "external_cross_system_reference", "published_reference",
})
ACCEPTED_RUN_STATUSES = frozenset({"complete"})
RANKING_STATES = (
    "ranked", "no_peer", "agent_memory_missing", "non_comparable",
    "not_measured", "not_rankable",
)
COMPETITIVE_STATES = (
    "leading_vs_external", "tied_leader", "leading_vs_controls_only",
    "behind_external", "behind_control",
)
CURRENCY_STATES = ("current", "superseded", "newer_unaccepted_evidence", "undetermined")
OBJECTIVE_REGISTRY_STATES = ("absent", "draft", "canonical")
# Nine Coverage Atlas capability families (docs/BENCHMARK_COVERAGE_ATLAS.md).
CAPABILITY_FAMILIES = {
    "A": "Ingestion and representation",
    "B": "Retrieval and relevance",
    "C": "Temporal memory",
    "D": "Lifecycle and metabolism",
    "E": "Governance and safety",
    "F": "Operational durability",
    "G": "Cognition and task utility",
    "H": "Multi-source / multi-agent / multimodal",
    "I": "Evaluator quality",
}


class FrontierProjectionError(ValueError):
    """The catalog is malformed or cannot safely describe a metric frontier."""


def _number(v: Any) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def _text(v: Any) -> bool:
    return isinstance(v, str) and v != ""


def _timestamp(v: Any) -> str | None:
    """Normalise an ISO-8601 timestamp for ordering; unparsable means unknown."""
    if not _text(v):
        return None
    try:
        parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone().isoformat()


def _identity_ready(comp: Mapping[str, Any]) -> bool:
    keys = ("benchmark_id", "task_profile", "input_sha256",
            "selection_id", "sample_count")
    return all(comp.get(key) is not None and comp.get(key) != "" for key in keys)


def _role(kind: Any, system_id: str) -> str:
    if kind in AGENT_KINDS or system_id in AGENT_IDS:
        return "subject"
    if kind in EXTERNAL_KINDS:
        return "external_competitor"
    if kind in CONTROL_KINDS:
        return "control"
    return "unclassified"


def _system_lookup(comp: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    systems = comp.get("systems")
    if not isinstance(systems, list) or not all(isinstance(s, dict) for s in systems):
        raise FrontierProjectionError("comparison system registry must be a list")
    lookup: dict[str, dict[str, Any]] = {}
    for system in systems:
        system_id = system.get("id")
        if not isinstance(system_id, str) or not system_id or system_id in lookup:
            raise FrontierProjectionError("missing or duplicate exact system identity")
        lookup[system_id] = system
    return lookup


def _agent_id(lookup: Mapping[str, Mapping[str, Any]]) -> str | None:
    agent_ids = [
        key for key, val in lookup.items() if _role(val.get("kind"), key) == "subject"
    ]
    if len(agent_ids) > 1:
        raise FrontierProjectionError("multiple Agent Memory rows in one comparison set")
    return agent_ids[0] if agent_ids else None


def _verify_run(
    system_id: str,
    config: Mapping[str, Any],
    ident: Mapping[str, Any],
    runs: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, list[str]]:
    """Return (provenance, problems). Provenance is None when unverifiable.

    A measured value whose run cannot be found, is not complete, or whose
    execution identity differs from the comparison identity is never ranked.
    """
    run_id = config.get("run_id")
    if not _text(run_id):
        return None, [f"provenance_missing:{system_id}"]
    run = runs.get(run_id)
    if not isinstance(run, dict):
        return None, [f"provenance_missing:{system_id}"]
    problems: list[str] = []
    if run.get("status") not in ACCEPTED_RUN_STATUSES:
        problems.append(f"run_not_complete:{system_id}")
    bench = run.get("benchmark") if isinstance(run.get("benchmark"), dict) else {}
    execution = run.get("execution") if isinstance(run.get("execution"), dict) else {}
    run_system = run.get("system") if isinstance(run.get("system"), dict) else {}
    checks = (
        ("input_sha256", bench.get("input_sha256"), ident.get("input_sha256")),
        ("benchmark_id", bench.get("id"), ident.get("benchmark_id")),
        ("task_profile", bench.get("task_profile"), ident.get("task_profile")),
        ("selection_id", execution.get("selection_id"), ident.get("selection_id")),
        ("sample_count", execution.get("sample_count"), ident.get("sample_count")),
    )
    for name, observed, expected in checks:
        if observed is None or str(observed) != str(expected):
            problems.append(f"run_identity_mismatch:{system_id}:{name}")
    # The run must be this system's own: a complete run for a different system
    # or kind carrying the same revision is never credited to this competitor.
    if run_system.get("id") != system_id:
        problems.append(f"run_system_mismatch:{system_id}:id")
    if run_system.get("kind") != config.get("kind"):
        problems.append(f"run_system_mismatch:{system_id}:kind")
    revision = config.get("revision")
    if not _text(revision) or run_system.get("revision") != revision:
        problems.append(f"run_revision_mismatch:{system_id}")
    provenance = {
        "run_id": run_id,
        "run_status": run.get("status"),
        "revision": run_system.get("revision"),
        "adapter_id": run_system.get("adapter_id"),
        "adapter_revision": run_system.get("adapter_revision"),
        "configuration_digest": run_system.get("configuration_digest"),
        "started_at": execution.get("started_at"),
        "seed": execution.get("seed"),
        "selection_method": execution.get("selection_method"),
        "benchmark_profile_id": run.get("benchmark_profile_id"),
        "dataset_id": bench.get("dataset_id"),
        "dataset_revision": bench.get("dataset_revision"),
        "source_revision": bench.get("source_revision"),
        "source_url": bench.get("source_url"),
        "evidence": [dict(e) for e in run.get("evidence", []) if isinstance(e, dict)],
        "verified": not problems,
    }
    return provenance, problems


def _observation_state(observation: Mapping[str, Any]) -> tuple[str, str | None]:
    """Classify one native observation: (class, reason)."""
    state = observation.get("state")
    value = observation.get("value")
    if state != "measured":
        return "unmeasured", f"state:{state if state is not None else 'absent'}"
    if isinstance(value, bool):
        return "measured_non_numeric", "boolean_value"
    if value is None:
        return "unmeasured", "state:measured_without_value"
    if not _number(value):
        return "measured_non_numeric", "non_finite_or_non_numeric_value"
    if observation.get("unit") == "ratio" and not 0.0 <= value <= 1.0:
        return "invalid", "ratio_out_of_range"
    if observation.get("direction") == "zero_target" and value < 0:
        # zero_target ranks ascending as distance from zero, which is only a valid
        # order on a nonnegative domain; a negative native value cannot be placed.
        return "invalid", "zero_target_negative_value"
    return "numeric", None


def _result(
    comp: Mapping[str, Any],
    dimension_id: str,
    metric: Mapping[str, Any],
    runs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    ident = comp["comparison_identity"]
    if not isinstance(metric, dict) or not _text(metric.get("metric_id")):
        raise FrontierProjectionError("scorecard row without exact metric identity")
    lookup = _system_lookup(comp)
    agent_id = _agent_id(lookup)
    observed = metric.get("systems", {})
    if not isinstance(observed, dict) or any(k not in lookup for k in observed):
        raise FrontierProjectionError("scorecard contains unknown system identity")

    reasons: list[str] = []
    systems_observed: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    any_measured = False
    for system_id in sorted(observed):
        observation = observed[system_id]
        if not isinstance(observation, dict):
            raise FrontierProjectionError("malformed native metric observation")
        config = lookup[system_id]
        role = _role(config.get("kind"), system_id)
        klass, reason = _observation_state(observation)
        record = {
            "system_id": system_id,
            "system_kind": config.get("kind"),
            "role": role,
            "state": observation.get("state"),
            "value": observation.get("value") if klass in ("numeric", "measured_non_numeric") else None,
            "direction": observation.get("direction"),
            "unit": observation.get("unit"),
            "denominator": observation.get("denominator"),
            "population": observation.get("population"),
            "eligible": False,
            "exclusion_reason": reason,
        }
        if klass == "invalid":
            reasons.append(f"invalid_observation:{system_id}:{reason}")
        if klass != "unmeasured":
            any_measured = True
        if klass == "numeric":
            provenance, problems = _verify_run(system_id, config, ident, runs)
            if problems:
                reasons.extend(problems)
                record["exclusion_reason"] = ";".join(problems)
            else:
                record["eligible"] = True
                record["exclusion_reason"] = None
                eligible.append({
                    "system_id": system_id,
                    "system_kind": config.get("kind"),
                    "role": role,
                    "revision": config.get("revision"),
                    "run_id": config.get("run_id"),
                    "value": observation["value"],
                    "direction": observation.get("direction"),
                    "unit": observation.get("unit"),
                    "denominator": observation.get("denominator"),
                    "population": observation.get("population"),
                    "evidence": list(provenance.pop("evidence")),
                    "provenance": provenance,
                })
        systems_observed.append(record)

    # No score can silently become a winner merely by being the only
    # available measurement. Known omissions are distinct from ties.
    ranking_state = "non_comparable"
    competitive_state = None
    leader = None
    leader_state = None
    co_leaders: list[str] = []
    agent_memory = None
    ranking: list[dict[str, Any]] = []
    gap = None
    gap_pp = None
    metric_dir = None
    native_unit = None
    evidence_class = comp.get("evidence_class")

    if evidence_class not in KNOWN_EVIDENCE_CLASSES:
        reasons.append("unknown_evidence_class")
    elif evidence_class != "same_harness":
        reasons.append(f"evidence_class:{evidence_class}")
    if comp.get("comparison_state") != "exact":
        reasons.append(f"comparison_state:{comp.get('comparison_state')}")
    if comp.get("eligible_for_numeric_delta") is not True:
        reasons.append("not_eligible_for_numeric_delta")
    if not _identity_ready(ident):
        reasons.append("comparison_identity_incomplete")
    accepted = (
        evidence_class == "same_harness"
        and comp.get("comparison_state") == "exact"
        and comp.get("eligible_for_numeric_delta") is True
        and _identity_ready(ident)
    )
    provenance_broken = any(
        r.startswith(("provenance_missing", "run_identity_mismatch",
                      "run_revision_mismatch", "run_not_complete", "invalid_observation"))
        for r in reasons
    )
    if accepted and provenance_broken:
        ranking_state = "non_comparable"
    elif accepted:
        if not eligible:
            if any_measured:
                ranking_state = "not_rankable"
                reasons.append("measured_values_are_not_ordinal_numbers")
            else:
                ranking_state = "not_measured"
                reasons.append("no_measured_observation")
        else:
            directions = {row["direction"] for row in eligible}
            units = {row["unit"] for row in eligible}
            populations = {row["population"] for row in eligible}
            denominators = {row["denominator"] for row in eligible}
            if len(directions) != 1:
                reasons.append("direction_mismatch")
            if len(units) != 1:
                reasons.append("unit_mismatch")
            if len(populations) != 1:
                reasons.append("population_mismatch")
            if len(denominators) != 1:
                reasons.append("denominator_mismatch")
            if any(row["unit"] in (None, "") for row in eligible):
                reasons.append("unit_missing")
            if any(row["population"] in (None, "") for row in eligible):
                reasons.append("population_missing")
            if any(not _number(row["denominator"]) or row["denominator"] <= 0
                   for row in eligible):
                reasons.append("denominator_missing_or_invalid")
            if any(r in reasons for r in (
                "direction_mismatch", "unit_mismatch", "population_mismatch",
                "denominator_mismatch", "unit_missing", "population_missing",
                "denominator_missing_or_invalid",
            )):
                ranking_state = "non_comparable"
            else:
                metric_dir = next(iter(directions))
                native_unit = next(iter(units))
                am = next((row for row in eligible if row["system_id"] == agent_id), None)
                if metric_dir not in RANKABLE:
                    ranking_state = "not_rankable"
                    reasons.append(f"direction:{metric_dir}")
                elif am is None:
                    ranking_state = "agent_memory_missing"
                    reasons.append("agent_memory_observation_not_eligible")
                elif len(eligible) < 2:
                    ranking_state = "no_peer"
                    reasons.append("no_eligible_peer_measurement")
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
                    leaders = [row for row in ranking if row["rank"] == 1]
                    co_leaders = [row["system_id"] for row in leaders]
                    leader_state = "tied" if len(co_leaders) > 1 else "sole"
                    # The representative leader is chosen by role, not by identifier order:
                    # an external competitor among the co-leaders is the market reference.
                    role_order = {"external_competitor": 0, "control": 1, "subject": 2, "unclassified": 3}
                    leader = dict(sorted(leaders, key=lambda row: (role_order[row["role"]], row["system_id"]))[0])
                    leader_roles = {row["role"] for row in leaders}
                    agent_memory = next(
                        dict(row) for row in ranking if row["system_id"] == agent_id
                    )
                    gap = (leader["value"] - agent_memory["value"]) if sign == -1 else (
                        agent_memory["value"] - leader["value"]
                    )
                    gap = max(0.0, float(gap))
                    if native_unit == "ratio":
                        gap_pp = round(gap * 100.0, 6)
                    externals = [r for r in ranking if r["role"] == "external_competitor"]
                    if agent_memory["rank"] == 1 and leader_state == "tied":
                        competitive_state = "tied_leader"
                    elif agent_memory["rank"] == 1 and externals:
                        competitive_state = "leading_vs_external"
                    elif agent_memory["rank"] == 1:
                        competitive_state = "leading_vs_controls_only"
                    elif "external_competitor" in leader_roles:
                        competitive_state = "behind_external"  # any external co-leader counts
                    else:
                        competitive_state = "behind_control"

    external_ids = sorted(
        k for k, v in lookup.items() if _role(v.get("kind"), k) == "external_competitor"
    )
    control_ids = sorted(
        k for k, v in lookup.items() if _role(v.get("kind"), k) == "control"
    )
    ranked_ids = {row["system_id"] for row in ranking}
    return {
        "comparison_set_id": comp["comparison_set_id"],
        "benchmark_id": ident.get("benchmark_id"),
        "task_profile": ident.get("task_profile"),
        "input_sha256": ident.get("input_sha256"),
        "selection_id": ident.get("selection_id"),
        "sample_count": ident.get("sample_count"),
        "dataset_id": ident.get("dataset_id"),
        "dataset_revision": ident.get("dataset_revision"),
        "dimension": dimension_id,
        "metric_id": metric["metric_id"],
        "metric_key": (
            str(ident.get("benchmark_id")) + ":" + str(ident.get("task_profile"))
            + ":" + dimension_id + ":" + metric["metric_id"]
        ),
        "evidence_class": evidence_class,
        "comparison_state": comp.get("comparison_state"),
        "baseline_system": comp.get("baseline_system"),
        "direction": metric_dir,
        "unit": native_unit,
        "ranking_state": ranking_state,
        "competitive_state": competitive_state,
        "reasons": sorted(set(reasons)),
        "ranking": ranking,
        "leader": leader,
        "leader_state": leader_state,
        "co_leaders": co_leaders,
        "agent_memory": agent_memory,
        "gap_to_leader_native": gap,
        "gap_percentage_points": gap_pp,
        "peer_population": {
            "external_competitors": external_ids,
            "controls": control_ids,
            "external_competitor_ranked": any(
                sid in ranked_ids for sid in external_ids
            ),
        },
        "systems_observed": systems_observed,
        "adequacy": {"state": "threshold_not_established", "target": None},
        "currency": None,
        "objectives": [],
        "authority_effect": "none",
    }


def _set_signature(comp: Mapping[str, Any]) -> str:
    """Structural identity of a comparison set independent of its label.

    Two sets are repeated runs of one comparison when they share the frozen
    input, selection, sample, the system-kind population and the exact native
    metric metadata. Task-profile labels are never parsed.
    """
    ident = comp["comparison_identity"]
    rows = set()
    for dimension, content in sorted(comp.get("dimensions", {}).items()):
        for metric in content.get("rows", []):
            for system_id, observation in metric.get("systems", {}).items():
                if not isinstance(observation, dict):
                    continue
                rows.add(json.dumps([
                    dimension, metric.get("metric_id"), observation.get("unit"),
                    observation.get("population"), observation.get("denominator"),
                ], sort_keys=True))
    kinds = sorted(str(s.get("kind")) for s in comp.get("systems", []))
    payload = json.dumps({
        "benchmark_id": ident.get("benchmark_id"),
        "input_sha256": ident.get("input_sha256"),
        "selection_id": str(ident.get("selection_id")),
        "sample_count": str(ident.get("sample_count")),
        "kinds": kinds,
        "rows": sorted(rows),
    }, sort_keys=True)
    return "lineage:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _currency(
    comparisons: list[Mapping[str, Any]],
    runs: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Chronology of repeated Agent Memory runs per structural lineage."""
    members: dict[str, list[dict[str, Any]]] = {}
    for comp in comparisons:
        lookup = _system_lookup(comp)
        agent_id = _agent_id(lookup)
        started = None
        revision = None
        if agent_id is not None:
            run = runs.get(lookup[agent_id].get("run_id"), {})
            execution = run.get("execution") if isinstance(run.get("execution"), dict) else {}
            started = execution.get("started_at")
            revision = lookup[agent_id].get("revision")
        members.setdefault(_set_signature(comp), []).append({
            "comparison_set_id": comp["comparison_set_id"],
            "evidence_class": comp.get("evidence_class"),
            "started_at": _timestamp(started),
            "revision": revision,
        })
    out: dict[str, dict[str, Any]] = {}
    for lineage_id, rows in members.items():
        ordered_ok = all(r["started_at"] is not None for r in rows)
        for row in rows:
            others = [r for r in rows if r["comparison_set_id"] != row["comparison_set_id"]]
            unaccepted = sorted({
                str(r["revision"]) for r in others if r["evidence_class"] != "same_harness"
            })
            superseded_by = None
            state = "current"
            if others and not ordered_ok:
                state = "undetermined"
            elif others:
                later_same = [
                    r for r in others
                    if r["evidence_class"] == "same_harness"
                    and r["started_at"] > row["started_at"]
                ]
                later_other = [
                    r for r in others
                    if r["evidence_class"] != "same_harness"
                    and r["started_at"] > row["started_at"]
                ]
                if later_same:
                    superseded_by = max(later_same, key=lambda r: r["started_at"])["comparison_set_id"]
                    state = "superseded"
                elif later_other:
                    state = "newer_unaccepted_evidence"
            out[row["comparison_set_id"]] = {
                "state": state,
                "lineage_id": lineage_id,
                "lineage_size": len(rows),
                "agent_memory_revision": row["revision"],
                "agent_memory_started_at": row["started_at"],
                "superseded_by": superseded_by,
                "unaccepted_sibling_revisions": unaccepted,
            }
    return out


def _norm(text: Any) -> str:
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


def validate_objectives(registry: Any) -> dict[str, Any]:
    """Validate a frontier objectives registry (PR #768 shape). Fail closed."""
    if not isinstance(registry, dict):
        raise FrontierProjectionError("objectives registry must be an object")
    groups = registry.get("capability_groups")
    if not isinstance(groups, dict) or sorted(groups) != sorted(CAPABILITY_FAMILIES):
        raise FrontierProjectionError("objectives registry must declare exactly families A-I")
    if any(not _text(v) for v in groups.values()):
        raise FrontierProjectionError("objective family names must be non-empty strings")
    policy = registry.get("claims_policy")
    if not isinstance(policy, dict) or policy.get("universal_score") is not None \
            or policy.get("authority_effect") != "none":
        raise FrontierProjectionError("objectives registry claims policy is not read-only")
    objectives = registry.get("objectives")
    if not isinstance(objectives, list) or not objectives:
        raise FrontierProjectionError("objectives registry has no objectives")
    seen: set[str] = set()
    items = []
    for obj in objectives:
        if not isinstance(obj, dict):
            raise FrontierProjectionError("objective must be an object")
        oid = obj.get("id")
        if not _text(oid) or oid in seen:
            raise FrontierProjectionError("objective id missing or duplicated")
        seen.add(oid)
        if obj.get("group") not in groups:
            raise FrontierProjectionError(f"objective {oid} has unknown family")
        owners = obj.get("owners")
        if not isinstance(owners, list) or not owners or \
                any(type(o) is not int or o <= 0 for o in owners):
            raise FrontierProjectionError(f"objective {oid} has no issue owners")
        if not _text(obj.get("benchmark")) or not _text(obj.get("metric")) \
                or not _text(obj.get("source_kind")):
            raise FrontierProjectionError(f"objective {oid} lacks benchmark/metric identity")
        for forbidden in ("score", "value", "rank", "gap"):
            if forbidden in obj:
                raise FrontierProjectionError(f"objective {oid} carries a numeric claim")
        items.append({
            "id": oid,
            "group": obj["group"],
            "capability": obj.get("capability"),
            "benchmark": obj["benchmark"],
            "metric": obj["metric"],
            "source_kind": obj["source_kind"],
            "unmeasured_state": obj.get("unmeasured_state"),
            "owners": [f"#{o}" for o in owners],
            "deficit_selector": obj.get("deficit_selector"),
            "release_gate": obj.get("release_gate"),
            "architecture": obj.get("architecture"),
            "linked_metric_keys": [],
            "linkage": "label_match",
        })
    present = {item["group"] for item in items}
    missing = sorted(set(groups) - present)
    return {
        "schema_version": registry.get("schema_version"),
        "families": {key: groups[key] for key in sorted(groups)},
        "families_without_objective": missing,
        "items": sorted(items, key=lambda x: x["id"]),
    }


def _link_objectives(rows: list[dict[str, Any]], items: list[dict[str, Any]]) -> None:
    """Attach ownership context by exact native metric id and benchmark token.

    Only ledger-backed objectives (those carrying an accepted deficit
    selector) are linked, the objective benchmark label must begin with the
    catalog benchmark id, and the native metric id must match exactly.
    Linkage never affects ranking, eligibility or gaps. It is annotated as a
    label match so the viewer can show it as ownership context, not evidence.
    """
    for item in items:
        if not _text(item.get("deficit_selector")):
            continue
        metric_tokens = {_norm(part) for part in str(item["metric"]).replace(" and ", "/").split("/")}
        bench_norm = _norm(item["benchmark"])
        plane = None
        for candidate in ("session", "turn"):
            if candidate in str(item["benchmark"]).lower().split():
                plane = candidate
        for row in rows:
            if _norm(row["metric_id"]) not in metric_tokens:
                continue
            if not bench_norm.startswith(_norm(row["benchmark_id"])):
                continue
            if plane and plane not in str(row["task_profile"]).lower():
                continue
            item["linked_metric_keys"].append(row["metric_key"])
            row["objectives"].append({
                "id": item["id"], "group": item["group"], "owners": list(item["owners"]),
                "linkage": "label_match",
            })
        item["linked_metric_keys"] = sorted(set(item["linked_metric_keys"]))


def build_frontier_leaderboard(
    catalog: Mapping[str, Any],
    objectives: Mapping[str, Any] | None = None,
    objectives_status: str = "absent",
    objectives_source: str | None = None,
) -> dict[str, Any]:
    """Project all F1 metric definitions plus exact accepted comparison rows.

    Rows outside same-harness evidence remain visible but ineligible. The F1
    catalog snapshot remains the sole identity of this projection. A frontier
    objectives registry is optional ownership context: ``absent`` when not
    supplied, ``draft`` when read from an unmerged source, ``canonical`` only
    when read from the committed repository data path.
    """
    if not isinstance(catalog, dict) or not isinstance(catalog.get("snapshot"), dict):
        raise FrontierProjectionError("missing versioned F1 catalog snapshot")
    snapshot_meta = catalog["snapshot"]
    snapshot = snapshot_meta.get("id")
    if not isinstance(snapshot, str) or not snapshot:
        raise FrontierProjectionError("snapshot identity is required")
    if catalog.get("aggregate_score") not in (None, "not_defined"):
        raise FrontierProjectionError("catalog carries an aggregate score; refusing projection")
    runs: dict[str, dict[str, Any]] = {}
    for r in catalog.get("runs", []):
        if isinstance(r, dict) and isinstance(r.get("run_id"), str):
            if r["run_id"] in runs:
                raise FrontierProjectionError("duplicate run identity in catalog")
            runs[r["run_id"]] = r
    comparisons = []
    seen_sets: set[str] = set()
    for comparison in catalog.get("comparison_sets", []):
        if not isinstance(comparison, dict) or not _text(comparison.get("comparison_set_id")):
            raise FrontierProjectionError("comparison set without exact identity")
        if comparison["comparison_set_id"] in seen_sets:
            raise FrontierProjectionError("duplicate comparison set identity")
        seen_sets.add(comparison["comparison_set_id"])
        if not isinstance(comparison.get("comparison_identity"), dict):
            raise FrontierProjectionError("comparison identity missing")
        comparisons.append(comparison)
    comparisons.sort(key=lambda item: item["comparison_set_id"])
    currency = _currency(comparisons, runs)
    rows = []
    for comparison in comparisons:
        for dimension, content in sorted(comparison.get("dimensions", {}).items()):
            if not isinstance(content, dict):
                raise FrontierProjectionError("malformed scorecard dimension")
            metrics = content.get("rows", [])
            if not isinstance(metrics, list) or any(
                not isinstance(m, dict) or not _text(m.get("metric_id")) for m in metrics
            ):
                raise FrontierProjectionError("scorecard row without exact metric identity")
            for metric in sorted(metrics, key=lambda x: x["metric_id"]):
                row = _result(comparison, dimension, metric, runs)
                row["currency"] = dict(currency[comparison["comparison_set_id"]])
                rows.append(row)
    # Coverage must reflect actual numeric eligibility, not merely the
    # presence of a record labelled same_harness. An invalid or missing
    # comparison is a gap, never a completed comparison.
    best_state: dict[str, str] = {}
    priority = {s: i for i, s in enumerate(RANKING_STATES)}
    for row in rows:
        key = row["metric_key"]
        if key not in best_state or priority[row["ranking_state"]] < priority[best_state[key]]:
            best_state[key] = row["ranking_state"]
    coverage = []
    for metric in sorted(catalog.get("metrics", []), key=lambda x: x["metric_key"]):
        key = metric["metric_key"]
        state = best_state.get(key)
        coverage.append({
            "metric_key": key,
            "benchmark_profile_id": metric["benchmark_profile_id"],
            "dimension": metric["dimension"],
            "metric_id": metric["metric_id"],
            "state": "has_accepted_comparison" if state == "ranked" else "no_accepted_comparison",
            "best_ranking_state": state if state is not None else "no_comparison_row",
            "gap_to_leader_native": None,
        })

    if objectives_status not in OBJECTIVE_REGISTRY_STATES:
        raise FrontierProjectionError("unknown objectives registry status")
    if objectives is None:
        objective_block: dict[str, Any] = {
            "state": "absent", "source": None, "sha256": None,
            "schema_version": None, "families": dict(CAPABILITY_FAMILIES),
            "families_without_objective": sorted(CAPABILITY_FAMILIES),
            "items": [], "note": "no objectives registry supplied; ownership context unavailable",
        }
    else:
        if objectives_status == "absent":
            raise FrontierProjectionError("objectives supplied without draft/canonical status")
        validated = validate_objectives(objectives)
        _link_objectives(rows, validated["items"])
        digest = hashlib.sha256(
            json.dumps(objectives, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        objective_block = {
            "state": objectives_status, "source": objectives_source, "sha256": digest,
            "schema_version": validated["schema_version"],
            "families": validated["families"],
            "families_without_objective": validated["families_without_objective"],
            "items": validated["items"],
            "note": (
                "draft registry from an unmerged source; ownership context only"
                if objectives_status == "draft"
                else "registry read from the committed repository data path"
            ),
        }

    published = []
    for ref in catalog.get("published_references", []):
        if not isinstance(ref, dict):
            raise FrontierProjectionError("malformed published reference")
        published.append({
            "system": ref.get("system"),
            "evidence_class": "published_reference",
            "eligible_for_numeric_delta": False,
            "methodology": ref.get("methodology"),
            "source": ref.get("source"),
            "signals": dict(ref.get("signals", {})) if isinstance(ref.get("signals"), dict) else {},
            "ranked": False,
        })
    same_harness_external = sorted({
        sid for row in rows if row["evidence_class"] == "same_harness"
        for sid in row["peer_population"]["external_competitors"]
    })
    summary_rank = {state: 0 for state in RANKING_STATES}
    summary_comp = {state: 0 for state in COMPETITIVE_STATES}
    summary_currency = {state: 0 for state in CURRENCY_STATES}
    for row in rows:
        summary_rank[row["ranking_state"]] += 1
        if row["competitive_state"]:
            summary_comp[row["competitive_state"]] += 1
        summary_currency[row["currency"]["state"]] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": snapshot,
        "snapshot": {
            "id": snapshot,
            "as_of": snapshot_meta.get("as_of"),
            "dashboard_id": snapshot_meta.get("dashboard_id"),
            "evidence_revision": snapshot_meta.get("evidence_revision"),
            "repository_is_newer": snapshot_meta.get("repository_is_newer"),
            "source_identity": dict(snapshot_meta.get("source_identity", {}))
            if isinstance(snapshot_meta.get("source_identity"), dict) else {},
            "catalog_schema_version": catalog.get("schema_version"),
        },
        "authority_effect": "none",
        "aggregate_score": None,
        "comparison_classes": dict(catalog.get("comparison_classes", {}))
        if isinstance(catalog.get("comparison_classes"), dict) else {},
        "reading_rules": list(catalog.get("reading_rules", [])),
        "vocabulary": {
            "ranking_states": list(RANKING_STATES),
            "competitive_states": list(COMPETITIVE_STATES),
            "currency_states": list(CURRENCY_STATES),
            "roles": ["subject", "external_competitor", "control", "unclassified"],
        },
        "summary": {
            "metric_rows_total": len(rows),
            "metric_definitions_total": len(coverage),
            "ranking_states": summary_rank,
            "competitive_states": summary_comp,
            "currency_states": summary_currency,
            "note": "counts with denominators; not a score and not an average",
        },
        "leaderboards": rows,
        "metric_coverage": coverage,
        "external_competitors": {
            "same_harness_measured": same_harness_external,
            "published_only": sorted({
                str(p["system"]) for p in published if p.get("system") is not None
            }),
        },
        "published_references": published,
        "published_reference_count_unranked": len(published),
        "objectives": objective_block,
    }
