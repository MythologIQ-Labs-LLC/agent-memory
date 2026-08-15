from __future__ import annotations

import json

import pytest

from agentmem_ref import policy
from agentmem_ref.adapter import RecallContext
from agentmem_ref.restart_runtime import (
    CapabilityBinding,
    RestartSafeRuntime,
    RuntimeProfile,
    RuntimeRecoveryError,
)
from agentmem_ref.visibility import VisibilityOperation, VisibilityTracker


COMMIT = "85970029b6ada43ef0844c5f58b504a8c642d5e0"


def _binding(*, component_version: str = "1.0.0") -> CapabilityBinding:
    return CapabilityBinding(
        component_id="reference-governed-memory",
        component_version=component_version,
        capability_id="governed-memory-core",
        capability_version="1.0.0",
        maturity="reference_qualified",
        evidence_ref="evidence:reference-runtime-core-v1",
    )


def _profile(*, profile_version: str = "1.0.0") -> RuntimeProfile:
    return RuntimeProfile(
        runtime_version="0.1.0-reference",
        profile_id="reference-project-memory",
        profile_version=profile_version,
        bindings=(_binding(),),
    )


def _proposal(
    proposal_id: str,
    *,
    operation: str,
    state_snapshot: str = "",
    review_satisfied: bool = False,
    approval_refs: tuple[str, ...] = (),
    project_ref: str = "project-alpha",
) -> policy.Proposal:
    return policy.Proposal(
        proposal_id=proposal_id,
        actor_id="agent:test",
        charter_version="charter-v1",
        target_reference="memory:release-branch",
        target_class=policy.M2,
        scope="tenant-acme",
        operation=operation,
        current_strength="candidate",
        proposed_strength="retained",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="low",
        evidence_refs=(f"evidence:{proposal_id}",),
        review_satisfied=review_satisfied,
        approval_refs=approval_refs,
        state_snapshot=state_snapshot,
        tenant_ref="tenant-acme",
        isolation_domain_refs=("tenant-acme", "project-alpha"),
        required_isolation_domain_refs=("project-alpha",),
        project_ref=project_ref,
        purpose="release-planning",
    )


def _context(*, project_ref: str = "project-alpha") -> RecallContext:
    return RecallContext(
        target_domain_refs=("tenant-acme", "project-alpha"),
        principal_ref="agent:test",
        project_ref=project_ref,
        purpose="release-planning",
    )


def test_release_branch_survives_restart_with_currentness_scope_and_stale_replay(tmp_path):
    profile = _profile()

    session_a = RestartSafeRuntime.create(tmp_path, tenant="tenant-acme", profile=profile)
    learned = session_a.commit_proposal(
        _proposal("proposal-release", operation="promotion"),
        "release_branch = release",
    )
    assert learned.committed is True
    release_uuid = learned.fact_uuid
    assert release_uuid is not None
    assert session_a.adapter.state_version("memory:release-branch") == 1

    # Session B has no process-local state from A. Durable recovery must be
    # sufficient to interpret and admit the retained memory.
    session_b = RestartSafeRuntime.recover(tmp_path, profile=profile)
    recalled = session_b.adapter.governed_recall("release_branch", _context())
    assert recalled.admitted == [release_uuid]

    correction = _proposal(
        "proposal-main",
        operation="correction",
        state_snapshot="v1",
        review_satisfied=True,
        approval_refs=("approval:release-branch-main",),
    )
    corrected = session_b.commit_proposal(correction, "release_branch = main")
    assert corrected.committed is True
    main_uuid = corrected.fact_uuid
    assert main_uuid is not None and main_uuid != release_uuid
    assert session_b.adapter.state_version("memory:release-branch") == 2

    # Replaying the previously valid correction after its state boundary has
    # moved must fail after the durable mutation, not merely during one process.
    replay = session_b.commit_proposal(correction, "release_branch = main")
    assert replay.committed is False
    assert replay.refusal == "stale_authorization"

    session_c = RestartSafeRuntime.recover(tmp_path, profile=profile)
    current = session_c.adapter.governed_recall("release_branch", _context())
    assert current.admitted == [main_uuid]
    assert current.refusals[release_uuid] == "superseded_not_current"
    assert session_c.adapter.current_fact_uuid("memory:release-branch") == main_uuid
    assert session_c.adapter.state_version("memory:release-branch") == 2

    wrong_project = session_c.adapter.governed_recall(
        "release_branch",
        _context(project_ref="project-beta"),
    )
    assert main_uuid not in wrong_project.admitted
    assert wrong_project.refusals[main_uuid] == "project_scope_mismatch"

    # Session D proves the same current/superseded and stale-state posture after
    # another full recovery boundary.
    session_d = RestartSafeRuntime.recover(tmp_path, profile=profile)
    after_restart = session_d.adapter.governed_recall("release_branch", _context())
    assert after_restart.admitted == [main_uuid]
    assert after_restart.refusals[release_uuid] == "superseded_not_current"
    replay_after_restart = session_d.commit_proposal(correction, "release_branch = main")
    assert replay_after_restart.committed is False
    assert replay_after_restart.refusal == "stale_authorization"


def test_pending_visibility_obligations_survive_restart_without_fake_quiescence(tmp_path):
    profile = _profile()
    runtime = RestartSafeRuntime.create(tmp_path, tenant="tenant-acme", profile=profile)

    operation = VisibilityOperation(
        operation_id="visibility:release-main",
        memory_id="memory:release-branch",
        memory_version=2,
        operation_type="correction",
        runtime_version=profile.runtime_version,
        profile_version=profile.profile_version,
        agent_memory_commit=COMMIT,
        required_projection_ids=("search-index",),
        component_versions=("reference-governed-memory@1.0.0",),
        capability_versions=("governed-memory-core@1.0.0",),
    )
    tracker = VisibilityTracker(operation)
    tracker.policy_decided()
    tracker.canonical_committed()
    tracker.projection_refresh_started("search-index")
    before = tracker.evaluate()
    assert before["settled"] is False
    assert before["quiescent"] is False

    runtime.persist_visibility_snapshot(operation.operation_id, tracker.snapshot_for_restart())
    recovered = RestartSafeRuntime.recover(tmp_path, profile=profile)
    restored_snapshot = recovered.visibility_snapshots[operation.operation_id]
    restored = VisibilityTracker.restore_after_restart(restored_snapshot)
    after = restored.evaluate()
    assert after["settled"] is False
    assert after["quiescent"] is False
    assert "projection:search-index" in after["pending_required_obligations"]
    assert recovered.recovery_evidence is not None
    assert recovered.recovery_evidence.recovered_visibility_operations == (operation.operation_id,)


def test_corrupt_or_torn_checkpoint_fails_closed(tmp_path):
    profile = _profile()
    runtime = RestartSafeRuntime.create(tmp_path, tenant="tenant-acme", profile=profile)
    runtime.commit_proposal(_proposal("proposal-release", operation="promotion"), "release_branch = release")

    governance_path = tmp_path / "governance.json"
    governance = json.loads(governance_path.read_text(encoding="utf-8"))
    governance["tenant"] = "attacker-tenant"
    governance_path.write_text(json.dumps(governance), encoding="utf-8")

    with pytest.raises(RuntimeRecoveryError, match="governance checkpoint digest mismatch"):
        RestartSafeRuntime.recover(tmp_path, profile=profile)


def test_missing_governance_state_fails_closed(tmp_path):
    profile = _profile()
    RestartSafeRuntime.create(tmp_path, tenant="tenant-acme", profile=profile)
    (tmp_path / "governance.json").unlink()

    with pytest.raises(RuntimeRecoveryError, match="required runtime state missing"):
        RestartSafeRuntime.recover(tmp_path, profile=profile)


def test_component_interpretation_cannot_silently_change_after_restart(tmp_path):
    profile = _profile()
    RestartSafeRuntime.create(tmp_path, tenant="tenant-acme", profile=profile)

    upgraded_without_compatibility_evidence = _binding(component_version="2.0.0")
    with pytest.raises(RuntimeRecoveryError, match="interpretation changed after restart"):
        RestartSafeRuntime.recover(
            tmp_path,
            profile=profile,
            available_bindings=(upgraded_without_compatibility_evidence,),
        )

    changed_profile = _profile(profile_version="2.0.0")
    with pytest.raises(RuntimeRecoveryError, match="profile/component interpretation changed"):
        RestartSafeRuntime.recover(tmp_path, profile=changed_profile)


def test_recovery_preserves_identifier_progress_to_avoid_object_collision(tmp_path):
    profile = _profile()
    runtime = RestartSafeRuntime.create(tmp_path, tenant="tenant-acme", profile=profile)
    first = runtime.commit_proposal(
        _proposal("proposal-first", operation="promotion"),
        "release_branch = release",
    )
    first_uuid = first.fact_uuid
    assert first_uuid is not None

    recovered = RestartSafeRuntime.recover(tmp_path, profile=profile)
    second = recovered.commit_proposal(
        policy.Proposal(
            **{
                **_proposal("proposal-second", operation="promotion").__dict__,
                "target_reference": "memory:deploy-branch",
            }
        ),
        "deploy_branch = deploy",
    )
    assert second.committed is True
    assert second.fact_uuid is not None
    assert second.fact_uuid != first_uuid
