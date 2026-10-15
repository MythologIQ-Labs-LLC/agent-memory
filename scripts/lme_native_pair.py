"""Paired per-question comparison of two native run_longmemeval reports: plane metric[,metric]"""
import json, math, sys
def rows(p, plane):
    d = json.load(open(p)); return {r["question_id"]: r for r in d["planes"][plane]["backends"]["agent_memory"]["rows"] if r.get("metrics")}
plane = sys.argv[3]; a, b = rows(sys.argv[1], plane), rows(sys.argv[2], plane)
for metric in sys.argv[4].split(","):
    common = [q for q in a if q in b and metric in (a[q]["metrics"].get(plane) or {})]
    fx = sum(1 for q in common if b[q]["metrics"][plane][metric] > a[q]["metrics"][plane][metric])
    br = sum(1 for q in common if b[q]["metrics"][plane][metric] < a[q]["metrics"][plane][metric])
    n = fx + br; k = min(fx, br); p = min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0
    print(f"{plane} {metric}: n={len(common)} improved {fx} regressed {br} McNemar p={p:.2g}")
