"""Rescore all (query, in-scope memory) pairs with named ONNX cross-encoder files; adds columns to a copy of features."""
import json, sys, time
from pathlib import Path
S = Path(sys.argv[1]); specs = sys.argv[2:]  # name=modeldir:onnxfile
sys.argv = [sys.argv[0], str(S), "x"]
src = open(S / "tools/features_ce.py").read().split("mini = OnnxSentenceEmbeddingProvider()")[0]
exec(src)
class CE2(CrossEncoder):
    def __init__(self, d, f):
        self.s = session(S / "models" / d / "onnx" / f)
        self.t = Tokenizer.from_file(str(S / "models" / d / "tokenizer.json")); self.t.enable_truncation(512); self.t.enable_padding()
        self.names = [i.name for i in self.s.get_inputs()]
ms = {}
for sp in specs:
    n, rest = sp.split("="); d, f = rest.split(":"); ms[n] = CE2(d, f)
cost = {n: 0.0 for n in ms}; scores = {}
import glob
for f in sorted(glob.glob(str(S / "fx/*.json"))):
    b = Path(f).stem; data = json.loads(Path(f).read_text()); scen = data["scenarios"] if isinstance(data, dict) else data
    for s in scen:
        for q in s["queries"]:
            texts = {}
            for op in s["operations"]:
                if op["scope"] != q["scope"]: continue
                if op["op"] in ("remember", "correct"): texts[op["ref"]] = op["text"]
                else: texts.pop(op["ref"], None)
            refs = list(texts)
            for n, m in ms.items():
                t = time.perf_counter(); v = m.score(q["query"], [texts[r] for r in refs]); cost[n] += time.perf_counter() - t
                for r, x in zip(refs, v): scores.setdefault((b, q["id"], r), {})[n] = round(x, 4)
rows = [json.loads(l) for l in open(S / "feas/features_ce.jsonl")]
with open(S / f"feas/features_{'_'.join(ms)}.jsonl", "w") as out:
    for r in rows:
        r.update(scores[(r["set"], r["q"], r["ref"])]); out.write(json.dumps(r) + "\n")
print(json.dumps({n: round(1000 * c / len(rows), 2) for n, c in cost.items()}))
