"""Behavioral transformation/authority-laundering proof for issue #202."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import policy
from .adapter import Clock, GovernedMemoryAdapter
from .substrate import InMemoryTemporalGraph
from .transformation_evidence import normalize_transformation_evidence, reevaluate_source_currentness

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures" / "authority-laundering.json"
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def _source(*, state: str = "current", evidence_class: str = "ordinary") -> dict[str, Any]:
    return {
        "source_ref": "memory:untrusted-origin",
        "evidence_refs": ["fixture://untrusted-origin"],
        "scope_ref": "scope:tenant-a/project-a",
        "tenant_ref": "tenant-a",
        "project_ref": "project-a",
        "state": state,
        "evidence_class": evidence_class,
    }


def _summary(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "transformation_id": "transform:summary:1",
        "transformation_type": "summary",
        "mode": "probabilistic",
        "status": "complete",
        "transformer_ref": "trusted-summary-service",
        "transformer_version": "v1",
        "transformer_trust_evidence_refs": ["evidence:transformer-reviewed"],
        "sources": [_source()],
        "derived_ref": "memory:derived-summary:1",
        "derived_evidence_ref": "evidence:summary-transform",
        "derived_evidence_digest": DIGEST_A,
        "derived_scope_ref": "scope:tenant-a/project-a",
        "derived_tenant_ref": "tenant-a",
        "derived_project_ref": "project-a",
        "scope_relation": "preserved",
        "created_at": "2026-08-12T23:15:00Z",
        "uncertainty": {
            "signal_semantics": "summary_fidelity_confidence",
            "estimator_ref": "estimator:trusted-summary-service",
            "estimator_version": "v1",
            "signal_value": 0.99,
            "uncertainty_summary": "High transformer confidence is evidence about the derived output, not source authority.",
        },
        # Hostile/overreaching transformer claims. The normalizer must ignore them.
        "pama_outcome": "allow",
        "permitted_actions": ["crystallize_transformed_claim"],
        "lifecycle_state": "crystallized",
        "certification_status": "certified",
        "memory_authority": "owner",
        "raw_source_content": "sensitive source body must not be copied",
        "hidden_reasoning": "private transformer reasoning must not be copied",
    }
    value.update(overrides)
    return value


def _pama_high_confidence_case(record: dict[str, Any]) -> dict[str, Any]:
    substrate = InMemoryTemporalGraph()
    adapter = GovernedMemoryAdapter(substrate, tenant="tenant-a", clock=Clock())
    proposal = policy.Proposal(
        proposal_id="proposal:transformed-summary:crystallize",
        actor_id="transformer:trusted-summary-service",
        charter_version="charter:transformation-v1",
        target_reference=record["derived"]["derived_ref"],
        target_class=policy.M4,
        scope=record["scope"]["scope_ref"],
        operation="promotion",
        current_strength="observed",
        proposed_strength="crystallized",
        downstream_authority=policy.A1,
        reversibility="reversible",
        risk_class="high",
        evidence_refs=(record["derived"]["derived_evidence_ref"], *record["lineage"]["original_source_refs"]),
        estimator_refs=("estimator:trusted-summary-service",),
        estimator_versions=("v1",),
        confidence=0.99,
        tenant_ref="tenant-a",
        project_ref="project-a",
        purpose="authority-laundering-harness",
    )
    result = adapter.commit_proposal(proposal, "derived transformed claim")
    writes = [entry for entry in substrate.write_log if entry[0] == "write_fact"]
    checks = {
        "high_confidence_not_committed": not result.committed and not writes,
        "promotion_remains_prohibited": "promotion" in result.decision.prohibited_actions,
        "review_or_verification_still_required": result.decision.outcome in {
            policy.REQUIRE_REVIEW,
            policy.REQUIRE_EXTERNAL_VERIFICATION,
            policy.BLOCK,
        },
        "source_lineage_reaches_pama_evidence": "memory:untrusted-origin" in result.pama_decision["basis"]["evidence_refs"],
    }
    return {"passed": all(checks.values()), "checks": checks, "outcome": result.decision.outcome}


def run_transformation_laundering_harness() -> dict[str, Any]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    expected = fixture["expected_behavior"]

    first = normalize_transformation_evidence(_summary())

    second = normalize_transformation_evidence(
        {
            "transformation_id": "transform:extraction:2",
            "transformation_type": "extraction",
            "mode": "deterministic",
            "status": "complete",
            "transformer_ref": "trusted-extraction-service",
            "transformer_version": "v2",
            "sources": [
                {
                    "source_ref": first["derived"]["derived_ref"],
                    "evidence_refs": [first["derived"]["derived_evidence_ref"]],
                    "scope_ref": first["scope"]["scope_ref"],
                    "tenant_ref": "tenant-a",
                    "project_ref": "project-a",
                    "state": "current",
                    "evidence_class": "ordinary",
                }
            ],
            "derived_ref": "memory:derived-extraction:2",
            "derived_evidence_ref": "evidence:derived-extraction:2",
            "derived_evidence_digest": DIGEST_B,
            "derived_scope_ref": "scope:tenant-a/project-a",
            "derived_tenant_ref": "tenant-a",
            "derived_project_ref": "project-a",
            "scope_relation": "preserved",
            "created_at": "2026-08-12T23:16:00Z",
        },
        parent_records=(first,),
    )

    revoked = reevaluate_source_currentness(first, {"memory:untrusted-origin": "revoked"})
    tombstoned = reevaluate_source_currentness(first, {"memory:untrusted-origin": "tombstoned"})

    widened = normalize_transformation_evidence(
        _summary(
            transformation_id="transform:summary:widened",
            derived_ref="memory:derived-summary:widened",
            derived_tenant_ref="tenant-b",
            derived_project_ref="project-b",
            derived_scope_ref="scope:tenant-b/project-b",
        )
    )

    adversarial = normalize_transformation_evidence(
        _summary(
            transformation_id="transform:summary:adversarial",
            sources=[_source(evidence_class="adversarial")],
            derived_ref="memory:derived-summary:adversarial",
        )
    )

    partial = normalize_transformation_evidence(
        _summary(
            transformation_id="transform:summary:partial",
            status="partial",
            derived_ref="memory:derived-summary:partial",
        )
    )

    pama_case = _pama_high_confidence_case(first)
    rendered = repr(first)
    hostile_fields = (
        "pama_outcome",
        "permitted_actions",
        "lifecycle_state",
        "certification_status",
        "memory_authority",
        "raw_source_content",
        "hidden_reasoning",
    )

    checks = {
        "fixture_origin_preserved": expected["origin_preserved"] is True,
        "fixture_transformation_grants_no_authority": expected["transformation_grants_authority"] is False,
        "fixture_durable_promotion_forbidden": expected["durable_promotion_allowed"] is False,
        "direct_origin_preserved": first["lineage"]["original_source_refs"] == ["memory:untrusted-origin"],
        "transformer_trust_not_source_trust": first["interpretation"]["transformer_trust_is_source_trust"] is False,
        "transformation_authority_none": first["interpretation"]["transformation_authority_effect"] == "none",
        "confidence_authority_none": first["interpretation"]["derived_confidence_authority"] == "none",
        "certification_none": first["interpretation"]["certification_claim"] == "none",
        "hostile_authority_fields_discarded": all(field not in first for field in hostile_fields),
        "raw_content_not_copied": "sensitive source body must not be copied" not in rendered,
        "hidden_reasoning_not_copied": "private transformer reasoning must not be copied" not in rendered,
        "multi_hop_original_lineage_preserved": "memory:untrusted-origin" in second["lineage"]["original_source_refs"],
        "multi_hop_parent_preserved": first["transformation_id"] in second["lineage"]["parent_transformation_refs"],
        "revocation_requires_revalidation": revoked["applicability"]["status"] == "revalidation_required",
        "revocation_reason_preserved": any(reason.startswith("source_revoked:") for reason in revoked["source_currentness"]["reasons"]),
        "tombstone_distinct_from_revocation": any(reason.startswith("source_tombstoned:") for reason in tombstoned["source_currentness"]["reasons"]),
        "scope_widening_invalid": widened["scope"]["binding_status"] == "mismatch" and widened["applicability"]["status"] == "invalid",
        "adversarial_evidence_not_neutralized": adversarial["derived"]["evidence_character"] == "negative_or_adversarial",
        "partial_transform_not_current": partial["applicability"]["status"] == "incomplete",
        "high_confidence_cannot_self_crystallize": pama_case["passed"],
    }

    return {
        "case_id": "authority-laundering-through-transformation",
        "passed": all(checks.values()),
        "checks": checks,
        "observed": {
            "first_transformation_id": first["transformation_id"],
            "first_identity_digest": first["identity_digest"],
            "second_original_source_refs": second["lineage"]["original_source_refs"],
            "revoked_applicability": revoked["applicability"],
            "tombstoned_currentness": tombstoned["source_currentness"],
            "widened_scope": widened["scope"],
            "pama_outcome": pama_case["outcome"],
        },
    }
