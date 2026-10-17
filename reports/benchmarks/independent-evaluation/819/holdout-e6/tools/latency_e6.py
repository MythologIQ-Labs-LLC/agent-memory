"""#819 e6 cost probe (public, synthetic; not cohort content).

A store of N short household/work notes that share the query's topical anchor, so nearly every
memory is admitted. Measures cold first recall, warm recall p50/p95 over 40 queries at budget 5,
admitted count, and peak RSS, under the arm's declared configuration.

usage: latency_e6.py N SEMANTIC REPDIR OUT.json [OPEN_KWARGS_JSON] [RECALL_KWARGS_JSON]
"""
import json
import random
import resource
import statistics
import sys
import tempfile
import time

from agentmem_ref import AgentMemory

N, sem, rep, out = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
okw = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}
rkw = json.loads(sys.argv[6]) if len(sys.argv) > 6 else {}
R = random.Random(8196)
who = ["the roofer", "my cousin", "the property manager", "a neighbor", "the carpenter", "my teammate", "the inspector", "a friend"]
what = ["the water heater", "the side gate", "the bathroom sink", "the crawlspace", "the garage roof", "the deck light",
        "the hedge line", "the dryer vent", "the gutter", "the thermostat"]
when = ["on Tuesday", "last autumn", "before dinner", "after the storm", "over the weekend", "in the morning"]
texts = [f"Cottage log {i}: {R.choice(who)} checked {R.choice(what)} at the cottage {R.choice(when)}." for i in range(N)]
queries = ["What happened with the cottage water heater?", "Who checked the cottage gutter?",
           "When was the cottage thermostat looked at?", "What did the inspector do at the cottage?",
           "Which cottage jobs did the carpenter handle?"] * 8
kw = dict(okw)
if sem != "off":
    kw.update({"semantic_retrieval": sem, "representation_dir": rep})
with tempfile.TemporaryDirectory() as t:
    with AgentMemory.open(t, tenant="tenant:lat", actor_id="agent:lat", scope="user:lat", purpose="lat", **kw) as m:
        w0 = time.perf_counter()
        for i, x in enumerate(texts):
            m.remember(f"n{i}", x)
        write_s = time.perf_counter() - w0
    ms, adm, ret = [], [], []
    with AgentMemory.open(t, tenant="tenant:lat", actor_id="agent:lat", scope="user:lat", purpose="lat", **kw) as m:
        c0 = time.perf_counter()
        m.recall(queries[0], budget=5, **rkw)
        cold_ms = (time.perf_counter() - c0) * 1000
        for q in queries:
            t0 = time.perf_counter()
            r = m.recall(q, budget=5, **rkw)
            ms.append((time.perf_counter() - t0) * 1000)
            adm.append(len(r.get("admitted") or []))
            ret.append(len(r.get("returned") or []))
res = {"N": N, "semantic": sem, "open_kwargs": okw, "recall_kwargs": rkw,
       "admitted_median": statistics.median(adm), "returned_median": statistics.median(ret),
       "write_seconds": round(write_s, 2), "cold_first_recall_ms": round(cold_ms, 1),
       "warm_p50_ms": round(statistics.median(ms), 1), "warm_p95_ms": round(sorted(ms)[int(.95 * (len(ms) - 1))], 1),
       "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}
json.dump(res, open(out, "w"))
print(json.dumps(res))
