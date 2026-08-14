"""Version-bound component capability qualification helpers for issue #300.

Qualification records describe behavior proven by an exact implementation and
adapter profile. They never grant memory mutation, structural, recall-admission,
or action authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Sequence

from .capabilities import MATURITY_ORDER, maturity_satisfies


class QualificationError(ValueError):
    """Qualification evidence is invalid or not applicable."""


class StaleQualificationError(QualificationError):
    """A qualification record does not apply to the requested exact subject."""


@dataclass(frozen=True)
class QualificationSubject:
    component_id: str
    component_version: str
    implementation_ref: str
    capability_id: str
    capability_version: str
    adapter_id: str
    adapter_version: str
    qualification_profile_id: str
    qualification_profile_version: str

    def __post_init__(self) -> None:
        for name, value in self.to_dict().items():
            if not value:
                raise ValueError(f"{name} is required")

    def to_dict(self) -> dict[str, str]:
        return {
            "component_id": self.component_id,
            "component_version": self.component_version,
            "implementation_ref": self.implementation_ref,
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "qualification_profile_id": self.qualification_profile_id,
            "qualification_profile_version": self.qualification_profile_version,
        }


@dataclass(frozen=True)
class QualificationRuntime:
    configuration_digest: str
    fixture_id: str
    fixture_digest: str
    dependency_refs: tuple[str, ...] = ()
    runtime_refs: tuple[str, ...] = ()

    def applicability_dict(self) -> dict[str, object]:
        return {
            "configuration_digest": self.configuration_digest,
            "fixture_id": self.fixture_id,
            "fixture_digest": self.fixture_digest,
            "dependency_refs": list(self.dependency_refs),
            "runtime_refs": list(self.runtime_refs),
        }


@dataclass(frozen=True)
class AdapterResult:
    """Provider-neutral envelope preserving native and normalized evidence refs."""

    subject: QualificationSubject
    operation: str
    runtime_identity: str
    input_refs: tuple[str, ...]
    raw_provider_refs: tuple[str, ...]
    normalized_refs: tuple[str, ...]
    currentness: str
    failure_result: str
    trace_ref: str

    def __post_init__(self) -> None:
        if not self.operation or not self.runtime_identity or not self.trace_ref:
            raise ValueError("operation, runtime identity, and trace reference are required")
        if not self.raw_provider_refs:
            raise ValueError("raw provider evidence must be preserved")
        if not self.normalized_refs:
            raise ValueError("normalized evidence reference is required")

    @property
    def authority_effect(self) -> str:
        return "none"


@dataclass(frozen=True)
class QualificationRecord:
    subject: QualificationSubject
    runtime: QualificationRuntime
    license_id: str
    license_ref: str
    use_posture: str
    operations: tuple[str, ...]
    raw_provider_refs: tuple[str, ...]
    normalized_refs: tuple[str, ...]
    checks: tuple[tuple[str, bool, str], ...]
    artifact_digests: tuple[str, ...]
    claimed_maturity: str
    earned_maturity: str
    limitations: tuple[str, ...] = ()
    qualification_current: bool = True

    def __post_init__(self) -> None:
        if self.claimed_maturity not in MATURITY_ORDER or self.earned_maturity not in MATURITY_ORDER:
            raise ValueError("unknown maturity")
        if not maturity_satisfies(self.claimed_maturity, self.earned_maturity):
            raise QualificationError("qualification cannot earn maturity above the component's claimed maturity")
        if not self.license_id or not self.license_ref:
            raise QualificationError("source-rights license identity and exact reference are required")
        if self.use_posture not in {"runtime_allowed", "comparator_only", "disallowed"}:
            raise ValueError("unknown source-rights use posture")
        if self.use_posture == "disallowed" and self.qualification_current:
            raise QualificationError("disallowed source cannot produce a current qualification")
        if not self.operations:
            raise QualificationError("qualification must exercise at least one operation")
        if not self.raw_provider_refs or not self.normalized_refs or not self.artifact_digests:
            raise QualificationError("qualification must preserve raw, normalized, and digest evidence")
        if self.earned_maturity == "reference_qualified":
            if self.use_posture != "runtime_allowed":
                raise QualificationError("reference_qualified requires runtime-allowed source rights")
            if not self.checks or not all(passed for _, passed, _ in self.checks):
                raise QualificationError("reference_qualified requires every required profile check to pass")

    @property
    def applicability_digest(self) -> str:
        return applicability_digest(self.subject, self.runtime)

    @property
    def authority_effect(self) -> str:
        return "none"

    def assert_applicable(self, subject: QualificationSubject, runtime: QualificationRuntime) -> None:
        expected = applicability_digest(subject, runtime)
        if expected != self.applicability_digest:
            raise StaleQualificationError(
                "qualification applicability changed; explicit compatibility evidence or requalification is required"
            )
        if not self.qualification_current:
            raise StaleQualificationError("qualification is explicitly non-current")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "subject": self.subject.to_dict(),
            "runtime": self.runtime.applicability_dict(),
            "source_rights": {
                "license_id": self.license_id,
                "license_ref": self.license_ref,
                "use_posture": self.use_posture,
            },
            "evidence": {
                "operations": list(self.operations),
                "raw_provider_refs": list(self.raw_provider_refs),
                "normalized_refs": list(self.normalized_refs),
                "checks": [
                    {"check_id": check_id, "passed": passed, "evidence_ref": evidence_ref}
                    for check_id, passed, evidence_ref in self.checks
                ],
                "artifact_digests": list(self.artifact_digests),
            },
            "result": {
                "claimed_maturity": self.claimed_maturity,
                "earned_maturity": self.earned_maturity,
                "applicability_digest": self.applicability_digest,
                "qualification_current": self.qualification_current,
                "authority_effect": "none",
                "limitations": list(self.limitations),
            },
        }


def applicability_digest(subject: QualificationSubject, runtime: QualificationRuntime) -> str:
    """Hash the exact qualification applicability boundary using deterministic JSON."""

    payload = {"subject": subject.to_dict(), "runtime": runtime.applicability_dict()}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def qualification_from_adapter_results(
    *,
    subject: QualificationSubject,
    runtime: QualificationRuntime,
    license_id: str,
    license_ref: str,
    use_posture: str,
    results: Sequence[AdapterResult],
    checks: Sequence[tuple[str, bool, str]],
    artifact_digests: Sequence[str],
    claimed_maturity: str,
    earned_maturity: str,
    limitations: Sequence[str] = (),
) -> QualificationRecord:
    if not results:
        raise QualificationError("at least one adapter result is required")
    for result in results:
        if result.subject != subject:
            raise QualificationError("adapter result subject does not match qualification subject")
        if result.authority_effect != "none":
            raise QualificationError("adapter result cannot grant authority")
    return QualificationRecord(
        subject=subject,
        runtime=runtime,
        license_id=license_id,
        license_ref=license_ref,
        use_posture=use_posture,
        operations=tuple(dict.fromkeys(result.operation for result in results)),
        raw_provider_refs=tuple(ref for result in results for ref in result.raw_provider_refs),
        normalized_refs=tuple(ref for result in results for ref in result.normalized_refs),
        checks=tuple(checks),
        artifact_digests=tuple(artifact_digests),
        claimed_maturity=claimed_maturity,
        earned_maturity=earned_maturity,
        limitations=tuple(limitations),
    )
