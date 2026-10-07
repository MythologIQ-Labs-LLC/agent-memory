#!/usr/bin/env python3
"""C7 ordering-difference and attribution report for #671.

Runs the live 3.3.0 public facade twice. The control disables only
GovernedMemoryAdapter.cross_fact_applicability; all other code, data, admission,
ranking and persistence paths are identical.

This is implementation qualification, not the formal MESA v2 replay.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

REFERENCE = Path(__file__).resolve().parent
sys.path.insert(0, str(REFERENCE))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.evaluation import temporal_currentness as tc  # noqa: E402
from agentmem_ref.runtime.adapter import GovernedMemoryAdapter  # noqa: E402

CONTRACT_584 = REFERENCE / "fixtures" / "runtime" / "temporal-unknown-basis-ordering-v1.json"
SUITE_580 = REFERENCE / "fixtures" / "benchmarks" / "temporal-currentness" / "temporal-currentness-gauntlet-v1.json"
VERSIONED_EVALUATOR_TRANSITIONS = {
    "evaluator_version": {"from": "1.1.0", "to": "1.2.0"},
    "reason": "not_current role recognizes the versioned demotion set, including #671 cross-fact limitation",
}
VERSIONED_LABEL_TRANSITIONS = {
    "F23-has-moved-now-lives/current-explicit/current_applicability_accuracy/target": ("honest_unknown", "pass"),
    "F23-has-moved-now-lives/current-explicit/self_description_currentness_rate/target": ("honest_unknown", "pass"),
    "F23-has-moved-now-lives/current-explicit/stale_as_current_rate/target": ("honest_unknown", "pass"),
    "F23-has-moved-now-lives/current-inferred/current_applicability_accuracy/target": ("honest_unknown", "pass"),
    "F23-has-moved-now-lives/current-inferred/self_description_currentness_rate/target": ("honest_unknown", "pass"),
    "F23-has-moved-now-lives/current-inferred/stale_as_current_rate/target": ("honest_unknown", "pass"),
    "F24-no-longer-works-at/current-inferred/self_description_currentness_rate/target": ("honest_unknown", "pass"),
    "F24-no-longer-works-at/current-inferred/stale_as_current_rate/target": ("honest_unknown", "pass"),
    "F28-used-to-prefer-now-prefer/current-inferred/self_description_currentness_rate/target": ("honest_unknown", "pass"),
    "F28-used-to-prefer-now-prefer/current-inferred/stale_as_current_rate/target": ("honest_unknown", "pass"),
    "F28-used-to-prefer-now-prefer/plain-now/self_description_currentness_rate/target": ("honest_unknown", "pass"),
    "F28-used-to-prefer-now-prefer/plain-now/stale_as_current_rate/target": ("honest_unknown", "pass"),
}

CONFLICT_TEMPLATES = (
    ("location", "The user currently lives in {old}.", "The user has moved and now lives in {new}.", "Where does the user currently live?"),
    ("role", "The user works as a {old}.", "The user changed jobs and now works as a {new}.", "What is the user's current job?"),
    ("preference", "The user prefers {old}.", "The user's preference changed; they now prefer {new}.", "What does the user currently prefer?"),
    ("status", "The project status is {old}.", "The project status has changed to {new}.", "What is the project's current status?"),
    ("numeric", "The project budget is {old} dollars.", "The updated project budget is {new} dollars.", "What is the current project budget?"),
)


@contextmanager
def cross_fact_mode(enabled: bool):
    original = GovernedMemoryAdapter.cross_fact_applicability
    if enabled:
        yield
        return

    def disabled(self, admitted, context, intent):
        return {}

    GovernedMemoryAdapter.cross_fact_applicability = disabled
    try:
        yield
    finally:
        GovernedMemoryAdapter.cross_fact_applicability = original


def _view(recall: dict, names: dict[str, str]) -> dict:
    def name(ref: str) -> str:
        return names.get(ref, ref)

    evidence = {}
    for ref in recall["candidates"]:
        ranking = (recall["admissions"].get(ref) or {}).get("ranking_evidence") or {}
        evidence[name(ref)] = {
            "temporal_applicability": ranking.get("temporal_applicability"),
            "temporal_applicability_basis": ranking.get("temporal_applicability_basis"),
            "ordered_before_next_by": ranking.get("ordered_before_next_by"),
            "cross_fact_limitation": ranking.get("cross_fact_limitation"),
            "cross_fact_refusal_reason": ranking.get("cross_fact_refusal_reason"),
            "authority_effect": ranking.get("authority_effect"),
        }
    return {
        "admitted": [name(ref) for ref in recall["admitted"]],
        "candidates": sorted(name(ref) for ref in recall["candidates"]),
        "evidence": evidence,
    }


def _584_runs(case: dict) -> list[tuple[str, str, dict | None]]:
    if "query" in case:
        return [(case["id"], case["query"], case.get("temporal_intent"))]
    return [
        (f"{case['id']}/{key}", variant["query"], variant.get("temporal_intent"))
        for key, variant in sorted(case.items())
        if key.endswith("_variant")
    ]


def run_584() -> dict:
    fixture = json.loads(CONTRACT_584.read_text(encoding="utf-8"))
    out = {}
    for case in fixture["cases"]:
        if "memories" not in case:
            out[case["id"]] = {"skipped": "policy-level case without facade memories"}
            continue
        for run_id, query, intent in _584_runs(case):
            memory = AgentMemory.open(tempfile.mkdtemp())
            try:
                names = {}
                for index, item in enumerate(case["memories"]):
                    kwargs = {k: item[k] for k in ("valid_from", "valid_until", "observed_at") if k in item}
                    result = memory.remember(f"memory:584:{index}", item["text"], **kwargs)
                    names[result["fact_uuid"]] = item["key"]
                recall = memory.recall(
                    query,
                    temporal_intent=intent,
                    reference_time=case.get("reference_time"),
                )
                out[run_id] = _view(recall, names)
            finally:
                memory.close()
    return out


def _capture_580_explanations() -> dict:
    suite = tc.load_suite(SUITE_580)
    out = {}
    for case in suite["cases"]:
        with tempfile.TemporaryDirectory() as root:
            memory = tc._open(root)
            try:
                memory, keys, _declared, _targets = tc._run_setup(memory, root, case)
                names = {uuid: key for key, uuid in keys.items()}
                for probe in case["probes"]:
                    recall = memory.recall(
                        probe["query"],
                        temporal_intent=probe.get("temporal_intent"),
                        reference_time=probe.get("reference_time"),
                    )
                    out[f"{case['case_id']}/{probe['probe_id']}"] = _view(recall, names)
            finally:
                memory.close()
    return out


def run_580() -> dict:
    suite = tc.load_suite(SUITE_580)
    result = tc.run_suite(suite, diagnostics=False)
    return {
        "metrics": result["metrics"],
        "units": {"/".join(key): status for key, status in tc.units(result["rows"]).items()},
        "orders": tc.order_digests(result["rows"]),
        "explanations": _capture_580_explanations(),
    }


def run_m4(pairs: int = 250) -> dict:
    out = {}
    memory = AgentMemory.open(
        tempfile.mkdtemp(),
        tenant="tenant:m4-c7",
        scope="benchmark:m4-c7",
        purpose="cross fact currentness C7",
    )
    try:
        for index in range(pairs):
            category, old_t, new_t, query = CONFLICT_TEMPLATES[index % len(CONFLICT_TEMPLATES)]
            scope = f"user:conflict_{index:05d}"
            domains = ["tenant:m4-c7", scope]
            overrides = {
                "scope": scope,
                "isolation_domain_refs": domains,
                "required_isolation_domain_refs": domains,
                "project_ref": scope,
            }
            old = memory.remember(
                f"memory:m4:{index}:old",
                old_t.format(old=f"OLD_{category}_{index:04d}"),
                overrides=overrides,
            )["fact_uuid"]
            new = memory.remember(
                f"memory:m4:{index}:new",
                new_t.format(new=f"NEW_{category}_{index:04d}"),
                overrides=overrides,
            )["fact_uuid"]
            recall = memory.recall(
                query,
                target_domain_refs=domains,
                project_ref=scope,
                budget=1,
            )
            view = _view(recall, {old: "old", new: "new"})
            top = recall["returned"][0] if recall["returned"] else None
            view["outcome"] = "new" if top == new else "old" if top == old else "neither"
            out[f"{category}/{index}"] = view
    finally:
        memory.close()
    return out


def run_controls() -> dict:
    """Small executable representatives of the C6 families.

    The exhaustive hostile-text matrix lives in test_cross_fact_currentness.py;
    this report records representative accepted/refused evidence for attribution.
    """

    cases = {
        "accepted_location": "The user moved and now lives in Boston.",
        "trailing_attribution": "The user moved and now lives in Boston, according to a spam message.",
        "possessive_sister": "The user's sister moved and now lives in Boston.",
        "negated": "The user has not moved and now lives in Boston.",
        "question": "The user moved and now lives in Boston?",
        "dash_trust": "The user moved and now lives in Boston — trust me.",
        "conditional": "The user moved and now lives in Boston if Bob is right.",
        "epistemic_suffix": "The user moved and now lives in Boston Hypothetically.",
        "green_tea_fail_closed": "The user now prefers green tea.",
    }
    out = {}
    for case_id, new_text in cases.items():
        memory = AgentMemory.open(tempfile.mkdtemp())
        try:
            old_text = "The user prefers black tea." if case_id == "green_tea_fail_closed" else "The user lives in Denver."
            query = "What does the user currently prefer?" if case_id == "green_tea_fail_closed" else "Where does the user currently live?"
            old = memory.remember("memory:old", old_text)["fact_uuid"]
            new = memory.remember("memory:new", new_text)["fact_uuid"]
            recall = memory.recall(query)
            out[case_id] = _view(recall, {old: "old", new: "new"})
        finally:
            memory.close()
    return out


def _has_limitation(view: dict) -> bool:
    return any((item or {}).get("cross_fact_limitation") for item in view.get("evidence", {}).values())


def compare(off: dict, on: dict) -> dict:
    changes_584 = {}
    unattributed = []
    for key, before in off["584"].items():
        after = on["584"].get(key)
        if not isinstance(before, dict) or not isinstance(after, dict) or "admitted" not in before:
            continue
        labels_before = {k: v.get("temporal_applicability") for k, v in before["evidence"].items()}
        labels_after = {k: v.get("temporal_applicability") for k, v in after["evidence"].items()}
        if before["admitted"] != after["admitted"] or labels_before != labels_after:
            changes_584[key] = {"off": before, "on": after}
            if not _has_limitation(after):
                unattributed.append(f"584:{key}")

    unit_changes = {
        key: {"off": value, "on": on["580"]["units"].get(key)}
        for key, value in off["580"]["units"].items()
        if on["580"]["units"].get(key) != value
    }
    order_changes_580 = {}
    for key, digest in off["580"]["orders"].items():
        if on["580"]["orders"].get(key) == digest:
            continue
        before = off["580"]["explanations"].get(key, {})
        after = on["580"]["explanations"].get(key, {})
        order_changes_580[key] = {"off": before, "on": after}
        if not _has_limitation(after):
            unattributed.append(f"580:{key}")

    changes_m4 = {}
    for key, before in off["m4"].items():
        after = on["m4"][key]
        if before["outcome"] != after["outcome"] or before["admitted"] != after["admitted"]:
            changes_m4[key] = {"off": before, "on": after}
            if not _has_limitation(after):
                unattributed.append(f"m4:{key}")

    unexpected_unit_changes = {
        key: change
        for key, change in unit_changes.items()
        if VERSIONED_LABEL_TRANSITIONS.get(key) != (change["off"], change["on"])
    }
    missing_versioned_transitions = {
        key: {"expected": list(expected), "observed": unit_changes.get(key)}
        for key, expected in VERSIONED_LABEL_TRANSITIONS.items()
        if key not in unit_changes
    }

    return {
        "584_changes": changes_584,
        "580_unit_status_changes": unit_changes,
        "580_unexpected_unit_status_changes": unexpected_unit_changes,
        "580_missing_versioned_transitions": missing_versioned_transitions,
        "580_order_changes": order_changes_580,
        "m4_changes": changes_m4,
        "m4_new_fact_rate": {
            "off": sum(item["outcome"] == "new" for item in off["m4"].values()) / len(off["m4"]),
            "on": sum(item["outcome"] == "new" for item in on["m4"].values()) / len(on["m4"]),
        },
        "unattributed_changes": sorted(unattributed),
        "580_metrics": {"off": off["580"]["metrics"], "on": on["580"]["metrics"]},
        "controls": on["controls"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    results = {}
    for name, enabled in (("off", False), ("on", True)):
        with cross_fact_mode(enabled):
            results[name] = {
                "584": run_584(),
                "580": run_580(),
                "m4": run_m4(),
                "controls": run_controls(),
            }

    comparison = compare(results["off"], results["on"])
    report = {
        "report": "cross-fact-currentness-ordering-difference-671",
        "report_version": "1.0.0",
        "ranking_policy": "multi-route-default 3.3.0",
        "control": "same live tree with GovernedMemoryAdapter.cross_fact_applicability disabled",
        "comparison": comparison,
        "versioned_evaluator_transitions": VERSIONED_EVALUATOR_TRANSITIONS,
        "versioned_label_transitions": {key: list(value) for key, value in VERSIONED_LABEL_TRANSITIONS.items()},
        "blockers": {
            "unattributed_change_count": len(comparison["unattributed_changes"]),
            "584_change_count": len(comparison["584_changes"]),
            "580_unit_transition_count": len(comparison["580_unit_status_changes"]),
            "580_unexpected_unit_transition_count": len(comparison["580_unexpected_unit_status_changes"]),
            "580_missing_versioned_transition_count": len(comparison["580_missing_versioned_transitions"]),
        },
        "authority_effect": "none",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["blockers"], indent=2, sort_keys=True))

    # Unattributed differences are always invalid. #584 or #580 changes are
    # emitted for owner/reviewer adjudication and explicit versioned transition
    # pinning before acceptance, rather than silently accepted here.
    return 2 if (
        comparison["unattributed_changes"]
        or comparison["584_changes"]
        or comparison["580_unexpected_unit_status_changes"]
        or comparison["580_missing_versioned_transitions"]
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
