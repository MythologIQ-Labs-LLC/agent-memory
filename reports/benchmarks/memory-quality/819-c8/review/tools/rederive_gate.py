"""Independent re-derivation of R1-R4, S1-S2, I4' from the committed C8 run files (not using gate_c8.py)."""
import json, sys
from pathlib import Path
D = Path(sys.argv[1]) / "reports/benchmarks/memory-quality/819-c8/dev"
scen = {q["id"]: (q, sc) for sc in json.load(open(D / "c8-scenarios.json"))["scenarios"] for q in sc["queries"]}
def rows(p): return {r["id"]: r for r in json.load(open(D / p))["rows"]}
def ranks(r):  # re-derive from top10 only + needed rank field cross-check
    return r["top10"]
c4 = rows("diag/C4-required-ranked_prefix.json"); c8 = rows("gate/C8-required-ranked_prefix.json")
c6rs = rows("diag/C6-required-relevance_sufficient.json"); c8rs = rows("gate/C8-required-relevance_sufficient.json")
c6rp = rows("diag/C6-required-ranked_prefix.json")
def must(q): return scen[q][0]["expect"].get("must_include") or []
def cov(rs, k):  # all needed inside top k, using the needed rank recorded
    return sum(1 for q, r in rs.items() if must(q) and all((r["needed"][m]["rank"] or 999) <= k for m in must(q)))
def cov_top10(rs, k):  # same from the top10 list itself (independent field)
    return sum(1 for q, r in rs.items() if must(q) and all(m in r["top10"][:k] for m in must(q)))
def n5(rs): return sum(1 for q, r in rs.items() for m in must(q) if (r["needed"][m]["rank"] or 999) <= 5)
def n5_top10(rs): return sum(1 for q, r in rs.items() for m in must(q) if m in r["top10"][:5])
out = {}
for lab, rs in (("C4+sem rp", c4), ("C6+sem rp", c6rp), ("C8 rp", c8)):
    out[lab] = {"R1 cover@5": [cov(rs, 5), cov_top10(rs, 5)], "R2 needed@5": [n5(rs), n5_top10(rs)],
                "cover@3": cov_top10(rs, 3), "cover@10": cov_top10(rs, 10), "queries_with_needed": sum(1 for q in rs if must(q))}
out["R1 margin"] = cov_top10(c8, 5) - cov_top10(c4, 5)
out["R2 margin"] = n5_top10(c8) - n5_top10(c4)
out["R4 lost"] = [q for q in c4 if must(q) and all(m in c4[q]["top10"][:5] for m in must(q)) and not all(m in c8[q]["top10"][:5] for m in must(q))]
# per-kind breakdown of gains
from collections import defaultdict
kind = defaultdict(lambda: [0, 0, 0])
for q in c8:
    if not must(q): continue
    k = scen[q][0]["kind"]
    kind[k][0] += 1
    kind[k][1] += all(m in c4[q]["top10"][:5] for m in must(q))
    kind[k][2] += all(m in c8[q]["top10"][:5] for m in must(q))
out["cover@5 by kind [n, C4+sem, C8]"] = dict(kind)
# I4'
i4 = []
for q, r in c6rp.items():
    if scen[q][0]["kind"] != "conflict_declared": continue
    p = r["pair"]
    i4.append({"id": q, "C6rp": r["newer_first"], "C8rp": c8[q]["newer_first"], "C6rs": c6rs[q]["newer_first"], "C8rs": c8rs[q]["newer_first"],
               "applicability_C6": p["applicability"], "ranks_C6": p["ranks"], "ranks_C8": c8[q]["pair"]["ranks"]})
out["I4' rows"] = i4
out["I4' pairs with equal applicability (where a temporal ORDER stage, not the tier, could decide)"] = sum(1 for x in i4 if len(set(x["applicability_C6"])) == 1)
# S1
s1 = [q for q in c6rs if set(c6rs[q]["returned"]) != set(c8rs[q]["returned"])]
out["S1 differing returned sets"] = s1
out["S1 order-only differences"] = [q for q in c6rs if c6rs[q]["returned"] != c8rs[q]["returned"] and q not in s1]
out["budget-binding C6 queries (returned==10)"] = [q for q in c6rs if len(c6rs[q]["returned"]) >= 10]
print(json.dumps(out, indent=1))
