#!/usr/bin/env python
"""Benchmark repeated keyed rebinding and stale-value resistance through AgentMemory.

The workload is independently synthesized from a bounded lesson identified while
reviewing UOR-R4: repeated updates to stable logical keys should be tested against
matched controls, stale-value resurfacing, and restart recovery. No UOR-R4 code,
schema, geometry, or runtime is used here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Mapping

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm

BENCHMARK_ID = "agent-memory-keyed-rebinding-stale-resistance"
BENCHMARK_VERSION = "1.0.0"
UOR_R4_REVISION = "552d847d49fb263966165004b835f2f53cccaae1"
TENANT = "tenant:keyed-rebinding"
SCOPE = "project:keyed-rebinding"
ACTOR = "agent:keyed-rebinding"
PURPOSE = "keyed rebinding benchmark"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _require_revision(value: str) -> str:
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError("agent_memory_revision must be exact lowercase 40-hex")
    return value


def _qualified_evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:keyed-rebinding-benchmark",
        version=1,
        purpose="verify deterministic keyed correction",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown=(
            "# Keyed rebinding verification\n"
            "Confirm the proposed value for the stable logical key against the benchmark source."
        ),
        provenance_refs=("evidence:keyed-rebinding-fixture",),
    )
    return pm.evidence_for(skill)


def _history(result: Mapping[str, object]) -> Mapping[str, object]:
    value = result.get("history", {})
    return value if isinstance(value, Mapping) else {}


def _current_fact(result: Mapping[str, object]) -> str | None:
    value = _history(result).get("current_fact_uuid")
    return value if isinstance(value, str) else None


def _state_version(result: Mapping[str, object]) -> int:
    value = _history(result).get("state_version", 0)
    return int(value) if isinstance(value, int) else 0


def _event_count(result: Mapping[str, object]) -> int:
    events = _history(result).get("events", [])
    return len(events) if isinstance(events, list) else 0


def _configuration_digest(result: Mapping[str, object]) -> str | None:
    posture = result.get("posture", {})
    if not isinstance(posture, Mapping):
        return None
    configuration = posture.get("configuration", {})
    if not isinstance(configuration, Mapping):
        return None
    digest = configuration.get("digest")
    return digest if isinstance(digest, str) else None


def _quantile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * fraction))))
    return round(ordered[index], 6)


def _fixture(key_count: int, rounds: int) -> dict:
    return {
        "key_count": key_count,
        "control_count": key_count,
        "rounds": rounds,
        "rebind_targets": [f"memory:rebind:{index:02d}" for index in range(key_count)],
        "control_targets": [f"memory:control:{index:02d}" for index in range(key_count)],
        "rebind_values": {
            f"memory:rebind:{index:02d}": [
                f"key {index:02d} binding value v{round_index}"
                for round_index in range(rounds + 1)
            ]
            for index in range(key_count)
        },
        "control_values": {
            f"memory:control:{index:02d}": f"control {index:02d} stable value v0"
            for index in range(key_count)
        },
    }


def run_benchmark(agent_memory_revision: str, *, key_count: int = 6, rounds: int = 4) -> dict:
    revision = _require_revision(agent_memory_revision)
    if key_count < 1:
        raise ValueError("key_count must be >= 1")
    if rounds < 2:
        raise ValueError("rounds must be >= 2 so midpoint and final recovery are both meaningful")

    fixture = _fixture(key_count, rounds)
    fixture_digest = _digest(fixture)
    evidence = _qualified_evidence()
    update_latencies_ms: list[float] = []
    recall_latencies_ms: list[float] = []
    correction_attempts = 0
    correction_commits = 0
    current_retrieval_attempts = 0
    current_retrieval_hits = 0
    stale_candidate_hits = 0
    stale_admission_hits = 0
    stale_observations = 0
    restart_mismatches = 0
    wall_started = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="agent-memory-rebinding-") as temporary:
        root = Path(temporary)
        memory = AgentMemory.open(
            root,
            tenant=TENANT,
            actor_id=ACTOR,
            scope=SCOPE,
            purpose=PURPOSE,
        )
        contract_version = memory.contract_version

        rebind_targets = list(fixture["rebind_targets"])
        control_targets = list(fixture["control_targets"])
        initial_fact: dict[str, str] = {}
        current_fact: dict[str, str] = {}
        stale_facts: dict[str, set[str]] = {target: set() for target in rebind_targets}

        for target in rebind_targets:
            seed = memory.remember(target, fixture["rebind_values"][target][0])
            if not seed.get("committed"):
                raise RuntimeError(f"seed failed for {target}: {seed}")
            history = memory.history(target)
            fact = _current_fact(history)
            if fact is None:
                raise RuntimeError(f"seed did not establish current fact for {target}")
            initial_fact[target] = fact
            current_fact[target] = fact

        control_initial: dict[str, str] = {}
        for target in control_targets:
            seed = memory.remember(target, fixture["control_values"][target])
            if not seed.get("committed"):
                raise RuntimeError(f"control seed failed for {target}: {seed}")
            fact = _current_fact(memory.history(target))
            if fact is None:
                raise RuntimeError(f"control seed did not establish current fact for {target}")
            control_initial[target] = fact

        probe_target = "memory:rebind:governance-probe"
        probe_seed = memory.remember(probe_target, "governance probe value v0")
        if not probe_seed.get("committed"):
            raise RuntimeError(f"governance probe seed failed: {probe_seed}")
        unqualified = memory.correct(probe_target, "governance probe value v1")

        configuration_digests = [_configuration_digest(memory.posture())]
        midpoint = rounds // 2
        restart_count = 0

        for round_index in range(1, rounds + 1):
            for target in rebind_targets:
                prior = current_fact[target]
                stale_facts[target].add(prior)
                new_value = fixture["rebind_values"][target][round_index]
                started = time.perf_counter()
                correction = memory.correct(target, new_value, evidence=evidence)
                update_latencies_ms.append((time.perf_counter() - started) * 1000.0)
                correction_attempts += 1
                if correction.get("committed"):
                    correction_commits += 1

                history = memory.history(target)
                new_current = _current_fact(history)
                if new_current is None:
                    raise RuntimeError(f"correction removed current fact for {target}")
                current_fact[target] = new_current

                started = time.perf_counter()
                recalled = memory.recall(new_value, logical_memory_refs=(target,))
                recall_latencies_ms.append((time.perf_counter() - started) * 1000.0)
                candidates = set(recalled.get("candidates", []))
                admitted = set(recalled.get("admitted", []))
                current_retrieval_attempts += 1
                if new_current in admitted:
                    current_retrieval_hits += 1

                stale_observations += len(stale_facts[target])
                stale_candidate_hits += len(stale_facts[target].intersection(candidates))
                stale_admission_hits += len(stale_facts[target].intersection(admitted))

            if round_index == midpoint:
                before_restart = dict(current_fact)
                memory.close()
                memory = AgentMemory.open(
                    root,
                    tenant=TENANT,
                    actor_id=ACTOR,
                    scope=SCOPE,
                    purpose=PURPOSE,
                )
                restart_count += 1
                configuration_digests.append(_configuration_digest(memory.posture()))
                for target, expected in before_restart.items():
                    if _current_fact(memory.history(target)) != expected:
                        restart_mismatches += 1

        control_stable = 0
        for target in control_targets:
            history = memory.history(target)
            current = _current_fact(history)
            if current == control_initial[target] and _state_version(history) == 1:
                control_stable += 1

        sample_target = rebind_targets[0]
        sample_value = fixture["rebind_values"][sample_target][-1]
        wrong_scope = memory.recall(
            sample_value,
            logical_memory_refs=(sample_target,),
            target_domain_refs=("tenant:other", "project:other"),
            project_ref="project:other",
        )
        wrong_scope_admissions = len(wrong_scope.get("admitted", []))

        pre_final = dict(current_fact)
        memory.close()
        memory = AgentMemory.open(
            root,
            tenant=TENANT,
            actor_id=ACTOR,
            scope=SCOPE,
            purpose=PURPOSE,
        )
        restart_count += 1
        configuration_digests.append(_configuration_digest(memory.posture()))
        for target, expected in pre_final.items():
            if _current_fact(memory.history(target)) != expected:
                restart_mismatches += 1

        history_preserved = 0
        final_state: dict[str, dict] = {}
        for target in rebind_targets:
            history = memory.history(target)
            current = _current_fact(history)
            version = _state_version(history)
            events = _event_count(history)
            if current == current_fact[target] and current != initial_fact[target] and version >= rounds + 1 and events >= rounds + 1:
                history_preserved += 1
            final_state[target] = {
                "current_fact_uuid": current,
                "initial_fact_uuid": initial_fact[target],
                "state_version": version,
                "event_count": events,
            }

        persistent_state_bytes = sum(
            path.stat().st_size for path in root.rglob("*") if path.is_file()
        )
        memory.close()

    total_wall_ms = (time.perf_counter() - wall_started) * 1000.0
    correction_commit_rate = correction_commits / correction_attempts if correction_attempts else 0.0
    current_retrieval_rate = current_retrieval_hits / current_retrieval_attempts if current_retrieval_attempts else 0.0
    stale_candidate_rate = stale_candidate_hits / stale_observations if stale_observations else 0.0
    stale_admission_rate = stale_admission_hits / stale_observations if stale_observations else 0.0
    control_stability_rate = control_stable / len(fixture["control_targets"])
    history_preservation_rate = history_preserved / len(fixture["rebind_targets"])
    digest_values = [value for value in configuration_digests if value is not None]
    configuration_digest_stable = bool(digest_values) and len(set(digest_values)) == 1

    quality = {
        "correction_attempts": correction_attempts,
        "correction_commits": correction_commits,
        "correction_commit_rate": round(correction_commit_rate, 6),
        "current_fact_retrieval_attempts": current_retrieval_attempts,
        "current_fact_retrieval_hits": current_retrieval_hits,
        "current_fact_retrieval_rate": round(current_retrieval_rate, 6),
        "stale_fact_observations": stale_observations,
        "stale_fact_candidate_hits": stale_candidate_hits,
        "stale_fact_candidate_rate": round(stale_candidate_rate, 6),
        "stale_fact_admission_hits": stale_admission_hits,
        "stale_fact_admission_rate": round(stale_admission_rate, 6),
        "matched_control_stability_rate": round(control_stability_rate, 6),
        "history_preservation_rate": round(history_preservation_rate, 6),
    }
    performance = {
        "update_latency_ms": {
            "count": len(update_latencies_ms),
            "median": round(statistics.median(update_latencies_ms), 6) if update_latencies_ms else 0.0,
            "p95": _quantile(update_latencies_ms, 0.95),
        },
        "recall_latency_ms": {
            "count": len(recall_latencies_ms),
            "median": round(statistics.median(recall_latencies_ms), 6) if recall_latencies_ms else 0.0,
            "p95": _quantile(recall_latencies_ms, 0.95),
        },
        "total_wall_ms": round(total_wall_ms, 6),
        "persistent_state_bytes": persistent_state_bytes,
        "timing_is_conformance_gate": False,
    }
    governance = {
        "unqualified_correction_committed": bool(unqualified.get("committed", False)),
        "unqualified_correction_outcome": unqualified.get("outcome"),
        "wrong_scope_admission_count": wrong_scope_admissions,
        "stale_currentness_violation_count": stale_admission_hits,
        "retrieval_evidence_authority_effect": "none",
    }
    recovery = {
        "restart_count": restart_count,
        "restart_current_fact_mismatch_count": restart_mismatches,
        "configuration_digests": configuration_digests,
        "configuration_digest_stable": configuration_digest_stable,
        "final_state": final_state,
    }
    checks = {
        "all_qualified_corrections_committed": correction_commit_rate == 1.0,
        "all_current_facts_retrieved": current_retrieval_rate == 1.0,
        "superseded_facts_never_candidates": stale_candidate_hits == 0,
        "superseded_facts_never_admitted": stale_admission_hits == 0,
        "matched_controls_stable": control_stability_rate == 1.0,
        "history_preserved": history_preservation_rate == 1.0,
        "unqualified_correction_did_not_commit": not bool(unqualified.get("committed", False)),
        "wrong_scope_not_admitted": wrong_scope_admissions == 0,
        "restart_currentness_recovered": restart_mismatches == 0,
        "configuration_binding_stable": configuration_digest_stable,
        "two_restarts_exercised": restart_count == 2,
    }

    return {
        "benchmark_id": BENCHMARK_ID,
        "benchmark_version": BENCHMARK_VERSION,
        "agent_memory_revision": revision,
        "contract_version": contract_version,
        "fixture": fixture,
        "fixture_digest": fixture_digest,
        "source_pressure": {
            "source": "UOR-Foundation/uor-r4",
            "revision": UOR_R4_REVISION,
            "rights_basis": "MIT at inspected revision",
            "lesson": "repeated exact-key rebinding with matched controls and explicit stale-value evaluation",
            "code_or_schema_reused": False,
            "geometric_model_adopted": False,
            "runtime_dependency_required": False,
        },
        "quality": quality,
        "performance": performance,
        "governance": governance,
        "runtime_recovery": recovery,
        "checks": checks,
        "passed": all(checks.values()),
        "claim_boundary": {
            "tests_native_agent_memory_currentness": True,
            "proves_uor_geometry": False,
            "external_swe_context_benchmark": False,
            "answer_generation_quality_claimed": False,
            "aggregate_health_score_emitted": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-commit", required=True)
    parser.add_argument("--key-count", type=int, default=6)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run_benchmark(args.agent_memory_commit, key_count=args.key_count, rounds=args.rounds)
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["passed"]:
        failed = [name for name, passed in report["checks"].items() if not passed]
        raise SystemExit(f"keyed rebinding benchmark failed: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
