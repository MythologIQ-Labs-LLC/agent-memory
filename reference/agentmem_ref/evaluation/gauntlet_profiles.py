"""System-neutral Agent Memory Gauntlet execution profiles.

Profiles are explicit qualification workloads. Their provenance class is part of the
public evidence semantics: an orchestration probe or Gauntlet-native gap suite must never
masquerade as independent external benchmark evidence.
"""

from __future__ import annotations

from copy import deepcopy

ORCHESTRATION_PROBE_PROFILE_ID = "gauntlet-orchestration-retrieval-probe-v1"
GOVERNANCE_ALPHA_PROFILE_ID = "governance-isolation-deletion-alpha-v1"

_PROFILES = (
    {
        "profile_id": ORCHESTRATION_PROBE_PROFILE_ID,
        "kind": "baseline_or_probe",
        "description": (
            "Deterministic three-record retrieval probe used to qualify Gauntlet "
            "orchestration, adapter transport, evidence normalization, and failure attribution. "
            "It is not an external efficacy benchmark."
        ),
        "runner": "agentmem_ref.evaluation.gauntlet_probe:run_retrieval_probe",
        "operations": ("describe", "reset", "remember", "recall"),
        "destructive_operations": {"reset": None},
        "requirements": {
            "contract_family": "agent-memory-gauntlet-profile-requirements",
            "contract_version": "0.1.0",
            "profile_id": ORCHESTRATION_PROBE_PROFILE_ID,
            "requires": {
                "describe": ["native", "mapped", "derived"],
                "reset": ["native", "mapped", "derived"],
                "remember": ["native", "mapped", "derived"],
                "recall": ["native", "mapped", "derived"],
            },
            "optional": {
                "health": ["native", "mapped", "derived"],
            },
            "notes": [
                "baseline_or_probe provenance; no external efficacy claim",
                "destructive reset requires a disposable-instance isolation claim and explicit caller consent for non-fixtures",
            ],
            "authority_effect": "none",
        },
        "dimensions": ("retrieval", "efficiency", "evaluator_integrity", "reproducibility"),
        "authority_effect": "none",
    },
    {
        "profile_id": GOVERNANCE_ALPHA_PROFILE_ID,
        "kind": "gauntlet_native_gap",
        "description": (
            "Claim-driven synthetic Governance Gauntlet alpha for tenant/scope isolation, "
            "foreign-cardinality non-disclosure, deletion, and authority-laundering pressure. "
            "Unsupported optional governance capabilities remain unsupported rather than zero-score failures."
        ),
        "runner": "agentmem_ref.evaluation.gauntlet_governance:run_governance_alpha",
        "operations": ("describe", "reset", "remember", "recall", "forget"),
        "destructive_operations": {
            "reset": None,
            "forget": "deletion",
        },
        "requirements": {
            "contract_family": "agent-memory-gauntlet-profile-requirements",
            "contract_version": "0.1.0",
            "profile_id": GOVERNANCE_ALPHA_PROFILE_ID,
            "requires": {
                "describe": ["native", "mapped", "derived"],
                "reset": ["native", "mapped", "derived"],
                "remember": ["native", "mapped", "derived"],
                "recall": ["native", "mapped", "derived"],
            },
            "optional": {
                "forget": ["native", "mapped", "derived"],
                "tenant_isolation": ["native", "mapped", "derived"],
                "scope_isolation": ["native", "mapped", "derived"],
                "foreign_cardinality_non_disclosure": ["native", "mapped", "derived"],
                "deletion": ["native", "mapped", "derived"],
                "durable_deletion": ["native", "mapped", "derived"],
                "route_authority_isolation": ["native", "mapped", "derived"],
                "classifier_authority_isolation": ["native", "mapped", "derived"],
                "source_trust": ["native", "mapped", "derived"],
            },
            "notes": [
                "claim-driven governance profile; optional capability absence is not numeric failure",
                "synthetic benchmark-owned tenants/scopes only",
                "Gauntlet-native evidence is not independent external validation",
                "forget is destructive only when deletion is positively claimed",
            ],
            "authority_effect": "none",
        },
        "dimensions": ("governance", "evaluator_integrity", "reproducibility"),
        "authority_effect": "none",
    },
)


def list_gauntlet_profiles() -> list[dict]:
    """Return stable profile metadata sorted by profile id."""

    return [deepcopy(profile) for profile in sorted(_PROFILES, key=lambda item: item["profile_id"])]


def get_gauntlet_profile(profile_id: str) -> dict:
    """Return one registered Gauntlet execution profile or raise ``KeyError``."""

    for profile in _PROFILES:
        if profile["profile_id"] == profile_id:
            return deepcopy(profile)
    raise KeyError(profile_id)


__all__ = [
    "ORCHESTRATION_PROBE_PROFILE_ID",
    "GOVERNANCE_ALPHA_PROFILE_ID",
    "list_gauntlet_profiles",
    "get_gauntlet_profile",
]
