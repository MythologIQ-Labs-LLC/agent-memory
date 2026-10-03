#!/usr/bin/env python3
"""Self-contained external-process example for the Agent Memory Gauntlet.

This file intentionally depends only on the Python standard library. It demonstrates
how an external memory-system author can implement the bounded Gauntlet stdio
operation contract without importing Agent Memory runtime code.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from typing import Any

CONTRACT_FAMILY = "agent-memory-gauntlet-operation"
CONTRACT_VERSION = "0.1.0"
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
STORES: dict[str, list[dict[str, str]]] = defaultdict(list)


def tokens(value: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(value)}


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
        "operation": request.get("operation", "health"),
        "request_id": str(request.get("request_id", "missing-request-id")),
        "status": status,
        "result": result,
        "error": error,
        "timing": {"elapsed_ms": max(0.0, (time.perf_counter() - started) * 1000.0)},
        "adapter_evidence": {
            "adapter_kind": "external_example",
            "implementation": "standard_library_lexical_memory",
        },
        "authority_effect": "none",
    }


def handle(request: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    if request.get("contract_family") != CONTRACT_FAMILY or request.get("direction") != "request":
        return response(
            request,
            status="invalid_request",
            error={
                "source": "system_adapter",
                "code": "invalid_envelope",
                "message": "expected a Gauntlet request envelope",
            },
            started=started,
        )

    operation = request.get("operation")
    payload = request.get("payload")
    if not isinstance(payload, dict):
        return response(
            request,
            status="invalid_request",
            error={
                "source": "system_adapter",
                "code": "invalid_payload",
                "message": "payload must be an object",
            },
            started=started,
        )

    namespace = str(payload.get("namespace", "default"))

    if operation == "describe":
        return response(
            request,
            result={
                "adapter": "minimal-stdio-example",
                "system": "standard-library-lexical-memory",
                "probe_only": True,
            },
            started=started,
        )

    if operation == "health":
        return response(request, result={"status": "ok"}, started=started)

    if operation == "reset":
        STORES[namespace] = []
        return response(request, result={"reset": True}, started=started)

    if operation == "remember":
        record = payload.get("record")
        if not isinstance(record, dict) or not record.get("id") or not isinstance(record.get("text"), str):
            return response(
                request,
                status="invalid_request",
                error={
                    "source": "system_adapter",
                    "code": "invalid_record",
                    "message": "remember requires record.id and record.text",
                },
                started=started,
            )
        STORES[namespace].append({"id": str(record["id"]), "text": str(record["text"])})
        return response(request, result={"accepted": True}, started=started)

    if operation == "recall":
        query = str(payload.get("query", ""))
        query_tokens = tokens(query)
        ranked: list[tuple[int, int, dict[str, str]]] = []
        for index, record in enumerate(STORES[namespace]):
            overlap = len(query_tokens & tokens(record["text"]))
            if overlap:
                ranked.append((-overlap, index, record))
        ranked.sort(key=lambda item: (item[0], item[1], item[2]["id"]))
        limit = max(0, int(payload.get("limit", 5)))
        return response(
            request,
            result={
                "items": [
                    {"id": item[2]["id"], "score": float(-item[0])}
                    for item in ranked[:limit]
                ]
            },
            started=started,
        )

    return response(
        request,
        status="unsupported",
        error={
            "source": "system_adapter",
            "code": "unsupported_operation",
            "message": f"{operation!r} is not supported by this example adapter",
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
        except Exception as exc:
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
                "adapter_evidence": {"adapter_kind": "external_example"},
                "authority_effect": "none",
            }
        print(json.dumps(output, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
