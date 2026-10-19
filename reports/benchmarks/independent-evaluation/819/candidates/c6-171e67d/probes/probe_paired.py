"""Paired comparison of probe arms (exact McNemar on strict; bootstrap 95% CI on needed-recall and strict deltas)."""
import json, math, random, sys
arms = ["A-def", "C4-def", "C4-sem", "C6-sem", "C6-off"]
R = {a: {r["id"]: r for r in json.load(open(f"out/{a}.json"))["rows"]} for a in arms}
def mc(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
def boot(d, reps=10000, seed=819):
    rnd = random.Random(seed); n = len(d)
    m = sorted(sum(d[rnd.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return [round(sum(d) / n, 4), round(m[250], 4), round(m[9750], 4)]
out = {}
for base, cand in [("C4-def", "C6-sem"), ("C4-sem", "C6-sem"), ("A-def", "C6-sem"), ("C4-def", "C4-sem"), ("C4-def", "C6-off")]:
    ids = list(R[cand]); B, C = R[base], R[cand]
    win = [i for i in ids if C[i]["strict"] and not B[i]["strict"]]; loss = [i for i in ids if B[i]["strict"] and not C[i]["strict"]]
    need = [i for i in ids if B[i]["needed"]]
    rec = [(C[i]["needed_returned"] - B[i]["needed_returned"]) / B[i]["needed"] for i in need]
    cats = sorted({R[cand][i]["category"] for i in ids})
    out[f"{base}->{cand}"] = {
        "n": len(ids), "strict": [sum(B[i]["strict"] for i in ids), sum(C[i]["strict"] for i in ids)],
        "wins": len(win), "losses": len(loss), "ties": len(ids) - len(win) - len(loss), "mcnemar_exact_p": round(mc(len(win), len(loss)), 6),
        "delta_strict_ci95": boot([int(C[i]["strict"]) - int(B[i]["strict"]) for i in ids]),
        "delta_needed_recall_per_query_ci95": boot(rec),
        "needed_returned": [sum(B[i]["needed_returned"] for i in ids), sum(C[i]["needed_returned"] for i in ids), sum(B[i]["needed"] for i in ids)],
        "extras": [sum(B[i]["extra"] for i in ids), sum(C[i]["extra"] for i in ids)],
        "excluded_returned": [sum(len(B[i]["excluded_returned"]) for i in ids), sum(len(C[i]["excluded_returned"]) for i in ids)],
        "by_category": {c: {"n": sum(1 for i in ids if C[i]["category"] == c),
                            "strict": [sum(B[i]["strict"] for i in ids if C[i]["category"] == c), sum(C[i]["strict"] for i in ids if C[i]["category"] == c)],
                            "needed_returned": [sum(B[i]["needed_returned"] for i in ids if C[i]["category"] == c), sum(C[i]["needed_returned"] for i in ids if C[i]["category"] == c), sum(B[i]["needed"] for i in ids if C[i]["category"] == c)]} for c in cats},
        "win_ids": win, "loss_ids": loss}
json.dump(out, open("out/paired.json", "w"), indent=1)
for k, v in out.items():
    print(k, {x: v[x] for x in ("strict", "wins", "losses", "mcnemar_exact_p", "delta_needed_recall_per_query_ci95", "needed_returned", "extras", "excluded_returned")})
print(json.dumps(out["C4-sem->C6-sem"]["by_category"]))
