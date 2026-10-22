#!/usr/bin/env python3
"""Can the v7 declaration's required lanes produce workflow-imported evidence? (credential-free, no Actions)

Applies, unchanged, the workflow lane-precondition assertions (amb-competitive.yml lines
240/244, longmemeval-competitive.yml lines 154/159) and the importers' own
runtime_baseline_binding() to each lane the v7 declaration requires, using the checker
identity of the current checkout.  usage: lane_gate_probe.py <repo_root>
"""
import json, runpy, subprocess, sys
from pathlib import Path

root = Path(sys.argv[1])
decl_path = root / "reports/runtime/baseline-v7-declaration.json"
decl = json.loads(decl_path.read_text())
blob = subprocess.check_output(["git", "hash-object", str(decl_path)], cwd=root, text=True).strip()
line = subprocess.run([sys.executable, "scripts/check_runtime_baseline_equivalence.py", "--candidate", "HEAD"],
                      cwd=root, capture_output=True, text=True).stdout.strip()
identity = {"runtime_baseline_state": line.split(";")[0].split(":")[-1].strip(), "runtime_baseline_line": line,
            "declaration_blob": blob}
importers = {"amb-precisionmembench": runpy.run_path(str(root / "scripts/import_amb_lane_evidence.py")),
             "longmemeval-s": runpy.run_path(str(root / "scripts/import_longmemeval_lane_evidence.py"))}
rows = []
for ref in [e["ref"] for e in decl["acceptance_evidence_required"] if e["kind"] == "lane"]:
    lane = json.loads((root / f"reference/agentmem_ref/evaluation/lanes/{ref}.json").read_text())
    control = next(s for s in lane["systems"] if s["role"] == "control")
    row = {"lane": ref, "lane_status": lane["status"], "control_row_status": control["status"]}
    try:
        assert lane["status"] == "frozen", lane["status"]
        assert control["status"] == "frozen", control["status"]
        row["workflow_precondition"] = "admitted"
    except AssertionError as exc:
        row["workflow_precondition"] = f"REFUSED: lane or row status {exc} (workflow asserts 'frozen')"
    mod = importers["amb-precisionmembench" if ref.startswith("amb") else "longmemeval-s"]
    try:
        mod["runtime_baseline_binding"](identity, lane)
        row["importer_posture"] = "admitted"
    except Exception as exc:  # noqa: BLE001 - the refusal is the observation
        row["importer_posture"] = f"REFUSED: {exc}"
    rows.append(row)
out = {"checker_line": line, "v7_declaration_blob": blob, "lanes": rows,
       "producible_as_declared": all(r["workflow_precondition"] == "admitted" and r["importer_posture"] == "admitted" for r in rows)}
print(json.dumps(out, indent=1))
