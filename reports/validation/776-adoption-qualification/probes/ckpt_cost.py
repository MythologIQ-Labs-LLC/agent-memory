import sys, time, tempfile, os
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
d = tempfile.mkdtemp(); root = d + "/m"
m = AgentMemory.open(root, tenant="t", actor_id="agent:x", scope="project:a", purpose="p")
N = int(sys.argv[2]); marks = {10, 100, 500, 1000, 2000, 4000}
t0 = time.time()
for i in range(1, N + 1):
    m.remember(f"memory:{i}", f"note {i} about pump station {i}")
    s = time.perf_counter(); r = m.forget(f"memory:{i}"); dt = time.perf_counter() - s
    assert r["committed"], r
    if i in marks:
        s2 = time.perf_counter(); m.recall("pump station note"); rt = time.perf_counter() - s2
        size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(root) for f in fs)
        print(f"tombstones={i:5d} forget={dt*1e3:8.1f} ms recall={rt*1e3:8.1f} ms state={size/1e6:6.2f} MB elapsed={time.time()-t0:6.0f}s", flush=True)
