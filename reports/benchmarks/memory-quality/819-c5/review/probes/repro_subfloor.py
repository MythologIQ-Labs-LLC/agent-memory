"""The 0.25 absolute floor sits below the semantic route's own 0.30 discovery floor, so facts the
lexical route proposed only through shared function words ("is", "my") and that the vector route
rejected are returned on similarity 0.25-0.30.  python3 repro_subfloor.py <worktree>"""
import sys
sys.path.insert(0, sys.path[0]); import fakes; fakes.setup(sys.argv[1])
FACTS = {"m:boss": "My manager is Priya Raman.", "m:cat": "The tabby is called Miso.",
         "m:car": "We drive a grey Corolla."}
for q, sims in (("Who is my dentist?", {"m:boss": 0.27, "m:cat": 0.26, "m:car": 0.05}),
                ("Who is my dentist? (all < 0.25)", {"m:boss": 0.24, "m:cat": 0.20, "m:car": 0.05})):
    query = q.split(" (")[0]
    table = {query: {FACTS[r]: v for r, v in sims.items()}}
    s = fakes.Store(fakes.table_provider(table)); s.seed(FACTS)
    res, ret = s.recall(query)
    routes = {s.refs[u]: sorted({h["route_id"] for h in d.get("route_provenance", [])}) for u, d in res["admissions"].items()}
    print(f"{q}: sims={sims} returned={ret} abstained={res['return_policy'].get('abstained')} routes={routes}")
    s.close()

# Same similarity (0.28), different outcome depending only on incidental function-word overlap.
query = "Which automobile do we own?"
for label, text in (("shares 'we'", "We drive a grey Corolla."), ("shares no token", "Grey Corolla parked outside.")):
    table = {query: {text: 0.28}}
    s = fakes.Store(fakes.table_provider(table)); s.seed({"m:car": text})
    res, ret = s.recall(query)
    print(f"{query} vs {text!r} ({label}, sim 0.28): returned={ret} admitted={len(res['admitted'])}")
    s.close()
