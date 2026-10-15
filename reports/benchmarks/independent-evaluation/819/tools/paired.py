"""Paired baseline-vs-candidate comparison for AMB, holdout and LongMemEval reports.

Usage: paired.py {amb|holdout|lme} BASE CAND [--plane session|turn] [--backend agent_memory]
Strict pass/fail is taken from each evaluator's own output; nothing is re-scored.
"""
import argparse, json, math, random, gzip


def load(p):
    return json.load(gzip.open(p) if p.endswith(".gz") else open(p))


def rows(kind, rep, plane=None, backend=None):
    out = {}
    if kind == "amb":
        for r in rep["results"]:
            m = r.get("meta") or {}
            out[r["query_id"]] = {"pass": bool(r["correct"]), "precision": m.get("retrieval_precision"),
                                  "recall": m.get("retrieval_recall"), "group": m.get("category"), "error": None,
                                  "latency": r.get("retrieve_time_ms")}
    elif kind == "holdout":
        for i, r in enumerate(rep["rows"]):
            out[f"{r['scenario_id']}#{r['query']}"] = {"pass": r["pass"], "precision": r.get("precision"), "recall": r.get("recall"),
                                                      "group": r["category"], "error": r.get("eval_failure"), "latency": r.get("latency_ms"),
                                                      "leaks": len(r.get("isolation_leak", [])) + len(r.get("forgotten_leak", [])) + len(r.get("stale_returned", []))}
    elif kind == "locomo":
        for x in rep["query_driven_multi_route"]["questions"]:
            m = x["at_k"]["10"]
            out[f"{x['sample_index']}#{x['question_index']}"] = {"pass": bool(m["hit"]), "precision": m["precision"], "recall": m["recall"],
                                                                "group": f"cat{x['category']}", "error": None, "latency": None}
    else:
        b = rep["planes"][plane]["backends"][backend]
        for r in b["rows"]:
            if r["status"] != "scored":
                continue
            met = r["metrics"][plane]
            key5 = "recall_all@5" if plane == "session" else "recall_all@10"
            out[r["question_id"]] = {"pass": met[key5] == 1.0, "precision": None, "recall": met[key5],
                                     "group": r["question_type"], "error": r.get("runtime_error"), "latency": None}
    return out


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def boot(diffs, reps=10000, seed=819):
    if not diffs:
        return None
    rnd = random.Random(seed)
    n = len(diffs)
    means = sorted(sum(diffs[rnd.randrange(n)] for _ in range(n)) / n for _ in range(reps))
    return [round(sum(diffs) / n, 4), round(means[int(0.025 * reps)], 4), round(means[int(0.975 * reps)], 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind"); ap.add_argument("base"); ap.add_argument("cand")
    ap.add_argument("--plane"); ap.add_argument("--backend", default="agent_memory"); ap.add_argument("--out")
    a = ap.parse_args()
    B = rows(a.kind, load(a.base), a.plane, a.backend); C = rows(a.kind, load(a.cand), a.plane, a.backend)
    keys = sorted(set(B) | set(C))
    cls = {}
    for k in keys:
        b, c = B.get(k), C.get(k)
        if b is None or c is None: cls[k] = "population_mismatch"
        elif c["error"]: cls[k] = "eval_failure_candidate"
        elif b["error"]: cls[k] = "eval_failure_baseline"
        elif b["pass"] and c["pass"]: cls[k] = "unchanged_pass"
        elif not b["pass"] and not c["pass"]: cls[k] = "unchanged_fail"
        elif c["pass"]: cls[k] = "improved"
        else: cls[k] = "regressed"
    paired = [k for k in keys if B.get(k) and C.get(k)]
    imp = sum(1 for k in keys if cls[k] == "improved"); reg = sum(1 for k in keys if cls[k] == "regressed")
    def dl(field):
        return [C[k][field] - B[k][field] for k in paired if B[k][field] is not None and C[k][field] is not None]
    groups = sorted({B[k]["group"] for k in paired})
    by = {g: {"n": sum(1 for k in paired if B[k]["group"] == g),
              "base_pass": sum(1 for k in paired if B[k]["group"] == g and B[k]["pass"]),
              "cand_pass": sum(1 for k in paired if C[k]["group"] == g and C[k]["pass"]),
              "improved": sum(1 for k in paired if B[k]["group"] == g and cls[k] == "improved"),
              "regressed": sum(1 for k in paired if B[k]["group"] == g and cls[k] == "regressed")} for g in groups}
    res = {"kind": a.kind, "plane": a.plane, "paired_n": len(paired),
           "base_pass": sum(1 for k in paired if B[k]["pass"]), "cand_pass": sum(1 for k in paired if C[k]["pass"]),
           "classes": {v: sum(1 for k in keys if cls[k] == v) for v in sorted(set(cls.values()))},
           "mcnemar_exact_p": round(mcnemar_exact(imp, reg), 6),
           "delta_pass_rate_ci95": boot([int(C[k]["pass"]) - int(B[k]["pass"]) for k in paired]),
           "delta_precision_ci95": boot(dl("precision")), "delta_recall_ci95": boot(dl("recall")),
           "by_group": by, "improved_ids": [k for k in keys if cls[k] == "improved"], "regressed_ids": [k for k in keys if cls[k] == "regressed"]}
    if a.kind == "holdout":
        res["cand_hard_gate_leaks"] = sum(C[k].get("leaks", 0) for k in paired)
        res["base_hard_gate_leaks"] = sum(B[k].get("leaks", 0) for k in paired)
    print(json.dumps({k: v for k, v in res.items() if k not in ("improved_ids", "regressed_ids", "by_group")}, indent=1))
    if a.out: json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
