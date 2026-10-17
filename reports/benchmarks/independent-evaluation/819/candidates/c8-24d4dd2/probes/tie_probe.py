"""Deterministic-tie probe: identical memories written forward and reversed; compare top-5 and count exact fused ties.
usage: tie_probe.py SEM SELECTION REP out.json"""
import json, sys, tempfile
from agentmem_ref import AgentMemory
sem, sel, rep, out = sys.argv[1:5]
STORES = [
    (["Our cat sleeps on the radiator shelf.", "The cat flap sticks in cold weather.", "Our neighbour's cat visits at night.",
      "Cat food is cheaper in bulk at the market.", "The cat was vaccinated in March.", "I sneeze around long-haired cats.",
      "The vet says our cat is slightly overweight.", "A cat calendar hangs in the kitchen."],
     ["What do I know about our cat?", "Is the cat healthy?", "Where does the cat sleep?"]),
    (["The train to Leeds leaves at 7:12.", "Train tickets are cheaper booked early.", "The train was cancelled twice last week.",
      "My season ticket covers the Leeds train.", "Leeds station has a new bike rack.", "I read on the train most mornings.",
      "The Leeds train is often standing room only.", "Engineering works close the line in August."],
     ["When is my train to Leeds?", "What happens on the Leeds line?", "How busy is my morning train?"]),
    (["Grandma's garden has three apple trees.", "The apple crumble recipe is grandma's.", "Apples from the market were sour.",
      "Grandma prunes the trees in February.", "The garden gate at grandma's squeaks.", "We pick apples every September.",
      "Grandma gave us apple chutney.", "An apple tree blew over in the storm."],
     ["What does grandma grow?", "When do we pick apples?", "What happened to the apple trees?"]),
]
kw = {} if sem == "off" else {"semantic_retrieval": sem, "representation_dir": rep}
res = {"semantic": sem, "selection": sel, "queries": 0, "top5_differs": 0, "returned_differs": 0, "exact_fused_ties_in_top5": 0, "details": []}
for texts, queries in STORES:
    runs = {}
    for order in ("forward", "reversed"):
        seq = texts if order == "forward" else list(reversed(texts))
        with tempfile.TemporaryDirectory() as t:
            with AgentMemory.open(t, tenant="tenant:tie", actor_id="agent:tie", scope="user:tie", purpose="tie", **kw) as m:
                uid = {}
                for x in seq:
                    uid[str(m.remember("m" + str(texts.index(x)), x)["fact_uuid"])] = texts.index(x)
                runs[order] = []
                for q in queries:
                    r = m.recall(q, budget=5, return_selection=sel)
                    top = [uid.get(u) for u in (r.get("admitted") or [])[:5]]
                    ret = [uid.get(u) for u in r.get("returned") or []]
                    fs = [((r["admissions"].get(u) or {}).get("ranking_evidence") or {}).get("fusion", {}).get("fused_score") for u in (r.get("admitted") or [])[:5]]
                    ties = sum(1 for i in range(len(fs) - 1) if fs[i] is not None and fs[i] == fs[i + 1])
                    runs[order].append((q, top, ret, ties))
    for (q, t1, r1, k1), (_, t2, r2, k2) in zip(runs["forward"], runs["reversed"]):
        res["queries"] += 1; res["top5_differs"] += int(t1 != t2); res["returned_differs"] += int(r1 != r2)
        res["exact_fused_ties_in_top5"] += int(k1 > 0)
        res["details"].append({"query": q, "forward_top5": t1, "reversed_top5": t2, "forward_returned": r1, "reversed_returned": r2, "adjacent_ties_forward": k1})
json.dump(res, open(out, "w"), indent=1); print(json.dumps({k: v for k, v in res.items() if k != "details"}))
