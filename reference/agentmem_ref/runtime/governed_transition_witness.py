"""Bounded read-only witness for already-governed corrections (#644).

This does not authorize, apply, infer, or undo a correction. It only
describes an existing replacement record which the governed adapter has
looked up under the current reader's isolation context. A recorded
replacement may have further successors, so the *current* target is never
claimed to be the immediate successor of a particular correction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any

TRANSITION_WITNESS_VERSION = "1.0.0"
STATE_CHANGE = "state_change"
ERROR_CORRECTION = "error_correction"


@dataclass(frozen=True)
class GovernedTransitionWitness:
    """Scoped references only, never a claim that historical text was true."""

    source_fact_ref: str
    prior_fact_ref: str
    current_target_fact_ref: str
    proposal_ref: str
    correction_proposal_ref: str
    replacement_kind: str
    observer_version: str = TRANSITION_WITNESS_VERSION
    immediate_successor_verified: bool = False
    answer_quality_verified: bool = False
    can_stop: bool = False
    can_mutate: bool = False
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        for value in (
            self.source_fact_ref, self.prior_fact_ref,
            self.current_target_fact_ref, self.proposal_ref,
            self.correction_proposal_ref,
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ValueError("witness identity must be a bounded, nonempty string")
        if self.replacement_kind not in (STATE_CHANGE, ERROR_CORRECTION):
            raise ValueError("unsupported committed replacement kind")
        if (self.immediate_successor_verified is not False
                or self.answer_quality_verified is not False
                or self.can_stop is not False or self.can_mutate is not False
                or self.authority_effect != "none"
                or self.observer_version != TRANSITION_WITNESS_VERSION):
            raise ValueError("witness cannot grant authority or assert immediate successor")

    @property
    def status(self) -> str:
        return ("applied_state_change_observed" if self.replacement_kind == STATE_CHANGE
                else "applied_error_correction_observed")

    def to_dict(self) -> dict[str, object]:
        return {
            "observer_version": self.observer_version,
            "status": self.status,
            "source_fact_ref": self.source_fact_ref,
            "prior_fact_ref": self.prior_fact_ref,
            "current_target_fact_ref": self.current_target_fact_ref,
            "proposal_ref": self.proposal_ref,
            "correction_proposal_ref": self.correction_proposal_ref,
            "replacement_kind": self.replacement_kind,
            "immediate_successor_verified": False,
            "answer_quality_verified": False,
            "can_stop": False,
            "can_mutate": False,
            "authority_effect": "none",
        }


def inspect_committed_replacement(
    *,
    source_fact_ref: str,
    prior_fact_ref: str,
    current_target_fact_ref: str,
    source_slot: str,
    relation: Mapping[str, Any],
    replacement: Mapping[str, Any],
) -> GovernedTransitionWitness | None:
    """Check an *adapter-sourced* relation against an *adapter-sourced* record.

    The adapter must first verify tenant and reader domain, current admission
    for source and latest target, visibility of the historical prior, shared
    scope, actual invalidation of prior, and membership in the original
    admitted set. This helper deliberately cannot attest those conditions.
    A mere typed change assertion, an uncommitted proposal, or mismatched
    evidence references never produces a witness.
    """
    if not isinstance(relation, Mapping) or not isinstance(replacement, Mapping):
        return None
    if relation.get("classification") != "state_change_candidate":
        return None
    if relation.get("other_fact_uuid") != prior_fact_ref or relation.get("slot") != source_slot:
        return None
    proposal = relation.get("proposal")
    if not isinstance(proposal, Mapping):
        return None
    if (proposal.get("operation") != "correction"
            or proposal.get("replacement_kind") != STATE_CHANGE
            or proposal.get("source_fact_uuid") != source_fact_ref
            or proposal.get("target_fact_uuid") != prior_fact_ref
            or proposal.get("authority_effect") != "none"
            or proposal.get("applied") is not False):
        return None
    proposal_ref = proposal.get("proposal_id")
    correction_ref = replacement.get("proposal_id")
    logical_ref = proposal.get("target_reference")
    if (not isinstance(proposal_ref, str) or not proposal_ref
            or not isinstance(correction_ref, str) or not correction_ref
            or not isinstance(logical_ref, str) or not logical_ref
            or replacement.get("memory_id") != logical_ref
            or replacement.get("kind") not in (STATE_CHANGE, ERROR_CORRECTION)):
        return None
    evidence_refs = replacement.get("evidence_refs")
    if not isinstance(evidence_refs, (tuple, list)) or proposal_ref not in evidence_refs:
        return None
    if current_target_fact_ref in (source_fact_ref, prior_fact_ref):
        # A distinct, currently admitted target is the only safe indication
        # that the prior was replaced; this does not identify the immediate
        # successor of this particular operation.
        return None
    return GovernedTransitionWitness(
        source_fact_ref=source_fact_ref,
        prior_fact_ref=prior_fact_ref,
        current_target_fact_ref=current_target_fact_ref,
        proposal_ref=proposal_ref,
        correction_proposal_ref=correction_ref,
        replacement_kind=replacement["kind"],
    )
