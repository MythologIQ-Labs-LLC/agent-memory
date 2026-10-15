"""Lexical normal forms and typo tolerance for recall (#819 C3 slice 2).

A remembered fact and the question about it rarely use the same word form ("weddings" /
"wedding", "attended" / "attend") and queries contain typos ("typsecript"). Exact-token matching
misses both. This module gives:

* ``normal_form``: the *inflectional* normal form of a lower-case token: Porter's (1980) step 1
  (plurals, ``-ed``/``-ing``, terminal ``y``), the standard deterministic inflection stage of
  English suffix stripping. Derivational steps (2-5) are deliberately not applied: they merge
  word families ("observability"/"observer", "preference"/"prefer") whose meanings differ, which
  turns morphology into false evidence. Tokens containing digits are left unchanged.
* ``typo_matches``: vocabulary terms one Damerau-Levenshtein edit away from a query term of at
  least ``TYPO_MIN_LENGTH`` characters (insertion, deletion, substitution or adjacent
  transposition). Without a lexicon every absent real word looks like a typo ("sending" is one
  edit from "spending"), so callers correct only when the query's topic matched nothing at all
  and it has at most ``TYPO_MAX_TOPICAL_TERMS`` topical terms, where one misspelling plausibly
  explains the miss (``typo_correction_allowed``).

Both are pure functions of their inputs. Nothing here reads memory, grants authority or
changes admission; callers decide which vocabulary is visible (current, eligible facts only).
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

NORMALIZATION_VERSION = "1.1.0"
TYPO_MIN_LENGTH = 5
TYPO_MAX_TOPICAL_TERMS = 3


def typo_correction_allowed(topical_term_count: int, any_topical_match: bool) -> bool:
    """Correct typos only for a short query whose topic matched nothing."""

    return 0 < topical_term_count <= TYPO_MAX_TOPICAL_TERMS and not any_topical_match

_VOWELS = frozenset("aeiou")


def _cons(word: str, i: int) -> bool:
    ch = word[i]
    if ch in _VOWELS:
        return False
    if ch == "y":
        return i == 0 or not _cons(word, i - 1)
    return True


def _measure(stem: str) -> int:
    """Porter's m: the number of VC sequences in ``stem``."""

    m, i, n = 0, 0, len(stem)
    while i < n and _cons(stem, i):
        i += 1
    while i < n:
        while i < n and not _cons(stem, i):
            i += 1
        if i >= n:
            break
        m += 1
        while i < n and _cons(stem, i):
            i += 1
    return m


def _has_vowel(stem: str) -> bool:
    return any(not _cons(stem, i) for i in range(len(stem)))


def _double_cons(word: str) -> bool:
    return len(word) >= 2 and word[-1] == word[-2] and _cons(word, len(word) - 1)


def _cvc(word: str) -> bool:
    if len(word) < 3:
        return False
    return (_cons(word, len(word) - 3) and not _cons(word, len(word) - 2) and _cons(word, len(word) - 1)
            and word[-1] not in "wxy")


def _replace(word: str, suffix: str, replacement: str, condition) -> tuple[str, bool]:
    if word.endswith(suffix):
        stem = word[: len(word) - len(suffix)]
        if condition(stem):
            return stem + replacement, True
        return word, True  # suffix matched: stop trying others in this step
    return word, False




@lru_cache(maxsize=65536)
def normal_form(token: str) -> str:
    """Inflectional normal form (Porter step 1) of an alphabetic token; others unchanged."""

    word = token.lower()
    if len(word) <= 2 or not word.isalpha():
        return word
    # Step 1a
    if word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("ies"):
        word = word[:-2]
    elif word.endswith("ss"):
        pass
    elif word.endswith("s"):
        word = word[:-1]
    # Step 1b
    if word.endswith("eed"):
        if _measure(word[:-3]) > 0:
            word = word[:-1]
    else:
        stripped = None
        for suffix in ("ed", "ing"):
            if word.endswith(suffix) and _has_vowel(word[: -len(suffix)]):
                stripped = word[: -len(suffix)]
                break
        if stripped is not None:
            word = stripped
            if word.endswith(("at", "bl", "iz")):
                word += "e"
            elif _double_cons(word) and word[-1] not in "lsz":
                word = word[:-1]
            elif _measure(word) == 1 and _cvc(word):
                word += "e"
    # Step 1c
    if word.endswith("y") and _has_vowel(word[:-1]):
        word = word[:-1] + "i"
    return word


def damerau_within_one(a: str, b: str) -> bool:
    """True when ``a`` and ``b`` differ by at most one insertion, deletion, substitution or
    adjacent transposition."""

    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = [i for i in range(la) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]
    if la > lb:
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def typo_matches(term: str, vocabulary: Iterable[str]) -> tuple[str, ...]:
    """Vocabulary terms within one edit of ``term`` (only for terms of ``TYPO_MIN_LENGTH``+)."""

    if len(term) < TYPO_MIN_LENGTH or not term.isalpha():
        return ()
    return tuple(sorted(v for v in vocabulary
                        if v != term and v.isalpha() and abs(len(v) - len(term)) <= 1 and damerau_within_one(term, v)))


_TOKEN = re.compile(r"[a-z0-9]+")
MAX_EXPANSIONS_PER_TERM = 8


def _key(token: str) -> str:
    core = "".join(_TOKEN.findall(token))
    return normal_form(core) if core.isalpha() else core


def expansion_terms(query_tokens: Iterable[str], vocabulary: Iterable[str], allow_typos: bool = True) -> dict:
    """Vocabulary surface forms to add to a discovery query, and what produced them.

    ``query_tokens`` and ``vocabulary`` are tokens in the lexical route's own tokenisation. For
    each query token: every vocabulary form sharing its normal form
    (``weddings`` -> ``wedding``); and, when no vocabulary form shares it, the forms one edit
    away (``typsecript`` -> ``typescript``) and their normal-form siblings. At most
    ``MAX_EXPANSIONS_PER_TERM`` forms are added per query token.
    """

    vocabulary = set(vocabulary)
    by_key: dict[str, set[str]] = {}
    for token in vocabulary:
        by_key.setdefault(_key(token), set()).add(token)
    alpha = sorted(v for v in vocabulary if v.isalpha())
    morphological: set[str] = set()
    typo: set[str] = set()
    for token in dict.fromkeys(query_tokens):
        core = "".join(_TOKEN.findall(token))
        if not core:
            continue
        key = _key(token)
        siblings = set(by_key.get(key, ())) - {token}
        if key in by_key:
            morphological.update(sorted(siblings)[:MAX_EXPANSIONS_PER_TERM])
            continue
        if not allow_typos:
            continue
        found: set[str] = set()
        for match in typo_matches(core, alpha):
            found.update(by_key.get(_key(match), {match}))
        typo.update(sorted(found)[:MAX_EXPANSIONS_PER_TERM])
    return {"morphological": tuple(sorted(morphological)), "typo": tuple(sorted(typo - morphological))}


def normalized_text(text: str) -> str:
    """``text`` with every ``[a-z0-9]+`` token replaced by its normal form."""

    return " ".join(normal_form(token) for token in _TOKEN.findall(text.lower()))


__all__ = ["MAX_EXPANSIONS_PER_TERM", "NORMALIZATION_VERSION", "TYPO_MAX_TOPICAL_TERMS", "TYPO_MIN_LENGTH",
           "damerau_within_one", "expansion_terms", "normal_form", "normalized_text", "typo_correction_allowed",
           "typo_matches"]
