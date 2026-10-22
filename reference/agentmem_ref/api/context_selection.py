"""Evidence-qualified context selection (#819, experimental opt-in consumer profile).

``AgentMemory.recall_context(..., consumer_profile="evidence_qualified")`` runs this selector
over the facts the governed recall already returned, *after* admission, ranking and the return
budget, and decides for each returned fact whether its content is delivered or declined. It is
a consumer-side delivery policy, never authority:

* it cannot add a fact the recall did not return, change admission, ranking, the ``returned``
  prefix, canonical truth, currentness, deletion or lifecycle; ``recall()`` is untouched;
* every declined fact stays in the package as ``omitted_selection`` with a versioned reason
  token and the terms that were inspected, so a consumer can audit or override the decision;
* it declines only on a *grounded* basis; when it cannot tell relevance from uncertainty it
  delivers the content and says so (``certainty: uncertain``), it never converts a lack of word
  overlap into an asserted negative when the fact carries non-lexical evidence.

Decision order for one returned fact (policy ``evidence-qualified-context-selection/0.4.1``):

1. ``preserved_exact_identity``: a caller-authorised ``logical_memory_refs`` hit (route
   ``exact_logical_identity``). Delivered whatever its wording.
2. ``preserved_corroborated_route``: any non-lexical route (shared-evidence graph, typed graph,
   semantic vector). The recall found it by evidence other than the words; delivered.
3. ``preserved_historical_admission``: admitted as historical / as-of evidence for a temporal
   query. Delivered: the query asked for that history.
4. Lexical-only facts are qualified against the query's *content terms*: tokens with a bounded
   list of English function words removed and a bounded, deterministic morphology fold applied
   (possessive, plural, ``-ing``/``-ed``, final ``-e``), so ``parents``/``parent``,
   ``works``/``work``, ``graduated``/``graduate`` and ``Mara's``/``Mara`` agree. No learned
   model, no corpus or benchmark vocabulary.

   * no query content term occurs in the fact in any folded form → ``no_query_term_evidence``
     (declined) **only when the fact is a single statement** (one sentence). A longer text can
     carry the answer in other words (an implicit relation, a paraphrase), so for it the absence
     of a shared term is uncertainty, not absence: delivered as ``undetermined_multi_statement``;
   * the query names a subject by a proper-noun possessive (``Liora's canoe``; a lowercase
     possessive such as ``composer's`` names no subject) and the fact grounds a different
     subject the same way or through its persisted write-time proposition entity, and the
     query's subject does not occur in the fact at all → ``subject_mismatch`` (declined). A
     first-person fact is about its speaker, so a proper-noun possessive inside it (``God's``,
     ``my friend Rachel's``) is a mention, not its subject: a first-person fact is never declined
     as a subject mismatch (policy 0.3.1);
   * the query is in the first person (``my``, ``our``, ``I``, ``we``: the subject is the caller)
     and the fact names a third party by proper-noun possessive while carrying no first-person
     marker and no ``speaker`` proposition → ``subject_mismatch`` (declined);
   * the query's subject occurs in the fact but none of the query's other content terms does
     → delivered as ``attribute_undetermined`` (uncertain), never declined (policy 0.4.0): a
     paraphrased predicate (``performs on the cello`` for ``plays an instrument``) is
     indistinguishable from a different attribute without a verified relation parser, and the
     selector must not turn what it cannot verify into a negative. The owner's product
     control that expected the wrong-object fact to be declined was corrected for this reason
     (PR #841 review, comment 6350329872);
   * otherwise delivered, with the matched terms listed. A fact that matches only by its subject
     while the query has no other content terms, a fact whose subject cannot be grounded, or a
     query with no content terms at all is delivered as ``uncertain``.

Subject grounding uses only what is persisted or caller-bound: the possessive form in the text
itself and the write-time proposition entity (``write_semantics.proposition``) when the
interpreter recorded one. Nothing here authenticates a subject.

The package-level ``selection`` block states the assessment: ``evidence_delivered``,
``undetermined`` (only uncertain items delivered), ``no_relevant_evidence`` (every returned fact
declined on a grounded basis) or ``no_returned_candidates`` (the recall returned nothing). A
consumer must not read ``no_relevant_evidence`` as proof that no relevant memory exists; it
means no returned fact carried evidence for the query under this policy.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

POLICY_ID = "evidence-qualified-context-selection"
POLICY_VERSION = "0.4.1"
BASIS = "post_admission_query_evidence_qualification"
EXACT_IDENTITY_ROUTE = "exact_logical_identity"
LEXICAL_ROUTE = "lexical"

OMITTED_REASONS = ("no_query_term_evidence", "subject_mismatch")
DELIVERED_EVIDENCE = (
    "preserved_exact_identity",
    "preserved_corroborated_route",
    "preserved_historical_admission",
    "subject_and_attribute_evidence",
    "query_term_evidence",
    "subject_only_evidence",
    "ungrounded_subject",
    "undetermined_query",
    "undetermined_multi_statement",
    "attribute_undetermined",
)
ASSESSMENTS = ("evidence_delivered", "undetermined", "no_relevant_evidence", "no_returned_candidates")

_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)?", re.UNICODE)
_STATEMENT_END = re.compile(r"[.!?]+(?:\s|$)")
# First-person markers: a query in the first person is about the caller (``speaker``).
FIRST_PERSON = frozenset({"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"})
_POSSESSIVE = re.compile(r"^(.+?)'s$|^(.+?s)'$")
# Bounded English function words (articles, pronouns, auxiliaries, prepositions, conjunctions,
# question words). Grammatical glue only: no nouns, no domain or benchmark vocabulary.
FUNCTION_WORDS = frozenset("""
a an the and or but nor so yet if then than that this these those there here
i me my mine myself we us our ours ourselves you your yours yourself yourselves
he him his himself she her hers herself it its itself they them their theirs themselves
who whom whose which what when where why how whether
is am are was were be been being
do does did doing done have has had having
can could may might must shall should will would
of to in on at by for from with without about into onto upon over under
between among through during before after above below up down out off
again further once more most some any all each every both few other such
no not only own same too very just also
tell say said know want need like please
""".split())


def _fold(term: str) -> str:
    """A bounded, deterministic English morphology fold. It is a normaliser for equality tests,
    not a lemmatiser: both sides of a comparison are folded the same way."""

    match = _POSSESSIVE.match(term)
    if match:
        term = match.group(1) or match.group(2)
    if any(character.isdigit() for character in term) or len(term) <= 3:
        return term
    if term.endswith("ies") and len(term) > 4:
        term = term[:-3] + "y"
    elif term.endswith(("sses", "xes", "zes", "ches", "shes")):
        term = term[:-2]
    elif term.endswith("s") and not term.endswith(("ss", "us", "is")):
        term = term[:-1]
    for suffix in ("ing", "ed"):
        if term.endswith(suffix) and len(term) - len(suffix) >= 3:
            term = term[: -len(suffix)]
            if len(term) >= 4 and term[-1] == term[-2] and term[-1] not in "aeiou":
                term = term[:-1]
            break
    if term.endswith("e") and len(term) > 3:
        term = term[:-1]
    return term


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.casefold().replace("’", "'"))


def content_terms(text: str) -> frozenset[str]:
    """The folded content terms of ``text``: every token that is not a function word."""

    return frozenset(_fold(token) for token in _tokens(text)
                     if _possessive_base(token) not in FUNCTION_WORDS and _contraction_base(token) not in FUNCTION_WORDS)


def _possessive_base(token: str) -> str:
    match = _POSSESSIVE.match(token)
    return (match.group(1) or match.group(2)) if match else token


def _contraction_base(token: str) -> str:
    """``i'm`` → ``i``, ``we've`` → ``we``, ``don't`` → ``don``: the word a contraction starts
    with, for function-word and first-person tests (0.4.1; a contracted first-person marker was
    previously missed, so a first-person fact could be declined as a third party's)."""

    return token.split("'", 1)[0]


def single_statement(text: str) -> bool:
    """Whether ``text`` is one sentence: the only regime in which the absence of a term is a
    grounded observation about the whole statement rather than about one of many."""

    return len([part for part in _STATEMENT_END.split(text.strip()) if part.strip()]) == 1


def possessive_subjects(text: str) -> frozenset[str]:
    """Folded subjects that ``text`` names by a proper-noun possessive (``Liora's``,
    ``Mara's``). A lowercase possessive (``composer's``, ``doctor's``) is a modifier, not a
    subject the query is about, and names nothing here."""

    subjects = set()
    for token in _WORD.findall(text.replace("\u2019", "'")):
        match = _POSSESSIVE.match(token.casefold())
        if match and token[0].isupper():
            base = match.group(1) or match.group(2)
            if base not in FUNCTION_WORDS:
                subjects.add(_fold(base))
    return frozenset(subjects)


def first_person(text: str, proposition: Mapping[str, Any] | None = None) -> bool:
    """Whether ``text`` speaks in the first person (or its persisted proposition names the
    ``speaker``). The marker is grammatical; nothing here authenticates who wrote it."""

    if isinstance(proposition, Mapping) and proposition.get("status") == "known" and proposition.get("entity") == "speaker":
        return True
    return any(_possessive_base(token) in FIRST_PERSON or _contraction_base(token) in FIRST_PERSON
               for token in _tokens(text))


def grounded_subject(text: str, proposition: Mapping[str, Any] | None) -> frozenset[str]:
    """The subject terms the fact itself grounds: its possessive subjects plus the entity of its
    persisted write-time proposition when the interpreter recorded one. ``speaker`` (first
    person) names no subject a query could anchor."""

    subject = set(possessive_subjects(text))
    if isinstance(proposition, Mapping) and proposition.get("status") == "known":
        entity = proposition.get("entity")
        if isinstance(entity, str) and entity != "speaker":
            subject.update(content_terms(entity))
    return frozenset(subject)


def _routes(decision: Mapping[str, Any]) -> list[str]:
    return [str(hit.get("route_id")) for hit in decision.get("route_provenance") or () if hit.get("route_id")]


def qualify(
    query: str,
    fact_ref: str,
    decision: Mapping[str, Any],
    text: str,
    proposition: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """The selection decision for one returned fact. Pure: reads the recall decision, the fact
    text and its persisted proposition; writes nothing."""

    routes = _routes(decision)
    basis = decision.get("admission_basis") or {}
    record: dict[str, Any] = {"fact_ref": fact_ref, "routes": sorted(set(routes))}
    if EXACT_IDENTITY_ROUTE in routes:
        return {**record, "outcome": "delivered", "evidence": "preserved_exact_identity", "certainty": "grounded"}
    if any(route != LEXICAL_ROUTE for route in routes):
        return {**record, "outcome": "delivered", "evidence": "preserved_corroborated_route", "certainty": "grounded"}
    currentness = basis.get("currentness")
    if currentness is not None and currentness != "current_state":
        return {**record, "outcome": "delivered", "evidence": "preserved_historical_admission",
                "certainty": "grounded", "currentness": currentness}
    query_terms = content_terms(query)
    if not query_terms:
        return {**record, "outcome": "delivered", "evidence": "undetermined_query", "certainty": "uncertain",
                "matched_terms": []}
    fact_terms = content_terms(text)
    matched = sorted(query_terms & fact_terms)
    single = single_statement(text)
    record["matched_terms"] = matched
    record["single_statement"] = single
    if not matched:
        if single:
            return {**record, "outcome": "omitted", "reason": "no_query_term_evidence", "certainty": "grounded"}
        return {**record, "outcome": "delivered", "evidence": "undetermined_multi_statement", "certainty": "uncertain"}
    anchors = possessive_subjects(query)
    record["query_subjects"] = sorted(anchors)
    speaker_query = first_person(query)
    speaker_fact = first_person(text, proposition)
    if not anchors:
        if speaker_query:
            # The caller asks about themselves: a fact grounded on a third party by possessive,
            # with no first-person marker of its own, is about someone else.
            record["query_subjects"] = ["speaker"]
            third_party = possessive_subjects(text)
            record["fact_subjects"] = sorted(third_party)
            if third_party and not speaker_fact:
                return {**record, "outcome": "omitted", "reason": "subject_mismatch", "certainty": "grounded"}
            if speaker_fact:
                return {**record, "outcome": "delivered", "evidence": "subject_and_attribute_evidence", "certainty": "grounded"}
        return {**record, "outcome": "delivered", "evidence": "query_term_evidence", "certainty": "grounded"}
    subject = grounded_subject(text, proposition)
    record["fact_subjects"] = sorted(subject)
    if not (anchors & fact_terms):
        if subject and not (anchors & subject) and not speaker_fact:
            return {**record, "outcome": "omitted", "reason": "subject_mismatch", "certainty": "grounded"}
        return {**record, "outcome": "delivered", "evidence": "ungrounded_subject", "certainty": "uncertain"}
    others = query_terms - anchors
    if not others:
        return {**record, "outcome": "delivered", "evidence": "subject_only_evidence", "certainty": "uncertain"}
    if not (others & fact_terms):
        return {**record, "outcome": "delivered", "evidence": "attribute_undetermined", "certainty": "uncertain"}
    return {**record, "outcome": "delivered", "evidence": "subject_and_attribute_evidence", "certainty": "grounded"}


def assessment(decisions: Sequence[Mapping[str, Any]]) -> str:
    """``no_relevant_evidence`` only when every returned fact was inspected and declined on a
    grounded basis. A fact that could not be inspected (``unavailable``: unresolved, withheld,
    unsupported or past the delivery budget) leaves the question open, so its presence makes the
    assessment ``undetermined`` unless grounded evidence was delivered."""

    if not decisions:
        return "no_returned_candidates"
    delivered = [d for d in decisions if d["outcome"] == "delivered"]
    if any(d.get("certainty") == "grounded" for d in delivered):
        return "evidence_delivered"
    if delivered or any(d["outcome"] == "unavailable" for d in decisions):
        return "undetermined"
    return "no_relevant_evidence"


def selection_block(query: str, decisions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The package-level ``selection`` record for ``consumer_profile="evidence_qualified"``."""

    delivered = [d for d in decisions if d["outcome"] == "delivered"]
    omitted = [d for d in decisions if d["outcome"] == "omitted"]
    reasons: dict[str, int] = {}
    for d in omitted:
        reasons[d["reason"]] = reasons.get(d["reason"], 0) + 1
    return {
        "consumer_profile": "evidence_qualified",
        "policy_id": POLICY_ID,
        "policy_version": POLICY_VERSION,
        "basis": BASIS,
        "query_terms": sorted(content_terms(query)),
        "query_subjects": sorted(possessive_subjects(query)),
        "decisions": {d["fact_ref"]: {k: v for k, v in d.items() if k != "fact_ref"} for d in decisions},
        "delivered_refs": [d["fact_ref"] for d in delivered],
        "omitted_refs": [d["fact_ref"] for d in omitted],
        "delivered_count": len(delivered),
        "omitted_count": len(omitted),
        "uncertain_count": sum(1 for d in delivered if d.get("certainty") == "uncertain"),
        "omitted_reasons": reasons,
        "assessment": assessment(decisions),
        "authority_effect": "none",
    }


__all__ = ["ASSESSMENTS", "BASIS", "DELIVERED_EVIDENCE", "FIRST_PERSON", "FUNCTION_WORDS", "OMITTED_REASONS",
           "POLICY_ID", "POLICY_VERSION", "assessment", "content_terms", "first_person", "grounded_subject",
           "possessive_subjects", "qualify", "selection_block", "single_statement"]
