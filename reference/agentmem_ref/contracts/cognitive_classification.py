"""Governed cognitive-classification provider contract.

This module implements the provider-neutral seam tracked by #490/#500. It
reuses the existing component/capability registry for provider selection rather
than creating a second registry.

The central rule is deliberately boring and important::

    classifier output != authority

A provider may emit an observation or recommendation. Exact metadata, scope,
currentness, recall admission, lifecycle policy, and PAMA remain outside the
provider's authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Callable, Mapping, Protocol, Sequence

from .capabilities import (
    CapabilityBehaviorContract,
    CapabilityDeclaration,
    CapabilityRequirement,
    CapabilityResolutionError,
    ComponentDeclaration,
    ComponentRegistry,
)

CAPABILITY_ID = "cognitive_classification"
CAPABILITY_VERSION = "1.0.0"
PROVIDER_CLASSES = frozenset({"deterministic", "ordinary_llm", "specialized_model", "external"})
RAW_STATUSES = frozenset({"ok", "abstained", "unavailable", "malformed"})
RESULT_STATUSES = frozenset({"ok", "abstained", "unavailable", "malformed", "refused"})


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: object) -> str:
    return sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _finite_nonnegative(value: float, name: str) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class ClassificationChoice:
    label: str
    score: float = 0.0
    probability: float | None = None

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("classification choice label is required")
        if not math.isfinite(self.score):
            raise ValueError("classification choice score must be finite")
        if self.probability is not None:
            if not math.isfinite(self.probability) or not 0.0 <= self.probability <= 1.0:
                raise ValueError("classification probability must be in [0, 1]")

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "score": self.score,
            "probability": self.probability,
        }


@dataclass(frozen=True)
class ClassificationRequest:
    request_id: str
    task: str
    input_data: Mapping[str, object]
    output_labels: tuple[str, ...]
    scope: str
    purpose: str
    tenant: str = ""
    candidate_scope: str = ""
    source_current: bool = True
    exact_label: str = ""
    evidence_refs: tuple[str, ...] = ()
    policy_context_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.request_id or not self.task:
            raise ValueError("classification request_id and task are required")
        if not self.scope or not self.purpose:
            raise ValueError("classification scope and purpose are required")
        if not self.output_labels:
            raise ValueError("classification output_labels must not be empty")
        if len(set(self.output_labels)) != len(self.output_labels):
            raise ValueError("classification output_labels must be unique")
        if any(not label for label in self.output_labels):
            raise ValueError("classification output_labels must be non-empty")
        if self.exact_label and self.exact_label not in self.output_labels:
            raise ValueError("exact_label must be one of output_labels")

    @property
    def input_digest(self) -> str:
        return _digest(
            {
                "request_id": self.request_id,
                "task": self.task,
                "input_data": self.input_data,
                "output_labels": self.output_labels,
                "scope": self.scope,
                "purpose": self.purpose,
                "tenant": self.tenant,
                "candidate_scope": self.candidate_scope,
                "source_current": self.source_current,
                "exact_label": self.exact_label,
                "evidence_refs": self.evidence_refs,
                "policy_context_refs": self.policy_context_refs,
            }
        )


@dataclass(frozen=True)
class ProviderMetadata:
    provider_id: str
    provider_version: str
    provider_class: str
    model_runtime_ref: str
    configuration_ref: str
    local_offline: bool
    data_egress: bool

    def __post_init__(self) -> None:
        if not self.provider_id or not self.provider_version:
            raise ValueError("provider identity and version are required")
        if self.provider_class not in PROVIDER_CLASSES:
            raise ValueError(f"unknown provider_class: {self.provider_class}")
        if not self.model_runtime_ref or not self.configuration_ref:
            raise ValueError("provider model/runtime and configuration refs are required")

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "provider_class": self.provider_class,
            "model_runtime_ref": self.model_runtime_ref,
            "configuration_ref": self.configuration_ref,
            "local_offline": self.local_offline,
            "data_egress": self.data_egress,
        }


@dataclass(frozen=True)
class RawClassification:
    status: str
    choices: tuple[ClassificationChoice, ...] = ()
    reason: str = ""
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    trace_ref: str = ""

    def __post_init__(self) -> None:
        if self.status not in RAW_STATUSES:
            raise ValueError(f"unknown raw classification status: {self.status}")
        _finite_nonnegative(self.latency_ms, "latency_ms")
        _finite_nonnegative(self.cost_usd, "cost_usd")


class ClassificationProvider(Protocol):
    metadata: ProviderMetadata

    def classify(self, request: ClassificationRequest) -> RawClassification:
        """Return provider evidence only, never an authorized consequence."""


@dataclass(frozen=True)
class ClassificationResult:
    request_id: str
    task: str
    status: str
    provider: ProviderMetadata
    input_digest: str
    choices: tuple[ClassificationChoice, ...]
    provider_label: str
    effective_label: str
    exact_metadata_override: bool
    consequence_eligible: bool
    gate_reasons: tuple[str, ...]
    reason: str
    evidence_refs: tuple[str, ...]
    latency_ms: float
    cost_usd: float
    trace_ref: str
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.status not in RESULT_STATUSES:
            raise ValueError(f"unknown classification result status: {self.status}")
        if self.authority_effect != "none":
            raise ValueError("classification result authority_effect must remain none")
        _finite_nonnegative(self.latency_ms, "latency_ms")
        _finite_nonnegative(self.cost_usd, "cost_usd")

    @property
    def result_digest(self) -> str:
        return _digest(self.to_dict(include_digest=False))

    def to_dict(self, *, include_digest: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "request_id": self.request_id,
            "task": self.task,
            "status": self.status,
            "provider": self.provider.to_dict(),
            "input_digest": self.input_digest,
            "choices": [choice.to_dict() for choice in self.choices],
            "provider_label": self.provider_label,
            "effective_label": self.effective_label,
            "exact_metadata_override": self.exact_metadata_override,
            "consequence_eligible": self.consequence_eligible,
            "gate_reasons": list(self.gate_reasons),
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "trace_ref": self.trace_ref,
            "authority_effect": self.authority_effect,
        }
        if include_digest:
            payload["result_digest"] = self.result_digest
        return payload


@dataclass(frozen=True)
class ClassificationComparison:
    request_id: str
    results: tuple[ClassificationResult, ...]
    disagreement: bool
    labels_by_provider: Mapping[str, str]
    authority_effect: str = "none"

    def __post_init__(self) -> None:
        if self.authority_effect != "none":
            raise ValueError("classification comparison authority_effect must remain none")

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "results": [result.to_dict() for result in self.results],
            "disagreement": self.disagreement,
            "labels_by_provider": dict(sorted(self.labels_by_provider.items())),
            "aggregation": "none",
            "authority_effect": self.authority_effect,
        }


@dataclass(frozen=True)
class FallbackClassification:
    selected: ClassificationResult
    attempts: tuple[ClassificationResult, ...]
    fallback_used: bool
    fallback_on_abstention: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "selected": self.selected.to_dict(),
            "attempts": [attempt.to_dict() for attempt in self.attempts],
            "fallback_used": self.fallback_used,
            "fallback_on_abstention": self.fallback_on_abstention,
            "authority_effect": "none",
        }


@dataclass
class DeterministicRuleProvider:
    metadata: ProviderMetadata
    rule: Callable[[ClassificationRequest], RawClassification]

    def __post_init__(self) -> None:
        if self.metadata.provider_class != "deterministic":
            raise ValueError("DeterministicRuleProvider requires provider_class=deterministic")

    def classify(self, request: ClassificationRequest) -> RawClassification:
        return self.rule(request)


@dataclass
class ReplayClassificationProvider:
    """Credential-free replay/simulation provider for conformance evaluation.

    Replay records let ordinary-LLM and specialized-model classes exercise the
    same contract without pretending to be live provider measurements.
    """

    metadata: ProviderMetadata
    records: Mapping[str, RawClassification]

    def __post_init__(self) -> None:
        if self.metadata.provider_class not in {"ordinary_llm", "specialized_model", "external"}:
            raise ValueError("replay provider must model a non-deterministic provider class")

    def classify(self, request: ClassificationRequest) -> RawClassification:
        record = self.records.get(request.request_id)
        if record is None:
            return RawClassification(
                status="unavailable",
                reason="no frozen replay record for request",
                trace_ref=f"replay:{self.metadata.provider_id}:{request.request_id}:missing",
            )
        return record


def classification_component(
    metadata: ProviderMetadata,
    *,
    maturity: str = "implemented",
    evidence_refs: Sequence[str] = (),
) -> ComponentDeclaration:
    """Declare one classifier through the existing component/capability contract."""

    capability = CapabilityDeclaration(
        capability_id=CAPABILITY_ID,
        capability_version=CAPABILITY_VERSION,
        maturity=maturity,
        state_posture="derived_observation",
        scope_posture="request_scoped",
        failure_posture="fail_closed_or_abstain",
        authority_effect="none",
        evidence_refs=tuple(evidence_refs),
        limitations=(
            "classification output is evidence only",
            "provider cannot create recall admission or durable mutation authority",
        ),
        behavior_contract=CapabilityBehaviorContract(
            write=False,
            read=True,
            recall_candidate=False,
            currentness_model="provider_revalidated",
            invalidation_model="provider_revalidation",
            correction_model="provider_revalidation",
            deletion_model="not_applicable",
            residue_model="none_expected",
            migration_rebuild_model="requires_requalification",
            structural_mutation_requirement="proposal_only",
        ),
    )
    return ComponentDeclaration(
        component_id=metadata.provider_id,
        component_version=metadata.provider_version,
        profile_version="component-capability-v2",
        failure_posture="explicit_unavailable_or_abstain",
        runtime_ref=metadata.model_runtime_ref,
        provenance_refs=(metadata.configuration_ref,),
        capabilities=(capability,),
    )


@dataclass
class CognitiveClassificationRuntime:
    """Resolve classifier capabilities and normalize provider evidence.

    ``provider_bindings`` is an executable binding table, not a capability
    registry. Eligibility is always resolved through ``ComponentRegistry``.
    """

    registry: ComponentRegistry
    provider_bindings: Mapping[str, ClassificationProvider]
    minimum_maturity: str = "implemented"

    def _provider(self, component_id: str) -> tuple[ProviderMetadata, ClassificationProvider | None, str]:
        try:
            resolved = self.registry.resolve(
                CapabilityRequirement(
                    capability_id=CAPABILITY_ID,
                    capability_version=CAPABILITY_VERSION,
                    minimum_maturity=self.minimum_maturity,
                    preferred_component=component_id,
                    required_state_postures=("derived_observation",),
                    required_scope_postures=("request_scoped",),
                )
            )
        except CapabilityResolutionError as exc:
            metadata = ProviderMetadata(
                provider_id=component_id,
                provider_version="unresolved",
                provider_class="external",
                model_runtime_ref="unresolved",
                configuration_ref="unresolved",
                local_offline=False,
                data_egress=False,
            )
            return metadata, None, str(exc)

        provider = self.provider_bindings.get(resolved.component_id)
        if provider is None:
            metadata = ProviderMetadata(
                provider_id=resolved.component_id,
                provider_version=resolved.component_version,
                provider_class="external",
                model_runtime_ref="unbound",
                configuration_ref="unbound",
                local_offline=False,
                data_egress=False,
            )
            return metadata, None, "eligible capability has no executable provider binding"

        metadata = provider.metadata
        if metadata.provider_id != resolved.component_id or metadata.provider_version != resolved.component_version:
            return metadata, None, "provider binding identity/version does not match resolved component"
        return metadata, provider, ""

    def classify(self, request: ClassificationRequest, component_id: str) -> ClassificationResult:
        metadata, provider, resolution_error = self._provider(component_id)
        if provider is None:
            return self._result_from_raw(
                request,
                metadata,
                RawClassification(status="unavailable", reason=resolution_error),
            )

        try:
            raw = provider.classify(request)
        except Exception as exc:
            raw = RawClassification(
                status="unavailable",
                reason=f"provider raised {type(exc).__name__}",
                trace_ref=f"provider-exception:{metadata.provider_id}",
            )
        return self._result_from_raw(request, metadata, raw)

    def _result_from_raw(
        self,
        request: ClassificationRequest,
        metadata: ProviderMetadata,
        raw: RawClassification,
    ) -> ClassificationResult:
        status = raw.status
        choices = raw.choices
        reason = raw.reason

        if status == "ok":
            malformed_reason = self._malformed_reason(request, choices)
            if malformed_reason:
                status = "malformed"
                choices = ()
                reason = malformed_reason
        elif choices:
            status = "malformed"
            choices = ()
            reason = "non-ok provider status must not carry choices"

        provider_label = choices[0].label if choices else ""
        effective_label = provider_label
        override = False
        gate_reasons: list[str] = []

        if request.exact_label:
            effective_label = request.exact_label
            if provider_label and provider_label != request.exact_label:
                override = True
                gate_reasons.append("provider_conflicts_exact_metadata")

        if request.candidate_scope and request.candidate_scope != request.scope:
            gate_reasons.append("cross_scope_input")
        if not request.source_current:
            gate_reasons.append("stale_source_evidence")
        if status != "ok":
            gate_reasons.append(f"provider_{status}")

        consequence_eligible = status == "ok" and not any(
            reason_name in {"cross_scope_input", "stale_source_evidence"}
            for reason_name in gate_reasons
        )
        result_status = status
        if status == "ok" and not consequence_eligible:
            result_status = "refused"

        return ClassificationResult(
            request_id=request.request_id,
            task=request.task,
            status=result_status,
            provider=metadata,
            input_digest=request.input_digest,
            choices=choices,
            provider_label=provider_label,
            effective_label=effective_label,
            exact_metadata_override=override,
            consequence_eligible=consequence_eligible,
            gate_reasons=tuple(gate_reasons),
            reason=reason,
            evidence_refs=request.evidence_refs,
            latency_ms=raw.latency_ms,
            cost_usd=raw.cost_usd,
            trace_ref=raw.trace_ref,
        )

    @staticmethod
    def _malformed_reason(
        request: ClassificationRequest,
        choices: tuple[ClassificationChoice, ...],
    ) -> str:
        if not choices:
            return "ok provider result requires at least one choice"
        labels = [choice.label for choice in choices]
        if len(set(labels)) != len(labels):
            return "provider returned duplicate labels"
        unknown = sorted(set(labels).difference(request.output_labels))
        if unknown:
            return f"provider returned out-of-contract labels: {unknown}"
        return ""

    def compare(
        self,
        request: ClassificationRequest,
        component_ids: Sequence[str],
    ) -> ClassificationComparison:
        results = tuple(self.classify(request, component_id) for component_id in component_ids)
        labels_by_provider = {
            result.provider.provider_id: result.effective_label
            for result in results
            if result.status == "ok" and result.effective_label
        }
        disagreement = len(set(labels_by_provider.values())) > 1
        return ClassificationComparison(
            request_id=request.request_id,
            results=results,
            disagreement=disagreement,
            labels_by_provider=labels_by_provider,
        )

    def classify_with_fallback(
        self,
        request: ClassificationRequest,
        primary_component: str,
        fallback_components: Sequence[str],
        *,
        fallback_on_abstention: bool = False,
    ) -> FallbackClassification:
        attempts: list[ClassificationResult] = []
        for index, component_id in enumerate((primary_component, *fallback_components)):
            result = self.classify(request, component_id)
            attempts.append(result)
            terminal = result.status in {"ok", "refused"}
            if result.status == "abstained" and not fallback_on_abstention:
                terminal = True
            if terminal:
                return FallbackClassification(
                    selected=result,
                    attempts=tuple(attempts),
                    fallback_used=index > 0,
                    fallback_on_abstention=fallback_on_abstention,
                )

        return FallbackClassification(
            selected=attempts[-1],
            attempts=tuple(attempts),
            fallback_used=len(attempts) > 1,
            fallback_on_abstention=fallback_on_abstention,
        )


def semantic_result_fingerprint(result: ClassificationResult) -> str:
    """Digest stable decision semantics while excluding operational timing/cost."""

    return _digest(
        {
            "request_id": result.request_id,
            "task": result.task,
            "status": result.status,
            "provider": result.provider.to_dict(),
            "input_digest": result.input_digest,
            "choices": [choice.to_dict() for choice in result.choices],
            "provider_label": result.provider_label,
            "effective_label": result.effective_label,
            "exact_metadata_override": result.exact_metadata_override,
            "consequence_eligible": result.consequence_eligible,
            "gate_reasons": result.gate_reasons,
            "reason": result.reason,
            "authority_effect": result.authority_effect,
        }
    )
