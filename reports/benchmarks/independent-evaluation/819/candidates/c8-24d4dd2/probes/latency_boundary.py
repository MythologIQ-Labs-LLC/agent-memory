"""Cost near the fusion boundary: stores where nearly every memory is admitted (N in 400..520), warm recall p50/p95.
usage: latency_boundary.py N SEM SELECTION REP out.json   (SELECTION: relevance_sufficient | ranked_prefix)"""
import json, random, resource, statistics, sys, tempfile, time
from agentmem_ref import AgentMemory
N, sem, sel, rep, out = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
R = random.Random(8190)
who = ["the plumber", "my sister", "the landlord", "a neighbour", "the electrician", "my manager", "the vet", "a colleague"]
what = ["the boiler", "the garden gate", "the kitchen tap", "the attic hatch", "the shed roof", "the porch light", "the back fence", "the bathroom fan"]
when = ["on Monday", "last spring", "after lunch", "before the holidays", "in the evening", "at the weekend"]
texts = [f"Note {i}: {R.choice(who)} looked at {R.choice(what)} for the house {R.choice(when)}." for i in range(N)]
queries = ["What happened with the house boiler?", "Who looked at the house fence?", "When was the house tap fixed?",
           "What did the landlord do at the house?", "Which house jobs did the electrician do?"] * 8
kw = {} if sem == "off" else {"semantic_retrieval": sem, "representation_dir": rep}
with tempfile.TemporaryDirectory() as t:
    with AgentMemory.open(t, tenant="tenant:lb", actor_id="agent:lb", scope="user:lb", purpose="lb", **kw) as m:
        for i, x in enumerate(texts):
            m.remember(f"n{i}", x)
    ms, adm, fusion = [], [], set()
    with AgentMemory.open(t, tenant="tenant:lb", actor_id="agent:lb", scope="user:lb", purpose="lb", **kw) as m:
        m.recall(queries[0], budget=5, return_selection=sel)  # warm the derived-vector cache
        for q in queries:
            t0 = time.perf_counter(); r = m.recall(q, budget=5, return_selection=sel); ms.append((time.perf_counter() - t0) * 1000)
            adm.append(len(r.get("admitted") or []))
            for d in (r.get("admissions") or {}).values():
                f = ((d.get("ranking_evidence") or d.get("ranking") or {}) if isinstance(d, dict) else {})
                if isinstance(f, dict) and "fusion" in f: fusion.add(str(f["fusion"].get("status")))
res = {"N": N, "semantic": sem, "selection": sel, "admitted_median": statistics.median(adm), "warm_p50_ms": round(statistics.median(ms), 1),
       "warm_p95_ms": round(sorted(ms)[int(.95 * (len(ms) - 1))], 1), "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
       "fusion_status_seen": sorted(fusion)}
json.dump(res, open(out, "w")); print(json.dumps(res))
