"""Per-depth, per-question, latency and failure detail for paired LongMemEval-S reports (nothing is re-scored).

usage: lme_detail.py BASE.json[.gz] CAND.json[.gz] OUT.json [--names base,cand]
"""
import gzip, json, math, statistics, sys

DEPTHS = (1, 3, 5, 10, 30, 50)


def load(p):
    return json.load(gzip.open(p) if p.endswith(".gz") else open(p))


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def pct(xs, q):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))], 4) if xs else None


def main():
    bp, cp, outp = sys.argv[1:4]
    names = sys.argv[sys.argv.index("--names") + 1].split(",") if "--names" in sys.argv else ["base", "cand"]
    B, C = load(bp), load(cp)
    out = {"base": names[0], "cand": names[1], "identity": {}, "planes": {}}
    for n, rep in zip(names, (B, C)):
        e = rep["execution"]
        out["identity"][n] = {"revision": e.get("agent_memory_revision"), "dirty": e.get("agent_memory_worktree_dirty"),
                              "configuration": e.get("agent_memory_configuration"), "input_sha256": rep["input"]["sha256"],
                              "python": e.get("python"), "wall_seconds": e.get("wall_seconds"),
                              "resource": e.get("resource_consumption"), "semantic": e.get("semantic_retrieval") or e.get("agent_memory_semantic_retrieval")}
    for plane in ("session", "turn"):
        rb = {r["question_id"]: r for r in B["planes"][plane]["backends"]["agent_memory"]["rows"]}
        rc = {r["question_id"]: r for r in C["planes"][plane]["backends"]["agent_memory"]["rows"]}
        scored = [q for q in rb if rb[q]["status"] == "scored" and rc.get(q, {}).get("status") == "scored"]
        p = {"scored_paired": len(scored),
             "status_counts": {n: {s: sum(1 for r in R.values() if r["status"] == s) for s in sorted({r["status"] for r in R.values()})} for n, R in zip(names, (rb, rc))},
             "runtime_errors": {n: [q for q, r in R.items() if r.get("runtime_error")] for n, R in zip(names, (rb, rc))},
             "ingestion_failures": {n: sum(len(r.get("ingestion_failures") or []) for r in R.values()) for n, R in zip(names, (rb, rc))},
             "depth": {}, "latency": {}, "returned_count": {}, "identical_ranked_top": sum(1 for q in rb if q in rc and rb[q].get("ranked_top") == rc[q].get("ranked_top"))}
        for k in DEPTHS:
            key = f"recall_all@{k}"
            xb = [rb[q]["metrics"][plane][key] for q in scored]
            xc = [rc[q]["metrics"][plane][key] for q in scored]
            win = sum(1 for a, b in zip(xb, xc) if a < 1.0 and b == 1.0)
            loss = sum(1 for a, b in zip(xb, xc) if a == 1.0 and b < 1.0)
            p["depth"][key] = {names[0]: round(sum(xb) / len(xb), 4), names[1]: round(sum(xc) / len(xc), 4),
                               "wins": win, "losses": loss, "ties": len(scored) - win - loss, "mcnemar_exact_p": round(mcnemar(win, loss), 6)}
        for n, R in zip(names, (rb, rc)):
            rs = [r["recall_seconds"] for r in R.values() if r.get("recall_seconds") is not None]
            ig = [r["ingest_seconds"] for r in R.values() if r.get("ingest_seconds") is not None]
            p["latency"][n] = {"recall_p50_s": pct(rs, .5), "recall_p95_s": pct(rs, .95), "recall_max_s": pct(rs, 1.0),
                               "recall_mean_s": round(statistics.mean(rs), 4) if rs else None, "ingest_mean_s": round(statistics.mean(ig), 4) if ig else None}
            rcnt = [r.get("returned_count") or 0 for q, r in R.items() if q in scored]
            p["returned_count"][n] = {"mean": round(statistics.mean(rcnt), 3), "zero": sum(1 for x in rcnt if x == 0), "p50": pct(rcnt, .5)}
        p["per_question"] = [{"question_id": q, "type": rb[q]["question_type"], "gold": rb[q].get("gold"),
                              names[0]: {"ranked_top": rb[q].get("ranked_top"), "returned_count": rb[q].get("returned_count"),
                                         "recall_all": {k: rb[q]["metrics"][plane][f"recall_all@{k}"] for k in DEPTHS}, "recall_seconds": rb[q].get("recall_seconds")},
                              names[1]: {"ranked_top": rc[q].get("ranked_top"), "returned_count": rc[q].get("returned_count"),
                                         "recall_all": {k: rc[q]["metrics"][plane][f"recall_all@{k}"] for k in DEPTHS}, "recall_seconds": rc[q].get("recall_seconds")}}
                             for q in scored]
        out["planes"][plane] = p
    json.dump(out, open(outp, "w"), indent=1)
    for plane, p in out["planes"].items():
        print(plane, "paired", p["scored_paired"], "identical ranked_top", p["identical_ranked_top"], "errors", {k: len(v) for k, v in p["runtime_errors"].items()})
        for k, v in p["depth"].items():
            print("  ", k, v)
        print("   latency", p["latency"]); print("   returned", p["returned_count"])


main()
