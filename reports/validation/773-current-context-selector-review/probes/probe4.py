import sys,tempfile
exec(open("/tmp/claude-0/v3/probe/selprobe.py").read())
T="2026-10-12T12:00:00Z"
scen={
 "G2-repro":([{"id":"freeze","op":"retain","memory":"freeze","text":"Payments deploys are frozen for the holiday window.","temporal":{"valid_from":"2025-11-20T00:00:00Z","valid_until":"2025-12-01T00:00:00Z"}},
              {"id":"days","op":"retain","memory":"days","text":"Payments deploys happen on Tuesdays and Thursdays."}],
             "Are payments deploys allowed this Thursday?",3),
 "freeze-still-active?":([{"id":"freeze","op":"retain","memory":"freeze","text":"Cedarline froze field-station firmware deployments during the 2025 winter migration window.","temporal":{"valid_from":"2025-11-01T00:00:00Z","valid_until":"2025-12-01T00:00:00Z"}},
              {"id":"mission","op":"retain","memory":"mission","text":"Cedarline's Mesa-7 sensor deployment monitors river turbidity."}],
             "Is the 2025 winter firmware freeze still active today?",2),
 "when-did-promo-end?":([{"id":"promo","op":"retain","memory":"promo","text":"The checkout discount promotion ran with a 20 percent code.","temporal":{"valid_from":"2026-03-01T00:00:00Z","valid_until":"2026-04-01T00:00:00Z"}},
              {"id":"pricing","op":"retain","memory":"pricing","text":"Checkout pricing is reviewed quarterly."}],
             "Is the checkout discount promotion still running?",2),
}
for name,(ev,q,b) in scen.items():
    prev.clear()
    with tempfile.TemporaryDirectory() as t:
        rt,lab=build(ev,t)
        d=rt.multi_route_recall(q,CTX,temporal_intent={"mode":"current"})
        ct=rt.multi_route_recall(q,CTX,temporal_intent={"mode":"current","reference_time":T})
        sc=rt.current_served_context(q,CTX,budget=b,reference_time=T)
        print(f"{name:22s} default {[lab[x] for x in d.ranked_admitted[:b]]}  composed-T {[lab[x] for x in ct.ranked_admitted[:b]]}  selector-T {[lab[x] for x in sc.served_refs]}")
