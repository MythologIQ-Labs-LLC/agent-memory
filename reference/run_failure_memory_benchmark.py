#!/usr/bin/env python
"""Emit revision-bound evidence for native governed failure memory (#471).

Quality, performance, and governance are reported independently. Similarity,
severity, and recurrence remain evidence and never become authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping

from agentmem_ref import policy
from agentmem_ref.adapter import Clock, GovernedMemoryAdapter, RecallContext
from agentmem_ref.failure_memory import (
    FailureRevision,
    FailureScope,
    derive_failure_ref,
)
from agentmem_ref.memory.failure_checkpoint import CheckpointedFailureMemory
from agentmem_ref.substrate import InMemoryTemporalGraph
from agentmem_ref.verification import (
    TRANSITION_VERIFIER,
    TransitionRule,
    TransitionRuleCorpus,
    VerifierRegistry,
)


SCHEMA_VERSION = "1.0.0"
BENCHMARK_ID = "agent-memory-native-failure-memory"
REFERENCE_ROOT = Path(__file__).resolve().parent
DEFAULT_FIXTURE = (
    REFERENCE_ROOT / "fixtures" / "benchmarks" / "rc-failure-memory-v1.json"
)
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_fixture(fixture: Mapping[str, Any]) -> None:
    if fixture.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported failure-memory benchmark fixture schema")
    if fixture.get("benchmark_id") != BENCHMARK_ID:
        raise ValueError("unexpected failure-memory benchmark id")
    if not fixture.get("benchmark_version"):
        raise ValueError("failure-memory benchmark requires benchmark_version")
    for key in ("tenant", "project_ref", "source_component", "scenario"):
        if not fixture.get(key):
            raise ValueError(f"failure-memory benchmark requires {key}")
    identity_cases = fixture.get("identity_cases")
    if not isinstance(identity_cases, list) or len(identity_cases) < 3:
        raise ValueError("failure-memory benchmark requires at least three identity cases")
    case_ids = [str(item.get("case_id", "")) for item in identity_cases]
    if any(not item for item in case_ids) or len(case_ids) != len(set(case_ids)):
        raise ValueError("identity case ids must be non-empty and unique")
    if any(not item.get("equivalence_group") for item in identity_cases):
        raise ValueError("identity cases require equivalence_group")


def _registry(failure_ref: str) -> tuple[TransitionRuleCorpus, VerifierRegistry]:
    corpus = TransitionRuleCorpus(
        (
            TransitionRule(
                rule_id="rule:failure-benchmark-revision",
                target_reference=failure_ref,
                criterion="failure-revision",
                from_state="current",
                permitted_to_values=("revised", "disputed", "retracted"),
            ),
        )
    )
    registry = VerifierRegistry()
    registry.register(TRANSITION_VERIFIER, corpus.verifier())
    return corpus, registry


def _scope(fixture: Mapping[str, Any]) -> FailureScope:
    tenant = str(fixture["tenant"])
    project_ref = str(fixture["project_ref"])
    return FailureScope(
        scope=tenant,
        isolation_domain_refs=(tenant, project_ref),
        required_isolation_domain_refs=(tenant, project_ref),
        project_ref=project_ref,
    )


def _context(
    fixture: Mapping[str, Any],
    *,
    project_ref: str | None = None,
) -> RecallContext:
    tenant = str(fixture["tenant"])
    project = project_ref or str(fixture["project_ref"])
    return RecallContext(
        target_domain_refs=(tenant, project),
        principal_ref="agent:failure-benchmark",
        project_ref=project,
        purpose="failure_recurrence_prevention",
    )


def _initial_revision(
    fixture: Mapping[str, Any],
    *,
    failure_ref: str,
) -> FailureRevision:
    scenario = fixture["scenario"]
    return FailureRevision(
        failure_ref=failure_ref,
        revision_ref="failure-benchmark-rev:001",
        action_class=str(scenario["action_class"]),
        summary=str(scenario["summary"]),
        category=str(scenario["category"]),
        causal_status="observed",
        scope=_scope(fixture),
        source_component=str(fixture["source_component"]),
        observed_at="2026-01-01T00:00:00Z",
        expected_outcome=str(scenario["expected_outcome"]),
        actual_outcome=str(scenario["actual_outcome"]),
        severity_label=str(scenario["severity_label"]),
        impact_score=float(scenario["impact_score"]),
        root_cause_candidates=tuple(
            str(item) for item in scenario.get("root_cause_candidates", [])
        ),
        mitigation=str(scenario["mitigation"]),
        verification_evidence_refs=("evidence:failure-benchmark-verified",),
        applicability_conditions=tuple(
            str(item) for item in scenario.get("applicability_conditions", [])
        ),
        source_evidence_refs=("evidence:failure-benchmark-source",),
        estimator_ref="estimator:failure-benchmark-similarity",
        estimator_version="1.0.0",
    )


def _retracted_revision(
    fixture: Mapping[str, Any],
    *,
    failure_ref: str,
    prior: FailureRevision,
) -> FailureRevision:
    return FailureRevision(
        failure_ref=failure_ref,
        revision_ref="failure-benchmark-rev:003",
        action_class=prior.action_class,
        summary="",
        category=prior.category,
        causal_status=prior.causal_status,
        scope=prior.scope,
        source_component=prior.source_component,
        observed_at="2026-01-03T00:00:00Z",
        severity_label=prior.severity_label,
        source_evidence_refs=("evidence:failure-benchmark-retraction",),
        prior_revision_ref=prior.revision_ref,
        revision_reason="benchmark source correction invalidated failure record",
        memory_status="retracted",
        estimator_ref=prior.estimator_ref,
        estimator_version=prior.estimator_version,
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
    if not _HEX40.fullmatch(agent_memory_revision):
        raise ValueError("agent_memory_revision must be an exact 40-hex commit")

    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    _validate_fixture(fixture)

    identity_rows: list[dict[str, Any]] = []
    refs_by_group: dict[str, set[str]] = {}
    for case in fixture["identity_cases"]:
        failure_ref = derive_failure_ref(
            scope=str(case["scope"]),
            action_class=str(case["action_class"]),
            category=str(case["category"]),
            identity_basis=str(case["identity_basis"]),
        )
        group = str(case["equivalence_group"])
        refs_by_group.setdefault(group, set()).add(failure_ref)
        identity_rows.append(
            {
                "case_id": str(case["case_id"]),
                "equivalence_group": group,
                "failure_ref": failure_ref,
            }
        )

    identity_equivalence_failures = sum(
        max(0, len(refs) - 1) for refs in refs_by_group.values()
    )
    groups = sorted(refs_by_group)
    identity_separation_failures = 0
    for index, left in enumerate(groups):
        for right in groups[index + 1 :]:
            if refs_by_group[left].intersection(refs_by_group[right]):
                identity_separation_failures += 1

    scenario = fixture["scenario"]
    failure_ref = derive_failure_ref(
        scope=str(fixture["tenant"]),
        action_class=str(scenario["action_class"]),
        category=str(scenario["category"]),
        identity_basis=str(scenario["identity_basis"]),
    )
    corpus, verifier_registry = _registry(failure_ref)
    substrate = InMemoryTemporalGraph()
    adapter = GovernedMemoryAdapter(
        substrate,
        tenant=str(fixture["tenant"]),
        clock=Clock(),
        verifier_registry=verifier_registry,
    )
    memory = CheckpointedFailureMemory(
        adapter=adapter,
        available_components=(str(fixture["source_component"]),),
    )

    latency: dict[str, float | None] = {
        "initial_write_ms": None,
        "recurrence_write_ms": None,
        "recall_ms": None,
        "retraction_ms": None,
    }

    first = _initial_revision(fixture, failure_ref=failure_ref)
    start = clock_ns() if measure_latency else 0
    first_result = memory.apply_revision(first, actor_id="agent:failure-benchmark")
    end = clock_ns() if measure_latency else 0
    if measure_latency:
        latency["initial_write_ms"] = _elapsed_ms(start, end)

    initial_commit_failures = int(not first_result.commit.committed)

    start = clock_ns() if measure_latency else 0
    initial_recall = memory.recall_active(
        str(scenario["query"]),
        context=_context(fixture),
    )
    end = clock_ns() if measure_latency else 0
    if measure_latency:
        latency["recall_ms"] = _elapsed_ms(start, end)
    retrieval_hits = int(failure_ref in initial_recall.active_object_refs)

    wrong_scope = memory.recall_active(
        str(scenario["query"]),
        context=_context(fixture, project_ref="project:failure-benchmark-foreign"),
    )
    wrong_scope_admission_violations = int(
        failure_ref in wrong_scope.active_object_refs
    )

    count_before_recall = memory.occurrence_count(failure_ref)
    history_before_recall = memory.history(failure_ref)
    for _ in range(int(fixture.get("repeat_recall_count", 5))):
        memory.recall_active(str(scenario["query"]), context=_context(fixture))
    recurrence_after_recall = memory.occurrence_count(failure_ref)
    recall_mutated_recurrence_violations = int(
        recurrence_after_recall != count_before_recall
        or memory.history(failure_ref) != history_before_recall
    )

    match = memory.match_evidence(failure_ref, similarity_score=1.0)
    similarity_authority_effect_violations = int(match.authority_effect != "none")

    refused = memory.record_recurrence(
        failure_ref,
        revision_ref="failure-benchmark-rev:blocked",
        recurrence_evidence_ref="evidence:failure-benchmark-blocked-recurrence",
        observed_at="2026-01-02T00:00:00Z",
        actor_id="agent:failure-benchmark",
        similarity_score=1.0,
    )
    similarity_correction_bypass_violations = int(refused.commit.committed)

    evidence = corpus.evidence_for(
        target_reference=failure_ref,
        criterion="failure-revision",
        pre_state="current",
        proposed_value="revised",
    )
    start = clock_ns() if measure_latency else 0
    second_result = memory.record_recurrence(
        failure_ref,
        revision_ref="failure-benchmark-rev:002",
        recurrence_evidence_ref="evidence:failure-benchmark-recurrence",
        observed_at="2026-01-02T00:00:00Z",
        actor_id="agent:failure-benchmark",
        similarity_score=float(scenario["recurrence_similarity_score"]),
        review_satisfied=True,
        approval_refs=("approval:failure-benchmark-review",),
        evidence=evidence,
    )
    end = clock_ns() if measure_latency else 0
    if measure_latency:
        latency["recurrence_write_ms"] = _elapsed_ms(start, end)

    recurrence_identification_failures = int(
        not second_result.commit.committed
        or memory.occurrence_count(failure_ref) != 2
        or memory.current(failure_ref) is None
        or memory.current(failure_ref).revision_ref != "failure-benchmark-rev:002"
    )
    currentness_failures = int(
        memory.revision_state(failure_ref, first.revision_ref) != "superseded"
        or memory.revision_state(
            failure_ref, "failure-benchmark-rev:002"
        ) != "current"
    )

    active_after_recurrence = memory.recall_active(
        str(scenario["query"]),
        context=_context(fixture),
    )
    retrieval_after_recurrence_hits = int(
        failure_ref in active_after_recurrence.active_object_refs
    )

    current = memory.current(failure_ref)
    if current is None:
        raise RuntimeError("benchmark requires current failure before retraction")
    retracted = _retracted_revision(
        fixture,
        failure_ref=failure_ref,
        prior=current,
    )
    start = clock_ns() if measure_latency else 0
    retraction_result = memory.apply_revision(
        retracted,
        actor_id="agent:failure-benchmark",
    )
    end = clock_ns() if measure_latency else 0
    if measure_latency:
        latency["retraction_ms"] = _elapsed_ms(start, end)

    post_retraction = memory.recall_active(
        str(scenario["query"]),
        context=_context(fixture),
    )
    retracted_resurfacing_violations = int(
        failure_ref in post_retraction.active_object_refs
        or adapter.current_fact_uuid(failure_ref) is not None
    )
    retraction_currentness_failures = int(
        not retraction_result.commit.committed
        or memory.revision_state(
            failure_ref, retracted.revision_ref
        ) != "retracted"
    )

    checkpoint = memory.export_checkpoint_state()
    checkpoint_bytes = len(
        json.dumps(
            checkpoint,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    )

    quality = {
        "identity_case_count": len(identity_rows),
        "identity_equivalence_failures": identity_equivalence_failures,
        "identity_separation_failures": identity_separation_failures,
        "false_recurrence_match_count": identity_separation_failures,
        "repeated_failure_retrieval": {
            "cases": 2,
            "hits": retrieval_hits + retrieval_after_recurrence_hits,
            "recall": round(
                (retrieval_hits + retrieval_after_recurrence_hits) / 2.0,
                6,
            ),
        },
        "initial_commit_failures": initial_commit_failures,
        "recurrence_identification_failures": recurrence_identification_failures,
        "correction_currentness_failures": currentness_failures,
        "retraction_currentness_failures": retraction_currentness_failures,
        "identity_cases": identity_rows,
        "avoided_repeated_failure": {
            "status": "not_measured",
            "reason": (
                "failure memory emits governed evidence; this benchmark does not "
                "own or simulate downstream action execution"
            ),
        },
    }

    performance = {
        "write_attempts": 4,
        "successful_writes": sum(
            int(result.commit.committed)
            for result in (first_result, refused, second_result, retraction_result)
        ),
        "recall_operations": 4 + int(fixture.get("repeat_recall_count", 5)),
        "owner_checkpoint_bytes": checkpoint_bytes,
        "substrate_storage_growth_bytes": None,
        "substrate_storage_growth_status": "not_measured_in_memory_profile",
        "latency_measurement": "wall_clock" if measure_latency else "not_measured",
        "latency": latency,
    }

    governance = {
        "wrong_scope_admission_violations": wrong_scope_admission_violations,
        "recall_mutated_recurrence_violations": recall_mutated_recurrence_violations,
        "similarity_authority_effect_violations": similarity_authority_effect_violations,
        "similarity_correction_bypass_violations": similarity_correction_bypass_violations,
        "retracted_resurfacing_violations": retracted_resurfacing_violations,
        "failure_memory_authority_effect": "none",
        "action_authority_claimed": False,
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": BENCHMARK_ID,
        "benchmark_version": str(fixture["benchmark_version"]),
        "agent_memory_revision": agent_memory_revision,
        "fixture": {
            "path": str(fixture_path),
            "sha256": sha256_file(fixture_path),
        },
        "quality": quality,
        "performance": performance,
        "governance": governance,
        "claim_boundary": {
            "no_aggregate_health_score": True,
            "similarity_is_authority": False,
            "recurrence_is_authority": False,
            "severity_is_authority": False,
            "action_execution_evaluated": False,
            "restart_recovery_evidence_source": (
                "reference/tests/test_failure_memory_restart.py"
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--agent-memory-commit", required=True)
    parser.add_argument("--measure-latency", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = run_benchmark(
        fixture_path=args.fixture,
        agent_memory_revision=args.agent_memory_commit,
        measure_latency=args.measure_latency,
    )
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
