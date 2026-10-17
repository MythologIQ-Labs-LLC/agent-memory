"""Paired per-query comparison of C9+sem (default selection) against C4, C4+sem, C6+sem and C8+sem on every set (#819 C9).

Strict wins/losses with an exact two-sided McNemar p-value, and totals of needed memories returned,
extras, no-answer queries returning something and safety violations.

    python compare_c9.py > comparison.json
"""
import json
from math import comb

SETS = (("c9set", "gate"), ("c8set", "diag"), ("c7set", "diag"), ("c6diag", "diag"), ("c5dev", "diag"), ("gen", "diag"))
ARMS = ("C4off-rs", "C4sem-rs", "C6sem-rs", "C8sem-rs")


def rows(arm, src, st):
    return {r["id"]: r for r in json.load(open(f"{src}/{arm}-{st}.json"))["rows"]}


def mcnemar(w, l):
    n = w + l
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(w, l) + 1)) / 2 ** n)


def got(r):
    return sum(1 for n in r["needed"] if n in r["returned"])


report = {}
for st, src in SETS:
    c9 = rows("C9sem-rs", src, st)
    report[st] = {}
    for arm in ARMS:
        other = rows(arm, src, st)
        w = sum(1 for i in c9 if c9[i]["passed"] and not other[i]["passed"])
        l = sum(1 for i in c9 if other[i]["passed"] and not c9[i]["passed"])
        report[st][f"C9sem vs {arm}"] = {
            "strict": [sum(r["passed"] for r in c9.values()), sum(r["passed"] for r in other.values())],
            "strict_wins": w, "strict_losses": l, "mcnemar_p": round(mcnemar(w, l), 4),
            "needed_returned": [sum(map(got, c9.values())), sum(map(got, other.values()))],
            "needed": sum(len(r["needed"]) for r in c9.values()),
            "extras": [sum(len(r["extra"]) for r in c9.values()), sum(len(r["extra"]) for r in other.values())],
            "no_answer_returning": [sum(1 for r in c9.values() if not r["needed"] and r["returned"]),
                                    sum(1 for r in other.values() if not r["needed"] and r["returned"])],
            "safety_violations_c9": sum(len(r.get("violations", [])) for r in c9.values()),
        }
print(json.dumps(report, indent=1))
