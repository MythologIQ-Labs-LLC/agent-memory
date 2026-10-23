"""Content terms: the one bounded lexical definition shared by admission and selection (#819).

A token is a *content term* when it is not one of a bounded list of English function words
(grammatical glue: articles, pronouns, auxiliaries, prepositions, conjunctions, question words;
no nouns, no domain or benchmark vocabulary), compared after a bounded, deterministic morphology
fold (possessive, plural, ``-ing``/``-ed``, final ``-e``). Moved verbatim from
``api.context_selection`` (selector policy 0.5.x) so that the experimental content-term lexical
admission (``runtime.adapter``) and the selector agree on what a shared content term is.
"""

from __future__ import annotations

import re

_WORD = re.compile(r"[^\W_]+(?:'[^\W_]+)?", re.UNICODE)
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
