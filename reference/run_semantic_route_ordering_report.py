#!/usr/bin/env python3
"""Ordering-difference report for the semantic vector route under ranking policy 3.2.0 (#669, LD7).

Runs the repository's currentness fixtures twice through the public facade:

* the #584 unknown-basis ordering contract (M1..M15; with any memory-level temporal
  declarations, explicit intent and reference time each case carries);
* every #580 temporal-currentness gauntlet case (its own scorer, units and order digests);
* MESA-M4-shaped independent old/new pairs (the five upstream conflict templates; the
  template strings are synthetic, not MemDialogue data).

Once with ``semantic_retrieval="off"`` and once with the real pinned provider
(``"required"``). Every ordering difference is listed. A required #580 unit or a #584
expectation that changes status is a blocker under the #669 plan, not something to
re-pin. Requires the optional extra ``semantic`` and the pinned model
(``$AGENT_MEMORY_REPRESENTATION_DIR``).
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

from agentmem_ref.api import surface  # noqa: E402
from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.evaluation import temporal_currentness as tc  # noqa: E402

CONTRACT_584 = REFERENCE / "fixtures" / "runtime" / "temporal-unknown-basis-ordering-v1.json"
SUITE_580 = REFERENCE / "fixtures" / "benchmarks" / "temporal-currentness" / "temporal-currentness-gauntlet-v1.json"
CONFLICT_TEMPLATES = (
    ("location", "The user currently lives in {old}.", "The user has moved and now lives in {new}.", "Where does the user currently live?"),
    ("role", "The user works as a {old}.", "The user changed jobs and now works as a {new}.", "What is the user's current job?"),
    ("preference", "The user prefers {old}.", "The user's preference changed; they now prefer {new}.", "What does the user currently prefer?"),
    ("status", "The project status is {old}.", "The project status has changed to {new}.", "What is the project's current status?"),
    ("numeric", "The project budget is {old} dollars.", "The updated project budget is {new} dollars.", "What is the current project budget?"),
)


@contextmanager
def semantic_mode(mode: str):
    """Force every facade open in this process to ``mode`` (report-only harness switch)."""

    original = surface._semantic_route

    def forced(root, _mode, representation_dir):
        return original(root, mode, representation_dir)

    surface._semantic_route = forced
    try:
        yield
    finally:
        surface._semantic_route = original


def _584_runs(case: dict) -> list[tuple[str, str, dict | None]]:
    if "query" in case:
        return [(case["id"], case["query"], case.get("temporal_intent"))]
    return [(f"{case['id']}/{key}", variant["query"], variant.get("temporal_intent"))
            for key, variant in sorted(case.items()) if key.endswith("_variant")]


def run_584() -> dict:
    fixture = json.loads(CONTRACT_584.read_text(encoding="utf-8"))
    out = {}
    for case in fixture["cases"]:
        if "memories" not in case:  # policy-level cases (no facade memories) are listed, not run
            out[case["id"]] = {"skipped": "policy-level case without facade memories", "admitted": None}
            continue
        for run_id, query, intent in _584_runs(case):
            memory = AgentMemory.open(tempfile.mkdtemp())
            try:
                keys = {}
                for index, item in enumerate(case["memories"]):
                    kwargs = {k: item[k] for k in ("valid_from", "valid_until", "observed_at") if k in item}
                    result = memory.remember(f"memory:584:{index}", item["text"], **kwargs)
                    keys[result["fact_uuid"]] = item["key"]
                recall = memory.recall(query, temporal_intent=intent, reference_time=case.get("reference_time"))
                out[run_id] = {
                    "admitted": [keys.get(ref, f"other:{ref}") for ref in recall["admitted"]],
                    "ordered_before_next_by": [
                        recall["admissions"][ref].get("ranking_evidence", {}).get("ordered_before_next_by")
                        for ref in recall["admitted"]],
                    "routes": {keys.get(ref, ref): sorted(h["route_id"] for h in recall["admissions"][ref]["route_provenance"])
                               for ref in recall["admitted"]},
                }
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
        "observations": {f"{row['case_id']}/{row['probe_id']}": {
            "admitted": row["observation"]["admitted"],
            "candidates": row["observation"]["candidates"],
            "ordered_before_next_by": {key: value["ordered_before_next_by"]
                                       for key, value in row["observation"]["per_key"].items()},
        } for row in result["rows"]},
    }


def run_m4(pairs: int = 50) -> dict:
    out = {}
    memory = AgentMemory.open(tempfile.mkdtemp(), tenant="tenant:m4", scope="benchmark:m4")
    try:
        for index in range(pairs):
            category, old_t, new_t, query = CONFLICT_TEMPLATES[index % len(CONFLICT_TEMPLATES)]
            scope = f"user:conflict_{index:05d}"
            domains = ["tenant:m4", scope]
            overrides = {"scope": scope, "isolation_domain_refs": domains,
                         "required_isolation_domain_refs": domains, "project_ref": scope}
            old = memory.remember(f"memory:m4:{index}:old", old_t.format(old=f"OLD_{category}_{index:04d}"),
                                  overrides=overrides)["fact_uuid"]
            new = memory.remember(f"memory:m4:{index}:new", new_t.format(new=f"NEW_{category}_{index:04d}"),
                                  overrides=overrides)["fact_uuid"]
            recall = memory.recall(query, target_domain_refs=domains, project_ref=scope, budget=1)
            top = recall["returned"][0] if recall["returned"] else None
            out[f"{category}/{index}"] = "new" if top == new else "old" if top == old else "neither"
    finally:
        memory.close()
    return out


def compare(off: dict, on: dict) -> dict:
    diff_584 = {case: {"off": off["584"][case], "on": on["584"][case]}
                for case in off["584"] if off["584"][case]["admitted"] != on["584"][case]["admitted"]}
    unit_changes = {unit: {"off": status, "on": on["580"]["units"].get(unit)}
                    for unit, status in off["580"]["units"].items() if on["580"]["units"].get(unit) != status}
    order_changes = {key: {"off": off["580"]["observations"][key], "on": on["580"]["observations"][key]}
                     for key, digest in sorted(off["580"]["orders"].items()) if on["580"]["orders"].get(key) != digest}
    m4_changes = {pair: {"off": outcome, "on": on["m4"][pair]} for pair, outcome in off["m4"].items()
                  if on["m4"][pair] != outcome}
    required_unit_changes = {unit: change for unit, change in unit_changes.items() if "/required/" in f"/{unit}/"}
    return {
        "584_admitted_order_changes": diff_584,
        "580_unit_status_changes": unit_changes,
        "580_required_unit_status_changes": required_unit_changes,
        "580_order_digest_changes": order_changes,
        "m4_top1_changes": m4_changes,
        "m4_new_fact_rate": {"off": sum(v == "new" for v in off["m4"].values()) / len(off["m4"]),
                             "on": sum(v == "new" for v in on["m4"].values()) / len(on["m4"])},
        "580_metrics": {"off": off["580"]["metrics"], "on": on["580"]["metrics"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = {}
    for mode in ("off", "required"):
        with semantic_mode(mode):
            results[mode] = {"584": run_584(), "580": run_580(), "m4": run_m4()}
    probe = AgentMemory.open(tempfile.mkdtemp(), semantic_retrieval="required")
    posture = probe.semantic_retrieval_posture()
    probe.close()
    report = {
        "report": "semantic-route-ordering-difference-669",
        "ranking_policy": "multi-route-default 3.2.0 (semantic_vector subordinate)",
        "representation": posture["representation"],
        "minimum_similarity": posture["minimum_similarity"],
        "comparison": compare(results["off"], results["required"]),
        "authority_effect": "none",
    }
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    comparison = report["comparison"]
    print(json.dumps({key: (len(value) if isinstance(value, (dict, list)) else value)
                      for key, value in comparison.items() if key != "580_metrics"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
