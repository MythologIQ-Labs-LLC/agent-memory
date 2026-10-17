"""Paired LongMemEval-S comparison for #819 C9 (local runs; the evaluator's metric and protocol).

For each plane (session, turn) and depth (3, 5, 10, 50), over scored questions only: pass counts of
recall_all@k, improved/regressed pairs, exact two-sided McNemar p, and a 95% bootstrap CI (2,000
resamples, seed 819) of the mean recall_all@k delta. Also reports whether two runs return identical
ranked lists (``ranked_top``), which checks that C8 is reproduced locally.

    python lme_paired.py BASE.json[.gz] CANDIDATE.json[.gz] > out.json
"""
import gzip
import json
import random
import sys
from math import comb

DEPTHS = (3, 5, 10, 50)


def load(path):
    return json.load(gzip.open(path) if path.endswith(".gz") else open(path))


def mcnemar(w, l):
    n = w + l
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n)


base, cand = load(sys.argv[1]), load(sys.argv[2])
out = {"base": sys.argv[1], "candidate": sys.argv[2],
       "base_revision": base["execution"].get("agent_memory_revision"),
       "candidate_revision": cand["execution"].get("agent_memory_revision"), "planes": {}}
rng = random.Random(819)
for plane in ("session", "turn"):
    rb = {r["question_id"]: r for r in base["planes"][plane]["backends"]["agent_memory"]["rows"]}
    rc = {r["question_id"]: r for r in cand["planes"][plane]["backends"]["agent_memory"]["rows"]}
    ids = sorted(i for i in rb if rb[i]["status"] == "scored" and rc.get(i, {}).get("status") == "scored")
    plane_out = {"paired_n": len(ids),
                 "identical_ranked_top": sum(rb[i].get("ranked_top") == rc[i].get("ranked_top") for i in ids),
                 "runtime_errors": [sum(1 for r in rb.values() if r.get("runtime_error")),
                                    sum(1 for r in rc.values() if r.get("runtime_error"))]}
    for k in DEPTHS:
        key = f"recall_all@{k}"
        b = [rb[i]["metrics"][plane][key] for i in ids]
        c = [rc[i]["metrics"][plane][key] for i in ids]
        w = sum(1 for x, y in zip(b, c) if y > x)
        l = sum(1 for x, y in zip(b, c) if x > y)
        deltas = [y - x for x, y in zip(b, c)]
        boots = sorted(sum(rng.choice(deltas) for _ in deltas) / len(deltas) for _ in range(2000))
        plane_out[key] = {"base": round(sum(b) / len(b), 4), "candidate": round(sum(c) / len(c), 4),
                          "improved": w, "regressed": l, "mcnemar_p": round(mcnemar(w, l), 5),
                          "delta": round(sum(deltas) / len(deltas), 4),
                          "delta_ci95": [round(boots[49], 4), round(boots[1949], 4)],
                          "improved_ids": [i for i, x, y in zip(ids, b, c) if y > x],
                          "regressed_ids": [i for i, x, y in zip(ids, b, c) if x > y]}
    out["planes"][plane] = plane_out
print(json.dumps(out, indent=1))
