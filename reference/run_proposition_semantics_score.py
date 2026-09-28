#!/usr/bin/env python3
"""Run the first post-freeze #594 proposition-semantics score against accepted gold."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference"
if str(REFERENCE) not in sys.path:
    sys.path.insert(0, str(REFERENCE))

from agentmem_ref.runtime import proposition_semantics as ps  # noqa: E402
import proposition_semantics_evaluator as evaluator  # noqa: E402

FIXTURES = REFERENCE / "fixtures" / "benchmarks" / "proposition-semantics"
GOLD_PATH = FIXTURES / "gold-v1.json"
ALIASES_PATH = FIXTURES / "property-aliases-gold-v1.json"
SAMPLE_PATH = FIXTURES / "sample-v1.json"


def _ratio(n: int, d: int) -> float | None:
    return None if not d else round(n / d, 6)


def _status_metrics(report: Mapping[str, Any]) -> dict[str, Any]:
    confusion = report["status_confusion"]
    out: dict[str, Any] = {}
    for label in evaluator.STATUSES:
        tp = int(confusion.get(label, {}).get(label, 0))
        predicted = sum(int(confusion.get(gold, {}).get(label, 0)) for gold in evaluator.STATUSES)
        actual = sum(int(v) for v in confusion.get(label, {}).values())
        out[label] = {
            "precision": _ratio(tp, predicted),
            "recall": _ratio(tp, actual),
            "predicted": predicted,
            "gold": actual,
            "true_positive": tp,
        }
    return out


def _evaluate_subset(items: list[dict[str, Any]], predictions: Mapping[str, Mapping[str, Any]], aliases: Mapping[str, Iterable[str]]) -> dict[str, Any]:
    report = evaluator.evaluate(items, predictions, property_aliases=aliases)
    report["status_metrics"] = _status_metrics(report)
    predicted_known = sum(report["status_confusion"].get(gold, {}).get("known", 0) for gold in evaluator.STATUSES)
    report["known_slot_value_precision"] = _ratio(report["failure_counts"].get("slot_and_value_correct", 0), predicted_known)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reports/benchmarks/proposition-semantics-score-v1")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    gold = evaluator.load_gold(GOLD_PATH)
    aliases_doc = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    aliases = aliases_doc.get("aliases", {})
    sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    texts = {item["item_id"]: item["text"] for item in sample["items"]}
    sample_meta = {item["item_id"]: item for item in sample["items"]}

    def run_once() -> dict[str, dict[str, Any]]:
        return {
            item["item_id"]: evaluator.normalize_runtime_prediction(ps.interpret_write(texts[item["item_id"]]))
            for item in gold["items"]
        }

    predictions = run_once()
    second = run_once()
    deterministic = json.dumps(predictions, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))
    if not deterministic:
        raise SystemExit("interpreter predictions are not deterministic across immediate replay")

    random_items = [item for item in gold["items"] if sample_meta[item["item_id"]]["part"] == "R"]
    stratified_items = [item for item in gold["items"] if sample_meta[item["item_id"]]["part"] == "S"]
    strata = sorted({sample_meta[item["item_id"]]["stratum"] for item in stratified_items})

    report = {
        "schema_version": 1,
        "issue": 594,
        "evidence_class": "repository-owned conformance",
        "aggregate_score": "not_defined",
        "gold": {
            "manifest": str(GOLD_PATH.relative_to(ROOT)),
            "manifest_sha256": hashlib.sha256(GOLD_PATH.read_bytes()).hexdigest(),
            "accepted_source": gold["accepted_source"],
            "accepted_by": gold["acceptance"]["accepted_by"],
            "accepted_at": gold["acceptance"]["accepted_at"],
            "review_id": gold["acceptance"]["review_id"],
            "item_count": len(gold["items"]),
        },
        "property_aliases": {
            "file": str(ALIASES_PATH.relative_to(ROOT)),
            "sha256": hashlib.sha256(ALIASES_PATH.read_bytes()).hexdigest(),
            "count": sum(len(v) for v in aliases.values()),
            "frozen_pre_score": True,
        },
        "deterministic_replay_identical": deterministic,
        "random_part_R": _evaluate_subset(random_items, predictions, aliases),
        "stratified_part_S": {
            stratum: _evaluate_subset(
                [item for item in stratified_items if sample_meta[item["item_id"]]["stratum"] == stratum],
                predictions,
                aliases,
            )
            for stratum in strata
        },
        "all_items_diagnostic_not_population_estimate": _evaluate_subset(gold["items"], predictions, aliases),
        "prediction_status_counts": dict(sorted(Counter(p["status"] for p in predictions.values()).items())),
    }

    (output / "predictions-v1.json").write_text(json.dumps(predictions, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "score-v1.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "deterministic_replay_identical": deterministic,
        "prediction_status_counts": report["prediction_status_counts"],
        "part_R_status_metrics": report["random_part_R"]["status_metrics"],
        "part_R_failure_counts": report["random_part_R"]["failure_counts"],
        "part_R_known_slot_value_precision": report["random_part_R"]["known_slot_value_precision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
