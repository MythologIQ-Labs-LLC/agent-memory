from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "runtime" / "canonicalization-scheme-registry-v1.json"


class SchemeRegistryError(ValueError):
    """Stable qualification refusal from the candidate scheme registry."""

    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)


@dataclass(frozen=True)
class SchemeBinding:
    binding_id: str
    domain: str
    recorded_scheme: str
    recorded_prefix: str
    logical_scheme: str
    canonicalizer: str
    root_contract: str
    runtime_state_schemas: tuple[str, ...]
    activation: str
    envelope_requirement: str | None = None


class CandidateSchemeRegistry:
    """Qualification-only registry for #620.

    This registry is intentionally outside ``agentmem_ref``. Resolving a binding is
    evidence about compatibility identity only. It cannot verify a commitment, emit a
    new scheme, migrate state, or grant any memory/runtime authority.
    """

    def __init__(self, fixture: dict[str, Any]) -> None:
        if fixture.get("fixture_id") != "agent-memory-canonicalization-scheme-registry-v1":
            raise ValueError("unexpected canonicalization scheme registry fixture")
        bindings = fixture.get("bindings")
        if not isinstance(bindings, list) or not bindings:
            raise ValueError("scheme registry fixture must contain bindings")
        self._bindings = tuple(self._binding(row) for row in bindings)
        self._excluded_domains = {
            str(row["domain"])
            for row in fixture.get("excluded_domains", [])
            if isinstance(row, dict) and row.get("domain")
        }
        self._assert_unique_domain_prefixes()

    @staticmethod
    def _binding(row: dict[str, Any]) -> SchemeBinding:
        return SchemeBinding(
            binding_id=str(row["binding_id"]),
            domain=str(row["domain"]),
            recorded_scheme=str(row["recorded_scheme"]),
            recorded_prefix=str(row["recorded_prefix"]),
            logical_scheme=str(row["logical_scheme"]),
            canonicalizer=str(row["canonicalizer"]),
            root_contract=str(row["root_contract"]),
            runtime_state_schemas=tuple(str(item) for item in row.get("runtime_state_schemas", [])),
            activation=str(row["activation"]),
            envelope_requirement=(
                None if row.get("envelope_requirement") is None else str(row["envelope_requirement"])
            ),
        )

    def _assert_unique_domain_prefixes(self) -> None:
        seen: set[tuple[str, str]] = set()
        for binding in self._bindings:
            key = (binding.domain, binding.recorded_prefix)
            if key in seen:
                raise ValueError(f"ambiguous scheme binding for domain/prefix {key!r}")
            seen.add(key)

    @classmethod
    def from_frozen_fixture(cls, path: Path = FIXTURE_PATH) -> "CandidateSchemeRegistry":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _validate_commitment_shape(recorded_commitment: str, prefix: str) -> None:
        if not recorded_commitment.startswith(prefix):
            raise SchemeRegistryError("unknown_scheme_for_domain")
        digest = recorded_commitment[len(prefix):]
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise SchemeRegistryError("invalid_commitment_shape")

    def resolve(
        self,
        *,
        operation: str,
        domain: str,
        recorded_commitment: str,
        requested_canonicalizer: str,
        requested_root_contract: str,
        runtime_state_schema: str | None,
    ) -> SchemeBinding:
        if domain in self._excluded_domains:
            raise SchemeRegistryError("excluded_identity_domain")
        if operation not in {"inspect", "verify", "emit"}:
            raise SchemeRegistryError("unsupported_registry_operation")

        candidates = [
            binding
            for binding in self._bindings
            if binding.domain == domain and recorded_commitment.startswith(binding.recorded_prefix)
        ]
        if not candidates:
            raise SchemeRegistryError("unknown_scheme_for_domain")
        if len(candidates) != 1:
            raise SchemeRegistryError("ambiguous_scheme_binding")
        binding = candidates[0]
        self._validate_commitment_shape(recorded_commitment, binding.recorded_prefix)

        if binding.canonicalizer != requested_canonicalizer:
            raise SchemeRegistryError("canonicalizer_mismatch")
        if binding.root_contract != requested_root_contract:
            raise SchemeRegistryError("root_contract_mismatch")

        if operation == "emit" and binding.activation == "candidate_not_emittable":
            raise SchemeRegistryError("candidate_activation_forbidden")

        if operation == "verify":
            if runtime_state_schema is None or runtime_state_schema not in binding.runtime_state_schemas:
                raise SchemeRegistryError("runtime_schema_binding_mismatch")

        return binding


def run_fixture_case(case: dict[str, Any], registry: CandidateSchemeRegistry) -> dict[str, str]:
    try:
        binding = registry.resolve(
            operation=str(case["operation"]),
            domain=str(case["domain"]),
            recorded_commitment=str(case["recorded_commitment"]),
            requested_canonicalizer=str(case["requested_canonicalizer"]),
            requested_root_contract=str(case["requested_root_contract"]),
            runtime_state_schema=(
                None if case.get("runtime_state_schema") is None else str(case["runtime_state_schema"])
            ),
        )
    except SchemeRegistryError as exc:
        return {"outcome": "refused", "reason": exc.reason}
    return {"outcome": "resolved", "binding_id": binding.binding_id}
