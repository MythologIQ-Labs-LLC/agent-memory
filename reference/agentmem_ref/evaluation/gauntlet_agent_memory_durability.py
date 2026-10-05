"""Agent Memory public-facade adapter for the durability/recovery Gauntlet slice.

This adapter is deliberately separate from the existing governance adapter so the
provenance identity of prior Gauntlet evidence does not drift when durability operations
are added. It translates the neutral Gauntlet operation contract into only supported
public ``AgentMemory`` facade behavior.

The qualified local runtime is single-tenant. The adapter exercises scope isolation
inside one tenant and maps neutral ``recover`` to the supported ``AgentMemory.open``
create-or-recover boundary. The public facade does not expose checkpoint creation, so
checkpoint remains unsupported. Correction also remains unsupported in this contestant
configuration until the neutral Gauntlet contract can carry the qualified evidence or
attestation required by Agent Memory's ordinary PAMA correction path.
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

_BASE = Path(tempfile.gettempdir()) / "agent-memory-gauntlet-public-durability"
_TENANT = "tenant:gauntlet-public-durability"
_ACTOR = "agent:gauntlet-durability"
_PURPOSE = "Agent Memory Gauntlet public durability qualification"

# Translation-only metadata. Lifecycle decisions are never made from this map. The SUT
# returns fact UUIDs while the neutral Gauntlet cases use stable record IDs.
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


def _drop_record_mapping(namespace: str, record_id: str) -> None:
    records = _RECORDS.get(namespace, {})
    for fact_uuid, record in list(records.items()):
        if record.get("id") == record_id:
            records.pop(fact_uuid, None)


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
            "adapter_kind": "agent_memory_public_durability",
            "public_contract": "1.3.0",
            "translation_only": True,
            "tenant_model": "single_tenant_local_composition",
            "recovery_surface": "AgentMemory.open",
            "checkpoint_surface": "unsupported_on_public_facade",
            "correction_surface": "unsupported_without_neutral_qualified_evidence_contract",
        },
        "authority_effect": "none",
    }
    return validate_operation_envelope(response)


def _invalid(request: Mapping[str, Any], code: str, message: str, *, started: float) -> dict[str, Any]:
    return _response(
        request,
        status="invalid_request",
        error={"source": "system_adapter", "code": code, "message": message},
        started=started,
    )


def _sut_refused(
    request: Mapping[str, Any], code: str, message: str, *, started: float
) -> dict[str, Any]:
    return _response(
        request,
        status="refused",
        error={"source": "system_under_test", "code": code, "message": message},
        started=started,
    )


def agent_memory_durability_adapter(request: Mapping[str, Any]) -> dict[str, Any]:
    """Translate one neutral durability operation into the public Agent Memory facade."""

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
                "adapter_enforces_lifecycle_policy": False,
                "recovery_surface": "AgentMemory.open",
                "checkpoint_surface": "unsupported",
                "correction_surface": "unsupported_without_neutral_qualified_evidence_contract",
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

    scope = str(payload.get("scope", ""))
    if not scope:
        return _invalid(
            request,
            "missing_scope",
            "Agent Memory durability adapter operations require scope",
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
            return _sut_refused(
                request,
                "remember_refused",
                str(outcome.get("refusal") or "remember was not committed"),
                started=started,
            )
        fact_uuid = str(outcome["fact_uuid"])
        _drop_record_mapping(namespace, record_id)
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
                items.append({"id": str(fact_uuid)})
            else:
                items.append({"id": translated["id"], "text": translated["text"]})
        return _response(
            request,
            result={
                "items": items,
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
            return _sut_refused(
                request,
                "forget_refused",
                str(outcome.get("refusal") or "forget was not committed"),
                started=started,
            )
        _drop_record_mapping(namespace, record_id)
        return _response(
            request,
            result={"deleted": True, "deletion_semantics": "governed_pruning"},
            started=started,
        )

    if operation == "history":
        record_id = str(payload.get("id", ""))
        if not record_id:
            return _invalid(
                request,
                "missing_memory_id",
                "history requires id",
                started=started,
            )
        with _handle(namespace, scope) as memory:
            outcome = memory.history(record_id)
        return _response(
            request,
            result={"history": outcome.get("history")},
            started=started,
        )

    if operation == "recover":
        # Opening existing durable state is the supported public recovery boundary. The
        # handle is closed immediately so no hidden in-process state survives the case.
        with _handle(namespace, scope) as memory:
            posture = memory.posture()
        return _response(
            request,
            result={
                "recovered": True,
                "recovery_surface": "AgentMemory.open",
                "namespace_identity": _namespace_key(namespace),
                "posture_stage": posture.get("stage"),
            },
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
            "message": f"{operation} is not supported by this Agent Memory durability contestant",
        },
        started=started,
    )


__all__ = ["agent_memory_durability_adapter"]
