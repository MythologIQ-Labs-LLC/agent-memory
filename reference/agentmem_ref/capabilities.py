"""Capability declarations and deterministic component resolution.

This module is the narrow executable surface for ADR-033 and issues #287/#290.
It deliberately does not know about PAMA, recall admission, or memory mutation.
Selecting a component says only which configured implementation may supply a
capability. It never grants authority to use the resulting memory consequence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping

MATURITY_ORDER = (
    "declared",
    "implemented",
    "runtime_wired",
    "evidence_proven",
    "reference_qualified",
)
_MATURITY_RANK = {name: index for index, name in enumerate(MATURITY_ORDER)}


class CapabilityResolutionError(ValueError):
    """No configured provider can satisfy the exact requirement."""


class AmbiguousCapabilityError(CapabilityResolutionError):
    """Several providers satisfy a requirement and configuration chooses none."""


@dataclass(frozen=True)
class CapabilityDeclaration:
    capability_id: str
    capability_version: str
    maturity: str
    state_posture: str
    scope_posture: str
    failure_posture: str
    authority_effect: str = "none"
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.capability_id or not self.capability_version:
            raise ValueError("capability identity and version are required")
        if self.maturity not in _MATURITY_RANK:
            raise ValueError(f"unknown capability maturity: {self.maturity}")
        if self.authority_effect not in {"none", "proposal_only"}:
            raise ValueError("capability authority_effect must be none or proposal_only")

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "CapabilityDeclaration":
        return cls(
            capability_id=str(value["capability_id"]),
            capability_version=str(value["capability_version"]),
            maturity=str(value["maturity"]),
            state_posture=str(value["state_posture"]),
            scope_posture=str(value["scope_posture"]),
            failure_posture=str(value["failure_posture"]),
            authority_effect=str(value.get("authority_effect", "none")),
            evidence_refs=tuple(str(item) for item in value.get("evidence_refs", ())),
            limitations=tuple(str(item) for item in value.get("limitations", ())),
            enabled=bool(value.get("enabled", True)),
        )

    def to_dict(self) -> dict:
        return {
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "maturity": self.maturity,
            "state_posture": self.state_posture,
            "scope_posture": self.scope_posture,
            "failure_posture": self.failure_posture,
            "authority_effect": self.authority_effect,
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
            "enabled": self.enabled,
        }


@dataclass(frozen=True)
class ComponentDeclaration:
    component_id: str
    component_version: str
    profile_version: str
    failure_posture: str
    capabilities: tuple[CapabilityDeclaration, ...]
    enabled: bool = True
    runtime_ref: str = ""
    provenance_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.component_id or not self.component_version or not self.profile_version:
            raise ValueError("component identity, component version, and profile version are required")
        seen: set[tuple[str, str]] = set()
        for capability in self.capabilities:
            identity = (capability.capability_id, capability.capability_version)
            if identity in seen:
                raise ValueError(f"duplicate capability declaration: {identity}")
            seen.add(identity)

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "ComponentDeclaration":
        raw_capabilities = value.get("capabilities", ())
        if not isinstance(raw_capabilities, (list, tuple)):
            raise ValueError("component capabilities must be an array")
        return cls(
            component_id=str(value["component_id"]),
            component_version=str(value["component_version"]),
            profile_version=str(value["profile_version"]),
            failure_posture=str(value["failure_posture"]),
            capabilities=tuple(CapabilityDeclaration.from_dict(item) for item in raw_capabilities),
            enabled=bool(value.get("enabled", True)),
            runtime_ref=str(value.get("runtime_ref", "")),
            provenance_refs=tuple(str(item) for item in value.get("provenance_refs", ())),
        )

    def to_dict(self) -> dict:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "profile_version": self.profile_version,
            "failure_posture": self.failure_posture,
            "enabled": self.enabled,
            "runtime_ref": self.runtime_ref,
            "provenance_refs": list(self.provenance_refs),
            "capabilities": [capability.to_dict() for capability in self.capabilities],
        }


@dataclass(frozen=True)
class CapabilityRequirement:
    capability_id: str
    minimum_maturity: str
    capability_version: str = ""
    required_state_postures: tuple[str, ...] = ()
    required_scope_postures: tuple[str, ...] = ()
    allowed_components: tuple[str, ...] = ()
    preferred_component: str = ""

    def __post_init__(self) -> None:
        if self.minimum_maturity not in _MATURITY_RANK:
            raise ValueError(f"unknown minimum maturity: {self.minimum_maturity}")


@dataclass(frozen=True)
class ResolvedCapability:
    component_id: str
    component_version: str
    profile_version: str
    capability_id: str
    capability_version: str
    maturity: str
    state_posture: str
    scope_posture: str
    failure_posture: str
    authority_effect: str
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "profile_version": self.profile_version,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "maturity": self.maturity,
            "state_posture": self.state_posture,
            "scope_posture": self.scope_posture,
            "failure_posture": self.failure_posture,
            "authority_effect": self.authority_effect,
            "evidence_refs": list(self.evidence_refs),
            "limitations": list(self.limitations),
        }


@dataclass
class ComponentRegistry:
    """Deterministic registry for independently matured capabilities.

    Registration order is intentionally irrelevant. If several providers remain
    eligible after all explicit constraints, resolution fails unless a preferred
    provider is configured. That is safer than first-match folklore.
    """

    preferences: Mapping[str, str] = field(default_factory=dict)
    _components: dict[str, ComponentDeclaration] = field(default_factory=dict, init=False)

    def register(self, component: ComponentDeclaration) -> None:
        existing = self._components.get(component.component_id)
        if existing is not None and existing.component_version == component.component_version:
            raise ValueError(
                f"component already registered at version {component.component_version}: {component.component_id}"
            )
        self._components[component.component_id] = component

    def register_many(self, components: Iterable[ComponentDeclaration]) -> None:
        for component in components:
            self.register(component)

    def resolve(self, requirement: CapabilityRequirement) -> ResolvedCapability:
        eligible: list[tuple[ComponentDeclaration, CapabilityDeclaration]] = []
        allowed = set(requirement.allowed_components)
        for component in self._components.values():
            if not component.enabled:
                continue
            if allowed and component.component_id not in allowed:
                continue
            for capability in component.capabilities:
                if not capability.enabled or capability.capability_id != requirement.capability_id:
                    continue
                if requirement.capability_version and capability.capability_version != requirement.capability_version:
                    continue
                if not maturity_satisfies(capability.maturity, requirement.minimum_maturity):
                    continue
                if requirement.required_state_postures and capability.state_posture not in requirement.required_state_postures:
                    continue
                if requirement.required_scope_postures and capability.scope_posture not in requirement.required_scope_postures:
                    continue
                eligible.append((component, capability))

        preferred = requirement.preferred_component or self.preferences.get(requirement.capability_id, "")
        if preferred:
            matches = [pair for pair in eligible if pair[0].component_id == preferred]
            if len(matches) != 1:
                raise CapabilityResolutionError(
                    f"preferred provider {preferred!r} is not eligible for {requirement.capability_id!r} "
                    f"at minimum maturity {requirement.minimum_maturity!r}"
                )
            return _resolved(*matches[0])

        if not eligible:
            raise CapabilityResolutionError(
                f"no eligible provider for {requirement.capability_id!r} at minimum maturity "
                f"{requirement.minimum_maturity!r}"
            )
        if len(eligible) > 1:
            providers = sorted(pair[0].component_id for pair in eligible)
            raise AmbiguousCapabilityError(
                f"ambiguous providers for {requirement.capability_id!r}: {providers}; configure explicit preference"
            )
        return _resolved(*eligible[0])

    def resolve_many(self, requirements: Iterable[CapabilityRequirement]) -> tuple[ResolvedCapability, ...]:
        return tuple(self.resolve(requirement) for requirement in requirements)

    def component(self, component_id: str) -> ComponentDeclaration | None:
        return self._components.get(component_id)


def maturity_satisfies(actual: str, minimum: str) -> bool:
    try:
        return _MATURITY_RANK[actual] >= _MATURITY_RANK[minimum]
    except KeyError as exc:
        raise ValueError(f"unknown maturity: {exc.args[0]}") from exc


def _resolved(component: ComponentDeclaration, capability: CapabilityDeclaration) -> ResolvedCapability:
    return ResolvedCapability(
        component_id=component.component_id,
        component_version=component.component_version,
        profile_version=component.profile_version,
        capability_id=capability.capability_id,
        capability_version=capability.capability_version,
        maturity=capability.maturity,
        state_posture=capability.state_posture,
        scope_posture=capability.scope_posture,
        failure_posture=capability.failure_posture,
        authority_effect=capability.authority_effect,
        evidence_refs=capability.evidence_refs,
        limitations=capability.limitations,
    )
