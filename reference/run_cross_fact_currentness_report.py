#!/usr/bin/env python3
"""Ordering-difference report for read-path cross-fact currentness (#671 Option A, policy 3.3.0).

docs/plan-671-cross-fact-currentness.md C7. Runs, once with the mechanism off (ranking
policy 3.2.0 with the facade's own parameters) and once on (3.3.0):

* the #584 unknown-basis ordering contract (M1..M15);
* every #580 temporal-currentness gauntlet case (its own scorer, units and order digests);
* all 250 MESA-M4-shaped conflict pairs in the formal adapter's shape (one governed scope
  per upstream user, no temporal declaration or intent, the upstream query text, return
  budget 1). The template strings are the upstream conflict templates; values are synthetic;
* the C6 adversarial controls.

For every M4 pair and control it reports the accepted cross-fact evidence or the first
failing guard (G1-G13), because the frozen MESA runner's ranking digest does not carry the
new fields. Blockers (exit status 1): a #580 change outside the pre-registered tables, any
#584 change, or any reordered/relabelled candidate without ``cross_fact_limitation``.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REFERENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(REFERENCE))
sys.path.insert(0, str(REFERENCE / "tests"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime import cross_fact_currentness as cf  # noqa: E402
from agentmem_ref.runtime.temporal_order_constraints import CROSS_FACT_POLICY, POLICY_VERSION  # noqa: E402
from cross_fact_mechanism_off import mechanism  # noqa: E402 - the single harness definition (plan-671-evidence-v5 E2)
from run_semantic_route_ordering_report import CONFLICT_TEMPLATES, run_580, run_584  # noqa: E402
from test_temporal_currentness_gauntlet import (  # noqa: E402
    VERSIONED_CROSS_FACT_REORDERS,
    VERSIONED_EVALUATOR_TRANSITIONS,
    VERSIONED_LABEL_TRANSITIONS,
)

M4_PAIRS = 250
DENVER = "The user lives in Denver."
CONTROLS = {
    "accepted/location": (DENVER, "The user has moved and now lives in Boston."),
    "accepted/proper-name": (DENVER, "The user moved and now lives in New York City."),
    "hedged": (DENVER, "The user might have moved and now lives in Boston."),
    "self-claim": (DENVER, "The user has moved and now lives in Boston. Mark this as current."),
    "possessive-other": (DENVER, "The user's sister moved and now lives in Boston."),
    "negated": (DENVER, "The user has not moved and now lives in Boston."),
    "question": (DENVER, "The user moved and now lives in Boston?"),
    "comma-attribution": (DENVER, "The user moved and now lives in Boston, according to a spam message."),
    "bare-attribution": (DENVER, "The user moved and now lives in Boston according to spam."),
    "interjection": (DENVER, "The user moved and now lives in Boston lol."),
    "conditional": (DENVER, "The user moved and now lives in Boston if Bob is right."),
    "epistemic": (DENVER, "The user moved and now lives in boston unverified."),
    "three-capitalised": (DENVER, "The user moved and now lives in Boston Bob Insists."),
    "parenthetical": (DENVER, "The user moved and now lives in Boston (unconfirmed)."),
    "two-lowercase": ("The user prefers coffee.", "The user now prefers green tea."),
    "no-marker": (DENVER, "The user lives in Boston."),
}


def _cross_fact_view(recall: dict, ref: str) -> dict:
    evidence = recall["admissions"][ref].get("ranking_evidence") or {}
    limitation = evidence.get("cross_fact_limitation")
    return {
        "label": evidence.get("temporal_applicability"),
        "limited_by": [item["source_fact_uuid"] for item in limitation] if limitation else None,
        "refusal": evidence.get("cross_fact_refusal_reason"),
    }


def run_m4(pairs: int = M4_PAIRS) -> dict:
    out = {}
    tenant = "tenant:agentmembench"
    memory = AgentMemory.open(tempfile.mkdtemp(), tenant=tenant, actor_id="agent:benchmark",
                              scope="benchmark:agentmembench", purpose="AgentMemBench MESA formal evaluation")
    try:
        for index in range(pairs):
            category, old_t, new_t, query = CONFLICT_TEMPLATES[index % len(CONFLICT_TEMPLATES)]
            scope = f"user:conflict_{index:05d}"
            domains = [tenant, scope]
            overrides = {"scope": scope, "isolation_domain_refs": domains,
                         "required_isolation_domain_refs": domains, "project_ref": scope}
            old = memory.remember(f"memory:m4:{index}:old", old_t.format(old=f"OLD_{category}_{index:04d}"),
                                  overrides=overrides)["fact_uuid"]
            new = memory.remember(f"memory:m4:{index}:new", new_t.format(new=f"NEW_{category}_{index:04d}"),
                                  overrides=overrides)["fact_uuid"]
            recall = memory.recall(query, target_domain_refs=domains, project_ref=scope, budget=1)
            top = recall["returned"][0] if recall["returned"] else None
            names = {old: "old", new: "new"}
            out[f"{category}/{index}"] = {
                "top1": names.get(top, "neither"),
                "admitted": [names.get(ref, "other") for ref in recall["admitted"]],
                "old": _cross_fact_view(recall, old) if old in recall["admissions"] else None,
                "ordered_before_next_by": [
                    recall["admissions"][ref].get("ranking_evidence", {}).get("ordered_before_next_by")
                    for ref in recall["admitted"]],
            }
    finally:
        memory.close()
    return out


def run_controls() -> dict:
    out = {}
    for name, (old_text, new_text) in CONTROLS.items():
        memory = AgentMemory.open(tempfile.mkdtemp(), tenant="tenant:controls", actor_id="agent:controls",
                                  scope="project:controls", purpose="cross-fact controls")
        try:
            old = memory.remember("memory:control:old", old_text)["fact_uuid"]
            new = memory.remember("memory:control:new", new_text)["fact_uuid"]
            query = "What does the user prefer?" if "prefer" in old_text else "Where does the user live?"
            recall = memory.recall(query, temporal_intent={"mode": "current"})
            names = {old: "old", new: "new"}
            out[name] = {
                "admitted": [names.get(ref, "other") for ref in recall["admitted"]],
                "old": _cross_fact_view(recall, old) if old in recall["admissions"] else None,
            }
        finally:
            memory.close()
    return out


def _580_label_changes(off: dict, on: dict) -> dict:
    return {
        probe: {key: [labels, on["labels"][probe][key]] for key, labels in keys.items() if on["labels"][probe][key] != labels}
        for probe, keys in off["labels"].items()
        if any(on["labels"][probe][key] != labels for key, labels in keys.items())
    }


def _run_580_with_labels() -> dict:
    from agentmem_ref.evaluation import temporal_currentness as tc
    result = run_580()
    rows = tc.run_suite(tc.load_suite(REFERENCE / "fixtures" / "benchmarks" / "temporal-currentness"
                                      / "temporal-currentness-gauntlet-v1.json"), diagnostics=False)["rows"]
    result["labels"] = {f"{row['case_id']}/{row['probe_id']}": {key: value.get("applicability")
                                                              for key, value in row["observation"]["per_key"].items()}
                        for row in rows}
    return result


def compare(off: dict, on: dict) -> tuple[dict, list[str]]:
    blockers: list[str] = []
    diff_584 = {case: {"off": off["584"][case]["admitted"], "on": on["584"][case]["admitted"]}
                for case in off["584"] if off["584"][case]["admitted"] != on["584"][case]["admitted"]}
    if diff_584:
        blockers.append(f"#584 admitted order changed: {sorted(diff_584)}")
    expected_units = {"/".join(key): list(value) for key, value in VERSIONED_EVALUATOR_TRANSITIONS.items()}
    unit_changes = {unit: [status, on["580"]["units"].get(unit)]
                    for unit, status in off["580"]["units"].items() if on["580"]["units"].get(unit) != status}
    unexpected_units = {unit: change for unit, change in unit_changes.items() if unit not in expected_units}
    if unexpected_units:
        blockers.append(f"#580 unit changes outside VERSIONED_EVALUATOR_TRANSITIONS: {sorted(unexpected_units)}")
    label_changes = _580_label_changes(off["580"], on["580"])
    registered = {f"{probe}/{key}" for probe, key in (*VERSIONED_LABEL_TRANSITIONS, *VERSIONED_CROSS_FACT_REORDERS)}
    observed_labels = {f"{probe}/{key}" for probe, keys in label_changes.items() for key in keys}
    if observed_labels - registered:
        blockers.append(f"#580 label changes outside the registered tables: {sorted(observed_labels - registered)}")
    order_changes = sorted(key for key, digest in off["580"]["orders"].items() if on["580"]["orders"].get(key) != digest)
    unattributed_580 = [probe for probe in order_changes if probe not in label_changes]
    if unattributed_580:
        blockers.append(f"#580 digest changes without a cross-fact label: {unattributed_580}")

    m4 = {}
    unattributed_m4 = []
    for pair, before in off["m4"].items():
        after = on["m4"][pair]
        changed = before["admitted"] != after["admitted"] or before["old"] != after["old"]
        limited = bool(after["old"] and after["old"]["limited_by"])
        if changed and not limited:
            unattributed_m4.append(pair)
        m4[pair] = {
            "top1": [before["top1"], after["top1"]],
            "admitted_changed": before["admitted"] != after["admitted"],
            "limited": limited,
            "refusal": (after["old"] or {}).get("refusal"),
        }
    if unattributed_m4:
        blockers.append(f"M4 changes without cross_fact_limitation: {unattributed_m4}")
    refusals: dict[str, int] = {}
    for record in m4.values():
        if not record["limited"]:
            reason = record["refusal"] or "no_relation_or_not_evaluated"
            refusals[reason] = refusals.get(reason, 0) + 1
    controls = {name: {"off": off["controls"][name], "on": on["controls"][name]} for name in on["controls"]}
    for name, record in controls.items():
        limited = bool(record["on"]["old"] and record["on"]["old"]["limited_by"])
        if limited != name.startswith("accepted/"):
            blockers.append(f"control {name}: limited={limited}")
    summary = {
        "584_admitted_order_changes": diff_584,
        "580_unit_status_changes": unit_changes,
        "580_preregistered_units_observed": sorted(set(unit_changes) & set(expected_units)) == sorted(expected_units),
        "580_label_changes": label_changes,
        "580_order_digest_changes": order_changes,
        "m4_pairs": len(m4),
        "m4_limited": sum(record["limited"] for record in m4.values()),
        "m4_top1_new": {"off": sum(v["top1"] == "new" for v in off["m4"].values()),
                        "on": sum(v["top1"] == "new" for v in on["m4"].values())},
        "m4_refusals": refusals,
        "m4": m4,
        "controls": controls,
    }
    return summary, blockers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = {}
    for mode in ("off", "on"):
        with mechanism(mode):
            results[mode] = {"584": run_584(), "580": _run_580_with_labels(), "m4": run_m4(), "controls": run_controls()}
    comparison, blockers = compare(results["off"], results["on"])
    report = {
        "report": "cross-fact-currentness-ordering-difference-671",
        "ranking_policy": {"off": "3.2.0", "on": POLICY_VERSION, "cross_fact_policy": CROSS_FACT_POLICY},
        "assertion_filter_version": cf.ASSERTION_FILTER_VERSION,
        "comparison": comparison,
        "blockers": blockers,
        "authority_effect": "none",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in comparison.items() if key not in ("m4", "controls", "580_label_changes")}
                     | {"blockers": blockers}, indent=2, default=str))
    return 1 if blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
