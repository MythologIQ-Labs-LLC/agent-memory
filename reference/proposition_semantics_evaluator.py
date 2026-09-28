#!/usr/bin/env python3
"""Evaluator contract for write-time proposition interpretation against accepted gold (#594).

Accepted gold is an immutable acceptance manifest over a byte-frozen draft source.
``load_gold`` verifies that source by SHA-256 before materializing its items. Direct
loading of draft annotation files remains refused.

Predictions are compared field by field. There is no aggregate score. Each failure
class the issue names has its own counter:

* ``wrong_slot``: gold known, predicted known, entity or property differs;
* ``wrong_value``: slot matches, value does not;
* ``over_eager_single_valued``: predicted single_valued where gold is multi_valued or hierarchical;
* ``coexistence_as_replacement``: gold coexistence, prediction carries a change/replacement signal;
* ``aspect_over_classification``: predicted an aspect where gold has none;
* ``aspect_mismatch``: both have an aspect and they differ;
* ``unknown_promoted_to_known``: gold unknown or ambiguous, predicted known;
* ``timestamp_leakage``: a prediction was produced with a declared observation anchor, or any
  field carries a source timestamp string.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

EVALUATOR_VERSION = "0.2.0"
STATUSES = ("known", "ambiguous", "unknown")
FIRST_PERSON = {"i", "me", "my", "myself", "user", "speaker", "the user"}
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = {"a", "an", "the", "of", "to", "my", "in", "at", "for", "and", "on", "with"}


class GoldNotAccepted(ValueError):
    """Raised when an annotation set has not been accepted by the maintainer."""


def _accepted(document: Mapping[str, Any]) -> bool:
    labels = set(document.get("status_labels", ()))
    acceptance = document.get("acceptance") or {}
    return not (labels & {"DRAFT", "NOT ACCEPTED GOLD", "NOT SCORED"}) and bool(
        acceptance.get("accepted_by") and acceptance.get("accepted_at")
    )


def load_gold(path: Path | str) -> dict[str, Any]:
    """Load accepted gold, verifying any immutable source manifest before use."""

    path = Path(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if not _accepted(document):
        labels = sorted(set(document.get("status_labels", ())))
        raise GoldNotAccepted(f"{path}: annotation set is not accepted gold (labels={labels})")

    source = document.get("source") or {}
    if source:
        source_path = path.parent / str(source.get("file") or "")
        expected = str(source.get("sha256") or "")
        if not expected or not source_path.is_file():
            raise GoldNotAccepted(f"{path}: accepted source is missing or unpinned")
        source_bytes = source_path.read_bytes()
        actual = hashlib.sha256(source_bytes).hexdigest()
        if actual != expected:
            raise GoldNotAccepted(f"{path}: accepted source digest mismatch ({actual} != {expected})")
        source_document = json.loads(source_bytes)
        if source.get("annotation_set") and source_document.get("annotation_set") != source.get("annotation_set"):
            raise GoldNotAccepted(f"{path}: accepted source annotation_set mismatch")
        expected_count = (document.get("acceptance") or {}).get("item_count")
        if expected_count is not None and len(source_document.get("items", ())) != int(expected_count):
            raise GoldNotAccepted(f"{path}: accepted source item-count mismatch")
        materialized = dict(document)
        materialized["items"] = source_document.get("items", [])
        materialized["accepted_source"] = {
            "file": source_path.name,
            "sha256": actual,
            "annotation_set": source_document.get("annotation_set"),
        }
        return materialized

    if "items" not in document:
        raise GoldNotAccepted(f"{path}: accepted gold has no items or immutable source")
    return document


def _entity(value: Any) -> str:
    text = " ".join(_TOKEN.findall(str(value or "").lower()))
    return "user" if text in FIRST_PERSON else text


def _property(value: Any) -> str:
    return " ".join(_TOKEN.findall(str(value or "").lower().replace("_", " ")))


def _value_tokens(value: Any) -> frozenset[str]:
    return frozenset(token for token in _TOKEN.findall(str(value or "").lower()) if token not in _STOP)


def value_matches(predicted: Any, gold: Any) -> bool:
    """Containment either way over content tokens; empty never matches."""

    left, right = _value_tokens(predicted), _value_tokens(gold)
    return bool(left) and bool(right) and (left <= right or right <= left)


def property_matches(predicted: Any, gold: Any, aliases: Mapping[str, Iterable[str]]) -> bool:
    gold_key = _property(gold)
    accepted = {gold_key} | {_property(alias) for alias in aliases.get(gold_key, ())}
    return _property(predicted) in accepted


def evaluate(
    gold_items: Sequence[Mapping[str, Any]],
    predictions: Mapping[str, Mapping[str, Any]],
    *,
    property_aliases: Mapping[str, Iterable[str]] | None = None,
    source_timestamps: Iterable[str] = (),
) -> dict[str, Any]:
    """Compare predictions with gold item by item; return per-field counters, never one score."""

    aliases = property_aliases or {}
    stamps = [stamp for stamp in source_timestamps if stamp]
    confusion = {gold: Counter() for gold in STATUSES}
    counters: Counter[str] = Counter()
    cardinality = Counter()
    aspect = Counter()
    findings: list[dict[str, str]] = []
    missing: list[str] = []

    def flag(kind: str, item_id: str) -> None:
        counters[kind] += 1
        findings.append({"item_id": item_id, "class": kind})

    for gold in gold_items:
        item_id = str(gold["item_id"])
        prediction = predictions.get(item_id)
        if prediction is None:
            missing.append(item_id)
            continue
        gold_status, predicted_status = gold["status"], prediction.get("status", "unknown")
        confusion[gold_status][predicted_status] += 1
        if predicted_status == "known" and gold_status != "known":
            flag("unknown_promoted_to_known", item_id)
        if predicted_status == "known" and gold_status == "known":
            principal = gold["propositions"][gold["principal"]]
            same_entity = _entity(prediction.get("entity")) == _entity(principal["entity"])
            same_property = property_matches(prediction.get("property"), principal["property"], aliases)
            if not (same_entity and same_property):
                flag("wrong_slot", item_id)
            elif not value_matches(prediction.get("value"), principal["value"]):
                flag("wrong_value", item_id)
            else:
                counters["slot_and_value_correct"] += 1
        predicted_cardinality = prediction.get("cardinality", "unknown")
        cardinality[(gold["cardinality"], predicted_cardinality)] += 1
        if predicted_cardinality == "single_valued" and gold["cardinality"] in {"multi_valued", "hierarchical"}:
            flag("over_eager_single_valued", item_id)
        if gold.get("coexistence_marker") == "yes" and (prediction.get("change") or prediction.get("replacement")):
            flag("coexistence_as_replacement", item_id)
        predicted_aspect = prediction.get("aspect") or "none_unknown"
        aspect[(gold["temporal_aspect"], predicted_aspect)] += 1
        if predicted_aspect != "none_unknown" and gold["temporal_aspect"] == "none_unknown":
            flag("aspect_over_classification", item_id)
        elif predicted_aspect != "none_unknown" and predicted_aspect != gold["temporal_aspect"]:
            flag("aspect_mismatch", item_id)
        rendered = json.dumps(prediction, sort_keys=True)
        if prediction.get("declared_observed_at") or any(stamp in rendered for stamp in stamps):
            flag("timestamp_leakage", item_id)

    return {
        "evaluator_version": EVALUATOR_VERSION,
        "aggregate_score": "not_defined",
        "items_evaluated": sum(sum(row.values()) for row in confusion.values()),
        "missing_predictions": missing,
        "status_confusion": {gold: dict(sorted(row.items())) for gold, row in confusion.items()},
        "failure_counts": dict(sorted(counters.items())),
        "cardinality_pairs": {f"{g}->{p}": n for (g, p), n in sorted(cardinality.items())},
        "aspect_pairs": {f"{g}->{p}": n for (g, p), n in sorted(aspect.items())},
        "findings": findings,
    }


def normalize_runtime_prediction(interpretation: Mapping[str, Any], *, declared_observed_at: str | None = None) -> dict[str, Any]:
    """Map one ``interpret_write`` result to the evaluator's prediction record."""

    proposition = interpretation.get("proposition") or {}
    markers = interpretation.get("markers") or {}
    aspects = sorted((markers.get("aspect") or {}).keys())
    cardinality = interpretation.get("cardinality") or {}
    return {
        "status": proposition.get("status", "unknown"),
        "entity": proposition.get("entity"),
        "property": proposition.get("property"),
        "value": proposition.get("value"),
        "cardinality": cardinality.get("class", "unknown"),
        "replacement": cardinality.get("basis") == "interpreted_replacement_marker",
        "change": bool(markers.get("change")),
        "aspect": aspects[0] if len(aspects) == 1 else ("none_unknown" if not aspects else aspects[0]),
        "aspect_all": aspects,
        "hedged": bool(markers.get("hedge")),
        "declared_observed_at": declared_observed_at,
    }
