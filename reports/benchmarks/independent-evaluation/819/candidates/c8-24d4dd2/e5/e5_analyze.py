"""e5 analysis: per-arm summaries, paired comparisons, and a discovery / ranking / selection decomposition.

usage: e5_analyze.py RESULTS_DIR OUT.json
Nothing is re-scored: strict, recall, ranks and returned lists come from the sealed harness output.
"""
import json, math, random, statistics, sys
from pathlib import Path

ARMS = ["c4-def", "c4-sem-rs", "c4-sem-rp", "c6-sem-rs", "c6-sem-rp", "c8-sem-rs", "c8-sem-rp", "c8-off"]
PAIRS = [("c4-sem-rs", "c8-sem-rs"), ("c4-sem-rp", "c8-sem-rp"), ("c6-sem-rs", "c8-sem-rs"), ("c6-sem-rp", "c8-sem-rp"),
         ("c4-def", "c8-sem-rs"), ("c4-def", "c4-sem-rs"), ("c4-sem-rs", "c6-sem-rs"), ("c8-sem-rs", "c8-sem-rp"), ("c4-def", "c8-off")]


def mc(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def boot(x, reps=10000, seed=819):
    if not x: return None
    r = random.Random(seed); n = len(x)
    m = sorted(sum(x[r.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return [round(sum(x) / n, 4), round(m[int(.025 * reps)], 4), round(m[int(.975 * reps)], 4)]


def pos(lst, ref):
    return lst.index(ref) + 1 if ref in lst else None


def decompose(r):
    """discovery: needed admitted at all; depth: needed in admitted top-k; selection: needed returned given admitted."""
    must = r["must"]
    if not must: return None
    ranks = r["must_rank_in_admitted"]
    admitted = [m for m in must if ranks.get(m) is not None]
    returned = [m for m in must if m in r["returned"]]
    return {"needed": len(must), "admitted": len(admitted), "returned": len(returned),
            "in_top5": sum(1 for m in must if ranks.get(m) is not None and ranks[m] <= 5),
            "in_top10": sum(1 for m in must if ranks.get(m) is not None and ranks[m] <= 10),
            "returned_of_admitted": len([m for m in returned if m in admitted])}


def special(r):
    """Category-specific behaviour read from the returned list and the admitted top 10."""
    c, top, ret = r["category"], r["admitted_top10"], r["returned"]
    out = {}
    if c in ("near_miss_no_answer", "near_miss_with_answer"):
        out["near_returned"] = "near" in ret
        out["near_rank1_admitted"] = bool(top) and top[0] == "near"
        if c == "near_miss_with_answer":
            pa, pn = pos(top, "ans"), pos(top, "near")
            out["near_above_answer"] = pn is not None and (pa is None or pn < pa)
    if c == "question_shaped":
        pq = pos(top, "qs"); ans = [pos(top, m) for m in r["must"]]
        out["qs_returned"] = "qs" in ret
        out["qs_rank1_admitted"] = pq == 1
        out["qs_above_an_answer"] = pq is not None and any(a is None or pq < a for a in ans)
    if c == "temporal_ordering":
        out["newer_first_returned"] = bool(ret) and ret[0] == "new"
        pn, po = pos(top, "new"), pos(top, "old")
        out["newer_above_older_admitted"] = pn is not None and (po is None or pn < po)
    if c == "temporal_as_of":
        ref = r["must"][0]
        out["earlier_first_returned"] = bool(ret) and ret[0] == ref
    if c == "temporal_current":
        out["stale_returned"] = any(x for x in ret if "@" not in x and not x.startswith("f"))
    return out


def summarise(rows):
    d = [x for x in (decompose(r) for r in rows) if x]
    tot = {k: sum(x[k] for x in d) for k in ("needed", "admitted", "returned", "in_top5", "in_top10", "returned_of_admitted")}
    sp = {}
    for r in rows:
        for k, v in special(r).items():
            sp.setdefault(f"{r['category']}.{k}", 0); sp[f"{r['category']}.{k}"] += int(bool(v))
    ms = sorted(r["ms"] for r in rows)
    return {"queries": len(rows), "strict": sum(r["strict"] for r in rows), "needed": tot["needed"],
            "discovery_rate": round(tot["admitted"] / tot["needed"], 4) if tot["needed"] else None,
            "depth_top5_rate": round(tot["in_top5"] / tot["needed"], 4) if tot["needed"] else None,
            "depth_top10_rate": round(tot["in_top10"] / tot["needed"], 4) if tot["needed"] else None,
            "returned_rate": round(tot["returned"] / tot["needed"], 4) if tot["needed"] else None,
            "selection_completeness": round(tot["returned_of_admitted"] / tot["admitted"], 4) if tot["admitted"] else None,
            "extras": sum(r["extras"] for r in rows), "mean_returned": round(statistics.mean(len(r["returned"]) for r in rows), 3),
            "excluded_returned": sum(len(r["excluded_returned"]) for r in rows), "excluded_text": sum(len(r["excluded_text"]) for r in rows),
            "order_violations": sum(1 for r in rows if not r["order_ok"]),
            "abstained": sum(1 for r in rows if r["abstained"]),
            "ms_p50": ms[len(ms) // 2], "ms_p95": ms[int(.95 * (len(ms) - 1))], "behaviour": sp}


def main():
    d = Path(sys.argv[1]); R = {}
    for a in ARMS + ["c8-sem-rs-rep2"]:
        p = d / f"{a}.json"
        if p.exists():
            j = json.load(open(p)); R[a] = {r["id"]: r for r in j["rows"]}; R[a]["__summary"] = j["summary"]
    out = {"arms": {}, "by_category": {}, "pairs": {}, "determinism": {}, "equivalence": {}}
    cats = sorted({r["category"] for r in R["c4-def"].values() if isinstance(r, dict) and "category" in r})
    for a in R:
        rows = [r for k, r in R[a].items() if k != "__summary"]
        out["arms"][a] = summarise(rows)
        out["arms"][a]["op_failures"] = len(R[a]["__summary"]["op_failures"]); out["arms"][a]["eval_failures"] = len(R[a]["__summary"]["eval_failures"])
        out["by_category"][a] = {c: summarise([r for r in rows if r["category"] == c]) for c in cats}
    for b, c in PAIRS:
        if b not in R or c not in R: continue
        ids = sorted(k for k in R[b] if k != "__summary")
        B, C = R[b], R[c]
        w = [i for i in ids if C[i]["strict"] and not B[i]["strict"]]; l = [i for i in ids if B[i]["strict"] and not C[i]["strict"]]
        rec = [C[i]["recall"] - B[i]["recall"] for i in ids if B[i]["recall"] is not None]
        d5 = [C[i]["depth_recall"]["5"] - B[i]["depth_recall"]["5"] for i in ids if B[i]["depth_recall"]["5"] is not None]
        d10 = [C[i]["depth_recall"]["10"] - B[i]["depth_recall"]["10"] for i in ids if B[i]["depth_recall"]["10"] is not None]
        disc = [sum(1 for m in C[i]["must"] if C[i]["must_rank_in_admitted"][m] is not None) / len(C[i]["must"]) -
                sum(1 for m in B[i]["must"] if B[i]["must_rank_in_admitted"][m] is not None) / len(B[i]["must"]) for i in ids if B[i]["must"]]
        allneed5 = lambda X, i: X[i]["depth_recall"]["5"] == 1.0
        out["pairs"][f"{b}->{c}"] = {
            "wins": len(w), "losses": len(l), "mcnemar_exact_p": round(mc(len(w), len(l)), 6),
            "delta_strict_ci95": boot([int(C[i]["strict"]) - int(B[i]["strict"]) for i in ids]),
            "delta_recall_ci95": boot(rec), "delta_discovery_ci95": boot(disc),
            "delta_depth5_ci95": boot(d5), "delta_depth10_ci95": boot(d10),
            "all_needed_top5": {"wins": sum(1 for i in ids if B[i]["must"] and allneed5(C, i) and not allneed5(B, i)),
                                "losses": sum(1 for i in ids if B[i]["must"] and allneed5(B, i) and not allneed5(C, i))},
            "identical_returned": sum(1 for i in ids if B[i]["returned"] == C[i]["returned"]),
            "identical_returned_set": sum(1 for i in ids if set(B[i]["returned"]) == set(C[i]["returned"])),
            "identical_admitted_top10": sum(1 for i in ids if B[i]["admitted_top10"] == C[i]["admitted_top10"]),
            "by_category": {cat: {"wins": sum(1 for i in w if B[i]["category"] == cat), "losses": sum(1 for i in l if B[i]["category"] == cat)} for cat in cats},
            "win_ids": w, "loss_ids": l}
    if "c8-sem-rs-rep2" in R:
        ids = [k for k in R["c8-sem-rs"] if k != "__summary"]
        out["determinism"]["c8-sem-rs_vs_rep2"] = {
            "identical_returned": sum(1 for i in ids if R["c8-sem-rs"][i]["returned"] == R["c8-sem-rs-rep2"][i]["returned"]),
            "identical_admitted_top10": sum(1 for i in ids if R["c8-sem-rs"][i]["admitted_top10"] == R["c8-sem-rs-rep2"][i]["admitted_top10"]),
            "identical_semantic": sum(1 for i in ids if R["c8-sem-rs"][i]["semantic"] == R["c8-sem-rs-rep2"][i]["semantic"]), "n": len(ids)}
    for x, y in (("c4-def", "c8-off"),):
        if x in R and y in R:
            ids = [k for k in R[x] if k != "__summary"]
            out["equivalence"][f"{x}=={y}"] = {"returned": sum(1 for i in ids if R[x][i]["returned"] == R[y][i]["returned"]),
                                              "admitted_top10": sum(1 for i in ids if R[x][i]["admitted_top10"] == R[y][i]["admitted_top10"]), "n": len(ids)}
    json.dump(out, open(sys.argv[2], "w"), indent=1)
    print(f'{"arm":16}{"strict":>7}{"disc":>7}{"top5":>7}{"top10":>7}{"ret":>7}{"selc":>7}{"extra":>6}{"leak":>5}{"ordv":>5}{"p50":>8}')
    for a, s in out["arms"].items():
        print(f'{a:16}{s["strict"]:>7}{s["discovery_rate"]:>7}{s["depth_top5_rate"]:>7}{s["depth_top10_rate"]:>7}{s["returned_rate"]:>7}{s["selection_completeness"]:>7}{s["extras"]:>6}{s["excluded_returned"]+s["excluded_text"]:>5}{s["order_violations"]:>5}{s["ms_p50"]:>8}')
    for k, v in out["pairs"].items():
        print(k, {x: v[x] for x in ("wins", "losses", "mcnemar_exact_p", "delta_recall_ci95", "delta_depth5_ci95", "delta_discovery_ci95", "all_needed_top5", "identical_returned_set")})
    print(json.dumps(out["determinism"]), json.dumps(out["equivalence"]))


main()
