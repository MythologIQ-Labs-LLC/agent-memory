"""Ergonomic RC1 developer facade over the canonical Agent Memory contract.

This module is intentionally small. It translates ordinary local developer
operations into the existing public 1.2.0 contract and the qualified SQLite
composition. It does not define a second policy model and it never turns
retrieval relevance, confidence, or convenience defaults into authority.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
import os
from pathlib import Path
from typing import Mapping, Sequence

from .api import contract, surface
from .core import policy
from .runtime.doctor import diagnose, load_configuration_value, load_qualification_bindings
from .runtime.restart_runtime import RuntimeRecoveryError
from .runtime.runtime_behavior import validate_runtime_behavior_contract
from .runtime.sqlite_composition import SQLiteConfiguredCompositionRuntime


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


class AgentMemory:
    """Small developer surface over one governed SQLite Agent Memory runtime.

    Defaults are explicit and bounded to low-risk local operation. Higher-risk
    mutation remains subject to the same public proposal contract, evidence
    qualification, and PAMA decisions as direct callers of ``agentmem_ref.surface``.
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
        runtime: SQLiteConfiguredCompositionRuntime,
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
        value = load_configuration_value(resolved_config)
        bindings = load_qualification_bindings(resolved_qualification)
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
    ) -> dict:
        """Retain a low-risk observation through ordinary PAMA and durable commit."""
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
        )
        return self._commit_result(outcome)

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
    ) -> dict:
        """Propose/commit a correction. Review requirements are not hidden or auto-satisfied."""
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
        )
        return self._commit_result(outcome)

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
    ) -> dict:
        """Run composed candidate generation followed by one governed admission pass."""
        self._require_open()
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
        )
        rank = {candidate: index + 1 for index, candidate in enumerate(result.ranked_admitted)}
        admissions: dict[str, dict] = {}
        for candidate in result.candidates:
            decision = dict(result.decisions.get(candidate, {}))
            decision["route_provenance"] = [hit.to_dict() for hit in result.provenance_for(candidate)]
            if candidate in rank:
                decision["rank_position"] = rank[candidate]
            if candidate in result.refusals:
                decision["refusal"] = result.refusals[candidate]
            admissions[candidate] = decision
        return contract.result(
            "recall",
            contract.CURRENT,
            candidates=list(result.candidates),
            admitted=list(result.ranked_admitted),
            admissions=admissions,
        )

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

    def history(self, target_reference: str, *, fact_text: str | None = None) -> dict:
        self._require_open()
        return surface.history(
            self.runtime.adapter,
            {"contract_version": contract.CONTRACT_VERSION, "target_reference": target_reference},
            fact_text=fact_text,
        )

    def posture(self) -> dict:
        """Return the canonical doctor report, including SQLite recovery when present."""
        self._require_open()
        report = diagnose(
            self.config_path,
            qualification_path=self.qualification_path,
            state_dir=self.root,
        )
        contract.validate_posture_report(report)
        return contract.result("posture", contract.CURRENT, posture=report)

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


__all__ = ["AgentMemory"]
