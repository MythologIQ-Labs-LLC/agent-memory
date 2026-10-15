"""Real pinned model: one question-shaped / meta memory takes K_single (and raises the margin floor).

usage: AGENT_MEMORY_REPRESENTATION_DIR=... python repro_stuffing.py <tree>
"""
import json
import sys
import tempfile
from pathlib import Path

tree = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tree / "reference"))
from agentmem_ref import AgentMemory  # noqa: E402

BASE = {
    "gp": "Dr. Mensah at the Elm Street surgery is my GP.",
    "dog": "Biscuit, our beagle, is terrified of thunderstorms.",
    "cat": "The tabby we adopted in March is called Miso.",
    "petfood": "Miso only eats the salmon pouches, Biscuit gets kibble.",
    "n1": "The boiler service is booked for 14 November.",
    "n2": "The hedge needs trimming before the neighbours complain.",
    "n3": "Our recycling bins are collected fortnightly.",
}
STUFF = {
    "stuff-doc": "I keep forgetting who my doctor is.",
    "stuff-pets": "Asked which pets we have and what the pets eat.",
}
QUERIES = ["Who is my doctor?", "Which pets do we have?", "What do the pets eat?"]

for label, mems in (("without meta notes", BASE), ("with meta notes", {**BASE, **STUFF})):
    with tempfile.TemporaryDirectory() as tmp, AgentMemory.open(
            tmp, tenant="tenant:rv", actor_id="agent:rv", scope="user:rv", purpose="rv", semantic_retrieval="required") as m:
        refs = {m.remember(r, t)["fact_uuid"]: r for r, t in mems.items()}
        for q in QUERIES:
            res = m.recall(q, budget=10)
            sem = sorted(((refs[u], round(h["raw_score"], 3)) for u, d in res["admissions"].items()
                          for h in d["route_provenance"] if h["route_id"] == "semantic_vector"), key=lambda x: -x[1])
            print(json.dumps({"tree": tree.name, "store": label, "query": q,
                              "returned": [refs[u] for u in res["returned"]], "semantic": sem}))
