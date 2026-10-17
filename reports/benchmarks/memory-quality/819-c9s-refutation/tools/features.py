"""Per (query, in-scope current memory) features for semantic-sufficiency design (evaluation-only).
Output feas/features.jsonl: label (need|may|other|excluded), cos, drank, best, rel=cos/best, lexical candidate,
topical relevance and C4 basis (if admitted), query kind and needs_several."""
import json, sys, glob
from pathlib import Path
sys.path.insert(0, "/tmp/claude-0/wt/c9/reference")
from agentmem_ref.runtime.representation_onnx import OnnxSentenceEmbeddingProvider
from agentmem_ref.runtime.return_selection import interpret_query
p = OnnxSentenceEmbeddingProvider(); cache = {}
def emb(t):
    if t not in cache: cache[t] = p.embed(t)
    return cache[t]
out = open("feas/features.jsonl", "w")
for f in sorted(glob.glob("fx/*.json")):
    b = Path(f).stem
    data = json.loads(Path(f).read_text()); scen = data["scenarios"] if isinstance(data, dict) else data
    run = {r["id"]: r for r in json.load(open(f"feas/c9d-{b}.json"))["rows"]}
    for s in scen:
        for q in s["queries"]:
            texts = {}
            for op in s["operations"]:
                if op["scope"] != q["scope"]: continue
                if op["op"] in ("remember", "correct"): texts[op["ref"]] = op["text"]
                else: texts.pop(op["ref"], None)
            e = q["expect"]; need = set(e.get("must_include") or []); may = set(e.get("may_include") or [])
            exc = {x["ref"] for x in e.get("must_exclude") or []}
            qv = emb(q["query"])
            sims = sorted(((sum(x*y for x, y in zip(qv, emb(t))), ref) for ref, t in texts.items()), reverse=True)
            best = sims[0][0] if sims else 0
            facts = {x["name"]: x for x in run[q["id"]]["facts"] if not x["refusal"]}
            reading = interpret_query(q["query"])
            for i, (c, ref) in enumerate(sims):
                fx = facts.get(ref, {})
                out.write(json.dumps({"set": b, "q": q["id"], "ref": ref, "label": "need" if ref in need else "may" if ref in may else "excluded" if ref in exc else "other",
                    "abstain_q": not need, "cos": round(c, 4), "drank": i + 1, "best": round(best, 4), "rel": round(c / best, 4) if best > 0 else 0,
                    "lex": "lexical" in fx.get("routes", []), "relevance": fx.get("relevance"), "relative": fx.get("relative"),
                    "basis": fx.get("basis"), "returned_c4sem": ref in run[q["id"]]["returned"], "several": reading.needs_several,
                    "n": len(sims)}) + "\n")
