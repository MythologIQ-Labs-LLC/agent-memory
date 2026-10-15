"""Score a lme_trace.py trace the way the frozen runner does (session plane): recall_all@k, recall_any@k on returned."""
import glob, json, sys, collections
rows = [json.loads(l) for f in glob.glob(sys.argv[1]) for l in open(f)]
by = collections.defaultdict(lambda: collections.Counter())
for q in rows:
    if q["qtype"] == "abstention" or not q["gold"]:
        by["abstention"]["n"] += 1; by["abstention"]["returned"] += sum(r["returned"] for r in q["admitted"]); continue
    ranked = [r["id"] for r in sorted(q["admitted"], key=lambda r: r["rank"]) if r["returned"]]
    gold = set(q["gold"])
    for t in (q["qtype"], "ALL"):
        b = by[t]; b["n"] += 1; b["returned"] += len(ranked)
        for k in (1, 5, 10, 50):
            top = set(ranked[:k]); b[f"all@{k}"] += gold <= top; b[f"any@{k}"] += bool(gold & top)
for t, b in sorted(by.items()):
    n = b["n"]
    if t == "abstention":
        print(f"{t:<28} n={n} mean_returned={b['returned']/n:.2f}"); continue
    print(f"{t:<28} n={n:<4} ret={b['returned']/n:5.2f} any@1={b['any@1']/n:.3f} all@5={b['all@5']/n:.3f} all@10={b['all@10']/n:.3f} all@50={b['all@50']/n:.3f}")
