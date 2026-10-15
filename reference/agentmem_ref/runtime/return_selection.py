"""Relevance-sufficient return selection (#819, contract 1.9.0).

Recall runs ``candidate routes -> governed admission -> ranking -> return``. Before this
stage the return step was a ranked prefix under the budget ``k`` (contract 1.4.0), so a recall
returned ``min(k, admitted)`` facts however weak the match: the lexical route proposes every
fact that shares *any* token with the query, function words included, and nothing asked
whether a ranked fact carried enough evidence to be worth returning. On the independent AMB
PrecisionMemBench run (#818/#819) 60 of 62 failed cases returned unexpected memories.

This stage asks that question after ranking and before the budget:

* **Informative query terms** are the ranking tokenizer's terms, after contractions are
  normalised ("don't" -> "do not", "Mara's" -> "Mara"), minus a fixed closed-class English
  function-word list. The list holds grammar words only, and no word whose content reading is
  common in memory text ("Will", "May", "US", "like", "one"); it names no domain, entity or
  benchmark vocabulary.
* **Content relevance** of a candidate is Okapi BM25 restricted to informative terms, over the
  same admitted-set statistics and the same #583 anti-laundering term masks as the ranking
  stage, so it sees exactly the evidence ranking sees minus the function words.
* A candidate is **sufficient** when it is an exact-identity hit, or a non-lexical route
  (relational, semantic) surfaced it -- this stage has no calibration for those scores and does
  not withhold them -- or its content relevance is positive and at least ``RELATIVE_FLOOR``
  times the best content relevance in the recall.
* **Ranking consistency** (1.1.0): a fact with positive content relevance that ranking placed
  above a sufficient fact is sufficient too, so selection never reverses ranking's order
  between two facts that both carry topical evidence (a fact stuffed with query terms cannot
  push the top-ranked fact out).
* If no candidate is sufficient the recall **abstains**: nothing is returned.

Policy 2.0.0 (#819 C3) builds an **evidence set** instead of filtering candidates one by one.
C2 (1.1.0) lost multi-evidence questions: every fact faced one floor relative to the best, and
question-frame words ("how many", "total", "months") counted as topical evidence. 2.0.0 reads
the query first (``query_interpretation``): relevance uses topical terms only, an aggregate or
relational question admits set evidence down to half the floor, and the fact most about each
named entity joins the set. Ranking, admission and governance are unchanged.

Policy 2.1.0 (#819 C3 slice 2) matches word forms, not exact tokens: query and fact terms are
compared by their inflectional normal form (``lexical_normalization``: Porter step 1, so
"weddings"/"wedding" and "attended"/"attend" meet; derivational families stay apart), and a
short query whose topic matched nothing may correct one Damerau edit against the admitted
vocabulary ("typsecript" -> "typescript"). The planner applies the same rules to candidate
discovery, using only the vocabulary of current, live, in-scope facts; ranking still scores
the query as written. Ranking consistency is anchored on primary evidence only: with set
evidence as an anchor, one weak set member ranked low pulled in every fact ranked above it that
carried any topical trace (on LongMemEval-S, 1,056 such returns of which 14 were gold).

Policy 2.2.0 (#819 C3 slice 3) adds **lifecycle closure**. A later fact can carry a guarded
write-time state-change relation to an earlier one (#671 typed slot; guards G2-G13, read by
``GovernedMemoryAdapter.lifecycle_successors``). Relevance alone withheld the later state when it
shared no topical word ("Where do I live now?" returned "I live in Boston." without "I moved to
Denver."), presenting a changed state as if it still held. A selected fact now brings the
admitted facts that change it, transitively. The relation is runtime write-time evidence, never
memory text; only admitted facts can join; no currentness decision is made, so the
explicit-current gate (G1) does not apply.

Policy 2.3.0 (#819 C4) controls what joins the set. C3 recovered multi-evidence recall but returned
facts no requirement asked for. Two rules tighten that without touching aggregate sets:
**uncovered-entity coverage** (an entity a selected fact already *writes as a name* with at least
half the best relevance to it is covered; only an uncovered entity brings another fact) and
**ranking consistency anchored on the best primary fact** (only a fact ranking places above the
best match is promoted, not ordering noise below it). Each admitted fact's record states the
requirement served and the query terms and entities it added.

The stage reads only the admitted, ranked list and its evidence. It never changes candidates,
admission, refusals, ``admitted`` or the ranked order, and it is never authority: a withheld
fact is still admitted and still visible to a caller that reads ``admitted`` or asks for the
1.4.0 ranked prefix (``return_selection="ranked_prefix"``). Selection can only remove facts
from what the budget sees, so it cannot surface a fact that governance or currentness refused.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Callable, Iterable, Mapping, Sequence

from .ranking_policy import (
    HIGH_RISK_SELF_CLAIMS,
    admitted_set_bm25,
    eligible_temporal_query_terms,
    persisted_self_claims,
    relevance_tokens,
)
from .lexical_normalization import normal_form, normalized_text, typo_correction_allowed, typo_matches
from .query_interpretation import QueryInterpretation, interpret, starts_sentence
from .temporal_intent import TemporalIntent

SELECTION_POLICY_ID = "relevance-sufficient-return-selection"
SELECTION_POLICY_VERSION = "2.3.0"
SELECTION_BASIS = "post_ranking_relevance_sufficiency_then_ranked_prefix"
RELATIVE_FLOOR = 0.5
# 2.0.0: a query that needs several pieces of evidence (aggregate or relational) admits set
# evidence down to half the single-answer floor.
SET_FLOOR_FACTOR = 0.5
# Entity coverage runs one admitted-set BM25 pass per mention; the first mentions in query order
# are covered (bounded cost for queries that list many identifiers).
MAX_COVERED_MENTIONS = 8
# 2.3.0: an entity is covered when a selected fact's admitted-set relevance to it is at least this
# fraction of the best such relevance (the primary floor's relative scale).
COVERAGE_FRACTION = 0.5
RELEVANCE_SUFFICIENT = "relevance_sufficient"
RANKED_PREFIX = "ranked_prefix"
RETURN_SELECTIONS = (RELEVANCE_SUFFICIENT, RANKED_PREFIX)
_SUFFICIENT = frozenset({"exact_identity", "non_lexical_route_evidence", "content_relevance", "set_evidence"})
_PRIMARY = frozenset({"exact_identity", "non_lexical_route_evidence", "content_relevance"})

# Closed-class English function words: articles and determiners, pronouns, auxiliaries and
# modals, prepositions, conjunctions, wh-words, negation and discourse particles. Grammar only;
# adding a content word here would be tuning, not linguistics. Words whose content reading is
# common in lower case stay out ("like", "one", "past", "near", "mine", "won"). Function words
# that are also names ("will", "may", "us") stay in, and ``informative_terms`` keeps them when
# the query writes them as a name. Contraction fragments are not listed:
# ``normalize_contractions`` removes them before tokenisation.
FUNCTION_WORDS = frozenset("""
a an the this that these those some any each every either neither no another such
i me my myself we us our ours ourselves you your yours yourself yourselves
he him his himself she her hers herself it its itself they them their theirs themselves
ones oneself what which who whom whose whatever whichever whoever
am is are was were be been being have has had having do does did doing done
will would shall should can could may might must ought
about above across after against along among around at before behind below beneath beside
besides between beyond by down during except for from in inside into of off on
onto out outside over since than through throughout till to toward towards under
underneath until up upon via with within without
and or but nor so yet if then else because although though while whereas unless whether
as both also too very just only even still already again ever never not
how when where why there here
""".split())

_CONTRACTIONS = (
    (re.compile(r"\bwon[\u2019']t\b", re.IGNORECASE), "will not"),
    (re.compile(r"\bcan[\u2019']t\b", re.IGNORECASE), "can not"),
    (re.compile(r"\bshan[\u2019']t\b", re.IGNORECASE), "shall not"),
    (re.compile(r"n[\u2019']t\b", re.IGNORECASE), " not"),
    (re.compile(r"[\u2019'](s|re|ve|ll|d|m)\b", re.IGNORECASE), ""),
)


def normalize_contractions(text: str) -> str:
    """Expand negative contractions and drop clitics ("don't" -> "do not", "Mara's" -> "Mara")."""

    for pattern, replacement in _CONTRACTIONS:
        text = pattern.sub(replacement, text)
    return text


_WORD = re.compile(r"[A-Za-z0-9]+")
_SENTENCE_START = re.compile(r"(^|[.!?:;]\s+|[\"\u201c(]\s*)$")


def _written_as_name(query: str, match: re.Match) -> bool:
    """A function word spelled as a name: capitalised mid-sentence, or an acronym ("US")."""

    token = match.group(0)
    if token.lower() == "i" or not token[0].isupper():
        return False
    if len(token) > 1 and token.isupper():
        return True
    return not _SENTENCE_START.search(query[:match.start()])


def informative_terms(query: str) -> tuple[str, ...]:
    """The query's terms that can carry topical evidence, sorted and deduplicated.

    Function words are dropped, except where the query writes one as a name ("Who is Will?",
    "in May", "the US"). That exception is off for a query in all capitals or title case,
    where capitalisation says nothing.
    """

    text = normalize_contractions(query)
    # Title case is judged on words that are not sentence-initial and not "I".
    inner = [m.group(0) for m in _WORD.finditer(text)
             if m.group(0)[0].isalpha() and m.group(0).lower() != "i"
             and not _SENTENCE_START.search(text[:m.start()])]
    capitalised = sum(1 for word in inner if word[0].isupper())
    case_informative = any(c.islower() for c in text) and capitalised * 2 <= len(inner)
    terms = set()
    for match in _WORD.finditer(text):
        term = match.group(0).lower()
        if term not in FUNCTION_WORDS or (case_informative and _written_as_name(text, match)):
            terms.add(term)
    return tuple(sorted(terms))


@lru_cache(maxsize=256)
def interpret_query(query: str) -> QueryInterpretation:
    """Topic, frame, entity mentions and information requirement of ``query`` (2.0.0)."""

    return interpret(query, function_words=FUNCTION_WORDS, normalize=normalize_contractions,
                     word_re=_WORD, sentence_start=_SENTENCE_START)


def _normal_form_masks(query: str, intent: TemporalIntent, facts: Mapping[str, Any],
                       texts: Mapping[str, str]) -> dict[str, tuple[str, ...]]:
    """The ranking stage's #583 anti-laundering masks, matched on normal forms (2.1.0).

    Relevance compares normal forms, so the mask must too: a self-claiming fact that writes an
    inflection of a masked temporal-intent query word ("planned" for "planning") is masked
    exactly as the word itself would be. Same eligibility and self-claim rules as
    ``ranking_policy._candidate_term_masks``.
    """

    eligible = {normal_form(term) for term in eligible_temporal_query_terms(query, intent)}
    masks: dict[str, tuple[str, ...]] = {}
    for ref, fact in facts.items():
        if not eligible or not (HIGH_RISK_SELF_CLAIMS & set(persisted_self_claims(fact))):
            masks[ref] = ()
            continue
        masks[ref] = tuple(sorted(eligible & set(texts.get(ref, "").split())))
    return masks


_POSSESSIVE_AFTER = ("'s", "\u2019s")
# A word after a line break, list marker, dash or closing parenthesis starts a clause, as after
# sentence punctuation: its capital says nothing about names ("- Mark it urgent").
_CLAUSE_OPENERS = frozenset("-*\u2022\u2013\u2014)")


def _starts_clause(text: str, position: int) -> bool:
    if starts_sentence(text, position):
        return True
    end = position
    while end > 0 and text[end - 1].isspace():
        if text[end - 1] == "\n":
            return True
        end -= 1
    return end > 0 and text[end - 1] in _CLAUSE_OPENERS


def _names_mention(text: str, mention: tuple[str, ...]) -> bool:
    """Whether ``text`` writes a term of ``mention`` as a name (2.3.0), by the query interpreter's
    orthographic rules: a letter-digit token always; otherwise only where capitals carry
    information (not an all-caps or title-case text), a capitalised token that does not start a
    sentence, or that starts one in possessive form ("Mom's new address"). A homograph ("mark it
    urgent", "Mark the form as urgent", "MARK IT URGENT", "Will confirm later") does not cover
    the person Mark or Will. ``text`` is the fact's original text."""

    inner = [m.group(0) for m in _WORD.finditer(text)
             if m.group(0)[0].isalpha() and m.group(0) != "I" and not _starts_clause(text, m.start())]
    capitalised = sum(1 for word in inner if word[0].isupper())
    # The query interpreter's rule: when most inner words are capitalised (a heading in title
    # case, even with lowercase small words) capitals carry no information about names.
    case_informative = any(c.islower() for c in text) and capitalised * 2 <= len(inner)
    for match in _WORD.finditer(text):
        token = match.group(0)
        if normal_form(token.lower()) not in mention:
            continue
        if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
            return True
        if not case_informative or not token[0].isupper():
            continue
        if not _starts_clause(text, match.start()) or text[match.end():match.end() + 2] in _POSSESSIVE_AFTER:
            return True
    return False


def _mention_matched(mention: tuple[str, ...], tokens: frozenset[str]) -> bool:
    hits = sum(1 for term in mention if term in tokens)
    return hits == len(mention) if len(mention) <= 2 else hits * 2 >= len(mention)


_WH_PLURAL_LEADS = frozenset({"which", "what", "who"})
_PLURAL_COPULAS = frozenset({"are", "were"})
_AUXILIARIES = frozenset("am is are was were do does did have has had can could will would shall should may might must".split())
_NOT_PLURAL_ENDINGS = ("ss", "us", "is")


def _plural(word: str) -> bool:
    return (len(word) > 3 and word.endswith("s") and not word.endswith(_NOT_PLURAL_ENDINGS)
            and normal_form(word) != word)


def plural_answer(query: str) -> bool:
    """Whether a wh-question asks for several items by its grammar (#819 C6: sizes the semantic
    route's proposals; selection does not read it).

    "which/what/who are|were ...", "which <plural> <auxiliary or function word>|<end>" ("Which
    pets do we have?"), or a plural noun-phrase head directly before an auxiliary ("What
    medications am I on?"). A plural is a non-function word that inflectional normalisation
    shortens (Porter step 1) and does not end in -ss, -us or -is. Third-person verbs are not read
    ("Which goes first?", "What happens next?", "Which does Alice prefer?"); irregular plurals
    ("people") and "which of ..." are not read either. Closed English grammar; no topic
    vocabulary."""

    words = [word.lower() for word in _WORD.findall(normalize_contractions(query))]
    if len(words) < 2 or words[0] not in _WH_PLURAL_LEADS:
        return False
    if words[1] in _PLURAL_COPULAS:
        return True
    if words[0] == "who":
        return False
    if (words[0] == "which" and words[1] not in FUNCTION_WORDS and _plural(words[1])
            and (len(words) == 2 or words[2] in FUNCTION_WORDS)):
        return True
    for index in range(2, min(len(words), 5)):
        if words[index] in _AUXILIARIES:
            return words[index - 1] not in FUNCTION_WORDS and _plural(words[index - 1])
        if words[index] in FUNCTION_WORDS:
            return False
    return False


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
    lifecycle_successors: Mapping[str, Iterable[str]] | None = None,
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, Any]]:
    """Return (the evidence set in ranked order, per-candidate records, summary).

    Evidence-set construction (2.0.0) over the ranked admitted list:

    1. **Primary evidence**: exact-identity hits, facts a non-lexical route surfaced, and
       lexical facts whose *topical* relevance (frame words excluded) is at least
       ``relative_floor`` of the best.
    2. **Set evidence**: when the query needs several pieces of evidence (aggregate or
       relational), lexical facts down to ``SET_FLOOR_FACTOR`` times that floor.
    3. **Ranking consistency**: a fact with topical evidence ranked above a primary-evidence
       fact is selected too (set evidence does not extend it, 2.1.0).
    4. **Entity coverage**: each entity the query names that no selected fact covers is
       covered by its highest-ranked candidate with topical evidence, if any.
    5. **Lifecycle closure** (2.2.0): a selected fact that ``lifecycle_successors`` maps to
       later admitted facts (guarded write-time state-change relations) brings them in,
       transitively. Facts outside the ranked admitted list never join.

    Nothing else is added; if nothing qualifies the recall abstains. Statistics cover the
    candidates some primary route found (#669), with the ranking stage's #583 masks.
    """

    if not 0.0 < relative_floor <= 1.0:
        raise ValueError("relative_floor must be in (0, 1]")
    ranked = list(ranked)
    subordinate = frozenset(subordinate_routes)
    routes = {ref: frozenset(route_ids_by_candidate.get(ref, ())) for ref in ranked}
    facts = {ref: fact_lookup(ref) for ref in ranked}
    lexical_scope = {ref: fact for ref, fact in facts.items() if routes[ref] - subordinate}
    reading = interpret_query(query)
    relevance: dict[str, float] = {}
    tokens: dict[str, frozenset[str]] = {}
    texts: dict[str, str] = {}
    masks: dict[str, tuple[str, ...]] = {}
    evidence_terms = reading.topical_terms
    query_forms: tuple[str, ...] = ()
    frame_fallback = False
    mentions = reading.entity_mentions
    if lexical_scope and (reading.topical_terms or reading.frame_terms):
        # Matching is on normal forms (2.1.0): "weddings" meets "wedding", and a query term that
        # matches nothing is read as its one-edit neighbours in the admitted text ("typsecript").
        raw_texts = {ref: normalize_contractions(getattr(fact, "fact_text", "") or "") for ref, fact in lexical_scope.items()}
        texts = {ref: normalized_text(text) for ref, text in raw_texts.items()}
        masks = _normal_form_masks(query, intent, lexical_scope, texts)
        tokens = {ref: frozenset(text.split()) - frozenset(masks.get(ref, ())) for ref, text in texts.items()}
        normal_vocabulary = frozenset().union(*tokens.values()) if tokens else frozenset()

        allow_typos = typo_correction_allowed(
            len(reading.topical_terms), any(normal_form(term) in normal_vocabulary for term in reading.topical_terms))
        raw_vocabulary = (sorted(set().union(*(relevance_tokens(text) for text in raw_texts.values())))
                          if allow_typos else [])

        def normalize_terms(terms: Iterable[str]) -> tuple[str, ...]:
            out: list[str] = []
            for term in terms:
                form = normal_form(term)
                corrected = () if form in normal_vocabulary or not allow_typos else typo_matches(term, raw_vocabulary)
                out.extend(normal_form(match) for match in corrected) if corrected else out.append(form)
            return tuple(dict.fromkeys(out))

        mentions = tuple(normalize_terms(mention) for mention in mentions)
        query_forms = normalize_terms(reading.topical_terms or reading.frame_terms)
        if reading.topical_terms:
            # A query with a topic is answered only by evidence about that topic: when nothing
            # topical matches, the recall abstains rather than fall back to frame words.
            relevance = admitted_set_bm25(" ".join(normalize_terms(reading.topical_terms)), texts, masks)
        else:
            # A query that is all frame ("what did I do last week?") has no other topic.
            evidence_terms = reading.frame_terms
            frame_fallback = True
            relevance = admitted_set_bm25(" ".join(normalize_terms(evidence_terms)), texts, masks)
    best = max(relevance.values(), default=0.0)
    set_floor = relative_floor * SET_FLOOR_FACTOR if reading.needs_several else relative_floor

    records: dict[str, dict[str, Any]] = {}
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
        elif relative is not None and relative >= set_floor:
            basis = "set_evidence"
        else:
            basis = "below_relative_floor"
        records[ref] = {
            "sufficient": basis in _SUFFICIENT,
            "basis": basis,
            "content_relevance": score,
            "relative_to_best": relative,
            "authority_effect": "none",
        }
    matched = {ref: frozenset(term for term in query_forms if term in tokens.get(ref, frozenset())) for ref in ranked}
    position = {ref: index for index, ref in enumerate(ranked)}
    # Ranking consistency (2.3.0): a fact with topical evidence that ranking places above the
    # *best* primary-evidence fact keeps its place. Only ranking's non-lexical stages (currentness,
    # temporal applicability, identity, corroboration) can put it there; ordering noise among
    # similar facts below the best match is not evidence (C3 anchored on the lowest primary fact).
    first = min((index for index, ref in enumerate(ranked) if records[ref]["basis"] in _PRIMARY), default=-1)
    for ref in ranked[:max(first, 0)]:
        if records[ref]["basis"] == "below_relative_floor":
            records[ref].update(sufficient=True, basis="ranked_above_sufficient")
    # Entity coverage (2.3.0): a named entity is covered when a selected fact is substantially
    # about it (its relevance to the mention is at least COVERAGE_FRACTION of the best). Only an
    # uncovered entity brings the admitted fact most about it; a passing mention is not coverage.
    entities_added: dict[str, int] = {}
    for mention in mentions[:MAX_COVERED_MENTIONS]:
        about = admitted_set_bm25(" ".join(mention), texts, masks) if lexical_scope else {}
        candidates = [ref for ref in ranked
                      if records[ref]["content_relevance"] > 0.0 and about.get(ref, 0.0) > 0.0
                      and _mention_matched(mention, tokens.get(ref, frozenset()))]
        if not candidates:
            continue
        best_about = max(about[ref] for ref in candidates)
        if any(records[ref]["sufficient"] and about.get(ref, 0.0) >= COVERAGE_FRACTION * best_about
               and _mention_matched(mention, tokens.get(ref, frozenset()))
               and _names_mention(getattr(facts[ref], "fact_text", "") or "", mention) for ref in ranked):
            continue
        chosen = max(candidates, key=lambda ref: (about[ref], -position[ref]))
        if not records[chosen]["sufficient"]:
            records[chosen].update(sufficient=True, basis="entity_coverage")
        entities_added[chosen] = entities_added.get(chosen, 0) + 1
    # Lifecycle closure: a returned state must not travel without the admitted later state that
    # the runtime's guarded write-time evidence says changes it. Transitive; admitted only.
    successors = {ref: tuple(lifecycle_successors.get(ref, ())) for ref in ranked} if lifecycle_successors else {}
    admitted_set = set(ranked)
    closure_count = 0
    frontier = [ref for ref in ranked if records[ref]["sufficient"]]
    while frontier:
        following: list[str] = []
        for ref in frontier:
            for successor in successors.get(ref, ()):
                if successor in admitted_set and not records[successor]["sufficient"]:
                    records[successor].update(sufficient=True, basis="lifecycle_successor")
                    closure_count += 1
                    following.append(successor)
        frontier = following
    selected = [ref for ref in ranked if records[ref]["sufficient"]]
    # Per-fact explanation (2.3.0): the requirement served and the coverage contributed, in counts
    # of the caller's own query terms.
    seen: set[str] = set()
    for ref in ranked:
        record = records[ref]
        record["requirement"] = reading.shape
        record["query_terms_matched"] = len(matched[ref])
        record["query_terms_added"] = len(matched[ref] - seen)
        record["entities_added"] = entities_added.get(ref, 0)
        if record["sufficient"]:
            seen |= matched[ref]
    summary = {
        "lifecycle_successor_count": closure_count,
        "informative_query_term_count": len(evidence_terms),
        "relative_floor": relative_floor,
        "set_floor": set_floor,
        "frame_fallback": frame_fallback,
        "information_requirement": reading.to_dict(),
        "withheld_insufficient_count": len(ranked) - len(selected),
        "abstained": bool(ranked) and not selected,
    }
    return selected, records, summary


__all__ = [
    "FUNCTION_WORDS",
    "RANKED_PREFIX",
    "RELATIVE_FLOOR",
    "plural_answer",
    "SET_FLOOR_FACTOR",
    "RELEVANCE_SUFFICIENT",
    "RETURN_SELECTIONS",
    "SELECTION_BASIS",
    "SELECTION_POLICY_ID",
    "SELECTION_POLICY_VERSION",
    "informative_terms",
    "interpret_query",
    "normalize_contractions",
    "select_relevance_sufficient",
]
