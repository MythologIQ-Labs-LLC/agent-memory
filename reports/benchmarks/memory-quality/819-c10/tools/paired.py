"""Paired per-query comparison of two harness arms over the dev sets (evaluation-only).

    paired.py <base_glob_prefix> <cand_glob_prefix> <fx_dir>
e.g. paired.py base/c4-required cand/c10-gate fx
Extras = returned refs that are neither must_include nor may_include (C9-S definition);
unrequested = returned refs not in must_include (harness log definition).
"""
import glob, json, math, sys
from pathlib import Path

base_p, cand_p, fx = sys.argv[1:4]

def expectations(fx_dir):
    out = {}
    for f in glob.glob(f"{fx_dir}/*.json"):
        data = json.loads(Path(f).read_text()); scen = data["scenarios"] if isinstance(data, dict) else data
        for s in scen:
            for q in s["queries"]:
                e = q["expect"]
                out[(Path(f).stem, q["id"])] = (set(e.get("must_include") or []), set(e.get("may_include") or []))
    return out

def load(prefix):
    rows = {}
    for f in sorted(glob.glob(f"{prefix}-*.json")):
        stem = Path(f).stem[len(Path(prefix).name) + 1:]
        d = json.load(open(f))
        for r in d["rows"]:
            rows[(stem, r["id"])] = r
        rev = d["revision"]
    return rows, rev

def mcnemar(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)

E = expectations(fx)
B, brev = load(base_p); C, crev = load(cand_p)
assert set(B) == set(C), (len(B), len(C))
def stats(rows):
    t = dict(strict=0, needed=0, extras=0, unrequested=0, abst_ok=0, abst_n=0, viol=0, superseded=0, returned=0)
    for k, r in rows.items():
        need, may = E[k]; got = set(r["returned"])
        t["strict"] += r["passed"]; t["needed"] += len(need & got)
        t["extras"] += len(got - need - may); t["unrequested"] += len(got - need)
        t["returned"] += len(got)
        if not need: t["abst_n"] += 1; t["abst_ok"] += not got
        t["viol"] += len(r["safety_violations"]); t["superseded"] += r.get("superseded_returned", 0)
    return t
sb, sc = stats(B), stats(C)
n_need = sum(len(E[k][0]) for k in B)
print(f"base {base_p} @ {brev[:8]}   cand {cand_p} @ {crev[:8]}   queries {len(B)} needed {n_need}")
for key in sb:
    print(f"  {key:12s} {sb[key]:5d} -> {sc[key]:5d}  ({sc[key] - sb[key]:+d})")
w = sum(1 for k in B if C[k]["passed"] and not B[k]["passed"]); l = sum(1 for k in B if B[k]["passed"] and not C[k]["passed"])
print(f"  strict paired +{w}/-{l}  McNemar p={mcnemar(w, l):.2g}")
gain = sum(len((E[k][0] & set(C[k]["returned"])) - set(B[k]["returned"])) for k in B)
loss = sum(len((E[k][0] & set(B[k]["returned"])) - set(C[k]["returned"])) for k in B)
print(f"  needed memories paired +{gain}/-{loss}")
# per query needed completeness (all must_include returned)
cw = sum(1 for k in B if E[k][0] and E[k][0] <= set(C[k]["returned"]) and not E[k][0] <= set(B[k]["returned"]))
cl = sum(1 for k in B if E[k][0] and E[k][0] <= set(B[k]["returned"]) and not E[k][0] <= set(C[k]["returned"]))
print(f"  all-needed-returned queries paired +{cw}/-{cl}  McNemar p={mcnemar(cw, cl):.2g}")
for kind in ("single", "multi", "abstention"):
    ks = [k for k in B if B[k]["kind"] == kind]
    print(f"  {kind:10s} n={len(ks):3d} strict {sum(B[k]['passed'] for k in ks)} -> {sum(C[k]['passed'] for k in ks)}")
print("  per set (strict / needed / extras):")
for s in sorted({k[0] for k in B}):
    ks = {k: None for k in B if k[0] == s}
    a = stats({k: B[k] for k in ks}); b = stats({k: C[k] for k in ks})
    print(f"    {s:32s} {a['strict']:3d}/{a['needed']:3d}/{a['extras']:3d} -> {b['strict']:3d}/{b['needed']:3d}/{b['extras']:3d}")
