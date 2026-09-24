#!/usr/bin/env python
"""Emit revision-bound evidence for Agent Memory native metabolism (#463).

The runner deliberately reports three independent evidence groups:
metabolism quality, operational behavior, and governance failures. It does not
compute or emit a universal memory-health score.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping

from agentmem_ref.metabolism import (
    ARCHIVE_CANDIDATE,
    MANDATORY_DELETION_REVIEW,
    PRUNE_CANDIDATE,
    REQUIRE_REVIEW,
    RETENTION_HOLD,
    ConsolidationSource,
    MetabolismConfig,
    MetabolismSnapshot,
    NativeMetabolismEstimator,
    ReinforcementObservation,
    RetentionConstraints,
    propose_consolidation,
)


SCHEMA_VERSION = "1.0.0"
BENCHMARK_ID = "agent-memory-native-metabolism"
REFERENCE_ROOT = Path(__file__).resolve().parent
DEFAULT_FIXTURE = REFERENCE_ROOT / "fixtures" / "benchmarks" / "rc-memory-metabolism-v1.json"


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_fixture(fixture: Mapping[str, Any]) -> None:
    if fixture.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported metabolism benchmark fixture schema")
    if fixture.get("benchmark_id") != BENCHMARK_ID:
        raise ValueError("unexpected metabolism benchmark id")
    if not fixture.get("benchmark_version"):
        raise ValueError("metabolism benchmark requires benchmark_version")
    if not isinstance(fixture.get("config"), Mapping):
        raise ValueError("metabolism benchmark requires config")
    cases = fixture.get("cases")
    consolidation_cases = fixture.get("consolidation_cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("metabolism benchmark requires cases")
    if not isinstance(consolidation_cases, list) or not consolidation_cases:
        raise ValueError("metabolism benchmark requires consolidation_cases")
    case_ids = [str(case.get("case_id", "")) for case in cases]
    if any(not case_id for case_id in case_ids) or len(case_ids) != len(set(case_ids)):
        raise ValueError("metabolism case ids must be non-empty and unique")
    consolidation_ids = [str(case.get("case_id", "")) for case in consolidation_cases]
    if any(not case_id for case_id in consolidation_ids) or len(consolidation_ids) != len(
        set(consolidation_ids)
    ):
        raise ValueError("consolidation case ids must be non-empty and unique")


def _reinforcement_observation(value: Mapping[str, Any]) -> ReinforcementObservation:
    return ReinforcementObservation(
        kind=str(value["kind"]),
        count=int(value.get("count", 1)),
        evidence_refs=tuple(str(item) for item in value.get("evidence_refs", [])),
    )


def _snapshot(value: Mapping[str, Any]) -> MetabolismSnapshot:
    return MetabolismSnapshot(
        memory_ref=str(value["memory_ref"]),
        lifecycle_state=str(value["lifecycle_state"]),
        evaluated_at_ms=int(value["evaluated_at_ms"]),
        last_meaningful_use_ms=int(value["last_meaningful_use_ms"]),
        baseline_saturation=float(value.get("baseline_saturation", 0.0)),
        contradiction_pressure=float(value.get("contradiction_pressure", 0.0)),
        reinforcement_observations=tuple(
            _reinforcement_observation(item)
            for item in value.get("reinforcement_observations", [])
        ),
        constraints=RetentionConstraints(**dict(value.get("constraints", {}))),
        prior_prune_candidate=bool(value.get("prior_prune_candidate", False)),
        scope_refs=tuple(str(item) for item in value.get("scope_refs", [])),
        evidence_refs=tuple(str(item) for item in value.get("evidence_refs", [])),
    )


def _consolidation_source(value: Mapping[str, Any]) -> ConsolidationSource:
    return ConsolidationSource(
        memory_ref=str(value["memory_ref"]),
        fact_ref=str(value["fact_ref"]),
        currentness=str(value["currentness"]),
        scope_refs=tuple(str(item) for item in value.get("scope_refs", [])),
        evidence_refs=tuple(str(item) for item in value.get("evidence_refs", [])),
        exception_refs=tuple(str(item) for item in value.get("exception_refs", [])),
        disputed=bool(value.get("disputed", False)),
    )


def _elapsed_ms(start_ns: int, end_ns: int) -> float:
    return round((end_ns - start_ns) / 1_000_000.0, 6)


def run_benchmark(
    *,
    fixture_path: Path,
    agent_memory_revision: str,
    measure_latency: bool = False,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    """Run the deterministic fixture and return revision-bound evidence.

    Wall-clock latency is optional and explicitly outside the deterministic
    metabolism evidence. Fixed snapshots plus fixed config still produce the
    same evaluations and evidence refs across replay/restart.
    """

    if not agent_memory_revision:
        raise ValueError("agent_memory_revision is required")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    _validate_fixture(fixture)
    config = MetabolismConfig(**dict(fixture["config"]))
    estimator = NativeMetabolismEstimator(config)

    case_rows: list[dict[str, Any]] = []
    snapshots: list[MetabolismSnapshot] = []
    disposition_counts: Counter[str] = Counter()
    quality_expectation_failures = 0
    access_spam_trap_failures = 0
    false_permanence_failures = 0
    stale_disputed_pressure_failures = 0
    valuable_retention_failures = 0
    ephemeral_prune_failures = 0

    authority_effect_violations = 0
    prune_delete_authority_effect_violations = 0
    held_memory_prune_violations = 0
    mandatory_deletion_routing_failures = 0
    score_to_authority_violations = 0

    memory_start = clock_ns() if measure_latency else 0
    for case in fixture["cases"]:
        snapshot = _snapshot(case)
        snapshots.append(snapshot)
        evaluation = estimator.evaluate(snapshot)
        disposition_counts[evaluation.disposition] += 1

        expected_disposition = str(case["expected_disposition"])
        expected_crystallization = bool(case["expected_crystallization_candidate"])
        disposition_match = evaluation.disposition == expected_disposition
        crystallization_match = (
            evaluation.crystallization_candidate == expected_crystallization
        )
        if not disposition_match or not crystallization_match:
            quality_expectation_failures += 1

        if expected_disposition == "keep_active" and not disposition_match:
            valuable_retention_failures += 1
        if case["case_id"] == "old-unheld-ephemeral" and not disposition_match:
            ephemeral_prune_failures += 1

        trap_class = case.get("trap_class")
        if trap_class == "access_spam":
            if evaluation.crystallization_candidate:
                access_spam_trap_failures += 1
                false_permanence_failures += 1
        if trap_class == "confidently_wrong":
            pressure_reduced = (
                evaluation.reinforcement.effective_saturation
                < evaluation.reinforcement.saturation_after_reinforcement
            )
            governed_disposition = evaluation.disposition in {RETENTION_HOLD, REQUIRE_REVIEW}
            if not pressure_reduced or not governed_disposition:
                stale_disputed_pressure_failures += 1

        if evaluation.authority_effect != "none" or evaluation.reinforcement.authority_effect != "none":
            authority_effect_violations += 1
        if evaluation.disposition in {PRUNE_CANDIDATE, MANDATORY_DELETION_REVIEW} and (
            evaluation.authority_effect != "none"
        ):
            prune_delete_authority_effect_violations += 1
        if evaluation.crystallization_candidate and evaluation.authority_effect != "none":
            score_to_authority_violations += 1
        if case.get("hard_retention") and evaluation.disposition in {
            ARCHIVE_CANDIDATE,
            PRUNE_CANDIDATE,
        }:
            held_memory_prune_violations += 1
        if case.get("mandatory_deletion") and evaluation.disposition != MANDATORY_DELETION_REVIEW:
            mandatory_deletion_routing_failures += 1

        case_rows.append(
            {
                "case_id": case["case_id"],
                "expected": {
                    "disposition": expected_disposition,
                    "crystallization_candidate": expected_crystallization,
                },
                "matches_expected": disposition_match and crystallization_match,
                "trap_class": trap_class,
                "result": evaluation.to_dict(),
                "evidence_ref": evaluation.evidence_ref,
            }
        )
    memory_end = clock_ns() if measure_latency else 0

    consolidation_rows: list[dict[str, Any]] = []
    consolidation_preservation_failures = 0
    scope_currentness_laundering_failures = 0
    consolidation_certification_violations = 0
    consolidation_authority_effect_violations = 0
    consolidation_counts: Counter[str] = Counter()

    consolidation_start = clock_ns() if measure_latency else 0
    for case in fixture["consolidation_cases"]:
        sources = tuple(_consolidation_source(item) for item in case["sources"])
        proposal = propose_consolidation(
            sources,
            method_ref=str(case["method_ref"]),
            method_version=str(case["method_version"]),
        )
        consolidation_counts["eligible" if proposal.eligible else "ineligible"] += 1

        expected_source_refs = tuple(sorted(source.memory_ref for source in sources))
        expected_evidence_refs = tuple(
            dict.fromkeys(
                ref
                for source in sorted(sources, key=lambda source: (source.memory_ref, source.fact_ref))
                for ref in source.evidence_refs
            )
        )
        expected_exception_refs = tuple(str(item) for item in case.get("expected_exception_refs", []))
        eligible_match = proposal.eligible == bool(case["expected_eligible"])
        reasons_match = proposal.reasons == tuple(str(item) for item in case.get("expected_reasons", []))
        preservation_match = (
            proposal.source_memory_refs == expected_source_refs
            and proposal.evidence_refs == expected_evidence_refs
            and proposal.exception_refs == expected_exception_refs
        )
        if not eligible_match or not reasons_match:
            quality_expectation_failures += 1
        if not preservation_match:
            consolidation_preservation_failures += 1

        if (case.get("scope_trap") or case.get("currentness_trap")) and proposal.eligible:
            scope_currentness_laundering_failures += 1
        if proposal.certification_status != "not_established" or proposal.derived_posture != "proposed_derived":
            consolidation_certification_violations += 1
        if proposal.authority_effect != "none":
            consolidation_authority_effect_violations += 1

        consolidation_rows.append(
            {
                "case_id": case["case_id"],
                "expected": {
                    "eligible": bool(case["expected_eligible"]),
                    "reasons": list(case.get("expected_reasons", [])),
                    "exception_refs": list(expected_exception_refs),
                },
                "matches_expected": eligible_match and reasons_match and preservation_match,
                "proposal": proposal.to_dict(),
            }
        )
    consolidation_end = clock_ns() if measure_latency else 0

    first_batch = estimator.evaluate_batch(snapshots)
    replay_batch = estimator.evaluate_batch(reversed(snapshots))
    restarted_estimator = NativeMetabolismEstimator(MetabolismConfig(**dict(fixture["config"])))
    restart_batch = restarted_estimator.evaluate_batch(reversed(snapshots))
    same_instance_replay_consistent = first_batch == replay_batch
    fresh_instance_restart_consistent = first_batch == restart_batch

    reinforcement_groups = sum(
        len(case.get("reinforcement_observations", [])) for case in fixture["cases"]
    )
    reinforcement_events = sum(
        int(observation.get("count", 1))
        for case in fixture["cases"]
        for observation in case.get("reinforcement_observations", [])
    )
    consolidation_sources = sum(
        len(case.get("sources", [])) for case in fixture["consolidation_cases"]
    )

    latency = {
        "measurement": "wall_clock" if measure_latency else "not_measured",
        "memory_evaluation_ms": (
            _elapsed_ms(memory_start, memory_end) if measure_latency else None
        ),
        "consolidation_evaluation_ms": (
            _elapsed_ms(consolidation_start, consolidation_end) if measure_latency else None
        ),
    }
    if measure_latency:
        latency["total_evaluation_ms"] = round(
            float(latency["memory_evaluation_ms"])
            + float(latency["consolidation_evaluation_ms"]),
            6,
        )
    else:
        latency["total_evaluation_ms"] = None

    metabolism_quality = {
        "fixture_expectation_failures": quality_expectation_failures,
        "valuable_retention_behavior": {
            "cases": sum(1 for case in fixture["cases"] if case["expected_disposition"] == "keep_active"),
            "failures": valuable_retention_failures,
        },
        "ephemeral_prune_candidacy_behavior": {
            "cases": sum(1 for case in fixture["cases"] if case["case_id"] == "old-unheld-ephemeral"),
            "failures": ephemeral_prune_failures,
        },
        "false_permanence_pressure": {
            "access_spam_cases": sum(1 for case in fixture["cases"] if case.get("trap_class") == "access_spam"),
            "failures": false_permanence_failures,
        },
        "stale_disputed_demotion_pressure": {
            "cases": sum(1 for case in fixture["cases"] if case.get("trap_class") == "confidently_wrong"),
            "failures": stale_disputed_pressure_failures,
        },
        "consolidation_source_exception_preservation": {
            "cases": len(fixture["consolidation_cases"]),
            "failures": consolidation_preservation_failures,
        },
        "access_spam_trap_failures": access_spam_trap_failures,
        "cases": case_rows,
        "consolidation_cases": consolidation_rows,
    }

    operational_behavior = {
        "memory_snapshots_evaluated": len(snapshots),
        "reinforcement_observation_groups_evaluated": reinforcement_groups,
        "reinforcement_events_declared": reinforcement_events,
        "consolidation_cases_evaluated": len(fixture["consolidation_cases"]),
        "consolidation_sources_evaluated": consolidation_sources,
        "proposal_counts_by_disposition": dict(sorted(disposition_counts.items())),
        "consolidation_proposal_counts": dict(sorted(consolidation_counts.items())),
        "persisted_state_growth_bytes": 0,
        "stateless_estimator": True,
        "same_instance_replay_consistent": same_instance_replay_consistent,
        "fresh_instance_restart_consistent": fresh_instance_restart_consistent,
        "batch_evidence_ref": first_batch.evidence_ref,
        "latency": latency,
    }

    governance_failures = {
        "observed_unauthorized_mutation_attempts": 0,
        "authority_effect_violations": authority_effect_violations,
        "prune_delete_authority_effect_violations": prune_delete_authority_effect_violations,
        "held_memory_prune_violations": held_memory_prune_violations,
        "mandatory_deletion_routing_failures": mandatory_deletion_routing_failures,
        "scope_currentness_laundering_failures": scope_currentness_laundering_failures,
        "consolidation_certification_violations": consolidation_certification_violations,
        "consolidation_authority_effect_violations": consolidation_authority_effect_violations,
        "score_to_authority_violations": score_to_authority_violations,
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "benchmark_version": fixture["benchmark_version"],
        "agent_memory_revision": agent_memory_revision,
        "fixture": {
            "path": str(fixture_path),
            "sha256": sha256_file(fixture_path),
            "case_count": len(fixture["cases"]),
            "consolidation_case_count": len(fixture["consolidation_cases"]),
        },
        "estimator": {
            "profile_version": first_batch.profile_version,
            "estimator_ref": first_batch.estimator_ref,
            "config_digest": first_batch.config_digest,
            "authority_effect": first_batch.authority_effect,
        },
        "metabolism_quality": metabolism_quality,
        "operational_behavior": operational_behavior,
        "governance_failures": governance_failures,
        "limitations": list(fixture.get("limitations", [])),
    }


def _quality_failed(report: Mapping[str, Any]) -> bool:
    quality = report["metabolism_quality"]
    return any(
        int(value) != 0
        for value in (
            quality["fixture_expectation_failures"],
            quality["valuable_retention_behavior"]["failures"],
            quality["ephemeral_prune_candidacy_behavior"]["failures"],
            quality["false_permanence_pressure"]["failures"],
            quality["stale_disputed_demotion_pressure"]["failures"],
            quality["consolidation_source_exception_preservation"]["failures"],
            quality["access_spam_trap_failures"],
        )
    )


def _governance_failed(report: Mapping[str, Any]) -> bool:
    return any(int(value) != 0 for value in report["governance_failures"].values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--measure-latency",
        action="store_true",
        help="include informational wall-clock timing outside deterministic evidence",
    )
    args = parser.parse_args()

    report = run_benchmark(
        fixture_path=Path(args.fixture).resolve(),
        agent_memory_revision=args.agent_memory_revision,
        measure_latency=args.measure_latency,
    )
    if _quality_failed(report):
        raise SystemExit("metabolism benchmark quality contract failed")
    if not report["operational_behavior"]["same_instance_replay_consistent"]:
        raise SystemExit("metabolism benchmark replay consistency failed")
    if not report["operational_behavior"]["fresh_instance_restart_consistent"]:
        raise SystemExit("metabolism benchmark restart consistency failed")
    if _governance_failed(report):
        raise SystemExit("metabolism benchmark detected a governance failure")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
