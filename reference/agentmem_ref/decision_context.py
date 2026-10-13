"""Read-only, provider-neutral decision-context projection (#780, #781).

A decision model does not get access to canonical memory or to policy authority.
This module consumes the *public* governed recall result and resolves only its
returned identifiers via a caller-supplied, authorized evidence reader. The
reader is part of the trusted host, not a decision-model extension.

This is an evaluation-stage consumer port, not an API that exposes canonical
fact text. In particular, the public AgentMemory facade currently returns IDs;
no internal SQLite/substrate read is used to work around that boundary (#691).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Callable, Protocol

CONTRACT_VERSION = "0.1.0"


@dataclass(frozen=True)
class ResolvedEvidence:
    """Host-asserted authorized text binding for exactly one recalled fact UUID.

    The host reader MUST validate current authorization and source binding;
    matching fields here only validate the port's handoff, not external truth.
    """

    fact_ref: str
    text: str
    tenant_ref: str
    scope_ref: str
    provenance_ref: str


class GovernedRecall(Protocol):
    tenant: str
    scope: str

    def recall(self, query: str, *, budget: int, purpose: str) -> dict: ...


EvidenceReader = Callable[[str], ResolvedEvidence | None]


class InvalidContextBinding(ValueError):
    """A recall/reader identity or isolation contract was violated."""


@dataclass(frozen=True)
class DecisionContextPort:
    """Assemble a bounded evidence payload; never invokes a model or mutates memory."""

    memory: GovernedRecall
    reader: EvidenceReader

    def assemble(
        self,
        query: str,
        *,
        purpose: str,
        max_items: int = 8,
        max_chars: int = 4000,
    ) -> dict:
        if not query.strip() or not purpose.strip():
            raise ValueError("query and purpose must be non-empty")
        if isinstance(max_items, bool) or not isinstance(max_items, int) or max_items < 1:
            raise ValueError("max_items must be a positive integer")
        if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
            raise ValueError("max_chars must be a positive integer")
        if not self.memory.tenant or not self.memory.scope:
            raise InvalidContextBinding("host tenant and scope must be bound")

        # Budget is supplied to the existing facade, never a private substrate.
        result = self.memory.recall(query, budget=max_items, purpose=purpose)
        if not isinstance(result, dict) or result.get("stage") != "recall":
            raise InvalidContextBinding("governed public recall did not complete")
        returned, admitted = result.get("returned"), result.get("admitted")
        if not isinstance(returned, list) or not isinstance(admitted, list):
            raise InvalidContextBinding("recall result lacks admitted/returned lists")
        if any(not isinstance(ref, str) or not ref for ref in returned + admitted):
            raise InvalidContextBinding("invalid recall reference")
        if len(returned) != len(set(returned)) or len(admitted) != len(set(admitted)):
            raise InvalidContextBinding("duplicate recall reference")
        if len(returned) > max_items or not set(returned).issubset(admitted):
            raise InvalidContextBinding("returned evidence violates governed recall budget/admission")
        policy = result.get("return_policy")
        if not isinstance(policy, dict) or policy.get("authority_effect") != "none" or policy.get("requested_k") != max_items:
            raise InvalidContextBinding("return budget policy is missing or inconsistent")

        evidence: list[dict] = []
        used_chars = 0
        unresolved = 0
        budget_limited = False
        # Only resolved and admitted facts are eligible; no fallback to an ungoverned search.
        for ref in returned:
            item = self.reader(ref)
            if item is None:
                unresolved += 1
                continue
            if not isinstance(item, ResolvedEvidence):
                raise InvalidContextBinding("reader returned an invalid evidence shape")
            if item.fact_ref != ref or item.tenant_ref != self.memory.tenant or item.scope_ref != self.memory.scope:
                raise InvalidContextBinding("reader returned mismatched fact/tenant/scope")
            if not item.text or not item.provenance_ref:
                raise InvalidContextBinding("reader must provide text and source provenance")
            if len(item.text) > max_chars - used_chars:
                budget_limited = True
                break  # Ranked prefix only. No silent truncation or backfill.
            used_chars += len(item.text)
            evidence.append({
                "fact_ref": ref,
                "text": item.text,
                "provenance_ref": item.provenance_ref,
                "sha256": "sha256:" + hashlib.sha256(item.text.encode("utf-8")).hexdigest(),
                "untrusted_content": True,
            })

        if unresolved:
            status = "partial_unresolved"  # Caller must not interpret as complete.
        elif budget_limited or policy.get("applied"):
            status = "partial_budget"
        elif not evidence:
            status = "no_evidence"
        else:
            status = "complete"
        return {
            "contract_version": CONTRACT_VERSION,
            "kind": "decision_context",
            "status": status,
            "authority_effect": "none",
            "decision_authority": "external_host",
            "tenant_ref": self.memory.tenant,
            "scope_ref": self.memory.scope,
            "purpose": purpose,
            "query": query,
            "evidence": evidence,
            "counts": {
                "admitted": len(admitted),
                "returned": len(returned),
                "resolved": len(evidence),
                "unresolved": unresolved,
                "max_items": max_items,
                "max_chars": max_chars,
                "used_chars": used_chars,
            },
            "limitations": [
                "host_asserted_text_binding_not_independently_verified",
                "char_budget_not_model_token_budget",
                "evidence_text_is_untrusted_data_not_instructions",
                "no_decision_model_was_called",
            ],
        }
