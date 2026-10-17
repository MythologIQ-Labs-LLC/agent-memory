#!/usr/bin/env python3
"""Post-hoc exploratory variant (#819 C9-D): all six longitudinal themes in one user's store.

    build_merged.py dev/longitudinal-scenarios.json > merged.json
Refs of theme memories get the theme id as a suffix ("memory:swim-kids"), since two themes share a ref name.
"""
import json, sys
S = json.load(open(sys.argv[1]))["scenarios"]
nm = lambda ref, sid: ref if ref.startswith("memory:s") and ref[8:].isdigit() else f"{ref}-{sid}"
ops = list(S[0]["operations"][:30])
for phase in ("remember", "correct", "forget"):
    for s in S:
        ops += [dict(op, ref=nm(op["ref"], s["id"])) for op in s["operations"][30:] if op["op"] == phase]
ex = []
for s in S:
    for op in s["operations"]:
        if op["op"] == "forget":
            ex.append({"ref": nm(op["ref"], s["id"]), "reason": "forgotten"})
        if op["scope"] == "user:c9d-other" and op["op"] == "remember":
            ex.append({"ref": "user:c9d-other#" + nm(op["ref"], s["id"]), "reason": "other_scope"})
qs = []
for s in S:
    for q in s["queries"]:
        q = json.loads(json.dumps(q))
        q["expect"]["must_include"] = [nm(r, s["id"]) for r in q["expect"]["must_include"]]
        q["expect"]["must_exclude"] = ex
        qs.append(q)
json.dump({"cohort": "819-c9d-longitudinal-merged (exploratory, post-hoc)",
           "scenarios": [{"id": "merged", "category": "c9d-merged", "operations": ops, "queries": qs}]}, sys.stdout, indent=1)
