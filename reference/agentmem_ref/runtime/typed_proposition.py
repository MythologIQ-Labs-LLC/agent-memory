"""Typed write-time propositions (#732 remediation R1 and R3; docs/plan-732-remediation.md).

A typed proposition is a closed record a caller declares with ``AgentMemory.remember(...,
proposition=...)`` or an opted-in extractor proposes at write time::

    {"subject": str, "attribute": str, "value": str,
     "assertion": "state" | "change",
     "cardinality": "single" | "multi" | null,
     "replaces_value": str | null,
     "flags": {"hedged", "attributed_to_other", "conditional", "negated",
               "joke_or_sarcasm", "quoted_or_forwarded", "coexistent": bool}}

Its identity is the typed slot ``typed:<norm(subject)>|<norm(attribute)>``: lower-cased,
whitespace collapsed, edge punctuation stripped; no stemming and no synonym table.

Classifier 1.1.0 relates a write that carries a typed proposition to retained facts of the
same typed slot (``typed_slot``) or to one deterministically confirmed link (``typed_link``).
A write without one is classified by 1.0.0 unchanged. Nothing here is authority::

    typed declaration != truth          typed relation != authority to replace
    extractor output != caller declaration

Every output carries ``authority_effect: none``; a proposal is still applied only through the
existing correction lifecycle under PAMA.
"""

from __future__ import annotations

import re
import string
from typing import Any, Iterable, Mapping

from . import proposition_semantics as semantics

TYPED_SLOT_PREFIX = "typed:"
CALLER_DECLARED = "caller_declared"
EXTRACTED_PREFIX = "extracted:"
TYPED_SLOT = "typed_slot"
TYPED_LINK = "typed_link"
TYPED_LINK_UNCONFIRMED = "typed_link_unconfirmed"
TYPED_RELATION_BASES = (TYPED_SLOT, TYPED_LINK)
ASSERTIONS = ("state", "change")
CARDINALITIES = ("single", "multi")
FLAGS = ("hedged", "attributed_to_other", "conditional", "negated", "joke_or_sarcasm", "quoted_or_forwarded",
         "coexistent")
REQUIRED_FIELDS = ("subject", "attribute", "value", "assertion")
OPTIONAL_FIELDS = ("cardinality", "replaces_value", "flags")
MAX_TEXT = 200
TRIVIAL_VALUES = frozenset({"yes", "no", "on", "off", "true", "false", "none", "n/a"})
PARSER_REASONS = ("proposition_unknown", "proposition_ambiguous")

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_EDGE = string.punctuation + string.whitespace
_TOKEN = re.compile(r"[a-z0-9]+")


def norm(text: str) -> str:
    """Lower-case, collapse whitespace, strip edge punctuation. No stemming, no synonyms."""

    return " ".join(" ".join(str(text).lower().split()).strip(_EDGE).split())


def typed_slot(subject: str, attribute: str) -> str:
    return f"{TYPED_SLOT_PREFIX}{norm(subject)}|{norm(attribute)}"


def _text(record: Mapping[str, Any], key: str, *, nullable: bool = False) -> str | None:
    value = record.get(key)
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT or _CONTROL.search(value):
        raise ValueError(f"proposition.{key} must be a non-empty string of at most {MAX_TEXT} characters "
                         "without control characters")
    if not norm(value):
        raise ValueError(f"proposition.{key} must contain more than punctuation")
    return value


def _flags(value: Any) -> dict[str, bool]:
    if value is None:
        return dict.fromkeys(FLAGS, False)
    if not isinstance(value, Mapping):
        raise ValueError("proposition.flags must be an object")
    unknown = sorted(set(value) - set(FLAGS))
    if unknown:
        raise ValueError(f"proposition.flags has unknown keys: {unknown}")
    if any(not isinstance(flag, bool) for flag in value.values()):
        raise ValueError("proposition.flags values must be booleans")
    return {name: bool(value.get(name, False)) for name in FLAGS}


def validate(record: Any) -> dict[str, Any]:
    """The closed R1 contract: a normalized copy, or ``ValueError``. Grants nothing."""

    if not isinstance(record, Mapping):
        raise ValueError("proposition must be an object")
    unknown = sorted(set(record) - set(REQUIRED_FIELDS) - set(OPTIONAL_FIELDS))
    if unknown:
        raise ValueError(f"proposition has unknown keys: {unknown}")
    missing = [key for key in REQUIRED_FIELDS if key not in record]
    if missing:
        raise ValueError(f"proposition is missing required keys: {missing}")
    if record["assertion"] not in ASSERTIONS:
        raise ValueError(f"proposition.assertion must be one of {ASSERTIONS}")
    cardinality = record.get("cardinality")
    if cardinality is not None and cardinality not in CARDINALITIES:
        raise ValueError(f"proposition.cardinality must be one of {CARDINALITIES} or null")
    return {
        "subject": _text(record, "subject"),
        "attribute": _text(record, "attribute"),
        "value": _text(record, "value"),
        "assertion": record["assertion"],
        "cardinality": cardinality,
        "replaces_value": _text(record, "replaces_value", nullable=True),
        "flags": _flags(record.get("flags")),
    }


def typed_record(validated: Mapping[str, Any], basis: str, *, updates_fact_uuid: str | None = None) -> dict[str, Any]:
    """The persisted ``typed_proposition``: the validated record, its basis and its typed slot."""

    record = {**dict(validated), "flags": dict(validated["flags"]), "basis": basis,
              "slot": typed_slot(validated["subject"], validated["attribute"])}
    if basis.startswith(EXTRACTED_PREFIX):
        record["updates_fact_uuid"] = updates_fact_uuid
    return record


def typed_basis_accepted(typed: Mapping[str, Any] | None) -> bool:
    basis = str((typed or {}).get("basis") or "")
    return basis == CALLER_DECLARED or (basis.startswith(EXTRACTED_PREFIX) and len(basis) > len(EXTRACTED_PREFIX))


def true_flags(typed: Mapping[str, Any] | None) -> list[str]:
    flags = (typed or {}).get("flags") or {}
    return [name for name in FLAGS if flags.get(name)]


def typed_ineligible_reasons(interpretation: Mapping[str, Any], typed: Mapping[str, Any]) -> list[str]:
    """R3 (Q1): the interpreter's reasons without the parser-dependent ones, plus a typed hedge.

    ``hedged`` is the conservative OR of the typed flag and the interpreter's lexical hedge
    scan; ``untrusted_self_claim`` is the interpreter's self-claim scan.
    """

    reasons = [r for r in interpretation.get("proposal_ineligible_reasons") or () if r not in PARSER_REASONS]
    if (typed.get("flags") or {}).get("hedged") and "hedged" not in reasons:
        reasons.insert(0, "hedged")
    return reasons


# --------------------------------------------------------------------------- R3 link confirmation


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(norm(text))


def _occurs(needle: list[str], haystack: list[str]) -> bool:
    width = len(needle)
    return bool(needle) and any(haystack[i:i + width] == needle for i in range(len(haystack) - width + 1))


def _interpreted_value(other: Mapping[str, Any] | None) -> str | None:
    proposition = (other or {}).get("proposition") or {}
    return proposition.get("value") if proposition.get("status") == semantics.KNOWN else None


def replaces_value_confirms(typed: Mapping[str, Any], other_text: str, other: Mapping[str, Any] | None) -> bool:
    """U1: the value-text branch, applied only to a linked fact without a typed proposition."""

    replaced, value = norm(typed.get("replaces_value") or ""), norm(typed.get("value") or "")
    if not replaced or replaced == value or len(replaced) < 2 or replaced in TRIVIAL_VALUES:
        return False
    interpreted = _interpreted_value(other)
    if re.sub(r"[\s.,]", "", replaced).isdigit() and interpreted != replaced:
        return False
    return interpreted == replaced or _occurs(_tokens(replaced), _tokens(other_text))


def link_confirmed(typed: Mapping[str, Any], other_text: str, other: Mapping[str, Any] | None) -> bool:
    """R3 (ii)/(iii) for a link whose target already passed the candidate filter (i).

    A typed target must share the typed slot (T2): a different slot is a different property
    and never confirms. Only an untyped target may confirm through the value text.
    """

    other_typed = (other or {}).get("typed_proposition")
    if other_typed:
        return other_typed.get("slot") == typed["slot"]
    return replaces_value_confirms(typed, other_text, other)


# --------------------------------------------------------------------------- R3 classification


def _kind(typed: Mapping[str, Any], other_value: str, other_cardinality: str | None, base: str) -> tuple[str, str]:
    if norm(typed["value"]) == norm(other_value):
        return semantics.SAME_VALUE, base
    if "multi" in (typed.get("cardinality"), other_cardinality):
        return semantics.COEXISTENCE, base
    flags = true_flags(typed)
    if flags:
        return semantics.UNRESOLVED, f"{base}_not_assertive:" + ",".join(flags)
    if typed.get("assertion") != "change":
        return semantics.UNRESOLVED, f"{base}_without_change_assertion"
    return semantics.STATE_CHANGE_CANDIDATE, base


def _relation(kind: str, basis: str, fact_uuid: str, memory_ref: str, slot: str) -> dict[str, Any]:
    return {"classification": kind, "basis": basis, "other_fact_uuid": fact_uuid, "other_memory_ref": memory_ref,
            "slot": slot}


def _proposal(new_fact_uuid: str, fact_uuid: str, memory_ref: str, new_text: str, observed_at: str | None) -> dict:
    return {
        "proposal_id": semantics.proposal_id(new_fact_uuid, fact_uuid,
                                             classifier_version=semantics.TYPED_CLASSIFIER_VERSION),
        "operation": "correction",
        "replacement_kind": "state_change",
        "target_reference": memory_ref,
        "target_fact_uuid": fact_uuid,
        "source_fact_uuid": new_fact_uuid,
        "replacement_text": new_text,
        "effective_no_later_than": observed_at,
        "applied": False,
        "authority_effect": "none",
        "application_path": "AgentMemory.correct(replacement_kind='state_change') under PAMA",
    }


def classify_typed(
    typed: Mapping[str, Any],
    reasons: list[str],
    new_fact_uuid: str,
    new_text: str,
    retained: Iterable[tuple[str, str, str, Mapping[str, Any] | None]],
    *,
    link: tuple[str, str] | None = None,
    link_is_candidate: bool = False,
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    """Classifier 1.1.0: typed relations against filtered retained facts.

    ``retained`` holds ``(uuid, memory ref, text, stored write semantics)`` for every filtered
    candidate: same-typed-slot facts and, when present, the linked fact. ``link`` is the
    linked ``(uuid, memory ref)`` when the extractor named one, and ``link_is_candidate`` says
    whether it was among the candidates the extractor was given (R3 (i)). A link that is not a
    filtered candidate, or does not confirm, is recorded ``unresolved`` / ``typed_link_unconfirmed``.
    """

    relations: list[dict[str, Any]] = []
    linked = link[0] if link and link_is_candidate else None
    confirmed = False
    for fact_uuid, memory_ref, text, other in sorted(retained, key=lambda item: item[0]):
        other_typed = (other or {}).get("typed_proposition")
        if fact_uuid == linked and link_confirmed(typed, text, other):
            base, confirmed = TYPED_LINK, True
            other_value = (other_typed or {}).get("value") or typed.get("replaces_value") or ""
        elif other_typed and other_typed.get("slot") == typed["slot"]:
            base, other_value = TYPED_SLOT, other_typed.get("value") or ""
        else:
            continue
        kind, basis = _kind(typed, other_value, (other_typed or {}).get("cardinality"), base)
        if kind == semantics.STATE_CHANGE_CANDIDATE and reasons:
            kind, basis = semantics.UNRESOLVED, "change_evidence_not_proposable:" + ",".join(reasons)
        relation = _relation(kind, basis, fact_uuid, memory_ref, typed["slot"])
        if kind == semantics.STATE_CHANGE_CANDIDATE:
            relation["proposal"] = _proposal(new_fact_uuid, fact_uuid, memory_ref, new_text, observed_at)
        relations.append(relation)
    if link and not confirmed:
        relations.append(_relation(semantics.UNRESOLVED, TYPED_LINK_UNCONFIRMED, link[0], link[1], typed["slot"]))
    return relations


__all__ = [
    "ASSERTIONS", "CALLER_DECLARED", "CARDINALITIES", "EXTRACTED_PREFIX", "FLAGS", "TYPED_LINK",
    "TYPED_LINK_UNCONFIRMED", "TYPED_RELATION_BASES", "TYPED_SLOT", "classify_typed", "link_confirmed", "norm",
    "replaces_value_confirms", "true_flags", "typed_basis_accepted", "typed_ineligible_reasons", "typed_record",
    "typed_slot", "validate",
]
