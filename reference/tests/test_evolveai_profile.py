from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agentmem_ref.evolveai_profile import (
    EVOLVEAI_COMMIT,
    EvolveAIProfileError,
    assert_scope_binding,
    build_profile_report,
    build_scope_binding,
    profile_digest,
    validate_profile,
)

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "reference/fixtures/component-capabilities/evolveai.example.json"


def profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def capability(value: dict, capability_id: str) -> dict:
    return next(item for item in value["capabilities"] if item["capability_id"] == capability_id)


def test_current_profile_is_valid_and_bounded() -> None:
    value = profile()
    component = validate_profile(value)
    assert component.component_version == EVOLVEAI_COMMIT
    report = build_profile_report(value, agent_memory_commit="a" * 40)
    assert all(report["invariants"].values())
    assert report["maturity_counts"]["reference_qualified"] == 4
    assert report["maturity_counts"]["declared"] == 1
    assert report["maturity_counts"]["implemented"] == 1


def test_old_pre_delete_fix_pin_is_rejected() -> None:
    value = profile()
    value["component_version"] = "7cd42412ceed2ab638249a1517b2a6dac46f1312"
    with pytest.raises(EvolveAIProfileError, match="repaired commit"):
        validate_profile(value)


def test_graphrag_cannot_hitchhike_on_graph_and_vector_evidence() -> None:
    value = profile()
    graph_rag = capability(value, "graph_augmented_context_assembly")
    graph_rag["maturity"] = "evidence_proven"
    graph_rag["enabled"] = True
    with pytest.raises(EvolveAIProfileError):
        validate_profile(value)


def test_mock_vector_boundary_cannot_be_removed() -> None:
    value = profile()
    vector = capability(value, "vector_candidate_retrieval")
    vector["limitations"] = ["candidate_ranking_does_not_create_recall_admission"]
    with pytest.raises(EvolveAIProfileError, match="mock-engine"):
        validate_profile(value)


def test_shadow_native_block_cannot_gain_agent_memory_authority() -> None:
    value = profile()
    shadow = capability(value, "negative_failure_memory")
    shadow["authority_effect"] = "none"
    with pytest.raises(EvolveAIProfileError, match="proposal_only"):
        validate_profile(value)


def test_native_delete_cannot_be_reframed_as_transitive_forgetting() -> None:
    value = profile()
    deletion = capability(value, "audited_deletion")
    deletion["limitations"] = [
        "qualified_claim_is_native_L3_live_removal_plus_reconstructable_delete_history"
    ]
    with pytest.raises(EvolveAIProfileError, match="transitive"):
        validate_profile(value)


def test_scope_binding_rejects_foreign_scope() -> None:
    digest = profile_digest(profile())
    binding = build_scope_binding(
        agent_memory_scope="qualification://tenant-a/project-evolveai",
        provider_scope="evolveai://qualification-store",
        profile_sha256=digest,
    )
    with pytest.raises(EvolveAIProfileError, match="requested Agent Memory scope"):
        assert_scope_binding(
            binding,
            requested_scope="qualification://tenant-b/project-evolveai",
            profile_sha256=digest,
        )


def test_scope_binding_rejects_stale_component_version() -> None:
    digest = profile_digest(profile())
    binding = build_scope_binding(
        agent_memory_scope="qualification://tenant-a/project-evolveai",
        provider_scope="evolveai://qualification-store",
        profile_sha256=digest,
    )
    with pytest.raises(EvolveAIProfileError, match="stale for this component version"):
        assert_scope_binding(
            binding,
            requested_scope=binding["agent_memory_scope"],
            profile_sha256=digest,
            component_version="0" * 40,
        )


def test_scope_binding_rejects_stale_profile_digest() -> None:
    digest = profile_digest(profile())
    binding = build_scope_binding(
        agent_memory_scope="qualification://tenant-a/project-evolveai",
        provider_scope="evolveai://qualification-store",
        profile_sha256=digest,
    )
    with pytest.raises(EvolveAIProfileError, match="stale for this profile digest"):
        assert_scope_binding(
            binding,
            requested_scope=binding["agent_memory_scope"],
            profile_sha256="sha256:" + "0" * 64,
        )


def test_profile_edit_changes_digest_and_invalidates_old_binding() -> None:
    original = profile()
    old_digest = profile_digest(original)
    binding = build_scope_binding(
        agent_memory_scope="qualification://tenant-a/project-evolveai",
        provider_scope="evolveai://qualification-store",
        profile_sha256=old_digest,
    )
    edited = copy.deepcopy(original)
    capability(edited, "temporal_graph")["limitations"].append("material_profile_change")
    new_digest = profile_digest(edited)
    assert new_digest != old_digest
    with pytest.raises(EvolveAIProfileError, match="stale for this profile digest"):
        assert_scope_binding(
            binding,
            requested_scope=binding["agent_memory_scope"],
            profile_sha256=new_digest,
        )
