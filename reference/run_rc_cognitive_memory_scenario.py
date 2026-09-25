#!/usr/bin/env python
"""Execute the RC1 end-to-end cognitive-memory lifecycle through AgentMemory.

This is product-composition evidence, not another provider benchmark. Every
mutation and recall enters through the installed developer facade added by
#477, while the report keeps retrieval, governance, and recovery observations
separate rather than manufacturing one universal health score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Mapping

from agentmem_ref import AgentMemory, policy
from agentmem_ref.memory import procedural_memory as pm

SCENARIO_ID = "agent-memory-rc1-cognitive-lifecycle"
SCENARIO_VERSION = "1.0.0"
TENANT = "tenant:rc-scenario"
SCOPE = "project:rc-scenario"
ACTOR = "agent:rc-scenario"
PURPOSE = "rc cognitive memory lifecycle"

PRIMARY = "memory:release-branch"
SECONDARY = "memory:deployment-window"
LOW_CONFIDENCE = "memory:confidence-low"
HIGH_CONFIDENCE = "memory:confidence-high"

PRIMARY_INITIAL = "release branch release"
PRIMARY_CORRECTED = "release branch main"
SECONDARY_VALUE = "deployment window Thursday"


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
        skill_id="skill:rc-cognitive-lifecycle",
        version=1,
        purpose="verify correction and governed lifecycle mutation",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown=(
            "# RC lifecycle verification\n"
            "Confirm the proposed memory change against the current source and preserve prior history."
        ),
        provenance_refs=("evidence:rc-cognitive-lifecycle-source",),
    )
    return pm.evidence_for(skill)


def _receipt_ref(result: Mapping[str, object]) -> str | None:
    receipt = result.get("receipt")
    return None if receipt is None else _digest(receipt)


def _mutation_summary(result: Mapping[str, object]) -> dict:
    decision = result.get("decision")
    decision_map = decision if isinstance(decision, Mapping) else {}
    return {
        "outcome": result.get("outcome"),
        "committed": bool(result.get("committed", False)),
        "fact_uuid": result.get("fact_uuid"),
        "refusal": result.get("refusal"),
        "receipt_ref": _receipt_ref(result),
        "permitted_actions": list(decision_map.get("permitted_actions", [])),
        "prohibited_actions": list(decision_map.get("prohibited_actions", [])),
    }


def _recall_summary(result: Mapping[str, object]) -> dict:
    candidates = list(result.get("candidates", []))
    admitted = list(result.get("admitted", []))
    admissions = result.get("admissions", {})
    routes: dict[str, list[str]] = {}
    refusals: dict[str, object] = {}
    if isinstance(admissions, Mapping):
        for candidate in candidates:
            row = admissions.get(candidate, {})
            if not isinstance(row, Mapping):
                continue
            provenance = row.get("route_provenance", [])
            route_ids: list[str] = []
            if isinstance(provenance, list):
                for item in provenance:
                    if isinstance(item, Mapping) and isinstance(item.get("route_id"), str):
                        route_ids.append(str(item["route_id"]))
            routes[candidate] = route_ids
            if "refusal" in row:
                refusals[candidate] = row.get("refusal")
    return {
        "candidates": candidates,
        "admitted": admitted,
        "candidate_count": len(candidates),
        "admitted_count": len(admitted),
        "route_ids": routes,
        "refusals": refusals,
    }


def _history_summary(result: Mapping[str, object]) -> dict:
    history = result.get("history", {})
    history_map = history if isinstance(history, Mapping) else {}
    events = history_map.get("events", [])
    event_types = []
    if isinstance(events, list):
        event_types = [
            str(event.get("event_type"))
            for event in events
            if isinstance(event, Mapping) and event.get("event_type") is not None
        ]
    return {
        "current_fact_uuid": history_map.get("current_fact_uuid"),
        "state_version": history_map.get("state_version"),
        "tombstoned": bool(history_map.get("tombstoned", False)),
        "event_count": len(events) if isinstance(events, list) else 0,
        "event_types": event_types,
    }


def _posture_summary(result: Mapping[str, object]) -> dict:
    posture = result.get("posture", {})
    posture_map = posture if isinstance(posture, Mapping) else {}
    configuration = posture_map.get("configuration", {})
    recovery = posture_map.get("recovery", {})
    durable = posture_map.get("durable_state", {})
    currentness = posture_map.get("currentness", {})
    return {
        "configuration_digest": configuration.get("digest") if isinstance(configuration, Mapping) else None,
        "profile_id": configuration.get("profile_id") if isinstance(configuration, Mapping) else None,
        "durable_state_status": durable.get("status") if isinstance(durable, Mapping) else None,
        "durable_state_profile": durable.get("profile") if isinstance(durable, Mapping) else None,
        "recovery_status": recovery.get("status") if isinstance(recovery, Mapping) else None,
        "durability_profile": recovery.get("durability_profile") if isinstance(recovery, Mapping) else None,
        "base_durability_profile": recovery.get("base_durability_profile") if isinstance(recovery, Mapping) else None,
        "substrate_profile": recovery.get("substrate_profile") if isinstance(recovery, Mapping) else None,
        "currentness_status": currentness.get("status") if isinstance(currentness, Mapping) else None,
        "authority_effect": posture_map.get("authority_effect"),
    }


def run_scenario(agent_memory_revision: str) -> dict:
    revision = _require_revision(agent_memory_revision)
    evidence = _qualified_evidence()

    with tempfile.TemporaryDirectory(prefix="agent-memory-rc1-") as temporary:
        root = Path(temporary)
        memory = AgentMemory.open(
            root,
            tenant=TENANT,
            actor_id=ACTOR,
            scope=SCOPE,
            purpose=PURPOSE,
        )
        contract_version = memory.contract_version

        primary_seed = memory.remember(PRIMARY, PRIMARY_INITIAL)
        secondary_seed = memory.remember(SECONDARY, SECONDARY_VALUE)
        low_confidence = memory.remember(LOW_CONFIDENCE, "same authority evidence", confidence=0.01)
        high_confidence = memory.remember(HIGH_CONFIDENCE, "same authority evidence", confidence=0.99)

        initial_recall = memory.recall(
            "release branch deployment Thursday",
            logical_memory_refs=(PRIMARY, SECONDARY),
        )

        correction_parked = memory.correct(PRIMARY, PRIMARY_CORRECTED)
        correction_committed = memory.correct(PRIMARY, PRIMARY_CORRECTED, evidence=evidence)
        corrected_history = memory.history(PRIMARY)
        corrected_recall = memory.recall(
            "release branch main",
            logical_memory_refs=(PRIMARY,),
        )
        wrong_scope = memory.recall(
            "release branch main",
            logical_memory_refs=(PRIMARY,),
            target_domain_refs=("tenant:other", "project:other"),
            project_ref="project:other",
        )
        posture_before_restart = memory.posture()
        memory.close()

        first_recovery = AgentMemory.open(
            root,
            tenant=TENANT,
            actor_id=ACTOR,
            scope=SCOPE,
            purpose=PURPOSE,
        )
        posture_restart_1 = first_recovery.posture()
        recall_restart_1 = first_recovery.recall(
            "release branch main",
            logical_memory_refs=(PRIMARY,),
        )
        forgotten = first_recovery.forget(SECONDARY, evidence=evidence)
        forgotten_history = first_recovery.history(SECONDARY)
        forgotten_recall = first_recovery.recall(
            SECONDARY_VALUE,
            logical_memory_refs=(SECONDARY,),
        )
        first_recovery.close()

        second_recovery = AgentMemory.open(
            root,
            tenant=TENANT,
            actor_id=ACTOR,
            scope=SCOPE,
            purpose=PURPOSE,
        )
        posture_restart_2 = second_recovery.posture()
        final_primary_history = second_recovery.history(PRIMARY)
        final_secondary_history = second_recovery.history(SECONDARY)
        final_primary_recall = second_recovery.recall(
            "release branch main",
            logical_memory_refs=(PRIMARY,),
        )
        final_secondary_recall = second_recovery.recall(
            SECONDARY_VALUE,
            logical_memory_refs=(SECONDARY,),
        )
        second_recovery.close()

    primary_seed_s = _mutation_summary(primary_seed)
    secondary_seed_s = _mutation_summary(secondary_seed)
    low_confidence_s = _mutation_summary(low_confidence)
    high_confidence_s = _mutation_summary(high_confidence)
    correction_parked_s = _mutation_summary(correction_parked)
    correction_committed_s = _mutation_summary(correction_committed)
    forgotten_s = _mutation_summary(forgotten)

    initial_recall_s = _recall_summary(initial_recall)
    corrected_recall_s = _recall_summary(corrected_recall)
    wrong_scope_s = _recall_summary(wrong_scope)
    restart_1_recall_s = _recall_summary(recall_restart_1)
    forgotten_recall_s = _recall_summary(forgotten_recall)
    final_primary_recall_s = _recall_summary(final_primary_recall)
    final_secondary_recall_s = _recall_summary(final_secondary_recall)

    corrected_history_s = _history_summary(corrected_history)
    forgotten_history_s = _history_summary(forgotten_history)
    final_primary_history_s = _history_summary(final_primary_history)
    final_secondary_history_s = _history_summary(final_secondary_history)

    posture_0_s = _posture_summary(posture_before_restart)
    posture_1_s = _posture_summary(posture_restart_1)
    posture_2_s = _posture_summary(posture_restart_2)

    old_primary = primary_seed_s["fact_uuid"]
    corrected_primary = correction_committed_s["fact_uuid"]
    secondary_fact = secondary_seed_s["fact_uuid"]

    checks = {
        "initial_memories_committed": bool(primary_seed_s["committed"] and secondary_seed_s["committed"]),
        "initial_recall_has_nontrivial_candidate_set": initial_recall_s["candidate_count"] >= 2,
        "initial_primary_and_secondary_admitted": (
            old_primary in initial_recall_s["admitted"] and secondary_fact in initial_recall_s["admitted"]
        ),
        "correction_without_qualified_evidence_requires_review": (
            correction_parked_s["committed"] is False
            and correction_parked_s["outcome"] == policy.REQUIRE_REVIEW
        ),
        "correction_with_qualified_evidence_commits": (
            correction_committed_s["committed"] is True
            and corrected_primary is not None
        ),
        "superseded_value_not_current": (
            corrected_history_s["current_fact_uuid"] == corrected_primary
            and corrected_primary != old_primary
        ),
        "superseded_value_not_admitted_as_current": (
            corrected_primary in corrected_recall_s["admitted"]
            and old_primary not in corrected_recall_s["admitted"]
        ),
        "superseded_history_preserved": corrected_history_s["event_count"] >= 2,
        "restart_one_recovers_corrected_current_state": (
            posture_1_s["recovery_status"] == "recovered"
            and corrected_primary in restart_1_recall_s["admitted"]
        ),
        "forget_pruning_commits": forgotten_s["committed"] is True,
        "forgotten_memory_tombstoned_with_history": (
            forgotten_history_s["tombstoned"] is True
            and forgotten_history_s["event_count"] >= 2
        ),
        "forgotten_memory_not_admitted": secondary_fact not in forgotten_recall_s["admitted"],
        "restart_two_preserves_current_and_tombstone_state": (
            posture_2_s["recovery_status"] == "recovered"
            and final_primary_history_s["current_fact_uuid"] == corrected_primary
            and final_secondary_history_s["tombstoned"] is True
            and corrected_primary in final_primary_recall_s["admitted"]
            and secondary_fact not in final_secondary_recall_s["admitted"]
        ),
        "wrong_scope_candidate_never_admitted": (
            corrected_primary in wrong_scope_s["candidates"]
            and corrected_primary not in wrong_scope_s["admitted"]
        ),
        "confidence_does_not_widen_authority": (
            low_confidence_s["outcome"] == high_confidence_s["outcome"]
            and low_confidence_s["permitted_actions"] == high_confidence_s["permitted_actions"]
            and low_confidence_s["prohibited_actions"] == high_confidence_s["prohibited_actions"]
        ),
        "configuration_digest_stable_across_restarts": (
            bool(posture_0_s["configuration_digest"])
            and posture_0_s["configuration_digest"] == posture_1_s["configuration_digest"]
            and posture_1_s["configuration_digest"] == posture_2_s["configuration_digest"]
        ),
        "sqlite_profile_recovered": (
            posture_2_s["durable_state_profile"] == "sqlite_single_host_v1"
            and posture_2_s["base_durability_profile"] == "sqlite_transactional_runtime_v1"
        ),
        "posture_never_claims_authority": (
            posture_0_s["authority_effect"] == "none"
            and posture_1_s["authority_effect"] == "none"
            and posture_2_s["authority_effect"] == "none"
        ),
    }

    report = {
        "schema_version": "1.0.0",
        "scenario_id": SCENARIO_ID,
        "scenario_version": SCENARIO_VERSION,
        "agent_memory_revision": revision,
        "contract_version": contract_version,
        "quality": {
            "initial_recall": initial_recall_s,
            "after_correction": corrected_recall_s,
            "after_restart_one": restart_1_recall_s,
            "after_forgetting": forgotten_recall_s,
            "final_primary_recall": final_primary_recall_s,
            "final_secondary_recall": final_secondary_recall_s,
            "interpretation": "retrieval observations only; no authority effect and no aggregate quality/health score",
        },
        "governance": {
            "primary_seed": primary_seed_s,
            "secondary_seed": secondary_seed_s,
            "correction_without_evidence": correction_parked_s,
            "correction_with_evidence": correction_committed_s,
            "forget_pruning": forgotten_s,
            "wrong_scope_recall": wrong_scope_s,
            "confidence_low": low_confidence_s,
            "confidence_high": high_confidence_s,
            "interpretation": "PAMA/lifecycle evidence; retrieval relevance and confidence do not create authority",
        },
        "runtime_recovery": {
            "before_restart": posture_0_s,
            "restart_one": posture_1_s,
            "restart_two": posture_2_s,
            "interpretation": "bounded single-host SQLite recovery/currentness evidence, not distributed durability",
        },
        "history": {
            "primary_after_correction": corrected_history_s,
            "secondary_after_forgetting": forgotten_history_s,
            "primary_final": final_primary_history_s,
            "secondary_final": final_secondary_history_s,
        },
        "checks": checks,
        "passed": all(checks.values()),
        "non_claims": [
            "no_universal_health_score",
            "no_distributed_sqlite_claim",
            "no_external_benchmark_claim",
            "no_answer_generation_claim",
            "no_learned_retrieval_controller",
            "pruning_is_not_mandatory_permanent_deletion",
            "retrieval_quality_is_not_governance_authority",
            "confidence_is_not_permission",
        ],
    }
    report["evidence_digest"] = _digest(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-memory-revision", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    report = run_scenario(args.agent_memory_revision)
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not report["passed"]:
        failed = [name for name, passed in report["checks"].items() if not passed]
        raise SystemExit(f"RC cognitive-memory scenario failed: {failed}")


if __name__ == "__main__":
    main()
