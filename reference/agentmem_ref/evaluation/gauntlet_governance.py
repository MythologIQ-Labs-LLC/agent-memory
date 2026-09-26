"""Claim-driven Governance Gauntlet alpha cases and conformance fixtures (#559).

The fixture adapters in this module exist to prove the evaluator. They are composed test
systems, not evidence that an external runtime provides native governance. The runner
uses only public adapter operations and declared capabilities; it never requires PAMA or
Agent Memory lifecycle vocabulary.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import defaultdict
from collections.abc import Mapping
from typing import Any

from .contract import DIMENSIONS, dimension_report, metric_observation
from .gauntlet_contract import CONTRACT_VERSION, capability_support, validate_operation_envelope
from .gauntlet_transport import AdapterSession, GauntletExecutionError

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
_POSITIVE_SUPPORT = {"native", "mapped", "derived"}

CASE_DEFINITIONS = (
    ("GOV-ISO-001", "tenant_isolation", "wrong-tenant perfect match"),
    ("GOV-ISO-002", "scope_isolation", "wrong-scope perfect match"),
    ("GOV-ISO-005", "foreign_cardinality_non_disclosure", "foreign cardinality side channel"),
    ("GOV-DEL-001", "deletion", "delete then recall"),
    ("GOV-DEL-002", "durable_deletion", "delete then restart then recall"),
    ("GOV-AUTH-002", "tenant_isolation", "recency-as-authority attack"),
    ("GOV-AUTH-003", "tenant_isolation", "similarity-as-authority attack"),
    ("GOV-AUTH-004", "route_authority_isolation", "route-count authority laundering"),
    ("GOV-AUTH-005", "classifier_authority_isolation", "classifier authority laundering"),
    ("GOV-SRC-002", "source_trust", "spoofed provenance"),
)
CASE_FIXTURE_BYTES = (
    json.dumps(CASE_DEFINITIONS, sort_keys=True, separators=(",", ":")) + "\n"
).encode("utf-8")
CASE_FIXTURE_SHA256 = hashlib.sha256(CASE_FIXTURE_BYTES).hexdigest()

_STRICT_STORES: dict[str, dict[str, dict[str, dict[str, dict[str, str]]]]] = defaultdict(
    lambda: defaultdict(lambda: defaultdict(dict))
)
_LEAKY_STORES: dict[str, dict[str, dict[str, dict[str, dict[str, str]]]]] = defaultdict(
    lambda: defaultdict(lambda: defaultdict(dict))
)
_COUNT_LEAK_STORES: dict[str, dict[str, dict[str, dict[str, dict[str, str]]]]] = defaultdict(
    lambda: defaultdict(lambda: defaultdict(dict))
)


def _tokens(value: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(value)}


def _response(
    request: Mapping[str, Any],
    *,
    status: str = "ok",
    result: Mapping[str, Any] | None = None,
    error: Mapping[str, Any] | None = None,
    started: float | None = None,
    fixture_mode: str,
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
        "adapter_evidence": {
            "adapter_kind": "gauntlet_governance_fixture",
            "fixture_mode": fixture_mode,
        },
        "authority_effect": "none",
    }
    return validate_operation_envelope(response)


def _all_records(store, namespace: str):
    for tenant_scopes in store[namespace].values():
        for records in tenant_scopes.values():
            yield from records.values()


def _handle_fixture(
    request: Mapping[str, Any],
    *,
    store,
    mode: str,
) -> dict[str, Any]:
    request = validate_operation_envelope(request)
    started = time.perf_counter()
    operation = request["operation"]
    payload = request["payload"]
    namespace = str(payload.get("namespace", "default"))

    if operation == "describe":
        return _response(
            request,
            result={"fixture_mode": mode, "probe_only": True},
            started=started,
            fixture_mode=mode,
        )
    if operation == "reset":
        store[namespace].clear()
        return _response(
            request,
            result={"reset": True},
            started=started,
            fixture_mode=mode,
        )

    tenant = str(payload.get("tenant", ""))
    scope = str(payload.get("scope", ""))
    if not tenant or not scope:
        return _response(
            request,
            status="invalid_request",
            error={
                "source": "system_adapter",
                "code": "missing_governance_context",
                "message": "governance fixture operations require tenant and scope",
            },
            started=started,
            fixture_mode=mode,
        )

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
                fixture_mode=mode,
            )
        store[namespace][tenant][scope][str(record["id"])] = {
            "id": str(record["id"]),
            "text": str(record["text"]),
            "created_at": str(record.get("created_at", "")),
        }
        return _response(
            request,
            result={"accepted": True},
            started=started,
            fixture_mode=mode,
        )

    if operation == "forget":
        memory_id = str(payload.get("id", ""))
        if not memory_id:
            return _response(
                request,
                status="invalid_request",
                error={
                    "source": "system_adapter",
                    "code": "missing_memory_id",
                    "message": "forget requires id",
                },
                started=started,
                fixture_mode=mode,
            )
        removed = store[namespace][tenant][scope].pop(memory_id, None) is not None
        return _response(
            request,
            result={"deleted": removed},
            started=started,
            fixture_mode=mode,
        )

    if operation == "recall":
        query = str(payload.get("query", ""))
        query_tokens = _tokens(query)
        if mode == "leaky":
            visible = list(_all_records(store, namespace))
        else:
            visible = list(store[namespace][tenant][scope].values())
        ranked = []
        for index, record in enumerate(visible):
            overlap = len(query_tokens & _tokens(record["text"]))
            if overlap:
                ranked.append((-overlap, index, record))
        ranked.sort(key=lambda item: (item[0], item[1], item[2]["id"]))
        limit = max(0, int(payload.get("limit", 10)))
        result: dict[str, Any] = {
            "items": [
                {
                    "id": item[2]["id"],
                    "text": item[2]["text"],
                    "score": float(-item[0]),
                }
                for item in ranked[:limit]
            ]
        }
        if mode == "count_leak":
            global_matches = 0
            for record in _all_records(store, namespace):
                if query_tokens & _tokens(record["text"]):
                    global_matches += 1
            result["candidate_count"] = global_matches
        return _response(
            request,
            result=result,
            started=started,
            fixture_mode=mode,
        )

    if operation == "health":
        return _response(
            request,
            result={"status": "ok"},
            started=started,
            fixture_mode=mode,
        )

    return _response(
        request,
        status="unsupported",
        error={
            "source": "system_adapter",
            "code": "unsupported_operation",
            "message": f"{operation} is not supported by this governance fixture",
        },
        started=started,
        fixture_mode=mode,
    )


def strict_governance_adapter(request: Mapping[str, Any]) -> dict[str, Any]:
    return _handle_fixture(request, store=_STRICT_STORES, mode="strict")


def leaky_governance_adapter(request: Mapping[str, Any]) -> dict[str, Any]:
    return _handle_fixture(request, store=_LEAKY_STORES, mode="leaky")


def count_leak_governance_adapter(request: Mapping[str, Any]) -> dict[str, Any]:
    return _handle_fixture(request, store=_COUNT_LEAK_STORES, mode="count_leak")


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


def _support(manifest: Mapping[str, Any], capability: str) -> str | None:
    return capability_support(manifest, capability)


def _claim_state(manifest: Mapping[str, Any], capability: str) -> str:
    support = _support(manifest, capability)
    if support in _POSITIVE_SUPPORT:
        return "claimed"
    if support == "unknown":
        return "invalid"
    return "unsupported"


def _case(case_id: str, capability: str, result: str, *, observations=None, note=None) -> dict[str, Any]:
    value = {
        "case_id": case_id,
        "capability": capability,
        "result": result,
        "authority_effect": "none",
    }
    if observations is not None:
        value["observations"] = observations
    if note:
        value["note"] = note
    return value


def _returned_identifiers(result: Mapping[str, Any]) -> set[str]:
    identifiers: set[str] = set()
    items = result.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, Mapping) and item.get("id") is not None:
                identifiers.add(str(item["id"]))
    return identifiers


def _returned_texts(result: Mapping[str, Any]) -> set[str]:
    texts: set[str] = set()
    items = result.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, Mapping) and item.get("text") is not None:
                texts.add(str(item["text"]))
    return texts


def _result_payload(response: Mapping[str, Any]) -> dict[str, Any]:
    result = response.get("result")
    if not isinstance(result, Mapping):
        raise GauntletExecutionError(
            "system_adapter", "invalid_governance_result", "operation result must be an object"
        )
    return dict(result)


def _dimensions(cases: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions = {dimension: dimension_report("not_applicable") for dimension in DIMENSIONS}
    metrics = []
    measured = 0
    non_measured = 0
    for case in cases:
        metric_id = case["case_id"].lower().replace("-", "_")
        result = case["result"]
        if result in {"pass", "fail"}:
            measured += 1
            metrics.append(
                metric_observation(
                    metric_id,
                    value=result == "pass",
                    direction="descriptive",
                    unit="boolean",
                    population="one deterministic Governance Gauntlet case",
                    note=f"native verdict={result}; no aggregate governance score is implied",
                )
            )
        elif result == "unsupported":
            non_measured += 1
            metrics.append(
                metric_observation(
                    metric_id,
                    state="not_applicable",
                    direction="descriptive",
                    population="one deterministic Governance Gauntlet case",
                    note="capability not claimed; unsupported is not numeric failure",
                )
            )
        else:
            non_measured += 1
            metrics.append(
                metric_observation(
                    metric_id,
                    state="blocked",
                    direction="descriptive",
                    population="one deterministic Governance Gauntlet case",
                    note=case.get("note") or f"native verdict={result}",
                )
            )

    if measured and non_measured:
        governance_status = "partial"
    elif measured:
        governance_status = "measured"
    elif metrics and all(metric["state"] == "not_applicable" for metric in metrics):
        governance_status = "not_applicable"
    else:
        governance_status = "blocked"

    dimensions["governance"] = dimension_report(
        governance_status,
        metrics,
        notes=[
            "Case verdicts remain separate; this suite intentionally emits no universal governance score.",
            "Unsupported optional capability is represented as not_applicable in the common contract and retained as unsupported in native evidence.",
        ],
    )
    dimensions["evaluator_integrity"] = dimension_report(
        "measured",
        [
            metric_observation(
                "claim_driven_case_count",
                value=len(cases),
                direction="descriptive",
                unit="cases",
                population="Governance Gauntlet alpha case registry",
            ),
            metric_observation(
                "aggregate_governance_score_emitted",
                value=False,
                direction="descriptive",
                population="normalized Governance Gauntlet evidence",
            ),
        ],
    )
    dimensions["reproducibility"] = dimension_report(
        "measured",
        [
            metric_observation(
                "governance_case_fixture_sha256",
                value=CASE_FIXTURE_SHA256,
                direction="descriptive",
                population="Governance Gauntlet alpha case registry",
            )
        ],
    )
    return dimensions


def run_governance_alpha(
    session: AdapterSession,
    *,
    run_id: str,
    namespace: str,
) -> dict[str, Any]:
    """Run the first system-neutral Governance Gauntlet claim suite."""

    manifest = session.manifest
    sequence = 0
    operation_count = 0

    def invoke(operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        nonlocal sequence, operation_count
        sequence += 1
        operation_count += 1
        return session.invoke(_request(operation, f"{run_id}:gov:{sequence:04d}", payload))

    def setup_ok(response: Mapping[str, Any], operation: str) -> None:
        if response["status"] != "ok":
            error = response.get("error") or {}
            raise GauntletExecutionError(
                error.get("source") or "system_under_test",
                error.get("code") or f"{operation}_{response['status']}",
                error.get("message") or f"setup operation {operation} returned {response['status']}",
            )

    def reset() -> None:
        setup_ok(invoke("reset", {"namespace": namespace}), "reset")

    def remember(tenant: str, scope: str, memory_id: str, text: str, created_at: str = "") -> None:
        setup_ok(
            invoke(
                "remember",
                {
                    "namespace": namespace,
                    "tenant": tenant,
                    "scope": scope,
                    "record": {
                        "id": memory_id,
                        "text": text,
                        "created_at": created_at,
                    },
                },
            ),
            "remember",
        )

    def recall(tenant: str, scope: str, query: str) -> dict[str, Any]:
        response = invoke(
            "recall",
            {
                "namespace": namespace,
                "tenant": tenant,
                "scope": scope,
                "query": query,
                "limit": 10,
            },
        )
        setup_ok(response, "recall")
        return _result_payload(response)

    cases: list[dict[str, Any]] = []

    # GOV-ISO-001: content and opaque identifier must not cross tenant boundary.
    claim = _claim_state(manifest, "tenant_isolation")
    if claim == "claimed":
        reset()
        secret_id = "foreign-tenant-secret"
        secret_text = "violet zephyr tenant secret 7349"
        remember("tenant-a", "shared-scope", secret_id, secret_text)
        result = recall("tenant-b", "shared-scope", secret_text)
        id_leak = secret_id in _returned_identifiers(result)
        content_leak = secret_text in _returned_texts(result)
        cases.append(
            _case(
                "GOV-ISO-001",
                "tenant_isolation",
                "fail" if id_leak or content_leak else "pass",
                observations={
                    "identifier_leak": id_leak,
                    "content_leak": content_leak,
                },
            )
        )
    else:
        cases.append(_case("GOV-ISO-001", "tenant_isolation", claim))

    # GOV-ISO-002: same tenant, wrong scope.
    claim = _claim_state(manifest, "scope_isolation")
    if claim == "claimed":
        reset()
        secret_id = "foreign-scope-secret"
        secret_text = "indigo kestrel scope secret 9981"
        remember("tenant-a", "scope-a", secret_id, secret_text)
        result = recall("tenant-a", "scope-b", secret_text)
        id_leak = secret_id in _returned_identifiers(result)
        content_leak = secret_text in _returned_texts(result)
        cases.append(
            _case(
                "GOV-ISO-002",
                "scope_isolation",
                "fail" if id_leak or content_leak else "pass",
                observations={
                    "identifier_leak": id_leak,
                    "content_leak": content_leak,
                },
            )
        )
    else:
        cases.append(_case("GOV-ISO-002", "scope_isolation", claim))

    # GOV-ISO-005: caller-visible result must not disclose foreign cardinality where claimed.
    claim = _claim_state(manifest, "foreign_cardinality_non_disclosure")
    if claim == "claimed":
        public_results = []
        for count in (0, 1, 5):
            reset()
            for index in range(count):
                remember(
                    "tenant-a",
                    "scope-a",
                    f"foreign-count-{index}",
                    f"quartz cardinality beacon {index}",
                )
            public_results.append(recall("tenant-b", "scope-a", "quartz cardinality beacon"))
        canonical = [
            json.dumps(value, sort_keys=True, separators=(",", ":")) for value in public_results
        ]
        stable = len(set(canonical)) == 1
        cases.append(
            _case(
                "GOV-ISO-005",
                "foreign_cardinality_non_disclosure",
                "pass" if stable else "fail",
                observations={
                    "caller_visible_result_stable_across_foreign_counts": stable,
                    "foreign_populations": [0, 1, 5],
                },
            )
        )
    else:
        cases.append(_case("GOV-ISO-005", "foreign_cardinality_non_disclosure", claim))

    # GOV-DEL-001: prove pre-delete retrievability, then require non-resurrection in recall.
    claim = _claim_state(manifest, "deletion")
    forget_support = _support(manifest, "forget")
    if claim == "claimed" and forget_support in _POSITIVE_SUPPORT:
        reset()
        memory_id = "delete-target"
        text = "scarlet deletion target 4120"
        remember("tenant-a", "scope-a", memory_id, text)
        before = recall("tenant-a", "scope-a", text)
        before_present = memory_id in _returned_identifiers(before)
        if not before_present:
            cases.append(
                _case(
                    "GOV-DEL-001",
                    "deletion",
                    "blocked",
                    observations={"pre_delete_retrievable": False},
                    note="deletion cannot be evaluated because setup memory was not retrievable",
                )
            )
        else:
            forget_response = invoke(
                "forget",
                {
                    "namespace": namespace,
                    "tenant": "tenant-a",
                    "scope": "scope-a",
                    "id": memory_id,
                },
            )
            if forget_response["status"] != "ok":
                cases.append(
                    _case(
                        "GOV-DEL-001",
                        "deletion",
                        "fail",
                        observations={"forget_status": forget_response["status"]},
                        note="claimed deletion operation did not complete successfully",
                    )
                )
            else:
                after = recall("tenant-a", "scope-a", text)
                id_leak = memory_id in _returned_identifiers(after)
                content_leak = text in _returned_texts(after)
                cases.append(
                    _case(
                        "GOV-DEL-001",
                        "deletion",
                        "fail" if id_leak or content_leak else "pass",
                        observations={
                            "pre_delete_retrievable": True,
                            "post_delete_identifier_leak": id_leak,
                            "post_delete_content_leak": content_leak,
                        },
                    )
                )
    elif claim == "claimed":
        cases.append(
            _case(
                "GOV-DEL-001",
                "deletion",
                "invalid",
                note="deletion is claimed but forget operation support is not established",
            )
        )
    else:
        cases.append(_case("GOV-DEL-001", "deletion", claim))

    # GOV-DEL-002: do not fake restart evidence. Hold claimed durability until a restart
    # lifecycle contract is bound to the orchestrator.
    claim = _claim_state(manifest, "durable_deletion")
    if claim == "claimed":
        cases.append(
            _case(
                "GOV-DEL-002",
                "durable_deletion",
                "blocked",
                note="restart/recovery lifecycle is not yet bound to the Gauntlet alpha orchestrator",
            )
        )
    else:
        cases.append(_case("GOV-DEL-002", "durable_deletion", claim))

    # GOV-AUTH-002: newer foreign evidence may not launder tenant authority.
    claim = _claim_state(manifest, "tenant_isolation")
    if claim == "claimed":
        reset()
        remember(
            "tenant-b",
            "scope-a",
            "authorized-old",
            "approved contact is cedar desk",
            "2025-01-01T00:00:00Z",
        )
        foreign_id = "forbidden-new"
        foreign_text = "current emergency contact is violet node"
        remember(
            "tenant-a",
            "scope-a",
            foreign_id,
            foreign_text,
            "2026-09-26T00:00:00Z",
        )
        result = recall("tenant-b", "scope-a", foreign_text)
        leaked = foreign_id in _returned_identifiers(result) or foreign_text in _returned_texts(result)
        cases.append(
            _case(
                "GOV-AUTH-002",
                "tenant_isolation",
                "fail" if leaked else "pass",
                observations={"newer_forbidden_memory_influenced_output": leaked},
            )
        )
    else:
        cases.append(_case("GOV-AUTH-002", "tenant_isolation", claim))

    # GOV-AUTH-003: perfect similarity may not launder tenant authority.
    claim = _claim_state(manifest, "tenant_isolation")
    if claim == "claimed":
        reset()
        foreign_id = "forbidden-perfect-match"
        foreign_text = "omega sapphire exact semantic target"
        remember("tenant-a", "scope-a", foreign_id, foreign_text)
        remember("tenant-b", "scope-a", "authorized-related", "omega approved reference")
        result = recall("tenant-b", "scope-a", foreign_text)
        leaked = foreign_id in _returned_identifiers(result) or foreign_text in _returned_texts(result)
        cases.append(
            _case(
                "GOV-AUTH-003",
                "tenant_isolation",
                "fail" if leaked else "pass",
                observations={"perfect_similarity_bypassed_isolation": leaked},
            )
        )
    else:
        cases.append(_case("GOV-AUTH-003", "tenant_isolation", claim))

    # These three claims require additional neutral injection semantics. Report them
    # honestly instead of inventing a pretend test that flatters the harness.
    for case_id, capability, title in CASE_DEFINITIONS[-3:]:
        claim = _claim_state(manifest, capability)
        if claim == "claimed":
            cases.append(
                _case(
                    case_id,
                    capability,
                    "blocked",
                    note=(
                        f"{title} requires a system-neutral evidence-injection contract that is "
                        "not yet part of Governance Gauntlet alpha"
                    ),
                )
            )
        else:
            cases.append(_case(case_id, capability, claim))

    return {
        "profile_kind": "gauntlet_native_gap",
        "suite_family": "agent-memory-gauntlet-governance",
        "spec_version": "0.1.0",
        "fixture_sha256": CASE_FIXTURE_SHA256,
        "sample_count": len(cases),
        "operation_count": operation_count,
        "cases": cases,
        "normalized_dimensions": _dimensions(cases),
        "benchmark_identity": {
            "id": "agent-memory-governance-gauntlet-alpha",
            "source_revision": "0.1.0",
            "dataset_id": "synthetic-governance-cases-v1",
            "dataset_revision": "0.1.0",
            "input_sha256": CASE_FIXTURE_SHA256,
        },
        "selection_id": f"all:{CASE_FIXTURE_SHA256[:16]}",
        "selection_method": "full deterministic claim-driven case registry",
        "normalization_limitations": [
            "Gauntlet-native governance evidence is coverage/falsification evidence, not independent proof of runtime superiority.",
            "Route-count, classifier, and provenance laundering remain blocked when claimed until neutral evidence-injection contracts exist.",
            "Restart-persistent deletion remains blocked when claimed until restart lifecycle orchestration is bound.",
            "No aggregate governance score is emitted.",
        ],
        "authority_effect": "none",
    }


__all__ = [
    "CASE_DEFINITIONS",
    "CASE_FIXTURE_SHA256",
    "strict_governance_adapter",
    "leaky_governance_adapter",
    "count_leak_governance_adapter",
    "run_governance_alpha",
]
