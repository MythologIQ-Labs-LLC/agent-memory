"""Relevance-sufficient return selection (#819, contract 1.9.0).

Recall runs ``candidate routes -> governed admission -> ranking -> return``. Before this
stage the return step was a ranked prefix under the budget ``k`` (contract 1.4.0), so a recall
returned ``min(k, admitted)`` facts however weak the match: the lexical route proposes every
fact that shares *any* token with the query, function words included, and nothing asked
whether a ranked fact carried enough evidence to be worth returning. On the independent AMB
PrecisionMemBench run (#818/#819) 60 of 62 failed cases returned unexpected memories.

This stage asks that question after ranking and before the budget:

* **Informative query terms** are the ranking tokenizer's terms minus a fixed closed-class
  English function-word list and single letters. The list holds grammar words only; it names
  no domain, entity or benchmark vocabulary.
* **Content relevance** of a candidate is Okapi BM25 restricted to informative terms, over the
  same admitted-set statistics and the same #583 anti-laundering term masks as the ranking
  stage, so it sees exactly the evidence ranking sees minus the function words.
* A candidate is **sufficient** when it is an exact-identity hit, or a non-lexical route
  (relational, semantic) surfaced it -- this stage has no calibration for those scores and does
  not withhold them -- or its content relevance is positive and at least ``RELATIVE_FLOOR``
  times the best content relevance in the recall.
* If no candidate is sufficient the recall **abstains**: nothing is returned.

The stage reads only the admitted, ranked list and its evidence. It never changes candidates,
admission, refusals, ``admitted`` or the ranked order, and it is never authority: a withheld
fact is still admitted and still visible to a caller that reads ``admitted`` or asks for the
1.4.0 ranked prefix (``return_selection="ranked_prefix"``). Selection can only remove facts
from what the budget sees, so it cannot surface a fact that governance or currentness refused.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Sequence

from .ranking_policy import _candidate_term_masks, admitted_set_bm25, relevance_tokens
from .temporal_intent import TemporalIntent

SELECTION_POLICY_ID = "relevance-sufficient-return-selection"
SELECTION_POLICY_VERSION = "1.0.0"
SELECTION_BASIS = "post_ranking_relevance_sufficiency_then_ranked_prefix"
RELATIVE_FLOOR = 0.5
RELEVANCE_SUFFICIENT = "relevance_sufficient"
RANKED_PREFIX = "ranked_prefix"
RETURN_SELECTIONS = (RELEVANCE_SUFFICIENT, RANKED_PREFIX)

# Closed-class English function words: articles and determiners, pronouns, auxiliaries and
# modals, prepositions, conjunctions, wh-words, negation and discourse particles, and the
# fragments the ``[a-z0-9]+`` tokenizer leaves from contractions ("what's" -> "what", "s").
# Grammar only; adding a content word here would be tuning, not linguistics.
FUNCTION_WORDS = frozenset("""
a an the this that these those some any each every either neither no another such
i me my mine myself we us our ours ourselves you your yours yourself yourselves
he him his himself she her hers herself it its itself they them their theirs themselves
one ones oneself what which who whom whose whatever whichever whoever
am is are was were be been being have has had having do does did doing done
will would shall should can could may might must ought
about above across after against along among around at before behind below beneath beside
besides between beyond by down during except for from in inside into like near of off on
onto out outside over past since than through throughout till to toward towards under
underneath until up upon via with within without
and or but nor so yet if then else because although though while whereas unless whether
as both also too very just only even still already again ever never not
how when where why there here
s t d m ll re ve don doesn didn isn aren wasn weren hasn haven hadn won wouldn shan
shouldn couldn mightn mustn needn ain
""".split())


def informative_terms(query: str) -> tuple[str, ...]:
    """The query's terms that can carry topical evidence, sorted and deduplicated."""

    return tuple(sorted({
        term for term in relevance_tokens(query)
        if term not in FUNCTION_WORDS and not (len(term) == 1 and term.isalpha())
    }))


def select_relevance_sufficient(
    ranked: Sequence[str],
    route_ids_by_candidate: Mapping[str, Iterable[str]],
    fact_lookup: Callable[[str], Any],
    *,
    query: str,
    intent: TemporalIntent,
    lexical_route: str,
    exact_identity_route: str,
    subordinate_routes: Iterable[str] = (),
    relative_floor: float = RELATIVE_FLOOR,
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, Any]]:
    """Return (sufficient refs in ranked order, per-candidate records, summary).

    ``ranked`` is the ranked admitted list; ``route_ids_by_candidate`` names the routes that
    surfaced each candidate. Statistics cover the candidates some primary route found, exactly
    the ranking stage's lexical scope (#669), so subordinate candidates cannot move a score.
    """

    if not 0.0 < relative_floor <= 1.0:
        raise ValueError("relative_floor must be in (0, 1]")
    ranked = list(ranked)
    subordinate = frozenset(subordinate_routes)
    routes = {ref: frozenset(route_ids_by_candidate.get(ref, ())) for ref in ranked}
    facts = {ref: fact_lookup(ref) for ref in ranked}
    lexical_scope = {ref: fact for ref, fact in facts.items() if routes[ref] - subordinate}
    terms = informative_terms(query)
    relevance: dict[str, float] = {}
    if terms and lexical_scope:
        texts = {ref: getattr(fact, "fact_text", "") or "" for ref, fact in lexical_scope.items()}
        masks = _candidate_term_masks(query, intent, lexical_scope)
        relevance = admitted_set_bm25(" ".join(terms), texts, masks)
    best = max(relevance.values(), default=0.0)

    records: dict[str, dict[str, Any]] = {}
    selected: list[str] = []
    for ref in ranked:
        score = relevance.get(ref, 0.0)
        relative = score / best if best > 0 else None
        if exact_identity_route in routes[ref]:
            basis = "exact_identity"
        elif routes[ref] - {lexical_route}:
            basis = "non_lexical_route_evidence"
        elif score <= 0.0:
            basis = "no_informative_term_match"
        elif relative is not None and relative >= relative_floor:
            basis = "content_relevance"
        else:
            basis = "below_relative_floor"
        sufficient = basis in {"exact_identity", "non_lexical_route_evidence", "content_relevance"}
        records[ref] = {
            "sufficient": sufficient,
            "basis": basis,
            "content_relevance": score,
            "relative_to_best": relative,
            "authority_effect": "none",
        }
        if sufficient:
            selected.append(ref)
    summary = {
        "informative_query_term_count": len(terms),
        "relative_floor": relative_floor,
        "withheld_insufficient_count": len(ranked) - len(selected),
        "abstained": bool(ranked) and not selected,
    }
    return selected, records, summary


__all__ = [
    "FUNCTION_WORDS",
    "RANKED_PREFIX",
    "RELATIVE_FLOOR",
    "RELEVANCE_SUFFICIENT",
    "RETURN_SELECTIONS",
    "SELECTION_BASIS",
    "SELECTION_POLICY_ID",
    "SELECTION_POLICY_VERSION",
    "informative_terms",
    "select_relevance_sufficient",
]
