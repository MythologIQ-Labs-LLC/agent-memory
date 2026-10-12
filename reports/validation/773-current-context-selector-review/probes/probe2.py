import sys,tempfile
exec(open("/tmp/claude-0/v3/probe/selprobe.py").read())
ev=[{"id":"pg15","op":"retain","memory":"pg","text":"The ledger database runs PostgreSQL 15."},
    {"id":"pg16","op":"update","memory":"pg","text":"The ledger database runs PostgreSQL 16."},
    {"id":"freeze","op":"retain","memory":"freeze","text":"Ledger database upgrades are frozen for the holiday window.","temporal":{"valid_from":"2025-11-20T00:00:00Z","valid_until":"2025-12-01T00:00:00Z"}}]
with tempfile.TemporaryDirectory() as t:
    rt,lab=build(ev,t)
    sub=rt.adapter.checkpoint_substrate()
    print({lab[f]:(sub.get_fact(f).created_at, sub.get_fact(f).invalid_at) for f in lab})
    for ref in ("2025-11-25T00:00:00Z","2026-10-12T12:00:00Z"):
        r=rt.multi_route_recall("Which PostgreSQL version does the ledger database run?",CTX,temporal_intent={"mode":"current","reference_time":ref})
        sc=rt.current_served_context("Which PostgreSQL version does the ledger database run?",CTX,budget=3,reference_time=ref)
        print(ref,"served",[lab[x] for x in sc.served_refs],{lab[x]:r.ranking_evidence[x].get("temporal_applicability") for x in r.ranked_admitted},"refused",{lab.get(k,k):v for k,v in r.refusals.items()} if hasattr(r,"refusals") else "")
