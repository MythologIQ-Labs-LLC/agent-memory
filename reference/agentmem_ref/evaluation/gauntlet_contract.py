"""System-neutral Agent Memory Gauntlet adapter contract (#557).

This module validates adapter manifests and operation envelopes and performs deterministic
capability negotiation. It deliberately does not import the Agent Memory runtime. The
Gauntlet may evaluate Agent Memory or any external memory system, but adapter metadata and
benchmark results never grant recall or mutation authority.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .._paths import PACKAGE_NAME, REPO_ROOT

CONTRACT_VERSION = "0.1.0"
MANIFEST_SCHEMA = "gauntlet-system-adapter.schema.json"
OPERATION_SCHEMA = "gauntlet-operation-envelope.schema.json"
PROFILE_SCHEMA = "gauntlet-profile-requirements.schema.json"

SUPPORT_CLASSES = ("native", "mapped", "derived", "unsupported", "unknown")
NEGOTIATION_OUTCOMES = (
    "eligible",
    "eligible_with_limitations",
    "unsupported",
    "blocked",
    "invalid",
)


class GauntletContractError(ValueError):
    """Raised when a Gauntlet adapter/profile document violates the contract."""


def _schema_document(schema_name: str) -> dict[str, Any]:
    source = REPO_ROOT / "schemas" / schema_name
    if source.is_file():
        return json.loads(source.read_text(encoding="utf-8"))
    try:
        resource = importlib.resources.files(PACKAGE_NAME) / "_schemas" / schema_name
        return json.loads(resource.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise GauntletContractError(f"Gauntlet schema unavailable: {schema_name}") from exc


def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(_schema_document(schema_name), format_checker=FormatChecker())


def _path(error: ValidationError) -> str:
    if not error.absolute_path:
        return "$"
    return "$" + "".join(
        f"[{item!r}]" if isinstance(item, int) else f".{item}" for item in error.absolute_path
    )


def _validate(document: Mapping[str, Any], schema_name: str) -> dict[str, Any]:
    detached = json.loads(json.dumps(document))
    errors = sorted(_validator(schema_name).iter_errors(detached), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        raise GauntletContractError(f"{_path(first)}: {first.message}") from first
    return detached


def validate_manifest(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one system-adapter manifest and enforce semantic invariants.

    ``describe`` is mandatory for every adapter and must actually be available. A
    manifest is descriptive evidence; validation does not establish that any capability
    claim is true. Gauntlet profiles may later exercise claims adversarially.
    """

    detached = _validate(document, MANIFEST_SCHEMA)
    describe = detached["capabilities"]["describe"]["support"]
    if describe in {"unsupported", "unknown"}:
        raise GauntletContractError("describe capability must be available, not unsupported/unknown")
    return detached


def validate_operation_envelope(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one transport-neutral Gauntlet operation request/response envelope."""

    return _validate(document, OPERATION_SCHEMA)


def validate_profile_requirements(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one profile's required and optional capability support classes."""

    detached = _validate(document, PROFILE_SCHEMA)
    overlap = set(detached["requires"]) & set(detached["optional"])
    if overlap:
        raise GauntletContractError(
            "capability may not be both required and optional: " + ", ".join(sorted(overlap))
        )
    return detached


def canonical_manifest_bytes(document: Mapping[str, Any]) -> bytes:
    """Stable validated manifest bytes for run identity and evidence binding."""

    validated = validate_manifest(document)
    return (
        json.dumps(validated, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def manifest_digest(document: Mapping[str, Any]) -> str:
    """Return SHA-256 of the validated canonical manifest representation."""

    return hashlib.sha256(canonical_manifest_bytes(document)).hexdigest()


def capability_support(manifest: Mapping[str, Any], capability: str) -> str | None:
    """Return one declared support class, or ``None`` when the capability is undeclared."""

    validated = validate_manifest(manifest)
    declaration = validated["capabilities"].get(capability)
    return None if declaration is None else str(declaration["support"])


def negotiate_capabilities(
    manifest: Mapping[str, Any], profile_requirements: Mapping[str, Any]
) -> dict[str, Any]:
    """Deterministically negotiate a SUT manifest against one Gauntlet profile.

    The result distinguishes four important states:

    * a declared ``unsupported`` capability means the profile is unsupported, not that
      execution failed;
    * a required capability declared ``unknown`` (or omitted entirely) fails closed as
      an invalid/incomplete qualification claim;
    * a support class that exists but is not accepted by the profile is unsupported for
      that profile (for example ``derived`` against a native-only governance test);
    * optional misses produce ``eligible_with_limitations`` and never fabricate a score.

    ``blocked`` is reserved for execution/environment conditions and is not emitted by
    pure capability negotiation.
    """

    system = validate_manifest(manifest)
    profile = validate_profile_requirements(profile_requirements)

    required_evidence: list[dict[str, Any]] = []
    optional_evidence: list[dict[str, Any]] = []
    invalid: list[str] = []
    unsupported: list[str] = []

    capabilities = system["capabilities"]

    for capability in sorted(profile["requires"]):
        accepted = tuple(profile["requires"][capability])
        declaration = capabilities.get(capability)
        support = None if declaration is None else declaration["support"]
        row = {
            "capability": capability,
            "declared_support": support,
            "accepted_support": list(accepted),
        }
        if support is None:
            row["state"] = "undeclared_required"
            invalid.append(capability)
        elif support == "unknown":
            row["state"] = "unknown_required"
            invalid.append(capability)
        elif support == "unsupported":
            row["state"] = "unsupported"
            unsupported.append(capability)
        elif support not in accepted:
            row["state"] = "support_class_not_accepted"
            unsupported.append(capability)
        else:
            row["state"] = "satisfied"
        required_evidence.append(row)

    for capability in sorted(profile["optional"]):
        accepted = tuple(profile["optional"][capability])
        declaration = capabilities.get(capability)
        support = None if declaration is None else declaration["support"]
        row = {
            "capability": capability,
            "declared_support": support,
            "accepted_support": list(accepted),
        }
        if support is None:
            row["state"] = "undeclared_optional"
        elif support == "unknown":
            row["state"] = "unknown_optional"
        elif support == "unsupported":
            row["state"] = "unsupported_optional"
        elif support not in accepted:
            row["state"] = "support_class_not_accepted"
        else:
            row["state"] = "satisfied"
        optional_evidence.append(row)

    if invalid:
        outcome = "invalid"
        reason = "required capability truth is unknown or undeclared"
    elif unsupported:
        outcome = "unsupported"
        reason = "system does not provide required capability in an accepted support class"
    elif any(row["state"] != "satisfied" for row in optional_evidence):
        outcome = "eligible_with_limitations"
        reason = "required capabilities satisfied; one or more optional dimensions unavailable"
    else:
        outcome = "eligible"
        reason = "required and declared optional capabilities satisfy the profile"

    return {
        "contract_family": "agent-memory-gauntlet-capability-negotiation",
        "contract_version": CONTRACT_VERSION,
        "profile_id": profile["profile_id"],
        "system_id": system["system"]["id"],
        "adapter_id": system["adapter"]["id"],
        "manifest_digest": manifest_digest(system),
        "outcome": outcome,
        "reason": reason,
        "required": required_evidence,
        "optional": optional_evidence,
        "authority_effect": "none",
    }


__all__ = [
    "CONTRACT_VERSION",
    "SUPPORT_CLASSES",
    "NEGOTIATION_OUTCOMES",
    "GauntletContractError",
    "validate_manifest",
    "validate_operation_envelope",
    "validate_profile_requirements",
    "canonical_manifest_bytes",
    "manifest_digest",
    "capability_support",
    "negotiate_capabilities",
]
