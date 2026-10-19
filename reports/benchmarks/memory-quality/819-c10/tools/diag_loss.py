import glob, json, collections
from pathlib import Path
F = {}
for l in open("feas/features_ce.jsonl"):
    r = json.loads(l); F[(r["set"], r["q"], r["ref"])] = r
lost, gained = collections.Counter(), collections.Counter(); ex = []
for f in sorted(glob.glob("cand/c10-gate-*.json")):
    s = Path(f).stem[len("c10-gate-"):]
    C = {r["id"]: r for r in json.load(open(f))["rows"]}; B = {r["id"]: r for r in json.load(open(f"base/c4-required-{s}.json"))["rows"]}
    for q in C:
        for need, st in C[q]["stages"].items():
            if st["stage"] != "returned" and B[q]["stages"][need]["stage"] == "returned":
                fr = F.get((s, q, need), {})
                key = (s.startswith("c9d"), st["stage"], "qnli>0" if fr.get("qnli", -9) > 0 else "qnli<=0", "drank<=8" if fr.get("drank", 99) <= 8 else "drank>8")
                lost[key] += 1
                if len(ex) < 6 and fr.get("qnli", -9) > 0: ex.append((s, q, need, st, fr.get("drank"), fr.get("qnli"), fr.get("cos")))
for k, v in sorted(lost.items(), key=lambda x: -x[1]): print("LOST", v, "longitudinal" if k[0] else "other", *k[1:])
for e in ex: print(" ex", e)
