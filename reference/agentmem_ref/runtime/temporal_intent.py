"""Query temporal intent for query-conditioned recall applicability (#538, ADR-039 proposed).

A query asks about *what* (relevance) and, separately, *when* (temporal intent). This
module represents the second question. It never admits, refuses, supersedes, or grants
authority; it only tells the post-admission applicability policy which temporal
relationship the query requests.

Modes (ADR-039 first vocabulary)::

    current                   presently applicable state at a reference time
    as_of                     state applicable at an instant or bounded interval
    historical                past evidence or chronology, no single instant
    atemporal_or_unspecified  no established temporal preference
    prospective               future-valid intent, plans, commitments

Posture:

* ``explicit``  - supplied by the caller or host (``intent_basis = caller_declared``;
  authoritative for this recall), or stated unambiguously by the query's own language
  (``intent_basis = query_language_explicit``, since 1.1.0; never caller authority).
* ``inferred``  - produced by the deterministic cue interpreter below. It is estimator
  output with a ``high`` or ``low`` confidence and the matched cues as evidence.
* ``unspecified`` - nothing established a temporal relationship. This is
  ``atemporal_or_unspecified`` and is never silently promoted to ``current``.

The cue lexicon is generic English temporal language. It was fixed before any benchmark
question was inspected and contains no dataset identifiers or benchmark phrasing
(ADR-039 C21). When cues for different modes co-occur, the interpreter preserves the
ambiguity (``atemporal_or_unspecified`` with ``low`` confidence and both cue sets as
evidence) rather than choosing one.

Expected recall shape is interpreted the same way: ``ranked`` by default, ``timeline``
when the query explicitly asks for change or evolution over time, or when the caller
declares it.

Interpreter 1.1.0 (#585) keeps every 1.0.0 mode rule and adds:

* typed source spans. Every consumed cue is a :class:`TemporalCueSpan` whose
  ``start``/``end`` index the original query (``query[start:end] == text``). Cue matches
  that were considered and deliberately not consumed are :class:`DeclinedCueSpan` with a
  reason. The query itself is never rewritten and no token is removed from relevance;
  spans are evidence for a later relevance seam (#583), not a relevance change.
* ``intent_basis``. Explicit posture has two distinct sources. ``caller_declared`` is the
  caller's declaration and the only source of caller authority. ``query_language_explicit``
  is current intent the query itself states unambiguously (``currently``, ``right now``,
  ``current``, temporal ``now`` ...): the query really did ask for that relationship, so
  it is ``posture = explicit``, but it never gains caller authority and never widens
  historical-evidence admission (#549). ``query_cue_inference`` is every other
  query-derived (inferred) intent and ``none`` is unspecified intent.
* contextual ``now``. Temporal ``now`` (clause-final, or after a form of *be*) is
  explicit current language unless its clause is imperative (``Show me now.``).
  Discourse ``now`` (clause-leading, followed by a comma or an imperative/discourse verb), quoted or metalinguistic mentions, and non-current idioms
  (``just now``, ``until now``, ``from now on``, ``now that``, ``now and then``,
  ``now or never``) are declined. ``for now``/``by now`` and any other ``now`` stay the
  1.0.0 low-confidence cue.
* contextual ``going to``. After an aspectual/habitual verb (``started``, ``began``,
  ``kept``, ``been`` ...) or before a determiner/destination (``the gym``, ``my office``)
  it is motion/habitual language and is declined. After a form of *be* with an optional
  short subject (``am I going to stay``) it is the future auxiliary and stays
  high-confidence prospective. Anything else is a low-confidence prospective cue.
* quoted (``"..."``, curly double quotes) and metalinguistic (``the word now``) cue
  mentions are declined for every cue.
* referent ``current``. ``current`` modifying a noun after a temporal connective in the
  same clause (``before I started my current job``) identifies *which* thing is meant; it
  does not ask for the present-time answer, so it is declined as ``referent_modifier``.
* cue scope. A clause-leading ``Right now,`` in a query that also asks about another
  mode is discourse urgency, not the temporal target, and is declined.
* composite cues win over nested ones (``right now`` over ``now``, ``next week`` over
  ``next``), so no contradictory nested evidence is emitted.
* a query-language-explicit current cue that co-occurs with a cue of another mode is a
  conflict: ambiguity is preserved rather than letting the stated mode win silently.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

INTERPRETER_REF = "agent-memory-deterministic-temporal-cues"
INTERPRETER_VERSION = "1.1.0"

CURRENT = "current"
AS_OF = "as_of"
HISTORICAL = "historical"
ATEMPORAL = "atemporal_or_unspecified"
PROSPECTIVE = "prospective"
MODES = (CURRENT, AS_OF, HISTORICAL, ATEMPORAL, PROSPECTIVE)

RANKED = "ranked"
TIMELINE = "timeline"
RECALL_SHAPES = (RANKED, TIMELINE)

EXPLICIT = "explicit"
INFERRED = "inferred"
UNSPECIFIED = "unspecified"

HIGH = "high"
LOW = "low"

# Intent basis (1.1.0): where the resolved intent came from.
CALLER_DECLARED = "caller_declared"
QUERY_LANGUAGE_EXPLICIT = "query_language_explicit"
QUERY_CUE_INFERENCE = "query_cue_inference"
NO_BASIS = "none"
INTENT_BASES = (CALLER_DECLARED, QUERY_LANGUAGE_EXPLICIT, QUERY_CUE_INFERENCE, NO_BASIS)

# Span basis (1.1.0): why one span was consumed.
SPAN_QUERY_LANGUAGE_EXPLICIT = "query_language_explicit"
SPAN_QUERY_CUE = "query_cue"
SPAN_AS_OF_EXPRESSION = "as_of_expression"
SPAN_TIMELINE_EXPRESSION = "timeline_expression"

# Decline reasons (1.1.0): why a cue match was not consumed.
QUOTED_MENTION = "quoted_mention"
METALINGUISTIC_MENTION = "metalinguistic_mention"
DISCOURSE_MARKER = "discourse_marker"
HABITUAL_OR_MOTION = "habitual_or_motion"
NON_CURRENT_IDIOM = "non_current_idiom"
REFERENT_MODIFIER = "referent_modifier"
DECLINE_REASONS = (
    QUOTED_MENTION, METALINGUISTIC_MENTION, DISCOURSE_MARKER, HABITUAL_OR_MOTION, NON_CURRENT_IDIOM, REFERENT_MODIFIER,
)


@dataclass(frozen=True)
class TemporalCueSpan:
    """One span of the original query consumed as temporal intent evidence."""

    start: int
    end: int
    text: str
    normalized_text: str
    mode: str
    confidence: str
    basis: str
    cue_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DeclinedCueSpan:
    """A cue match that was considered and deliberately not consumed."""

    start: int
    end: int
    text: str
    normalized_text: str
    cue_id: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _cue(phrase: str) -> re.Pattern[str]:
    return re.compile(r"\b" + phrase + r"\b", re.IGNORECASE)


# Frozen cue lexicon. High-confidence cues name the temporal relationship directly;
# low-confidence cues are suggestive only and never activate temporal ordering on their
# own (ADR-039 C16). Entries: (cue_id, mode, level, phrase, span basis). ``now`` and
# ``going to`` keep their 1.0.0 lexicon slot (evidence order) but are classified in
# context. The phrases are unchanged from 1.0.0.
_CONTEXTUAL_NOW = "current.low.now"
_CONTEXTUAL_GOING_TO = "prospective.high.going_to"
_LEXICON_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (CURRENT, HIGH, "currently", SPAN_QUERY_LANGUAGE_EXPLICIT),
    (CURRENT, HIGH, "current", SPAN_QUERY_LANGUAGE_EXPLICIT),
    (CURRENT, HIGH, "right now", SPAN_QUERY_LANGUAGE_EXPLICIT),
    (CURRENT, HIGH, "at the moment", SPAN_QUERY_LANGUAGE_EXPLICIT),
    (CURRENT, HIGH, "at present", SPAN_QUERY_LANGUAGE_EXPLICIT),
    (CURRENT, HIGH, "presently", SPAN_QUERY_LANGUAGE_EXPLICIT),
    (CURRENT, HIGH, "nowadays", SPAN_QUERY_CUE),
    (CURRENT, HIGH, "these days", SPAN_QUERY_CUE),
    (CURRENT, HIGH, "as of now", SPAN_QUERY_LANGUAGE_EXPLICIT),
    (CURRENT, HIGH, "as of today", SPAN_QUERY_LANGUAGE_EXPLICIT),
    (CURRENT, HIGH, "most recent", SPAN_QUERY_CUE),
    (CURRENT, HIGH, "latest", SPAN_QUERY_CUE),
    (CURRENT, LOW, "now", SPAN_QUERY_CUE),
    (CURRENT, LOW, "still", SPAN_QUERY_CUE),
    (CURRENT, LOW, "today", SPAN_QUERY_CUE),
    (CURRENT, LOW, "anymore", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "used to", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "previously", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "formerly", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "originally", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "initially", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "at first", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "in the past", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "back then", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "at the time", SPAN_QUERY_CUE),
    (HISTORICAL, HIGH, "prior to", SPAN_QUERY_CUE),
    (HISTORICAL, LOW, "before", SPAN_QUERY_CUE),
    (HISTORICAL, LOW, "earlier", SPAN_QUERY_CUE),
    (HISTORICAL, LOW, "ago", SPAN_QUERY_CUE),
    (HISTORICAL, LOW, "last time", SPAN_QUERY_CUE),
    (HISTORICAL, LOW, "first time", SPAN_QUERY_CUE),
    (HISTORICAL, LOW, "once", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "upcoming", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "scheduled", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "next week", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "next month", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "next year", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "tomorrow", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "planning to", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "plan to", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "going to", SPAN_QUERY_CUE),
    (PROSPECTIVE, HIGH, "intend to", SPAN_QUERY_CUE),
    (PROSPECTIVE, LOW, "will", SPAN_QUERY_CUE),
    (PROSPECTIVE, LOW, "next", SPAN_QUERY_CUE),
    (PROSPECTIVE, LOW, "later", SPAN_QUERY_CUE),
    (PROSPECTIVE, LOW, "soon", SPAN_QUERY_CUE),
    (PROSPECTIVE, LOW, "future", SPAN_QUERY_CUE),
)
_LEXICON: tuple[tuple[int, str, str, str, str, re.Pattern[str]], ...] = tuple(
    (order, f"{mode}.{level}.{phrase.replace(' ', '_')}", mode, level, basis, _cue(phrase))
    for order, (mode, level, phrase, basis) in enumerate(_LEXICON_ROWS)
)
_TIMELINE_CUES = tuple(
    re.compile(r"\b" + phrase + r"\b", re.IGNORECASE)
    for phrase in (
        "timeline", "history of", "over time", "how did .{0,60}?(change|changed|evolve|evolved|develop)",
        "what changed", "sequence of",
    )
)
_AS_OF_DATE = re.compile(r"\b(?:as of|on|at)\s+(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)
_AS_OF_YEAR = re.compile(r"\b(?:as of|in|during)\s+((?:19|20)\d{2})\b", re.IGNORECASE)

# Contextual rules (1.1.0). Bounded, inspectable word lists; not a parser.
_METALINGUISTIC_BEFORE = re.compile(r"\b(?:word|words|term|phrase|expression)\s*['\u2018]?$", re.IGNORECASE)
_NOW_IDIOM_BEFORE = re.compile(r"\b(?:just|until|till|up to|up until|up till|from)\s+$", re.IGNORECASE)
_NOW_IDIOM_AFTER = re.compile(r"^\s+(?:that\b|and\s+then\b|or\s+never\b|on\b)", re.IGNORECASE)
# ``for now`` / ``by now`` are temporal but not clearly "presently applicable": weak only.
_NOW_WEAK_BEFORE = re.compile(r"\b(?:for|by)\s+$", re.IGNORECASE)
_CLAUSE_BREAK = re.compile(r"[.!?;:,\n\"\u201c\u201d]")
_LEADING_FILLERS = frozenset({"and", "so", "ok", "okay", "alright", "well", "but", "then", "oh"})
_DISCOURSE_VERBS = frozenset({
    "tell", "explain", "summarize", "summarise", "list", "show", "give", "describe", "let", "let's", "lets",
    "compare", "write", "draft", "translate", "walk", "help", "remind", "repeat", "answer", "consider",
    "continue", "move", "turn", "focus", "switch", "please", "check", "find", "search", "look", "review",
    "provide", "outline", "recap", "return", "suppose", "imagine", "say",
})
_BE_BEFORE_NOW = re.compile(r"(?:\b(?:is|are|am)(?:n't|n\u2019t)?|'s|'re|'m|\u2019s|\u2019re|\u2019m)\s+$", re.IGNORECASE)
_CLAUSE_FINAL = re.compile(r"^\s*(?:[?.!,;:]|$)")
# ``current`` after one of these connectives in the same clause names a referent.
# ``when``/``while`` are excluded: they also open questions ("When does the current ...").
_REFERENT_CONNECTIVE_BEFORE = re.compile(
    r"\b(?:before|after|since|until|till|prior to)\b[^.!?;:,]*$", re.IGNORECASE
)
_CURRENT_ADJECTIVE = "current.high.current"
_URGENCY_COMPOSITE = "current.high.right_now"
_HABITUAL_BEFORE_GOING = frozenset({
    "start", "started", "starting", "starts", "begin", "began", "begun", "beginning", "begins",
    "continue", "continued", "continues", "continuing", "keep", "kept", "keeps", "keeping",
    "stop", "stopped", "stopping", "stops", "quit", "quits", "quitting", "resume", "resumed", "resumes",
    "resuming", "enjoy", "enjoyed", "enjoys", "like", "liked", "likes", "love", "loved", "loves",
    "hate", "hated", "hates", "avoid", "avoided", "avoids", "try", "tried", "tries", "trying",
    "miss", "missed", "misses", "finish", "finished", "been", "was", "were",
})
_MOTION_AFTER_GOING = frozenset({
    "the", "a", "an", "my", "your", "his", "her", "its", "our", "their", "this", "that", "these", "those",
    "some", "school", "church", "work", "bed", "class", "college", "therapy", "practice", "lunch",
    "dinner", "breakfast",
})
_FUTURE_AUXILIARY_BEFORE_GOING = re.compile(
    r"(?:\b(?:am|is|are|be|being)(?:n't|n\u2019t)?|'s|'re|'m|\u2019s|\u2019re|\u2019m)\s+"
    r"(?:[\w'\u2019]+\s+){0,3}?(?:not\s+)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TemporalIntent:
    """The temporal relationship a query requests, with its basis."""

    mode: str = ATEMPORAL
    posture: str = UNSPECIFIED
    confidence: str | None = None
    reference_time: str | None = None
    target_start: str | None = None
    target_end: str | None = None
    expected_recall_shape: str = RANKED
    evidence: tuple[str, ...] = field(default_factory=tuple)
    interpreter_ref: str = INTERPRETER_REF
    interpreter_version: str = INTERPRETER_VERSION
    authority_effect: str = "none"
    intent_basis: str | None = None
    spans: tuple[TemporalCueSpan, ...] = field(default_factory=tuple)
    declined_spans: tuple[DeclinedCueSpan, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.intent_basis is None:
            # Backward-compatible derivation for pre-1.1.0 constructions.
            default = {EXPLICIT: CALLER_DECLARED, INFERRED: QUERY_CUE_INFERENCE}.get(self.posture, NO_BASIS)
            object.__setattr__(self, "intent_basis", default)
        if self.mode not in MODES:
            raise ValueError(f"unknown temporal intent mode {self.mode!r}")
        if self.posture not in {EXPLICIT, INFERRED, UNSPECIFIED}:
            raise ValueError(f"unknown temporal intent posture {self.posture!r}")
        if self.expected_recall_shape not in RECALL_SHAPES:
            raise ValueError(f"unknown recall shape {self.expected_recall_shape!r}")
        if self.posture == INFERRED and self.confidence not in {HIGH, LOW}:
            raise ValueError("inferred temporal intent requires high or low confidence")
        if self.intent_basis not in INTENT_BASES:
            raise ValueError(f"unknown temporal intent basis {self.intent_basis!r}")
        # Posture/basis invariant: explicit posture comes from the caller's declaration or
        # from unambiguous query language, and the two stay distinguishable.
        allowed = {EXPLICIT: {CALLER_DECLARED, QUERY_LANGUAGE_EXPLICIT}, INFERRED: {QUERY_CUE_INFERENCE},
                   UNSPECIFIED: {NO_BASIS}}[self.posture]
        if self.intent_basis not in allowed:
            raise ValueError(f"temporal intent basis {self.intent_basis!r} is invalid for posture {self.posture!r}")
        for value in (self.reference_time, self.target_start, self.target_end):
            if value is not None and parse_time(value) is None:
                raise ValueError(f"temporal intent time {value!r} is not ISO-8601")
        if self.mode == AS_OF and self.target_start is None and self.target_end is None and self.reference_time is None:
            raise ValueError("as_of intent requires a target instant or interval")

    @property
    def orders_temporally(self) -> bool:
        """Whether this intent is established strongly enough to influence ordering.

        Explicit intent always is. Inferred intent is only at high confidence, so a
        suggestive cue never becomes a temporal preference (ADR-039 C16).
        """

        if self.mode in {ATEMPORAL, HISTORICAL}:
            return False
        return self.posture == EXPLICIT or (self.posture == INFERRED and self.confidence == HIGH)

    def target_instant(self) -> float | None:
        """The instant applicability is evaluated at, when one is established."""

        if self.mode == AS_OF:
            start, end = parse_time(self.target_start), parse_time(self.target_end)
            if start is not None and end is not None:
                return end - 1e-6
            return start if start is not None else end if end is not None else parse_time(self.reference_time)
        return parse_time(self.reference_time)

    @property
    def caller_declared(self) -> bool:
        """Whether the caller declared this intent: the only source of caller authority.

        Query-language explicit intent is explicit posture but is never caller-declared.
        """

        return self.intent_basis == CALLER_DECLARED

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = list(self.evidence)
        value["spans"] = [span.to_dict() for span in self.spans]
        value["declined_spans"] = [span.to_dict() for span in self.declined_spans]
        value["orders_temporally"] = self.orders_temporally
        return value


def parse_time(value: Any) -> float | None:
    """ISO-8601 (date or datetime, naive = UTC) to POSIX seconds; anything else None."""

    if value is None or value == "":
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def explicit_intent(value: Mapping[str, Any] | TemporalIntent, *, reference_time: str | None = None) -> TemporalIntent:
    """Validate caller-declared temporal intent. Explicit intent is authoritative."""

    if isinstance(value, TemporalIntent):
        return value
    allowed = {"mode", "reference_time", "target_start", "target_end", "expected_recall_shape"}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"unknown temporal intent fields: {sorted(unknown)}")
    return TemporalIntent(
        mode=str(value.get("mode", ATEMPORAL)),
        posture=EXPLICIT,
        confidence=None,
        reference_time=value.get("reference_time", reference_time),
        target_start=value.get("target_start"),
        target_end=value.get("target_end"),
        expected_recall_shape=str(value.get("expected_recall_shape", RANKED)),
        evidence=("caller_declared",),
        intent_basis=CALLER_DECLARED,
    )


def _quoted_regions(query: str) -> list[tuple[int, int]]:
    """Double-quoted regions (straight and curly). An unbalanced quote runs to the end."""

    regions: list[tuple[int, int]] = []
    opened: int | None = None
    for index, char in enumerate(query):
        if char == '"':
            if opened is None:
                opened = index
            else:
                regions.append((opened, index + 1))
                opened = None
        elif char == "\u201c" and opened is None:
            opened = index
        elif char == "\u201d" and opened is not None:
            regions.append((opened, index + 1))
            opened = None
    if opened is not None:
        regions.append((opened, len(query)))
    return regions


def _clause_prefix(query: str, start: int) -> str:
    """The words of the current clause before ``start``, without leading fillers."""

    before = query[:start]
    breaks = [match.end() for match in _CLAUSE_BREAK.finditer(before)]
    words = re.findall(r"[\w'\u2019]+", before[breaks[-1] if breaks else 0:].lower())
    while words and words[0] in _LEADING_FILLERS:
        words.pop(0)
    return " ".join(words)


def _next_word(query: str, end: int) -> str:
    match = re.match(r"\s*([\w'\u2019]+)", query[end:])
    return match.group(1).lower() if match else ""


def _previous_word(query: str, start: int) -> str:
    words = re.findall(r"[\w'\u2019]+", query[:start].lower())
    if words and words[-1].endswith("ly") and len(words) > 1:
        return words[-2]
    return words[-1] if words else ""


def _classify_now(query: str, start: int, end: int) -> tuple[str, str | None]:
    """``(level or decline reason, None)``: ``high``/``low`` consume; a reason declines."""

    before, after = query[:start], query[end:]
    if _NOW_IDIOM_BEFORE.search(before) or _NOW_IDIOM_AFTER.match(after):
        return NON_CURRENT_IDIOM, None
    if _NOW_WEAK_BEFORE.search(before):
        return LOW, None
    final = bool(_CLAUSE_FINAL.match(after))
    if not _clause_prefix(query, start):
        if re.match(r"^\s*,", after) or _next_word(query, end) in _DISCOURSE_VERBS:
            return DISCOURSE_MARKER, None
        if final and re.search(r"\w", before):
            return HIGH, "current.now.temporal_clause_final"
        return LOW, None
    if _clause_prefix(query, start).split()[0] in _DISCOURSE_VERBS:
        # Imperative clause ("Show me now."): urgency, not a stated current state.
        return LOW, None
    if final:
        return HIGH, "current.now.temporal_clause_final"
    if _BE_BEFORE_NOW.search(before):
        return HIGH, "current.now.temporal_after_be"
    return LOW, None


def _classify_going_to(query: str, start: int, end: int) -> tuple[str, str | None]:
    if _previous_word(query, start) in _HABITUAL_BEFORE_GOING or _next_word(query, end) in _MOTION_AFTER_GOING:
        return HABITUAL_OR_MOTION, None
    if _FUTURE_AUXILIARY_BEFORE_GOING.search(query[:start]):
        return HIGH, "prospective.going_to.future_auxiliary"
    return LOW, "prospective.going_to.unresolved"


def _select(matches: list[tuple[int, int, int, Any]]) -> list[tuple[int, int, int, Any]]:
    """Leftmost-longest non-overlapping matches: composites win over nested cues."""

    chosen: list[tuple[int, int, int, Any]] = []
    for item in sorted(matches, key=lambda m: (m[0], -(m[1] - m[0]), m[2])):
        if chosen and item[0] < chosen[-1][1]:
            continue
        chosen.append(item)
    return chosen


def _mention_reason(query: str, start: int, end: int, quoted: list[tuple[int, int]]) -> str | None:
    if any(q_start < end and start < q_end for q_start, q_end in quoted):
        return QUOTED_MENTION
    if _METALINGUISTIC_BEFORE.search(query[:start]):
        return METALINGUISTIC_MENTION
    return None


def _span(query: str, start: int, end: int, mode: str, confidence: str, basis: str, cue_id: str) -> TemporalCueSpan:
    text = query[start:end]
    return TemporalCueSpan(start, end, text, text.lower(), mode, confidence, basis, cue_id)


def _declined(query: str, start: int, end: int, cue_id: str, reason: str) -> DeclinedCueSpan:
    text = query[start:end]
    return DeclinedCueSpan(start, end, text, text.lower(), cue_id, reason)


def interpret_query(query: str, *, reference_time: str | None = None) -> TemporalIntent:
    """Deterministic, bounded inference of temporal intent from generic cues."""

    quoted = _quoted_regions(query)
    declined: list[DeclinedCueSpan] = []

    shape = RANKED
    shape_evidence: tuple[str, ...] = ()
    shape_span: TemporalCueSpan | None = None
    for pattern in _TIMELINE_CUES:
        match = next(
            (m for m in pattern.finditer(query) if _mention_reason(query, m.start(), m.end(), quoted) is None), None
        )
        if match:
            shape, shape_evidence = TIMELINE, (f"shape:timeline:{match.group(0).lower()}",)
            shape_span = _span(query, match.start(), match.end(), HISTORICAL, HIGH, SPAN_TIMELINE_EXPRESSION, "shape.timeline")
            break

    def first_unquoted(pattern: re.Pattern[str]) -> re.Match[str] | None:
        return next((m for m in pattern.finditer(query) if _mention_reason(query, m.start(), m.end(), quoted) is None), None)

    date = first_unquoted(_AS_OF_DATE)
    year = None if date else first_unquoted(_AS_OF_YEAR)
    if date or year:
        if date:
            start = date.group(1)
            end_seconds = parse_time(start) + 86400.0
            end = datetime.fromtimestamp(end_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            cue, cue_id = date, "as_of.date"
        else:
            start, end, cue, cue_id = f"{year.group(1)}-01-01", f"{int(year.group(1)) + 1}-01-01", year, "as_of.year"
        spans = [_span(query, cue.start(), cue.end(), AS_OF, HIGH, SPAN_AS_OF_EXPRESSION, cue_id)]
        if shape_span is not None:
            spans.append(shape_span)
        return TemporalIntent(
            mode=AS_OF,
            posture=INFERRED,
            confidence=HIGH,
            reference_time=reference_time,
            target_start=start,
            target_end=end,
            expected_recall_shape=shape,
            evidence=(f"as_of:{cue.group(0).lower()}",) + shape_evidence,
            intent_basis=QUERY_CUE_INFERENCE,
            spans=tuple(sorted(spans, key=lambda item: (item.start, item.end))),
        )

    candidates = [
        (m.start(), m.end(), order, (cue_id, mode, level, basis))
        for order, cue_id, mode, level, basis, pattern in _LEXICON
        for m in pattern.finditer(query)
    ]
    consumed: list[tuple[int, TemporalCueSpan]] = []
    for start, end, order, (cue_id, mode, level, basis) in _select(candidates):
        reason = _mention_reason(query, start, end, quoted)
        contextual_id = cue_id
        if reason is None and cue_id == _CONTEXTUAL_NOW:
            outcome, contextual_id = _classify_now(query, start, end)
            if outcome in (HIGH, LOW):
                level = outcome
                basis = SPAN_QUERY_LANGUAGE_EXPLICIT if outcome == HIGH else SPAN_QUERY_CUE
                contextual_id = contextual_id or "current.now.unresolved"
            else:
                reason = outcome
        elif reason is None and cue_id == _CURRENT_ADJECTIVE and _next_word(query, end) \
                and _REFERENT_CONNECTIVE_BEFORE.search(query[:start]):
            reason = REFERENT_MODIFIER
        elif reason is None and cue_id == _CONTEXTUAL_GOING_TO:
            outcome, contextual_id = _classify_going_to(query, start, end)
            if outcome in (HIGH, LOW):
                level = outcome
            else:
                reason = outcome
        if reason is not None:
            declined.append(_declined(query, start, end, cue_id, reason))
            continue
        consumed.append((order, _span(query, start, end, mode, level, basis, contextual_id or cue_id)))

    # Cue scope: a clause-leading "Right now," is discourse urgency when the query asks
    # about another mode; the co-occurring mode is the temporal target.
    other_modes = {span.mode for _, span in consumed if span.mode != CURRENT}
    if other_modes:
        for item in list(consumed):
            span = item[1]
            if (
                span.cue_id == _URGENCY_COMPOSITE
                and not _clause_prefix(query, span.start)
                and re.match(r"^\s*,", query[span.end:])
            ):
                consumed.remove(item)
                declined.append(_declined(query, span.start, span.end, span.cue_id, DISCOURSE_MARKER))

    matched: dict[str, dict[str, list[str]]] = {}
    for _, span in sorted(consumed, key=lambda item: (item[0], item[1].start)):
        cues = matched.setdefault(span.mode, {}).setdefault(span.confidence, [])
        if span.normalized_text not in cues:
            cues.append(span.normalized_text)
    if shape == TIMELINE:
        matched.setdefault(HISTORICAL, {}).setdefault(HIGH, [])
    evidence = tuple(
        f"{mode}:{level}:{cue}"
        for mode in sorted(matched)
        for level in sorted(matched[mode])
        for cue in matched[mode][level]
    ) + shape_evidence

    spans = [span for _, span in consumed] + ([shape_span] if shape_span is not None else [])
    spans_out = tuple(sorted(spans, key=lambda item: (item.start, item.end)))
    declined_out = tuple(sorted(declined, key=lambda item: (item.start, item.end)))
    common = dict(reference_time=reference_time, expected_recall_shape=shape, spans=spans_out, declined_spans=declined_out)

    high_modes = sorted(mode for mode, levels in matched.items() if HIGH in levels)
    all_modes = sorted(matched)
    stated = {span.mode for span in spans_out if span.basis == SPAN_QUERY_LANGUAGE_EXPLICIT}
    if len(high_modes) == 1 and not (stated & set(high_modes) and len(all_modes) > 1):
        mode = high_modes[0]
        if mode in stated:
            # The query states this mode unambiguously: explicit posture, not caller authority.
            return TemporalIntent(mode=mode, posture=EXPLICIT, confidence=None, evidence=evidence,
                                  intent_basis=QUERY_LANGUAGE_EXPLICIT, **common)
        return TemporalIntent(mode=mode, posture=INFERRED, confidence=HIGH, evidence=evidence,
                              intent_basis=QUERY_CUE_INFERENCE, **common)
    if len(high_modes) >= 1 or len(all_modes) > 1:
        # Conflicting cues: preserve ambiguity rather than choose (ADR-039 C16). Since
        # 1.1.0 a mode the query states explicitly conflicts with any other mode's cue.
        return TemporalIntent(mode=ATEMPORAL, posture=INFERRED, confidence=LOW, evidence=evidence + ("ambiguous:conflicting_cues",),
                              intent_basis=QUERY_CUE_INFERENCE, **common)
    if len(all_modes) == 1:
        return TemporalIntent(mode=all_modes[0], posture=INFERRED, confidence=LOW, evidence=evidence,
                              intent_basis=QUERY_CUE_INFERENCE, **common)
    return TemporalIntent(mode=ATEMPORAL, posture=UNSPECIFIED, confidence=None, evidence=evidence, intent_basis=NO_BASIS, **common)


DECLARED_TEMPORAL_KEY = "declared_temporal"
_DECLARED_FIELDS = ("valid_from", "valid_until", "observed_at")


def declared_temporal(value: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Validate caller-declared temporal evidence for a write.

    ``valid_from``/``valid_until`` declare when the proposition applies (valid time);
    ``observed_at`` declares when it was observed. They are recorded as the caller's
    claim (``basis = caller_declared``). They are evidence for applicability, not
    lifecycle: an elapsed ``valid_until`` never refuses the fact at admission, never
    supersedes another fact, and never changes currentness state.
    """

    if not value:
        return None
    if value.get("basis", "caller_declared") != "caller_declared":
        raise ValueError("declared temporal basis must be caller_declared")
    unknown = set(value) - set(_DECLARED_FIELDS) - {"basis"}
    if unknown:
        raise ValueError(f"unknown declared temporal fields: {sorted(unknown)}")
    declared: dict[str, str] = {}
    for key in _DECLARED_FIELDS:
        raw = value.get(key)
        if raw is None:
            continue
        if parse_time(raw) is None:
            raise ValueError(f"declared {key} {raw!r} is not ISO-8601")
        declared[key] = str(raw)
    start, end = parse_time(declared.get("valid_from")), parse_time(declared.get("valid_until"))
    if start is not None and end is not None and end <= start:
        raise ValueError("declared valid_until must be after valid_from")
    if not declared:
        return None
    declared["basis"] = "caller_declared"
    return declared


def resolve_intent(
    query: str,
    temporal_intent: Mapping[str, Any] | TemporalIntent | None = None,
    *,
    reference_time: str | None = None,
) -> TemporalIntent:
    """Explicit caller intent when supplied; otherwise bounded deterministic inference."""

    if temporal_intent is not None:
        return explicit_intent(temporal_intent, reference_time=reference_time)
    return interpret_query(query, reference_time=reference_time)


__all__ = [
    "AS_OF", "ATEMPORAL", "CURRENT", "HISTORICAL", "PROSPECTIVE", "MODES", "RANKED", "TIMELINE",
    "EXPLICIT", "INFERRED", "UNSPECIFIED", "HIGH", "LOW", "INTERPRETER_REF", "INTERPRETER_VERSION",
    "CALLER_DECLARED", "QUERY_LANGUAGE_EXPLICIT", "QUERY_CUE_INFERENCE", "NO_BASIS", "INTENT_BASES", "DECLINE_REASONS",
    "DECLARED_TEMPORAL_KEY", "DeclinedCueSpan", "TemporalCueSpan", "TemporalIntent", "declared_temporal", "explicit_intent", "interpret_query", "parse_time", "resolve_intent",
]
