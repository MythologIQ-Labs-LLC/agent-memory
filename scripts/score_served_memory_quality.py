#!/usr/bin/env python3
"""#771: grade the memories actually served, not the speed of their retrieval.

Offline, post-hoc scoring only. Gold labels and relevance judgments MUST NEVER
flow into a production runtime or a retrieval-control decision. No overall score.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

CASE_SCHEMA = "served-memory-quality-v1"
RUN_SCHEMA = "served-memory-run-v1"
INTENTS = frozenset(("current", "historical", "timeless"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _nonempty(value, label):
    if type(value) is not str or not value.strip():
        raise ValueError(label + " must be a nonempty string")
    return value


def _ids(values, label):
    if type(values) is not list or any(type(x) is not str or not x for x in values):
        raise ValueError(label + " must be a list of nonempty string IDs")
    if len(set(values)) != len(values):
        raise ValueError(label + " must not contain duplicates")
    return values


def _validate_case(case):
    if type(case) is not dict or set(case) != {
        "id", "scenario", "intent", "budget", "relevance", "critical_groups",
        "prohibited", "stale", "safe_answer_exists",
    }:
        raise ValueError("invalid or incomplete case")
    _nonempty(case["id"], "case id")
    _nonempty(case["scenario"], "scenario")
    if case["intent"] not in INTENTS:
        raise ValueError("unknown temporal intent")
    if type(case["budget"]) is not int or not 1 <= case["budget"] <= 100:
        raise ValueError("budget must be an integer 1..100")
    if type(case["safe_answer_exists"]) is not bool:
        raise ValueError("safe_answer_exists must be bool")
    relevance = case["relevance"]
    if type(relevance) is not dict or not relevance:
        raise ValueError("relevance must be a nonempty dict")
    for key, grade in relevance.items():
        _nonempty(key, "relevance ref")
        if type(grade) is not int or grade not in (0, 1, 2, 3):
            raise ValueError("graded relevance must be integer 0..3")
    banned = set(_ids(case["prohibited"], "prohibited"))
    stale = set(_ids(case["stale"], "stale"))
    if not banned.issubset(relevance) or not stale.issubset(relevance):
        raise ValueError("banned/stale IDs must be annotated in relevance")
    groups = case["critical_groups"]
    if type(groups) is not list:
        raise ValueError("critical_groups must be list of nonempty alternative lists")
    for group in groups:
        _ids(group, "critical group")
        if not group:
            raise ValueError("critical group must have alternatives")
        if any(ref not in relevance or ref in banned or ref in stale
               or relevance[ref] < 2 for ref in group):
            raise ValueError("critical alternatives must be eligible and relevant")
    eligible = [ref for ref, grade in relevance.items()
                if grade >= 2 and ref not in banned and ref not in stale]
    if case["safe_answer_exists"] != bool(groups and eligible):
        raise ValueError("answerability must match presence of safe critical groups")
    if not case["safe_answer_exists"] and any(grade >= 2 and ref not in banned and ref not in stale
                                               for ref, grade in relevance.items()):
        raise ValueError("no-safe-answer case cannot contain unused eligible answers")
    return case


def _gain(grade):
    return (2 ** grade) - 1


def _dcg(grades):
    return sum(_gain(grade) / math.log2(index + 2)
               for index, grade in enumerate(grades))


def _case_result(case, served):
    _ids(served, "returned")
    if len(served) > case["budget"]:
        raise ValueError("returned facts exceed declared budget")
    relevance = case["relevance"]
    if any(ref not in relevance for ref in served):
        raise ValueError("unlabeled served fact, do not presume irrelevant")
    prohibited = set(case["prohibited"])
    stale = set(case["stale"])
    safe_relevant = {ref for ref, grade in relevance.items()
                     if grade >= 2 and ref not in prohibited and ref not in stale}
    quality_hits = sum(ref in safe_relevant for ref in served)
    group_hits = sum(any(ref in served for ref in group) for group in case["critical_groups"])
    served_grades = [0 if ref in prohibited or ref in stale else relevance[ref] for ref in served]
    ideal_grades = sorted(
        (grade for ref, grade in relevance.items() if ref not in prohibited and ref not in stale),
        reverse=True,
    )[:case["budget"]]
    dcg_denom = _dcg(ideal_grades)
    return {
        "id": case["id"],
        "intent": case["intent"],
        "served_count": len(served),
        "prohibited_served": sum(ref in prohibited for ref in served),
        "stale_served": sum(ref in stale for ref in served),
        "irrelevant_served": sum(relevance[ref] == 0 and ref not in prohibited and ref not in stale
                                 for ref in served),
        "relevant_precision": round(quality_hits / len(served), 6) if served else None,
        "relevant_recall": round(quality_hits / len(safe_relevant), 6) if safe_relevant else None,
        "critical_groups_met": group_hits,
        "critical_groups_total": len(case["critical_groups"]),
        "critical_coverage": round(group_hits / len(case["critical_groups"]), 6)
                             if case["critical_groups"] else None,
        "top1_relevant": bool(served and served[0] in safe_relevant),
        "ndcg_at_budget": round(_dcg(served_grades) / dcg_denom, 6)
                          if dcg_denom else None,
        "abstained": not served,
        "abstention_correct": (not served) == (not case["safe_answer_exists"]),
        "safely_answerable": case["safe_answer_exists"],
    }


def score(cases_doc, runs_doc):
    if type(cases_doc) is not dict or set(cases_doc) != {"schema", "cases"} or cases_doc["schema"] != CASE_SCHEMA:
        raise ValueError("invalid case schema")
    if type(runs_doc) is not dict or set(runs_doc) != {"schema", "runtime_revision", "lane_id", "rows"} or runs_doc["schema"] != RUN_SCHEMA:
        raise ValueError("invalid run schema")
    _nonempty(runs_doc["runtime_revision"], "runtime revision")
    _nonempty(runs_doc["lane_id"], "lane id")
    cases = cases_doc["cases"]
    rows = runs_doc["rows"]
    if type(cases) is not list or not cases or type(rows) is not list:
        raise ValueError("cases and rows must be lists")
    for case in cases:
        _validate_case(case)
    case_ids = _ids([case["id"] for case in cases], "case ids")
    observed = {}
    for row in rows:
        if type(row) is not dict or set(row) != {"id", "returned"}:
            raise ValueError("run rows must have exactly id and returned")
        _nonempty(row["id"], "run case id")
        if row["id"] in observed:
            raise ValueError("duplicate run case id")
        observed[row["id"]] = _ids(row["returned"], "returned")
    if set(observed) != set(case_ids):
        raise ValueError("missing or extra run rows")
    evaluated = [_case_result(case, observed[case["id"]]) for case in cases]
    size = len(evaluated)
    answerable = [row for row in evaluated if row["safely_answerable"]]
    def rate(predicate, group=None):
        selected = evaluated if group is None else group
        return (round(sum(bool(predicate(row)) for row in selected) / len(selected), 6)
                if selected else None)
    def mean(name):
        nums = [row[name] for row in evaluated if row[name] is not None]
        return round(sum(nums) / len(nums), 6) if nums else None
    return {
        "schema": "served-memory-quality-report-v1",
        "runtime_revision": runs_doc["runtime_revision"],
        "lane_id": runs_doc["lane_id"],
        "quality_case_count": size,
        "P0_safety": {
            "cases_with_prohibited_exposure": sum(bool(row["prohibited_served"]) for row in evaluated),
            "cases_with_stale_exposure": sum(bool(row["stale_served"]) for row in evaluated),
        },
        "P1_served_correctness": {
            "answerable_case_count": len(answerable),
            "no_safe_answer_case_count": size - len(answerable),
            "top1_relevant_rate": rate(lambda r: r["top1_relevant"], answerable),
            "all_critical_groups_covered_rate": rate(
                lambda r: r["critical_groups_met"] == r["critical_groups_total"],
                answerable),
            "correct_abstention_rate": rate(lambda r: r["abstention_correct"]),
            "unsafe_empty_on_answerable_count": sum(r["safely_answerable"] and r["abstained"]
                                                    for r in evaluated),
        },
        "P2_context_utility": {
            "macro_relevant_precision": mean("relevant_precision"),
            "macro_relevant_recall": mean("relevant_recall"),
            "macro_critical_coverage": mean("critical_coverage"),
            "macro_ndcg_at_budget": mean("ndcg_at_budget"),
            "irrelevant_served_total": sum(r["irrelevant_served"] for r in evaluated),
        },
        "P3_efficiency": {"status": "not_measured_in_quality_scorer"},
        "per_case": evaluated,
        "not_a_composite_score": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    case_bytes = args.cases.read_bytes()
    run_bytes = args.runs.read_bytes()
    report = score(json.loads(case_bytes), json.loads(run_bytes))
    report["input_digests"] = {
        "cases_sha256": _sha256(case_bytes),
        "runs_sha256": _sha256(run_bytes),
    }
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")


if __name__ == "__main__":
    main()
