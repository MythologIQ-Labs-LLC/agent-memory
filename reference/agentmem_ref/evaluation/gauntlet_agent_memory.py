"""Agent Memory public-facade adapter for the Governance Gauntlet alpha.

This adapter is intentionally thin. It translates the neutral Gauntlet operation
contract into the public ``AgentMemory`` facade and does not implement isolation,
admission, ranking, or deletion policy itself.

The qualified local runtime is single-tenant. This adapter therefore does not claim
cross-tenant isolation. It does exercise native scope isolation inside one tenant,
caller-visible foreign-cardinality minimization, deletion, and restart-safe durable
state through repeated ``AgentMemory.open`` recovery.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import time
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from agentmem_ref import AgentMemory

from .gauntlet_contract import CONTRACT_VERSION, validate_operation_envelope

_BASE = Path(tempfile.gettempdir()) / "agent-memory-gauntlet-public-facade"
_TENANT = "tenant:gauntlet-public-facade"
_ACTOR = "agent:gauntlet"
_PURPOSE = "Agent Memory Governance Gauntlet synthetic qualification"

# Translation-only metadata. Governance decisions are never made from this map.
# The SUT returns fact UUIDs while the neutral Gauntlet cases use stable record IDs.
_RECORDS: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)


def _namespace_key(namespace: str) -> str:
    return hashlib.sha256(namespace.encode("utf-8")).hexdigest()


def _root(namespace: str) -> Path:
    return _BASE / _namespace_key(namespace)


def _handle(namespace: str, scope: str) -> AgentMemory:
    return AgentMemory.open(
        _root(namespace),
        tenant=_TENANT,
        actor_id=_ACTOR,
        scope=scope,
        purpose=_PURPOSE,
    )


def _response(
    request: Mapping[str, Any],
    *,
    status: str = "ok",
    result: Mapping[str, Any] | None = None,
    error: Mapping[str, Any] | None = None,
    started: float,
) -> dict[str, Any]:
    response = {
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
            "adapter_kind": "agent_memory_public_facade",
            "public_contract": "1.3.0",
            "translation_only": True,
            "tenant_model": "single_tenant_local_composition",
        },
        "authority_effect": "none",
    }
    return validate_operation_envelope(response)


def _invalid(request: Mapping[str, Any], code: str, message: str, *, started: float):
    return _response(
        request,
        status="invalid_request",
        error={"source": "system_adapter", "code": code, "message": message},
        started=started,
    )


def agent_memory_public_adapter(request: Mapping[str, Any]) -> dict[str, Any]:
    """Translate one neutral Gauntlet operation into the public Agent Memory facade."""

    request = validate_operation_envelope(request)
    started = time.perf_counter()
    operation = request["operation"]
    payload = request["payload"]
    namespace = str(payload.get("namespace", "default"))

    if operation == "describe":
        return _response(
            request,
            result={
                "system": "Agent Memory",
                "surface": "AgentMemory public facade",
                "public_contract": "1.3.0",
                "tenant_model": "single_tenant_local_composition",
                "adapter_enforces_governance": False,
            },
            started=started,
        )

    if operation == "reset":
        shutil.rmtree(_root(namespace), ignore_errors=True)
        _RECORDS.pop(namespace, None)
        return _response(
            request,
            result={"reset": True, "reset_support": "mapped"},
            started=started,
        )

    # The local public composition is single-tenant. Tenant routing is deliberately not
    # manufactured here, and the manifest truthfully leaves tenant isolation unsupported.
    scope = str(payload.get("scope", ""))
    if not scope:
        return _invalid(
            request,
            "missing_scope",
            "Agent Memory governance adapter operations require scope",
            started=started,
        )

    if operation == "remember":
        record = payload.get("record")
        if not isinstance(record, Mapping) or not record.get("id") or not isinstance(record.get("text"), str):
            return _invalid(
                request,
                "invalid_record",
                "remember requires record.id and record.text",
                started=started,
            )
        record_id = str(record["id"])
        text = str(record["text"])
        with _handle(namespace, scope) as memory:
            outcome = memory.remember(record_id, text)
        if not outcome.get("committed") or not outcome.get("fact_uuid"):
            return _response(
                request,
                status="error",
                error={
                    "source": "system_under_test",
                    "code": "remember_refused",
                    "message": str(outcome.get("refusal") or "remember was not committed"),
                },
                started=started,
            )
        fact_uuid = str(outcome["fact_uuid"])
        _RECORDS[namespace][fact_uuid] = {
            "id": record_id,
            "text": text,
            "scope": scope,
        }
        return _response(
            request,
            result={"accepted": True, "fact_uuid": fact_uuid},
            started=started,
        )

    if operation == "recall":
        query = str(payload.get("query", ""))
        limit = max(0, int(payload.get("limit", 10)))
        with _handle(namespace, scope) as memory:
            outcome = memory.recall(query)
        admitted = list(outcome.get("admitted") or [])[:limit]
        items = []
        for fact_uuid in admitted:
            translated = _RECORDS.get(namespace, {}).get(str(fact_uuid))
            if translated is None:
                # The public facade may contain state not created by this Gauntlet run.
                # Never fabricate content or identifiers for it.
                items.append({"id": str(fact_uuid)})
            else:
                items.append(
                    {
                        "id": translated["id"],
                        "text": translated["text"],
                    }
                )
        return _response(
            request,
            result={
                "items": items,
                # Contract 1.3.0 candidates are already domain-eligible. Exposing their
                # count therefore tests the public minimization boundary rather than a
                # hidden adapter-side prefilter.
                "candidate_count": len(outcome.get("candidates") or []),
            },
            started=started,
        )

    if operation == "forget":
        record_id = str(payload.get("id", ""))
        if not record_id:
            return _invalid(
                request,
                "missing_memory_id",
                "forget requires id",
                started=started,
            )
        with _handle(namespace, scope) as memory:
            outcome = memory.forget(record_id)
        if not outcome.get("committed"):
            return _response(
                request,
                status="error",
                error={
                    "source": "system_under_test",
                    "code": "forget_refused",
                    "message": str(outcome.get("refusal") or "forget was not committed"),
                },
                started=started,
            )
        return _response(
            request,
            result={"deleted": True, "deletion_semantics": "governed_pruning"},
            started=started,
        )

    if operation == "health":
        with _handle(namespace, scope) as memory:
            posture = memory.posture()
        return _response(
            request,
            result={"status": "ok", "posture_stage": posture.get("stage")},
            started=started,
        )

    return _response(
        request,
        status="unsupported",
        error={
            "source": "system_adapter",
            "code": "unsupported_operation",
            "message": f"{operation} is not supported by the Agent Memory Gauntlet adapter",
        },
        started=started,
    )


__all__ = ["agent_memory_public_adapter"]
