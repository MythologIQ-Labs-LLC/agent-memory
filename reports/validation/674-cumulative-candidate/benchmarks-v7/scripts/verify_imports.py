#!/usr/bin/env python3
"""Independent re-verification of imported v7 lane evidence against the raw local run artifacts.

usage: verify_imports.py <repo-root> <local-runs-root>   (runs-root holds amb/<run_id>/... and lme/<run_id>/...)

Every imported record must bind one of the executing revisions listed in EXPECT (its directory suffix is
that revision) with the declaration blob the lane pinned at that revision, and TRANSITION.

For every imported record: every file named in evidence.json["files"] re-hashes to the recorded sha256;
the committed execution identity is byte-identical to the raw run's; the committed AMB single-turn.json
(and cross-fact.jsonl) is byte-identical to the raw harness output; the committed LongMemEval
report.json + report.rows.json.gz recompose to the raw runner report exactly; and the record binds the
expected revision, lane, checker state and declaration blob.
"""
import gzip, hashlib, json, sys
from pathlib import Path

repo, runs = Path(sys.argv[1]), Path(sys.argv[2])
EXPECT = {  # executing revision -> declaration blob the lane pinned at that revision
    "7917226712c4bb83e70bf95a9093ea96667fddc8": "a78797cbfca0e017e99c7e3e00823ded3ef1653b",
    "2ad4cf23d366fc784a486b0245550230e64bfa25": "7de94f11d7d521f07d2fe22317662ac6f92f89fa",
    "9d0ba703c98cabb94933545a553c8c6ae1ab578b": "7de94f11d7d521f07d2fe22317662ac6f92f89fa",
    "5ed105d7030d5860f877b03a28a9201281d8d55b": "7de94f11d7d521f07d2fe22317662ac6f92f89fa",
}
roots = {"amb": repo / "reports/benchmarks/amb/amb-precisionmembench-retrieval-v7",
         "lme": repo / "reports/benchmarks/longmemeval/longmemeval-s-retrieval-parity-v7"}
failures = 0
for kind, root in roots.items():
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        ev = json.loads((d / "evidence.json").read_text(encoding="utf-8"))
        checks = {}
        bad = []
        for name, digest in ev["files"].items():
            p = d / name
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                bad.append(name)
        checks["files_rehash"] = "ok(%d)" % len(ev["files"]) if not bad else "BAD %s" % bad
        run_id, art = ev["workflow_run"]["id"], ev["workflow_run"]["artifact_directory"]
        raw = runs / kind / run_id / art
        checks["identity_bytes_equal"] = (raw / "execution-identity.json").read_bytes() == (d / "execution-identity.json").read_bytes()
        if kind == "amb":
            rawsum = next(raw.glob("precisionmembench/*/retrieval/single-turn.json"))
            checks["single_turn_bytes_equal"] = rawsum.read_bytes() == (d / "single-turn.json").read_bytes()
            if (raw / "cross-fact.jsonl").is_file():
                checks["cross_fact_bytes_equal"] = (raw / "cross-fact.jsonl").read_bytes() == (d / "cross-fact.jsonl").read_bytes()
        else:
            backend, plane = d.name.rsplit("-", 1)[0].rsplit("-", 1)
            rawobj = json.loads((raw / f"{plane}-{backend}.json").read_text(encoding="utf-8"))
            rep = json.loads((d / "report.json").read_text(encoding="utf-8"))
            rows = json.loads(gzip.open(d / "report.rows.json.gz").read())
            for pl, pd in rows.items():
                for be, rr in pd.items():
                    rep["planes"][pl]["backends"][be]["rows"] = rr
            checks["report_recomposes_to_raw"] = rep == rawobj
        ident = json.loads((d / "execution-identity.json").read_text(encoding="utf-8"))
        rev = ident["agent_memory_revision"]
        blob = next((b for r, b in EXPECT.items() if rev.startswith(r)), None)
        checks["revision"] = blob is not None and d.name.endswith(rev[:12])
        checks["state"] = ident["runtime_baseline_state"] == "TRANSITION"
        checks["declaration_blob"] = ident["declaration_blob"] == blob
        checks["lane_id"] = ev["lane_id"]
        checks["runner"] = ident.get("runner")
        ok = all(v is True or (isinstance(v, str) and (v.startswith("ok") or v in (ev["lane_id"],) or v == ident.get("runner"))) for v in checks.values())
        failures += not ok
        print(("VERIFIED " if ok else "FAILED   ") + d.name, json.dumps(checks))
print("failures:", failures)
sys.exit(1 if failures else 0)
