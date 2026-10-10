#!/usr/bin/env python3
"""Field-by-field v6 -> v7 lane comparison at a revision (no execution).

Compares each -v7 lane with its -v6 lane read as frozen (_as_frozen: accepted rows back to
frozen without status_reason, the v6 acceptance finding dropped), keyed by provider_key, and
classifies every differing leaf as an allowed identity change or UNLISTED.
usage: lane_field_diff.py <repo_root> <revision>
"""
import json, subprocess, sys
from pathlib import Path

root, rev = Path(sys.argv[1]), sys.argv[2]
sys.path.insert(0, str(root / "reference"))
from tests.test_same_harness_lanes_v3 import POSTURE, SEMANTIC_KEY, _as_frozen, _flat  # noqa: E402

LANE_LEVEL = {"/lane_id", "/frozen_on", "/owning_issue", "/description", "/freeze_rationale", "/comparability/notes",
              "/comparability/not_comparable_to"}
SPEC = {"amb-precisionmembench-retrieval": ("agent-memory", {"agent-memory", "agent-memory-shadow"}, {"agent-memory-shadow", SEMANTIC_KEY}, set()),
        "longmemeval-s-retrieval-parity": ("agent_memory", {"agent_memory", "agent_memory_shadow", SEMANTIC_KEY},
                                           {"agent_memory_shadow", SEMANTIC_KEY}, {"/execution/environment/dispatch_unit"})}


def show(path):
    return json.loads(subprocess.run(["git", "show", f"{rev}:{path}"], cwd=root, capture_output=True, text=True, check=True).stdout)


out = {"revision": subprocess.run(["git", "rev-parse", rev], cwd=root, capture_output=True, text=True).stdout.strip(), "lanes": {}}
for family, (control, posture_rows, deferred, extra) in SPEC.items():
    base = "reference/agentmem_ref/evaluation/lanes/"
    v6, v7 = _flat(_as_frozen(show(f"{base}{family}-v6.json"))), _flat(show(f"{base}{family}-v7.json"))
    allowed = (LANE_LEVEL | {f"/systems/{k}{s}" for k in posture_rows for s in POSTURE} | {f"/systems/{control}/display_name"}
               | {f"/systems/{k}/status_reason" for k in deferred} | extra)
    rows = []
    for path in sorted(set(v6) | set(v7)):
        a, b = v6.get(path, "<absent>"), v7.get(path, "<absent>")
        if a != b:
            rows.append({"path": path, "class": "identity (listed)" if path in allowed else "UNLISTED",
                         "v6_as_frozen": a, "v7": b})
    out["lanes"][family] = {"leaves_compared": len(set(v6) | set(v7)), "differences": len(rows),
                            "unlisted": [r["path"] for r in rows if r["class"] == "UNLISTED"],
                            "listed_but_unchanged": sorted(allowed - {r["path"] for r in rows}), "rows": rows}
print(json.dumps(out, indent=1, ensure_ascii=False))
