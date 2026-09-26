"""System-neutral Agent Memory Gauntlet execution profiles (#558).

These profiles are orchestration/conformance workloads, not claims of independent memory
quality. They exist to prove that different systems can traverse one public Gauntlet
contract while benchmark-native semantics and evidence provenance remain explicit.
"""

from __future__ import annotations

from copy import deepcopy

ORCHESTRATION_PROBE_PROFILE_ID = "gauntlet-orchestration-retrieval-probe-v1"

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
                "destructive reset is permitted only for a disposable-instance isolation claim",
            ],
            "authority_effect": "none",
        },
        "dimensions": ("retrieval", "efficiency", "evaluator_integrity", "reproducibility"),
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
    "list_gauntlet_profiles",
    "get_gauntlet_profile",
]
