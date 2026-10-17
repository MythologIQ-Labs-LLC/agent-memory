#!/usr/bin/env python3
"""For a harness run, report dense cosine and dense rank of each lost needed memory (evaluation-only).

    dense_probe.py <runtime_root> <scenarios.json> <run.json>
Rank is among the query scope's current (not forgotten) memory texts, the population the route scores.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "reference"))
from agentmem_ref.runtime.representation_onnx import OnnxSentenceEmbeddingProvider
p = OnnxSentenceEmbeddingProvider()
cache = {}
def emb(t):
    if t not in cache:
        cache[t] = p.embed(t)
    return cache[t]
def cos(a, b):
    return sum(x * y for x, y in zip(a, b))
data = json.loads(Path(sys.argv[2]).read_text()); scen = data["scenarios"] if isinstance(data, dict) else data
run = {r["id"]: r for r in json.loads(Path(sys.argv[3]).read_text())["rows"]}
out = []
for s in scen:
    for q in s["queries"]:
        r = run[q["id"]]
        texts = {}
        for op in s["operations"]:
            if op["scope"] != q["scope"]:
                continue
            if op["op"] in ("remember", "correct"):
                texts[op["ref"]] = op["text"]
            else:
                texts.pop(op["ref"], None)
        qv = emb(q["query"])
        sims = sorted(((cos(qv, emb(t)), ref) for ref, t in texts.items()), reverse=True)
        rank = {ref: i + 1 for i, (_, ref) in enumerate(sims)}
        simd = {ref: c for c, ref in sims}
        for need, st in r["stages"].items():
            out.append({"q": q["id"], "need": need, "stage": st["stage"], "cos": round(simd.get(need, float("nan")), 3),
                        "drank": rank.get(need), "best": round(sims[0][0], 3) if sims else None, "n": len(sims),
                        "kind": r["kind"], "query": q["query"]})
for o in out:
    if o["stage"] != "returned":
        print(json.dumps(o))
