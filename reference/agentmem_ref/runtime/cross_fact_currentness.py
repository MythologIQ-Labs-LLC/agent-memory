"""Bounded read-time guards for #671 cross-fact currentness.

This module deliberately contains no ranking or lifecycle authority. It only
validates whether persisted typed state-change evidence is assertive enough to
be considered by the explicit-current read path.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Mapping

ASSERTION_FILTER_REF = "cross_fact_assertion_filter"
ASSERTION_FILTER_VERSION = "6.0.0"

_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@&'+%-]*$")
_WORD_RE = re.compile(r"[A-Za-z0-9_'-]+")
_TEMPORAL_SUFFIX = ("now", "today", "currently", "anymore", "these days")

# Closed-class words are intentionally conservative. The value grammar below is
# the primary positive bound; this set prevents function-word tails from being
# laundered into a value.
_CLOSED_CLASS = frozenset(
    """
    a an the this that these those some any each every either neither both all
    another other others such what whatever which whichever who whoever whom whose
    i me my mine myself we us our ours ourselves you your yours yourself yourselves
    he him his himself she her hers herself it its itself they them their theirs themselves
    am is are was were be been being have has had having do does did doing
    can could shall should will would may might must ought
    and or but nor for so yet if unless whether assuming provided supposing though although even
    as than because since while when whenever where wherever before after until till once
    of at by for from in into on onto to toward towards with within without about above
    across against along amid among around behind below beneath beside besides between
    beyond during except inside near off outside over past per through throughout under underneath
    up upon via
    not no never nobody nothing neither nor
    here there now then today tomorrow yesterday currently anymore
    very too quite rather just only also still already again ever
    according said says told wrote stated heard source sources
    """.split()
)

_EPISTEMIC = frozenset(
    {
        "unverified", "unconfirmed", "unclear", "uncertain", "unsure", "perchance",
        "hypothetical", "supposed", "alleged", "purported", "rumored", "rumoured",
        "reputed", "disputed", "doubtful", "questionable", "presumed",
        "untrue", "false", "fake", "wrong", "dubious", "hearsay", "guessed",
        "reckoned", "bogus", "fabricated", "invented", "made-up", "mistaken",
    }
)

_UNITS = frozenset(
    """
    dollar dollars usd euro euros eur pound pounds gbp yen cent cents
    km kilometer kilometers kilometre kilometres mile miles m meter meters metre metres cm mm
    feet foot ft inch inches in kg kilogram kilograms g gram grams lb lbs ounce ounces oz
    second seconds minute minutes hour hours day days week weeks month months year years
    percent % point points item items people user users unit units
    """.split()
)

_PROPER_SUFFIX = frozenset(
    """
    City Town County Bay Beach Springs Falls Heights Park Valley Island
    Labs Lab Inc Corp Corporation Company Co LLC Ltd Group Bank University
    College School Hospital Systems Technologies Partners
    """.split()
)

_NEGATORS = frozenset({"not", "never", "no", "n't", "nobody", "nothing", "neither", "nor"})
_CONDITIONALS = frozenset({"if", "unless", "whether", "assuming", "provided", "supposing", "though", "although", "even"})
_ATTRIBUTION = frozenset(
    {
        "according", "per", "via", "reportedly", "allegedly", "rumor", "rumour",
        "heard", "told", "said", "says", "stated", "wrote", "claim", "claims",
        "tip", "spam", "forwarded", "supposedly", "unconfirmed", "apparently",
        "maybe", "might", "may", "perhaps", "possibly", "probably", "trust",
        "lol", "jk", "haha", "lmao", "kidding", "joke", "joking", "allegation",
        "source", "sources",
    }
)


def normalize_assertion_text(text: str) -> str:
    for char in ("\u2019", "\u2018", "\u02bc", "\uff07"):
        text = text.replace(char, "'")
    for char in ("\u201c", "\u201d"):
        text = text.replace(char, '"')
    return unicodedata.normalize("NFKC", text)


def _words(text: str) -> list[str]:
    return [token.casefold() for token in _WORD_RE.findall(text)]


def _one_sentence(text: str) -> bool:
    if "?" in text or "(" in text or ")" in text:
        return False
    if "—" in text or "–" in text or "--" in text or re.search(r"\w\s-\s\w", text):
        return False
    stripped = text.strip()
    if not stripped:
        return False
    body = stripped[:-1] if stripped[-1:] in {".", "!"} else stripped
    return not any(mark in body for mark in ".!")


def _first_change_marker(text: str, markers: list[str]) -> int | None:
    lowered = text.casefold()
    positions = []
    for marker in markers:
        pos = lowered.find(str(marker).casefold())
        if pos >= 0:
            positions.append(pos)
    return min(positions) if positions else None


def _possessive_prefix_ok(prefix: str, property_name: str) -> bool:
    prop = re.sub(r"[^a-z]", "", property_name.casefold())
    prop_head = prop[:4]
    # noun directly following a possessive owner must name the persisted property.
    pattern = re.compile(r"\b[A-Za-z0-9_]+(?:'s|s')\s+([A-Za-z][A-Za-z0-9_-]*)")
    for match in pattern.finditer(prefix):
        noun = re.sub(r"[^a-z]", "", match.group(1).casefold())
        if not prop_head or noun[:4] != prop_head:
            return False
    return True


def _value_shape_ok(value_span: str, persisted_value: str) -> bool:
    raw_tokens = value_span.strip().split()
    if not raw_tokens:
        return False
    if any(not _TOKEN_RE.match(token) for token in raw_tokens):
        return False

    lowered = [token.casefold() for token in raw_tokens]
    if any(token in _CLOSED_CLASS for token in lowered):
        return False
    if any(
        index > 0 and (token.endswith("ly") or token in _EPISTEMIC)
        for index, token in enumerate(lowered)
    ):
        return False
    if any(token in _EPISTEMIC for token in lowered):
        return False

    if len(raw_tokens) == 1:
        return True

    first = raw_tokens[0]
    if (any(ch.isdigit() for ch in first) or "_" in first):
        return len(raw_tokens) == 2 and lowered[1] in _UNITS

    if len(raw_tokens) == 2 and all(token[:1].isupper() for token in raw_tokens):
        return True
    if (
        len(raw_tokens) == 3
        and all(token[:1].isupper() for token in raw_tokens)
        and raw_tokens[-1] in _PROPER_SUFFIX
    ):
        return True

    # 6.0.0 deliberately removed the generic two-lowercase-token shape.
    return False


def _suffix_ok(suffix: str) -> bool:
    remaining = suffix.strip()
    if remaining[-1:] in {".", "!"}:
        remaining = remaining[:-1].strip()
    while remaining:
        matched = False
        lowered = remaining.casefold()
        for phrase in sorted(_TEMPORAL_SUFFIX, key=len, reverse=True):
            if lowered == phrase:
                return True
            if lowered.startswith(phrase + " "):
                remaining = remaining[len(phrase):].strip()
                matched = True
                break
        if not matched:
            return False
    return True


def assertion_filter_refusal(text: str, semantics: Mapping[str, Any]) -> str | None:
    """Return G12 refusal code, or None when the positive 6.0.0 grammar passes."""

    normalized = normalize_assertion_text(text)
    if not _one_sentence(normalized):
        return "change_evidence_not_assertive:1"

    proposition = semantics.get("proposition") or {}
    property_name = str(proposition.get("property") or "")
    persisted_value = str(proposition.get("value") or "")
    markers = [str(item) for item in (semantics.get("markers") or {}).get("change", ()) if item]
    marker_pos = _first_change_marker(normalized, markers)
    if marker_pos is None:
        # explicit-termination relations carry their marker in ended evidence.
        ended_markers = [str(item.get("marker") or "") for item in semantics.get("ended_values", ()) if item.get("marker")]
        marker_pos = _first_change_marker(normalized, ended_markers)
    if marker_pos is None:
        return "change_evidence_not_assertive:2"

    prefix = normalized[:marker_pos]
    # Quotes in a possessive apostrophe are handled by the possessive rule.
    if any(mark in prefix for mark in (",", ":", ";", '"')):
        return "change_evidence_not_assertive:2"
    if not _possessive_prefix_ok(prefix, property_name):
        return "change_evidence_not_assertive:2"

    if not persisted_value:
        return "change_evidence_not_assertive:3"
    value_pos = normalized.casefold().rfind(persisted_value.casefold())
    if value_pos < 0:
        return "change_evidence_not_assertive:3"
    value_span = normalized[value_pos : value_pos + len(persisted_value)]
    if not _value_shape_ok(value_span, persisted_value):
        return "change_evidence_not_assertive:4"

    suffix = normalized[value_pos + len(persisted_value) :]
    if not _suffix_ok(suffix):
        return "change_evidence_not_assertive:5"

    whole = normalized.casefold()
    whole_without_no_longer = re.sub(r"\bno\s+longer\b", " ", whole)
    words = _words(whole_without_no_longer)
    if any(word in _NEGATORS or word in _CONDITIONALS for word in words):
        return "change_evidence_not_assertive:6"

    # May followed by a digit is a month/date token, not the hedge modal.
    attribution_text = re.sub(r"\bMay(?=\s+\d)", "MayMonth", normalized)
    if any(word in _ATTRIBUTION for word in _words(attribution_text)):
        return "change_evidence_not_assertive:7"

    return None
