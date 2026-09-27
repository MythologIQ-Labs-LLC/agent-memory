"""#576 cross-process driver: run seed_probe.py in fresh processes per PYTHONHASHSEED.

Usage: python cross_seed.py <label> <out.json>
Each seed runs twice (two independent processes, i.e. a restart) and the summary
records whether BM25 score bits, ranking order and evidence digests agree across seeds.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEEDS = ["0", "1", "2", "3", "4", "5", "6", "7"]


def _run(seed: str) -> dict:
    env = {**os.environ, "PYTHONHASHSEED": seed}
    out = subprocess.run([sys.executable, str(HERE / "seed_probe.py")], env=env, capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def main(label: str, target: str) -> None:
    rev = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=HERE).stdout.strip()
    runs = {seed: [_run(seed), _run(seed)] for seed in SEEDS}
    restart_identical = all(a == b for a, b in runs.values())
    first = {seed: pair[0] for seed, pair in runs.items()}
    summary = {
        "label": label,
        "revision": rev,
        "seeds": SEEDS,
        "restart_identical_per_seed": restart_identical,
        "distinct_pure_digests": sorted({r["pure_digest"] for r in first.values()}),
        "distinct_governed_digests": sorted({r["governed_digest"] for r in first.values()}),
        "distinct_pure_orders": sorted({tuple(r["pure"]["order_by_score_then_ref"]) for r in first.values()}),
        "distinct_governed_orders": sorted({tuple(r["governed"]["admitted_order"]) for r in first.values()}),
        "distinct_refused_sets": sorted({tuple(r["governed"]["refused"]) for r in first.values()}),
        "per_seed": {seed: {
            "set_iteration_order": r["set_iteration_order"],
            "scores_hex": r["pure"]["scores_hex"],
            "governed_admitted_order": r["governed"]["admitted_order"],
            "governed_refused": r["governed"]["refused"],
            "pure_digest": r["pure_digest"],
            "governed_digest": r["governed_digest"],
        } for seed, r in first.items()},
    }
    summary["cross_seed_identical"] = len(summary["distinct_pure_digests"]) == 1 and len(summary["distinct_governed_digests"]) == 1
    Path(target).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in ("label", "revision", "restart_identical_per_seed", "cross_seed_identical",
                                              "distinct_pure_orders", "distinct_governed_orders", "distinct_refused_sets")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
