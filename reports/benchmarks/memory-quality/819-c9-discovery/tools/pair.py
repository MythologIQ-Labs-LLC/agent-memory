"""Paired per-query comparison of two harness runs (same cohort)."""
import json, sys
a, b = (json.load(open(p)) for p in sys.argv[1:3])
assert a["cohort_sha256"] == b["cohort_sha256"]
ra = {r["id"]: r for r in a["rows"]}; rb = {r["id"]: r for r in b["rows"]}
same_ret = sum(ra[i]["returned"] == rb[i]["returned"] for i in ra)
w = sum(rb[i]["passed"] and not ra[i]["passed"] for i in ra); l = sum(ra[i]["passed"] and not rb[i]["passed"] for i in ra)
disc = lambda r: sum(st["stage"] != "never_discovered" for st in r["stages"].values())
ret = lambda r: sum(st["stage"] == "returned" for st in r["stages"].values())
ext = lambda r: sum(1 for x in r["returned"] if x not in r["stages"])
dd = [disc(rb[i]) - disc(ra[i]) for i in ra]
out = dict(queries=len(ra), same_returned=same_ret, strict_w=w, strict_l=l,
           disc_gain=sum(x for x in dd if x > 0), disc_loss=-sum(x for x in dd if x < 0),
           returned_needed=(sum(map(ret, ra.values())), sum(map(ret, rb.values()))),
           extras=(sum(map(ext, ra.values())), sum(map(ext, rb.values()))),
           admitted_same=sum(ra[i]["admitted_count"] == rb[i]["admitted_count"] for i in ra),
           p50_ms=(sorted(r["elapsed_ms"] for r in ra.values())[len(ra)//2], sorted(r["elapsed_ms"] for r in rb.values())[len(rb)//2]))
print(sys.argv[1].split("/")[-1], "->", sys.argv[2].split("/")[-1], json.dumps(out))
