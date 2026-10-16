"""Compare harness outputs: per-query table + aggregates."""
import json, sys
from pathlib import Path
O = Path(sys.argv[1])
cfgs = [a.split("=") for a in sys.argv[2:]]
data = {lab: {r["id"]: r for r in json.load(open(O / f))["rows"]} for lab, f in cfgs}
ids = list(next(iter(data.values())))
def cell(r):
    k = r["kind"]
    nr = r["needed_rank"]
    s = "/".join(str(v) if v else "-" for v in nr.values()) if nr else "."
    if r.get("pair"):
        s += " pf=" + {True: "Y", False: "N", None: "?"}[r["pair"]["preferred_first"]]
    if r["planted_rank"]:
        s += " pl=" + "/".join(str(v) for v in r["planted_rank"].values())
    s += f" ret={len(r['returned'])}" + ("" if not r["needed_rank"] else f"({sum(r['needed_returned'].values())})")
    return s
print("| query | kind | " + " | ".join(l for l, _ in cfgs) + " |")
print("|---|---|" + "---|" * len(cfgs))
for q in ids:
    print(f"| {q} | {data[cfgs[0][0]][q]['kind']} | " + " | ".join(cell(data[l][q]) for l, _ in cfgs) + " |")
print()
print("| aggregate | " + " | ".join(l for l, _ in cfgs) + " |")
print("|---|" + "---|" * len(cfgs))
def agg(name, f):
    print(f"| {name} | " + " | ".join(str(f(d)) for d in data.values()) + " |")
need = lambda d: [r for r in d.values() if r["needed_rank"]]
agg("queries with needed", lambda d: len(need(d)))
for k in ("@1", "@3", "@5", "@10"):
    agg(f"all needed in top {k[1:]}", lambda d, k=k: sum(r["cover"][k] for r in need(d)))
agg("needed memories (total)", lambda d: sum(len(r["needed_rank"]) for r in need(d)))
agg("needed in top 5", lambda d: sum(1 for r in need(d) for v in r["needed_rank"].values() if v and v <= 5))
agg("needed in top 10", lambda d: sum(1 for r in need(d) for v in r["needed_rank"].values() if v and v <= 10))
agg("needed not admitted", lambda d: sum(1 for r in need(d) for v in r["needed_rank"].values() if not v))
agg("needed returned", lambda d: sum(sum(r["needed_returned"].values()) for r in need(d)))
agg("strict pass", lambda d: sum(r["passed"] for r in d.values()))
agg("extras returned", lambda d: sum(len(r["extras_returned"]) for r in d.values()))
agg("no-answer queries returning", lambda d: sum(1 for r in d.values() if r["kind"] == "no_answer" and r["returned"]))
agg("planted memory at rank 1", lambda d: sum(1 for r in d.values() if r["planted_rank"] and 1 in r["planted_rank"].values()))
agg("near_miss: answer at rank 1", lambda d: sum(1 for r in d.values() if r["kind"] == "near_miss" and r["cover"]["@1"]))
agg("temporal pairs preferred first", lambda d: sum(1 for r in d.values() if r.get("pair") and r["pair"]["preferred_first"]))
agg("forbidden in admitted/returned", lambda d: sum(1 for r in d.values() for x in r["forbidden_seen"] if x in r["ranked"] or x in r["returned"]))
agg("forbidden among candidates only", lambda d: sum(1 for r in d.values() for x in r["forbidden_seen"] if x not in r["ranked"] and x not in r["returned"]))
agg("p50 ms", lambda d: sorted(r["ms"] for r in d.values())[len(d) // 2])
