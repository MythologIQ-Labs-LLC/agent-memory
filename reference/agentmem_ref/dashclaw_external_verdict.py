"""DashClaw external-verdict v1 adapter for governed Agent Memory mutations.

The adapter deliberately keeps four identities/consequences separate:

- DashClaw ``input_identity``: echoed verbatim; never recomputed here.
- Agent Memory proposal identity/digest: internal reconstruction evidence.
- PAMA decision: a decision projection only, never execution evidence.
- governed commit receipt: produced later by ``GovernedMemoryAdapter``.

DashClaw v5.24.0 owns host-side applicability. A correctly configured provider is
scoped to ``agent_memory.mutation`` while ``dashclaw.connection_test`` bypasses
that scope. This module still fails conservatively if called directly with an
unsupported action type.

Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping

from . import policy
from .adapter import GovernedMemoryAdapter

ACTION_MUTATION = "agent_memory.mutation"
ACTION_CONNECTION_TEST = "dashclaw.connection_test"
POLICY_SOURCE = "agent-memory-pama"
EVIDENCE_LIMIT = 4096

_PAMA_TO_DASHCLAW = {
    policy.ALLOW: "allow",
    policy.ALLOW_WITH_LEDGER: "allow",
    policy.REQUIRE_REVIEW: "escalate",
    policy.REQUIRE_EXTERNAL_VERIFICATION: "escalate",
    policy.BLOCK: "deny",
}

_PAMA_REASON = {
    policy.ALLOW: "pama_allow",
    policy.ALLOW_WITH_LEDGER: "pama_allow_with_ledger",
    policy.REQUIRE_REVIEW: "pama_require_review",
    policy.REQUIRE_EXTERNAL_VERIFICATION: "pama_require_external_verification",
    policy.BLOCK: "pama_block",
}

_REQUIRED_REQUEST_STRINGS = (
    "request_id",
    "org_id",
    "agent_id",
    "action_type",
    "declared_goal",
    "input_identity",
)

_REQUIRED_PROPOSAL_STRINGS = (
    "proposal_id",
    "charter_version",
    "target_reference",
    "target_class",
    "scope",
    "operation",
    "current_strength",
    "proposed_strength",
    "downstream_authority",
    "reversibility",
    "risk_class",
    "state_snapshot",
    "purpose",
    "content_sha256",
)

_FORBIDDEN_PROPOSAL_FIELDS = {
    "actor_id",
    "tenant_ref",
    "approval_refs",
    "review_satisfied",
}


class DashClawRequestError(ValueError):
    """The wire request cannot be evaluated safely or echoed correctly."""


class MutationEnvelopeError(ValueError):
    """A contract-valid DashClaw request contains an unsafe mutation envelope."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class BoundMutation:
    """Exact mutation content and reconstructed PAMA proposal for one request."""

    request_id: str
    input_identity: str
    org_id: str
    agent_id: str
    fact_text: str
    content_sha256: str
    proposal: policy.Proposal
    proposal_digest: str


@dataclass
class BoundCommitResult:
    """Result of the Agent Memory commit seam after DashClaw decision/approval."""

    committed: bool
    refusal: str | None
    input_identity: str
    proposal_digest: str
    adapter_result: Any | None = None
    approval_ref: str | None = None


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_string(payload: Mapping[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise DashClawRequestError(f"{name} must be a non-empty string")
    return value


def _tuple_of_strings(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if value is None:
        if required:
            raise MutationEnvelopeError("malformed_mutation_envelope", f"{name} is required")
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise MutationEnvelopeError("malformed_mutation_envelope", f"{name} must be a list of non-empty strings")
    if required and not value:
        raise MutationEnvelopeError("malformed_mutation_envelope", f"{name} must not be empty")
    return tuple(value)


def _trusted_domains(org_id: str, refs: tuple[str, ...], *, name: str) -> tuple[str, ...]:
    org_ref = f"org:{org_id}"
    for ref in refs:
        if ref.startswith("org:") and ref != org_ref:
            raise MutationEnvelopeError(
                "conflicting_trusted_binding",
                f"{name} contains an org domain that conflicts with DashClaw org_id",
            )
    return tuple(dict.fromkeys((org_ref,) + refs))


def _proposal_digest(proposal: policy.Proposal, content_sha256: str) -> str:
    material = {"proposal": asdict(proposal), "content_sha256": content_sha256}
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _validate_wire_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping):
        raise DashClawRequestError("request must be a JSON object")
    for field in _REQUIRED_REQUEST_STRINGS:
        _require_string(request, field)


def parse_mutation_request(request: Mapping[str, Any]) -> BoundMutation:
    """Reconstruct a PAMA proposal without importing act-supplied authority.

    ``org_id`` and ``agent_id`` are the trusted tenant/actor bindings. The act
    is not allowed to inject replacements, review satisfaction, or approval
    references. Human approval arrives later as separate DashClaw evidence.
    """

    _validate_wire_request(request)
    if request["action_type"] != ACTION_MUTATION:
        raise MutationEnvelopeError("unsupported_action_type", "request is not an Agent Memory mutation")

    act = request.get("act")
    if not isinstance(act, Mapping) or act.get("kind") != ACTION_MUTATION:
        raise MutationEnvelopeError("malformed_mutation_envelope", "act.kind must be agent_memory.mutation")

    fact_text = act.get("memory_value")
    if not isinstance(fact_text, str) or not fact_text:
        raise MutationEnvelopeError("malformed_mutation_envelope", "act.memory_value must be a non-empty string")

    raw = act.get("proposal")
    if not isinstance(raw, Mapping):
        raise MutationEnvelopeError("malformed_mutation_envelope", "act.proposal must be an object")

    forbidden = sorted(_FORBIDDEN_PROPOSAL_FIELDS.intersection(raw))
    if forbidden:
        raise MutationEnvelopeError(
            "authority_injection_attempt",
            "mutation proposal may not supply trusted actor/tenant or approval state",
        )

    values: dict[str, str] = {}
    for name in _REQUIRED_PROPOSAL_STRINGS:
        value = raw.get(name)
        if not isinstance(value, str) or not value:
            raise MutationEnvelopeError("malformed_mutation_envelope", f"proposal.{name} must be a non-empty string")
        values[name] = value

    actual_content_sha256 = sha256_text(fact_text)
    if values["content_sha256"] != actual_content_sha256:
        raise MutationEnvelopeError(
            "content_binding_mismatch",
            "proposal.content_sha256 does not bind the exact memory_value",
        )

    evidence_refs = _tuple_of_strings(raw.get("evidence_refs"), "proposal.evidence_refs", required=True)
    estimator_refs = _tuple_of_strings(raw.get("estimator_refs"), "proposal.estimator_refs")
    estimator_versions = _tuple_of_strings(raw.get("estimator_versions"), "proposal.estimator_versions")
    isolation_refs = _trusted_domains(
        request["org_id"],
        _tuple_of_strings(raw.get("isolation_domain_refs"), "proposal.isolation_domain_refs", required=True),
        name="proposal.isolation_domain_refs",
    )
    required_isolation_refs = _trusted_domains(
        request["org_id"],
        _tuple_of_strings(
            raw.get("required_isolation_domain_refs"),
            "proposal.required_isolation_domain_refs",
            required=True,
        ),
        name="proposal.required_isolation_domain_refs",
    )

    project_ref = raw.get("project_ref", "")
    task_ref = raw.get("task_ref", "")
    requested_scope_change = raw.get("requested_scope_change", "")
    for field_name, field_value in (
        ("project_ref", project_ref),
        ("task_ref", task_ref),
        ("requested_scope_change", requested_scope_change),
    ):
        if not isinstance(field_value, str):
            raise MutationEnvelopeError("malformed_mutation_envelope", f"proposal.{field_name} must be a string")

    if project_ref:
        if project_ref not in isolation_refs or project_ref not in required_isolation_refs:
            raise MutationEnvelopeError(
                "project_isolation_not_bound",
                "project_ref must be both a bound and required isolation domain",
            )

    confidence = raw.get("confidence")
    if confidence is not None and (isinstance(confidence, bool) or not isinstance(confidence, (int, float))):
        raise MutationEnvelopeError("malformed_mutation_envelope", "proposal.confidence must be numeric when present")

    proposal = policy.Proposal(
        proposal_id=values["proposal_id"],
        actor_id=request["agent_id"],
        charter_version=values["charter_version"],
        target_reference=values["target_reference"],
        target_class=values["target_class"],
        scope=values["scope"],
        operation=values["operation"],
        current_strength=values["current_strength"],
        proposed_strength=values["proposed_strength"],
        downstream_authority=values["downstream_authority"],
        reversibility=values["reversibility"],
        risk_class=values["risk_class"],
        evidence_refs=evidence_refs,
        estimator_refs=estimator_refs,
        estimator_versions=estimator_versions,
        confidence=float(confidence) if confidence is not None else None,
        actor_authority_resolved=True,
        approves_own_authority=False,
        approval_refs=(),
        review_satisfied=False,
        requested_scope_change=requested_scope_change,
        state_snapshot=values["state_snapshot"],
        tenant_ref=request["org_id"],
        purpose=values["purpose"],
        isolation_domain_refs=isolation_refs,
        required_isolation_domain_refs=required_isolation_refs,
        project_ref=project_ref,
        task_ref=task_ref,
    )

    return BoundMutation(
        request_id=request["request_id"],
        input_identity=request["input_identity"],
        org_id=request["org_id"],
        agent_id=request["agent_id"],
        fact_text=fact_text,
        content_sha256=actual_content_sha256,
        proposal=proposal,
        proposal_digest=_proposal_digest(proposal, actual_content_sha256),
    )


def _bounded_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(evidence, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if len(encoded) <= EVIDENCE_LIMIT:
        return evidence
    return {
        "truncated": True,
        "proposal_id": evidence.get("proposal_id", ""),
        "proposal_digest": evidence.get("proposal_digest", ""),
        "pama_outcome": evidence.get("pama_outcome", ""),
    }


def _response(*, request: Mapping[str, Any], decision: str, reason: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": decision,
        "reason": reason,
        "policy_source": POLICY_SOURCE,
        "policy_version": policy.POLICY_VERSION,
        "input_identity": request["input_identity"],
        "evidence": _bounded_evidence(evidence),
    }


def evaluate_request(request: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate one DashClaw v1 provider request with no mutation side effects."""

    _validate_wire_request(request)

    if request["action_type"] == ACTION_CONNECTION_TEST:
        act = request.get("act")
        if not isinstance(act, Mapping) or act.get("synthetic") is not True:
            return _response(
                request=request,
                decision="deny",
                reason="malformed_connection_test",
                evidence={"connection_test": True, "accepted": False},
            )
        return _response(
            request=request,
            decision="allow",
            reason="connection_test_ok",
            evidence={"connection_test": True, "accepted": True},
        )

    if request["action_type"] != ACTION_MUTATION:
        return _response(
            request=request,
            decision="deny",
            reason="unsupported_action_type",
            evidence={"action_type": request["action_type"]},
        )

    try:
        mutation = parse_mutation_request(request)
    except MutationEnvelopeError as exc:
        return _response(
            request=request,
            decision="deny",
            reason=exc.code,
            evidence={"mutation_envelope_valid": False},
        )

    decision = policy.evaluate(mutation.proposal)
    evidence = {
        "mutation_envelope_valid": True,
        "proposal_id": mutation.proposal.proposal_id,
        "proposal_digest": mutation.proposal_digest,
        "content_sha256": mutation.content_sha256,
        "target_reference": mutation.proposal.target_reference,
        "state_snapshot": mutation.proposal.state_snapshot,
        "pama_outcome": decision.outcome,
        "pama_policy_version": decision.policy_version,
        "execution_evidence": False,
    }
    return _response(
        request=request,
        decision=_PAMA_TO_DASHCLAW[decision.outcome],
        reason=_PAMA_REASON[decision.outcome],
        evidence=evidence,
    )


def commit_bound_mutation(
    memory: GovernedMemoryAdapter,
    mutation: BoundMutation,
    *,
    approval_ref: str | None = None,
    approval_actor_id: str | None = None,
    approved_input_identity: str | None = None,
) -> BoundCommitResult:
    """Commit through the ordinary governed path after independent revalidation.

    A DashClaw approval never becomes standing authority. When PAMA requires
    review, the commit seam requires a distinct approval record bound to the
    exact DashClaw ``input_identity`` and refuses self-approval before the
    governed adapter is called. The governed adapter then re-evaluates PAMA and
    current state again, including stale ``state_snapshot`` rejection.
    """

    predecision = policy.evaluate(mutation.proposal)
    if predecision.outcome == policy.BLOCK:
        return BoundCommitResult(
            committed=False,
            refusal="pama_blocked",
            input_identity=mutation.input_identity,
            proposal_digest=mutation.proposal_digest,
        )

    proposal = mutation.proposal
    if predecision.outcome in (policy.REQUIRE_REVIEW, policy.REQUIRE_EXTERNAL_VERIFICATION):
        if not approval_ref or not approval_actor_id or not approved_input_identity:
            return BoundCommitResult(
                committed=False,
                refusal="approval_required",
                input_identity=mutation.input_identity,
                proposal_digest=mutation.proposal_digest,
            )
        if approved_input_identity != mutation.input_identity:
            return BoundCommitResult(
                committed=False,
                refusal="approval_identity_mismatch",
                input_identity=mutation.input_identity,
                proposal_digest=mutation.proposal_digest,
                approval_ref=approval_ref,
            )
        if approval_actor_id == mutation.agent_id:
            return BoundCommitResult(
                committed=False,
                refusal="self_approval_forbidden",
                input_identity=mutation.input_identity,
                proposal_digest=mutation.proposal_digest,
                approval_ref=approval_ref,
            )
        proposal = replace(
            proposal,
            review_satisfied=True,
            approval_refs=(approval_ref,),
            approves_own_authority=False,
        )

    result = memory.commit_proposal(proposal, mutation.fact_text)
    return BoundCommitResult(
        committed=result.committed,
        refusal=result.refusal,
        input_identity=mutation.input_identity,
        proposal_digest=mutation.proposal_digest,
        adapter_result=result,
        approval_ref=approval_ref,
    )
