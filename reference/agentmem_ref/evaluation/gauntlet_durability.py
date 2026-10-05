"""Claim-driven durability/recovery Gauntlet cases for #571.

This suite evaluates lifecycle behavior through the neutral system-adapter contract. It
keeps behavioral outcome separate from evidence sufficiency and emits no aggregate
"durability score". A case may therefore record a real behavioral failure with sufficient
evidence, or be blocked when the evaluator cannot establish the required pre/post state.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .contract import DIMENSIONS, dimension_report, metric_observation
from .gauntlet_contract import CONTRACT_VERSION, capability_support
from .gauntlet_transport import AdapterSession, GauntletExecutionError

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
    stable = []
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


def _unsupported_case(case_id: str, capability: str, support: str | None, note: str) -> dict[str, Any]:
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


def _blocked_case(
    case_id: str,
    capability: str,
    *,
    pre_state: Mapping[str, Any],
    transition: Mapping[str, Any],
    expected_boundary: Mapping[str, Any],
    post_state: Mapping[str, Any],
    note: str,
) -> dict[str, Any]:
    return _case(
        case_id,
        capability,
        "blocked",
        "insufficient",
        pre_state=pre_state,
        transition=transition,
        expected_boundary=expected_boundary,
        post_state=post_state,
        note=note,
    )


def _dimensions(cases: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions = {dimension: dimension_report("not_applicable") for dimension in DIMENSIONS}

    behavior_metrics = []
    measured = 0
    unmeasured = 0
    evidence_metrics = []
    for case in cases:
        metric_id = case["case_id"].lower().replace("-", "_")
        outcome = case["behavioral_outcome"]
        if outcome in {"pass", "fail"}:
            measured += 1
            behavior_metrics.append(
                metric_observation(
                    metric_id,
                    value=outcome == "pass",
                    direction="descriptive",
                    unit="boolean",
                    population="one deterministic durability/recovery Gauntlet case",
                    note=f"native behavioral outcome={outcome}; no aggregate durability score is implied",
                )
            )
        elif outcome == "unsupported":
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
                    "evidence sufficiency is independent of behavioral pass/fail; "
                    f"qualification={case['evidence_qualification']}"
                ),
            )
        )

    if measured and unmeasured:
        lifecycle_status = "partial"
    elif measured:
        lifecycle_status = "measured"
    elif behavior_metrics and all(metric["state"] == "not_applicable" for metric in behavior_metrics):
        lifecycle_status = "not_applicable"
    else:
        lifecycle_status = "blocked"

    # The common evidence contract has no generic durability dimension yet. Lifecycle
    # mutation/recovery claims therefore live under governance with an explicit note; the
    # native case vocabulary remains authoritative for what was actually exercised.
    dimensions["governance"] = dimension_report(
        lifecycle_status,
        behavior_metrics,
        notes=[
            "Durability/lifecycle cases are normalized under governance because the common contract has no generic durability dimension.",
            "Native case identities and behavioral outcomes remain separate; no aggregate durability score is emitted.",
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
    cases: list[dict[str, Any]] = []

    def invoke(operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        nonlocal sequence, operation_count
        sequence += 1
        operation_count += 1
        return session.invoke(
            _request(operation, f"{run_id}:dur:{sequence:04d}", {"namespace": namespace, **dict(payload)})
        )

    def reset() -> dict[str, Any]:
        return invoke("reset", {})

    def remember(scope: str, memory_id: str, text: str) -> dict[str, Any]:
        return invoke("remember", {"scope": scope, "record": {"id": memory_id, "text": text}})

    def recall(scope: str, query: str) -> dict[str, Any]:
        return invoke("recall", {"scope": scope, "query": query, "limit": 10})

    def recover(scope: str) -> dict[str, Any]:
        return invoke("recover", {"scope": scope})

    def basic_ready(*responses: Mapping[str, Any]) -> bool:
        return all(response.get("status") == "ok" for response in responses)

    # DUR-REC-001: retained state survives an explicit reopen/recovery transition.
    rec_scope = "scope:durability:recover"
    rec_id = "dur:recover:001"
    rec_token = "durabilityretainedtoken571"
    r_reset = reset()
    r_remember = remember(rec_scope, rec_id, f"Recovery marker {rec_token} is retained.")
    r_before = recall(rec_scope, rec_token)
    r_recover = recover(rec_scope)
    r_after = recall(rec_scope, rec_token)
    rec_ready = basic_ready(r_reset, r_remember, r_before, r_recover, r_after)
    rec_pass = rec_ready and rec_id in _item_ids(r_before) and rec_id in _item_ids(r_after)
    cases.append(
        _case(
            "DUR-REC-001",
            "restart_recovery",
            "pass" if rec_pass else ("fail" if rec_ready else "blocked"),
            "sufficient" if rec_ready else "insufficient",
            pre_state={"record_id": rec_id, "visible_before_recover": rec_id in _item_ids(r_before)},
            transition={"operation": "recover", "status": r_recover.get("status"), "surface": _result(r_recover).get("recovery_surface")},
            expected_boundary={"record_visible_after_recover": True},
            post_state={"visible_after_recover": rec_id in _item_ids(r_after), "returned_ids": _item_ids(r_after)},
            note=None if rec_ready else "setup/recovery operation did not complete",
        )
    )

    # DUR-DEL-001: governed deletion must remain absent after reopen and history must
    # retain a tombstone rather than silently resetting the whole namespace.
    del_scope = "scope:durability:delete"
    del_id = "dur:delete:001"
    del_token = "durabilitydeletetoken571"
    d_reset = reset()
    d_remember = remember(del_scope, del_id, f"Deletion marker {del_token} must not resurrect.")
    d_before = recall(del_scope, del_token)
    d_forget = invoke("forget", {"scope": del_scope, "id": del_id})
    d_recover = recover(del_scope)
    d_after = recall(del_scope, del_token)
    d_history = invoke("history", {"scope": del_scope, "id": del_id})
    d_ready = basic_ready(d_reset, d_remember, d_before, d_forget, d_recover, d_after, d_history)
    history = _result(d_history).get("history")
    tombstoned = isinstance(history, Mapping) and history.get("tombstoned") is True
    no_current = isinstance(history, Mapping) and not history.get("current_fact_uuid")
    d_pass = (
        d_ready
        and del_id in _item_ids(d_before)
        and del_id not in _item_ids(d_after)
        and tombstoned
        and no_current
    )
    cases.append(
        _case(
            "DUR-DEL-001",
            "durable_deletion",
            "pass" if d_pass else ("fail" if d_ready else "blocked"),
            "sufficient" if d_ready else "insufficient",
            pre_state={"record_id": del_id, "visible_before_delete": del_id in _item_ids(d_before)},
            transition={"forget_status": d_forget.get("status"), "recover_status": d_recover.get("status")},
            expected_boundary={"record_visible_after_recover": False, "tombstone_retained": True, "current_fact_uuid": None},
            post_state={"visible_after_recover": del_id in _item_ids(d_after), "history_tombstoned": tombstoned, "history_current_fact_uuid": history.get("current_fact_uuid") if isinstance(history, Mapping) else None},
            note=None if d_ready else "delete/recover/history evidence was incomplete",
        )
    )

    # DUR-COR-001: corrected current value survives recovery; the prior erroneous value
    # must not re-enter ordinary recall.
    cor_scope = "scope:durability:correct"
    cor_id = "dur:correct:001"
    old_token = "durabilityoldtoken571"
    new_token = "durabilitynewtoken571"
    c_reset = reset()
    c_remember = remember(cor_scope, cor_id, f"Correction marker is {old_token}.")
    c_before = recall(cor_scope, old_token)
    c_correct = invoke(
        "correct",
        {
            "scope": cor_scope,
            "id": cor_id,
            "text": f"Correction marker is {new_token}.",
            "replacement_kind": "error_correction",
        },
    )
    c_recover = recover(cor_scope)
    c_new = recall(cor_scope, new_token)
    c_old = recall(cor_scope, old_token)
    c_history = invoke("history", {"scope": cor_scope, "id": cor_id})
    c_ready = basic_ready(c_reset, c_remember, c_before, c_correct, c_recover, c_new, c_old, c_history)
    c_pass = (
        c_ready
        and cor_id in _item_ids(c_before)
        and cor_id in _item_ids(c_new)
        and cor_id not in _item_ids(c_old)
    )
    cases.append(
        _case(
            "DUR-COR-001",
            "durable_correction",
            "pass" if c_pass else ("fail" if c_ready else "blocked"),
            "sufficient" if c_ready else "insufficient",
            pre_state={"record_id": cor_id, "old_value_visible": cor_id in _item_ids(c_before), "old_token": old_token},
            transition={"correct_status": c_correct.get("status"), "recover_status": c_recover.get("status"), "replacement_kind": "error_correction"},
            expected_boundary={"new_value_visible": True, "old_value_visible_in_ordinary_recall": False},
            post_state={"new_value_visible": cor_id in _item_ids(c_new), "old_value_visible": cor_id in _item_ids(c_old), "history_present": bool(_result(c_history).get("history"))},
            note=None if c_ready else "correction/recovery evidence was incomplete or correction was refused",
        )
    )

    # DUR-DET-001: two recovery transitions over unchanged state must produce identical
    # stable semantic observations. Timing/transport metadata is intentionally excluded.
    det_scope = "scope:durability:deterministic"
    det_id = "dur:deterministic:001"
    det_token = "durabilitydeterministictoken571"
    t_reset = reset()
    t_remember = remember(det_scope, det_id, f"Deterministic recovery marker {det_token}.")
    t_recover_1 = recover(det_scope)
    t_recall_1 = recall(det_scope, det_token)
    t_recover_2 = recover(det_scope)
    t_recall_2 = recall(det_scope, det_token)
    t_ready = basic_ready(t_reset, t_remember, t_recover_1, t_recall_1, t_recover_2, t_recall_2)
    stable_1 = _stable_items(t_recall_1)
    stable_2 = _stable_items(t_recall_2)
    t_pass = t_ready and bool(stable_1) and stable_1 == stable_2 and det_id in [item["id"] for item in stable_1]
    cases.append(
        _case(
            "DUR-DET-001",
            "deterministic_recovery",
            "pass" if t_pass else ("fail" if t_ready else "blocked"),
            "sufficient" if t_ready else "insufficient",
            pre_state={"record_id": det_id, "expected_token": det_token},
            transition={"recoveries": 2, "first_status": t_recover_1.get("status"), "second_status": t_recover_2.get("status")},
            expected_boundary={"stable_semantic_observation_equal": True},
            post_state={"first_items": stable_1, "second_items": stable_2, "stable_equal": stable_1 == stable_2},
            note=None if t_ready else "repeated recovery evidence was incomplete",
        )
    )

    # DUR-ISO-001: recovery may not broaden scope admission.
    iso_scope_a = "scope:durability:isolation:a"
    iso_scope_b = "scope:durability:isolation:b"
    iso_id = "dur:isolation:001"
    iso_token = "durabilityscopetoken571"
    i_reset = reset()
    i_remember = remember(iso_scope_a, iso_id, f"Scope marker {iso_token} belongs only to A.")
    i_recover_b = recover(iso_scope_b)
    i_wrong = recall(iso_scope_b, iso_token)
    i_recover_a = recover(iso_scope_a)
    i_right = recall(iso_scope_a, iso_token)
    i_ready = basic_ready(i_reset, i_remember, i_recover_b, i_wrong, i_recover_a, i_right)
    i_pass = i_ready and iso_id not in _item_ids(i_wrong) and iso_id in _item_ids(i_right)
    cases.append(
        _case(
            "DUR-ISO-001",
            "scope_isolation",
            "pass" if i_pass else ("fail" if i_ready else "blocked"),
            "sufficient" if i_ready else "insufficient",
            pre_state={"record_id": iso_id, "write_scope": iso_scope_a},
            transition={"recover_wrong_scope": i_recover_b.get("status"), "recover_right_scope": i_recover_a.get("status")},
            expected_boundary={"visible_in_scope_b": False, "visible_in_scope_a": True},
            post_state={"scope_b_ids": _item_ids(i_wrong), "scope_a_ids": _item_ids(i_right)},
            note=None if i_ready else "scope recovery/admission evidence was incomplete",
        )
    )

    checkpoint_support = capability_support(manifest, "checkpoint")
    if checkpoint_support in _POSITIVE_SUPPORT:
        # A contestant claiming checkpoint support must be exercised. This first Agent
        # Memory contestant deliberately does not make the claim, but the profile remains
        # neutral for systems that do.
        cp_response = invoke("checkpoint", {"scope": "scope:durability:checkpoint"})
        cp_ready = cp_response.get("status") == "ok"
        cases.append(
            _case(
                "DUR-CHK-001",
                "checkpoint",
                "pass" if cp_ready else "fail",
                "sufficient",
                pre_state={"declared_support": checkpoint_support},
                transition={"operation": "checkpoint", "status": cp_response.get("status")},
                expected_boundary={"checkpoint_operation_succeeds": True},
                post_state={"result": _result(cp_response)},
            )
        )
    else:
        cases.append(
            _unsupported_case(
                "DUR-CHK-001",
                "checkpoint",
                checkpoint_support,
                "checkpoint is not exposed by this contestant; unsupported remains non-numeric and private runtime access is not manufactured by the adapter",
            )
        )

    normalized_dimensions = _dimensions(cases)
    return {
        "profile_kind": "gauntlet_native_gap",
        "sample_count": len(cases),
        "case_fixture_sha256": CASE_FIXTURE_SHA256,
        "operation_count": operation_count,
        "cases": cases,
        "normalized_dimensions": normalized_dimensions,
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


__all__ = [
    "CASE_DEFINITIONS",
    "CASE_FIXTURE_SHA256",
    "run_durability_recovery_alpha",
]
