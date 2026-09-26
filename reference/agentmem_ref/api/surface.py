"""The public surface: PRD-001 R1's stages as functions of an adapter and an envelope.

Sprint 4a (plan LD4-LD6). Every function first evaluates ADR-030 compatibility
and validates the envelope; a stage runs only on ``current``. ``propose`` and
``approve`` write nothing. ``commit`` and ``forget`` forward the caller's
evidence and attestation to the adapter unchanged and otherwise park there
(DoD 20). No function accepts a verifier: the registry is the adapter's own.

Sprint 4c-2 (ADR-038): ``authorize`` binds an executable decision only for terminal
PAMA outcomes with no authority-floor constraint, after its ledger exists; ``witness``
binds the host's observation to that decision and consumes the authorization once.

RC-4 adds ``AgentMemory`` as a convenience facade over these same stages and the
qualified SQLite composition. It is not a second contract or authority surface.
"""

from __future__ import annotations

import functools
import threading

import hashlib
import importlib.resources
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..core import policy
from ..memory import action_authority
from ..runtime import doctor
from ..runtime.adapter import REPLACEMENT_KINDS, GovernedMemoryAdapter
from ..runtime.temporal_intent import declared_temporal, resolve_intent
from . import contract

__all__ = [
    "AgentMemory",
    "propose",
    "approve",
    "commit",
    "recall",
    "forget",
    "history",
    "posture",
    "authorize",
    "witness",
]


def _gate(envelope: Mapping[str, Any], validator, stage: str):
    """(compat, validated envelope or None, early result or None)."""
    compat = contract.compatibility(envelope)
    if compat != contract.CURRENT:
        return compat, None, contract.result("none", compat)
    try:
        validated = validator(envelope)
    except ValueError as exc:
        return compat, None, contract.result("none", compat, validation_error=str(exc))
    return compat, validated, None


def propose(memory: GovernedMemoryAdapter, envelope: Mapping[str, Any]) -> dict:
    """The proposal stage: evaluate, write nothing."""
    compat, validated, early = _gate(envelope, contract.validate_proposal_envelope, "proposal")
    if early is not None:
        return early
    decision = policy.evaluate(contract.proposal_from_envelope(validated))
    return contract.result("proposal", compat, outcome=decision.outcome,
                           decision=contract.decision_projection(decision))


def approve(memory: GovernedMemoryAdapter, envelope: Mapping[str, Any], *,
            evidence: Sequence = (), attestation: policy.ExternalVerification | None = None) -> dict:
    """The approval stage: ADR-037 4a discharge through the adapter's own registry; write nothing."""
    compat, validated, early = _gate(envelope, contract.validate_proposal_envelope, "approval")
    if early is not None:
        return early
    decision = memory.evaluate_proposal(contract.proposal_from_envelope(validated),
                                        evidence=evidence, attestation=attestation)
    return contract.result("approval", compat, outcome=decision.outcome,
                           decision=contract.decision_projection(decision))


def commit(memory: GovernedMemoryAdapter, envelope: Mapping[str, Any], fact_text: str, *,
           evidence: Sequence = (), attestation: policy.ExternalVerification | None = None) -> dict:
    """The commit stage: the adapter decides again and writes, or parks."""
    compat, validated, early = _gate(envelope, contract.validate_proposal_envelope, "commit")
    if early is not None:
        return early
    outcome = memory.commit_proposal(contract.proposal_from_envelope(validated), fact_text,
                                     evidence=list(evidence) or None, attestation=attestation)
    return contract.result("commit", compat, outcome=outcome.decision.outcome,
                           decision=contract.decision_projection(outcome.decision),
                           receipt=outcome.receipt, committed=outcome.committed,
                           fact_uuid=outcome.fact_uuid, refusal=outcome.refusal)


def recall(memory: GovernedMemoryAdapter, query: str, context_envelope: Mapping[str, Any]) -> dict:
    """Retrieval candidates and recall admission, as the adapter records them."""
    compat, validated, early = _gate(context_envelope, contract.validate_recall_context, "recall")
    if early is not None:
        return early
    admission = memory.governed_recall(query, contract.recall_context_from_envelope(validated))
    return contract.result("recall", compat, candidates=list(admission.candidates),
                           admitted=list(admission.admitted), admissions=dict(admission.decisions),
                           candidate_policy=dict(admission.candidate_policy))


def forget(memory: GovernedMemoryAdapter, envelope: Mapping[str, Any], *,
           evidence: Sequence = (), attestation: policy.ExternalVerification | None = None) -> dict:
    """Governed deletion of the target's current fact; the adapter's keyword for the attestation is ``external_verification``."""
    compat, validated, early = _gate(envelope, contract.validate_proposal_envelope, "forget")
    if early is not None:
        return early
    proposal = contract.proposal_from_envelope(validated)
    fact_uuid = memory.current_fact_uuid(proposal.target_reference) or ""
    outcome = memory.governed_delete(proposal, fact_uuid,
                                     evidence=list(evidence) or None, external_verification=attestation)
    return contract.result("forget", compat, outcome=outcome.decision.outcome,
                           decision=contract.decision_projection(outcome.decision),
                           receipt=outcome.receipt, committed=outcome.committed,
                           fact_uuid=outcome.fact_uuid, refusal=outcome.refusal)


def history(memory: GovernedMemoryAdapter, target_envelope: Mapping[str, Any], *, fact_text: str | None = None) -> dict:
    """Inspect history: what the adapter retains for one target. Reads only."""
    compat, validated, early = _gate(target_envelope, contract.validate_target_envelope, "history")
    if early is not None:
        return early
    target = validated["target_reference"]
    record = {
        "current_fact_uuid": memory.current_fact_uuid(target),
        "state_version": memory.state_version(target),
        "tombstoned": target in memory.tombstoned_ids(),
        "events": [event for event in memory.events if event.get("memory_id") == target],
    }
    if fact_text is not None:
        record["rejected_values"] = [dict(item) for item in memory.rejected_value_history(target, fact_text)]
    return contract.result("history", compat, history=record)


def posture(config_path: str | Path, *, qualification_path: str | Path | None = None,
            state_dir: str | Path | None = None) -> dict:
    """Inspect posture: the doctor's report for a configuration, under its schema. Reads only."""
    try:
        report = doctor.diagnose(config_path, qualification_path=qualification_path, state_dir=state_dir)
        contract.validate_posture_report(report)
    except (ValueError, OSError) as exc:
        return contract.result("none", contract.CURRENT, validation_error=f"{type(exc).__name__}: {exc}")
    return contract.result("posture", contract.CURRENT, posture=report)


def authorize(memory: GovernedMemoryAdapter, action_envelope: Mapping[str, Any], *,
              evidence: Sequence = (), attestation: policy.ExternalVerification | None = None) -> dict:
    """The action-authority stage: the adapter decides; a terminal outcome binds, after its ledger; else nothing binds."""
    compat, validated, early = _gate(action_envelope, contract.validate_action_envelope, "action_authority")
    if early is not None:
        return early
    action, proposal = contract.action_from_envelope(validated)
    try:
        authority = action_authority.authorize_action(memory, action, proposal,
                                                      evidence=list(evidence) or None, attestation=attestation)
    except ValueError as exc:
        return contract.result("action_authority", compat, refusal=str(exc))
    return contract.result(
        "action_authority", compat, outcome=authority.decision.outcome,
        decision=contract.decision_projection(authority.decision),
        action_authority={
            "decision_ref": authority.decision_ref,
            "bound": authority.bound,
            "execution_status": None if authority.action is None else authority.action.execution_status,
            "ledger_required": authority.ledger_required,
            "requirement": authority.requirement,
            "composition_id": None if authority.composition is None else authority.composition["composition_id"],
        },
    )


def witness(memory: GovernedMemoryAdapter, observation_envelope: Mapping[str, Any]) -> dict:
    """The execution-evidence stage: the host's observation, bound to the decision the adapter bound; consumes once."""
    compat, validated, early = _gate(observation_envelope, contract.validate_observation_envelope, "execution_evidence")
    if early is not None:
        return early
    try:
        document = action_authority.witness_execution(memory, validated["action_id"], validated)
    except ValueError as exc:
        return contract.result("execution_evidence", compat, refusal=str(exc))
    return contract.result("execution_evidence", compat, witness=document)


_DEFAULT_PROFILE = "rc1-local.json"
_DEFAULT_CONFIG_NAME = "runtime-config.json"
_DATABASE_NAME = "agent-memory.sqlite3"
_BINDING_NAME = "configuration-binding.json"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _content_ref(text: str) -> str:
    return "content:" + _digest(text)


def _packaged_profile_text() -> str:
    resource = importlib.resources.files("agentmem_ref") / "_profiles" / _DEFAULT_PROFILE
    return resource.read_text(encoding="utf-8")


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _serialized(method):
    """Run one public handle operation under the runtime-owned serialization lock (#530)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._serialization_lock:
            return method(self, *args, **kwargs)

    return wrapper


class AgentMemory:
    """Small developer surface over one governed SQLite Agent Memory runtime.

    Thread contract (#530): one handle may be called from any thread. Every public
    operation runs under the runtime-owned serialization lock, so operations never
    interleave and each still commits as one single-writer SQLite generation.
    Objects reached through ``handle.runtime`` are not independently thread-safe;
    direct callers must hold ``handle.runtime.serialization_lock``.

    Defaults are explicit and bounded to low-risk local operation. Higher-risk
    mutation remains subject to the same public proposal contract, evidence
    qualification, and PAMA decisions as direct callers of this module.
    """

    def __init__(
        self,
        *,
        root: Path,
        config_path: Path,
        qualification_path: Path | None,
        tenant: str,
        actor_id: str,
        charter_version: str,
        scope: str,
        purpose: str,
        runtime: Any,
    ) -> None:
        self.root = root
        self.config_path = config_path
        self.qualification_path = qualification_path
        self.tenant = tenant
        self.actor_id = actor_id
        self.charter_version = charter_version
        self.scope = scope
        self.purpose = purpose
        self.runtime = runtime
        self._closed = False
        self._serialization_lock = getattr(runtime, "serialization_lock", None) or threading.RLock()

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        tenant: str = "tenant:local",
        actor_id: str = "agent:local",
        charter_version: str = "charter:local-v1",
        scope: str = "project:local",
        purpose: str = "local memory",
        config_path: str | Path | None = None,
        qualification_path: str | Path | None = None,
        verifier_registry=None,
    ) -> "AgentMemory":
        """Create or recover one qualified local SQLite composition.

        Existing durable state is never replaced by a fresh runtime. A partial
        state marker fails closed so a damaged or incomplete runtime cannot be
        silently reinitialized as empty memory.
        """
        from ..runtime.restart_runtime import RuntimeRecoveryError
        from ..runtime.runtime_behavior import validate_runtime_behavior_contract
        from ..runtime.sqlite_composition import SQLiteConfiguredCompositionRuntime

        root = Path(path)
        root.mkdir(parents=True, exist_ok=True)
        if not tenant or not actor_id or not charter_version or not scope:
            raise ValueError("tenant, actor_id, charter_version, and scope must be non-empty")

        if config_path is None:
            resolved_config = root / _DEFAULT_CONFIG_NAME
            if not resolved_config.exists():
                _atomic_write_text(resolved_config, _packaged_profile_text())
        else:
            resolved_config = Path(config_path)

        resolved_qualification = Path(qualification_path) if qualification_path is not None else None
        value = doctor.load_configuration_value(resolved_config)
        bindings = doctor.load_qualification_bindings(resolved_qualification)
        plan = validate_runtime_behavior_contract(value, qualification_bindings=bindings)

        database = root / _DATABASE_NAME
        binding = root / _BINDING_NAME
        if database.exists():
            runtime = SQLiteConfiguredCompositionRuntime.recover(
                root,
                plan=plan,
                verifier_registry=verifier_registry,
            )
        elif binding.exists():
            raise RuntimeRecoveryError(
                "incomplete durable state: configuration binding exists without SQLite runtime database"
            )
        else:
            runtime = SQLiteConfiguredCompositionRuntime.create(
                root,
                tenant=tenant,
                plan=plan,
                verifier_registry=verifier_registry,
            )

        actual_tenant = runtime.adapter.checkpoint_tenant()
        if actual_tenant != tenant:
            runtime.close()
            raise RuntimeRecoveryError(
                f"requested tenant {tenant!r} does not match recovered runtime tenant {actual_tenant!r}"
            )
        return cls(
            root=root,
            config_path=resolved_config,
            qualification_path=resolved_qualification,
            tenant=tenant,
            actor_id=actor_id,
            charter_version=charter_version,
            scope=scope,
            purpose=purpose,
            runtime=runtime,
        )

    @property
    def contract_version(self) -> str:
        return contract.CONTRACT_VERSION

    @property
    def closed(self) -> bool:
        return self._closed

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("AgentMemory runtime is closed")

    def _domain_refs(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((self.tenant, self.scope)))

    def _proposal(
        self,
        *,
        target_reference: str,
        operation: str,
        fact_text: str = "",
        target_class: str = policy.M2,
        current_strength: str = "observed",
        proposed_strength: str = "reinforced",
        downstream_authority: str = policy.A1,
        reversibility: str = "reversible",
        risk_class: str = "low",
        evidence_refs: Sequence[str] = (),
        confidence: float | None = None,
        purpose: str | None = None,
        overrides: Mapping[str, object] | None = None,
    ) -> dict:
        self._require_open()
        if not target_reference:
            raise ValueError("target_reference must be non-empty")
        state_snapshot = f"v{self.runtime.adapter.state_version(target_reference)}"
        refs = tuple(evidence_refs) or ((_content_ref(fact_text),) if fact_text else (f"state:{state_snapshot}",))
        material = {
            "actor_id": self.actor_id,
            "charter_version": self.charter_version,
            "target_reference": target_reference,
            "operation": operation,
            "state_snapshot": state_snapshot,
            "scope": self.scope,
            "tenant_ref": self.tenant,
            "fact_ref": _content_ref(fact_text) if fact_text else "",
            "risk_class": risk_class,
        }
        envelope: dict[str, object] = {
            "contract_version": contract.CONTRACT_VERSION,
            "proposal_id": "facade:" + hashlib.sha256(_canonical_bytes(material)).hexdigest(),
            "actor_id": self.actor_id,
            "charter_version": self.charter_version,
            "target_reference": target_reference,
            "target_class": target_class,
            "scope": self.scope,
            "operation": operation,
            "current_strength": current_strength,
            "proposed_strength": proposed_strength,
            "downstream_authority": downstream_authority,
            "reversibility": reversibility,
            "risk_class": risk_class,
            "evidence_refs": list(refs),
            "state_snapshot": state_snapshot,
            "tenant_ref": self.tenant,
            "purpose": self.purpose if purpose is None else purpose,
            "isolation_domain_refs": list(self._domain_refs()),
            "required_isolation_domain_refs": list(self._domain_refs()),
            "project_ref": self.scope,
        }
        if confidence is not None:
            envelope["confidence"] = confidence
        if overrides:
            protected = {"contract_version", "proposal_id", "actor_id", "charter_version", "state_snapshot"}
            attempted = protected.intersection(overrides)
            if attempted:
                raise ValueError(f"facade proposal overrides may not replace protected fields: {sorted(attempted)}")
            envelope.update(dict(overrides))
        contract.validate_proposal_envelope(envelope)
        return envelope

    @staticmethod
    def _commit_result(outcome, *, stage: str = "commit") -> dict:
        return contract.result(
            stage,
            contract.CURRENT,
            outcome=outcome.decision.outcome,
            decision=contract.decision_projection(outcome.decision),
            receipt=outcome.receipt,
            committed=outcome.committed,
            fact_uuid=outcome.fact_uuid,
            refusal=outcome.refusal,
        )

    @_serialized
    def remember(
        self,
        target_reference: str,
        fact_text: str,
        *,
        evidence: Sequence = (),
        attestation: policy.ExternalVerification | None = None,
        evidence_refs: Sequence[str] = (),
        confidence: float | None = None,
        target_class: str = policy.M2,
        downstream_authority: str = policy.A1,
        purpose: str | None = None,
        overrides: Mapping[str, object] | None = None,
        valid_from: str | None = None,
        valid_until: str | None = None,
        observed_at: str | None = None,
    ) -> dict:
        """Retain a low-risk observation through ordinary PAMA and durable commit.

        ``valid_from``/``valid_until``/``observed_at`` optionally declare temporal
        evidence (ISO-8601). They are recorded as the caller's claim and used only as
        post-admission applicability evidence (ADR-039, proposed). They never refuse,
        supersede, or change currentness.
        """
        temporal = declared_temporal(
            {"valid_from": valid_from, "valid_until": valid_until, "observed_at": observed_at}
        )
        proposal = contract.proposal_from_envelope(
            self._proposal(
                target_reference=target_reference,
                fact_text=fact_text,
                operation="promotion",
                target_class=target_class,
                downstream_authority=downstream_authority,
                risk_class="low",
                evidence_refs=evidence_refs,
                confidence=confidence,
                purpose=purpose,
                overrides=overrides,
            )
        )
        outcome = self.runtime.retain(
            proposal,
            fact_text,
            evidence=list(evidence) or None,
            attestation=attestation,
            temporal=temporal,
        )
        return self._commit_result(outcome)

    @_serialized
    def correct(
        self,
        target_reference: str,
        fact_text: str,
        *,
        evidence: Sequence = (),
        attestation: policy.ExternalVerification | None = None,
        evidence_refs: Sequence[str] = (),
        risk_class: str = "medium",
        purpose: str | None = None,
        overrides: Mapping[str, object] | None = None,
        valid_from: str | None = None,
        valid_until: str | None = None,
        observed_at: str | None = None,
        replacement_kind: str = "error_correction",
    ) -> dict:
        """Propose/commit a correction. Review requirements are not hidden or auto-satisfied.

        ``replacement_kind`` (#549) records why the current value is replaced:
        ``error_correction`` (default; the prior value was wrong and is never presented as
        historically true) or ``state_change`` (the prior value was true until this
        replacement's ``valid_from``, or the replacement time). The kind rides the same
        governed correction; it grants nothing, and only explicit historical/as-of recall
        may return a state-changed record, labelled as non-current historical evidence.
        """
        temporal = declared_temporal(
            {"valid_from": valid_from, "valid_until": valid_until, "observed_at": observed_at}
        )
        if replacement_kind not in REPLACEMENT_KINDS:
            raise ValueError(f"unknown replacement_kind {replacement_kind!r}")
        current = self.runtime.adapter.current_fact_uuid(target_reference)
        if current is None:
            return contract.result(
                "commit",
                contract.CURRENT,
                committed=False,
                fact_uuid=None,
                refusal="fact_not_found",
            )
        proposal = contract.proposal_from_envelope(
            self._proposal(
                target_reference=target_reference,
                fact_text=fact_text,
                operation="correction",
                current_strength="reinforced",
                proposed_strength="reinforced",
                risk_class=risk_class,
                evidence_refs=evidence_refs,
                purpose=purpose,
                overrides=overrides,
            )
        )
        outcome = self.runtime.correct(
            proposal,
            fact_text,
            evidence=list(evidence) or None,
            attestation=attestation,
            temporal=temporal,
            replacement_kind=replacement_kind,
        )
        return self._commit_result(outcome)

    @_serialized
    def recall(
        self,
        query: str,
        *,
        logical_memory_refs: Sequence[str] = (),
        target_domain_refs: Sequence[str] | None = None,
        principal_ref: str | None = None,
        project_ref: str | None = None,
        task_ref: str | None = None,
        purpose: str | None = None,
        temporal_intent: Mapping[str, Any] | None = None,
        reference_time: str | None = None,
    ) -> dict:
        """Run composed candidate generation followed by one governed admission pass.

        ``temporal_intent`` optionally declares what time the query is about
        (``{"mode": "current"|"as_of"|"historical"|"atemporal_or_unspecified"|
        "prospective", "reference_time", "target_start", "target_end",
        "expected_recall_shape"}``); explicit intent is authoritative. Without it, a
        bounded deterministic interpreter infers intent from generic temporal cues and
        records its confidence; ``reference_time`` anchors current/prospective
        applicability. Intent only orders admitted candidates (ADR-039, proposed).
        """
        self._require_open()
        intent = resolve_intent(query, temporal_intent, reference_time=reference_time)
        domains = tuple(target_domain_refs) if target_domain_refs is not None else self._domain_refs()
        envelope = {
            "contract_version": contract.CONTRACT_VERSION,
            "target_domain_refs": list(domains),
            "principal_ref": self.actor_id if principal_ref is None else principal_ref,
            "project_ref": self.scope if project_ref is None else project_ref,
            "purpose": self.purpose if purpose is None else purpose,
        }
        if task_ref is not None:
            envelope["task_ref"] = task_ref
        validated = contract.validate_recall_context(envelope)
        context = contract.recall_context_from_envelope(validated)
        result = self.runtime.multi_route_recall(
            query,
            context,
            logical_memory_refs=tuple(logical_memory_refs),
            temporal_intent=intent,
        )
        rank = {candidate: index + 1 for index, candidate in enumerate(result.ranked_admitted)}
        admissions: dict[str, dict] = {}
        for candidate in result.candidates:
            decision = dict(result.decisions.get(candidate, {}))
            decision["route_provenance"] = [hit.to_dict() for hit in result.provenance_for(candidate)]
            basis = getattr(result, "admission_basis", {}).get(candidate)
            if basis is not None:
                decision["admission_basis"] = dict(basis)
            if candidate in rank:
                decision["rank_position"] = rank[candidate]
                ranking = getattr(result, "ranking_evidence", {}).get(candidate)
                if ranking is not None:
                    decision["ranking_evidence"] = dict(ranking)
            if candidate in result.refusals:
                decision["refusal"] = result.refusals[candidate]
            admissions[candidate] = decision
        return contract.result(
            "recall",
            contract.CURRENT,
            candidates=list(result.candidates),
            admitted=list(result.ranked_admitted),
            admissions=admissions,
            candidate_policy=dict(getattr(result, "candidate_policy", {}) or {}) or None,
        )

    @_serialized
    def forget(
        self,
        target_reference: str,
        *,
        permanent: bool = False,
        evidence: Sequence = (),
        attestation: policy.ExternalVerification | None = None,
        evidence_refs: Sequence[str] = (),
        risk_class: str | None = None,
        purpose: str | None = None,
        overrides: Mapping[str, object] | None = None,
    ) -> dict:
        """Tombstone by default; permanent deletion remains a stricter explicit request."""
        self._require_open()
        if self.runtime.adapter.current_fact_uuid(target_reference) is None:
            return contract.result(
                "forget",
                contract.CURRENT,
                committed=False,
                fact_uuid=None,
                refusal="fact_not_found",
            )
        operation = "permanent_deletion" if permanent else "pruning"
        proposal = contract.proposal_from_envelope(
            self._proposal(
                target_reference=target_reference,
                operation=operation,
                current_strength="reinforced",
                proposed_strength="not_applicable" if permanent else "archived",
                reversibility="irreversible" if permanent else "reversible",
                risk_class=risk_class or ("high" if permanent else "low"),
                evidence_refs=evidence_refs,
                purpose=purpose,
                overrides=overrides,
            )
        )
        outcome = self.runtime.delete_current(
            proposal,
            evidence=list(evidence) or None,
            external_verification=attestation,
        )
        return self._commit_result(outcome, stage="forget")

    @_serialized
    def history(self, target_reference: str, *, fact_text: str | None = None) -> dict:
        self._require_open()
        return history(
            self.runtime.adapter,
            {"contract_version": contract.CONTRACT_VERSION, "target_reference": target_reference},
            fact_text=fact_text,
        )

    @_serialized
    def posture(self) -> dict:
        """Return the canonical doctor report, including SQLite recovery when present."""
        self._require_open()
        report = doctor.diagnose(
            self.config_path,
            qualification_path=self.qualification_path,
            state_dir=self.root,
        )
        contract.validate_posture_report(report)
        return contract.result("posture", contract.CURRENT, posture=report)

    @_serialized
    def close(self) -> None:
        if self._closed:
            return
        self.runtime.close()
        self._closed = True

    def __enter__(self) -> "AgentMemory":
        self._require_open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
