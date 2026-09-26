"""Paired before/after comparison of two LongMemEval profile reports (diagnostic only).

Usage: python reference/compare_longmemeval_reports.py BEFORE.json BEFORE.rows.json.gz AFTER.json [AFTER.rows.json.gz]
"""
import json, gzip, sys, random, statistics
before_rep = json.load(open(sys.argv[1])); before_rows = json.load(gzip.open(sys.argv[2])); after = json.load(open(sys.argv[3]))
if len(sys.argv) > 4:
    for plane, backends in json.load(gzip.open(sys.argv[4])).items():
        for backend, rows in backends.items():
            after["planes"][plane]["backends"][backend]["rows"] = rows
print("after:", after["execution"]["agent_memory_revision"][:7], "dirty", after["execution"]["agent_memory_worktree_dirty"], "input", after["input"]["sha256"][:12], "n", after["input"]["question_count"], "wall", after["execution"]["wall_seconds"])
out = {}
for plane in ("session", "turn"):
    A = {r["question_id"]: r for r in after["planes"][plane]["backends"]["agent_memory"]["rows"]}
    B = {r["question_id"]: r for r in before_rows[plane]["agent_memory"]}
    L = {r["question_id"]: r for r in before_rows[plane]["lexical_overlap"]}
    scored = [q for q in A if A[q]["status"] == "scored"]
    ha, hb = after["planes"][plane]["backends"]["agent_memory"]["aggregate"]["headline"], before_rep["planes"][plane]["backends"]["agent_memory"]["aggregate"]["headline"]
    hl = before_rep["planes"][plane]["backends"]["lexical_overlap"]["aggregate"]["headline"]
    print(f"== {plane}  failures {after['planes'][plane]['backends']['agent_memory']['failures']}")
    for m in sorted(ha):
        d = [A[q]["metrics"][plane][m] - B[q]["metrics"][plane][m] for q in scored]
        rng = random.Random(2027); bs = sorted(statistics.fmean(rng.choices(d, k=len(d))) for _ in range(2000))
        print(f"  {m:14s} before {hb[m]:.3f} after {ha[m]:.3f} (lexical {hl[m]:.3f})  paired Δ {statistics.fmean(d):+.4f} [{bs[50]:+.4f},{bs[1949]:+.4f}]  better {sum(x>0 for x in d)} worse {sum(x<0 for x in d)}")
    ca, cb = after["planes"][plane]["backends"]["agent_memory"]["currentness"], before_rep["planes"][plane]["backends"]["agent_memory"]["currentness"]
    fixed = sum(1 for q in A if B[q]["latest_gold_first"] is False and A[q]["latest_gold_first"] is True)
    broke = sum(1 for q in A if B[q]["latest_gold_first"] is True and A[q]["latest_gold_first"] is False)
    print(f"  latest_gold_first before {cb['latest_gold_ranked_first']['rate']:.3f} after {ca['latest_gold_ranked_first']['rate']:.3f}  fixed {fixed} newly broken {broke}")
    ta, tb = after["planes"][plane]["backends"]["agent_memory"]["by_question_type"], before_rep["planes"][plane]["backends"]["agent_memory"]["by_question_type"]
    key = "recall_all@5" if plane == "session" else "recall_all@10"
    print("  by type", key, {t: f"{tb[t]['headline'][key]:.3f}->{ta[t]['headline'][key]:.3f}" for t in sorted(ta)})
    print("  timing", after["planes"][plane]["backends"]["agent_memory"]["timing"])
