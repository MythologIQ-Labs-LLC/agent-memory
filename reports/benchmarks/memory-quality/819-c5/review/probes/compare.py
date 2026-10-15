"""python3 compare.py <tag>  -> table of returned lists for c4/cand x off/required, plus C5 sims."""
import json, sys
tag = sys.argv[1]
runs = {f"{wt}-{m}": json.load(open(f"out{tag}-{wt}-{m}.json")) for wt in ("c4", "cand") for m in ("off", "required")}
for i, row in enumerate(runs["cand-required"]):
    print(f"\n[{row['scenario']}] {row['query']}")
    for key in ("c4-off", "cand-off", "c4-required", "cand-required"):
        print(f"  {key:14s} {runs[key][i]['returned']}")
    sims = sorted(((v.get('semantic_similarity') or 0, k, v['basis']) for k, v in row['records'].items()), reverse=True)
    print("  C5 sims:", ", ".join(f"{k}={s:.3f}({b})" for s, k, b in sims[:6]), "| admitted", len(row['admitted']))
same = all(a["returned"] == b["returned"] for a, b in zip(runs["c4-off"], runs["cand-off"]))
print("\nsemantic off: C5 == C4 on every query:", same)
