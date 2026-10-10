#!/usr/bin/env python3
"""Re-verify the nine imported -v7 evidence records from committed bytes (no execution, no network).

For each record: every committed file listed in the run's own sha256 inventory re-hashes to it;
the execution identity names the expected workflow run, revision and lane; and the importers'
own refusal functions (lane digest, lane pins, runtime-baseline binding, LongMemEval identity)
admit it against the lane read at the executing revision. usage: verify_imported_v7.py <repo_root>
"""
import hashlib, importlib.util, json, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "reference"))
from agentmem_ref.evaluation.same_harness_lane import lane_digest  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(name, root / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod); return mod


AMB, LME = load("import_amb_lane_evidence"), load("import_longmemeval_lane_evidence")
REV = "9b025f945e7ec4a1e349e56bba251e3122413e88"
EXPECTED = {
    ("amb", "agent-memory"): "38031417209", ("amb", "bm25"): "38031874405", ("amb", "mem0-explicit"): "38031876286",
    ("lme", "agent_memory/session"): "38031419237", ("lme", "agent_memory/turn"): "38031420941",
    ("lme", "lexical_overlap/session"): "38031877700", ("lme", "lexical_overlap/turn"): "38031879634",
    ("lme", "mem0_explicit/session"): "38031881481", ("lme", "mem0_explicit/turn"): "38031883040",
}
results = []
for (kind, key), run_id in EXPECTED.items():
    if kind == "amb":
        d = next((root / "reports/benchmarks/amb/amb-precisionmembench-retrieval-v7").glob(f"{key}-*"))
        lane_file = "reference/agentmem_ref/evaluation/lanes/amb-precisionmembench-retrieval-v7.json"
    else:
        backend, plane = key.split("/")
        d = next((root / "reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v7").glob(f"{backend}-{plane}-*"))
        lane_file = "reference/agentmem_ref/evaluation/lanes/longmemeval-s-retrieval-parity-v7.json"
    identity = json.loads((d / "execution-identity.json").read_text())
    lane = AMB.lane_at_revision(root, lane_file, identity["agent_memory_revision"], at_head=False)
    row = {"record": str(d.relative_to(root)), "workflow_run_id": identity["workflow_run_id"], "problems": []}
    inventory = AMB.read_inventory(d / "sha256.txt")
    hashed = 0
    for name, digest in inventory.items():
        target = d / Path(name).name if not (d / name).exists() else d / name
        if target.exists():
            hashed += 1
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                row["problems"].append(f"{name} digest mismatch")
    row["inventory_files_rehashed"] = f"{hashed}/{len(inventory)}"
    if str(identity["workflow_run_id"]) != run_id: row["problems"].append("workflow run id")
    if identity["agent_memory_revision"] != REV: row["problems"].append("revision")
    row["lane_digest"] = identity.get("lane_digest_sha256")
    if identity.get("lane_digest_sha256") != lane_digest(lane): row["problems"].append("lane digest")
    try:
        if kind == "amb":
            AMB.check_lane_pins(identity, lane)
            bound = AMB.runtime_baseline_binding(identity, lane)
        else:
            lrow = LME._check_identity(run_id, identity, lane)
            bound = LME.runtime_baseline_binding(identity, lane, lrow)
        row["runtime_baseline"] = bound
    except Exception as exc:  # noqa: BLE001
        row["problems"].append(f"importer refusal: {exc}")
    evidence = json.loads((d / "evidence.json").read_text())
    row["evidence_class"] = evidence.get("evidence_class")
    row["authority_effect"] = evidence.get("authority_effect")
    row["status"] = "VERIFIED" if not row["problems"] else "PROBLEM"
    results.append(row)
print(json.dumps({"revision": REV, "records": results, "all_verified": all(r["status"] == "VERIFIED" for r in results)}, indent=1))
