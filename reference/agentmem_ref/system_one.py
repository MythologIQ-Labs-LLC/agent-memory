"""Offline-testable System One provider transport for GLiDE and Jev (#780/#781).

No HTTP client, credentials, retries, or network calls are implemented here.
A trusted host injects transport and egress policy separately. Transport-level
request/response correlation is assumed, not cryptographically attested.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Protocol

from .decision_gateway import DecisionContractError, DecisionRequest

ENDPOINTS = {
    "fastino": "https://api.fastino.ai/v1/systemone",
    "typesafe": "https://api.typesafe.ai/v1/systemone",
}


class SystemOneTransport(Protocol):
    def post_json(self, endpoint: str, body: Mapping[str, object]) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class SystemOneProvider:
    """One trusted transport contract for both System One API providers.

    The caller owns credential handling, TLS, timeout and retries. This module
    cannot authorize egress or read memory; DecisionGateway must enforce those.
    """
    vendor: str
    model: str
    transport: SystemOneTransport
    remote: bool = True

    def __post_init__(self):
        if self.vendor not in ENDPOINTS:
            raise ValueError("unsupported System One vendor")
        if not isinstance(self.model, str) or not self.model or len(self.model) > 128 or any(c.isspace() for c in self.model):
            raise ValueError("a pinned non-empty model identifier is required")
        if self.remote is not True:
            raise ValueError("hosted System One provider must declare remote")

    @property
    def provider_ref(self) -> str:
        return f"systemone:{self.vendor}:{self.model}"

    def decide(self, request: DecisionRequest) -> dict:
        # Only already governed evidence TEXT leaves this boundary. Do not send
        # tenant identifiers, internal fact UUIDs, provenance refs or hashes.
        evidence = request.context.get("evidence", [])
        if not isinstance(evidence, list) or any(not isinstance(v, dict) or not isinstance(v.get("text"), str) for v in evidence):
            raise DecisionContractError("invalid context evidence for System One")
        state = {
            "purpose": request.context["purpose"],
            "context_status": request.context["status"],
            "evidence": [
                {"citation": f"e{idx}", "text": value["text"], "role": "untrusted_evidence"}
                for idx, value in enumerate(evidence, start=1)
            ],
        }
        body = {
            "model": self.model,
            "state": state,
            "questions": {
                "decision": {
                    "type": "choice",
                    "instructions": request.question,
                    "criteria": {label: label for label in request.choices},
                },
            },
        }
        response = self.transport.post_json(ENDPOINTS[self.vendor], body)
        if not isinstance(response, Mapping):
            raise DecisionContractError("System One returned non-object response")
        # Strict model pin: aliases returning a different concrete checkpoint are
        # not silently accepted as equivalent reproducibility evidence.
        if response.get("model") != self.model:
            raise DecisionContractError("System One model identity mismatch")
        answers = response.get("answers")
        if not isinstance(answers, Mapping) or not isinstance(answers.get("decision"), Mapping):
            raise DecisionContractError("System One decision answer is missing")
        answer = answers["decision"]
        if answer.get("type") != "choice":
            raise DecisionContractError("System One returned unsupported answer type")
        return {
            "request_ref": request.request_ref,
            "status": "complete",
            "choice": answer.get("choice"),
            "probabilities": answer.get("probabilities"),
        }
