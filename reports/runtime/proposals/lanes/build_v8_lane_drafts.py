#!/usr/bin/env python3
"""Derive DRAFT -v8 lane definitions from the frozen -v7 lanes (#786 successor preparation).

The frozen -v7 files are read, never written. Exactly the identity-only transformation
reports/validation/770-v7-lane-freeze/scripts/rebuild_v7_lanes.py established for v6 -> v7
is applied for v7 -> v8: lane id, owning issue, the change sentence, the runtime-baseline
posture in every Agent Memory row, the control display name, the deferred rows' sentence.
Every executed row goes back to ``pending`` (a successor needs new lane ids and no -v7
result transfers; docs/67). The drafts carry ``status: draft`` and are not registered,
not frozen and not lane evidence until the owner sanctions the v8 declaration.

usage: build_v8_lane_drafts.py <repo_root>
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
lanes = root / "reference/agentmem_ref/evaluation/lanes"
out = root / "reports/runtime/proposals/lanes"
DECLARATION = "reports/runtime/proposals/786-cumulative-v6-to-v8.PROPOSED.json"
declaration = json.loads((root / DECLARATION).read_text(encoding="utf-8"))
blob = subprocess.run(["git", "hash-object", DECLARATION], cwd=root, capture_output=True, text=True, check=True).stdout.strip()
n = len(declaration["declared_changes"])
deltas = ", ".join(f"{d['identity_path'].split('.', 1)[1]} {d['from']} -> {d['to']}" for d in declaration["identity_deltas"]) or "no identity delta"
CHANGE = (f"the {n} protected blobs {DECLARATION} declares (the cumulative #776/#777/#772/#774/#786/#802 runtime candidate: "
          f"fact-level deletion lineage, public deleted-identifier redaction, JSON checkpoint journal scaling, the strict "
          f"caller-targeted historical predecessor, cross-scope write-target authority, and derived semantic-vector "
          f"sidecar reconciliation on permanent deletion and recovery); {deltas}")
DEFERRED_SUFFIX = "; at -v8 (#786 draft): deferral carried forward unchanged; this row is not executed under this lane"

for family in ("amb-precisionmembench-retrieval", "longmemeval-s-retrieval-parity"):
    v7 = json.loads((lanes / f"{family}-v7.json").read_text(encoding="utf-8"))
    lane = copy.deepcopy(v7)
    lane["lane_id"] = f"{family}-v8"
    lane["status"] = "draft"
    lane["owning_issue"] = 786
    lane["frozen_on"] = None
    lane["frozen_before_any_score"] = True
    lane["description"] = (v7["description"].replace("Eighth lane generation (#770)", "Ninth lane generation (#786 DRAFT)")
                           .replace("-v6", "-v7").replace("Runtime Baseline v7", "Runtime Baseline v8")
                           .replace("reports/runtime/baseline-v7-declaration.json", DECLARATION)
                           .replace("No v7 score", "No v8 score"))
    # the change sentence is the only free text that differs between generations
    start = lane["description"].index("(the ")
    end = lane["description"].index("). The Agent Memory control")
    lane["description"] = lane["description"][:start] + "(" + CHANGE + lane["description"][end:]
    lane["freeze_rationale"] = [
        (f"the -v7 lane is frozen (not accepted) and its control executed the declared transition to Runtime Baseline v7; "
         f"the cumulative successor proposal declares a transition from the published v6 to Runtime Baseline v8 ({CHANGE}), "
         "so the executing runtime is new and needs a new lane id (change_rule; docs/67: a successor needs new lane ids)"),
        (v7["freeze_rationale"][1].replace("(#770)", "(#786 draft)").replace("-v6", "-v7")
         .replace("blocks v7 publication", "blocks v8 publication")),
        ("expected effect, recorded before any score under this lane: the declared v8 changes alter no ranking policy or "
         "assertion filter; the public contract moves 1.6.0 -> 1.7.0 (#777 projection) and the write path refuses "
         "cross-scope targets (#786), neither of which any single-scope lane input reaches, so v8 is expected to be "
         "observationally identical to v7 on these lanes and no row is expected to differ; up/down counts and the summary "
         "deltas are reported, never gated, and must be zero"),
        *[item.replace("(#770)", "(#786 draft)").replace("-v6", "-v7").replace("-v7 row", "-v8 row") for item in v7["freeze_rationale"][3:]],
    ]
    lane["comparability"]["not_comparable_to"][0] = (v7["comparability"]["not_comparable_to"][0]
        .replace("-v6", "-v7").replace("Runtime Baseline v7", "Runtime Baseline v8").replace("(#770", "(#786 draft"))
    lane["comparability"]["notes"][-2] = (v7["comparability"]["notes"][-2].replace("#770", "#786 draft").replace("-v6", "-v7")
                                          .replace("Runtime Baseline v7", "Runtime Baseline v8"))
    lane["comparability"]["notes"][-1] = v7["comparability"]["notes"][-1].replace("the -v7 control", "the -v8 control")
    for row in lane["systems"]:
        if row["status"] == "frozen":
            row["status"] = "pending"
            row["status_reason"] = "draft -v8 row: to be executed only after the v8 declaration is sanctioned; no -v7 result transfers"
        configuration = row.get("configuration") or {}
        posture = configuration.get("runtime_baseline_posture")
        if posture is not None:
            posture.update({"predecessor": "agent-memory-runtime-baseline-v6",
                            "declared_successor": "agent-memory-runtime-baseline-v8",
                            "declaration": DECLARATION, "declaration_blob": blob})
        if row["role"] == "control":
            row["display_name"] = row["display_name"].replace("Runtime Baseline v7", "Runtime Baseline v8 (DRAFT)")
        if row["status"] == "deferred":
            row["status_reason"] = row["status_reason"] + DEFERRED_SUFFIX
    lane["findings"] = ["DRAFT: derived mechanically from the frozen -v7 lane by build_v8_lane_drafts.py; not registered, not frozen, no evidence"]
    (out / f"{family}-v8.DRAFT.json").write_text(json.dumps(lane, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{family}-v8 draft written")
