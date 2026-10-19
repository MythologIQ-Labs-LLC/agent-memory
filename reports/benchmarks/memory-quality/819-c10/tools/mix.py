"""Exact per-query mixtures of two real runtime arms (each query recalls independently over the same store)."""
import glob, json, sys
from pathlib import Path
sys.path.insert(0, "wt/c10/reference")
from agentmem_ref.runtime.return_selection import interpret_query
Q = {}
for f in glob.glob("fx/*.json"):
    d = json.load(open(f)); sc = d["scenarios"] if isinstance(d, dict) else d
    for x in sc:
        for q in x["queries"]: Q[(Path(f).stem, q["id"])] = q
def rows(prefix):
    out = {}
    for f in glob.glob(f"{prefix}-*.json"):
        s = Path(f).stem[len(Path(prefix).name) + 1:]
        for r in json.load(open(f))["rows"]: out[(s, r["id"])] = r
    return out
B, C = rows("base/c4-required"), rows("cand/c10-gate")
def score(pick):
    st = nd = ex = ab = 0
    for k in B:
        r = C[k] if pick(k) else B[k]; e = Q[k]["expect"]
        need = set(e.get("must_include") or []); may = set(e.get("may_include") or []); got = set(r["returned"])
        st += r["passed"]; nd += len(need & got); ex += len(got - need - may); ab += (not need and not got)
    return f"strict {st:3d} needed {nd:3d} extras {ex:3d} abstain {ab}"
print("C4+sem everywhere           ", score(lambda k: False))
print("C10 gate everywhere         ", score(lambda k: True))
print("gate unless interpreter needs_several (realistic)", score(lambda k: not interpret_query(Q[k]["query"]).needs_several))
print("gate unless gold multi-evidence (ORACLE ceiling)", score(lambda k: len(set(Q[k]["expect"].get("must_include") or [])) <= 1))
