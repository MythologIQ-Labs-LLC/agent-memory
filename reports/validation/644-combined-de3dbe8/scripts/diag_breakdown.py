"""Secondary analysis of heldout_bench output (does not alter cases or gold labels).
A case's 'latent clear' = observer saw no obstacle: diagnosis == mechanical_coverage_observed (old)
or coverage_observed_unattested (candidate) with no non-same_value coherence status."""
import json, sys, collections
CLEAR = {"mechanical_coverage_observed", "coverage_observed_unattested"}
for path in sys.argv[1:]:
    rows = json.load(open(path))["rows"]
    print("==", path.split("/")[-1])
    per = collections.defaultdict(collections.Counter)
    for r in rows:
        per[(r["cat"], r["gold_stop_safe"])][(r["diagnosis"], r["obs_stop"])] += 1
    unsafe_clear = sum(1 for r in rows if not r["gold_stop_safe"] and r["diagnosis"] in CLEAR)
    safe_clear = sum(1 for r in rows if r["gold_stop_safe"] and r["diagnosis"] in CLEAR)
    print(f"latent-clear on unsafe (missed counter-evidence): {unsafe_clear}/78 ; latent-clear on safe: {safe_clear}/48")
    for (c, g), cnt in per.items():
        print(f"  {'SAFE ' if g else 'UNSAFE'} {c:26s} {dict(cnt)}")
