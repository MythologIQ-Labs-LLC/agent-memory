"""Truthful diagnostics for an Agent Memory runtime configuration.

The doctor surface distinguishes configuration validity, durable-state
recovery, currentness, and live provider availability. It intentionally does
not reduce those independent claims to a generic ``healthy`` boolean.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .configured_restart import ConfigBoundRestartRuntime
from .restart_runtime import RuntimeRecoveryError
from .runtime_behavior import validate_runtime_behavior_contract
from .runtime_config import QualificationBinding
from .visibility import VisibilityTracker


class DiagnosticInputError(ValueError):
    """A CLI diagnostic input cannot be interpreted safely."""


def load_qualification_bindings(path: str | Path | None) -> tuple[QualificationBinding, ...]:
    if path is None:
        return ()
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DiagnosticInputError(f"qualification binding file not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise DiagnosticInputError(f"qualification binding file is not valid JSON: {source}") from exc
    if isinstance(value, Mapping):
        rows = value.get("bindings")
    else:
        rows = value
    if not isinstance(rows, list):
        raise DiagnosticInputError("qualification binding document must be an array or contain a bindings array")
    try:
        return tuple(QualificationBinding(**row) for row in rows)
    except (TypeError, KeyError, ValueError) as exc:
        raise DiagnosticInputError(f"qualification binding row is invalid: {exc}") from exc


def load_configuration_value(path: str | Path) -> dict:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DiagnosticInputError(f"runtime configuration not found: {source}") from exc
    except json.JSONDecodeError as exc:
        raise DiagnosticInputError(f"runtime configuration is not valid JSON: {source}") from exc
    if not isinstance(value, dict):
        raise DiagnosticInputError("runtime configuration must be a JSON object")
    return value


def validate_configuration_file(
    config_path: str | Path,
    *,
    qualification_path: str | Path | None = None,
) -> dict:
    value = load_configuration_value(config_path)
    bindings = load_qualification_bindings(qualification_path)
    plan = validate_runtime_behavior_contract(value, qualification_bindings=bindings)
    required_qualification_routes = [
        str(route.get("route_id"))
        for route in value.get("routes", ())
        if isinstance(route, Mapping)
        and isinstance(route.get("qualification"), Mapping)
        and bool(route["qualification"].get("required", False))
    ]
    return {
        "schema_version": "1.0.0",
        "command": "config_validate",
        "valid": True,
        "configuration_digest": plan.configuration_digest,
        "entry_mode": plan.entry_mode,
        "runtime_id": plan.runtime_id,
        "runtime_version": plan.runtime_version,
        "profile_id": plan.profile_id,
        "profile_version": plan.profile_version,
        "canonical_owner_component_id": plan.canonical_owner_component_id,
        "canonical_owner_capability_id": plan.canonical_owner_capability_id,
        "route_count": len(plan.resolved_routes),
        "required_projection_ids": list(plan.required_projection_ids),
        "required_qualification_routes": required_qualification_routes,
        "qualification_binding_count": len(bindings),
        "authority_effect": "none",
        "startable_configuration": True,
        "plan": plan.to_dict(),
    }


def _currentness_summary(snapshots: Mapping[str, dict]) -> dict:
    if not snapshots:
        return {
            "status": "not_observed",
            "operation_count": 0,
            "quiescent_operations": 0,
            "pending_operations": 0,
            "degraded_operations": 0,
        }
    quiescent = pending = degraded = 0
    operations: list[dict] = []
    for operation_id, snapshot in sorted(snapshots.items()):
        try:
            disposition = VisibilityTracker.restore_after_restart(snapshot).evaluate()
        except (KeyError, TypeError, ValueError) as exc:
            degraded += 1
            operations.append({
                "operation_id": operation_id,
                "status": "invalid_snapshot",
                "detail": str(exc),
            })
            continue
        if disposition["quiescent"]:
            quiescent += 1
            status = "quiescent"
        elif disposition["settled"]:
            degraded += 1
            status = "degraded"
        else:
            pending += 1
            status = "pending"
        operations.append({
            "operation_id": operation_id,
            "status": status,
            "pending_required_obligations": disposition["pending_required_obligations"],
            "failed_required_obligations": disposition["failed_required_obligations"],
        })
    if degraded:
        status = "degraded"
    elif pending:
        status = "pending"
    else:
        status = "quiescent"
    return {
        "status": status,
        "operation_count": len(snapshots),
        "quiescent_operations": quiescent,
        "pending_operations": pending,
        "degraded_operations": degraded,
        "operations": operations,
    }


def diagnose(
    config_path: str | Path,
    *,
    qualification_path: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> dict:
    value = load_configuration_value(config_path)
    bindings = load_qualification_bindings(qualification_path)
    plan = validate_runtime_behavior_contract(value, qualification_bindings=bindings)

    report = {
        "schema_version": "1.0.0",
        "command": "doctor",
        "configuration": {
            "status": "valid",
            "digest": plan.configuration_digest,
            "entry_mode": plan.entry_mode,
            "profile_id": plan.profile_id,
            "profile_version": plan.profile_version,
            "route_count": len(plan.resolved_routes),
            "required_projection_ids": list(plan.required_projection_ids),
            "authority_effect": "none",
        },
        "qualification": {
            "status": "valid_for_configured_routes",
            "binding_count": len(bindings),
            "scope": "configured_routes_only",
        },
        "durable_state": {"status": "not_checked"},
        "recovery": {"status": "not_attempted"},
        "currentness": {"status": "not_checked"},
        "provider_availability": {
            "status": "not_probed",
            "detail": "configuration and recovery evidence do not prove live provider availability",
        },
        "configuration_startable": True,
        "operational_readiness": "not_proven",
        "authority_effect": "none",
    }

    if state_dir is None:
        return report

    root = Path(state_dir)
    manifest = root / "runtime-manifest.json"
    config_binding = root / "configuration-binding.json"
    if not root.exists() or not manifest.exists():
        report["durable_state"] = {
            "status": "not_initialized",
            "state_dir": str(root),
        }
        report["currentness"] = {"status": "not_observed"}
        report["operational_readiness"] = "configuration_valid_state_not_initialized"
        return report

    report["durable_state"] = {
        "status": "checkpoint_present",
        "state_dir": str(root),
        "configuration_binding_present": config_binding.exists(),
    }
    try:
        runtime = ConfigBoundRestartRuntime.recover(root, plan=plan)
    except RuntimeRecoveryError as exc:
        report["recovery"] = {
            "status": "failed_closed",
            "detail": str(exc),
        }
        report["currentness"] = {"status": "not_proven"}
        report["configuration_startable"] = False
        report["operational_readiness"] = "blocked_by_recovery_failure"
        return report

    evidence = runtime.recovery_evidence
    report["recovery"] = {
        "status": "recovered",
        "durability_profile": evidence.durability_profile,
        "recovery_posture": evidence.recovery_posture,
        "base_generation": evidence.base_generation,
        "configuration_digest": evidence.configuration_digest,
        "plan_digest": evidence.plan_digest,
        "route_activations": [item.to_dict() for item in evidence.route_activations],
    }
    report["durable_state"]["status"] = "recovered"
    report["currentness"] = _currentness_summary(runtime.visibility_snapshots)
    if report["currentness"]["status"] == "degraded":
        report["operational_readiness"] = "degraded_currentness"
    elif report["currentness"]["status"] == "pending":
        report["operational_readiness"] = "pending_currentness"
    else:
        report["operational_readiness"] = "provider_availability_not_probed"
    return report
