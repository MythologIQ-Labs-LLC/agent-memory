"""Evaluate the preregistered C7 gate on the development set (R1-R4, S1-S2, I1, I4).

Comparators are the diagnosis runs (``diag/``): C4+sem ``ranked_prefix``, C6+sem
``relevance_sufficient`` and C4 with the route off. The candidate runs are in ``gate/``.
Out-of-sample R5 and the remaining invariants are evaluated by ``../oos/gate_oos.py`` and the
tests.

    python gate_c7.py > gate/gate-dev.json
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(path):
    return {r["id"]: r for r in json.load(open(HERE / path))["rows"]}


def top5_needed(rows):
    return sum(1 for r in rows.values() for n in r["needed"].values() if n["rank"] and n["rank"] <= 5)


def cover(rows, k):
    return sum(1 for r in rows.values() if r["needed"] and r["coverage"][f"@{k}"])


c4rp, c7rp = load("diag/C4-required-ranked_prefix.json"), load("gate/C7-required-ranked_prefix.json")
c6rs, c7rs = load("diag/C6-required-relevance_sufficient.json"), load("gate/C7-required-relevance_sufficient.json")
offs = {mode: (load(f"diag/C4-off-{mode}.json"), load(f"gate/C7-off-{mode}.json")) for mode in ("ranked_prefix", "relevance_sufficient")}

lost5 = [q for q in c4rp if c4rp[q]["coverage"]["@5"] and not c7rp[q]["coverage"]["@5"]]
gained5 = [q for q in c4rp if c7rp[q]["coverage"]["@5"] and not c4rp[q]["coverage"]["@5"]]
gate = {
    "R1 all needed in top 5 >= 22": [cover(c7rp, 5), cover(c4rp, 5), cover(c7rp, 5) >= 22],
    "R2 needed in top 5 >= 39": [top5_needed(c7rp), top5_needed(c4rp), top5_needed(c7rp) >= 39],
    "R3 all needed in top 10 >= 24": [cover(c7rp, 10), cover(c4rp, 10), cover(c7rp, 10) >= 24],
    "R3 all needed in top 3 >= 14": [cover(c7rp, 3), cover(c4rp, 3), cover(c7rp, 3) >= 14],
    "R4 queries losing top-5 coverage <= 2": [len(lost5), lost5, len(lost5) <= 2],
}
set_diff = []
for q in c6rs:
    a, b = set(c6rs[q]["returned"]), set(c7rs[q]["returned"])
    if a != b:
        set_diff.append({"id": q, "c6": sorted(a), "c7": sorted(b), "c6_budget_bound": len(c6rs[q]["returned"]) >= 10})
strict = lambda rows: sum(r["passed"] for r in rows.values())  # noqa: E731
extras = lambda rows: sum(len(r["extra"]) for r in rows.values())  # noqa: E731
abst = lambda rows: sum(1 for r in rows.values() if not r["needed"] and r["returned"])  # noqa: E731
gate["S1 returned sets equal C6+sem (except budget-bound)"] = [len([d for d in set_diff if not d["c6_budget_bound"]]), set_diff,
                                                              not [d for d in set_diff if not d["c6_budget_bound"]]]
gate["S2 strict >= C6+sem"] = [strict(c7rs), strict(c6rs), strict(c7rs) >= strict(c6rs)]
gate["S2 extras <= C6+sem"] = [extras(c7rs), extras(c6rs), extras(c7rs) <= extras(c6rs)]
gate["S2 no-answer returning <= C6+sem"] = [abst(c7rs), abst(c6rs), abst(c7rs) <= abst(c6rs)]
for mode, (c4, c7) in offs.items():
    diff = [q for q in c4 if (c4[q]["top10"], c4[q]["returned"]) != (c7[q]["top10"], c7[q]["returned"])]
    gate[f"I1 route off equals C4 ({mode}: top 10 and returned)"] = [len(diff), diff, not diff]
newer = lambda rows: sum(1 for r in rows.values() if r["newer_first"])  # noqa: E731
gate["I4 newer-first conflicts >= C4 (2)"] = [newer(c7rp), newer(c4rp), newer(c7rp) >= newer(c4rp)]
gate["I4 newer-first conflicts (relevance_sufficient)"] = [newer(c7rs), newer(c6rs), newer(c7rs) >= newer(c6rs)]
summary = {"gate": gate, "gained_top5_coverage": gained5,
           "c7_summary_rp": json.load(open(HERE / "gate/C7-required-ranked_prefix.json"))["summary"],
           "c7_summary_rs": json.load(open(HERE / "gate/C7-required-relevance_sufficient.json"))["summary"]}
print(json.dumps(summary, indent=1))
