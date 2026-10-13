"""Experimental provider-neutral decision gateway over a governed context package.

#780/#781: provider integration seam; no built-in network transport, no implicit
permission to share memories, and no delegation of memory/policy authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Mapping, Protocol

from .decision_context import DecisionContextPort

GATEWAY_VERSION = "0.1.0"


class DecisionContractError(ValueError):
    """A model, request or context violated a typed decision contract."""


@dataclass(frozen=True)
class DecisionRequest:
    request_ref: str
    question: str
    choices: tuple[str, ...]
    context: dict
    provider_ref: str


@dataclass(frozen=True)
class EgressDecision:
    """Host policy outcome bound to the exact model request and provider."""

    request_ref: str
    provider_ref: str
    permitted: bool
    authorization_ref: str


class EgressAuthorizer(Protocol):
    def authorize(self, request: DecisionRequest) -> EgressDecision: ...


class DecisionProvider(Protocol):
    provider_ref: str
    remote: bool

    def decide(self, request: DecisionRequest) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class DecisionGateway:
    context_port: DecisionContextPort
    provider: DecisionProvider
    egress_authorizer: EgressAuthorizer | None = None

    def decide(
        self,
        question: str,
        *,
        choices: tuple[str, ...],
        purpose: str,
        max_items: int = 8,
        max_chars: int = 4000,
    ) -> dict:
        if not isinstance(question, str) or not question.strip():
            raise DecisionContractError("decision question must be non-empty")
        if not isinstance(choices, tuple) or not (2 <= len(choices) <= 255):
            raise DecisionContractError("choices must be a tuple of 2..255 options")
        if any(not isinstance(c, str) or not c.strip() or len(c) > 256 for c in choices):
            raise DecisionContractError("choices must be non-empty bounded strings")
        if len(set(choices)) != len(choices):
            raise DecisionContractError("choices must be unique")
        if not isinstance(self.provider.provider_ref, str) or not self.provider.provider_ref:
            raise DecisionContractError("provider identity must be explicit")
        if not isinstance(self.provider.remote, bool):
            raise DecisionContractError("provider remote/local posture must be explicit")
        if self.provider.remote and self.egress_authorizer is None:
            # Check BEFORE any recall/resolution, not merely before transport.
            raise DecisionContractError("remote egress requires a host policy authorizer")
        context = self.context_port.assemble(question, purpose=purpose, max_items=max_items, max_chars=max_chars)
        if context.get("kind") != "decision_context" or context.get("authority_effect") != "none":
            raise DecisionContractError("context contract is invalid")
        if context.get("status") == "partial_unresolved":
            return {"gateway_version": GATEWAY_VERSION, "status": "context_unavailable",
                    "authority_effect": "none", "context_status": context["status"], "provider_called": False}
        if context.get("status") not in ("complete", "partial_budget", "no_evidence"):
            raise DecisionContractError("unexpected context status")
        # No-evidence cases are needed for the model-only control. They are *not*
        # a claim that the memory system supplied sufficient evidence.
        if context["status"] != "no_evidence" and not context["evidence"]:
            raise DecisionContractError("non-empty context status without evidence")
        envelope = {"gateway_version": GATEWAY_VERSION, "question": question, "choices": list(choices),
                    "context": context, "provider_ref": self.provider.provider_ref}
        canonical = json.dumps(envelope, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        ref = "sha256:" + sha256(canonical.encode("utf-8")).hexdigest()
        request = DecisionRequest(ref, question, choices, context, self.provider.provider_ref)
        if self.provider.remote:
            decision = self.egress_authorizer.authorize(request)
            if not isinstance(decision, EgressDecision) or not (
                decision.permitted is True
                and decision.request_ref == ref
                and decision.provider_ref == self.provider.provider_ref
                and isinstance(decision.authorization_ref, str)
                and decision.authorization_ref.strip()
            ):
                raise DecisionContractError("host egress authorization refused or mismatched")
        response = self.provider.decide(request)
        if not isinstance(response, Mapping):
            raise DecisionContractError("provider must return a mapping")
        if set(response) - {"request_ref", "status", "choice", "probabilities", "reason"}:
            raise DecisionContractError("provider returned undeclared fields")
        if response.get("request_ref") != ref:
            raise DecisionContractError("response request binding mismatch")
        if response.get("status") == "abstained":
            if response.get("choice") is not None or response.get("probabilities") is not None:
                raise DecisionContractError("abstention must not pretend to choose")
            return {"gateway_version": GATEWAY_VERSION, "status": "abstained",
                    "request_ref": ref, "provider_ref": self.provider.provider_ref,
                    "context_status": context["status"], "authority_effect": "none", "provider_called": True}
        if response.get("status") != "complete":
            raise DecisionContractError("unknown provider decision status")
        winner = response.get("choice")
        if not isinstance(winner, str) or winner not in choices:
            raise DecisionContractError("provider chose an undeclared option")
        probabilities = response.get("probabilities")
        if not isinstance(probabilities, Mapping) or set(probabilities) != set(choices):
            raise DecisionContractError("probability support must equal declared options")
        if any(isinstance(p, bool) or not isinstance(p, (int, float)) or
               not math.isfinite(p) or p < 0.0 or p > 1.0 for p in probabilities.values()):
            raise DecisionContractError("probabilities must be finite within [0,1]")
        if abs(sum(probabilities.values()) - 1.0) > 0.001:
            raise DecisionContractError("probabilities must sum to one")
        if probabilities[winner] < max(probabilities.values()):
            raise DecisionContractError("choice is inconsistent with maximum probability")
        return {"gateway_version": GATEWAY_VERSION, "status": "complete", "choice": winner,
                "probabilities": {k: float(probabilities[k]) for k in choices},
                "request_ref": ref, "provider_ref": self.provider.provider_ref,
                "context_status": context["status"], "authority_effect": "none",
                "provider_called": True, "decision_authority": "external_host"}
