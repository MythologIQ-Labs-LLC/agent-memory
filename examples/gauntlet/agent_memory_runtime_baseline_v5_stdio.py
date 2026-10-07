#!/usr/bin/env python3
"""Public-process Gauntlet contestant for Agent Memory Runtime Baseline v5.

This adapter deliberately imports only the public ``AgentMemory`` facade. It runs as a
separate stdio process under the same neutral Gauntlet operation contract used by
external contestants. The adapter translates neutral benchmark record IDs to Agent
Memory fact UUIDs; it does not implement admission, ranking, integrity, or governance
policy itself.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from agentmem_ref import AgentMemory

CONTRACT_FAMILY = "agent-memory-gauntlet-operation"
CONTRACT_VERSION = "0.1.0"
PUBLIC_CONTRACT_VERSION = "1.5.0"
FROZEN_RUNTIME_REVISION = "74c8683e33f2b716577138e5b4c750a9ae670966"
TENANT = "tenant:gauntlet-runtime-baseline-v5"
ACTOR = "agent:gauntlet-runtime-baseline-v5"
SCOPE = "scope:gauntlet-runtime-baseline-v5"
PURPOSE = "Runtime Baseline v5 public Gauntlet qualification"
BASE = Path(tempfile.gettempdir()) / "agent-memory-gauntlet-runtime-baseline-v5"

# Translation-only state. The SUT owns memory semantics; this map merely preserves the
# benchmark's stable record IDs across the public facade's fact UUID responses.
RECORDS: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)


def namespace_key(namespace: str) -> str:
    return hashlib.sha256(namespace.encode("utf-8")).hexdigest()


def root(namespace: str) -> Path:
    return BASE / namespace_key(namespace)


def handle_for(namespace: str) -> AgentMemory:
    return AgentMemory.open(
        root(namespace),
        tenant=TENANT,
        actor_id=ACTOR,
        scope=SCOPE,
        purpose=PURPOSE,
    )


def response(
    request: dict[str, Any],
    *,
    status: str = "ok",
    result: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
    started: float,
) -> dict[str, Any]:
    return {
        "contract_family": CONTRACT_FAMILY,
        "contract_version": CONTRACT_VERSION,
        "direction": "response",
        "operation": str(request.get("operation", "health")),
        "request_id": str(request.get("request_id", "missing-request-id")),
        "status": status,
        "result": result,
        "error": error,
        "timing": {"elapsed_ms": max(0.0, (time.perf_counter() - started) * 1000.0)},
        "adapter_evidence": {
            "adapter_kind": "agent_memory_public_stdio",
            "surface": "AgentMemory public facade",
            "public_contract": PUBLIC_CONTRACT_VERSION,
            "frozen_runtime_revision": FROZEN_RUNTIME_REVISION,
            "translation_only": True,
        },
        "authority_effect": "none",
    }


def invalid(request: dict[str, Any], code: str, message: str, *, started: float) -> dict[str, Any]:
    return response(
        request,
        status="invalid_request",
        error={"source": "system_adapter", "code": code, "message": message},
        started=started,
    )


def handle(request: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    if request.get("contract_family") != CONTRACT_FAMILY or request.get("direction") != "request":
        return invalid(request, "invalid_envelope", "expected a Gauntlet request envelope", started=started)

    payload = request.get("payload")
    if not isinstance(payload, dict):
        return invalid(request, "invalid_payload", "payload must be an object", started=started)

    operation = request.get("operation")
    namespace = str(payload.get("namespace", "default"))

    if operation == "describe":
        return response(
            request,
            result={
                "system": "Agent Memory",
                "runtime": "agent-memory-rc1-local",
                "runtime_version": "0.2.0-rc1",
                "runtime_profile": "rc1-local-sqlite-composition",
                "public_contract": PUBLIC_CONTRACT_VERSION,
                "frozen_runtime_revision": FROZEN_RUNTIME_REVISION,
                "surface": "AgentMemory public facade",
                "transport": "stdio",
                "adapter_enforces_memory_policy": False,
            },
            started=started,
        )

    if operation == "health":
        try:
            with handle_for(namespace) as memory:
                posture = memory.posture()
            return response(request, result={"status": "ok", "posture_stage": posture.get("stage")}, started=started)
        except Exception as exc:  # noqa: BLE001
            return response(
                request,
                status="system_error",
                error={"source": "system_under_test", "code": "health_failed", "message": f"{type(exc).__name__}: {exc}"},
                started=started,
            )

    if operation == "reset":
        shutil.rmtree(root(namespace), ignore_errors=True)
        RECORDS.pop(namespace, None)
        return response(request, result={"reset": True, "reset_support": "mapped"}, started=started)

    if operation == "remember":
        record = payload.get("record")
        if not isinstance(record, dict) or not record.get("id") or not isinstance(record.get("text"), str):
            return invalid(request, "invalid_record", "remember requires record.id and record.text", started=started)
        record_id = str(record["id"])
        text = str(record["text"])
        try:
            with handle_for(namespace) as memory:
                outcome = memory.remember(record_id, text)
        except Exception as exc:  # noqa: BLE001
            return response(
                request,
                status="system_error",
                error={"source": "system_under_test", "code": "remember_error", "message": f"{type(exc).__name__}: {exc}"},
                started=started,
            )
        if not outcome.get("committed") or not outcome.get("fact_uuid"):
            return response(
                request,
                status="refused",
                error={
                    "source": "system_under_test",
                    "code": "remember_refused",
                    "message": str(outcome.get("refusal") or "remember was not committed"),
                },
                started=started,
            )
        fact_uuid = str(outcome["fact_uuid"])
        RECORDS[namespace][fact_uuid] = {"id": record_id, "text": text}
        return response(request, result={"accepted": True, "fact_uuid": fact_uuid}, started=started)

    if operation == "recall":
        query = str(payload.get("query", ""))
        limit = max(0, int(payload.get("limit", 5)))
        try:
            with handle_for(namespace) as memory:
                outcome = memory.recall(query)
        except Exception as exc:  # noqa: BLE001
            return response(
                request,
                status="system_error",
                error={"source": "system_under_test", "code": "recall_error", "message": f"{type(exc).__name__}: {exc}"},
                started=started,
            )
        admitted = list(outcome.get("admitted") or [])[:limit]
        items = []
        for fact_uuid in admitted:
            translated = RECORDS.get(namespace, {}).get(str(fact_uuid))
            if translated is None:
                items.append({"id": str(fact_uuid)})
            else:
                items.append({"id": translated["id"], "text": translated["text"]})
        return response(
            request,
            result={"items": items, "candidate_count": len(outcome.get("candidates") or [])},
            started=started,
        )

    return response(
        request,
        status="unsupported",
        error={
            "source": "system_adapter",
            "code": "unsupported_operation",
            "message": f"{operation!r} is not supported by this baseline adapter",
        },
        started=started,
    )


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must decode to an object")
            output = handle(request)
        except Exception as exc:  # noqa: BLE001
            output = {
                "contract_family": CONTRACT_FAMILY,
                "contract_version": CONTRACT_VERSION,
                "direction": "response",
                "operation": "health",
                "request_id": "adapter-parse-error",
                "status": "adapter_error",
                "result": None,
                "error": {
                    "source": "system_adapter",
                    "code": "adapter_parse_error",
                    "message": f"{type(exc).__name__}: {exc}",
                },
                "timing": {"elapsed_ms": 0.0},
                "adapter_evidence": {"adapter_kind": "agent_memory_public_stdio"},
                "authority_effect": "none",
            }
        print(json.dumps(output, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
