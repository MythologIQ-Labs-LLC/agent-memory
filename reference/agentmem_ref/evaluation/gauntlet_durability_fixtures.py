"""Adversarial durability fixtures used to prove the #571 evaluator itself.

These are benchmark-owned composed test systems, not evidence about real products.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from .gauntlet_contract import CONTRACT_VERSION, validate_operation_envelope

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_STORES: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))


def _response(
    request: Mapping[str, Any],
    *,
    result: Mapping[str, Any] | None = None,
    status: str = "ok",
    error: Mapping[str, Any] | None = None,
    started: float,
) -> dict[str, Any]:
    return validate_operation_envelope(
        {
            "contract_family": "agent-memory-gauntlet-operation",
            "contract_version": CONTRACT_VERSION,
            "direction": "response",
            "operation": request["operation"],
            "request_id": request["request_id"],
            "status": status,
            "result": None if result is None else dict(result),
            "error": None if error is None else dict(error),
            "timing": {"elapsed_ms": max(0.0, (time.perf_counter() - started) * 1000.0)},
            "adapter_evidence": {
                "adapter_kind": "gauntlet_durability_fixture",
                "fixture_mode": "lossy_recovery",
            },
            "authority_effect": "none",
        }
    )


def lossy_recovery_adapter(request: Mapping[str, Any]) -> dict[str, Any]:
    """Pretend recovery succeeded while silently losing the persisted namespace."""

    request = validate_operation_envelope(request)
    started = time.perf_counter()
    operation = request["operation"]
    payload = request["payload"]
    namespace = str(payload.get("namespace", "default"))
    scope = str(payload.get("scope", "scope:default"))

    if operation == "describe":
        return _response(
            request,
            result={"fixture_mode": "lossy_recovery", "probe_only": True},
            started=started,
        )
    if operation == "reset":
        _STORES[namespace].clear()
        return _response(request, result={"reset": True}, started=started)
    if operation == "remember":
        record = payload.get("record")
        if not isinstance(record, Mapping) or not record.get("id") or not isinstance(record.get("text"), str):
            return _response(
                request,
                status="invalid_request",
                error={"source": "system_adapter", "code": "invalid_record", "message": "remember requires record.id and record.text"},
                started=started,
            )
        _STORES[namespace][scope].append({"id": str(record["id"]), "text": str(record["text"])})
        return _response(request, result={"accepted": True}, started=started)
    if operation == "recall":
        query_tokens = {token.lower() for token in _TOKEN_RE.findall(str(payload.get("query", "")))}
        items = []
        for record in _STORES[namespace][scope]:
            record_tokens = {token.lower() for token in _TOKEN_RE.findall(record["text"])}
            if query_tokens & record_tokens:
                items.append(dict(record))
        return _response(request, result={"items": items[: int(payload.get("limit", 10))]}, started=started)
    if operation == "recover":
        # This is the defect under test: state disappears, yet the SUT claims recovery
        # succeeded. The evaluator must call this a behavioral failure with sufficient
        # evidence instead of an execution failure.
        _STORES[namespace].clear()
        return _response(
            request,
            result={"recovered": True, "fixture_defect": "silent_state_loss"},
            started=started,
        )
    if operation == "health":
        return _response(request, result={"status": "ok"}, started=started)
    return _response(
        request,
        status="unsupported",
        error={"source": "system_adapter", "code": "unsupported_operation", "message": f"{operation} is unsupported by the lossy recovery fixture"},
        started=started,
    )


__all__ = ["lossy_recovery_adapter"]
