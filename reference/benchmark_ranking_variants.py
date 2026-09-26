"""Evaluated ranking variants for benchmark ablation (#538, ADR-039 proposed).

Evaluation tooling only. A variant replaces the three planner policy constants with a
documented alternative of ``PostAdmissionRankingPolicy`` for the duration of a benchmark
process. ``default`` leaves the shipped runtime policy untouched. Every report records
the variant used. Two variants exist only as reproduction checks: they must reproduce
frozen evidence exactly, which validates the harness before any comparison is read.
"""

from __future__ import annotations

import dataclasses
from typing import Any

VARIANTS: dict[str, dict[str, Any]] = {
    "default": {},
    # Shipped relevance (admitted-set BM25) with evaluated temporal alternatives.
    "unspecified_newer_first_among_ties": {"unspecified_intent_order": "newer_first_among_ties"},
    "universal_newer_first": {"temporal_regime": "universal_newer_first", "stable_fallback": "candidate_ref_asc"},
    # Token-overlap route score (policy 2.0 relevance), where relevance ties are common.
    "overlap_query_conditioned": {"lexical_relevance": "route_score"},
    "overlap_query_conditioned_ref_asc": {"lexical_relevance": "route_score", "stable_fallback": "candidate_ref_asc"},
    "overlap_unspecified_newer_first_among_ties": {
        "lexical_relevance": "route_score",
        "unspecified_intent_order": "newer_first_among_ties",
    },
    # Reproduction checks: must equal frozen f73b872 (no temporal stage, ascending id)
    # and 9c2ba70 (universal newer-first, ascending id) exactly.
    "reproduce_f73b872": {"lexical_relevance": "route_score", "temporal_regime": "none", "stable_fallback": "candidate_ref_asc"},
    "reproduce_9c2ba70": {
        "lexical_relevance": "route_score",
        "temporal_regime": "universal_newer_first",
        "stable_fallback": "candidate_ref_asc",
    },
}


def apply_ranking_variant(name: str) -> dict[str, Any]:
    """Install a variant into the planner policy constants; return the applied overrides."""

    if name not in VARIANTS:
        raise ValueError(f"unknown ranking variant {name!r}")
    overrides = VARIANTS[name]
    if overrides:
        from agentmem_ref.runtime import query_driven_recall, recall_control, runtime_composition

        for module, attribute in (
            (runtime_composition, "MULTI_ROUTE_RANKING_POLICY"),
            (query_driven_recall, "QUERY_DRIVEN_RANKING_POLICY"),
            (recall_control, "CONTROLLED_RECALL_RANKING_POLICY"),
        ):
            setattr(module, attribute, dataclasses.replace(getattr(module, attribute), **overrides))
    return dict(overrides)
