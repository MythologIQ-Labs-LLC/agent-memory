#!/usr/bin/env python3
"""Probe benchmark evaluator sensitivity with controlled retrieval mutations.

This is an evaluator-integrity harness, not a benchmark result. It independently
re-expresses a useful lesson observed during ancestry review: a benchmark check
must demonstrate that plausible failure mutations actually change the expected
metrics instead of merely producing a green report.

Each accepted external benchmark profile gets probes that respect its own
semantics and are scored by that profile's existing evaluator:

* SWE-ContextBench: ``run_swe_context_bench_harness._quality``;
* LongMemEval: ``run_longmemeval.score_record`` / ``summarize`` (the replicated
  upstream retrieval evaluator);
* AgentMemBench / MemDialogue: recorded as not yet available until its profile
  exists.

No second retrieval implementation is created and there is no memory-authority
effect.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Callable

import run_longmemeval as longmemeval
import run_swe_context_bench_harness as harness


REPORT_SCHEMA_VERSION = "2.0.0"
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


def _swe_contextbench_probes() -> dict[str, Any]:
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
        "evaluator": "run_swe_context_bench_harness._quality",
        "baseline": baseline,
        "probes": probes,
        "all_detected": all(probe["detected"] for probe in probes),
    }


# LongMemEval ---------------------------------------------------------------

_LME_GRANULARITY = "session"


def _lme_dataset() -> list[dict[str, Any]]:
    return longmemeval._load(longmemeval.DEFAULT_FIXTURE)


def _lme_ideal_rankings(dataset: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Gold-only rankings, most recent gold first; nothing for abstention rows."""
    rankings: dict[str, list[str]] = {}
    for row in dataset:
        items, gold = longmemeval.corpus(row, _LME_GRANULARITY)
        dates = {item["id"]: longmemeval._parse_date(item["date"]) or () for item in items}
        ideal = [] if longmemeval.is_abstention(row) else sorted(gold, key=lambda doc: (dates[doc], doc), reverse=True)
        rankings[str(row["question_id"])] = ideal
    return rankings


def _lme_summary(dataset: list[dict[str, Any]], rankings: dict[str, list[str]]) -> dict[str, Any]:
    records = [
        longmemeval.score_record(row, _LME_GRANULARITY, rankings.get(str(row["question_id"]), []))
        for row in dataset
    ]
    return longmemeval.summarize(records, _LME_GRANULARITY)


def _lme_metric(summary: dict[str, Any], name: str) -> float:
    return summary["aggregate"]["metrics"][_LME_GRANULARITY][name]


def _lme_currentness(summary: dict[str, Any]) -> float:
    return summary["currentness"]["latest_gold_ranked_first"]["rate"]


def _lme_evaluated(summary: dict[str, Any]) -> int:
    return summary["aggregate"]["evaluated_question_count"]


def _lme_missing_gold(dataset, rankings) -> None:
    rankings["syn_multi_pets"] = rankings["syn_multi_pets"][:1]


def _lme_irrelevant_ahead(dataset, rankings) -> None:
    rankings["syn_multi_pets"] = [rankings["syn_multi_pets"][0], "syn_filler_garden"] + rankings["syn_multi_pets"][1:]


def _lme_irrelevant_at_rank_one(dataset, rankings) -> None:
    rankings["syn_single_editor"] = ["syn_filler_lunch"] + rankings["syn_single_editor"]


def _lme_rank_below_cutoff(dataset, rankings) -> None:
    rankings["syn_single_editor"] = ["syn_filler_lunch", "syn_filler_music"] + rankings["syn_single_editor"]


def _lme_stale_over_current(dataset, rankings) -> None:
    rankings["syn_update_branch"] = list(reversed(rankings["syn_update_branch"]))


def _lme_suppressed_abstention(dataset, rankings) -> None:
    for row in dataset:
        if row["question_id"] == "syn_bicycle_abs":
            row["question_id"] = "syn_bicycle"
            rankings["syn_bicycle"] = rankings.pop("syn_bicycle_abs")


def _lme_identity_corruption(dataset, rankings) -> None:
    for row in dataset:
        items, _ = longmemeval.corpus(row, _LME_GRANULARITY)
        ids = [item["id"] for item in items]
        shifted = {doc: ids[(index + 1) % len(ids)] for index, doc in enumerate(ids)}
        key = str(row["question_id"])
        rankings[key] = [shifted[doc] for doc in rankings[key]]


def _lme_cross_scope_injection(dataset, rankings) -> None:
    rankings["syn_multi_pets"] = rankings["syn_multi_pets"] + ["answer_syn_editor_1"]


def _lme_probe(name, mutate, detect, expectation, base, expected_detection=True) -> dict[str, Any]:
    dataset = _lme_dataset()
    rankings = _lme_ideal_rankings(dataset)
    mutate(dataset, rankings)
    summary = _lme_summary(dataset, rankings)
    return {
        "name": name,
        "detected": bool(detect(base, summary)),
        "expected_detection": expected_detection,
        "expectation": expectation,
        "metrics": {
            "headline": summary["aggregate"]["headline"],
            "evaluated_question_count": _lme_evaluated(summary),
            "latest_gold_ranked_first_rate": _lme_currentness(summary),
            "out_of_corpus_returned_count": summary["failures"]["out_of_corpus_returned_count"],
        },
    }


def _longmemeval_probes() -> dict[str, Any]:
    dataset = _lme_dataset()
    base = _lme_summary(dataset, _lme_ideal_rankings(dataset))
    specs = [
        (
            "missing_gold",
            _lme_missing_gold,
            lambda b, v: _lme_metric(v, "recall_all@5") < _lme_metric(b, "recall_all@5")
            and _lme_evaluated(v) == _lme_evaluated(b),
            "dropping one gold session of a multi-session question must lower recall_all without changing the denominator",
        ),
        (
            "irrelevant_ahead",
            _lme_irrelevant_ahead,
            lambda b, v: _lme_metric(v, "ndcg_any@5") < _lme_metric(b, "ndcg_any@5")
            and _lme_metric(v, "recall_all@5") == _lme_metric(b, "recall_all@5"),
            "an irrelevant session ranked ahead of a gold session must lower ndcg_any even when recall_all is preserved",
        ),
        (
            "irrelevant_at_rank_one",
            _lme_irrelevant_at_rank_one,
            lambda b, v: _lme_metric(v, "ndcg_any@5") < _lme_metric(b, "ndcg_any@5"),
            "KNOWN UPSTREAM INSENSITIVITY: upstream dcg weights ranks 1 and 2 equally (rel1 + rel2/log2(2)), so "
            "displacing a single gold item from rank 1 to rank 2 does not change ndcg_any; recall_all@1 is the "
            "sensitive signal for that damage",
            False,
        ),
        (
            "rank_below_cutoff",
            _lme_rank_below_cutoff,
            lambda b, v: _lme_metric(v, "recall_all@1") < _lme_metric(b, "recall_all@1")
            and _lme_metric(v, "recall_all@5") == _lme_metric(b, "recall_all@5"),
            "pushing gold below k must be visible at that cutoff and only at that cutoff",
        ),
        (
            "stale_over_current",
            _lme_stale_over_current,
            lambda b, v: _lme_currentness(v) < _lme_currentness(b)
            and _lme_metric(v, "recall_all@5") == _lme_metric(b, "recall_all@5"),
            "ranking a superseded knowledge-update session ahead of the current one must lower the currentness "
            "diagnostic while retrieval recall is unchanged",
        ),
        (
            "suppressed_abstention",
            _lme_suppressed_abstention,
            lambda b, v: _lme_evaluated(v) > _lme_evaluated(b)
            and v["aggregate"]["excluded_abstention_count"] < b["aggregate"]["excluded_abstention_count"],
            "losing the _abs identity of an abstention question must change the scored denominator",
        ),
        (
            "identity_mapping_corruption",
            _lme_identity_corruption,
            lambda b, v: _lme_metric(v, "recall_any@5") < _lme_metric(b, "recall_any@5"),
            "mapping returned memories to the wrong benchmark ids must lower recall",
        ),
        (
            "cross_scope_injection",
            _lme_cross_scope_injection,
            lambda b, v: v["failures"]["out_of_corpus_returned_count"] > b["failures"]["out_of_corpus_returned_count"]
            and _lme_metric(v, "recall_all@5") == _lme_metric(b, "recall_all@5"),
            "an item from another question's haystack must be counted as out-of-corpus and earn no recall",
        ),
    ]
    probes = [_lme_probe(*spec[:4], base, *spec[4:]) for spec in specs]
    detection_probes = [probe for probe in probes if probe["expected_detection"]]
    insensitivities = [probe for probe in probes if not probe["expected_detection"]]
    return {
        "evaluator": "run_longmemeval.score_record + run_longmemeval.summarize",
        "fixture": "reference/fixtures/benchmarks/longmemeval/synthetic.json",
        "granularity": _LME_GRANULARITY,
        "baseline": {
            "ranking": "ideal gold-only, most recent gold first, nothing returned for abstention",
            "headline": base["aggregate"]["headline"],
            "evaluated_question_count": _lme_evaluated(base),
            "latest_gold_ranked_first_rate": _lme_currentness(base),
            "out_of_corpus_returned_count": base["failures"]["out_of_corpus_returned_count"],
        },
        "probes": probes,
        "all_detected": all(probe["detected"] for probe in detection_probes),
        "known_insensitivities": [probe["name"] for probe in insensitivities],
        "known_insensitivities_confirmed": all(not probe["detected"] for probe in insensitivities),
    }


def _agentmembench_probes() -> dict[str, Any]:
    return {
        "status": "profile_not_available",
        "reason": "no accepted AgentMemBench / MemDialogue evaluator exists yet (#517); probes are added with that profile",
        "all_detected": None,
    }


def run_mutation_probes() -> dict[str, Any]:
    profiles = {
        "swe_contextbench": _swe_contextbench_probes(),
        "longmemeval": _longmemeval_probes(),
        "agentmembench_memdialogue": _agentmembench_probes(),
    }
    exercised = [profile for profile in profiles.values() if profile["all_detected"] is not None]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_id": REPORT_ID,
        "purpose": "benchmark evaluator integrity, not retrieval efficacy",
        "profiles": profiles,
        "all_detected": all(profile["all_detected"] for profile in exercised),
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
