"""Deterministic Gauntlet orchestration probe.

This workload is ``baseline_or_probe`` evidence. It proves orchestration and normalized
evidence plumbing; it is not an independent benchmark of memory quality.
"""

from __future__ import annotations

import hashlib
import json
import time
from statistics import median
from typing import Any

from .gauntlet_contract import CONTRACT_VERSION
from .gauntlet_transport import AdapterSession, GauntletExecutionError

FIXTURE = {
    "records": [
        {"id": "probe:cobalt", "text": "Project Alpha uses the cobalt ledger for invoices."},
        {"id": "probe:amber", "text": "Project Beta uses the amber queue for dispatch."},
        {"id": "probe:cedar", "text": "Project Gamma uses the cedar cache for sessions."},
    ],
    "queries": [
        {"query": "Which project uses the cobalt ledger?", "expected_id": "probe:cobalt"},
        {"query": "What uses the amber queue?", "expected_id": "probe:amber"},
        {"query": "Where is the cedar cache used?", "expected_id": "probe:cedar"},
    ],
}
FIXTURE_BYTES = (json.dumps(FIXTURE, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
FIXTURE_SHA256 = hashlib.sha256(FIXTURE_BYTES).hexdigest()


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


def _require_ok(response: dict[str, Any], operation: str) -> None:
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


def run_retrieval_probe(
    session: AdapterSession,
    *,
    run_id: str,
    namespace: str,
) -> dict[str, Any]:
    """Execute the deterministic retrieval probe through one adapter session."""

    started = time.perf_counter()
    transcript: list[dict[str, Any]] = []
    timings: list[float] = []
    sequence = 0

    def invoke(operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        nonlocal sequence
        sequence += 1
        request = _request(operation, f"{run_id}:{sequence:04d}", {"namespace": namespace, **payload})
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
        timing = response.get("timing") or {}
        if isinstance(timing.get("elapsed_ms"), (int, float)):
            timings.append(float(timing["elapsed_ms"]))
        _require_ok(response, operation)
        return response

    invoke("describe", {})
    invoke("reset", {})

    for record in FIXTURE["records"]:
        invoke("remember", {"record": record})

    rows = []
    correct = 0
    for item in FIXTURE["queries"]:
        response = invoke("recall", {"query": item["query"], "limit": 3})
        result = response.get("result") or {}
        candidates = result.get("items")
        if not isinstance(candidates, list):
            raise GauntletExecutionError(
                "system_adapter",
                "invalid_recall_result",
                "recall result.items must be a list",
            )
        top_id = None
        if candidates:
            first = candidates[0]
            if not isinstance(first, dict) or not first.get("id"):
                raise GauntletExecutionError(
                    "system_adapter",
                    "invalid_recall_item",
                    "recall items must be objects with non-empty id",
                )
            top_id = str(first["id"])
        hit = top_id == item["expected_id"]
        correct += int(hit)
        rows.append(
            {
                "query": item["query"],
                "expected_id": item["expected_id"],
                "top_id": top_id,
                "exact_top1": hit,
            }
        )

    elapsed_ms = max(0.0, (time.perf_counter() - started) * 1000.0)
    return {
        "profile_kind": "baseline_or_probe",
        "fixture_sha256": FIXTURE_SHA256,
        "sample_count": len(rows),
        "correct_top1": correct,
        "exact_top1": correct / len(rows),
        "operation_count": len(transcript),
        "operation_elapsed_ms_p50": median(timings) if timings else 0.0,
        "elapsed_ms": elapsed_ms,
        "rows": rows,
        "transcript": transcript,
        "authority_effect": "none",
    }


__all__ = ["FIXTURE", "FIXTURE_SHA256", "run_retrieval_probe"]
