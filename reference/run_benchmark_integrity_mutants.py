#!/usr/bin/env python3
"""Probe benchmark evaluator sensitivity with controlled retrieval mutations.

This is an evaluator-integrity harness, not a benchmark result. It independently
re-expresses a useful lesson observed during ancestry review: a benchmark check
must demonstrate that plausible failure mutations actually change the expected
metrics instead of merely producing a green report.

The probes exercise the existing SWE-ContextBench metric implementation. They do
not create a second retrieval implementation and have no memory-authority effect.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Callable

import run_swe_context_bench_harness as harness


REPORT_SCHEMA_VERSION = "1.0.0"
REPORT_ID = "agent-memory-benchmark-integrity-mutation-probes"


def _baseline_rows() -> list[dict[str, Any]]:
    return [
        {
            "related_instance_id": "query-a",
            "repo": "example/repo",
            "gold_experience_instance_ids": ["gold-a"],
            "candidate_experience_ids": ["gold-a", "noise-a"],
            "retrieved_experience_ids": ["gold-a"],
        },
        {
            "related_instance_id": "query-b",
            "repo": "example/repo",
            "gold_experience_instance_ids": ["gold-b", "gold-c"],
            "candidate_experience_ids": ["gold-b", "gold-c", "noise-b"],
            "retrieved_experience_ids": ["gold-b", "gold-c"],
        },
    ]


def _mutate_admitted_noise(rows: list[dict[str, Any]]) -> None:
    rows[0]["retrieved_experience_ids"] = ["noise-a", "gold-a"]


def _mutate_missing_gold(rows: list[dict[str, Any]]) -> None:
    rows[1]["retrieved_experience_ids"] = ["gold-b"]


def _mutate_candidate_admission_collapse(rows: list[dict[str, Any]]) -> None:
    rows[0]["retrieved_experience_ids"] = list(rows[0]["candidate_experience_ids"])


def _mutate_rank_inversion(rows: list[dict[str, Any]]) -> None:
    rows[0]["retrieved_experience_ids"] = ["noise-a", "gold-a"]


def _mutate_admission_refusal(rows: list[dict[str, Any]]) -> None:
    rows[0]["retrieved_experience_ids"] = []


def _probe(
    *,
    name: str,
    baseline: dict[str, Any],
    mutate: Callable[[list[dict[str, Any]]], None],
    detect: Callable[[dict[str, Any], dict[str, Any]], bool],
    expectation: str,
) -> dict[str, Any]:
    rows = copy.deepcopy(_baseline_rows())
    mutate(rows)
    metrics = harness._quality(rows)
    return {
        "name": name,
        "detected": bool(detect(baseline, metrics)),
        "expectation": expectation,
        "metrics": metrics,
    }


def run_mutation_probes() -> dict[str, Any]:
    baseline = harness._quality(_baseline_rows())
    probes = [
        _probe(
            name="admitted_noise",
            baseline=baseline,
            mutate=_mutate_admitted_noise,
            detect=lambda base, value: (
                value["false_admission_count"] > base["false_admission_count"]
                and value["final_admitted_precision"] < base["final_admitted_precision"]
            ),
            expectation="admitting non-gold memory must increase false admissions and reduce precision",
        ),
        _probe(
            name="missing_gold",
            baseline=baseline,
            mutate=_mutate_missing_gold,
            detect=lambda base, value: (
                value["false_refusal_count"] > base["false_refusal_count"]
                and value["final_admitted_recall"] < base["final_admitted_recall"]
                and value["gold_edge_count"] == base["gold_edge_count"]
            ),
            expectation="dropping one multi-gold edge must increase false refusals without changing the denominator",
        ),
        _probe(
            name="candidate_admission_collapse",
            baseline=baseline,
            mutate=_mutate_candidate_admission_collapse,
            detect=lambda base, value: (
                value["candidate_recall"] == base["candidate_recall"]
                and value["false_admission_count"] > base["false_admission_count"]
                and value["final_admitted_precision"] < base["final_admitted_precision"]
            ),
            expectation="candidate quality may remain unchanged while improper final admission is penalized",
        ),
        _probe(
            name="rank_inversion",
            baseline=baseline,
            mutate=_mutate_rank_inversion,
            detect=lambda base, value: (
                value["final_admitted_recall"] == base["final_admitted_recall"]
                and value["ndcg_at_1"] < base["ndcg_at_1"]
            ),
            expectation="placing noise ahead of the relevant memory must reduce nDCG@1 even when recall is preserved",
        ),
        _probe(
            name="admission_refusal",
            baseline=baseline,
            mutate=_mutate_admission_refusal,
            detect=lambda base, value: (
                value["candidate_recall"] == base["candidate_recall"]
                and value["final_admitted_recall"] < base["final_admitted_recall"]
                and value["false_refusal_count"] > base["false_refusal_count"]
            ),
            expectation="candidate recall and final admitted recall must remain independently measurable",
        ),
    ]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "purpose": "benchmark evaluator integrity, not retrieval efficacy",
        "baseline": baseline,
        "probes": probes,
        "all_detected": all(probe["detected"] for probe in probes),
        "claim_boundary": {
            "benchmark_result": False,
            "external_comparability": False,
            "memory_authority_effect": "none",
            "mutant_detection_proves_real_world_quality": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_mutation_probes()
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if report["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
