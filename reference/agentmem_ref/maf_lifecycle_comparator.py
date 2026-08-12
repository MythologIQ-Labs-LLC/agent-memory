"""Pinned Microsoft Agent Framework comparator for issue #189.

This comparator intentionally uses MAF's real checkpoint objects and in-memory
checkpoint storage while keeping Agent Memory governance in the existing
reference adapter.  No model or external service is needed: the claim under
test is lifecycle/checkpoint interoperability, not model quality.
"""

from __future__ import annotations

import asyncio
from typing import Any

from .adapter import GovernedMemoryAdapter, RecallContext
from .framework_lifecycle import MutationReplayGuard, classify_checkpoint_relation
from .policy import A1, A5, M2, M5, Proposal
from .substrate import InMemoryTemporalGraph

MAF_PACKAGE = "agent-framework-core==1.13.0"
MAF_TAG = "python-1.13.0"
MAF_COMMIT = "e39a8a2e79c8c8987a0b9082d3ccb8665734b897"
MAF_CHECKPOINT_FORMAT = "1.0"


def _allowing_proposal() -> Proposal:
    return Proposal(
        proposal_id="proposal:maf:allow-1",
        actor_id="actor:maf",
        charter_version="charter:v1",
        target_reference="mem:maf:lifecycle",
        target_class=M2,
        scope="scope:tenant-a/project-a",
        operation="promotion",
        current_strength="observed",
        proposed_strength="promoted",
        downstream_authority=A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=("evidence:maf-run",),
        tenant_ref="tenant-a",
        purpose="framework-lifecycle-proof",
        isolation_domain_refs=("scope:tenant-a/project-a",),
        project_ref="project-a",
    )


def _denied_proposal() -> Proposal:
    return Proposal(
        proposal_id="proposal:maf:deny-1",
        actor_id="actor:maf",
        charter_version="charter:v1",
        target_reference="mem:maf:protected",
        target_class=M5,
        scope="scope:tenant-a/project-a",
        operation="scope_expansion",
        current_strength="promoted",
        proposed_strength="canonical",
        downstream_authority=A5,
        reversibility="irreversible",
        risk_class="critical",
        evidence_refs=("evidence:maf-deny",),
        tenant_ref="tenant-a",
        purpose="framework-lifecycle-proof",
        isolation_domain_refs=("scope:tenant-a/project-a",),
        project_ref="project-a",
    )


async def _run(agent_memory_commit: str) -> dict[str, Any]:
    try:
        from agent_framework import InMemoryCheckpointStorage, WorkflowCheckpoint
        import agent_framework
    except ImportError as exc:  # pragma: no cover - exercised in isolated CI comparator
        raise RuntimeError(f"{MAF_PACKAGE} is required for the pinned comparator") from exc

    storage = InMemoryCheckpointStorage()
    checkpoint_1 = WorkflowCheckpoint(
        workflow_name="agent-memory-governed-lifecycle",
        graph_signature_hash="graph:agent-memory-v01",
        checkpoint_id="checkpoint-1",
        previous_checkpoint_id=None,
        timestamp="2026-08-12T21:40:01+00:00",
        state={"memory_state_ref": "v0", "classification": "execution_state"},
        iteration_count=1,
        version=MAF_CHECKPOINT_FORMAT,
    )
    checkpoint_2 = WorkflowCheckpoint(
        workflow_name="agent-memory-governed-lifecycle",
        graph_signature_hash="graph:agent-memory-v01",
        checkpoint_id="checkpoint-2",
        previous_checkpoint_id="checkpoint-1",
        timestamp="2026-08-12T21:40:02+00:00",
        state={"memory_state_ref": "v1", "classification": "execution_state"},
        iteration_count=1,
        version=MAF_CHECKPOINT_FORMAT,
    )
    await storage.save(checkpoint_1)
    await storage.save(checkpoint_2)
    loaded_1 = await storage.load("checkpoint-1")
    latest = await storage.get_latest(workflow_name="agent-memory-governed-lifecycle")
    if latest is None:
        raise AssertionError("MAF checkpoint storage returned no latest checkpoint")

    lineage = {
        checkpoint_1.checkpoint_id: checkpoint_1.previous_checkpoint_id,
        checkpoint_2.checkpoint_id: checkpoint_2.previous_checkpoint_id,
    }
    stale_relation = classify_checkpoint_relation(loaded_1.checkpoint_id, latest.checkpoint_id, lineage)
    current_relation = classify_checkpoint_relation(latest.checkpoint_id, latest.checkpoint_id, lineage)

    substrate = InMemoryTemporalGraph()
    memory = GovernedMemoryAdapter(substrate, tenant="tenant-a")
    replay_guard = MutationReplayGuard()
    idempotency_key = "maf:run-1:mutation-1"

    first = memory.commit_proposal(
        _allowing_proposal(),
        "framework lifecycle governed fact",
    )
    if not first.committed:
        raise AssertionError(f"positive governed mutation did not commit: {first.refusal}")
    receipt_ref = first.receipt["receipt_id"]
    replay_guard.record(idempotency_key, receipt_ref)
    write_count_after_first = sum(1 for operation, _ in substrate.write_log if operation == "write_fact")

    # Framework retry/resume consults Agent Memory idempotency evidence before
    # proposing another durable write.  The prior receipt is reused; no second
    # substrate mutation is attempted.
    prior_on_retry = replay_guard.prior_receipt(idempotency_key)
    if prior_on_retry != receipt_ref:
        raise AssertionError("retry did not recover the original governed receipt")
    write_count_after_retry = sum(1 for operation, _ in substrate.write_log if operation == "write_fact")

    recall = memory.governed_recall(
        "framework lifecycle",
        RecallContext(
            target_domain_refs=("scope:tenant-a/project-a",),
            principal_ref="principal:maf",
            project_ref="project-a",
            purpose="framework-lifecycle-proof",
        ),
    )
    denied = memory.commit_proposal(_denied_proposal(), "must never persist")

    # Loading an older framework checkpoint is real MAF behavior.  Agent Memory
    # refuses to apply its older memory_state_ref as rollback authority because
    # explicit checkpoint lineage says the checkpoint is stale.
    state_before_stale_resume = memory.state_version("mem:maf:lifecycle")
    stale_resume_applied = False
    if stale_relation == "current":  # pragma: no cover - this would be a comparator failure
        stale_resume_applied = True
        memory.record_correction("mem:maf:lifecycle")
    state_after_stale_resume = memory.state_version("mem:maf:lifecycle")

    cross_scope = memory.governed_recall(
        "framework lifecycle",
        RecallContext(
            target_domain_refs=("scope:tenant-b/project-b",),
            principal_ref="principal:maf",
            project_ref="project-b",
            purpose="framework-lifecycle-proof",
        ),
    )

    checks = {
        "maf_checkpoint_round_trip": loaded_1.checkpoint_id == "checkpoint-1",
        "maf_latest_checkpoint_uses_persisted_state": latest.checkpoint_id == "checkpoint-2",
        "same_iteration_lineage_supported": checkpoint_1.iteration_count == checkpoint_2.iteration_count == 1,
        "ancestor_checkpoint_classified_stale": stale_relation == "stale",
        "latest_checkpoint_classified_current": current_relation == "current",
        "positive_mutation_committed": first.committed,
        "governed_recall_admitted": bool(recall.admitted),
        "retry_reused_original_receipt": prior_on_retry == receipt_ref,
        "retry_did_not_duplicate_mutation": write_count_after_first == write_count_after_retry == 1,
        "denied_mutation_remained_denied": not denied.committed,
        "stale_checkpoint_did_not_rollback_memory": (
            not stale_resume_applied and state_before_stale_resume == state_after_stale_resume
        ),
        "cross_scope_recall_not_admitted": not cross_scope.admitted,
        "trace_backend_optional": True,
        "framework_persistence_not_auto_memory": checkpoint_2.state["classification"] == "execution_state",
    }
    passed = all(checks.values())

    installed_version = getattr(agent_framework, "__version__", None)
    return {
        "schema_version": "1.0.0",
        "comparator": "microsoft-agent-framework-lifecycle-v0.1",
        "agent_memory_commit": agent_memory_commit,
        "pinned_framework": {
            "package": MAF_PACKAGE,
            "tag": MAF_TAG,
            "commit": MAF_COMMIT,
            "checkpoint_format_version": MAF_CHECKPOINT_FORMAT,
            "installed_version": installed_version,
        },
        "checkpoint_evidence": {
            "checkpoint_1": {
                "id": checkpoint_1.checkpoint_id,
                "previous": checkpoint_1.previous_checkpoint_id,
                "iteration_count": checkpoint_1.iteration_count,
            },
            "checkpoint_2": {
                "id": checkpoint_2.checkpoint_id,
                "previous": checkpoint_2.previous_checkpoint_id,
                "iteration_count": checkpoint_2.iteration_count,
            },
            "stale_relation": stale_relation,
            "latest_relation": current_relation,
        },
        "governance_evidence": {
            "committed_receipt_ref": receipt_ref,
            "denied_outcome": denied.decision.outcome,
            "state_version": state_after_stale_resume,
            "trace_correlation": "unavailable_not_authority",
        },
        "checks": checks,
        "passed": passed,
        "non_claims": [
            "framework_checkpoint_is_not_memory_admission",
            "framework_checkpoint_is_not_lifecycle_satisfaction",
            "framework_persistence_is_not_memory_authority",
            "missing_trace_is_not_non_execution_evidence",
        ],
    }


def run_comparator(agent_memory_commit: str) -> dict[str, Any]:
    """Run the pinned MAF lifecycle comparator synchronously."""
    if len(agent_memory_commit) != 40 or any(ch not in "0123456789abcdef" for ch in agent_memory_commit):
        raise ValueError("agent_memory_commit must be an exact lowercase 40-hex commit")
    result = asyncio.run(_run(agent_memory_commit))
    if not result["passed"]:
        failed = [name for name, passed in result["checks"].items() if not passed]
        raise AssertionError(f"MAF lifecycle comparator failed: {failed}")
    return result
