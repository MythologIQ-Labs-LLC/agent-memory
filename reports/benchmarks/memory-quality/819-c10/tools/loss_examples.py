"""Needed memories C4+sem returned and C10 lost: query, memory text, QNLI logit, cosine, dense rank, query kind."""
import glob, json, collections
from pathlib import Path
F = {}
for l in open("feas/features_ce.jsonl"):
    r = json.loads(l); F[(r["set"], r["q"], r["ref"])] = r
Q = {}; T = {}
for f in glob.glob("fx/*.json"):
    s = Path(f).stem; d = json.load(open(f)); sc = d["scenarios"] if isinstance(d, dict) else d
    for x in sc:
        for op in x["operations"]:
            if op["op"] != "forget": T[(s, op["scope"], op["ref"])] = op["text"]
        for q in x["queries"]: Q[(s, q["id"])] = q
kinds = collections.Counter()
for f in sorted(glob.glob("cand/c10-gate-*.json")):
    s = Path(f).stem[len("c10-gate-"):]
    C = {r["id"]: r for r in json.load(open(f))["rows"]}; B = {r["id"]: r for r in json.load(open(f"base/c4-required-{s}.json"))["rows"]}
    for q in C:
        for need, st in C[q]["stages"].items():
            if st["stage"] != "returned" and B[q]["stages"][need]["stage"] == "returned":
                fr = F.get((s, q, need), {}); qq = Q[(s, q)]
                kinds[(C[q]["kind"], "needs_several" if fr.get("several") else "single_reading")] += 1
                print(f"[{s} {C[q]['kind']}] Q: {qq['query']!r}\n    M: {T.get((s, qq['scope'], need), '?')!r}  qnli={fr.get('qnli')} cos={fr.get('cos')} drank={fr.get('drank')} stage={st['stage']}")
print(dict(kinds))
