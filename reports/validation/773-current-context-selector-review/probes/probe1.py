import sys,tempfile
exec(open("/tmp/claude-0/v3/probe/selprobe.py").read())
ev=[{"id":"freeze","op":"retain","memory":"freeze","text":"Deploys are frozen for the holiday window.","temporal":{"valid_from":"2025-11-20T00:00:00Z","valid_until":"2025-12-01T00:00:00Z"}},
    {"id":"days","op":"retain","memory":"days","text":"Deploys happen on Tuesdays and Thursdays."},
    {"id":"open","op":"retain","memory":"open","text":"Deploys are open to all teams from 2026.","temporal":{"valid_from":"2026-01-01T00:00:00Z"}}]
with tempfile.TemporaryDirectory() as t:
    rt,lab=build(ev,t)
    print("written at:",{lab[f]:rt.adapter.checkpoint_substrate().get_fact(f).created_at for f in lab})
    for ref in ["2025-06-01T00:00:00Z","2025-11-25T00:00:00Z","2025-11-30T23:59:59Z","2025-12-01T00:00:00Z","2025-12-01T01:00:00+01:00","2025-11-30T23:30:00-01:00","2026-01-01T00:00:00Z","2026-01-01T00:00:30Z","2030-01-01T00:00:00Z","2025-12-01T00:00:00.000001Z"]:
        try:
            r=rt.multi_route_recall("Are deploys frozen?",CTX,temporal_intent={"mode":"current","reference_time":ref})
            app={lab[x]:r.ranking_evidence[x].get("temporal_applicability") for x in r.ranked_admitted}
            sc=rt.current_served_context("Are deploys frozen?",CTX,budget=3,reference_time=ref)
            print(ref.ljust(32),"served",[lab[x] for x in sc.served_refs],"inapp",sc.known_inapplicable_count,"unk",sc.unknown_applicability_count,app)
        except Exception as e: print(ref,"ERR",type(e).__name__,e)
    for bad in ["2025-12-01T00:00:00+99:99","2025-13-01T00:00:00Z","2025-12-01T24:00:00Z","2025-12-01T00:00:00-00:00","2025-12-01 00:00:00Z","2025-12-01T00:00:00z","0001-01-01T00:00:00Z","9999-12-31T23:59:59Z"]:
        try:
            sc=rt.current_served_context("Are deploys frozen?",CTX,budget=3,reference_time=bad); print("ACCEPTED",bad,[lab[x] for x in sc.served_refs])
        except Exception as e: print("rejected",bad,type(e).__name__)
