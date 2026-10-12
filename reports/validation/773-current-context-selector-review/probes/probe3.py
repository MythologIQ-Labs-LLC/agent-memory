import sys,tempfile
exec(open("/tmp/claude-0/v3/probe/selprobe.py").read())
pairs=[
 ("We deploy the ledger with Jenkins.","We moved ledger deploys from Jenkins to GitHub Actions in 2025.","How do we deploy the ledger?"),
 ("Alice leads the ledger team.","Alice moved to the Berlin office in 2025.","Who leads the ledger team?"),
 ("The ledger API is documented in the wiki.","The ledger team moved its standup to Tuesdays.","Where is the ledger API documented?"),
 ("Ledger backups run nightly to S3.","Ledger backups now also replicate weekly to GCS.","Where do ledger backups go?"),
 ("The payments team uses Python 3.11.","The payments team switched its laptops to Linux.","Which Python version does the payments team use?"),
]
for a,b,q in pairs:
    ev=[{"id":"a","op":"retain","memory":"a","text":a},{"id":"b","op":"retain","memory":"b","text":b}]
    prev.clear()
    with tempfile.TemporaryDirectory() as t:
        rt,lab=build(ev,t)
        r=rt.multi_route_recall(q,CTX,temporal_intent={"mode":"current","reference_time":"2026-10-12T12:00:00Z"})
        sc=rt.current_served_context(q,CTX,budget=3,reference_time="2026-10-12T12:00:00Z")
        print(q,"|",{lab[x]:r.ranking_evidence[x]["temporal_applicability"] for x in r.ranked_admitted},"served",[lab[x] for x in sc.served_refs])
