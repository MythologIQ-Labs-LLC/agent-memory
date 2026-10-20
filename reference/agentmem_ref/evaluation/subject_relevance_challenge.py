"""Evaluation-only #775 challenge of lexical vs claimed subject evidence.

This is NOT a runtime selector, identity verifier, or authority decision. A
candidate that looks unrelated to a query can still provide needed context.
In particular, absent, false, or incomplete relation annotations MUST NOT
be interpreted as grounds for deleting memories or withholding answers.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

_WORDS = re.compile(r"[^\\W_]+", re.UNICODE)
_FUNCTION_WORDS = frozenset("a an and are as at be but by for from have how i in is it my of on or our the their to was were what when where which who why with you your".split())
Signal = Literal[
    "unverified_claims", "unknown", "direct_subject_claim", "related_subject_claim",
    "different_subject_claim", "property_mismatch_claim",
]


def _terms(text: str) -> frozenset[str]:
    """Simplistic lexical comparator, deliberately *not* a semantic classifier."""
    return frozenset(_WORDS.findall(text.casefold())) - _FUNCTION_WORDS


@dataclass(frozen=True)
class ChallengeInput:
    query: str
    memory_text: str
    query_subject_refs: tuple[str, ...] = ()
    memory_subject_refs: tuple[str, ...] = ()
    related_subject_refs: tuple[str, ...] = ()
    query_property_refs: tuple[str, ...] = ()
    memory_property_refs: tuple[str, ...] = ()
    # Verification is an external precondition, not established by this data class.
    identity_binding_checked: bool = False


@dataclass(frozen=True)
class ChallengeResult:
    lexical_overlap: bool
    structured_signal: Signal
    disagrees_with_lexical_control: bool
    may_withhold_content: bool = False
    authority_effect: str = "none"


def challenge(item: ChallengeInput) -> ChallengeResult:
    """Label *possible* relevance without modifying or omitting candidates.

    The distinction is deliberately asymmetric: a claimed relationship can
    explain why literal text matching would miss evidence, but even a checked
    difference in primary subjects cannot PROVE a memory irrelevant. A later
    independent evaluator must decide what is required for each task.
    """
    lexical = bool(_terms(item.query) & _terms(item.memory_text))
    if not item.identity_binding_checked:
        signal: Signal = "unverified_claims"
    elif not item.query_subject_refs or not item.memory_subject_refs:
        signal = "unknown"
    elif set(item.query_subject_refs) & set(item.memory_subject_refs):
        if (item.query_property_refs and item.memory_property_refs
                and not (set(item.query_property_refs) & set(item.memory_property_refs))):
            signal = "property_mismatch_claim"
        else:
            signal = "direct_subject_claim"
    elif set(item.query_subject_refs) & set(item.related_subject_refs):
        signal = "related_subject_claim"
    else:
        signal = "different_subject_claim"
    structured_support = signal in {"direct_subject_claim", "related_subject_claim"}
    # Deliberately report disagreements, rather than turning them into gates.
    return ChallengeResult(
        lexical_overlap=lexical,
        structured_signal=signal,
        disagrees_with_lexical_control=(structured_support != lexical)
        if signal in {"direct_subject_claim", "related_subject_claim", "different_subject_claim"}
        else False,
    )


__all__ = ["ChallengeInput", "ChallengeResult", "challenge"]
