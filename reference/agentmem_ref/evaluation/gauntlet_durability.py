"""Claim-driven durability/recovery Gauntlet cases for #571.

Behavior and evidence sufficiency are deliberately separate. A claimed capability may
fail with sufficient evidence; an unavailable capability remains unsupported rather than
becoming a numeric zero. This suite emits no aggregate durability score.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any, Callable

from .contract import DIMENSIONS, dimension_report, metric_observation
from .gauntlet_contract import CONTRACT_VERSION, capability_support
from .gauntlet_transport import AdapterSession

_POSITIVE_SUPPORT = {"native", "mapped", "derived"}

CASE_DEFINITIONS = (
    ("DUR-REC-001", "restart_recovery", "retained memory survives explicit recover/reopen"),
    ("DUR-DEL-001", "durable_deletion", "governed deletion does not resurrect after recover/reopen"),
    ("DUR-COR-001", "durable_correction", "governed correction remains current after recover/reopen"),
    ("DUR-DET-001", "deterministic_recovery", "repeated recovery yields identical stable observations"),
    ("DUR-ISO-001", "scope_isolation", "scope admission remains fail-closed across recover/reopen"),
    ("DUR-CHK-001", "checkpoint", "checkpoint posture is reported without manufacturing private capability"),
)
CASE_FIXTURE_BYTES = (
    json.dumps(CASE_DEFINITIONS, sort_keys=True, separators=(",", ":")) + "\n"
).encode("utf-8")
CASE_FIXTURE_SHA256 = hashlib.sha256(CASE_FIXTURE_BYTES).hexdigest()


def _request(operation: str, request_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "contract_family": "agent-memory-gauntlet-operation",
        "contract_version": CONTRACT_VERSION,
        "direction": "request",
        "operation": operation,
        "request_id": request_id,
        "payload": dict(payload),
        "authority_effect": "none",
    }


def _result(response: Mapping[str, Any]) -> dict[str, Any]:
    value = response.get("result")
    return dict(value) if isinstance(value, Mapping) else {}


def _item_ids(response: Mapping[str, Any]) -> list[str]:
    items = _result(response).get("items")
    if not isinstance(items, list):
        return []
    return [str(item["id"]) for item in items if isinstance(item, Mapping) and item.get("id")]


def _stable_items(response: Mapping[str, Any]) -> list[dict[str, str]]:
    items = _result(response).get("items")
    if not isinstance(items, list):
        return []
    stable: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, Mapping) or not item.get("id"):
            continue
        row = {"id": str(item["id"])}
        if item.get("text") is not None:
            row["text"] = str(item["text"])
        stable.append(row)
    return stable


def _case(
    case_id: str,
    capability: str,
    behavioral_outcome: str,
    evidence_qualification: str,
    *,
    pre_state: Mapping[str, Any],
    transition: Mapping[str, Any],
    expected_boundary: Mapping[str, Any],
    post_state: Mapping[str, Any],
    note: str | None = None,
) -> dict[str, Any]:
    value = {
        "case_id": case_id,
        "capability": capability,
        "behavioral_outcome": behavioral_outcome,
        "evidence_qualification": evidence_qualification,
        "pre_state": dict(pre_state),
        "transition": dict(transition),
        "expected_boundary": dict(expected_boundary),
        "post_state": dict(post_state),
        "authority_effect": "none",
    }
    if note:
        value["note"] = note
    return value


def _support(manifest: Mapping[str, Any], capability: str) -> str | None:
    return capability_support(manifest, capability)


def _claimed(manifest: Mapping[str, Any], capability: str) -> bool:
    return _support(manifest, capability) in _POSITIVE_SUPPORT


def _unsupported(case_id: str, capability: str, manifest: Mapping[str, Any], note: str) -> dict[str, Any]:
    support = _support(manifest, capability)
    return _case(
        case_id,
        capability,
        "unsupported",
        "sufficient",
        pre_state={"declared_support": support},
        transition={"operation_executed": False},
        expected_boundary={"unsupported_must_not_be_emulated": True},
        post_state={"declared_support": support},
        note=note,
    )


def _outcome(ready: bool, passed: bool) -> tuple[str, str]:
    if not ready:
        return "blocked", "insufficient"
    return ("pass" if passed else "fail"), "sufficient"


def _dimensions(cases: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions = {dimension: dimension_report("not_applicable") for dimension in DIMENSIONS}
    behavior_metrics = []
    evidence_metrics = []
    measured = 0
    unmeasured = 0

    for case in cases:
        metric_id = case["case_id"].lower().replace("-", "_")
        behavior = case["behavioral_outcome"]
        if behavior in {"pass", "fail"}:
            measured += 1
            behavior_metrics.append(
                metric_observation(
                    metric_id,
                    value=behavior == "pass",
                    direction="descriptive",
                    unit="boolean",
                    population="one deterministic durability/recovery Gauntlet case",
                    note=f"native behavioral outcome={behavior}; no aggregate durability score is implied",
                )
            )
        elif behavior == "unsupported":
            unmeasured += 1
            behavior_metrics.append(
                metric_observation(
                    metric_id,
                    state="not_applicable",
                    direction="descriptive",
                    population="one deterministic durability/recovery Gauntlet case",
                    note="capability not claimed; unsupported is not numeric failure",
                )
            )
        else:
            unmeasured += 1
            behavior_metrics.append(
                metric_observation(
                    metric_id,
                    state="blocked",
                    direction="descriptive",
                    population="one deterministic durability/recovery Gauntlet case",
                    note=case.get("note") or "evaluator could not establish sufficient evidence",
                )
            )
        evidence_metrics.append(
            metric_observation(
                f"{metric_id}_evidence_sufficient",
                value=case["evidence_qualification"] == "sufficient",
                direction="descriptive",
                unit="boolean",
                population="one durability/recovery Gauntlet case evidence package",
                note=(
                    "evidence sufficiency is independent of behavioral outcome; "
                    f"qualification={case['evidence_qualification']}"
                ),
            )
        )

    if measured and unmeasured:
        lifecycle_status = "partial"
    elif measured:
        lifecycle_status = "measured"
    elif behavior_metrics:
        lifecycle_status = "not_applicable"
    else:
        lifecycle_status = "blocked"

    # The common evidence contract has no durability dimension yet. Keep native case
    # semantics explicit and normalize lifecycle behavior under governance only as a
    # transport/reporting accommodation.
    dimensions["governance"] = dimension_report(
        lifecycle_status,
        behavior_metrics,
        notes=[
            "Durability/lifecycle cases are normalized under governance because the common contract has no generic durability dimension.",
            "Native case identities remain primary; no aggregate durability score is emitted.",
        ],
    )
    dimensions["evaluator_integrity"] = dimension_report(
        "measured",
        evidence_metrics,
        notes=[
            "Every case reports evidence sufficiency separately from behavioral outcome.",
            "A behavioral failure with sufficient evidence remains a valid measured finding.",
        ],
    )
    dimensions["reproducibility"] = dimension_report(
        "measured",
        [
            metric_observation(
                "durability_case_fixture_sha256",
                value=CASE_FIXTURE_SHA256,
                direction="descriptive",
                population="durability/recovery Gauntlet case registry",
            ),
            metric_observation(
                "durability_case_count",
                value=len(cases),
                direction="descriptive",
                unit="cases",
                population="durability/recovery Gauntlet case registry",
            ),
        ],
    )
    return dimensions


def _run_recovery_case(
    manifest: Mapping[str, Any],
    invoke: Callable[[str, Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if not _claimed(manifest, "restart_recovery"):
        return _unsupported(
            "DUR-REC-001", "restart_recovery", manifest,
            "restart/reopen durability is not claimed by this contestant",
        )
    scope, memory_id, token = "scope:durability:recover", "dur:recover:001", "durabilityretainedtoken571"
    responses = [
        invoke("reset", {}),
        invoke("remember", {"scope": scope, "record": {"id": memory_id, "text": f"Recovery marker {token} is retained."}}),
    ]
    before = invoke("recall", {"scope": scope, "query": token, "limit": 10})
    recovered = invoke("recover", {"scope": scope})
    after = invoke("recall", {"scope": scope, "query": token, "limit": 10})
    responses += [before, recovered, after]
    ready = all(item.get("status") == "ok" for item in responses)
    passed = ready and memory_id in _item_ids(before) and memory_id in _item_ids(after)
    behavior, evidence = _outcome(ready, passed)
    return _case(
        "DUR-REC-001", "restart_recovery", behavior, evidence,
        pre_state={"record_id": memory_id, "visible_before_recover": memory_id in _item_ids(before)},
        transition={"operation": "recover", "status": recovered.get("status"), "surface": _result(recovered).get("recovery_surface")},
        expected_boundary={"record_visible_after_recover": True},
        post_state={"visible_after_recover": memory_id in _item_ids(after), "returned_ids": _item_ids(after)},
        note=None if ready else "setup/recovery operation did not complete",
    )


def _run_deletion_case(
    manifest: Mapping[str, Any],
    invoke: Callable[[str, Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if not _claimed(manifest, "durable_deletion"):
        return _unsupported(
            "DUR-DEL-001", "durable_deletion", manifest,
            "durable deletion is not claimed by this contestant",
        )
    scope, memory_id, token = "scope:durability:delete", "dur:delete:001", "durabilitydeletetoken571"
    reset = invoke("reset", {})
    remembered = invoke("remember", {"scope": scope, "record": {"id": memory_id, "text": f"Deletion marker {token} must not resurrect."}})
    before = invoke("recall", {"scope": scope, "query": token, "limit": 10})
    forgotten = invoke("forget", {"scope": scope, "id": memory_id})
    recovered = invoke("recover", {"scope": scope})
    after = invoke("recall", {"scope": scope, "query": token, "limit": 10})
    history_response = invoke("history", {"scope": scope, "id": memory_id})
    responses = (reset, remembered, before, forgotten, recovered, after, history_response)
    ready = all(item.get("status") == "ok" for item in responses)
    history = _result(history_response).get("history")
    tombstoned = isinstance(history, Mapping) and history.get("tombstoned") is True
    no_current = isinstance(history, Mapping) and not history.get("current_fact_uuid")
    passed = ready and memory_id in _item_ids(before) and memory_id not in _item_ids(after) and tombstoned and no_current
    behavior, evidence = _outcome(ready, passed)
    return _case(
        "DUR-DEL-001", "durable_deletion", behavior, evidence,
        pre_state={"record_id": memory_id, "visible_before_delete": memory_id in _item_ids(before)},
        transition={"forget_status": forgotten.get("status"), "recover_status": recovered.get("status")},
        expected_boundary={"record_visible_after_recover": False, "tombstone_retained": True, "current_fact_uuid": None},
        post_state={
            "visible_after_recover": memory_id in _item_ids(after),
            "history_tombstoned": tombstoned,
            "history_current_fact_uuid": history.get("current_fact_uuid") if isinstance(history, Mapping) else None,
        },
        note=None if ready else "delete/recover/history evidence was incomplete",
    )


def _run_correction_case(
    manifest: Mapping[str, Any],
    invoke: Callable[[str, Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if not _claimed(manifest, "durable_correction"):
        return _unsupported(
            "DUR-COR-001", "durable_correction", manifest,
            "durable correction is not claimed by this contestant",
        )
    scope, memory_id = "scope:durability:correct", "dur:correct:001"
    old_token, new_token = "durabilityoldtoken571", "durabilitynewtoken571"
    reset = invoke("reset", {})
    remembered = invoke("remember", {"scope": scope, "record": {"id": memory_id, "text": f"Correction marker is {old_token}."}})
    before = invoke("recall", {"scope": scope, "query": old_token, "limit": 10})
    corrected = invoke("correct", {"scope": scope, "id": memory_id, "text": f"Correction marker is {new_token}.", "replacement_kind": "error_correction"})
    recovered = invoke("recover", {"scope": scope})
    current = invoke("recall", {"scope": scope, "query": new_token, "limit": 10})
    prior = invoke("recall", {"scope": scope, "query": old_token, "limit": 10})
    history = invoke("history", {"scope": scope, "id": memory_id})
    responses = (reset, remembered, before, corrected, recovered, current, prior, history)
    ready = all(item.get("status") == "ok" for item in responses)
    passed = ready and memory_id in _item_ids(before) and memory_id in _item_ids(current) and memory_id not in _item_ids(prior)
    behavior, evidence = _outcome(ready, passed)
    return _case(
        "DUR-COR-001", "durable_correction", behavior, evidence,
        pre_state={"record_id": memory_id, "old_value_visible": memory_id in _item_ids(before), "old_token": old_token},
        transition={"correct_status": corrected.get("status"), "recover_status": recovered.get("status"), "replacement_kind": "error_correction"},
        expected_boundary={"new_value_visible": True, "old_value_visible_in_ordinary_recall": False},
        post_state={"new_value_visible": memory_id in _item_ids(current), "old_value_visible": memory_id in _item_ids(prior), "history_present": bool(_result(history).get("history"))},
        note=None if ready else "correction/recovery evidence was incomplete or correction was refused",
    )


def _run_deterministic_case(
    manifest: Mapping[str, Any],
    invoke: Callable[[str, Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if not _claimed(manifest, "deterministic_recovery"):
        return _unsupported(
            "DUR-DET-001", "deterministic_recovery", manifest,
            "deterministic recovered observation is not claimed by this contestant",
        )
    scope, memory_id, token = "scope:durability:deterministic", "dur:deterministic:001", "durabilitydeterministictoken571"
    reset = invoke("reset", {})
    remembered = invoke("remember", {"scope": scope, "record": {"id": memory_id, "text": f"Deterministic recovery marker {token}."}})
    recovery_one = invoke("recover", {"scope": scope})
    recall_one = invoke("recall", {"scope": scope, "query": token, "limit": 10})
    recovery_two = invoke("recover", {"scope": scope})
    recall_two = invoke("recall", {"scope": scope, "query": token, "limit": 10})
    responses = (reset, remembered, recovery_one, recall_one, recovery_two, recall_two)
    ready = all(item.get("status") == "ok" for item in responses)
    stable_one, stable_two = _stable_items(recall_one), _stable_items(recall_two)
    passed = ready and bool(stable_one) and stable_one == stable_two and memory_id in [item["id"] for item in stable_one]
    behavior, evidence = _outcome(ready, passed)
    return _case(
        "DUR-DET-001", "deterministic_recovery", behavior, evidence,
        pre_state={"record_id": memory_id, "expected_token": token},
        transition={"recoveries": 2, "first_status": recovery_one.get("status"), "second_status": recovery_two.get("status")},
        expected_boundary={"stable_semantic_observation_equal": True},
        post_state={"first_items": stable_one, "second_items": stable_two, "stable_equal": stable_one == stable_two},
        note=None if ready else "repeated recovery evidence was incomplete",
    )


def _run_scope_case(
    manifest: Mapping[str, Any],
    invoke: Callable[[str, Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if not _claimed(manifest, "scope_isolation"):
        return _unsupported(
            "DUR-ISO-001", "scope_isolation", manifest,
            "scope isolation across recovery is not claimed by this contestant",
        )
    scope_a, scope_b = "scope:durability:isolation:a", "scope:durability:isolation:b"
    memory_id, token = "dur:isolation:001", "durabilityscopetoken571"
    reset = invoke("reset", {})
    remembered = invoke("remember", {"scope": scope_a, "record": {"id": memory_id, "text": f"Scope marker {token} belongs only to A."}})
    recovery_b = invoke("recover", {"scope": scope_b})
    wrong = invoke("recall", {"scope": scope_b, "query": token, "limit": 10})
    recovery_a = invoke("recover", {"scope": scope_a})
    right = invoke("recall", {"scope": scope_a, "query": token, "limit": 10})
    responses = (reset, remembered, recovery_b, wrong, recovery_a, right)
    ready = all(item.get("status") == "ok" for item in responses)
    passed = ready and memory_id not in _item_ids(wrong) and memory_id in _item_ids(right)
    behavior, evidence = _outcome(ready, passed)
    return _case(
        "DUR-ISO-001", "scope_isolation", behavior, evidence,
        pre_state={"record_id": memory_id, "write_scope": scope_a},
        transition={"recover_wrong_scope": recovery_b.get("status"), "recover_right_scope": recovery_a.get("status")},
        expected_boundary={"visible_in_scope_b": False, "visible_in_scope_a": True},
        post_state={"scope_b_ids": _item_ids(wrong), "scope_a_ids": _item_ids(right)},
        note=None if ready else "scope recovery/admission evidence was incomplete",
    )


def _run_checkpoint_case(
    manifest: Mapping[str, Any],
    invoke: Callable[[str, Mapping[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if not _claimed(manifest, "checkpoint"):
        return _unsupported(
            "DUR-CHK-001", "checkpoint", manifest,
            "checkpoint is not exposed by this contestant; unsupported remains non-numeric and private runtime access is not manufactured by the adapter",
        )
    response = invoke("checkpoint", {"scope": "scope:durability:checkpoint"})
    ready = response.get("status") in {"ok", "refused", "unsupported"}
    passed = response.get("status") == "ok"
    behavior, evidence = _outcome(ready, passed)
    return _case(
        "DUR-CHK-001", "checkpoint", behavior, evidence,
        pre_state={"declared_support": _support(manifest, "checkpoint")},
        transition={"operation": "checkpoint", "status": response.get("status")},
        expected_boundary={"checkpoint_operation_succeeds": True},
        post_state={"result": _result(response)},
        note=None if ready else "checkpoint response was not evaluable",
    )


def run_durability_recovery_alpha(
    session: AdapterSession,
    *,
    run_id: str,
    namespace: str,
) -> dict[str, Any]:
    """Run bounded neutral durability/recovery cases against one contestant."""

    manifest = session.manifest
    sequence = 0
    operation_count = 0

    def invoke(operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        nonlocal sequence, operation_count
        sequence += 1
        operation_count += 1
        return session.invoke(
            _request(operation, f"{run_id}:dur:{sequence:04d}", {"namespace": namespace, **dict(payload)})
        )

    cases = [
        _run_recovery_case(manifest, invoke),
        _run_deletion_case(manifest, invoke),
        _run_correction_case(manifest, invoke),
        _run_deterministic_case(manifest, invoke),
        _run_scope_case(manifest, invoke),
        _run_checkpoint_case(manifest, invoke),
    ]

    return {
        "profile_kind": "gauntlet_native_gap",
        "sample_count": len(cases),
        "case_fixture_sha256": CASE_FIXTURE_SHA256,
        "operation_count": operation_count,
        "cases": cases,
        "normalized_dimensions": _dimensions(cases),
        "normalization_limitations": [
            "This first slice exercises supported public reopen/recovery, lifecycle durability, deterministic observation, and scope isolation only.",
            "A recover operation mapped to AgentMemory.open qualifies handle/reopen recovery, not abrupt process-kill/crash recovery.",
            "Checkpoint is unsupported for the Agent Memory public facade and is not emulated through private runtime access.",
            "Concurrent-handle, stale-writer, migration, mixed-version, and crash/kill cases remain open under #571.",
            "No aggregate durability score is emitted.",
        ],
        "benchmark_identity": {
            "id": "agent-memory-gauntlet-durability-recovery-alpha",
            "source_revision": "0.1.0",
            "dataset_id": "durability-recovery-alpha-v1",
            "dataset_revision": "0.1.0",
            "input_sha256": CASE_FIXTURE_SHA256,
        },
        "selection_id": f"all:{CASE_FIXTURE_SHA256[:16]}",
        "selection_method": "full declared durability/recovery alpha case registry",
        "authority_effect": "none",
    }


__all__ = ["CASE_DEFINITIONS", "CASE_FIXTURE_SHA256", "run_durability_recovery_alpha"]
