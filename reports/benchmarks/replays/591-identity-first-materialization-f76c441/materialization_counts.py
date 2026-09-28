"""Per-search materialization and decode counts on the AgentMemBench retrieval workload."""
import sys, cProfile, pstats, json, time
sys.path.insert(0, sys.argv[1] + "/reference")
import run_agentmembench as amb
from agentmem_ref.state import sqlite_substrate
from pathlib import Path
recs = amb.load_records(Path(sys.argv[2]), 1000, 2027)
a = amb.AgentMemoryAdapter(); a.reset()
for i, r in enumerate(recs): a.add(r["text"], f"user_{i // 10:05d}")
counts = {"fact_from_row": 0}
orig = sqlite_substrate.SQLiteTemporalGraph._fact_from_row
def counted(row):
    counts["fact_from_row"] += 1
    return orig(row)
sqlite_substrate.SQLiteTemporalGraph._fact_from_row = staticmethod(counted)
import json as _json
dec = {"n": 0}; od = _json.decoder.JSONDecoder.raw_decode
def rd(self, *a, **k):
    dec["n"] += 1
    return od(self, *a, **k)
_json.decoder.JSONDecoder.raw_decode = rd
N = 300
pr = cProfile.Profile(); t = time.perf_counter(); pr.enable()
cand = 0
for i, r in enumerate(recs[:N]):
    a.search(r["query"], f"user_{i // 10:05d}", 5)
pr.disable(); wall = time.perf_counter() - t
st = pstats.Stats(pr)
rd_time = sum(v[2] for k, v in st.stats.items() if k[2] == "raw_decode" or k[2] == "rd")
stats = a.governance() if hasattr(a, "governance") else {}
print(json.dumps({"searches": N, "fact_from_row": counts["fact_from_row"], "fact_from_row_per_search": round(counts["fact_from_row"] / N, 1),
                  "json_raw_decode_calls": dec["n"], "json_raw_decode_per_search": round(dec["n"] / N, 1),
                  "raw_decode_cpu_s": round(rd_time, 3), "profiled_wall_s": round(wall, 2),
                  "candidates_per_search": round(a._stats["candidate_count"] / a._stats["recall_calls"], 2) if a._stats.get("recall_calls") else None}))
a.close()
