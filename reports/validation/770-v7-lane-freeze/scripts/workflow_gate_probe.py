#!/usr/bin/env python3
"""Run the lane workflows' own precondition code locally against v6/v7 lanes (no Actions, no credentials).

For each workflow it extracts, verbatim, the lane-precondition step's `validate-lane` call and
inline Python (substituting only `${{ inputs.* }}`), and the step that records the Runtime
Baseline posture, then executes them at this checkout for chosen (lane, row) dispatches. It also
compares the workflow's permissions and referenced secrets with a base revision, so a widened
grant or a new credential is reported. usage: workflow_gate_probe.py <repo_root> <base_revision>
"""
import json, os, re, subprocess, sys, tempfile
from pathlib import Path

import yaml

root, base = Path(sys.argv[1]).resolve(), sys.argv[2]
WORKFLOWS = {
    "amb": (".github/workflows/amb-competitive.yml", "Verify the frozen lane preconditions (PrecisionMemBench retrieval)",
            {"dataset": "precisionmembench", "mode": "retrieval"}, "memory"),
    "lme": (".github/workflows/longmemeval-competitive.yml", "Verify the frozen lane and the evaluator/adapter blobs it binds",
            {}, "backend"),
}
CASES = {
    "amb": [("amb-precisionmembench-retrieval-v7", "agent-memory"), ("amb-precisionmembench-retrieval-v7", "bm25"),
            ("amb-precisionmembench-retrieval-v7", "mem0-explicit"), ("amb-precisionmembench-retrieval-v7", "agent-memory-shadow"),
            ("amb-precisionmembench-retrieval-v6", "agent-memory")],
    "lme": [("longmemeval-s-retrieval-parity-v7", "agent_memory"), ("longmemeval-s-retrieval-parity-v7", "lexical_overlap"),
            ("longmemeval-s-retrieval-parity-v7", "mem0_explicit"), ("longmemeval-s-retrieval-parity-v7", "agent_memory_shadow"),
            ("longmemeval-s-retrieval-parity-v6", "agent_memory")],
}


def git(*args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


def workflow_doc(path, rev=None):
    return yaml.safe_load(git("show", f"{rev}:{path}") if rev else (root / path).read_text(encoding="utf-8"))


def secrets(text):
    return sorted(set(re.findall(r"secrets\.([A-Z0-9_]+)", text)))


out = {"checkout": git("rev-parse", "HEAD").strip(), "base": base, "workflows": {}}
checker = subprocess.run([sys.executable, "scripts/check_runtime_baseline_equivalence.py", "--candidate", "HEAD"], cwd=root,
                         capture_output=True, text=True)
register = json.loads((root / "reports/runtime/baseline-register.json").read_text(encoding="utf-8"))
declaration_blob = git("hash-object", register["declared_successor"]["declaration"]).strip()
out["runtime_baseline"] = {"line": checker.stdout.strip(), "rc": checker.returncode, "workflow_declaration_blob": declaration_blob}
for key, (path, step_name, fixed_inputs, row_input) in WORKFLOWS.items():
    doc, base_doc = workflow_doc(path), workflow_doc(path, base)
    text, base_text = (root / path).read_text(encoding="utf-8"), git("show", f"{base}:{path}")
    on = doc.get("on", doc.get(True))
    lane_input = on["workflow_dispatch"]["inputs"]["lane_id"]
    job = next(iter(doc["jobs"].values()))
    base_job = next(iter(base_doc["jobs"].values()))
    step = next(s for s in job["steps"] if s.get("name") == step_name)
    report = {
        "lane_options": lane_input["options"], "default": lane_input["default"],
        "permissions_unchanged": (doc.get("permissions"), job.get("permissions")) == (base_doc.get("permissions"), base_job.get("permissions")),
        "permissions": doc.get("permissions"), "secrets": secrets(text), "secrets_unchanged": secrets(text) == secrets(base_text),
        "diff_vs_base": git("diff", base, "--", path).count("\n+") - 1, "dispatches": [],
    }
    script = step["run"]
    blocks = re.findall(r"python - <<'PY'\n(.*?)\n\s*PY\n", script, re.S)
    for lane_id, row in CASES[key]:
        inputs = {"lane_id": lane_id, row_input: row, **fixed_inputs}
        lane_file = f"reference/agentmem_ref/evaluation/lanes/{lane_id}.json"
        env = {**os.environ, "LANE_FILE": lane_file, "AMB_REVISION": "03c1d0f1d27da63034f0931121c858faba512383"}
        result = {"lane_id": lane_id, "row": row}
        v = subprocess.run(["agent-memory", "benchmark", "validate-lane", lane_file, "--json"], cwd=root, env=env, capture_output=True, text=True)
        result["validate_lane_rc"] = v.returncode
        if v.returncode:
            result["outcome"] = "REFUSED at validate-lane: " + json.loads(v.stdout).get("error", "")[:200]
        else:
            for block in blocks:
                code = re.sub(r"\$\{\{ inputs\.(\w+) \}\}", lambda m: str(inputs[m.group(1)]), block)
                code = "\n".join(line[10:] if line.startswith(" " * 10) else line for line in code.splitlines())
                with tempfile.TemporaryDirectory() as tmp:
                    os.makedirs("/tmp/pmb-fixtures", exist_ok=True)
                    r = subprocess.run([sys.executable, "-c", code], cwd=root, env=env, capture_output=True, text=True, timeout=600)
                if r.returncode:
                    last = (r.stderr.strip().splitlines() or ["?"])[-1]
                    result["outcome"] = "REFUSED by workflow precondition: " + last[:240]
                    break
            else:
                lane = json.loads((root / lane_file).read_text(encoding="utf-8"))
                control = next(s for s in lane["systems"] if s["role"] == "control")
                pinned = control["configuration"]["runtime_baseline_posture"]["declaration_blob"]
                result["outcome"] = "ADMITTED"
                result["workflow_declaration_blob_equals_lane_pin"] = pinned == declaration_blob
        report["dispatches"].append(result)
    out["workflows"][key] = report
print(json.dumps(out, indent=1))
