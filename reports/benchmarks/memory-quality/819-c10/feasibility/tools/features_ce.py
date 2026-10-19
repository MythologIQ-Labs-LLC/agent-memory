"""C10 feasibility: per (query, in-scope current memory) features incl. candidate model scores (evaluation-only).

    features_ce.py <scratch> -> <scratch>/feas/features_ce.jsonl
Same row definition as C9-S tools/features.py; C4+sem lexical/basis fields come from base/c4-required-<set>.json (--dump).
"""
import glob, json, sys, time
from pathlib import Path
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

S = Path(sys.argv[1])
sys.path.insert(0, str(S / "wt/c4/reference"))
from agentmem_ref.runtime.representation_onnx import OnnxSentenceEmbeddingProvider
from agentmem_ref.runtime.return_selection import interpret_query

def session(path):
    o = ort.SessionOptions(); o.intra_op_num_threads = 1; o.inter_op_num_threads = 1
    o.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    return ort.InferenceSession(str(path), o, providers=["CPUExecutionProvider"])

class CrossEncoder:
    def __init__(self, d, max_len=512):
        self.s = session(S / "models" / d / "onnx/model.onnx")
        self.t = Tokenizer.from_file(str(S / "models" / d / "tokenizer.json"))
        self.t.enable_truncation(max_len); self.t.enable_padding()
        self.names = [i.name for i in self.s.get_inputs()]
    def score(self, q, docs):
        if not docs: return []
        enc = self.t.encode_batch([(q, x) for x in docs])
        feed = {"input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64)}
        if "token_type_ids" in self.names:
            feed["token_type_ids"] = np.array([e.type_ids for e in enc], dtype=np.int64)
        out = self.s.run(None, feed)[0]
        return [float(v) for v in out.reshape(len(docs), -1)[:, 0]]

class Bge:
    def __init__(self, d):
        self.s = session(S / "models" / d / "onnx/model.onnx")
        self.t = Tokenizer.from_file(str(S / "models" / d / "tokenizer.json")); self.t.enable_truncation(512)
        self.c = {}
    def emb(self, x):
        if x not in self.c:
            e = self.t.encode(x)
            o = self.s.run(None, {"input_ids": np.array([e.ids]), "attention_mask": np.array([e.attention_mask]),
                                  "token_type_ids": np.array([e.type_ids])})[0][0, 0]
            self.c[x] = o / np.linalg.norm(o)
        return self.c[x]

mini = OnnxSentenceEmbeddingProvider(); mc = {}
def memb(t):
    if t not in mc: mc[t] = np.array(mini.embed(t))
    return mc[t]
CES = {"msm6": "cross-encoder_ms-marco-MiniLM-L6-v2", "msm12": "cross-encoder_ms-marco-MiniLM-L12-v2",
       "mxbx": "mixedbread-ai_mxbai-rerank-xsmall-v1", "qnli": "cross-encoder_qnli-electra-base",
       "bger": "BAAI_bge-reranker-base"}
ces = {k: CrossEncoder(v) for k, v in CES.items()}
bge = Bge("BAAI_bge-small-en-v1.5"); BQ = "Represent this sentence for searching relevant passages: "
cost = {k: 0.0 for k in CES}; pairs = 0
ONLY = sys.argv[2]
out = open(S / f"feas/features_ce-{ONLY}.jsonl", "w")
for f in [str(S / f"fx/{ONLY}.json")]:
    b = Path(f).stem
    data = json.loads(Path(f).read_text()); scen = data["scenarios"] if isinstance(data, dict) else data
    run = {r["id"]: r for r in json.load(open(S / f"base/c4-required-{b}.json"))["rows"]}
    for s in scen:
        for q in s["queries"]:
            texts = {}
            for op in s["operations"]:
                if op["scope"] != q["scope"]: continue
                if op["op"] in ("remember", "correct"): texts[op["ref"]] = op["text"]
                else: texts.pop(op["ref"], None)
            e = q["expect"]; need = set(e.get("must_include") or []); may = set(e.get("may_include") or [])
            exc = {x["ref"] for x in e.get("must_exclude") or []}
            qv = memb(q["query"])
            refs = list(texts)
            cos = {r: float(qv @ memb(texts[r])) for r in refs}
            order = sorted(refs, key=lambda r: -cos[r]); best = cos[order[0]] if order else 0
            bq = bge.emb(BQ + q["query"]); bcos = {r: float(bq @ bge.emb(texts[r])) for r in refs}
            border = sorted(refs, key=lambda r: -bcos[r])
            sc = {}
            for k, m in ces.items():
                t = time.perf_counter(); v = m.score(q["query"], [texts[r] for r in refs]); cost[k] += time.perf_counter() - t
                sc[k] = dict(zip(refs, v))
            pairs += len(refs)
            facts = {x["name"]: x for x in run[q["id"]]["facts"] if not x["refusal"]}
            reading = interpret_query(q["query"])
            for i, ref in enumerate(order):
                fx = facts.get(ref, {})
                row = {"set": b, "q": q["id"], "ref": ref,
                       "label": "need" if ref in need else "may" if ref in may else "excluded" if ref in exc else "other",
                       "abstain_q": not need, "cos": round(cos[ref], 4), "drank": i + 1, "best": round(best, 4),
                       "rel": round(cos[ref] / best, 4) if best > 0 else 0,
                       "lex": "lexical" in fx.get("routes", []), "relevance": fx.get("relevance"), "relative": fx.get("relative"),
                       "basis": fx.get("basis"), "returned_c4sem": ref in run[q["id"]]["returned"], "several": reading.needs_several,
                       "n": len(refs), "bcos": round(bcos[ref], 4), "brank": border.index(ref) + 1}
                for k in CES:
                    row[k] = round(sc[k][ref], 4)
                    row[k + "_rank"] = sorted(refs, key=lambda r: -sc[k][r]).index(ref) + 1
                out.write(json.dumps(row) + "\n")
print(json.dumps({"pairs": pairs, "seconds": {k: round(v, 1) for k, v in cost.items()},
                  "ms_per_pair": {k: round(1000 * v / pairs, 2) for k, v in cost.items()}}))
