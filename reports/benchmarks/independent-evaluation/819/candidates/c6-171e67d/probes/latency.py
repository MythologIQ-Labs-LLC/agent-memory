"""Latency/resource probe: one store of N generated memories, 1 cold + 40 warm recalls. usage: latency.py N SEM REP out.json"""
import json, random, resource, statistics, sys, tempfile, time
from pathlib import Path
from agentmem_ref import AgentMemory

N, sem, rep, out = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
R = random.Random(819)
subj = ["my sister", "the landlord", "our neighbour", "my manager", "the dentist", "my cousin", "the plumber", "my old flatmate", "the vet", "my coach"]
verb = ["recommended", "mentioned", "booked", "cancelled", "moved", "bought", "repaired", "borrowed", "returned", "suggested"]
obj = ["a new bike", "the boiler", "a weekend in Bath", "the green sofa", "a pasta maker", "the spare tent", "a piano lesson", "the garden hose", "a train ticket", "the red kettle"]
when = ["last Tuesday", "in March", "after the party", "before Christmas", "this morning", "two weeks ago", "over the summer", "on Friday"]
texts = [f"{R.choice(subj).capitalize()} {R.choice(verb)} {R.choice(obj)} {R.choice(when)} (note {i})." for i in range(N)]
queries = ["What did the vet suggest?", "Who borrowed the spare tent?", "When was the boiler repaired?", "What do I know about piano lessons?",
           "Which things did my sister buy?", "Has anyone cancelled a trip?", "What happened before Christmas?", "Who moved the sofa?"] * 5
kw = {} if sem == "off" else {"semantic_retrieval": sem, "representation_dir": rep}
with tempfile.TemporaryDirectory() as tmp:
    t0 = time.perf_counter()
    with AgentMemory.open(tmp, tenant="tenant:lat", actor_id="agent:lat", scope="user:lat", purpose="lat", **kw) as m:
        for i, t in enumerate(texts):
            m.remember(f"mem{i}", t)
    ingest = time.perf_counter() - t0
    ms = []
    with AgentMemory.open(tmp, tenant="tenant:lat", actor_id="agent:lat", scope="user:lat", purpose="lat", **kw) as m:
        for q in queries:
            t = time.perf_counter(); r = m.recall(q, budget=5); ms.append((time.perf_counter() - t) * 1000)
    disk = sum(p.stat().st_size for p in Path(tmp).rglob("*") if p.is_file())
res = {"N": N, "semantic": sem, "ingest_s": round(ingest, 2), "cold_first_ms": round(ms[0], 1),
       "warm_p50_ms": round(statistics.median(ms[1:]), 1), "warm_p95_ms": round(sorted(ms[1:])[int(.95 * (len(ms) - 1))], 1),
       "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "store_bytes": disk}
json.dump(res, open(out, "w")); print(json.dumps(res))
