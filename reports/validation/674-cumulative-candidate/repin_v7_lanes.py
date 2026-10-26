#!/usr/bin/env python3
"""Re-pin the two staged -v7 candidate lanes to the cumulative v7 declaration (#674).

The lanes were frozen (no score) for the #644 v7 candidate and pin that declaration's blob in
every Agent Memory row's runtime_baseline_posture. The cumulative successor replaces that
declaration, so the posture blob and the two sentences that described the #644 change set are
updated. Nothing else in the lanes changes (lane id, frozen_on, owning issue, rows, budgets).
usage: repin_v7_lanes.py <repo_root>
"""
import json
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
lanes = root / "reference/agentmem_ref/evaluation/lanes"
blob = subprocess.run(["git", "hash-object", "reports/runtime/baseline-v7-declaration.json"],
                      cwd=root, capture_output=True, text=True, check=True).stdout.strip()
OLD_CHANGE = ("the eight protected blobs reports/runtime/baseline-v7-declaration.json declares (evidence sufficiency, the "
              "governed transition witness, the recall observation receipt, the runtime adapter and recall control); "
              "ranking policy 3.4.0, assertion filter 6.1.0 and public contract 1.6.0 are unchanged")
NEW_CHANGE = ("the 21 protected blobs reports/runtime/baseline-v7-declaration.json declares for the cumulative candidate "
              "(#674): the #786/#809 write-target authority and writer-bound canonical derivation, the #816/#821 "
              "runtime-owned generations and atomic configuration binding, the #802 derived-cache reconciliation, the #644 "
              "evidence sufficiency, transition witness and recall observation receipt, the #777 deleted-lineage projection "
              "and the #835 scope-safe multi-route and typed-graph discovery; ranking policy 3.4.0 and assertion filter 6.1.0 "
              "are unchanged; public contract 1.6.0 -> 1.8.0, provisional (owner decision at PR #805)")
OLD_WHO = "#644 declared a transition to Runtime Baseline v7"
NEW_WHO = "the cumulative candidate (#674) declares a transition to Runtime Baseline v7"
OLD_EFFECT = ("the declared v7 changes alter no ranking policy, assertion filter or public contract version, so v7 is "
              "expected to be observationally identical to v6")
NEW_EFFECT = ("the declared v7 changes alter no ranking policy or assertion filter; the public contract moves to 1.8.0 by "
              "refusal tokens on write paths this retrieval-only lane does not exercise, and the #835 discovery gates act "
              "on cross-scope seeds this single-scope lane does not contain, so v7 is expected to be observationally "
              "identical to v6")


def rewrite(value):
    if isinstance(value, str):
        return value.replace(OLD_CHANGE, NEW_CHANGE).replace(OLD_WHO, NEW_WHO).replace(OLD_EFFECT, NEW_EFFECT)
    if isinstance(value, list):
        return [rewrite(item) for item in value]
    if isinstance(value, dict):
        out = {key: rewrite(item) for key, item in value.items()}
        if "runtime_baseline_posture" in out and isinstance(out["runtime_baseline_posture"], dict):
            posture = dict(out["runtime_baseline_posture"])
            assert posture["declared_successor"] == "agent-memory-runtime-baseline-v7", posture
            posture["declaration_blob"] = blob
            out["runtime_baseline_posture"] = posture
        return out
    return value


for family in ("amb-precisionmembench-retrieval", "longmemeval-s-retrieval-parity"):
    path = lanes / f"{family}-v7.json"
    lane = json.loads(path.read_text(encoding="utf-8"))
    text_before = json.dumps(lane)
    for needle, replacement in ((OLD_CHANGE, NEW_CHANGE), (OLD_WHO, NEW_WHO), (OLD_EFFECT, NEW_EFFECT)):
        assert needle in text_before or replacement in text_before, (family, needle[:40])
    lane = rewrite(lane)
    path.write_text(json.dumps(lane, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{family}-v7 re-pinned to declaration blob {blob}")
