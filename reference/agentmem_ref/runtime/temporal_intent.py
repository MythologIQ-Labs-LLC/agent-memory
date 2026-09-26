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

* ``explicit``  - supplied by the caller or host; authoritative for this recall.
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
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

INTERPRETER_REF = "agent-memory-deterministic-temporal-cues"
INTERPRETER_VERSION = "1.0.0"

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


def _cues(*phrases: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(r"\b" + phrase + r"\b", re.IGNORECASE) for phrase in phrases)


# Frozen cue lexicon (INTERPRETER_VERSION 1.0.0). High-confidence cues name the temporal
# relationship directly; low-confidence cues are suggestive only and never activate
# temporal ordering on their own (ADR-039 C16).
_LEXICON: dict[str, dict[str, tuple[re.Pattern[str], ...]]] = {
    CURRENT: {
        HIGH: _cues(
            "currently", "current", "right now", "at the moment", "at present", "presently",
            "nowadays", "these days", "as of now", "as of today", "most recent", "latest",
        ),
        LOW: _cues("now", "still", "today", "anymore"),
    },
    HISTORICAL: {
        HIGH: _cues(
            "used to", "previously", "formerly", "originally", "initially", "at first",
            "in the past", "back then", "at the time", "prior to",
        ),
        LOW: _cues("before", "earlier", "ago", "last time", "first time", "once"),
    },
    PROSPECTIVE: {
        HIGH: _cues(
            "upcoming", "scheduled", "next week", "next month", "next year", "tomorrow",
            "planning to", "plan to", "going to", "intend to",
        ),
        LOW: _cues("will", "next", "later", "soon", "future"),
    },
}
_TIMELINE_CUES = _cues(
    "timeline", "history of", "over time", "how did .{0,60}?(change|changed|evolve|evolved|develop)",
    "what changed", "sequence of",
)
_AS_OF_DATE = re.compile(r"\b(?:as of|on|at)\s+(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)
_AS_OF_YEAR = re.compile(r"\b(?:as of|in|during)\s+((?:19|20)\d{2})\b", re.IGNORECASE)


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

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"unknown temporal intent mode {self.mode!r}")
        if self.posture not in {EXPLICIT, INFERRED, UNSPECIFIED}:
            raise ValueError(f"unknown temporal intent posture {self.posture!r}")
        if self.expected_recall_shape not in RECALL_SHAPES:
            raise ValueError(f"unknown recall shape {self.expected_recall_shape!r}")
        if self.posture == INFERRED and self.confidence not in {HIGH, LOW}:
            raise ValueError("inferred temporal intent requires high or low confidence")
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

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = list(self.evidence)
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
    )


def interpret_query(query: str, *, reference_time: str | None = None) -> TemporalIntent:
    """Deterministic, bounded inference of temporal intent from generic cues."""

    shape = RANKED
    shape_evidence: tuple[str, ...] = ()
    for pattern in _TIMELINE_CUES:
        match = pattern.search(query)
        if match:
            shape, shape_evidence = TIMELINE, (f"shape:timeline:{match.group(0).lower()}",)
            break

    date = _AS_OF_DATE.search(query)
    year = None if date else _AS_OF_YEAR.search(query)
    if date or year:
        if date:
            start = date.group(1)
            end_seconds = parse_time(start) + 86400.0
            end = datetime.fromtimestamp(end_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            cue = date.group(0)
        else:
            start, end, cue = f"{year.group(1)}-01-01", f"{int(year.group(1)) + 1}-01-01", year.group(0)
        return TemporalIntent(
            mode=AS_OF,
            posture=INFERRED,
            confidence=HIGH,
            reference_time=reference_time,
            target_start=start,
            target_end=end,
            expected_recall_shape=shape,
            evidence=(f"as_of:{cue.lower()}",) + shape_evidence,
        )

    matched: dict[str, dict[str, list[str]]] = {}
    for mode, levels in _LEXICON.items():
        for level, patterns in levels.items():
            for pattern in patterns:
                match = pattern.search(query)
                if match:
                    matched.setdefault(mode, {}).setdefault(level, []).append(match.group(0).lower())
    if shape == TIMELINE:
        matched.setdefault(HISTORICAL, {}).setdefault(HIGH, [])
    evidence = tuple(
        f"{mode}:{level}:{cue}"
        for mode in sorted(matched)
        for level in sorted(matched[mode])
        for cue in matched[mode][level]
    ) + shape_evidence

    high_modes = sorted(mode for mode, levels in matched.items() if HIGH in levels)
    all_modes = sorted(matched)
    if len(high_modes) == 1:
        mode = high_modes[0]
        return TemporalIntent(mode=mode, posture=INFERRED, confidence=HIGH, reference_time=reference_time,
                              expected_recall_shape=shape, evidence=evidence)
    if len(high_modes) > 1 or len(all_modes) > 1:
        # Conflicting cues: preserve ambiguity rather than choose (ADR-039 C16).
        return TemporalIntent(mode=ATEMPORAL, posture=INFERRED, confidence=LOW, reference_time=reference_time,
                              expected_recall_shape=shape, evidence=evidence + ("ambiguous:conflicting_cues",))
    if len(all_modes) == 1:
        return TemporalIntent(mode=all_modes[0], posture=INFERRED, confidence=LOW, reference_time=reference_time,
                              expected_recall_shape=shape, evidence=evidence)
    return TemporalIntent(mode=ATEMPORAL, posture=UNSPECIFIED, confidence=None, reference_time=reference_time,
                          expected_recall_shape=shape, evidence=evidence)


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
    "DECLARED_TEMPORAL_KEY", "TemporalIntent", "declared_temporal", "explicit_intent", "interpret_query", "parse_time", "resolve_intent",
]
