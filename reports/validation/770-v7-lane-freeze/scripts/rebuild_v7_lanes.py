#!/usr/bin/env python3
"""Rebuild the two -v7 lanes from their accepted -v6 lanes (#770 independent repair).

Start from the -v6 lane read as frozen (accepted rows back to frozen without status_reason,
the v6 acceptance finding dropped) and apply exactly the identity-only list the -v5 to -v6
generation established: lane-level fields, the v7 posture in every Agent Memory row that
carries one, the control display name, a v7 sentence on the deferred shadow and semantic
reasons, and the LongMemEval dispatch unit. Identity values the #770 author chose (lane id,
frozen_on, owning issue, display name, dispatch unit, control posture) are read from the
committed -v7 file, never retyped. usage: rebuild_v7_lanes.py <repo_root>
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
lanes = root / "reference/agentmem_ref/evaluation/lanes"
DECLARATION = "reports/runtime/baseline-v7-declaration.json"
CHANGE = ("the eight protected blobs reports/runtime/baseline-v7-declaration.json declares (evidence sufficiency, the "
          "governed transition witness, the recall observation receipt, the runtime adapter and recall control); "
          "ranking policy 3.4.0, assertion filter 6.1.0 and public contract 1.6.0 are unchanged")
DEFERRED_SUFFIX = "; at -v7 (#770): deferral carried forward unchanged; this row is not executed under this lane"
DISCLOSURE = ("disclosure: non-importable local reproductions of this exact configuration at the v7 candidate b854d5e "
              "(#644 independent validation) were visible before this freeze; no frozen fact differs from -v6, so they "
              "could not shape any frozen choice, and they are not lane evidence")
SPEC = {
    "amb-precisionmembench-retrieval": {
        "unit": "case", "verdicts": 77, "baseline": "the BM25 baseline",
        "shadow": "agent-memory-shadow", "semantic_reason": "for the uv.lock conflict (plan-669-lanes-v3 D3, unchanged at -v6 and -v7)",
        "description": ("Eighth lane generation (#770): PrecisionMemBench single-turn belief-ID retrieval under the frozen "
                        "independent AMB harness, retrieval mode, no LLM anywhere, re-executing every executed row of "
                        "amb-precisionmembench-retrieval-v6 at a runtime revision in the declared transition to Runtime "
                        f"Baseline v7 ({CHANGE}). The Agent Memory control runs the facade default through the unchanged "
                        "bridge 0.4.0, which writes the cross-fact sidecar cross-fact.jsonl, and every case's harness fields "
                        "and cross-fact record must equal the accepted -v6 control. This lane is acceptance evidence "
                        "reports/runtime/baseline-v7-declaration.json names for the successor publication. No v7 score is "
                        "accepted and no -v6 acceptance transfers. The shadow, semantic-route and Hindsight rows are deferred."),
        "nct0": ("amb-precisionmembench-retrieval-v6 rows for the same system: the executing runtime (declared transition to "
                 f"Runtime Baseline v7: {CHANGE}) differs while the bridge blob (bridge 0.4.0) is unchanged, so rows are "
                 "re-executed under this lane, never copied forward; the control's relation to the -v6 control is equality "
                 "(#770: every case's correct, context and nine meta fields, and its cross-fact limited_count, "
                 "limited_document_ids and refusal_counts, equal -v6), not attribution, and is an acceptance check, not a "
                 "comparability claim"),
        "rule_note": ("the control row is held to the #770 equality rule against the accepted -v6 control: every case's "
                      "harness fields, and its cross-fact limited_count, limited_document_ids and refusal_counts, equal -v6; "
                      "any difference blocks Runtime Baseline v7 publication"),
    },
    "longmemeval-s-retrieval-parity": {
        "unit": "question", "verdicts": 1000, "baseline": "the lexical baseline",
        "shadow": "agent_memory_shadow", "semantic_reason": "(#770): unchanged from -v6, where its reason is recorded",
        "description": ("Eighth lane generation (#770): frozen LongMemEval_S retrieval parity, retrieval only, no LLM anywhere, "
                        "re-executing every executed row of longmemeval-s-retrieval-parity-v6 at a runtime revision in the "
                        f"declared transition to Runtime Baseline v7 ({CHANGE}). The Agent Memory control runs the facade "
                        "default; every question records its cross-fact limitation as at -v6, and every question's ranked_top, "
                        "metrics and cross-fact record must equal the accepted -v6 control. This lane is acceptance evidence "
                        "reports/runtime/baseline-v7-declaration.json names for the successor publication. No v7 score is "
                        "accepted and no -v6 acceptance transfers. The shadow, semantic-route and Hindsight rows are deferred."),
        "nct0": ("longmemeval-s-retrieval-parity-v6 rows for the same system: the executing runtime (declared transition to "
                 f"Runtime Baseline v7: {CHANGE}) differs while the runner blob is unchanged, so rows are re-executed under "
                 "this lane, never copied forward; the control's relation to the -v6 control is equality (#770: every "
                 "question's ranked_top, metrics and cross_fact limited_count, limited_item_ids and refusal_counts equal "
                 "-v6), not attribution, and is an acceptance check, not a comparability claim"),
        "rule_note": ("the control row is held to the #770 equality rule against the accepted -v6 control: every question's "
                      "ranked_top and metrics, and its cross_fact limited_count, limited_item_ids and refusal_counts, equal "
                      "-v6; any difference blocks Runtime Baseline v7 publication"),
    },
}

for family, spec in SPEC.items():
    v6 = json.loads((lanes / f"{family}-v6.json").read_text(encoding="utf-8"))
    staged = json.loads((lanes / f"{family}-v7.json").read_text(encoding="utf-8"))
    lane = copy.deepcopy(v6)
    lane["status"] = "frozen"
    for row in lane["systems"]:
        if row["status"] in {"executed", "accepted"}:
            row["status"] = "frozen"
            del row["status_reason"]
    lane["findings"] = [item for item in lane["findings"] if not item.startswith("accepted rows ")]
    for key in ("lane_id", "frozen_on", "owning_issue"):
        lane[key] = staged[key]
    lane["description"] = spec["description"]
    v6_rule = v6["freeze_rationale"][1]
    rule = (v6_rule.replace("(plan-732-evidence-v6 V6-E1)", "(#770)").replace("-v5", "-v6")
            .replace("blocks v6 publication", "blocks v7 publication"))
    assert "-v5" not in rule and "blocks v7 publication" in rule and f"{{EQUAL: {spec['verdicts']}}}" in rule
    lane["freeze_rationale"] = [
        (f"the -v6 lane is accepted and its control executed the declared transition to Runtime Baseline v6; #644 declared "
         f"a transition to Runtime Baseline v7 ({CHANGE}), so the executing runtime is new and needs a new lane id "
         "(change_rule; docs/67: a successor needs new lane ids)"),
        rule,
        (f"expected effect, recorded before any score under this lane: the declared v7 changes alter no ranking policy, "
         f"assertion filter or public contract version, so v7 is expected to be observationally identical to v6 and no "
         f"{spec['unit']} is expected to differ; up/down counts and the summary deltas are reported, never gated, and must "
         f"be zero; {DISCLOSURE}"),
        f"the {spec['shadow']} row stays deferred (#770): unchanged from -v6, where its reason is recorded; it is neither re-executed nor copied forward",
        f"the agent_memory_semantic row stays deferred {spec['semantic_reason']}",
        (f"{spec['baseline']} is re-executed and must equal -v6 exactly; the Mem0 row is re-executed, a difference from -v6 "
         "being an environment finding as at -v4 to -v6; accepted -v6 rows are never copied forward, and no -v7 row is "
         "accepted before its workflow-imported evidence is independently reviewed"),
    ]
    lane["comparability"]["not_comparable_to"][0] = spec["nct0"]
    lane["comparability"]["notes"][-2] = spec["rule_note"]
    lane["comparability"]["notes"][-1] = lane["comparability"]["notes"][-1].replace("the -v6 control", "the -v7 control")
    staged_rows = {row["provider_key"]: row for row in staged["systems"]}
    control_posture = next(row for row in staged["systems"] if row["role"] == "control")["configuration"]["runtime_baseline_posture"]
    blob = subprocess.run(["git", "hash-object", DECLARATION], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
    assert control_posture["declaration_blob"] == blob, (control_posture, blob)
    for row in lane["systems"]:
        configuration = row.get("configuration") or {}
        if "runtime_baseline_posture" in configuration:
            configuration["runtime_baseline_posture"] = dict(control_posture)
        if row["role"] == "control":
            row["display_name"] = staged_rows[row["provider_key"]]["display_name"]
        if row["status"] == "deferred" and row["provider_key"] in {spec["shadow"], "agent_memory_semantic"}:
            row["status_reason"] = row["status_reason"] + DEFERRED_SUFFIX
    if "dispatch_unit" in lane["execution"].get("environment", {}):
        lane["execution"]["environment"]["dispatch_unit"] = staged["execution"]["environment"]["dispatch_unit"]
    (lanes / f"{family}-v7.json").write_text(json.dumps(lane, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{family}-v7 rebuilt")
