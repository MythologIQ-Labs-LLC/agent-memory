"""Validate independent, blinded qualitative reviews without inventing scores.

Usage: python scripts/check_789_qualitative_review.py DOSSIER.json REVIEWS.json
The reviewer identity and blinding procedures are verified by the study owner,
not by this purely structural checker. No scores are automatically inferred.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

DIMENSIONS = (
    "task_utility", "source_accuracy", "temporal_correctness",
    "selection_precision", "safe_absence", "workflow_recoverability",
)
ARMS = ("A", "B")
KINDS = {"human", "machine"}


def validate_review(r: object, target_ids: set[str]) -> tuple[str, str, str]:
    if not isinstance(r, dict):
        raise ValueError("review must be an object")
    if r.get("schema_version") != "competitive-qualitative-review/1":
        raise ValueError("wrong review schema")
    case, arm, reviewer = (r.get(k) for k in ("case_id", "blind_arm", "reviewer_id"))
    if case not in target_ids or arm not in ARMS or not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("invalid case, blind arm or reviewer identity")
    if r.get("reviewer_kind") not in KINDS or r.get("locked") is not True:
        raise ValueError("review must declare reviewer type and be locked")
    if r.get("benchmark_outcome_visible") is not False:
        raise ValueError("native outcome must not be shown before review lock")
    if not isinstance(r.get("source_trace"), str) or not r["source_trace"].strip():
        raise ValueError("source trace must be recorded")
    dims = r.get("dimensions")
    if not isinstance(dims, dict) or set(dims) != set(DIMENSIONS):
        raise ValueError("all dimensions required")
    for name in DIMENSIONS:
        d = dims[name]
        if not isinstance(d, dict) or not isinstance(d.get("rationale"), str) or not d["rationale"].strip():
            raise ValueError("each dimension needs a reason: " + name)
        value = d.get("rating")
        if (type(value) is not int or not 0 <= value <= 3) and value != "not_applicable":
            raise ValueError("unanchored rating: " + name)
        refs = d.get("evidence_refs")
        if not isinstance(refs, list) or any(not isinstance(x, str) or not x.strip() for x in refs):
            raise ValueError("invalid evidence refs: " + name)
        if value != "not_applicable" and not refs:
            raise ValueError("scored rating without supporting evidence: " + name)
    safety = r.get("safety_flags")
    if not isinstance(safety, dict) or set(safety) != {"unauthorized_exposure", "deleted_data_exposure"}:
        raise ValueError("explicit P0 safety flags required")
    if any(type(v) is not bool for v in safety.values()):
        raise ValueError("safety flags must be booleans")
    return case, arm, reviewer


def review_coverage(dossier: dict, reviews: list[dict]) -> dict:
    targets = dossier.get("review_selection", {}).get("target_case_ids", [])
    if not isinstance(targets, list) or not targets or len(set(targets)) != len(targets):
        raise ValueError("invalid frozen case selection")
    all_cases = {x.get("case_id") for x in dossier.get("entries", [])}
    if not set(targets) <= all_cases:
        raise ValueError("review selection not found in source dossier")
    if not isinstance(reviews, list):
        raise ValueError("reviews must be a list")
    groups = defaultdict(list)
    unique = set()
    for r in reviews:
        case, arm, reviewer = validate_review(r, set(targets))
        key = (case, arm, reviewer)
        if key in unique:
            raise ValueError("duplicate reviewer submission")
        unique.add(key)
        groups[(case, arm)].append(r)
    complete, disagreement, safety_cases = 0, {d: 0 for d in DIMENSIONS}, set()
    for case in targets:
        for arm in ARMS:
            entries = groups[(case, arm)]
            humans = [x for x in entries if x["reviewer_kind"] == "human"]
            if len(humans) >= 2:
                if len({x["reviewer_id"] for x in humans}) < 2:
                    raise ValueError("independent human reviewers missing")
                complete += 1
                for d in DIMENSIONS:
                    if len({x["dimensions"][d]["rating"] for x in humans}) > 1:
                        disagreement[d] += 1
            if any(x["safety_flags"][f] for x in entries for f in ("unauthorized_exposure", "deleted_data_exposure")):
                safety_cases.add(case)
    required = len(targets) * len(ARMS)
    return {
        "status": "ready_for_independent_adjudication" if complete == required else "incomplete_not_publishable",
        "frozen_target_cases": len(targets),
        "required_blind_case_arms": required,
        "independently_human_reviewed_case_arms": complete,
        "received_reviews": len(reviews),
        "unresolved_dimension_disagreements": disagreement,
        "cases_with_reported_P0_flags": sorted(safety_cases),
        "note": "No numerical quality score, provider ranking or adjudicated verdict is produced by this structural checker. Identity independence and blinding must be verified outside the tool.",
    }


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: check_789_qualitative_review.py dossier.json reviews.json")
    dossier = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    reviews = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    print(json.dumps(review_coverage(dossier, reviews), indent=2))


if __name__ == "__main__":
    main()
