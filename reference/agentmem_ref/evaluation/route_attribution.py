"""Evaluation-only route attribution for heterogeneous memory (#636).

Observes which routes produced already *returned* governed facts, using their
public admission receipts. It cannot run a route-disabled counterfactual,
measure downstream answer correctness, authorize content, or score hidden facts.
Gold annotations belong to the offline evaluator, never to the runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RouteEvidence:
    route_id: str
    returned: int
    required: int
    forbidden: int
    uniquely_required: int
    uniquely_forbidden: int
    shared_required: int


@dataclass(frozen=True)
class AttributionReport:
    returned: int
    required_total: int
    required_returned: int
    required_missing: int
    forbidden_returned: int
    unlabelled_returned: int
    unattributed_returned: int
    routes: tuple[RouteEvidence, ...]
    interpretation: str = "observed_returned_route_attribution_not_counterfactual_ablation"
    authority_effect: str = "none"


def attribute_returned_routes(
    recall: Mapping[str, Any],
    *,
    required_refs: frozenset[str],
    forbidden_refs: frozenset[str],
) -> AttributionReport:
    """Count route contributions only over IDs in a public `recall` result.

    `required_refs` and `forbidden_refs` are external evaluator annotations.
    Unlabelled is not synonymous with irrelevant; forbidden is explicit.
    Missing required items cannot be assigned to a route, nor can a route's
    observed attribution predict what a rerun with that route disabled does.
    """
    if not isinstance(recall, Mapping):
        raise ValueError("recall must be a mapping")
    returned, admitted, receipts = (recall.get(k) for k in ("returned", "admitted", "admissions"))
    if not isinstance(returned, list) or not isinstance(admitted, list) or not isinstance(receipts, Mapping):
        raise ValueError("recall must provide returned, admitted and admissions")
    for label, refs in (("required", required_refs), ("forbidden", forbidden_refs)):
        if not isinstance(refs, frozenset) or any(type(ref) is not str or not ref for ref in refs):
            raise ValueError(f"{label} refs must be a frozenset of nonempty strings")
    if required_refs & forbidden_refs:
        raise ValueError("a fact cannot be both required and forbidden")
    if any(type(ref) is not str or not ref for ref in returned + admitted):
        raise ValueError("recall refs must be nonempty strings")
    if len(returned) != len(set(returned)) or len(admitted) != len(set(admitted)):
        raise ValueError("duplicate recalled refs")
    if not set(returned) <= set(admitted):
        raise ValueError("returned fact is not admitted")
    route_sets: dict[str, frozenset[str]] = {}
    for ref in returned:
        receipt = receipts.get(ref)
        if not isinstance(receipt, Mapping):
            raise ValueError("returned fact lacks admission receipt")
        if receipt.get("outcome") != "admit":
            raise ValueError("returned fact lacks an admit decision")
        hits = receipt.get("route_provenance")
        if not isinstance(hits, (tuple, list)):
            raise ValueError("returned fact lacks route provenance list")
        ids: set[str] = set()
        for hit in hits:
            if not isinstance(hit, Mapping) or type(hit.get("route_id")) is not str or not hit["route_id"]:
                raise ValueError("malformed route provenance")
            ids.add(hit["route_id"])
        route_sets[ref] = frozenset(ids)
    reported = frozenset(returned)
    route_ids = sorted(set().union(*route_sets.values())) if route_sets else []
    rows: list[RouteEvidence] = []
    for route_id in route_ids:
        members = {ref for ref in returned if route_id in route_sets[ref]}
        required = members & required_refs
        forbidden = members & forbidden_refs
        rows.append(RouteEvidence(
            route_id=route_id,
            returned=len(members),
            required=len(required),
            forbidden=len(forbidden),
            uniquely_required=sum(len(route_sets[ref]) == 1 for ref in required),
            uniquely_forbidden=sum(len(route_sets[ref]) == 1 for ref in forbidden),
            shared_required=sum(len(route_sets[ref]) > 1 for ref in required),
        ))
    return AttributionReport(
        returned=len(returned),
        required_total=len(required_refs),
        required_returned=len(reported & required_refs),
        required_missing=len(required_refs - reported),
        forbidden_returned=len(reported & forbidden_refs),
        unlabelled_returned=len(reported - required_refs - forbidden_refs),
        unattributed_returned=sum(not route_sets[ref] for ref in returned),
        routes=tuple(rows),
    )


__all__ = ["AttributionReport", "RouteEvidence", "attribute_returned_routes"]
