"""Evaluate the preregistered C8 gate on the C8 development set (R1-R4, S1-S2, I1, restated I4).

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


c4rp, c8rp = load("diag/C4-required-ranked_prefix.json"), load("gate/C8-required-ranked_prefix.json")
c6rs, c8rs = load("diag/C6-required-relevance_sufficient.json"), load("gate/C8-required-relevance_sufficient.json")
offs = {mode: (load(f"diag/C4-off-{mode}.json"), load(f"gate/C8-off-{mode}.json")) for mode in ("ranked_prefix", "relevance_sufficient")}

lost5 = [q for q in c4rp if c4rp[q]["coverage"]["@5"] and not c8rp[q]["coverage"]["@5"]]
gained5 = [q for q in c4rp if c8rp[q]["coverage"]["@5"] and not c4rp[q]["coverage"]["@5"]]
gate = {
    "R1 all needed in top 5 >= C4+sem + 3": [cover(c8rp, 5), cover(c4rp, 5), cover(c8rp, 5) >= cover(c4rp, 5) + 3],
    "R2 needed in top 5 >= C4+sem + 6": [top5_needed(c8rp), top5_needed(c4rp), top5_needed(c8rp) >= top5_needed(c4rp) + 6],
    "R3 all needed in top 10 >= C4+sem": [cover(c8rp, 10), cover(c4rp, 10), cover(c8rp, 10) >= cover(c4rp, 10)],
    "R3 all needed in top 3 >= C4+sem": [cover(c8rp, 3), cover(c4rp, 3), cover(c8rp, 3) >= cover(c4rp, 3)],
    "R4 queries losing top-5 coverage <= 2": [len(lost5), lost5, len(lost5) <= 2],
}
set_diff = []
for q in c6rs:
    a, b = set(c6rs[q]["returned"]), set(c8rs[q]["returned"])
    if a != b:
        set_diff.append({"id": q, "c6": sorted(a), "c8": sorted(b), "c6_budget_bound": len(c6rs[q]["returned"]) >= 10})
strict = lambda rows: sum(r["passed"] for r in rows.values())  # noqa: E731
extras = lambda rows: sum(len(r["extra"]) for r in rows.values())  # noqa: E731
abst = lambda rows: sum(1 for r in rows.values() if not r["needed"] and r["returned"])  # noqa: E731
gate["S1 returned sets equal C6+sem (except budget-bound)"] = [len([d for d in set_diff if not d["c6_budget_bound"]]), set_diff,
                                                              not [d for d in set_diff if not d["c6_budget_bound"]]]
gate["S2 strict >= C6+sem"] = [strict(c8rs), strict(c6rs), strict(c8rs) >= strict(c6rs)]
gate["S2 extras <= C6+sem"] = [extras(c8rs), extras(c6rs), extras(c8rs) <= extras(c6rs)]
gate["S2 no-answer returning <= C6+sem"] = [abst(c8rs), abst(c6rs), abst(c8rs) <= abst(c6rs)]
for mode, (c4, c7) in offs.items():
    diff = [q for q in c4 if (c4[q]["top10"], c4[q]["returned"]) != (c7[q]["top10"], c7[q]["returned"])]
    gate[f"I1 route off equals C4 ({mode}: top 10 and returned)"] = [len(diff), diff, not diff]
newer = lambda rows: sum(1 for r in rows.values() if r["kind"] == "conflict" and r["newer_first"])  # noqa: E731
gate["measured only: incidental newer-first, unspecified intent (C4+sem rp / C8 rp / C6+sem rs / C8 rs)"] = [
    newer(c4rp), newer(c8rp), newer(c6rs), newer(c8rs), True]
c6rp = load("diag/C6-required-ranked_prefix.json")
for label, base, cand in (("ranked_prefix", c6rp, c8rp), ("relevance_sufficient", c6rs, c8rs)):
    broken = [q for q, r in base.items() if r["kind"] == "conflict_declared" and r["newer_first"] and not cand[q]["newer_first"]]
    temporal = [q for q, r in base.items() if r["kind"] == "conflict_declared" and r["pair"]
                and len(set(r["pair"]["applicability"])) > 1]
    gate[f"I4' declared conflicts: C8 keeps every preferred-first ordering C6+sem has ({label})"] = [
        len(broken), {"broken": broken, "temporally_decided_pairs_in_C6": len(temporal),
                      "c6_preferred_first": sum(1 for r in base.values() if r["kind"] == "conflict_declared" and r["newer_first"]),
                      "c8_preferred_first": sum(1 for r in cand.values() if r["kind"] == "conflict_declared" and r["newer_first"])},
        not broken]
summary = {"gate": gate, "gained_top5_coverage": gained5,
           "c8_summary_rp": json.load(open(HERE / "gate/C8-required-ranked_prefix.json"))["summary"],
           "c8_summary_rs": json.load(open(HERE / "gate/C8-required-relevance_sufficient.json"))["summary"]}
print(json.dumps(summary, indent=1))
