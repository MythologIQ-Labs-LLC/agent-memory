"""#825 synthetic 19k workload: indexed FTS5 vs Agent Memory default / rejected lexical / evidence_qualified.
usage: scale_paired.py <runtime> <output.json> <size>
Development evidence only (synthetic corpus, labels known to the project), never a holdout.
"""
import json, platform, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import paired  # noqa: E402
import jarvis_experiment as ex  # tools/jarvis_scale/experiment.py at 1d0de74c, unmodified

runtime, output = Path(sys.argv[1]), Path(sys.argv[2]); size = int(sys.argv[3])
sys.path.insert(0, str(runtime / "reference"))
records, cases = ex.workload(size, 825); results = []
start = time.perf_counter(); index = ex.IndexedArm(records); index_ms = (time.perf_counter() - start) * 1000
try:
    r = ex.evaluate(index, cases, 5, 3); r["ingest_ms"] = index_ms; results.append(r)
finally:
    index.close()
with tempfile.TemporaryDirectory(prefix="scale-819-") as tmp:
    start = time.perf_counter(); native = ex.AgentMemoryArm(records, Path(tmp)); ingest_ms = (time.perf_counter() - start) * 1000
    try:
        for arm_name in ("default", "lexical", "eq"):
            class ProfileArm:
                name = "agent_memory_context_" + arm_name
                def recall(self, query, scope, limit):
                    if scope not in native.handles:
                        native.handles[scope] = native._open(scope)
                    am = paired.am_arms(native.handles[scope], query, limit)
                    return [native.mapping[u] for u in am[arm_name]]
            r = ex.evaluate(ProfileArm(), cases, 5, 3); r["shared_ingest_ms"] = ingest_ms; results.append(r)
    finally:
        native.close()
p = {"evidence_class": "synthetic_development_only_not_independent",
     "runtime_sha": subprocess.check_output(["git", "-C", str(runtime), "rev-parse", "HEAD"], text=True).strip(),
     "selector_blob": subprocess.check_output(["git", "-C", str(runtime), "hash-object", "reference/agentmem_ref/api/context_selection.py"], text=True).strip(),
     "harness": "tools/jarvis_scale/experiment.py @ 1d0de74cc2c52c6c19645f99b367205afecbc637 (unmodified copy)",
     "corpus_sha256": ex.digest(records, cases), "synthetic_episodes": size, "records": len(records), "cases": len(cases), "budget": 5, "repeats": 3,
     "python": sys.version, "platform": platform.platform(), "results": results,
     "limitations": ["shared runtime ingest across three context arms", "fixed arm order", "FTS5 in memory vs durable governed store",
                     "latency indicative only", "no independent labels; not a holdout"]}
output.write_text(json.dumps(p, indent=2) + "\n")
for r in results:
    print({k: v for k, v in r.items() if k not in ("cases", "by_family")})
