"""Read-path cross-fact currentness (#671, Option A; docs/plan-671-cross-fact-currentness.md).

A typed, open, unapplied ``state_change_candidate`` relation persisted on a newer fact S may
limit the *applicability* of the older fact T for an explicit-current recall, and nothing else.
The limitation is evidence for one currentness decision under the explicit basis
``interpreted_cross_fact``: it mutates no lifecycle state, applies no proposal, corrects
nothing, removes nothing from admission, and is never computed from recency or a clock (a
declared clock can only refuse, G13).

Guards G1-G13 must all hold; the first failing guard is the refusal reason. Write provenance
(``write_provenance``, C1) supplies the actor, source and tenant identities the guards compare:
a fact without it (any fact committed before Runtime Baseline v5) never participates.

G12 is a positive structural requirement on S's text, versioned ``ASSERTION_FILTER_VERSION``:
only a single first-party declarative sentence, whose change marker is not preceded by another
entity's possessive or a clause boundary and whose value is a bounded proper name, number-unit
or single token, with no hedge, negation, condition, attribution or interjection anywhere,
qualifies. The residual it accepts is stated in the plan: a deliberately Capitalised two-token
value from the same actor and declared source.

Assertion filter 6.1.0 (#732 R4, docs/plan-732-remediation.md) adds a typed branch only. A
``typed_slot`` or ``typed_link`` relation is accepted at G3 only when S carries a typed
proposition with basis ``caller_declared`` or ``extracted:*``; G6 reads its
``typed_ineligible_reasons``; G12 reads its persisted typed flags (any true flag refuses with
``typed_assertion_not_assertive:<flag>``) and never re-checks a typed relation against S's text.
Interpreted relations pass G3, G6 and G12 exactly as in 6.0.0; every other guard is unchanged.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Callable, Mapping, Sequence

from . import proposition_semantics as semantics
from . import typed_proposition as typed
from .temporal_intent import DECLARED_TEMPORAL_KEY, TemporalIntent, parse_time

WRITE_PROVENANCE_KEY = "write_provenance"
WRITE_PROVENANCE_VERSION = "1.0.0"
CROSS_FACT_BASIS = "interpreted_cross_fact"
CROSS_FACT_LABEL = "limited_by_cross_fact_state_change"
ASSERTION_FILTER_VERSION = "6.1.0"
SOURCE_REF_MAX = 256
ACCEPTED_RELATION_BASES = ("single_valued_replacement_marker",)
ACCEPTED_RELATION_BASIS_PREFIXES = ("explicit_termination:",)
GUARDS = tuple(f"G{index}" for index in range(1, 14))


def default_source_ref(actor_id: str) -> str:
    return f"actor:{actor_id}"


def validate_source_ref(source_ref: str | None) -> str | None:
    if source_ref is None:
        return None
    if not isinstance(source_ref, str) or not source_ref.strip() or len(source_ref) > SOURCE_REF_MAX:
        raise ValueError(f"source_ref must be a non-empty string of at most {SOURCE_REF_MAX} characters")
    return source_ref


def write_provenance(*, actor_id: str, tenant: str, purpose: str, operation: str, source_ref: str | None) -> dict:
    """C1: the immutable per-fact identities the guards compare (never caller-overridable)."""

    channel = {"promotion": "caller_observation", "correction": "caller_correction"}.get(operation, f"other:{operation}")
    return {
        "version": WRITE_PROVENANCE_VERSION,
        "actor_id": actor_id,
        "tenant": tenant,
        "purpose": purpose,
        "channel": channel,
        "source_ref": source_ref or default_source_ref(actor_id),
    }


# ---------------------------------------------------------------------------- G12

_APOSTROPHES = "’‘ʼ＇"
_CLOSED_CLASS = frozenset(
    """a an the this that these those my your his her its our their mine yours hers ours theirs
    i me you he him she it we us they them myself yourself himself herself itself ourselves themselves
    who whom whose which what someone somebody anyone anybody everyone everybody one some any each every
    all both either neither none no nor not never nothing nobody about above across after against along
    among around as at before behind below beneath beside besides between beyond by despite down during
    except for from in inside into like near of off on onto out outside over past since than through
    throughout till to toward towards under underneath until up upon via with within without per and but
    or so yet because although though while whereas if unless whether once whenever wherever where when
    why how then also too very just only even still already am is are was were be been being have has had
    having do does did doing will would shall should can could may might must ought there here n't s t ll
    ve re d o""".split()
)
_ATTRIBUTION_HEDGE = re.compile(
    r"\b(according|per|via|reportedly|allegedly|rumou?r|heard|told|said|says|stated|wrote|claims?|tip|spam|"
    r"forwarded|supposedly|unconfirmed|apparently|maybe|might|may|perhaps|possibly|probably|trust|lol|jk|haha|"
    r"lmao|kidding|joke|joking|allegation|source|sources)\b",
    re.IGNORECASE,
)
_NEGATOR = re.compile(r"\b(not|never|no|nobody|nothing|neither|nor)\b|n't")
_SUBORDINATOR = re.compile(r"\b(if|unless|whether|assuming|provided|supposing|though|although|even)\b")
_EPISTEMIC = re.compile(
    r"unverified|unconfirmed|unclear|uncertain|unsure|perchance|hypothetical|supposed|alleged|purported|"
    r"rumou?red|reputed|disputed|doubtful|questionable|presumed|untrue|false|fake|wrong|dubious|hearsay|"
    r"guessed|reckoned|bogus|fabricated|invented|made-up|mistaken"
)
_PLACE_ORG_SUFFIX = frozenset(
    "City Town County Bay Beach Springs Falls Heights Park Valley Island Labs Lab Inc Corp Corporation "
    "Company Co LLC Ltd Group Bank University College School Hospital Systems Technologies Partners".split()
)
_UNIT = re.compile(
    r"dollars?|usd|euros?|eur|pounds?|gbp|yen|cents?|km|kilometers?|kilometres?|miles?|m|meters?|metres?|cm|mm|"
    r"feet|foot|ft|inches?|in|kg|kilograms?|g|grams?|lbs?|ounces?|oz|seconds?|minutes?|hours?|days?|weeks?|"
    r"months?|years?|percent|%|points?|items?|people|users?|units?"
)
_SUFFIX_ALLOWED = re.compile(r"^(\s*(now|today|currently|anymore|these days))*\s*[.!]?\s*$")
_VALUE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@&'+-]*$")


def _normalise(text: str) -> str:
    for mark in _APOSTROPHES:
        text = text.replace(mark, "'")
    text = text.replace("“", '"').replace("”", '"')
    return unicodedata.normalize("NFKC", text.strip())


def _capitalised(token: str) -> bool:
    return token[0].isupper() and token[1:] == token[1:].lower() if len(token) > 1 else token.isupper()


def _identifier(token: str) -> bool:
    return any(char.isdigit() for char in token) or "_" in token


def _value_shape_ok(span: Sequence[str]) -> bool:
    if len(span) == 1:
        return True
    if len(span) == 2 and _identifier(span[0]) and _UNIT.fullmatch(span[1]):
        return True
    if len(span) == 2 and all(_capitalised(token) for token in span):
        return True
    return len(span) == 3 and all(_capitalised(token) for token in span) and span[2] in _PLACE_ORG_SUFFIX


def assertion_refusal(text: str, write_semantics: Mapping[str, Any], relation: Mapping[str, Any]) -> str | None:
    """G12: the first failing structural rule ("1".."7"), or None when S qualifies."""

    normalised = _normalise(text or "")
    lowered = normalised.lower()
    if not normalised:
        return "1"
    # (1) one sentence: no question, parenthetical or dash; one terminal mark at the end at most
    if any(mark in normalised for mark in "?()—–") or "--" in normalised or re.search(r"\w\s-\s\w", normalised):
        return "1"
    body = normalised[:-1] if normalised[-1:] in ".!" else normalised
    if "!" in body or re.search(r"\.\s", body):
        return "1"
    # (2) the prefix before the first change marker
    markers = list((write_semantics.get("markers") or {}).get("change") or ())
    basis = str(relation.get("basis") or "")
    if basis.startswith("explicit_termination:"):
        markers.append(basis.split(":", 1)[1])
    positions = [match.start() for match in (re.search(r"\b" + re.escape(str(marker).lower()) + r"\b", lowered) for marker in markers) if match]
    if not positions:
        return "2"
    prefix = lowered[: min(positions)]
    if re.search(r"[,:;\"]", prefix):
        return "2"
    proposition = write_semantics.get("proposition") or {}
    head = (str(proposition.get("property") or "").split() or [""])[0]
    for match in re.finditer(r"('s|s')(\s+(\w+))?", prefix):
        possessed = match.group(3)
        if not possessed or not head or possessed[:4] != head[:4]:
            return "2"
    # (3) the persisted value must be located
    value = str(proposition.get("value") or "").lower()
    index = lowered.rfind(value) if value else -1
    if index < 0:
        return "3"
    # (4) the value is bounded positively (casing read from the text span)
    span = normalised[index : index + len(value)].split()
    if not span or not all(_VALUE_TOKEN.match(token) for token in span) or any(token.lower() in _CLOSED_CLASS for token in span):
        return "4"
    if any(token.lower().endswith("ly") or _EPISTEMIC.fullmatch(token.lower()) for token in span[1:]):
        return "4"
    if not _value_shape_ok(span):
        return "4"
    # (5) only temporal adverbs and terminal punctuation after the value
    if not _SUFFIX_ALLOWED.match(lowered[index + len(value) :]):
        return "5"
    # (6) no negator (outside the termination marker 'no longer') and no subordinator anywhere
    if _NEGATOR.search(lowered.replace("no longer", "")) or _SUBORDINATOR.search(lowered):
        return "6"
    # (7) the attribution / hedge / interjection layer (whole text; 'May <digit>' is a date)
    if _ATTRIBUTION_HEDGE.search(re.sub(r"\bMay(?=\s+\d)", "", normalised)):
        return "7"
    return None


# ---------------------------------------------------------------------------- G1-G13


def _typed_relation(relation: Mapping[str, Any]) -> bool:
    return str(relation.get("basis") or "") in typed.TYPED_RELATION_BASES


def _relation_basis_accepted(basis: str, write_semantics: Mapping[str, Any]) -> bool:
    if basis in typed.TYPED_RELATION_BASES:
        return typed.typed_basis_accepted(write_semantics.get("typed_proposition"))
    return basis in ACCEPTED_RELATION_BASES or basis.startswith(ACCEPTED_RELATION_BASIS_PREFIXES)


def _not_proposable(write_semantics: Mapping[str, Any], relation: Mapping[str, Any]) -> bool:
    """G6: typed relations read ``typed_ineligible_reasons``; interpreted ones are unchanged."""

    if _typed_relation(relation):
        return bool(write_semantics.get("typed_ineligible_reasons"))
    markers = write_semantics.get("markers") or {}
    return bool(markers.get("hedge") or markers.get("self_claims") or write_semantics.get("proposal_ineligible_reasons"))


def typed_assertion_refusal(write_semantics: Mapping[str, Any]) -> str | None:
    """G12 for a typed relation: the persisted flags are the assertion evidence; no text re-check."""

    flags = typed.true_flags(write_semantics.get("typed_proposition"))
    return f"typed_assertion_not_assertive:{flags[0]}" if flags else None


def _clock_refusal(source_attributes: Mapping[str, Any], target_attributes: Mapping[str, Any]) -> str | None:
    """G13: declared clocks may refuse the relation's direction, never choose a winner."""

    source = source_attributes.get(DECLARED_TEMPORAL_KEY) or {}
    target = target_attributes.get(DECLARED_TEMPORAL_KEY) or {}
    for kind in ("observed_at", "valid_from"):
        if target.get(kind):
            if not source.get(kind):
                return "declared_clock_unconfirmed"
            if parse_time(source[kind]) < parse_time(target[kind]):
                return "declared_clock_contradicts_direction"
    return None


def evaluate(
    admitted: Sequence[str],
    intent: TemporalIntent,
    *,
    fact_lookup: Callable[[str], Any],
    proposal_status: Callable[[Mapping[str, Any]], str],
    fact_scope: Callable[[str], Mapping[str, Any] | None],
    same_scope: Callable[[Mapping[str, Any] | None, Mapping[str, Any]], bool],
    explicit_current: Callable[[TemporalIntent], bool],
) -> dict[str, dict[str, Any]]:
    """C2: {target_uuid: {"accepted": [evidence...], "refusal": reason | None}} (pure read).

    Under any intent outside the explicit-current profile (G1) nothing is returned, so
    historical, as-of, atemporal and inferred recalls carry no cross-fact field at all.
    """

    if not explicit_current(intent):
        return {}
    admitted = list(admitted)
    admitted_set = set(admitted)
    out: dict[str, dict[str, Any]] = {}

    def note(target: str, *, reason: str | None = None, evidence: dict | None = None) -> None:
        record = out.setdefault(target, {"accepted": [], "refusal": None})
        if evidence is not None:
            record["accepted"].append(evidence)
        elif record["refusal"] is None:
            record["refusal"] = reason

    staged: list[tuple[str, str, Mapping[str, Any]]] = []
    for source_uuid in admitted:
        source = fact_lookup(source_uuid)
        source_attributes = (getattr(source, "attributes", None) or {}) if source is not None else {}
        write_semantics = source_attributes.get(semantics.WRITE_SEMANTICS_KEY) or {}
        for relation in write_semantics.get("relations", ()) or ():
            target_uuid = relation.get("other_fact_uuid")
            if target_uuid not in admitted_set or target_uuid == source_uuid:
                continue
            target = fact_lookup(target_uuid)
            target_attributes = (getattr(target, "attributes", None) or {}) if target is not None else {}
            reason = _refusal(source, target, source_attributes, target_attributes, write_semantics, relation,
                              source_uuid, target_uuid, proposal_status, fact_scope, same_scope)
            if reason is None:
                staged.append((source_uuid, target_uuid, relation))
            else:
                note(target_uuid, reason=reason)
    accepted_pairs = {(source_uuid, target_uuid) for source_uuid, target_uuid, _ in staged}
    for source_uuid, target_uuid, relation in staged:
        if (target_uuid, source_uuid) in accepted_pairs:  # G11 (defensive; relations live on the newer fact)
            note(target_uuid, reason="contradictory_cross_fact_evidence")
            continue
        note(target_uuid, evidence={
            "basis": CROSS_FACT_BASIS,
            "source_fact_uuid": source_uuid,
            "proposal_id": relation["proposal"]["proposal_id"],
            "relation_basis": relation["basis"],
            "guards": list(GUARDS),
            "assertion_filter_version": ASSERTION_FILTER_VERSION,
            "authority_effect": "none",
        })
    return out


def _refusal(source, target, source_attributes, target_attributes, write_semantics, relation,
             source_uuid, target_uuid, proposal_status, fact_scope, same_scope) -> str | None:
    if relation.get("classification") != semantics.STATE_CHANGE_CANDIDATE:  # G2
        return "relation_not_state_change"
    if not _relation_basis_accepted(str(relation.get("basis") or ""), write_semantics):  # G3
        return "relation_basis_not_accepted"
    proposal = relation.get("proposal")
    if not proposal or proposal.get("applied") is not False or proposal.get("authority_effect") != "none":  # G4
        return "no_open_proposal"
    status = proposal_status(proposal)
    if status != "open":  # G5: live, undisputed, untombstoned, unapplied
        return f"proposal_not_open:{status}"
    if _not_proposable(write_semantics, relation):  # G6
        return "hedged_or_untrusted_claim"
    source_provenance = source_attributes.get(WRITE_PROVENANCE_KEY)
    target_provenance = target_attributes.get(WRITE_PROVENANCE_KEY)
    if not source_provenance or not target_provenance:  # G7
        return "cross_fact_identity_unavailable"
    if not source_provenance.get("actor_id") or source_provenance.get("actor_id") != target_provenance.get("actor_id"):  # G8
        return "actor_mismatch"
    if (source_provenance.get("channel") != "caller_observation" or target_provenance.get("channel") != "caller_observation"
            or source_provenance.get("source_ref") != target_provenance.get("source_ref")
            or source_provenance.get("tenant") != target_provenance.get("tenant")
            or source_provenance.get("purpose") != target_provenance.get("purpose")):  # G9
        return "source_mismatch"
    source_scope, target_scope = fact_scope(source_uuid), fact_scope(target_uuid)
    if (not source_scope or not target_scope or not same_scope(source_scope, target_scope)
            or set(source_scope.get("required_domain_refs", ())) != set(target_scope.get("required_domain_refs", ()))
            or getattr(source, "group_id", None) != getattr(target, "group_id", None)):  # G10
        return "scope_mismatch"
    if _typed_relation(relation):  # G12, typed branch
        assertion = typed_assertion_refusal(write_semantics)
        if assertion is not None:
            return assertion
    else:  # G12
        assertion = assertion_refusal(getattr(source, "fact_text", "") or "", write_semantics, relation)
        if assertion is not None:
            return f"change_evidence_not_assertive:{assertion}"
    return _clock_refusal(source_attributes, target_attributes)  # G13


__all__ = [
    "ASSERTION_FILTER_VERSION",
    "CROSS_FACT_BASIS",
    "CROSS_FACT_LABEL",
    "WRITE_PROVENANCE_KEY",
    "assertion_refusal",
    "typed_assertion_refusal",
    "default_source_ref",
    "evaluate",
    "validate_source_ref",
    "write_provenance",
]
