import json, sys, glob
from pathlib import Path
sys.path.insert(0, "/tmp/claude-0/wt/c4/reference")
from agentmem_ref.runtime.representation_onnx import OnnxSentenceEmbeddingProvider
p = OnnxSentenceEmbeddingProvider(); cache = {}
def emb(t):
    if t not in cache: cache[t] = p.embed(t)
    return cache[t]
tot = {r: dict(gain_need=0, extra=0, absent_nonempty=0) for r in (1, 2, 3)}
for b in sys.argv[1:]:
    data = json.loads(Path(f"fx/{b}.json").read_text()); scen = data["scenarios"] if isinstance(data, dict) else data
    run = {r["id"]: r for r in json.loads(Path(f"runs/c4-required-{b}.json").read_text())["rows"]}
    for s in scen:
        for q in s["queries"]:
            texts = {}
            for op in s["operations"]:
                if op["scope"] != q["scope"]: continue
                if op["op"] in ("remember", "correct"): texts[op["ref"]] = op["text"]
                else: texts.pop(op["ref"], None)
            qv = emb(q["query"])
            sims = sorted(((sum(x*y for x, y in zip(qv, emb(t))), ref) for ref, t in texts.items()), reverse=True)
            r0 = run[q["id"]]; ret = set(r0["returned"]); need = set(q["expect"].get("must_include") or [])
            allowed = need | set(q["expect"].get("may_include") or [])
            for r in (1, 2, 3):
                add = [ref for c, ref in sims[:r] if c <= 0.30 and ref not in ret]
                tot[r]["gain_need"] += sum(1 for x in add if x in need)
                tot[r]["extra"] += sum(1 for x in add if x not in allowed)
                tot[r]["absent_nonempty"] += int(not need and not ret and bool(add))
print(json.dumps(tot))
