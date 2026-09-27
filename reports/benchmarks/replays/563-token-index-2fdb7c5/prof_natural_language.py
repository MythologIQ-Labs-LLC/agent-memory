import sys, time, tempfile, importlib.util, statistics as st
from pathlib import Path
from unittest import mock
W = Path(sys.argv[1]); sys.path.insert(0, str(W / "reference"))
spec = importlib.util.spec_from_file_location("r", W / "reference/run_longmemeval.py"); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
from agentmem_ref import AgentMemory
from agentmem_ref.state.sqlite_substrate import SQLiteTemporalGraph
from agentmem_ref.runtime import runtime_composition
rows = []
for row in R.iter_questions(R.InputStream(Path(sys.argv[2]))):
    rows.append(row)
    if len(rows) == 3: break
tot = {}
def timed(owner, name, key):
    orig = getattr(owner, name)
    def w(*a, **k):
        t = time.perf_counter()
        try: return orig(*a, **k)
        finally: tot[key] = tot.get(key, 0) + time.perf_counter() - t
    return mock.patch.object(owner, name, w)
for mode in ("index", "scan"):
    tot.clear(); recalls = []; cands = []; stores = []
    for qi, row in enumerate(rows):
        items, _ = R.corpus(row, "turn")
        with tempfile.TemporaryDirectory() as d:
            with AgentMemory.open(d, tenant="t", actor_id="a", scope="s", purpose="p") as m:
                for i, it in enumerate(items): m.remember(f"m:{i}", it["text"])
                ctx = [timed(SQLiteTemporalGraph, "search", "search"), timed(runtime_composition, "admit_preselected_candidates", "admission")]
                if mode == "scan": ctx.insert(0, mock.patch.object(SQLiteTemporalGraph, "search", SQLiteTemporalGraph.search_by_scan))
                for c in ctx: c.start()
                for _ in range(3):
                    t = time.perf_counter(); r = m.recall(row["question"]); recalls.append(time.perf_counter() - t); cands.append(len(r["candidates"]))
                for c in reversed(ctx): c.stop()
        stores.append(len(items))
    n = len(recalls)
    print(mode, "stores", stores, "recall mean ms %.1f" % (st.mean(recalls)*1000), "search ms %.1f" % (tot.get("search",0)/n*1000), "admission ms %.1f" % (tot.get("admission",0)/n*1000), "candidates mean %.0f" % st.mean(cands))
