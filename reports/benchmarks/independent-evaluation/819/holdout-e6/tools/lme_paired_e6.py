"""#819 e6 LongMemEval-S paired comparison (public benchmark; runner output only, nothing re-scored).

usage: lme_paired_e6.py BASE.json[.gz] CAND.json[.gz] OUT.json
For each plane (session, turn) and k in {3, 5, 10, 50}: mean recall_all@k over questions scored in
both runs, exact two-sided McNemar on recall_all@k == 1.0, and a paired percentile bootstrap 95% CI
(10,000 resamples, seed 819) on the mean difference.
"""
import gzip
import json
import math
import random
import sys

KS, B, SEED = (3, 5, 10, 50), 10000, 819


def load(p):
    return json.load(gzip.open(p) if p.endswith(".gz") else open(p))


def rows(rep, plane):
    b = rep["planes"][plane]["backends"]["agent_memory"]
    return {r["question_id"]: r["metrics"][plane] for r in b["rows"] if r["status"] == "scored"}


def mcnemar(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def boot(d):
    rng, n = random.Random(SEED), len(d)
    m = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return [round(m[int(0.025 * B)], 4), round(m[int(0.975 * B) - 1], 4)]


def main():
    base, cand, out = load(sys.argv[1]), load(sys.argv[2]), {}
    for plane in ("session", "turn"):
        A, C = rows(base, plane), rows(cand, plane)
        ids = sorted(set(A) & set(C))
        out[plane] = {"n": len(ids), "only_base": len(set(A) - set(C)), "only_cand": len(set(C) - set(A))}
        for k in KS:
            key = f"recall_all@{k}"
            a = [A[i][key] for i in ids]
            c = [C[i][key] for i in ids]
            wins = sum(1 for x, y in zip(a, c) if y == 1.0 and x != 1.0)
            losses = sum(1 for x, y in zip(a, c) if x == 1.0 and y != 1.0)
            d = [y - x for x, y in zip(a, c)]
            out[plane][key] = {"base": round(sum(a) / len(a), 4), "cand": round(sum(c) / len(c), 4),
                               "full_wins": wins, "full_losses": losses, "p_exact_mcnemar": mcnemar(wins, losses),
                               "delta_ci95": boot(d)}
    json.dump(out, open(sys.argv[3], "w"), indent=1, sort_keys=True)
    print(json.dumps({p: {k: (v["base"], v["cand"], v["full_wins"], v["full_losses"], round(v["p_exact_mcnemar"], 4))
                          for k, v in out[p].items() if k.startswith("recall")} for p in out}))


if __name__ == "__main__":
    main()
