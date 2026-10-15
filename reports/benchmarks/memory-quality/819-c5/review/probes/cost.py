"""Per-recall cost of the semantic channel with the real pinned model.
python3 cost.py <worktree> <n_facts> -> JSON summary"""
import json, os, random, statistics, sys, tempfile, time
from pathlib import Path
wt, n = sys.argv[1], int(sys.argv[2])
sys.path.insert(0, str(Path(wt) / "reference"))
os.environ.setdefault("AGENT_MEMORY_REPRESENTATION_DIR",
                      "/tmp/claude-0/-home-user-agent-memory/d36426e4-2c3f-5d02-b5a0-991ea8f96c90/scratchpad/representation")
from agentmem_ref import AgentMemory
from agentmem_ref.runtime import representation_onnx, vector_retrieval

counts = {"embed": 0, "embed_s": 0.0, "sim_s": 0.0, "sim_calls": 0}
orig_embed = representation_onnx.OnnxSentenceEmbeddingProvider.embed
def embed(self, text):
    t = time.perf_counter(); v = orig_embed(self, text)
    counts["embed"] += 1; counts["embed_s"] += time.perf_counter() - t; return v
representation_onnx.OnnxSentenceEmbeddingProvider.embed = embed
orig_sim = getattr(vector_retrieval.NativeVectorCandidateRetriever, "similarities", None)
if orig_sim:
    def sim(self, *a, **k):
        t = time.perf_counter(); r = orig_sim(self, *a, **k)
        counts["sim_s"] += time.perf_counter() - t; counts["sim_calls"] += 1; return r
    vector_retrieval.NativeVectorCandidateRetriever.similarities = sim

rng = random.Random(819)
people = ["Ana", "Priya", "Tom", "Miguel", "Sofia", "Kenji", "Lena", "Omar", "Grace", "Ivan"]
things = ["the boiler", "the car", "the dentist", "the garden", "the budget", "the flight", "the lease", "the vet",
          "the gym", "the piano", "the report", "the server", "the insurance", "the school run", "the wedding"]
verbs = ["is handling", "booked", "asked about", "cancelled", "moved", "paid for", "needs to check", "forgot",
         "recommended", "complained about"]
when = ["on Monday", "next week", "in March", "every Friday", "tomorrow", "last summer", "before the holiday", ""]
facts = [f"{rng.choice(people)} {rng.choice(verbs)} {rng.choice(things)} {rng.choice(when)}".strip() + f" (note {i})." for i in range(n)]
queries = ["Who is dealing with the heating?", "When is the vet visit?", "What did Priya book?", "Which trips are planned?",
           "Who complained about the car?", "What happens with the apartment rental?", "Who handles the money?",
           "What is the plan for the wedding?", "Who forgot the dentist?", "What is on Friday?"]
with tempfile.TemporaryDirectory() as tmp:
    m = AgentMemory.open(Path(tmp), tenant="t:cost", actor_id="a:cost", scope="u:cost", purpose="cost",
                         semantic_retrieval="required")
    for i, text in enumerate(facts):
        m.remember(f"m:{i}", text)
    m.recall("warm up", budget=10)  # populate derived vector cache
    lat = []; per = []; adm = []
    for rep in range(3):
        for q in queries:
            c0 = dict(counts); t = time.perf_counter()
            r = m.recall(q, budget=10, return_selection="relevance_sufficient"); adm.append(len(r["admitted"]))
            lat.append((time.perf_counter() - t) * 1000)
            per.append({k: counts[k] - c0[k] for k in counts})
    m.close()
print(json.dumps({"worktree": Path(wt).name, "facts": n, "recalls": len(lat), "mean_admitted": round(statistics.mean(adm),1),
                  "p50_ms": round(statistics.median(lat), 1), "p95_ms": round(sorted(lat)[int(0.95 * len(lat)) - 1], 1),
                  "mean_embeds_per_recall": round(statistics.mean(p["embed"] for p in per), 2),
                  "mean_embed_ms_per_recall": round(1000 * statistics.mean(p["embed_s"] for p in per), 2),
                  "mean_similarities_ms": round(1000 * statistics.mean(p["sim_s"] for p in per), 2)}))
