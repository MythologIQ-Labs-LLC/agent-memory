"""Local reference evidence for governed cross-system memory interchange.

This module does not define a transport standard and does not import another
project's authority semantics. It exercises Agent Memory's own Profile 6 seam:

- sender export requires a committed governed boundary crossing;
- the memory's identity, provenance, lifecycle, sensitivity, ownership, and
  source-domain scope survive export;
- sender authority travels as evidence, never as receiver permission;
- the receiver evaluates its own PAMA authority before admitting the import;
- ownership conflicts fail closed;
- successful imports bind a receiving isolation domain while retaining source
  domain provenance.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from . import policy, receipts


@dataclass(frozen=True)
class ExportBundle:
    sender_system: str
    receiver_system: str
    memory: dict
    crossing_receipt: dict
    sender_authority_evidence: tuple[str, ...]


@dataclass(frozen=True)
class ImportResult:
    decision: policy.Decision
    admitted: bool
    memory: dict | None
    refusal: str | None = None


def build_export_bundle(
    memory: dict,
    *,
    sender_system: str,
    receiver_system: str,
    crossing_receipt: dict,
) -> ExportBundle:
    """Build an export only from a schema-valid memory and committed crossing."""
    receipts.validate("memory-unit.schema.json", memory)
    receipts.validate("boundary-crossing-receipt.schema.json", crossing_receipt)

    if crossing_receipt.get("outcome") != "committed":
        raise ValueError("memory export requires a committed governed crossing")
    if memory["id"] not in crossing_receipt.get("source_refs", ()):
        raise ValueError("crossing receipt does not bind the exported memory")

    scope = memory.get("scope") or {}
    if not scope.get("owner_principal"):
        raise ValueError("cross-system export requires an explicit owner_principal")
    if not scope.get("isolation_domain_refs"):
        raise ValueError("cross-system export requires explicit source isolation domains")

    evidence = []
    for key in ("decision_receipt_ref", "ledger_ref"):
        value = crossing_receipt.get(key)
        if value:
            evidence.append(value)
    evidence.append(crossing_receipt["receipt_id"])

    return ExportBundle(
        sender_system=sender_system,
        receiver_system=receiver_system,
        memory=deepcopy(memory),
        crossing_receipt=deepcopy(crossing_receipt),
        sender_authority_evidence=tuple(evidence),
    )


def import_bundle(
    bundle: ExportBundle,
    *,
    receiver_domain_ref: str,
    receiver_proposal: policy.Proposal,
    expected_owner_principal: str | None = None,
) -> ImportResult:
    """Evaluate one import under receiver-local authority.

    The sender's crossing receipt is evidence that the sender authorized an
    export. It is never reused as the receiver's allow decision.
    """
    source = deepcopy(bundle.memory)
    receipts.validate("memory-unit.schema.json", source)

    source_scope = source.get("scope") or {}
    owner = source_scope.get("owner_principal")
    if expected_owner_principal is not None and owner != expected_owner_principal:
        decision = policy.Decision(
            outcome=policy.BLOCK,
            permitted_actions=(),
            prohibited_actions=("scope_expansion",),
            reasons=("cross-system ownership conflict",),
        )
        return ImportResult(decision, False, None, "ownership_conflict")

    if receiver_proposal.target_reference != source["id"]:
        raise ValueError("receiver proposal must bind the imported memory id")
    if receiver_proposal.operation != "scope_expansion":
        decision = policy.Decision(
            outcome=policy.BLOCK,
            permitted_actions=(),
            prohibited_actions=(receiver_proposal.operation, "scope_expansion"),
            reasons=("cross-system import must be evaluated as scope_expansion",),
        )
        return ImportResult(decision, False, None, "receiver_reauthorization_required")

    decision = policy.evaluate(receiver_proposal)
    if decision.outcome not in (policy.ALLOW, policy.ALLOW_WITH_LEDGER):
        return ImportResult(decision, False, None, f"receiver_{decision.outcome}")

    source_domains = tuple(source_scope.get("isolation_domain_refs", ()))
    inherited_sources = tuple(source_scope.get("source_isolation_domain_refs", ()))
    all_sources = list(dict.fromkeys((*source_domains, *inherited_sources)))

    imported = deepcopy(source)
    imported["acquisition_mode"] = "imported"
    imported_scope = deepcopy(source_scope)
    imported_scope["primary_isolation_domain_ref"] = receiver_domain_ref
    imported_scope["isolation_domain_refs"] = [receiver_domain_ref]
    imported_scope["source_isolation_domain_refs"] = all_sources
    imported["scope"] = imported_scope
    imported["authority"] = {
        "pama_outcome": decision.outcome,
        "risk_class": receiver_proposal.risk_class,
        "policy_version": decision.policy_version,
        "authority_refs": list(receiver_proposal.approval_refs),
        "permitted_actions": list(decision.permitted_actions),
        "prohibited_actions": list(decision.prohibited_actions),
        "selection_mode": "deterministic",
    }

    receipts.validate("memory-unit.schema.json", imported)
    return ImportResult(decision, True, imported)
