"""#598 re-score comparison: write interpreter 1.0.0 (base 0103b9f) vs 1.1.0 on accepted #594 gold.

Inputs (this directory): ``score-before-v1.0.0.json`` / ``predictions-before-v1.0.0.json`` from
``run_proposition_semantics_score.py`` at base, the ``-after-v1.1.0`` pair from the branch, and the
pre-remediation ``failure-inventory-v1.json``. Evaluator and gold are unchanged (evaluator 0.2.0).

Usage: PYTHONPATH=reference python3 reports/benchmarks/replays/598-write-time-temporal-aspect/rescore_compare.py
Writes ``rescore-comparison-v1.json`` next to this script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref.runtime import proposition_semantics as ps  # noqa: E402
import proposition_semantics_evaluator as evaluator  # noqa: E402

ASPECT = ("aspect_mismatch", "aspect_over_classification")
PARTS = {"part_R": "random_part_R", "all_268_diagnostic": "all_items_diagnostic_not_population_estimate"}
FIXTURES = ROOT / "reference" / "fixtures" / "benchmarks" / "proposition-semantics"


def _load(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def _correct_non_none(pairs: dict[str, int]) -> dict[str, int]:
    out = {}
    for pair, count in pairs.items():
        gold, predicted = pair.split("->")
        if gold == predicted != "none_unknown":
            out[gold] = out.get(gold, 0) + count
    return dict(sorted(out.items()))


def main() -> None:
    before, after = _load("score-before-v1.0.0.json"), _load("score-after-v1.1.0.json")
    pred_before, pred_after = _load("predictions-before-v1.0.0.json"), _load("predictions-after-v1.1.0.json")
    inventory = {item["item_id"]: item for item in _load("failure-inventory-v1.json")["items"]}
    texts = {item["item_id"]: item["text"]
             for item in json.loads((FIXTURES / "sample-v1.json").read_text(encoding="utf-8"))["items"]}
    gold = {item["item_id"]: item["temporal_aspect"] for item in evaluator.load_gold(FIXTURES / "gold-v1.json")["items"]}
    report: dict = {
        "schema_version": "598-rescore-comparison-v1",
        "issue": 598,
        "base_sha": "0103b9f3ba0ab90c4914837dcb98a9cdad7c4c2a",
        "interpreter": {"ref": ps.INTERPRETER_REF, "before": "1.0.0", "after": ps.INTERPRETER_VERSION},
        "classifier_version": ps.CLASSIFIER_VERSION,
        "evaluator_version": after["random_part_R"]["evaluator_version"],
        "gold_changed": False,
        "abstention_note": ("The evaluator never penalizes aspect abstention (none_unknown), so correct non-none "
                            "aspect retention is reported beside the two failure classes."),
        "parts": {},
    }
    for label, key in PARTS.items():
        b, a = before[key], after[key]
        fb = {(f["class"], f["item_id"]) for f in b["findings"] if f["class"] in ASPECT}
        fa = {(f["class"], f["item_id"]) for f in a["findings"] if f["class"] in ASPECT}
        report["parts"][label] = {
            "items_evaluated": a["items_evaluated"],
            "aspect_failures_before": {c: b["failure_counts"].get(c, 0) for c in ASPECT},
            "aspect_failures_after": {c: a["failure_counts"].get(c, 0) for c in ASPECT},
            "non_aspect_failure_counts_before": {k: v for k, v in b["failure_counts"].items() if k not in ASPECT},
            "non_aspect_failure_counts_after": {k: v for k, v in a["failure_counts"].items() if k not in ASPECT},
            "fixed": [{"class": c, "item_id": i} for c, i in sorted(fb - fa)],
            "newly_regressed": [{"class": c, "item_id": i} for c, i in sorted(fa - fb)],
            "unresolved": [{"class": c, "item_id": i, "mechanism": inventory[i]["mechanism"],
                            "aspect_after": pred_after[i]["aspect"], "gold": inventory[i]["gold_temporal_aspect"],
                            "aspect_scope_after": ps.interpret_write(texts[i])["aspect_scope"]}
                           for c, i in sorted(fa & fb)],
            "aspect_pairs_before": b["aspect_pairs"],
            "aspect_pairs_after": a["aspect_pairs"],
            "correct_non_none_aspect_before": _correct_non_none(b["aspect_pairs"]),
            "correct_non_none_aspect_after": _correct_non_none(a["aspect_pairs"]),
        }
    report["correct_aspect_withheld_by_1_1_0"] = _withheld(pred_before, pred_after, texts, gold)
    report["non_aspect_prediction_drift_items"] = sorted(
        i for i in pred_before
        if {k: v for k, v in pred_before[i].items() if not k.startswith("aspect")}
        != {k: v for k, v in pred_after[i].items() if not k.startswith("aspect")})
    (HERE / "rescore-comparison-v1.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    for label, part in report["parts"].items():
        print(label, part["aspect_failures_before"], "->", part["aspect_failures_after"],
              "correct", part["correct_non_none_aspect_before"], "->", part["correct_non_none_aspect_after"])
    print("non-aspect drift", report["non_aspect_prediction_drift_items"])


def _withheld(pred_before: dict, pred_after: dict, texts: dict, gold: dict) -> list[dict]:
    """Items 1.0.0 got right with a non-none regime and 1.1.0 no longer does (all 268; Part R ids marked)."""

    rows = []
    for item_id in sorted(pred_before):
        was, now = pred_before[item_id]["aspect"], pred_after[item_id]["aspect"]
        if was != "none_unknown" and was == gold[item_id] and now != was:
            rows.append({"item_id": item_id, "gold": gold[item_id], "before": pred_before[item_id]["aspect_all"],
                         "after": pred_after[item_id]["aspect_all"],
                         "aspect_scope_after": ps.interpret_write(texts[item_id])["aspect_scope"]})
    return rows


if __name__ == "__main__":
    main()
