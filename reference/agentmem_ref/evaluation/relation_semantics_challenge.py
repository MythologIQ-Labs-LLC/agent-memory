"""#688: non-authoritative, opt-in ontology reasoning *hypotheses*.

This is an offline evaluator, not a relation registry, access-control gate,
identity verifier, or public recall selector. All source/rule/eligibility
claims are caller supplied. Only edges from an already-public returned set
may contribute hints. Missing hints are NEVER evidence of irrelevance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RuleKind = Literal["inverse", "implies", "subclass", "disjoint"]
Operation = Literal["direct", "inverse", "implication"]


@dataclass(frozen=True)
class RelationObservation:
    returned_memory_ref: str
    subject_ref: str
    predicate_ref: str
    object_ref: str
    domain_ref: str
    source_claim_ref: str


@dataclass(frozen=True)
class RelationRuleClaim:
    rule_ref: str
    kind: RuleKind
    from_relation: str
    to_relation: str
    domain_ref: str
    provenance_ref: str
    active: bool = True


@dataclass(frozen=True)
class RelationQuestion:
    subject_ref: str
    predicate_ref: str
    domain_ref: str


@dataclass(frozen=True)
class CandidateHint:
    returned_memory_ref: str
    object_ref: str
    explanation_kind: str
    source_claim_ref: str
    rule_claim_ref: str | None
    # Never a factual assertion: even a supplied 'signed' rule is just a claim.
    authority_effect: str = "none"


@dataclass(frozen=True)
class ChallengeResult:
    hints: tuple[CandidateHint, ...]
    inspected_returned_edges: int
    truncated: bool
    unsupported_rule_claims: int
    claim_verification: str = "not_performed"
    may_withhold_content: bool = False
    authority_effect: str = "none"


def inspect_relation_claims(
    question: RelationQuestion,
    observations: tuple[RelationObservation, ...],
    rule_claims: tuple[RelationRuleClaim, ...],
    *,
    public_returned_refs: frozenset[str],
    requested_operations: frozenset[Operation] = frozenset({"direct"}),
    max_returned_edges: int = 64,
    max_rule_claims: int = 32,
) -> ChallengeResult:
    """Bounded diagnostics; NEVER use absence as an admission/selection veto.

    An inverse/implication rule is only a hypothesis about an already-returned
    relation. No new fact is retrieved; no graph traversal or canonical state
    read occurs. Caller must separately establish scope and issuer provenance.
    """
    if not isinstance(question, RelationQuestion) or not all((
        question.subject_ref, question.predicate_ref, question.domain_ref
    )):
        raise ValueError("nonempty relation question required")
    if type(max_returned_edges) is not int or max_returned_edges < 1:
        raise ValueError("positive finite edge budget required")
    if type(max_rule_claims) is not int or max_rule_claims < 0 or len(rule_claims) > max_rule_claims:
        raise ValueError("rule claim budget exceeded or invalid")
    if not isinstance(public_returned_refs, frozenset) or any(
        type(x) is not str or not x for x in public_returned_refs
    ):
        raise ValueError("public returned references must be nonempty strings")
    if not requested_operations or not requested_operations <= {"direct", "inverse", "implication"}:
        raise ValueError("unknown or empty reasoning operation")
    if any(not isinstance(r, RelationRuleClaim) or r.kind not in
           {"inverse", "implies", "subclass", "disjoint"} for r in rule_claims):
        raise ValueError("invalid relation rule")

    if any(not all((r.rule_ref, r.from_relation, r.to_relation, r.domain_ref,
                    r.provenance_ref)) for r in rule_claims):
        raise ValueError("rule claims require identity and provenance")
    if len({r.rule_ref for r in rule_claims}) != len(rule_claims):
        raise ValueError("duplicate rule identity in evaluation snapshot")
    # Traverse only public returned IDs. The caller's input is untrusted; this
    # evaluator never obtains missing content or reads a private substrate.
    visible = [edge for edge in observations if edge.returned_memory_ref in public_returned_refs
               and edge.domain_ref == question.domain_ref]
    truncated = len(visible) > max_returned_edges
    visible = visible[:max_returned_edges]
    rules = tuple(r for r in rule_claims if r.active and r.domain_ref == question.domain_ref)
    hints: set[CandidateHint] = set()
    for edge in visible:
        if ("direct" in requested_operations and edge.subject_ref == question.subject_ref
                and edge.predicate_ref == question.predicate_ref):
            hints.add(CandidateHint(edge.returned_memory_ref, edge.object_ref,
                                    "direct_claim", edge.source_claim_ref, None))
        for rule in rules:
            if ("inverse" in requested_operations and rule.kind == "inverse"
                    and rule.from_relation == edge.predicate_ref
                    and rule.to_relation == question.predicate_ref
                    and edge.object_ref == question.subject_ref):
                hints.add(CandidateHint(edge.returned_memory_ref, edge.subject_ref,
                                        "inverse_rule_claim", edge.source_claim_ref, rule.rule_ref))
            if ("implication" in requested_operations and rule.kind == "implies"
                    and rule.from_relation == edge.predicate_ref
                    and rule.to_relation == question.predicate_ref
                    and edge.subject_ref == question.subject_ref):
                hints.add(CandidateHint(edge.returned_memory_ref, edge.object_ref,
                                        "implication_rule_claim", edge.source_claim_ref, rule.rule_ref))
    return ChallengeResult(
        hints=tuple(sorted(hints, key=lambda x: (
            x.returned_memory_ref, x.explanation_kind, x.rule_claim_ref or "", x.object_ref))),
        inspected_returned_edges=len(visible), truncated=truncated,
        unsupported_rule_claims=sum(r.kind in {"subclass", "disjoint"} for r in rules),
    )


__all__ = ["RelationObservation", "RelationRuleClaim", "RelationQuestion",
           "CandidateHint", "ChallengeResult", "inspect_relation_claims"]
