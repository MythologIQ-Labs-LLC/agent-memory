"""#771: score identical runs with the candidate scorer (23321e4) and the repaired scorer.

Only the scorer differs; runs and gold are byte-identical. Writes
scorer-before-after.json next to this script.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CANDIDATE = "23321e4bc1d8039ea64f8d135aac080fc98806fa"
sys.path.insert(0, str(ROOT / "scripts"))
from score_served_memory_quality import score as repaired  # noqa: E402


def _candidate_scorer():
    source = subprocess.run(["git", "-C", str(ROOT), "show", f"{CANDIDATE}:scripts/score_served_memory_quality.py"],
                            check=True, capture_output=True).stdout
    tmp = Path(tempfile.mkdtemp()) / "candidate_scorer.py"
    tmp.write_bytes(source)
    spec = importlib.util.spec_from_file_location("candidate_scorer", tmp)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.score


def main():
    before_score = _candidate_scorer()
    measurements = json.loads((HERE / "measurements-baseline.json").read_text())
    fixtures = {
        "v1-integration": ROOT / "reference/fixtures/evaluation/served-memory-integration-v1-gold.json",
        "halcyon-holdout": HERE / "holdout/halcyon-holdout-v1-gold.json",
        "halcyon-holdout-v1.1": HERE / "holdout/halcyon-holdout-v1-gold.json",
    }
    out = {"candidate_scorer": CANDIDATE, "runs_from": "measurements-baseline.json", "comparisons": {}}
    for corpus, entry in measurements["corpora"].items():
        gold = json.loads(fixtures[corpus].read_text())
        for backend, data in entry["backends"].items():
            before = before_score(copy.deepcopy(gold), copy.deepcopy(data["run"]))
            after = repaired(copy.deepcopy(gold), copy.deepcopy(data["run"]))
            changed_cases = []
            for b_row, a_row in zip(before["per_case"], after["per_case"]):
                diff = {k: (b_row.get(k), a_row.get(k)) for k in set(b_row) | set(a_row)
                        if b_row.get(k) != a_row.get(k)}
                if diff:
                    changed_cases.append({"id": a_row["id"], "changes": diff})
            out["comparisons"][f"{corpus}/{backend}"] = {
                "P2_before": before["P2_context_utility"],
                "P2_after": after["P2_context_utility"],
                "P0_identical": before["P0_safety"] == after["P0_safety"],
                "P1_top1_and_coverage_identical": all(
                    before["P1_served_correctness"][k] == after["P1_served_correctness"][k]
                    for k in ("top1_relevant_rate", "all_critical_groups_covered_rate")),
                "P1_new_fields": {k: after["P1_served_correctness"][k] for k in ("no_safe_answer_served_total",)},
                "per_case_changes": changed_cases,
            }
    (HERE / "scorer-before-after.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    for key, item in out["comparisons"].items():
        b, a = item["P2_before"], item["P2_after"]
        print(key, "prec", b["macro_relevant_precision"], "->", a["macro_relevant_precision"],
              "ndcg", b["macro_ndcg_at_budget"], "->", a["macro_ndcg_at_budget"],
              "| P0 same", item["P0_identical"], "| P1 same", item["P1_top1_and_coverage_identical"])


if __name__ == "__main__":
    main()
