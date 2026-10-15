"""Latency/CPU of recall with the semantic route (real pinned model). usage: perf.py <tree> <N>"""
import json
import random
import statistics
import sys
import tempfile
import time
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402

N = int(sys.argv[2])
rng = random.Random(7)
SUBJ = ["Mia", "Leo", "Dad", "Ines", "Sam", "Priya", "the landlord", "Grandad", "my manager", "the vet", "our neighbour"]
VERB = ["booked", "mentioned", "forgot", "paid for", "fixed", "ordered", "cancelled", "recommended", "borrowed", "moved"]
OBJ = ["the dentist appointment", "a new kettle", "the car service", "train tickets to Leeds", "the garden fence",
       "a birthday cake", "the broadband contract", "a yoga class", "the passport renewal", "a plumber",
       "the holiday cottage", "a second-hand piano", "the school trip", "winter tyres", "a standing desk"]
WHEN = ["on Monday", "last week", "in March", "before Christmas", "yesterday", "at the weekend", "in the autumn"]
texts = [f"{rng.choice(SUBJ)} {rng.choice(VERB)} {rng.choice(OBJ)} {rng.choice(WHEN)} (note {i})." for i in range(N)]
QUERIES = ["Who sorted out the plumbing?", "What did we buy for the kitchen?", "Which trips are planned?",
           "Who is learning an instrument?", "What happened with the internet provider?", "When is the dentist?",
           "What exercise classes are booked?", "Which documents need renewing?", "Who repaired the fence?",
           "What did Mia order?"] * 3

with tempfile.TemporaryDirectory() as tmp:
    t0 = time.perf_counter()
    with AgentMemory.open(tmp, tenant="tenant:perf", actor_id="agent:perf", scope="user:perf", purpose="perf",
                          semantic_retrieval="required") as m:
        for i, t in enumerate(texts):
            m.remember(f"m{i}", t)
        build = time.perf_counter() - t0
        m.recall("warm up the cache", budget=10)
        lat, cpu, ret = [], [], []
        for q in QUERIES:
            w, c = time.perf_counter(), time.process_time()
            r = m.recall(q, budget=10)
            lat.append((time.perf_counter() - w) * 1000)
            cpu.append((time.process_time() - c) * 1000)
            ret.append(len(r["returned"]))
print(json.dumps({"tree": tree.name, "N": N, "build_s": round(build, 1), "p50_ms": round(statistics.median(lat), 1),
                  "p95_ms": round(sorted(lat)[int(0.95 * len(lat)) - 1], 1), "cpu_p50_ms": round(statistics.median(cpu), 1),
                  "mean_returned": round(sum(ret) / len(ret), 2)}))
