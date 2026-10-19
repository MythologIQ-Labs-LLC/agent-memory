"""Recompute e4 paired comparisons from the cohort author's text-free per-case file (method of tools/paired.py)."""
import json, math, random, sys
d = json.load(open(sys.argv[1])); C = d["cases"]
def mc(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
def boot(x, reps=10000, seed=819):
    if not x: return None
    r = random.Random(seed); n = len(x)
    m = sorted(sum(x[r.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return [round(sum(x) / n, 4), round(m[int(.025 * reps)], 4), round(m[int(.975 * reps)], 4)]
F = ("strict_pass", "precision", "recall", "returned_count", "isolation_leaks", "forgotten_leaks", "stale_returned", "eval_failure")
out = {"source_sha256_note": "e4-percase-textfree.json from bdbd8a63", "c6_off_identical_to_c4_all_fields": sum(1 for c in C if all(c["C6_off"][f] == c["C4"][f] for f in F)),
       "arms": {}, "pairs": {}}
for a in ("A", "C4", "C6_off", "C4_sem", "C6_sem"):
    rec = [c[a]["recall"] for c in C if c[a]["recall"] is not None]; pr = [c[a]["precision"] for c in C if c[a]["precision"] is not None]
    out["arms"][a] = {"strict": sum(c[a]["strict_pass"] for c in C), "mean_recall": round(sum(rec) / len(rec), 4), "mean_precision": round(sum(pr) / len(pr), 4),
                      "leaks": sum(c[a]["isolation_leaks"] + c[a]["forgotten_leaks"] + c[a]["stale_returned"] for c in C),
                      "eval_failures": sum(c[a]["eval_failure"] for c in C), "mean_returned": round(sum(c[a]["returned_count"] for c in C) / len(C), 3)}
for b, a in (("C4", "C6_sem"), ("C4_sem", "C6_sem"), ("A", "C6_sem"), ("C4", "C4_sem"), ("C4", "C6_off")):
    w = [c["case_id"] for c in C if c[a]["strict_pass"] and not c[b]["strict_pass"]]
    l = [c["case_id"] for c in C if c[b]["strict_pass"] and not c[a]["strict_pass"]]
    cats = sorted({c["category"] for c in C})
    out["pairs"][f"{b}->{a}"] = {
        "wins": len(w), "losses": len(l), "mcnemar_exact_p": round(mc(len(w), len(l)), 6),
        "delta_strict_ci95": boot([int(c[a]["strict_pass"]) - int(c[b]["strict_pass"]) for c in C]),
        "delta_recall_ci95": boot([c[a]["recall"] - c[b]["recall"] for c in C if c[a]["recall"] is not None and c[b]["recall"] is not None]),
        "delta_precision_ci95": boot([c[a]["precision"] - c[b]["precision"] for c in C if c[a]["precision"] is not None and c[b]["precision"] is not None]),
        "by_category": {k: {"n": sum(1 for c in C if c["category"] == k),
                            "wins": sum(1 for c in C if c["category"] == k and c["case_id"] in w), "losses": sum(1 for c in C if c["category"] == k and c["case_id"] in l),
                            "recall": [None if not any(c[x]["recall"] is not None for c in C if c["category"] == k) else
                                       round(sum(c[x]["recall"] for c in C if c["category"] == k and c[x]["recall"] is not None) / sum(1 for c in C if c["category"] == k and c[x]["recall"] is not None), 4) for x in (b, a)]} for k in cats},
        "win_case_ids": w, "loss_case_ids": l}
json.dump(out, open(sys.argv[2], "w"), indent=1)
print("C6_off == C4 on all fields:", out["c6_off_identical_to_c4_all_fields"], "/", len(C))
for a, v in out["arms"].items(): print(a, v)
for k, v in out["pairs"].items(): print(k, {x: v[x] for x in ("wins", "losses", "mcnemar_exact_p", "delta_strict_ci95", "delta_recall_ci95", "delta_precision_ci95")})
print(json.dumps({k: v for k, v in out["pairs"]["C4_sem->C6_sem"]["by_category"].items()}))
