"""Write-time proposition identity, cardinality, and temporal self-description (#550).

A bounded, deterministic, versioned interpreter reads one memory write and emits
typed *evidence*:

* clause-level proposition candidates (entity, property, value, polarity);
* a proposition identity for the write: ``known`` / ``unknown`` / ``ambiguous``;
* cardinality evidence: ``single_valued`` / ``multi_valued`` / ``hierarchical`` /
  ``unknown`` (``unknown`` by default; there is no property ontology);
* change, coexistence, hedge, and self-claim markers found in the text;
* temporal aspect (present / prospective / past habitual) scoped to the principal
  proposition (1.1.0, #598): cues inside questions, requests, subordinate clauses,
  discourse markers, passive or motion idioms, or clauses other than the known
  proposition's are declined with a typed reason, and mixed regimes stay unknown;
* anchored temporal self-description (``for the next two weeks``, ``starting next
  month``) resolved only against a caller-declared ``observed_at`` anchor.

A second, separate step classifies the write against retained current memories that
occupy the same proposition slot (``same_value`` / ``coexistence`` /
``state_change_candidate`` / ``conflict`` / ``unresolved``) and, only for an explicit,
unhedged change of a same-slot memory, prepares a governed ``state_change`` proposal
for the existing correction lifecycle (#549).

Nothing here is authority::

    interpretation != authority          classifier confidence != truth
    proposition match != authority to replace
    single-valued candidate != automatic supersession
    conflict detection != mutation       proposal != application

Every output carries ``authority_effect: none``. A proposal is applied only by an
explicit caller through ``AgentMemory.correct(..., replacement_kind="state_change")``
under ordinary PAMA. Caller-declared temporal metadata always outranks interpreted
self-validity, which is never reported as a caller-declared basis. Text that claims
authority, verification, currentness, or supersession for itself is recorded as a
self-claim and makes the write ineligible to originate any proposal.

The interpretation is computed once at write and persisted with the fact, so a later
interpreter version never silently reinterprets a historical write. Facts written
before this interpreter carry no interpretation and are treated as ``unknown``.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence

from .temporal_intent import parse_time

INTERPRETER_REF = "agent-memory-deterministic-write-semantics"
INTERPRETER_VERSION = "1.2.0"
WRITE_SEMANTICS_KEY = "write_semantics"
CLASSIFIER_VERSION = "1.0.0"
# Classifier 1.1.0 (#732 R3) classifies only a write that carries a typed proposition; every
# other write keeps 1.0.0 and its persisted version tag, so its stored bytes are unchanged.
TYPED_CLASSIFIER_VERSION = "1.1.0"
TYPED_KEYS = ("typed_proposition", "typed_ineligible_reasons", "extraction")
MAX_CLAUSES = 4  # persisted clause evidence is bounded; clause_count records the total
MAX_RELATIONS = 8  # persisted relations per write are bounded; relation_count records the total
_RELATION_PRIORITY = {"state_change_candidate": 0, "conflict": 1, "same_value": 2, "coexistence": 3, "unresolved": 4}

KNOWN, UNKNOWN, AMBIGUOUS = "known", "unknown", "ambiguous"
SINGLE_VALUED, MULTI_VALUED, HIERARCHICAL = "single_valued", "multi_valued", "hierarchical"
CARDINALITIES = (SINGLE_VALUED, MULTI_VALUED, HIERARCHICAL, UNKNOWN)
AFFIRMED, ENDED, NEGATED, PAST = "affirmed", "ended", "negated", "past"

SAME_VALUE = "same_value"
COEXISTENCE = "coexistence"
STATE_CHANGE_CANDIDATE = "state_change_candidate"
CONFLICT = "conflict"
UNRESOLVED = "unresolved"
CLASSIFICATIONS = (SAME_VALUE, COEXISTENCE, STATE_CHANGE_CANDIDATE, CONFLICT, UNRESOLVED)

# Generic English function-word vocabulary. None of it names a domain property.
_AUX = {"is", "are", "was", "were", "am", "be", "been", "has", "have", "had", "does", "do", "did",
        "will", "would", "shall", "should", "can", "could", "may", "might", "must"}
_MODALS = {"will", "would", "shall", "should", "can", "could", "may", "might", "must"}
_PREPOSITIONS = {"in", "at", "on", "for", "with", "to", "from", "as", "of", "into", "near", "by", "under", "over"}
_DETERMINERS = {"the", "my", "our", "their", "his", "her", "its", "your", "this", "that", "these", "those"}
_PRONOUNS = {"i": "speaker", "we": "speaker_group", "he": None, "she": None, "they": None}
_LEADING_ADVERBS = ("by the way", "actually", "currently", "now", "also", "still", "then", "today",
                    "these days", "nowadays", "at the moment", "presently")
_TRAILING_ADVERBS = ("now", "currently", "anymore", "any more", "too", "as well", "again", "today",
                     "these days", "nowadays", "at the moment", "at some point", "maybe", "perhaps",
                     "probably", "possibly")
_MID_ADVERBS = {"also", "currently", "now", "still", "always", "already", "just", "really", "actually",
                "presently", "usually", "often", "sometimes", "again", "then",
                "maybe", "perhaps", "probably", "possibly", "likely"}
# Leading noun-phrase qualifiers that describe recency or revision, not the entity:
# "the updated project budget" names the same slot as "the project budget".
_NP_QUALIFIERS = {"updated", "revised", "new", "latest", "current", "corrected"}
_REVISION_QUALIFIERS = {"updated", "revised", "corrected"}
# Words that open a new clause after "and": adverbs, subject pronouns, determiners.
_CLAUSE_OPENERS = _MID_ADVERBS | {"he", "she", "they", "i", "we", "the", "my", "our", "their", "his", "her"}
_CONTRACTIONS = (("i'm", "i am"), ("we're", "we are"), ("they're", "they are"), ("you're", "you are"),
                 ("doesn't", "does not"), ("don't", "do not"), ("didn't", "did not"), ("isn't", "is not"),
                 ("aren't", "are not"), ("wasn't", "was not"), ("weren't", "were not"), ("can't", "can not"),
                 ("won't", "will not"), ("i've", "i have"), ("we've", "we have"), ("they've", "they have"))
_COEXISTENCE = ("also", "as well", "too", "in addition", "additionally", "another", "both")
_REPLACEMENT_VERBS = ("moved", "switched", "changed", "relocated", "transferred", "replaced")
_HEDGES = ("might", "may", "maybe", "perhaps", "possibly", "probably", "likely", "could",
           "i think", "i guess", "i believe", "not sure", "unsure", "at some point", "hopefully")
_SELF_CLAIMS = {
    "authority": r"\b(authoritative|authority|official|override|overrides|system override)\b",
    "verification": r"\b(verified|confirmed as true|certified)\b",
    "supersession": r"\b(supersedes?|superseded|replaces all|overrides? (all|every))\b",
    "currentness": r"\b(this (memory|note|record|fact) is (the )?(current|latest|valid))\b|\b(is|are) current;",
    "instruction": r"\b(ignore (all )?(previous|prior)|mark this as|treat this as|you must)\b",
}
# Temporal aspect the memory asserts about itself. Recorded as typed evidence even when no
# proposition parses, so a memory's own "currently" is carried by type rather than only by
# lexical overlap (#583). Evidence only: never a validity window, never currentness.
_ASPECT_CUES = {
    "present": ("currently", "right now", "at the moment", "these days", "nowadays", "presently", "at present",
                "as of now", "now"),
    "prospective": ("planning to", "plan to", "going to", "intend to", "will", "next week", "next month",
                    "next year", "tomorrow", "upcoming", "soon"),
    "past_habitual": ("used to", "no longer", "not anymore", "previously", "formerly"),
}
# Aspect scope (interpreter 1.1.0, #598). A cue describes the memory only when it sits in
# asserted speaker content that belongs to the principal proposition. Bounded, deterministic
# declines; when scope cannot be established the regime is left unknown rather than guessed.
_ASPECT_CUE_RE = {cue: re.compile(r"(?<![a-z0-9])" + re.escape(cue) + r"(?![a-z0-9])")
                  for cues in _ASPECT_CUES.values() for cue in cues}
_ASPECT_REGIME = {cue: name for name, cues in _ASPECT_CUES.items() for cue in cues}
_DISCOURSE_FILLERS = {"so", "ok", "okay", "well", "also", "and", "but", "then", "yes", "yeah", "wow", "great",
                      "thanks", "hmm", "hmmm", "oh", "honestly", "actually"}
_REQUEST_OPENERS = {"please", "let's", "lets", "tell", "explain", "give", "write", "create", "describe", "list",
                    "limit", "include", "make", "show", "provide", "suggest", "summarize", "summarise", "rewrite",
                    "re-write", "generate", "draft", "imagine", "feel", "help", "find", "compare", "recommend",
                    "translate", "pretend", "continue", "what", "what's", "how", "how's", "why", "which"}
_REQUEST_PAIRS = {("let", "us")} | {(aux, "you") for aux in ("can", "could", "would", "will", "do", "does", "did",
                                                            "are", "should")} | {
    (aux, "there") for aux in ("is", "are", "do", "does", "should")}
# Indirect requests that open the interrogative part of a question sentence.
_INDIRECT_REQUESTS = ("i was wondering", "i am wondering", "i wonder", "i was hoping", "i am hoping",
                      "do you know", "any idea", "any ideas", "any suggestions", "any recommendations", "any tips")
# Segment boundaries inside one clause piece: a comma, or a coordinating conjunction.
_SEGMENT_BOUNDARY = re.compile(r",\s*|\s+(?:and|but|so)\s+")
# Words that open a clause subordinate to the one the cue would otherwise describe
# (relative, causal, conditional, concessive). "when"/"while" are deliberately absent.
_SUBORDINATORS = {"that", "which", "who", "whom", "whose", "because", "since", "if", "whether", "although",
                  "though", "unless", "whereas", "especially"}
_PASSIVE_HEADS = {"is", "are", "was", "were", "be", "been", "being", "am", "get", "gets", "got", "getting",
                  "become", "becomes", "became", "becoming"}
_DEGREE_WORDS = {"really", "so", "very", "quite", "pretty", "still", "finally"}
_HABITUAL_GOING = {"start", "started", "starting", "starts", "begin", "began", "begun", "beginning", "begins",
                   "continue", "continued", "continues", "continuing", "keep", "kept", "keeps", "keeping", "stop",
                   "stopped", "stopping", "stops", "quit", "quits", "quitting", "resume", "resumed", "resumes",
                   "resuming", "enjoy", "enjoyed", "like", "liked", "love", "loved", "hate", "hated", "avoid",
                   "avoided", "try", "tried", "trying", "miss", "missed", "finish", "finished", "been", "was",
                   "were"}
_MOTION_DESTINATIONS = {"the", "a", "an", "my", "your", "his", "her", "its", "our", "their", "this", "that",
                        "these", "those", "some", "school", "church", "work", "bed", "class", "college", "therapy",
                        "practice", "lunch", "dinner", "breakfast", "yoga", "gym"}
_SELF_REFERENCE = re.compile(r"^(this|the) (memory|note|record|fact|entry)\b")

_NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                 "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
_UNIT = r"(day|week|month|year)s?"
_INTERVAL = re.compile(r"\bfor the next (\d{1,3}|" + "|".join(_NUMBER_WORDS) + r")\s+" + _UNIT + r"\b")
_START_REL = re.compile(r"\b(?:starting|beginning|from|effective)\s+(tomorrow|next (?:week|month|year))\b")
_START_ISO = re.compile(r"\b(?:starting|beginning|from|effective)(?: on)?\s+(\d{4}-\d{2}-\d{2})\b")
_UNTIL_REL = re.compile(r"\buntil (tomorrow|next (?:week|month|year)|the end of (?:the|this) (?:week|month|year))\b")
_UNTIL_ISO = re.compile(r"\b(?:until|through)\s+(\d{4}-\d{2}-\d{2})\b")

_WORD = re.compile(r"[a-z0-9][a-z0-9'\-.]*")


_CONTRACTION_RE = re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(short) for short, _ in _CONTRACTIONS) + r")(?![a-z0-9])")
_CONTRACTION_MAP = dict(_CONTRACTIONS)


def _norm(text: str) -> str:
    lowered = " ".join(text.lower().replace("\u2019", "'").split())
    return _CONTRACTION_RE.sub(lambda match: _CONTRACTION_MAP[match.group(1)], lowered)


def _norm_value(value: str) -> str:
    words = [w.strip(".,;:!?\"()") for w in _norm(value).split()]
    words = [w for w in words if w]
    while words and words[0] in {"the", "a", "an"}:
        words = words[1:]
    return " ".join(words)


def _contains(text: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", text) is not None


def _strip_edges(words: list[str], phrases: Sequence[str], *, leading: bool, found: list[str]) -> list[str]:
    changed = True
    while changed and words:
        changed = False
        for phrase in sorted(phrases, key=lambda p: -len(p.split())):
            parts = phrase.split()
            window = words[: len(parts)] if leading else words[-len(parts):]
            if [w.strip(",.;:") for w in window] == parts:
                found.append(phrase)
                words = words[len(parts):] if leading else words[: -len(parts)]
                changed = True
                break
    return words


def _lemma(verb: str) -> str:
    verb = verb.strip(",.;:")
    if verb.endswith("ies") and len(verb) > 4:
        return verb[:-3] + "y"
    if re.search(r"(ss|sh|ch|x|z|o)es$", verb):
        return verb[:-2]
    if verb.endswith("s") and not verb.endswith("ss") and len(verb) > 2:
        return verb[:-1]
    return verb


def _stem(verb: str) -> str:
    """Inflection-insensitive verb key: lives/living/live -> liv, prefers/preferring -> prefer."""

    verb = _lemma(verb)
    if verb.endswith("ing") and len(verb) > 5:
        verb = verb[:-3]
    if verb.endswith("ed") and len(verb) > 4:
        verb = verb[:-2]
    if len(verb) > 3 and verb[-1] == verb[-2] and verb[-1] not in "aeiousl":
        verb = verb[:-1]
    if verb.endswith("e") and len(verb) > 3:
        verb = verb[:-1]
    return verb


def _is_finite_verb(words: list[str], index: int) -> bool:
    word = words[index].strip(",.;:")
    if word in _AUX or word in {"used", "no", "not", "never"} or word in _MID_ADVERBS:
        return True
    if word.endswith("ed") and len(word) > 4 and index >= 2:
        # Simple past after a noun ("the user changed jobs"); a participle *before* the
        # head noun ("the updated budget") sits at index 1 and stays a qualifier.
        return True
    if "'" in word or word.endswith("ss") or len(word) < 3 or not word.endswith("s"):
        return False
    following = words[index + 1].strip(",.;:") if index + 1 < len(words) else ""
    return following not in _AUX


# --------------------------------------------------------------------------- clauses


def _separate_trailing_request(piece: str) -> tuple[str, ...]:
    """A comma plus an explicit grammatical request opens a separate discourse act.

    Ordinary lists and conjoined assertions are never split by this rule.
    This is punctuation/syntax evidence only, never semantic truth or authority.
    """
    for boundary in re.finditer(r",\s*(?:and\s+)?|\s+and\s+", piece, flags=re.IGNORECASE):
        prefix = piece[:boundary.start()].strip()
        # Syntactic request markers inside quoted content are data, not new
        # discourse acts. Apostrophes in contractions are not quote delimiters.
        if prefix.count('"') % 2 or prefix.count("“") > prefix.count("”"):
            continue
        suffix = piece[boundary.end():].strip()
        if suffix and _opens_question(_norm(suffix).split()):
            return tuple(part for part in (prefix, suffix) if part)
    return (piece,)


def _clause_pieces(text: str) -> list[tuple[str, int, bool]]:
    """Clause pieces with their sentence number and whether that sentence ends in ``?``."""

    parts: list[tuple[str, int, bool]] = []
    for number, sentence in enumerate(re.split(r"(?<=[.!?])\s+|;\s*|:\s+", text)):
        question = sentence.rstrip().rstrip("\"')]}*\u201d\u2019").endswith("?")
        for piece in re.split(r",?\s+but\s+|,?\s+and\s+(?=(?:" + "|".join(sorted(_CLAUSE_OPENERS)) + r")\b)", sentence):
            for bounded in _separate_trailing_request(piece):
                bounded = bounded.strip(" ,.!?")
                if bounded:
                    parts.append((bounded, number, question))
    return parts


def _split_clauses(text: str) -> list[str]:
    return [piece for piece, _, _ in _clause_pieces(text)]


def _subject(words: list[str]) -> tuple[str | None, int, str]:
    """(entity, index of the first predicate word, subject kind)."""

    if not words:
        return None, 0, "none"
    first = words[0]
    if first == "user":
        return "user", 1, "noun"
    if first in _PRONOUNS:
        return _PRONOUNS[first], 1, "pronoun"
    if first in _DETERMINERS:
        for index in range(2, min(len(words), 7)):
            if _is_finite_verb(words, index):
                qualifiers = [w.strip(",.;:") for w in words[1:index]]
                while len(qualifiers) > 1 and qualifiers[0] in _NP_QUALIFIERS:
                    qualifiers = qualifiers[1:]
                phrase = " ".join(qualifiers)
                owner = {"my": "speaker", "our": "speaker_group"}.get(first)
                return (f"{owner}'s {phrase}" if owner else phrase), index, "noun"
        return None, 0, "none"
    return None, 0, "none"


def _skip_adverbs(words: list[str], markers: list[str]) -> list[str]:
    words = _strip_edges(words, _LEADING_ADVERBS, leading=True, found=markers)
    while words and words[0].strip(",") in _MID_ADVERBS:
        markers.append(words[0].strip(","))
        words = words[1:]
    return words


def _clause(entity, prop, value, polarity, kind, modal, markers, raw) -> dict[str, Any]:
    if polarity == NEGATED and ("anymore" in markers or "any more" in markers):
        polarity = ENDED
        markers = [*markers, "not anymore"]
    if entity and "'s " in f"{entity} ":
        # Possessive subject: "the user's role is X" -> entity user, property "role be".
        owner, _, attribute = entity.partition("'s ")
        if attribute:
            entity, prop = owner, f"{attribute} {prop}"
    return {"entity": entity, "property": prop if entity else None, "value": value or None, "polarity": polarity,
            "subject": kind, "modal": modal, "markers": markers, "span": raw}


def _parse_clause(raw: str, antecedent: str | None) -> dict[str, Any] | None:
    markers: list[str] = []
    words = _skip_adverbs(_norm(raw).split(), markers)
    entity, index, kind = _subject(words)
    if kind == "noun" and index > 1:
        markers.extend(w.strip(",.;:") for w in words[1:index] if w.strip(",.;:") in _REVISION_QUALIFIERS)
    if kind == "none" and antecedent is not None and words and _is_finite_verb(words, 0):
        entity, index, kind = antecedent, 0, "inherited"
    if kind == "none":
        return None
    if kind == "pronoun" and entity is None:
        entity = antecedent
        kind = "coreferent" if antecedent else "unresolved_pronoun"
    rest = _skip_adverbs(words[index:], markers)
    polarity = AFFIRMED
    if rest[:2] == ["no", "longer"]:
        polarity, rest = ENDED, rest[2:]
        markers.append("no longer")
    elif rest[:2] == ["used", "to"]:
        polarity, rest = ENDED, rest[2:]
        markers.append("used to")
    modal, auxiliaries = None, []
    while rest and rest[0].strip(",") in _AUX and not (rest[0] == "may" and len(rest) > 1 and rest[1][:1].isdigit()):
        auxiliaries.append(rest[0].strip(","))
        head = rest[0].strip(",")
        if head in _MODALS:
            modal = head
        rest = _skip_adverbs(rest[1:], markers)
        if rest[:1] in (["not"], ["never"]):
            polarity, rest = NEGATED, _skip_adverbs(rest[1:], markers)
        if head in {"is", "are", "am", "was", "were"}:
            nxt = rest[0].strip(",") if rest else ""
            month = nxt == "may" and len(rest) > 1 and rest[1][:1].isdigit()
            if nxt.endswith("ing") or nxt in {"scheduled", "going", "planning"} or (nxt in _AUX and not month):
                continue
            value = _norm_value(" ".join(_strip_edges(rest, _TRAILING_ADVERBS, leading=False, found=markers)))
            return _clause(entity, "be", value, PAST if head in {"was", "were"} and polarity == AFFIRMED else polarity,
                           kind, modal, markers, raw)
    if not rest:
        return None
    verb = rest[0].strip(",.;:")
    tail = rest[1:]
    if verb in _REPLACEMENT_VERBS:
        markers.append(verb)
        if verb in {"changed", "switched"} and tail[:1] == ["to"]:
            # "X has changed/switched to Y" states X's new value: the slot is X's state.
            value = _norm_value(" ".join(_strip_edges(tail[1:], _TRAILING_ADVERBS, leading=False, found=markers)))
            return _clause(entity, "be", value, polarity, kind, modal, markers, raw)
    if polarity == AFFIRMED and verb.endswith("ed") and not auxiliaries:
        # Simple past ("I lived in Maryland") is not a present-state proposition.
        polarity = PAST
    prop = _stem(verb)
    if tail and tail[0].strip(",") in _PREPOSITIONS:
        prop = f"{prop} {tail[0].strip(',')}"
        tail = tail[1:]
    value = _norm_value(" ".join(_strip_edges(tail, _TRAILING_ADVERBS, leading=False, found=markers)))
    return _clause(entity, prop, value, polarity, kind, modal, markers, raw)


# --------------------------------------------------------------------------- self-validity


def _utc(seconds: float) -> datetime:
    return datetime.fromtimestamp(seconds, tz=timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _add_months(moment: datetime, months: int) -> datetime:
    month = moment.month - 1 + months
    year, month = moment.year + month // 12, month % 12 + 1
    day = min(moment.day, calendar.monthrange(year, month)[1])
    return moment.replace(year=year, month=month, day=day)


def _start_of(unit: str, anchor: datetime) -> datetime:
    day = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
    if unit == "tomorrow":
        return day + timedelta(days=1)
    if unit == "next week":
        return day + timedelta(days=7 - day.weekday())
    if unit == "next month":
        return _add_months(day.replace(day=1), 1)
    if unit == "next year":
        return day.replace(year=day.year + 1, month=1, day=1)
    raise ValueError(unit)


def _end_of_current(unit: str, anchor: datetime) -> datetime:
    return _start_of(f"next {unit}", anchor)


def _resolve_self_validity(lowered: str, anchor: Mapping[str, Any] | None, hedged: bool,
                           declared: Mapping[str, Any] | None) -> dict[str, Any]:
    found: list[tuple[str, str, str]] = []  # (kind, expression, argument)
    for match in _INTERVAL.finditer(lowered):
        found.append(("interval", match.group(0), f"{match.group(1)} {match.group(2)}"))
    for match in _START_REL.finditer(lowered):
        found.append(("start", match.group(0), match.group(1)))
    for match in _START_ISO.finditer(lowered):
        found.append(("start_iso", match.group(0), match.group(1)))
    for match in _UNTIL_REL.finditer(lowered):
        found.append(("until", match.group(0), match.group(1)))
    for match in _UNTIL_ISO.finditer(lowered):
        found.append(("until_iso", match.group(0), match.group(1)))
    if not found:
        return {"status": "none"}
    record: dict[str, Any] = {"basis": "interpreted", "expressions": [expr for _, expr, _ in found],
                              "valid_from": None, "valid_until": None, "anchor": None}
    if declared and (declared.get("valid_from") or declared.get("valid_until")):
        return {**record, "status": "superseded_by_caller_declared"}
    if hedged:
        return {**record, "status": "hedged_not_resolved"}
    starts = [item for item in found if item[0] in {"interval", "start", "start_iso"}]
    ends = [item for item in found if item[0] in {"until", "until_iso"}]
    if len(starts) > 1 or len(ends) > 1 or (ends and starts and starts[0][0] == "interval"):
        return {**record, "status": "ambiguous"}
    needs_anchor = any(kind in {"interval", "start", "until"} for kind, _, _ in found)
    anchor_seconds = parse_time(anchor.get("value")) if anchor else None
    if needs_anchor and anchor_seconds is None:
        return {**record, "status": "unanchored"}
    base = _utc(anchor_seconds) if anchor_seconds is not None else None
    valid_from = valid_until = None
    for kind, _, argument in found:
        if kind == "interval":
            count_text, unit = argument.split()
            count = int(count_text) if count_text.isdigit() else _NUMBER_WORDS[count_text]
            valid_from = base
            if unit.startswith("day"):
                valid_until = base + timedelta(days=count)
            elif unit.startswith("week"):
                valid_until = base + timedelta(days=7 * count)
            elif unit.startswith("month"):
                valid_until = _add_months(base, count)
            else:
                valid_until = _add_months(base, 12 * count)
        elif kind == "start":
            valid_from = _start_of(argument, base)
        elif kind == "start_iso":
            seconds = parse_time(argument)
            valid_from = _utc(seconds) if seconds is not None else None
        elif kind == "until":
            valid_until = (_start_of(argument, base) if not argument.startswith("the end of")
                           else _end_of_current(argument.split()[-1], base))
        elif kind == "until_iso":
            seconds = parse_time(argument)
            valid_until = _utc(seconds) if seconds is not None else None
    if valid_from is not None and valid_until is not None and valid_until <= valid_from:
        return {**record, "status": "ambiguous"}
    return {
        **record,
        "status": "resolved",
        "valid_from": _iso(valid_from) if valid_from else None,
        "valid_until": _iso(valid_until) if valid_until else None,
        "anchor": dict(anchor) if needs_anchor and anchor else None,
    }


# --------------------------------------------------------------------------- aspect scope


def _bare(word: str) -> str:
    return word.strip(",.;:!?\"'()")


def _opening(words: list[str]) -> list[str]:
    """Piece words after leading discourse fillers ("so", "okay", "honestly", ...)."""

    index = 0
    while index < len(words) and _bare(words[index]) in _DISCOURSE_FILLERS:
        index += 1
    return words[index:]


def _is_request(words: list[str]) -> bool:
    opening = _opening(words)
    if opening and opening[0].rstrip(",") == "now" and opening[0].endswith(","):
        opening = _opening(opening[1:])
    first = [_bare(w) for w in opening[:2]]
    return bool(first) and (first[0] in _REQUEST_OPENERS or tuple(first) in _REQUEST_PAIRS)


def _opens_question(words: list[str]) -> bool:
    opening = " ".join(_bare(w) for w in _opening(words)[:4])
    return _is_request(words) or any(re.match(re.escape(phrase) + r"\b", opening) for phrase in _INDIRECT_REQUESTS)


def _question_starts(pieces: list[tuple[str, int, bool]]) -> dict[int, int]:
    """For pieces of question sentences: the offset (in the normalized piece) where the
    interrogative part begins. A declarative lead-in before the first segment that opens
    a question or request ("I'm planning X next month, do you have tips?") stays asserted;
    with no such segment the whole sentence is treated as the question."""

    by_sentence: dict[int, list[int]] = {}
    for index, (_, number, question) in enumerate(pieces):
        if question:
            by_sentence.setdefault(number, []).append(index)
    starts: dict[int, int] = {}
    for indexes in by_sentence.values():
        first: tuple[int, int] | None = None
        for index in indexes:
            lowered = _norm(pieces[index][0])
            offsets = [0] + [m.end() for m in _SEGMENT_BOUNDARY.finditer(lowered)]
            offset = next((o for o in offsets if _opens_question(lowered[o:].split())), None)
            if offset is not None:
                first = (index, offset)
                break
        for index in indexes:
            if first is None or index > first[0]:
                starts[index] = 0
            elif index == first[0]:
                starts[index] = first[1]
    return starts


def _cue_matches(lowered: str) -> list[tuple[int, int, str]]:
    """Leftmost-longest cue matches: "right now" is one cue, not also "now"."""

    found = sorted(((m.start(), m.end(), cue) for cue, pattern in _ASPECT_CUE_RE.items()
                    for m in pattern.finditer(lowered)), key=lambda item: (item[0], -(item[1] - item[0]), item[2]))
    selected, last_end = [], -1
    for start, end, cue in found:
        if start >= last_end:
            selected.append((start, end, cue))
            last_end = end
    return selected


def _decline_reason(cue: str, lowered: str, start: int, end: int, words_before: list[str], question: bool,
                    request: bool) -> str | None:
    before = [_bare(w) for w in words_before]
    after = [_bare(w) for w in lowered[end:].split()]
    if cue == "now" and lowered[end:end + 1] == "," and not [w for w in before if w not in _DISCOURSE_FILLERS]:
        return "discourse_marker"
    if question or request:
        return "question_or_request"
    # A subordinator scopes over its own comma-delimited segment ("Speaking of which, I ...").
    if any(_bare(w) in _SUBORDINATORS for w in lowered[:start].rpartition(",")[2].split()):
        return "subordinate_clause"
    if cue == "used to":
        head = [w for w in before if not (w.endswith("ly") or w in _DEGREE_WORDS)]
        if head and head[-1] in _PASSIVE_HEADS:
            return "passive_or_accustomed"
    if cue == "going to":
        if (before and before[-1] in _HABITUAL_GOING) or (after and after[0] in _MOTION_DESTINATIONS):
            return "motion_or_habitual"
    return None


def _scoped_aspect(pieces: list[tuple[str, int, bool]], principal: set[int] | None) -> tuple[dict[str, list[str]], dict]:
    """Aspect evidence scoped to the principal proposition, plus the scope diagnostic.

    ``principal`` is the set of piece indexes carrying the known proposition, or None
    when the write has no single known proposition (the whole asserted write is scope).
    """

    accepted: dict[str, set[str]] = {}
    declined: list[dict[str, str]] = []
    question_starts = _question_starts(pieces)
    for index, (piece, _, _) in enumerate(pieces):
        lowered = _norm(piece)
        request = _is_request(lowered.split())
        for start, end, cue in _cue_matches(lowered):
            question = index in question_starts and start >= question_starts[index]
            reason = _decline_reason(cue, lowered, start, end, lowered[:start].split(), question, request)
            if reason is None and principal is not None and index not in principal:
                reason = "non_principal_clause"
            if reason is None:
                accepted.setdefault(_ASPECT_REGIME[cue], set()).add(cue)
            else:
                declined.append({"cue": cue, "reason": reason})
    if len(accepted) > 1:
        status = "mixed_regimes"
    elif accepted:
        status = "resolved_principal" if principal is not None else "resolved_write"
    else:
        status = "none"
    aspect = {name: sorted(cues) for name, cues in accepted.items()} if len(accepted) == 1 else {}
    return aspect, {"status": status, "declined": declined}


# --------------------------------------------------------------------------- interpretation


def slot_key(entity: str | None, prop: str | None) -> str | None:
    return f"{entity}|{prop}" if entity and prop else None


def interpret_write(text: str, *, declared_temporal: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Deterministic typed interpretation of one write. Evidence only; grants nothing."""

    lowered = _norm(text)
    month_free = re.sub(r"\bmay(?=\s+\d)", "maymonth", lowered)  # "May 3" is a date, not a hedge
    hedges = sorted(h for h in _HEDGES if _contains(month_free, h))
    self_claims = sorted(name for name, pattern in _SELF_CLAIMS.items() if re.search(pattern, lowered))
    pieces = _clause_pieces(text)
    # 1.2.0: a trailing request must not be incorporated into the value.
    clauses: list[dict[str, Any]] = []
    antecedent: str | None = None
    for piece_index, (raw, _, _) in enumerate(pieces):
        if _opens_question(_norm(raw).split()):
            continue
        clause = _parse_clause(raw, antecedent)
        if clause is None:
            continue
        clause["piece"] = piece_index
        if _SELF_REFERENCE.match(_norm(raw)):
            clause["self_reference"] = True
        clauses.append(clause)
        # Subject inheritance follows the nearest preceding explicit subject; a clause
        # about the memory itself never becomes an antecedent.
        if clause["entity"] and clause["subject"] in {"noun", "pronoun"} and not clause.get("self_reference"):
            antecedent = clause["entity"]
    propositional = [c for c in clauses if not c.get("self_reference")]
    change = sorted({m for c in propositional for m in c["markers"]
                     if m in {"no longer", "used to", "not anymore", *_REPLACEMENT_VERBS, *_REVISION_QUALIFIERS}})
    coexistence = sorted({m for c in propositional for m in c["markers"] if m in _COEXISTENCE}
                         | {m for m in ("in addition", "additionally", "as well") if _contains(lowered, m)})
    if any(c.get("modal") in {"might", "may", "could"} for c in propositional):
        hedges = sorted(set(hedges) | {c["modal"] for c in propositional if c.get("modal") in {"might", "may", "could"}})

    affirmed = [c for c in propositional if c["polarity"] == AFFIRMED and c["entity"] and c["value"]]
    slots = sorted({slot_key(c["entity"], c["property"]) for c in affirmed})
    if any(c["subject"] == "unresolved_pronoun" for c in propositional):
        proposition = {"status": AMBIGUOUS, "reason": "unresolved_pronoun"}
    elif len(slots) == 1:
        primary = affirmed[-1]
        values = sorted({c["value"] for c in affirmed})
        proposition = {"status": KNOWN if len(values) == 1 else AMBIGUOUS,
                       "entity": primary["entity"], "property": primary["property"],
                       "value": primary["value"] if len(values) == 1 else None,
                       "reason": None if len(values) == 1 else "multiple_values_in_one_write"}
    elif slots:
        proposition = {"status": AMBIGUOUS, "reason": "multiple_proposition_slots", "slots": slots}
    else:
        proposition = {"status": UNKNOWN, "reason": "no_parseable_affirmed_proposition"}
    proposition["basis"] = "interpreted" if proposition["status"] != UNKNOWN else "none"
    # Aspect describes the principal proposition: with one known proposition, only cues in
    # its own affirmed clauses count; otherwise cues anywhere in asserted speaker content.
    principal = {c["piece"] for c in affirmed} if proposition["status"] == KNOWN else None
    aspect, aspect_scope = _scoped_aspect(pieces, principal)

    ended = [{"entity": c["entity"], "property": c["property"], "value": c["value"], "marker": next(
        (m for m in c["markers"] if m in {"no longer", "used to", "not anymore"}), None)}
        for c in propositional if c["polarity"] == ENDED and c["entity"] and c["value"]]

    if coexistence:
        cardinality = {"class": MULTI_VALUED, "basis": "interpreted_coexistence_marker", "evidence": coexistence}
    elif any(m in _REPLACEMENT_VERBS or m in _REVISION_QUALIFIERS for m in change) and proposition["status"] == KNOWN:
        cardinality = {"class": SINGLE_VALUED, "basis": "interpreted_replacement_marker",
                       "evidence": [m for m in change if m in _REPLACEMENT_VERBS or m in _REVISION_QUALIFIERS]}
    else:
        cardinality = {"class": UNKNOWN, "basis": "none", "evidence": []}

    anchor = None
    if declared_temporal and declared_temporal.get("observed_at"):
        anchor = {"value": str(declared_temporal["observed_at"]), "source": "caller_declared_observed_at"}
    self_validity = _resolve_self_validity(lowered, anchor, bool(hedges), declared_temporal)

    ineligible = []
    if hedges:
        ineligible.append("hedged")
    if self_claims:
        ineligible.append("untrusted_self_claim")
    if proposition["status"] != KNOWN:
        ineligible.append(f"proposition_{proposition['status']}")
    return _compact({
        "interpreter": {"ref": INTERPRETER_REF, "version": INTERPRETER_VERSION},
        "authority_effect": "none",
        "classifier": {"version": CLASSIFIER_VERSION},
        "clauses": [{k: c[k] for k in ("entity", "property", "value", "polarity") if c[k] is not None}
                    for c in clauses[:MAX_CLAUSES]],
        "clause_count": len(clauses),
        "proposition": proposition,
        "ended_values": ended,
        "cardinality": cardinality,
        "markers": {"change": change, "coexistence": coexistence, "hedge": hedges, "self_claims": self_claims,
                    "aspect": aspect},
        "aspect_scope": aspect_scope,
        "self_validity": self_validity,
        "proposal_ineligible_reasons": ineligible,
    })


def persisted_form(interpretation: Mapping[str, Any]) -> dict[str, Any]:
    """The compact stored form: only non-default evidence plus one version tag.

    Every fact carries this, and recall decodes fact attributes for every candidate,
    so defaults (unknown proposition and cardinality, no self-validity, no relations,
    the constant interpreter ref, ``authority_effect: none``) are implied, not stored.
    Clause-level parses are diagnostic and are not persisted (``clause_count`` is).
    ``expanded_form`` restores the full typed contract exactly.
    """

    classifier_version = (interpretation.get("classifier") or {}).get("version") or CLASSIFIER_VERSION
    stored: dict[str, Any] = {"version": f"{INTERPRETER_VERSION}/{classifier_version}"}
    proposition = {k: v for k, v in (interpretation.get("proposition") or {}).items() if k != "basis"}
    if proposition.get("status", UNKNOWN) != UNKNOWN:
        if "slots" in proposition:
            proposition["slot_count"] = len(proposition.pop("slots"))
        stored["proposition"] = proposition
    cardinality = interpretation.get("cardinality") or {}
    if cardinality.get("class", UNKNOWN) != UNKNOWN:
        stored["cardinality"] = dict(cardinality)
    validity = interpretation.get("self_validity") or {}
    if validity.get("status", "none") != "none":
        stored["self_validity"] = dict(validity)
    for key in ("ended_values", "markers", "relations", "clause_count", "relation_count",
                "unresolved_cardinality_unknown_count"):
        if interpretation.get(key):
            stored[key] = interpretation[key]
    reasons = [r for r in interpretation.get("proposal_ineligible_reasons") or () if not r.startswith("proposition_")]
    if reasons:
        stored["proposal_ineligible_reasons"] = reasons
    stored.update({key: interpretation[key] for key in TYPED_KEYS if key in interpretation})
    return stored


def expanded_form(stored: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """The full typed contract from a stored form; ``None`` for pre-#550 facts."""

    if not stored:
        return None
    interpreter_version, _, classifier_version = str(stored.get("version", "")).partition("/")
    proposition = dict(stored.get("proposition") or {"status": UNKNOWN})
    proposition["basis"] = "none" if proposition["status"] == UNKNOWN else "interpreted"
    reasons = list(stored.get("proposal_ineligible_reasons") or ())
    if proposition.get("status") != KNOWN:
        reasons.append(f"proposition_{proposition.get('status', UNKNOWN)}")
    return {
        "interpreter": {"ref": INTERPRETER_REF, "version": interpreter_version},
        "classifier": {"version": classifier_version},
        "authority_effect": "none",
        "proposition": proposition,
        "cardinality": dict(stored.get("cardinality") or {"class": UNKNOWN, "basis": "none"}),
        "self_validity": dict(stored.get("self_validity") or {"status": "none"}),
        "markers": dict(stored.get("markers") or {}),
        "ended_values": list(stored.get("ended_values") or ()),
        "relations": list(stored.get("relations") or ()),
        "relation_count": int(stored.get("relation_count", 0)),
        "clause_count": int(stored.get("clause_count", 0)),
        **({"unresolved_cardinality_unknown_count": stored["unresolved_cardinality_unknown_count"]}
           if "unresolved_cardinality_unknown_count" in stored else {}),
        "proposal_ineligible_reasons": reasons,
        **{key: stored[key] for key in TYPED_KEYS if key in stored},
    }


def index_summary(interpretation: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """The minimal stored fields classification reads; kept in the in-memory slot index."""

    if not interpretation or write_slot(interpretation) is None:
        return None
    return {"proposition": dict(interpretation["proposition"]),
            "cardinality": {"class": (interpretation.get("cardinality") or {}).get("class", UNKNOWN)}}


def write_slot(interpretation: Mapping[str, Any] | None) -> str | None:
    if not interpretation:
        return None
    proposition = interpretation.get("proposition") or {}
    if proposition.get("status") != KNOWN:
        return None
    return slot_key(proposition.get("entity"), proposition.get("property"))


def ended_slots(interpretation: Mapping[str, Any] | None) -> set[str]:
    return {slot_key(item["entity"], item["property"]) for item in (interpretation or {}).get("ended_values", ())} - {None}


def interpreted_validity(interpretation: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """The resolved self-validity window, or None. Always basis ``interpreted``."""

    validity = (interpretation or {}).get("self_validity") or {}
    if validity.get("status") != "resolved":
        return None
    return {"valid_from": validity.get("valid_from"), "valid_until": validity.get("valid_until"),
            "basis": "interpreted", "anchor": validity.get("anchor"),
            "interpreter": dict((interpretation or {}).get("interpreter") or {
                "ref": INTERPRETER_REF, "version": str((interpretation or {}).get("version", "")).partition("/")[0]})}


# --------------------------------------------------------------------------- classification


def proposal_id(source_fact_uuid: str, target_fact_uuid: str, *, classifier_version: str = CLASSIFIER_VERSION) -> str:
    material = json.dumps([INTERPRETER_VERSION, classifier_version, source_fact_uuid, target_fact_uuid])
    return "semantic-proposal:" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def bounded_relations(relations: list[dict[str, Any]]) -> dict[str, Any]:
    """Persisted relation evidence, bounded.

    Informative relations (state change, conflict, same value, coexistence, and
    unresolved change evidence that was *not proposable*) are kept most significant
    first, up to ``MAX_RELATIONS``. Plain same-slot pairs with unknown cardinality carry
    no further information than the slot itself, so they are kept only as a count.
    """

    plain, informative = [], []
    for relation in relations:
        is_plain = relation["classification"] == UNRESOLVED and relation["basis"] == "cardinality_unknown"
        (plain if is_plain else informative).append(relation)
    informative.sort(key=lambda r: (_RELATION_PRIORITY[r["classification"]], r["other_fact_uuid"]))
    out: dict[str, Any] = {"relations": informative[:MAX_RELATIONS], "relation_count": len(relations)}
    if plain:
        out["unresolved_cardinality_unknown_count"] = len(plain)
    return out


def _compact(value: Any) -> Any:
    """Drop empty and null fields so persisted evidence stays small; structure is unchanged."""

    if isinstance(value, dict):
        return {k: _compact(v) for k, v in value.items() if v not in (None, [], {}, "")}
    if isinstance(value, list):
        return [_compact(v) for v in value]
    return value


def classify_write(
    new: Mapping[str, Any],
    new_fact_uuid: str,
    new_text: str,
    retained: Iterable[tuple[str, str, Mapping[str, Any] | None]],
    *,
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    """Classify a new write against retained current memories (uuid, memory ref, interpretation).

    Only same-slot pairs are related. The result is evidence; a ``state_change``
    proposal is attached only for an explicit, unhedged, untrusted-claim-free change.
    """

    new_slot = write_slot(new)
    # Stored proposition and ended values are normalized at interpretation time.
    new_value = (new.get("proposition") or {}).get("value") or ""
    new_card = (new.get("cardinality") or {}).get("class", UNKNOWN)
    reasons = list(new.get("proposal_ineligible_reasons") or ())
    ended = {(slot_key(e["entity"], e["property"]), e["value"] or ""): e for e in new.get("ended_values", ())}
    ended_slot_names = {slot for slot, _ in ended}
    relations: list[dict[str, Any]] = []
    for fact_uuid, memory_ref, other in sorted(retained, key=lambda item: item[0]):
        other_slot = write_slot(other)
        if other_slot is None or (other_slot != new_slot and other_slot not in ended_slot_names):
            continue
        other_value = ((other or {}).get("proposition") or {}).get("value") or ""
        termination = ended.get((other_slot, other_value))
        other_card = ((other or {}).get("cardinality") or {}).get("class", UNKNOWN)
        if other_slot == new_slot and other_value == new_value:
            kind, basis = SAME_VALUE, "identical_slot_and_value"
        elif termination is not None:
            kind, basis = STATE_CHANGE_CANDIDATE, f"explicit_termination:{termination['marker']}"
        elif other_slot != new_slot:
            continue
        elif MULTI_VALUED in (new_card, other_card) or HIERARCHICAL in (new_card, other_card):
            kind, basis = COEXISTENCE, f"cardinality:{new_card if new_card != UNKNOWN else other_card}"
        elif new_card == SINGLE_VALUED and (new.get("markers") or {}).get("change"):
            kind, basis = STATE_CHANGE_CANDIDATE, "single_valued_replacement_marker"
        elif SINGLE_VALUED in (new_card, other_card):
            kind, basis = CONFLICT, "single_valued_without_change_evidence"
        else:
            kind, basis = UNRESOLVED, "cardinality_unknown"
        if kind == STATE_CHANGE_CANDIDATE and reasons:
            kind, basis = UNRESOLVED, "change_evidence_not_proposable:" + ",".join(reasons)
        relation: dict[str, Any] = {
            "classification": kind,
            "basis": basis,
            "other_fact_uuid": fact_uuid,
            "other_memory_ref": memory_ref,
            "slot": other_slot,
        }
        if kind == STATE_CHANGE_CANDIDATE:
            relation["proposal"] = {
                "proposal_id": proposal_id(new_fact_uuid, fact_uuid),
                "operation": "correction",
                "replacement_kind": "state_change",
                "target_reference": memory_ref,
                "target_fact_uuid": fact_uuid,
                "source_fact_uuid": new_fact_uuid,
                "replacement_text": new_text,
                # The change happened no later than the caller-declared observation.
                # This is an upper bound for a caller to consider, not an effective time.
                "effective_no_later_than": observed_at,
                "applied": False,
                "authority_effect": "none",
                "application_path": "AgentMemory.correct(replacement_kind='state_change') under PAMA",
            }
        relations.append(relation)
    return relations


__all__ = [
    "AFFIRMED", "AMBIGUOUS", "CARDINALITIES", "CLASSIFICATIONS", "CLASSIFIER_VERSION", "COEXISTENCE", "CONFLICT",
    "ENDED", "HIERARCHICAL", "INTERPRETER_REF", "INTERPRETER_VERSION", "KNOWN", "MULTI_VALUED", "SAME_VALUE",
    "SINGLE_VALUED", "STATE_CHANGE_CANDIDATE", "TYPED_CLASSIFIER_VERSION", "TYPED_KEYS", "UNKNOWN", "UNRESOLVED", "WRITE_SEMANTICS_KEY", "bounded_relations", "classify_write", "expanded_form", "index_summary", "persisted_form",
    "ended_slots", "interpret_write", "interpreted_validity", "proposal_id", "slot_key", "write_slot",
]
