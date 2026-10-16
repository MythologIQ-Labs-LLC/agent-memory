import json, statistics, sys, tempfile, time
sys.path.insert(0, sys.argv[1] + "/reference")
from agentmem_ref import AgentMemory
rem, rec, oc = [], [], []
with tempfile.TemporaryDirectory() as t:
    for i in range(100):
        t0 = time.perf_counter(); m = AgentMemory.open(t, tenant="tenant:p", actor_id="agent:p", scope="project:p", purpose="p"); t1 = time.perf_counter()
        m.remember(f"memory:{i}", f"perf fact number {i} about the garden"); t2 = time.perf_counter()
        m.recall("garden fact", budget=5); t3 = time.perf_counter(); m.close(); t4 = time.perf_counter()
        rem.append((t2 - t1) * 1e3); rec.append((t3 - t2) * 1e3); oc.append(((t1 - t0) + (t4 - t3)) * 1e3)
q = lambda x: [round(statistics.median(x), 2), round(sorted(x)[94], 2)]
print(json.dumps({"tree": sys.argv[2], "remember_p50_p95": q(rem), "recall_p50_p95": q(rec), "open_close_p50_p95": q(oc)}))
