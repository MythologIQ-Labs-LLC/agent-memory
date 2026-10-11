"""#769: diagnostic-only reference classification over synthetic admitted observations.

This evaluator is NOT imported by the Agent Memory runtime or recall controller.
Its 'reviewable' signal is hypothetical future-policy evidence, never permission
to recommend/execute stopping, attest receipt integrity, or access hidden memory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

FIELDS = (
    "receipt_state", "scope_enumeration", "admission_boundary",
    "support_posture", "typed_conflict", "untyped_competitor",
)
DOMAINS = {
    "receipt_state": frozenset(("verified", "missing", "mismatch", "stale")),
    "scope_enumeration": frozenset(("attested_complete", "read_path_observed", "partial", "unknown")),
    "admission_boundary": frozenset(("admitted_only", "unverified")),
    "support_posture": frozenset(("typed_support", "controller_estimate", "none")),
}


def assess(observation: dict) -> dict:
    """Classify *already-governed* evidence, preserving fail-closed precedence.

    ATTENTION: the current runtime cannot assert attested_complete. An
    independent durable scoped attestation is a necessary future precondition;
    the classification does not provide or verify such attestation.
    """
    if type(observation) is not dict or set(observation) != set(FIELDS):
        raise TypeError("observation must contain exactly the closed contract fields")
    for field, allowed in DOMAINS.items():
        if type(observation[field]) is not str or observation[field] not in allowed:
            raise ValueError("invalid evidence state for " + field)
    for field in ("typed_conflict", "untyped_competitor"):
        if type(observation[field]) is not bool:
            raise ValueError(field + " must be boolean, not inferred")
    if observation["receipt_state"] != "verified":
        state = "observation_integrity_unknown"
    elif observation["scope_enumeration"] != "attested_complete":
        state = "enumeration_unattested"
    elif observation["admission_boundary"] != "admitted_only":
        state = "admission_scope_unverified"
    elif observation["typed_conflict"]:
        state = "typed_conflict"
    elif observation["untyped_competitor"]:
        state = "untyped_identity_unverified"
    else:
        state = "no_competitor_observed"
    return {
        "competition_state": state,
        "reviewable_for_future_positive_policy": (
            state == "no_competitor_observed"
            and observation["support_posture"] == "typed_support"
        ),
        "stop_recommendation": "abstain",
        "authority_effect": "none",
    }


def verify_fixture(path: Path) -> dict:
    """Pure off-runtime evidence self-check, not a benchmark or acceptance."""
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema_version") != "769-observation-contract-v1":
        raise ValueError("unknown preregistered contract revision")
    cases = record.get("cases")
    if type(cases) is not list or record.get("case_count") != len(cases) or len(cases) < 30:
        raise ValueError("incomplete preregistered contract")
    ids: set[str] = set()
    states: dict[str, int] = {}
    for case in cases:
        if type(case) is not dict or set(case) != {"id", "group", "input", "expected", "notes"}:
            raise ValueError("invalid case shape")
        case_id = case["id"]
        if type(case_id) is not str or not case_id or case_id in ids:
            raise ValueError("duplicate or invalid case id")
        ids.add(case_id)
        observed = assess(case["input"])
        if observed != case["expected"]:
            raise AssertionError("contract failure at " + case_id)
        state = observed["competition_state"]
        states[state] = states.get(state, 0) + 1
    return {"contract": record["schema_version"], "cases": len(ids), "states": states,
            "positive_stops": 0, "authority_effect": "none", "runtime_qualified": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path,
                        default=Path(__file__).resolve().parents[1] /
                        "reference/fixtures/runtime/769-untyped-competition-v1.json")
    args = parser.parse_args()
    print(json.dumps(verify_fixture(args.fixture), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
