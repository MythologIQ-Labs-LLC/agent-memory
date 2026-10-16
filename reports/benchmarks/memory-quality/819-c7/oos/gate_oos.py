"""Out-of-sample C7 gate checks (R5, S1/S2 and I1) on the C6 development union and the C6 reviewer set.

Neither set was used in C7's design or feasibility.
- R5: under ``ranked_prefix`` with the route on, needed recall@10 >= C4+sem, and needed memories in
  the top 5 >= C4+sem - 2, per set.
- S1/S2: under ``relevance_sufficient`` with the route on, the returned sets equal C6+sem's (except
  where the budget binds), and strict, extras and no-answer queries returning something are no
  worse than C6+sem.
- I1: with the route off, returned lists equal C6's.

    python gate_oos.py > gate-oos.json
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
C6 = HERE.parents[0] / ".." / "819-c6"


def expectations(paths):
    out = {}
    for path in paths:
        data = json.load(open(path))
        scenarios = data["scenarios"] if isinstance(data, dict) else data
        for s in scenarios:
            for q in s["queries"]:
                out[q["id"]] = q["expect"]
    return out


def runner_rows(path):
    return {q["id"]: q["returned"] for s in json.load(open(path))["scenarios"] for q in s["queries"]}


def harness_rows(path):
    return {q["id"]: q["returned"] for q in json.load(open(path))}


def depth(rows, exp):
    needed = sum(len(exp[q]["must_include"]) for q in rows)
    at10 = sum(len(set(r[:10]) & set(exp[q]["must_include"])) for q, r in rows.items())
    at5 = sum(len(set(r[:5]) & set(exp[q]["must_include"])) for q, r in rows.items())
    return {"needed": needed, "recall@10": round(at10 / needed, 4), "needed_top5": at5}


def selection(rows, exp):
    def allowed(q):
        return set(exp[q]["must_include"]) | set(exp[q].get("may_include") or [])
    strict = sum(1 for q, r in rows.items() if set(exp[q]["must_include"]) <= set(r) and set(r) <= allowed(q)
                 and not ({x["ref"] if isinstance(x, dict) else x for x in exp[q].get("must_exclude") or []} & set(r)))
    extras = sum(len([x for x in r if x not in allowed(q)]) for q, r in rows.items())
    no_answer = sum(1 for q, r in rows.items() if not exp[q]["must_include"] and set(r) - allowed(q))
    return {"strict": strict, "extras": extras, "no_answer_returning": no_answer}


report = {}
union_exp = expectations([C6 / "dev" / "diag-scenarios.json", C6 / "dev" / "c5-dev-scenarios.json"])
gen_exp = expectations([C6 / "review" / "gen.json"])
sets = {
    "c6-dev-union": dict(
        exp=union_exp,
        rp=({**runner_rows(HERE / "C4-sem-rp-diag.json"), **runner_rows(HERE / "C4-sem-rp-c5-dev.json")},
            {**runner_rows(HERE / "C7-sem-rp-diag.json"), **runner_rows(HERE / "C7-sem-rp-c5-dev.json")}),
        rs=({**runner_rows(C6 / "dev" / "runs" / "C6-sem-diag.json"), **runner_rows(C6 / "dev" / "runs" / "C6-sem-c5-dev.json")},
            {**runner_rows(HERE / "C7-sem-diag.json"), **runner_rows(HERE / "C7-sem-c5-dev.json")}),
        off=({**runner_rows(C6 / "dev" / "runs" / "C6-off-diag.json"), **runner_rows(C6 / "dev" / "runs" / "C6-off-c5-dev.json")},
             {**runner_rows(HERE / "C7-off-diag.json"), **runner_rows(HERE / "C7-off-c5-dev.json")}),
    ),
    "c6-reviewer-set": dict(
        exp=gen_exp,
        rp=(harness_rows(C6 / "review" / "outputs" / "runs-gen-c4-rp.json"), harness_rows(HERE / "C7-gen-rp.json")),
        rs=(harness_rows(C6 / "review" / "after-fixes" / "c6fix-gen-required.json"), harness_rows(HERE / "C7-gen-required.json")),
        off=(harness_rows(C6 / "review" / "outputs" / "runs-gen-c4-off.json"), harness_rows(HERE / "C7-gen-off.json")),
    ),
}
for name, s in sets.items():
    exp = s["exp"]
    base_rp, c7_rp = s["rp"]
    d4, d7 = depth(base_rp, exp), depth(c7_rp, exp)
    base_rs, c7_rs = s["rs"]
    sel6, sel7 = selection(base_rs, exp), selection(c7_rs, exp)
    set_diff = [q for q in base_rs if set(base_rs[q]) != set(c7_rs[q]) and len(base_rs[q]) < 10]
    order_only = sum(1 for q in base_rs if set(base_rs[q]) == set(c7_rs[q]) and base_rs[q] != c7_rs[q])
    off_diff = [q for q in s["off"][0] if s["off"][0][q] != s["off"][1][q]]
    report[name] = {
        "ranked_prefix C4+sem": d4, "ranked_prefix C7+sem": d7,
        "R5 recall@10 >= C4+sem": d7["recall@10"] >= d4["recall@10"],
        "R5 needed_top5 >= C4+sem - 2": d7["needed_top5"] >= d4["needed_top5"] - 2,
        "relevance_sufficient C6+sem": sel6, "relevance_sufficient C7+sem": sel7,
        "S1 returned-set differences (not budget-bound)": set_diff,
        "returned order changed only": order_only,
        "S2 no worse": sel7["strict"] >= sel6["strict"] and sel7["extras"] <= sel6["extras"]
                        and sel7["no_answer_returning"] <= sel6["no_answer_returning"],
        "I1 route-off list differences": off_diff,
    }
print(json.dumps(report, indent=1))
