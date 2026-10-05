"""System-neutral Agent Memory Gauntlet execution profiles.

Profiles are explicit qualification workloads. Their provenance class is part of the
public evidence semantics: an orchestration probe or Gauntlet-native gap suite must never
masquerade as independent external benchmark evidence.

Every profile declares ``benchmark_integration``: either ``None`` for a Gauntlet-native
suite/probe, or the id of a committed benchmark integration descriptor whose
``gauntlet.relationship`` is ``bound_profile``. ``registry.validate_registry_relationships``
enforces that the binding is mutual and that ``kind`` equals the descriptor provenance
class, so registration can never upgrade evidence class.
"""

from __future__ import annotations

from copy import deepcopy

ORCHESTRATION_PROBE_PROFILE_ID = "gauntlet-orchestration-retrieval-probe-v1"
GOVERNANCE_ALPHA_PROFILE_ID = "governance-isolation-deletion-alpha-v1"
DURABILITY_RECOVERY_PROFILE_ID = "durability-recovery-alpha-v1"
GOLDEN_KEYED_RETRIEVAL_PROFILE_ID = "golden-keyed-retrieval-v1"

_PROFILES = (
    {
        "profile_id": ORCHESTRATION_PROBE_PROFILE_ID,
        "kind": "baseline_or_probe",
        "benchmark_integration": None,
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
        "benchmark_integration": None,
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
    {
        "profile_id": DURABILITY_RECOVERY_PROFILE_ID,
        "kind": "gauntlet_native_gap",
        "benchmark_integration": None,
        "description": (
            "Claim-driven durability/recovery alpha for public reopen recovery, durable "
            "correction/deletion, deterministic recovered observation, scope isolation, and "
            "truthful checkpoint capability posture. Behavioral outcome and evidence "
            "sufficiency are reported separately."
        ),
        "runner": "agentmem_ref.evaluation.gauntlet_durability:run_durability_recovery_alpha",
        "operations": (
            "describe",
            "reset",
            "remember",
            "recall",
            "correct",
            "forget",
            "history",
            "recover",
            "checkpoint",
        ),
        "destructive_operations": {
            "reset": None,
            "forget": "durable_deletion",
        },
        "requirements": {
            "contract_family": "agent-memory-gauntlet-profile-requirements",
            "contract_version": "0.1.0",
            "profile_id": DURABILITY_RECOVERY_PROFILE_ID,
            "requires": {
                "describe": ["native", "mapped", "derived"],
                "reset": ["native", "mapped", "derived"],
                "remember": ["native", "mapped", "derived"],
                "recall": ["native", "mapped", "derived"],
                "recover": ["native", "mapped"],
            },
            "optional": {
                "correct": ["native", "mapped", "derived"],
                "forget": ["native", "mapped", "derived"],
                "history": ["native", "mapped", "derived"],
                "checkpoint": ["native", "mapped", "derived"],
                "restart_recovery": ["native", "mapped", "derived"],
                "durable_deletion": ["native", "mapped", "derived"],
                "durable_correction": ["native", "mapped", "derived"],
                "deterministic_recovery": ["native", "mapped", "derived"],
                "scope_isolation": ["native", "mapped", "derived"],
            },
            "notes": [
                "Gauntlet-native field-gap evidence; not independent external validation",
                "recover qualifies the contestant's declared reopen/recovery surface, not an implied crash/kill guarantee",
                "unsupported checkpoint remains not_applicable and must not be emulated through private implementation access",
                "forget is destructive only when durable_deletion is positively claimed",
                "case behavioral outcome and evaluator evidence sufficiency remain separate",
            ],
            "authority_effect": "none",
        },
        "dimensions": ("governance", "evaluator_integrity", "reproducibility"),
        "authority_effect": "none",
    },
    {
        "profile_id": GOLDEN_KEYED_RETRIEVAL_PROFILE_ID,
        "kind": "baseline_or_probe",
        "benchmark_integration": GOLDEN_KEYED_RETRIEVAL_PROFILE_ID,
        "description": (
            "Benchmark-author golden path: a deliberately small keyed-retrieval benchmark "
            "bound to a committed benchmark integration descriptor and a frozen input file. "
            "It demonstrates exact input identity, native-result retention, descriptor-driven "
            "normalization, and evaluator-integrity controls. It is not an external efficacy "
            "benchmark."
        ),
        "runner": "agentmem_ref.evaluation.benchmark_golden_keyed_retrieval:run_golden_keyed_retrieval",
        "operations": ("describe", "reset", "remember", "recall"),
        "destructive_operations": {"reset": None},
        "requirements": {
            "contract_family": "agent-memory-gauntlet-profile-requirements",
            "contract_version": "0.1.0",
            "profile_id": GOLDEN_KEYED_RETRIEVAL_PROFILE_ID,
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
                "baseline_or_probe provenance; bound to benchmark integration golden-keyed-retrieval-v1",
                "frozen input identity is verified against the descriptor before any operation is issued",
                "destructive reset requires a disposable-instance isolation claim and explicit caller consent for non-fixtures",
            ],
            "authority_effect": "none",
        },
        "dimensions": ("retrieval", "evaluator_integrity", "reproducibility"),
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
    "DURABILITY_RECOVERY_PROFILE_ID",
    "GOLDEN_KEYED_RETRIEVAL_PROFILE_ID",
    "list_gauntlet_profiles",
    "get_gauntlet_profile",
]
