import json, glob, os, sys
FX = [("819-c6_dev_diag-scenarios", "C6 diag"), ("819-c6_dev_c5-dev-scenarios", "C5 dev"), ("819-c6_review_gen", "C6 reviewer gen"),
      ("819-c7_dev_c7-scenarios", "C7 dev"), ("819-c8_dev_c8-scenarios", "C8 dev"), ("c9d_longitudinal", "C9-D longitudinal (prereg)"),
      ("c9d_merged", "C9-D merged (post-hoc)")]
ARMS = [("c4-off", "C4"), ("c9-off", "C9-D off"), ("c4-required", "C4+sem"), ("c6-required", "C6+sem"), ("c9-required", "C9-D+sem")]
def load(arm, fx):
    for d in ("runs", "runs-long", "runs-merged"):
        p = f"{d}/{arm}-{fx}.json"
        if os.path.exists(p): return json.load(open(p))
print("| Fixture | Arm | Strict | Needed discovered | Admitted, withheld | Returned needed | Extras | Leaks |")
print("|---|---|---:|---:|---:|---:|---:|---:|")
for fx, name in FX:
    for arm, label in ARMS:
        d = load(arm, fx)
        if not d: continue
        rows = d["rows"]; st = [s["stage"] for r in rows for s in r["stages"].values()]; n = len(st)
        print(f"| {name} | {label} | {sum(r['passed'] for r in rows)}/{len(rows)} | {n - st.count('never_discovered')}/{n} | "
              f"{st.count('admitted_withheld')} | {st.count('returned')} | {sum(1 for r in rows for x in r['returned'] if x not in r['stages'])} | "
              f"{sum(len(r['safety_violations']) + r.get('superseded_returned', 0) for r in rows)} |")
