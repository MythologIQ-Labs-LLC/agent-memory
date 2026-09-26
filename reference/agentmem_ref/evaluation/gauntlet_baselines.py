"""Deterministic baseline adapters for Agent Memory Gauntlet orchestration tests.

These adapters are intentionally simple and are not the canonical Agent Memory adapter.
They prove the system-neutral transport/operation contract only.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from typing import Any, Mapping

from .gauntlet_contract import CONTRACT_VERSION, validate_operation_envelope

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_NO_MEMORY_STORES: dict[str, list[dict[str, str]]] = defaultdict(list)
_LEXICAL_STORES: dict[str, list[dict[str, str]]] = defaultdict(list)


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(value)}


def _response(
    request: Mapping[str, Any],
    *,
    status: str = "ok",
    result: Mapping[str, Any] | None = None,
    error: Mapping[str, Any] | None = None,
    started: float | None = None,
) -> dict[str, Any]:
    elapsed_ms = 0.0 if started is None else max(0.0, (time.perf_counter() - started) * 1000.0)
    response = {
        "contract_family": "agent-memory-gauntlet-operation",
        "contract_version": CONTRACT_VERSION,
        "direction": "response",
        "operation": request["operation"],
        "request_id": request["request_id"],
        "status": status,
        "result": None if result is None else dict(result),
        "error": None if error is None else dict(error),
        "timing": {"elapsed_ms": elapsed_ms},
        "adapter_evidence": {"adapter_kind": "gauntlet_baseline"},
        "authority_effect": "none",
    }
    return validate_operation_envelope(response)


def _handle(
    request: Mapping[str, Any],
    *,
    stores: dict[str, list[dict[str, str]]],
    lexical: bool,
) -> dict[str, Any]:
    request = validate_operation_envelope(request)
    started = time.perf_counter()
    operation = request["operation"]
    payload = request["payload"]
    namespace = str(payload.get("namespace", "default"))

    if operation == "describe":
        return _response(
            request,
            result={
                "adapter": "lexical" if lexical else "no_memory",
                "probe_only": True,
            },
            started=started,
        )
    if operation == "reset":
        stores[namespace] = []
        return _response(request, result={"reset": True}, started=started)
    if operation == "remember":
        record = payload.get("record")
        if not isinstance(record, Mapping) or not record.get("id") or not isinstance(record.get("text"), str):
            return _response(
                request,
                status="invalid_request",
                error={
                    "source": "system_adapter",
                    "code": "invalid_record",
                    "message": "remember requires record.id and record.text",
                },
                started=started,
            )
        if lexical:
            stores[namespace].append({"id": str(record["id"]), "text": str(record["text"])})
        return _response(request, result={"accepted": True}, started=started)
    if operation == "recall":
        if not lexical:
            return _response(request, result={"items": []}, started=started)
        query = str(payload.get("query", ""))
        query_tokens = _tokens(query)
        ranked = []
        for index, record in enumerate(stores[namespace]):
            overlap = len(query_tokens & _tokens(record["text"]))
            if overlap:
                ranked.append((-overlap, index, record))
        ranked.sort(key=lambda item: (item[0], item[1], item[2]["id"]))
        limit = max(0, int(payload.get("limit", 5)))
        return _response(
            request,
            result={
                "items": [
                    {"id": item[2]["id"], "score": float(-item[0])}
                    for item in ranked[:limit]
                ]
            },
            started=started,
        )
    if operation == "health":
        return _response(request, result={"status": "ok"}, started=started)
    return _response(
        request,
        status="unsupported",
        error={
            "source": "system_adapter",
            "code": "unsupported_operation",
            "message": f"{operation} is not supported by this baseline",
        },
        started=started,
    )


def no_memory_adapter(request: Mapping[str, Any]) -> dict[str, Any]:
    """Accept writes but retain nothing and return no recall candidates."""

    return _handle(request, stores=_NO_MEMORY_STORES, lexical=False)


def lexical_adapter(request: Mapping[str, Any]) -> dict[str, Any]:
    """Minimal deterministic token-overlap memory baseline."""

    return _handle(request, stores=_LEXICAL_STORES, lexical=True)


def broken_adapter(request: Mapping[str, Any]) -> dict[str, Any]:
    """Fixture adapter used to prove system-adapter failure attribution."""

    raise RuntimeError("intentional Gauntlet fixture adapter failure")


__all__ = ["no_memory_adapter", "lexical_adapter", "broken_adapter"]
