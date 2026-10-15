"""Deterministic query interpretation for evidence selection (#819 C3).

What a recall query asks for has three parts that lexical relevance must not conflate:

* **Topic**: the words that say what the memory is about ("charity", "museum", "Kubernetes").
* **Frame**: the words that say what shape of answer is wanted and when ("how *many*",
  "in *total*", "*last* *month*", "*currently*"). A memory that merely contains "many" or
  "month" is not about the question's topic; counting such words as topical evidence lets
  incidental matches set the relevance scale and push real evidence below it.
* **Information requirement**: a single answer, an aggregate over several items ("how many",
  "total", "all", "list"), or a relation between items ("before", "since", "older than",
  "between"). Aggregate and relational questions need several pieces of evidence, each of
  which may be a weak standalone match.

It also finds **entity mentions**: names the query writes as names (capitalised mid-sentence,
acronyms, CamelCase, letter-digit tokens such as ``k8s``, quoted spans). A question naming
several entities needs evidence about each of them.

Everything here is a closed, documented English vocabulary or an orthographic rule. Nothing
names a domain, dataset, benchmark or expected answer. The interpretation is evidence for
selection only; it never grants authority, changes admission or reorders ranking.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

INTERPRETER_VERSION = "1.0.0"

SINGLE = "single"
AGGREGATE = "aggregate"
RELATIONAL = "relational"

# Frame vocabulary: quantity and aggregation, time units and temporal framing, and generic
# request words. These describe the requested answer, not the remembered topic. When a query
# has no topical term left, its frame terms are used as topic (nothing is thrown away).
FRAME_WORDS = frozenset("""
all many much total totals amount amounts number numbers count sum overall altogether combined
average percent percentage ratio times often several few various different multiple most
least more less fewer
second seconds minute minutes hour hours day days week weeks weekend weekends month months
year years today yesterday tomorrow tonight ago last past previous previously recent recently
lately current currently now nowadays since earliest latest earlier later typical typically
usually normally long
tell remind remember recall mention mentioned told said know knew thing things stuff
something anything everything
""".split())

_AGGREGATE_CUES = (
    r"how many", r"how much", r"in total", r"total", r"all", r"every", r"each", r"list",
    r"how often", r"number of", r"count", r"different", r"altogether", r"combined", r"average",
    r"times", r"so far",
)
# Choice between alternatives ("X versus Y", "X or Y") is not a multi-evidence relation: a single
# preference or decision usually answers it, so "versus"/"vs"/"or" are not cues.
_RELATIONAL_CUES = (
    r"between", r"compar\w*", r"difference", r"than", r"before", r"after",
    r"since", r"ago", r"how long", r"first", r"last", r"earlier", r"later", r"older", r"younger",
    r"percentage", r"ratio", r"which came", r"in what order",
)
_AGGREGATE_RE = re.compile(r"\b(" + "|".join(_AGGREGATE_CUES) + r")\b")
_RELATIONAL_RE = re.compile(r"\b(" + "|".join(_RELATIONAL_CUES) + r")\b")
_QUOTED = re.compile(r"[\"“‘']([^\"”’']{3,120})[\"”’']")


@dataclass(frozen=True)
class QueryInterpretation:
    topical_terms: tuple[str, ...]
    frame_terms: tuple[str, ...]
    entity_mentions: tuple[tuple[str, ...], ...]
    shape: str
    cues: tuple[str, ...] = field(default=())
    version: str = INTERPRETER_VERSION

    @property
    def needs_several(self) -> bool:
        return self.shape in (AGGREGATE, RELATIONAL)

    def to_dict(self) -> dict:
        return {
            "interpreter_version": self.version,
            "shape": self.shape,
            "cues": list(self.cues),
            "topical_term_count": len(self.topical_terms),
            "frame_term_count": len(self.frame_terms),
            "entity_mention_count": len(self.entity_mentions),
            "authority_effect": "none",
        }


_SENTENCE_END = frozenset(".!?:;")
_OPENERS = frozenset("\"\u201c(")


def starts_sentence(text: str, position: int) -> bool:
    """Whether ``text[:position]`` matches ``(^|[.!?:;]\\s+|["\u201c(]\\s*)$``: nothing before, a
    sentence end and whitespace, or an opening quote or parenthesis. Linear overall: it reads
    only the whitespace run before ``position`` (the regex re-scanned the whole prefix per
    word, which made interpretation quadratic in query length)."""

    # ``$`` also matches before a final newline; reproduce that so behaviour is unchanged.
    if position > 0 and text[position - 1] == "\n" and _sentence_boundary(text, position - 1):
        return True
    return _sentence_boundary(text, position)


def _sentence_boundary(text: str, position: int) -> bool:
    if position == 0:
        return True
    end = position
    while end > 0 and text[end - 1].isspace():
        end -= 1
    if end == 0:
        return False
    previous = text[end - 1]
    return (previous in _SENTENCE_END and end < position) or previous in _OPENERS


_NEVER_NAMES = frozenset({"i", "not", "no", "never", "nor"})  # emphasis ("I do NOT want"), not names


def _is_name_token(text: str, match: re.Match, case_informative: bool, sentence_start) -> bool:
    token = match.group(0)
    if token.lower() in _NEVER_NAMES:
        return False
    if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
        return True  # k8s, v2, b12
    if not case_informative:
        return False
    if len(token) > 1 and token.isupper():
        return True  # GHA, DLQ, US
    if any(c.isupper() for c in token[1:]) and any(c.islower() for c in token):
        return True  # ReactJS, TypeScript, GitHub
    return token[0].isupper() and not starts_sentence(text, match.start())


def interpret(query: str, *, function_words: frozenset, normalize, word_re, sentence_start) -> QueryInterpretation:
    """Interpret ``query``. The tokenisation helpers come from ``return_selection``."""

    text = normalize(query)
    lowered = text.lower()
    inner = [m.group(0) for m in word_re.finditer(text)
             if m.group(0)[0].isalpha() and m.group(0).lower() != "i"
             and not starts_sentence(text, m.start())]
    capitalised = sum(1 for word in inner if word[0].isupper())
    case_informative = any(c.islower() for c in text) and capitalised * 2 <= len(inner)

    topical: set[str] = set()
    frame: set[str] = set()
    mentions: list[tuple[str, ...]] = []
    for match in word_re.finditer(text):
        term = match.group(0).lower()
        name = _is_name_token(text, match, case_informative, sentence_start)
        if term in function_words and not name:
            continue
        if term in FRAME_WORDS and not name:
            frame.add(term)
        else:
            topical.add(term)
        if name:
            # One name token per mention: adjacent names may be one entity ("GitHub Actions")
            # or two ("MongoDB TypeScript"); a fact covering both covers either reading.
            mentions.append((term,))
    for quoted in _QUOTED.finditer(text):
        words = tuple(dict.fromkeys(
            w.lower() for w in word_re.findall(quoted.group(1))
            if w.lower() not in function_words and w.lower() not in FRAME_WORDS
        ))
        if words:
            mentions.append(words)
            topical.update(words)

    aggregate = sorted({m.group(1) for m in _AGGREGATE_RE.finditer(lowered)})
    relational = sorted({m.group(1) for m in _RELATIONAL_RE.finditer(lowered)})
    shape = AGGREGATE if aggregate else RELATIONAL if relational else SINGLE
    return QueryInterpretation(
        topical_terms=tuple(sorted(topical)),
        frame_terms=tuple(sorted(frame - topical)),
        entity_mentions=tuple(dict.fromkeys(mentions)),
        shape=shape,
        cues=tuple(aggregate + relational),
    )


__all__ = ["AGGREGATE", "FRAME_WORDS", "INTERPRETER_VERSION", "QueryInterpretation", "RELATIONAL", "SINGLE", "interpret"]
