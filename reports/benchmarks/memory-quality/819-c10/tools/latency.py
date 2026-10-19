"""Recall-only latency, model init and RSS: one store per scenario, one open, each query x3 (evaluation-only).

    latency.py <runtime_root> <scenarios.json> <out.json> [--answerability qnli-electra-base] [--threads N]
"""
import argparse, json, resource, statistics, sys, tempfile, time
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("root"); ap.add_argument("scenarios"); ap.add_argument("out")
ap.add_argument("--answerability", default="off"); ap.add_argument("--threads", type=int, default=1)
a = ap.parse_args()
ROOT = Path(a.root).resolve()
sys.path.insert(0, str(ROOT / "reference")); sys.path.insert(0, str(ROOT / "scripts"))
import run_memory_quality_scenarios as R  # noqa: E402
from agentmem_ref import AgentMemory  # noqa: E402
rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
init = {}
if a.answerability != "off":
    from agentmem_ref.runtime import answerability_onnx as ao
    t = time.perf_counter(); scorer = ao.OnnxAnswerabilityScorer(intra_op_threads=a.threads); init["answerability_s"] = time.perf_counter() - t
    ao.OnnxAnswerabilityScorer = lambda model_dir=None, **kw: scorer
from agentmem_ref.runtime import representation_onnx as ro
t = time.perf_counter(); prov = ro.OnnxSentenceEmbeddingProvider(); init["representation_s"] = time.perf_counter() - t
ro.OnnxSentenceEmbeddingProvider = lambda model_dir=None: prov
kw = {"semantic_answerability": a.answerability} if a.answerability != "off" else {}
data = json.loads(Path(a.scenarios).read_bytes()); scen = data["scenarios"] if isinstance(data, dict) else data
lat = []
for s in scen:
    with tempfile.TemporaryDirectory() as tmp:
        for op in s["operations"]:
            with AgentMemory.open(tmp, tenant=R.TENANT, actor_id=R.ACTOR, scope=op["scope"], purpose="lat", semantic_retrieval="required", **kw) as m:
                if op["op"] == "remember": m.remember(op["ref"], op["text"])
                elif op["op"] == "correct": m.correct(op["ref"], op["text"], evidence=R._evidence(op["scope"]))
                else: m.forget(op["ref"], evidence=R._evidence(op["scope"]))
        by_scope = {}
        for q in s["queries"]: by_scope.setdefault(q["scope"], []).append(q)
        for scope, qs in by_scope.items():
            with AgentMemory.open(tmp, tenant=R.TENANT, actor_id=R.ACTOR, scope=scope, purpose="lat", semantic_retrieval="required", **kw) as m:
                for q in qs: m.recall(q["query"], budget=R.BUDGET)  # warm the derived-vector cache
                for _ in range(3):
                    for q in qs:
                        t = time.perf_counter(); m.recall(q["query"], budget=R.BUDGET); lat.append((time.perf_counter() - t) * 1000)
lat.sort()
out = {"revision_root": str(ROOT), "answerability": a.answerability, "threads": a.threads, "recalls": len(lat),
       "p50_ms": round(statistics.median(lat), 1), "p95_ms": round(lat[int(0.95 * len(lat))], 1), "mean_ms": round(statistics.mean(lat), 1),
       "init_s": {k: round(v, 2) for k, v in init.items()},
       "maxrss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024, "rss_before_models_mib": rss0 // 1024}
Path(a.out).write_text(json.dumps(out, indent=1)); print(json.dumps(out))
