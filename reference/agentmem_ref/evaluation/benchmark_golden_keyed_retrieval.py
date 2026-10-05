"""Benchmark-author golden path: a small keyed-retrieval benchmark integration (#652).

This module is the executable half of ``integrations/golden-keyed-retrieval-v1.json``.
It demonstrates the complete benchmark-author contract on purpose-sized inputs:

* exact integration identity, read from the committed descriptor rather than restated;
* exact frozen input identity, verified against the descriptor before any operation;
* system invocation through the neutral Gauntlet operation envelope only;
* benchmark-native results retained in full;
* common-dimension normalization driven strictly by the descriptor's declared mappings;
* evaluator-integrity negative controls that can fail;
* failure attribution through the Gauntlet boundary vocabulary.

Its provenance class is ``baseline_or_probe``. It is a demonstration of the contributor
contract, not independent evidence about any memory system, and it has no authority.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from .._paths import REPO_ROOT
from .benchmark_integration import mapped_metric_observations
from .contract import dimension_report, metric_observation
from .gauntlet_contract import CONTRACT_VERSION, validate_operation_envelope
from .gauntlet_transport import AdapterSession, GauntletExecutionError

INTEGRATION_ID = "golden-keyed-retrieval-v1"
RECALL_LIMIT = 3


def descriptor() -> dict[str, Any]:
    """The committed descriptor for this integration (validated on load)."""

    from .registry import get_integration

    return get_integration(INTEGRATION_ID)


def input_path(document: Mapping[str, Any] | None = None) -> Path:
    document = document or descriptor()
    return REPO_ROOT / document["input_contract"]["committed_input_path"]


def load_frozen_input(document: Mapping[str, Any] | None = None) -> tuple[dict[str, Any], str]:
    """Load the committed input and refuse to proceed if its digest is not the declared one."""

    document = document or descriptor()
    path = input_path(document)
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise GauntletExecutionError("benchmark_input", "input_unavailable", f"frozen input unavailable: {exc}") from exc
    digest = hashlib.sha256(payload).hexdigest()
    expected = document["input_contract"]["known_input_sha256"]
    if digest != expected:
        raise GauntletExecutionError(
            "benchmark_input",
            "input_digest_mismatch",
            f"frozen input digest {digest} != descriptor known_input_sha256 {expected}",
        )
    try:
        fixture = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GauntletExecutionError("benchmark_input", "input_malformed", str(exc)) from exc
    if not isinstance(fixture, dict) or not fixture.get("records") or not fixture.get("queries"):
        raise GauntletExecutionError("benchmark_input", "input_malformed", "input requires records and queries")
    return fixture, digest


def _request(operation: str, request_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_family": "agent-memory-gauntlet-operation",
        "contract_version": CONTRACT_VERSION,
        "direction": "request",
        "operation": operation,
        "request_id": request_id,
        "payload": payload,
        "authority_effect": "none",
    }


def _require_ok(response: Mapping[str, Any], operation: str) -> None:
    if response["status"] == "ok":
        return
    error = response.get("error") or {}
    source = error.get("source") or (
        "system_under_test" if response["status"] in {"refused", "system_error"} else "system_adapter"
    )
    raise GauntletExecutionError(
        source,
        error.get("code") or f"{operation}_{response['status']}",
        error.get("message") or f"{operation} returned {response['status']}",
    )


def _recalled_ids(response: Mapping[str, Any]) -> list[str]:
    result = response.get("result") or {}
    items = result.get("items")
    if not isinstance(items, list):
        raise GauntletExecutionError("system_adapter", "invalid_recall_result", "recall result.items must be a list")
    ids: list[str] = []
    for item in items:
        if not isinstance(item, Mapping) or not item.get("id"):
            raise GauntletExecutionError("system_adapter", "invalid_recall_item", "recall items must be objects with non-empty id")
        ids.append(str(item["id"]))
    return ids


def execute_native(
    session: Any,
    *,
    run_id: str,
    namespace: str,
    fixture: Mapping[str, Any],
    input_sha256: str,
    document: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the benchmark-native protocol over one adapter session and return native results."""

    sequence = 0
    operation_count = 0
    transcript: list[dict[str, Any]] = []

    def invoke(operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal sequence, operation_count
        sequence += 1
        operation_count += 1
        request = _request(operation, f"{run_id}:gkr:{sequence:04d}", {"namespace": namespace, **payload})
        response = session.invoke(request)
        transcript.append(
            {
                "operation": operation,
                "request_id": request["request_id"],
                "status": response["status"],
                "result": response.get("result"),
                "error": response.get("error"),
            }
        )
        _require_ok(response, operation)
        return response

    invoke("describe", {})
    invoke("reset", {})
    for record in fixture["records"]:
        invoke("remember", {"record": {"id": record["id"], "text": record["text"]}})

    rows: list[dict[str, Any]] = []
    top1_hits = 0
    recall3_hits = 0
    for query in fixture["queries"]:
        response = invoke("recall", {"query": query["query"], "limit": RECALL_LIMIT})
        ids = _recalled_ids(response)
        top1 = bool(ids) and ids[0] == query["gold_id"]
        within3 = query["gold_id"] in ids[:RECALL_LIMIT]
        top1_hits += int(top1)
        recall3_hits += int(within3)
        rows.append(
            {
                "query_id": query["query_id"],
                "gold_id": query["gold_id"],
                "recalled_ids": ids[:RECALL_LIMIT],
                "exact_top1": top1,
                "gold_within_3": within3,
            }
        )

    sample_count = len(rows)
    benchmark = document["benchmark"]
    inputs = document["input_contract"]
    return {
        "integration_id": document["integration_id"],
        "profile_kind": benchmark["provenance_class"],
        "input_sha256": input_sha256,
        "sample_count": sample_count,
        "metrics": {
            "exact_top1": top1_hits / sample_count,
            "recall_at_3": recall3_hits / sample_count,
            "operation_count": operation_count,
            "operation_contract_valid_rate": 1.0,
        },
        "rows": rows,
        "transcript": transcript,
        "benchmark_identity": {
            "id": benchmark["id"],
            "source_revision": benchmark["source_revision"],
            "dataset_id": inputs["dataset_id"],
            "dataset_revision": inputs.get("known_dataset_revision") or benchmark["source_revision"],
            "input_sha256": input_sha256,
        },
        "selection_id": f"all:{input_sha256[:16]}",
        "selection_method": "full declared query set",
        "authority_effect": "none",
    }


def normalize_golden_keyed_retrieval(native: Mapping[str, Any], document: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build the common dimensions strictly from descriptor mappings and native evidence.

    Dimensions the descriptor leaves unmapped are declared ``not_applicable`` or
    ``not_measured`` with the descriptor's reason; nothing is invented.
    """

    document = document or descriptor()
    sample_count = int(native["sample_count"])
    retrieval = mapped_metric_observations(
        document,
        native,
        dimension="retrieval",
        denominator=sample_count,
        unit="fraction",
        population="golden keyed-retrieval queries",
    )
    integrity = mapped_metric_observations(
        document,
        native,
        dimension="evaluator_integrity",
        denominator=int(native["metrics"]["operation_count"]),
        unit="fraction",
        population="operation responses",
    )
    reproducibility = mapped_metric_observations(document, native, dimension="reproducibility", population="frozen input")

    def _status(metrics: list[dict[str, Any]]) -> str:
        states = {metric["state"] for metric in metrics}
        if states == {"measured"}:
            return "measured"
        return "partial" if "measured" in states else "not_measured"

    dimensions: dict[str, Any] = {}
    for dimension, reason in document["normalization"]["unmapped_dimensions"].items():
        status = "not_applicable" if reason.startswith("not_applicable") else "not_measured"
        dimensions[dimension] = dimension_report(status, notes=[reason])
    dimensions["retrieval"] = dimension_report(_status(retrieval), retrieval)
    dimensions["evaluator_integrity"] = dimension_report(
        _status(integrity),
        integrity,
        notes=["evaluator-integrity negative controls run separately (reference/run_golden_benchmark_integrity.py)"],
    )
    dimensions["reproducibility"] = dimension_report(_status(reproducibility), reproducibility)
    return dimensions


def run_golden_keyed_retrieval(session: AdapterSession, *, run_id: str, namespace: str) -> dict[str, Any]:
    """Gauntlet profile runner entry point."""

    document = descriptor()
    fixture, digest = load_frozen_input(document)
    native = execute_native(
        session, run_id=run_id, namespace=namespace, fixture=fixture, input_sha256=digest, document=document
    )
    native["normalized_dimensions"] = normalize_golden_keyed_retrieval(native, document)
    native["normalization_limitations"] = list(document["limitations"])
    return native


# Evaluator-integrity negative controls ------------------------------------------------


class ControlledSession:
    """Wrap an adapter session with one evaluator-side mutation.

    The mutation is applied at the operation-envelope boundary so the control exercises
    the evaluator against the same neutral surface a real system uses. The wrapped
    session is never told it is being mutated.
    """

    def __init__(self, inner: Any, *, before: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None,
                 after: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None):
        self._inner = inner
        self._before = before
        self._after = after
        self.manifest = getattr(inner, "manifest", None)

    def invoke(self, request: Mapping[str, Any]) -> dict[str, Any]:
        validated = validate_operation_envelope(request)
        if self._before is not None:
            synthetic = self._before(validated)
            if synthetic is not None:
                return validate_operation_envelope(synthetic)
        response = self._inner.invoke(validated)
        if self._after is not None:
            response = validate_operation_envelope(self._after(validated, response))
        return response


def _ok(request: Mapping[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_family": "agent-memory-gauntlet-operation",
        "contract_version": CONTRACT_VERSION,
        "direction": "response",
        "operation": request["operation"],
        "request_id": request["request_id"],
        "status": "ok",
        "result": result,
        "error": None,
        "timing": {"elapsed_ms": 0.0},
        "adapter_evidence": {"evaluator_control": True},
        "authority_effect": "none",
    }


def _drop_records(ids: set[str]) -> Callable[[dict[str, Any]], dict[str, Any] | None]:
    def before(request: dict[str, Any]) -> dict[str, Any] | None:
        if request["operation"] == "remember":
            record = request["payload"].get("record") or {}
            if str(record.get("id")) in ids:
                return _ok(request, {"accepted": True, "evaluator_control": "dropped"})
        return None

    return before


def _invert_top_two(request: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    if request["operation"] == "recall" and response.get("status") == "ok":
        items = list((response.get("result") or {}).get("items") or [])
        if len(items) >= 2:
            items[0], items[1] = items[1], items[0]
            response = dict(response)
            response["result"] = {**(response.get("result") or {}), "items": items}
    return response


def _corrupt_identities(request: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    if request["operation"] == "recall" and response.get("status") == "ok":
        items = [
            {**item, "id": f"corrupt:{item['id']}"} if isinstance(item, Mapping) else item
            for item in (response.get("result") or {}).get("items") or []
        ]
        response = dict(response)
        response["result"] = {**(response.get("result") or {}), "items": items}
    return response


def control_factories(fixture: Mapping[str, Any]) -> dict[str, Callable[[Any], ControlledSession]]:
    gold = {query["gold_id"] for query in fixture["queries"]}
    unrelated = {record["id"] for record in fixture["records"] if record["id"].startswith("gkr:unrelated-")}
    return {
        "gold_omission": lambda inner: ControlledSession(inner, before=_drop_records(gold)),
        "rank_inversion": lambda inner: ControlledSession(inner, after=_invert_top_two),
        "identity_corruption": lambda inner: ControlledSession(inner, after=_corrupt_identities),
        "unrelated_record_omission": lambda inner: ControlledSession(inner, before=_drop_records(unrelated)),
    }


def run_integrity_controls(manifest: Mapping[str, Any], *, allow_external_process: bool = False) -> dict[str, Any]:
    """Execute the healthy arm and every declared negative control through one adapter.

    A control is ``detected`` when ``exact_top1`` falls below the healthy arm. A control
    whose descriptor expectation is ``false`` is an isolation control: it must leave the
    metric unchanged. ``all_as_expected`` is true only when every control matches its
    declared expectation. This is evidence about the evaluator, never about the system.
    """

    document = descriptor()
    fixture, digest = load_frozen_input(document)
    declared = {control["control_id"]: control for control in document["evaluator_integrity"]["negative_controls"]}
    factories = control_factories(fixture)
    missing = sorted(set(declared) - set(factories))
    unknown = sorted(set(factories) - set(declared))
    if missing or unknown:
        raise GauntletExecutionError(
            "benchmark_adapter",
            "control_registry_mismatch",
            f"descriptor controls {missing} are not implemented; implemented controls {unknown} are undeclared",
        )

    def arm(label: str, wrap: Callable[[Any], Any] | None) -> dict[str, Any]:
        with AdapterSession(manifest, allow_external_process=allow_external_process) as session:
            target = wrap(session) if wrap else session
            return execute_native(
                target,
                run_id=f"integrity-{label}",
                namespace=f"integrity-{label}",
                fixture=fixture,
                input_sha256=digest,
                document=document,
            )

    healthy = arm("healthy", None)
    healthy_value = healthy["metrics"]["exact_top1"]
    controls = []
    all_as_expected = True
    for control_id in sorted(declared):
        native = arm(control_id, factories[control_id])
        value = native["metrics"]["exact_top1"]
        detected = value < healthy_value
        expected = declared[control_id]["expected_detection"]
        as_expected = detected == expected
        all_as_expected = all_as_expected and as_expected
        controls.append(
            {
                "control_id": control_id,
                "description": declared[control_id]["description"],
                "metric_id": "exact_top1",
                "healthy_value": healthy_value,
                "control_value": value,
                "expected_detection": expected,
                "detected": detected,
                "as_expected": as_expected,
                "recall_at_3": native["metrics"]["recall_at_3"],
            }
        )
    system = manifest["system"]
    return {
        "schema_version": "1.0.0",
        "report_kind": "evaluator_integrity_controls",
        "integration_id": document["integration_id"],
        "profile_kind": document["benchmark"]["provenance_class"],
        "input_sha256": digest,
        "system": {"id": system["id"], "kind": system["kind"], "revision": system["revision"]},
        "healthy": {"exact_top1": healthy_value, "recall_at_3": healthy["metrics"]["recall_at_3"], "sample_count": healthy["sample_count"]},
        "controls": controls,
        "all_as_expected": all_as_expected,
        "claim_boundary": [
            "evaluator-integrity evidence establishes evaluator sensitivity to controlled defects only",
            "it is not evidence of memory efficacy, benchmark comparability, or authority",
        ],
        "authority_effect": "none",
    }


__all__ = [
    "INTEGRATION_ID",
    "RECALL_LIMIT",
    "ControlledSession",
    "descriptor",
    "input_path",
    "load_frozen_input",
    "execute_native",
    "normalize_golden_keyed_retrieval",
    "run_golden_keyed_retrieval",
    "control_factories",
    "run_integrity_controls",
]
