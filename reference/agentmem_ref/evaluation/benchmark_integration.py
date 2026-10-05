"""Benchmark integration contract (#652).

A benchmark integration descriptor describes how one benchmark enters the Memory
Evaluation laboratory: its exact identity, source rights, frozen-input rules, native
protocol, system invocation surface, provider requirements, optional mappings into the
common evidence dimensions, evaluator-integrity controls, reproducibility requirements,
and its relationship to the Agent Memory Gauntlet.

The descriptor is deliberately *not* a universal benchmark execution protocol. It points
truthfully at a benchmark-native runner and records which heterogeneous semantics that
runner owns. Validation is structural and semantic only: it never imports or executes the
runner, the normalizer, or the evaluator-integrity controls it names.

Benchmark integration metadata has no authority over Agent Memory runtime behavior and
cannot upgrade the evidence class of anything it describes.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
import re
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .._paths import PACKAGE_NAME, REPO_ROOT
from .contract import DIMENSIONS, BenchmarkContractError, metric_observation

CONTRACT_FAMILY = "agent-memory-benchmark-integration"
CONTRACT_VERSION = "1.0.0"
SCHEMA_NAME = "memory-benchmark-integration.schema.json"

# Explicit compatibility policy. A descriptor is accepted only when its major version
# matches the supported major and its minor version does not exceed the supported minor.
# Patch versions are always accepted within a compatible major.minor. Anything newer or
# from another major fails closed: this validator cannot know what it does not implement.
SUPPORTED_MAJOR = 1
SUPPORTED_MINOR = 0

PROVENANCE_CLASSES = (
    "external_independent",
    "external_adapted",
    "gauntlet_native_gap",
    "agent_memory_conformance",
    "baseline_or_probe",
)
# Evidence-strength ordering used to refuse provenance upgrades. Lower index is stronger
# as *independent* evidence. Registration machinery may never move a benchmark upward.
PROVENANCE_STRENGTH = {name: index for index, name in enumerate(PROVENANCE_CLASSES)}
EXTERNAL_PROVENANCE = {"external_independent", "external_adapted"}
GAUNTLET_RELATIONSHIPS = ("not_applicable", "eligible", "bound_profile")
EXECUTED_EVIDENCE = {"complete", "partial"}

_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class BenchmarkIntegrationError(BenchmarkContractError):
    """Raised when a benchmark integration descriptor violates the contract."""


def _schema_document() -> dict[str, Any]:
    source = REPO_ROOT / "schemas" / SCHEMA_NAME
    if source.is_file():
        return json.loads(source.read_text(encoding="utf-8"))
    try:
        resource = importlib.resources.files(PACKAGE_NAME) / "_schemas" / SCHEMA_NAME
        return json.loads(resource.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise BenchmarkIntegrationError(f"benchmark integration schema unavailable: {SCHEMA_NAME}") from exc


def _validator() -> Draft202012Validator:
    return Draft202012Validator(_schema_document(), format_checker=FormatChecker())


def _path(error: ValidationError) -> str:
    if not error.absolute_path:
        return "$"
    return "$" + "".join(
        f"[{item!r}]" if isinstance(item, int) else f".{item}" for item in error.absolute_path
    )


def contract_version_compatible(version: str) -> bool:
    """Apply the explicit compatibility policy to one declared contract version."""

    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return False
    major, minor, _patch = (int(part) for part in parts)
    return major == SUPPORTED_MAJOR and minor <= SUPPORTED_MINOR


def is_placeholder_sha256(value: str | None) -> bool:
    """Detect digests that cannot identify a real frozen input.

    A repeated single hex character, the digest of zero bytes, or anything that is not
    64 lowercase hex characters is a placeholder, not an input identity.
    """

    if not isinstance(value, str) or len(value) != 64:
        return True
    if any(ch not in "0123456789abcdef" for ch in value):
        return True
    if len(set(value)) == 1:
        return True
    return value == _EMPTY_SHA256


def _refuse(message: str) -> None:
    raise BenchmarkIntegrationError(message)


def _semantic_validate(document: Mapping[str, Any]) -> None:
    version = document["contract_version"]
    if not contract_version_compatible(version):
        _refuse(
            f"unsupported benchmark integration contract version {version}; "
            f"supported: {SUPPORTED_MAJOR}.{SUPPORTED_MINOR}.x and earlier minors of major {SUPPORTED_MAJOR}"
        )

    benchmark = document["benchmark"]
    provenance = benchmark["provenance_class"]
    upstream = benchmark["upstream"]
    revision_rule = benchmark.get("source_revision_rule", "static_exact_revision")
    if provenance in EXTERNAL_PROVENANCE:
        if not upstream.get("repository") or not upstream.get("url"):
            _refuse(f"{provenance} benchmark requires benchmark.upstream.repository and url")
        if revision_rule == "repository_owned":
            _refuse(f"{provenance} benchmark may not declare source_revision_rule=repository_owned")
    if benchmark["source_revision"] == "unbound" and revision_rule != "manifest_bound":
        _refuse("benchmark.source_revision may be 'unbound' only with source_revision_rule=manifest_bound")
    if provenance == "baseline_or_probe" and upstream.get("repository"):
        _refuse("baseline_or_probe benchmark may not claim an upstream repository")

    inputs = document["input_contract"]
    known_sha = inputs.get("known_input_sha256")
    if known_sha is not None and is_placeholder_sha256(known_sha):
        _refuse("input_contract.known_input_sha256 is a placeholder, not a frozen input identity")
    if inputs["input_may_be_absent_before_execution"] is False:
        if known_sha is None:
            _refuse(
                "input_contract.known_input_sha256 is required when the input is committed "
                "(input_may_be_absent_before_execution=false)"
            )
        if inputs["input_digest_rule"] != "sha256_inline_fixture" and not inputs.get("committed_input_path"):
            _refuse("committed inputs require input_contract.committed_input_path")
    if inputs["dataset_revision_rule"] == "exact_revision_required" and provenance in EXTERNAL_PROVENANCE:
        if not inputs.get("known_dataset_revision"):
            _refuse("exact_revision_required inputs must record input_contract.known_dataset_revision")

    protocol = document["native_protocol"]
    if not protocol["native_metrics"]:
        _refuse("native_protocol.native_metrics must name at least one benchmark-native metric")
    runner = protocol["runner"]
    if runner["kind"] in {"module_callable", "gauntlet_profile_runner"} and ":" not in runner["entry_point"]:
        _refuse(f"{runner['kind']} entry_point must use module:callable syntax")
    if runner["kind"] == "repository_script" and ":" in runner["entry_point"]:
        _refuse("repository_script entry_point must be a repository-relative path")

    system = document["system_requirements"]
    surface = system["invocation_surface"]
    entry = system["external_system_entry"]
    if surface == "gauntlet_operation_envelope":
        if entry != "gauntlet_system_adapter":
            _refuse("gauntlet_operation_envelope invocation requires external_system_entry=gauntlet_system_adapter")
        if not system["required_operations"]:
            _refuse("gauntlet_operation_envelope invocation must list required_operations")
    elif entry == "gauntlet_system_adapter":
        _refuse(f"external_system_entry=gauntlet_system_adapter requires invocation_surface=gauntlet_operation_envelope, not {surface}")
    overlap = set(system["required_operations"]) & set(system["optional_operations"])
    if overlap:
        _refuse("operations may not be both required and optional: " + ", ".join(sorted(overlap)))

    provider = document["provider_requirements"]
    judge = provider["judge"]
    if judge["required"]:
        if provider["credentials"] == "credential_free":
            _refuse("a required judge model contradicts credentials=credential_free")
        if not isinstance(judge.get("identity"), Mapping) or not judge["identity"]:
            _refuse("a required judge model must record its identity (provider/model/version/configuration)")
        if provider["model_dependency"] != "answer_and_judge_models":
            _refuse("a required judge model requires model_dependency=answer_and_judge_models")
    elif provider["model_dependency"] == "answer_and_judge_models":
        _refuse("model_dependency=answer_and_judge_models requires judge.required=true")

    normalization = document["normalization"]
    mapped_dimensions = {mapping["dimension"] for mapping in normalization["mappings"]}
    unmapped = normalization["unmapped_dimensions"]
    if normalization["normalizer"] is None and normalization["mappings"]:
        _refuse("normalization.mappings require a normalizer; a mapping with no normalizer invents evidence")
    both = mapped_dimensions & set(unmapped)
    if both:
        _refuse("dimension may not be both mapped and unmapped: " + ", ".join(sorted(both)))
    missing = set(DIMENSIONS) - mapped_dimensions - set(unmapped)
    if missing:
        _refuse(
            "every common dimension must be mapped or explicitly unmapped with a reason; missing: "
            + ", ".join(sorted(missing))
        )
    seen: set[tuple[str, str]] = set()
    for mapping in normalization["mappings"]:
        key = (mapping["dimension"], mapping["metric_id"])
        if key in seen:
            _refuse(f"duplicate normalization mapping: {key[0]}.{key[1]}")
        seen.add(key)
        if not mapping["native_evidence"].strip():
            _refuse(f"mapping {key[0]}.{key[1]} has no native evidence")
    declared = document.get("dimensions")
    if declared is not None:
        extra = set(declared) - mapped_dimensions
        if extra:
            _refuse("dimensions declares unmapped dimensions: " + ", ".join(sorted(extra)))

    integrity = document["evaluator_integrity"]
    if integrity["negative_controls"] and not integrity["runner"]:
        _refuse("evaluator_integrity.negative_controls require evaluator_integrity.runner")
    control_ids = [control["control_id"] for control in integrity["negative_controls"]]
    if len(control_ids) != len(set(control_ids)):
        _refuse("evaluator_integrity.negative_controls contain duplicate control ids")

    gauntlet = document["gauntlet"]
    if gauntlet["relationship"] == "bound_profile":
        if not gauntlet["profile_id"]:
            _refuse("gauntlet.relationship=bound_profile requires gauntlet.profile_id")
        if surface != "gauntlet_operation_envelope":
            _refuse("a Gauntlet-bound integration must invoke systems through gauntlet_operation_envelope")
        if runner["kind"] != "gauntlet_profile_runner":
            _refuse("a Gauntlet-bound integration must declare runner.kind=gauntlet_profile_runner")
    elif gauntlet["profile_id"] is not None:
        _refuse(f"gauntlet.relationship={gauntlet['relationship']} may not name a profile_id")

    variants: set[str] = set()
    executed = 0
    for item in document["evidence_history"]:
        variant = item["variant"]
        if variant in variants:
            _refuse(f"duplicate evidence_history variant: {variant}")
        variants.add(variant)
        status = item["status"]
        sha = item.get("input_sha256")
        if sha is not None and is_placeholder_sha256(sha):
            _refuse(f"evidence_history[{variant}].input_sha256 is a placeholder digest")
        if status in EXECUTED_EVIDENCE:
            executed += 1
            for field in ("input_sha256", "system_revision", "report", "report_binding"):
                if not item.get(field):
                    _refuse(f"{status} evidence_history[{variant}] requires exact {field}")
        else:
            for field in ("report", "normalized_reports", "input_sha256", "report_binding"):
                if item.get(field):
                    _refuse(f"{status} evidence_history[{variant}] may not carry {field}")
            if status == "blocked" and not item.get("blocker"):
                _refuse(f"blocked evidence_history[{variant}] requires a blocker")

    state = document["admission_state"]
    if state in {"evidence_complete", "evidence_partial"} and executed == 0:
        _refuse(f"admission_state={state} requires at least one complete or partial evidence_history entry")
    if state == "evidence_complete" and any(item["status"] != "complete" for item in document["evidence_history"]):
        _refuse("admission_state=evidence_complete requires every evidence_history entry to be complete")
    if state in {"discovered", "qualification_pending", "rejected", "watchlist"} and executed:
        _refuse(f"admission_state={state} contradicts executed evidence_history entries")


def validate_integration(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached benchmark integration descriptor.

    Structural validation runs against the published schema; semantic validation enforces
    the identity, rights, provenance, normalization, and Gauntlet-relationship rules that
    JSON Schema cannot express. Nothing named by the descriptor is imported or executed.
    """

    detached = json.loads(json.dumps(document))
    errors = sorted(_validator().iter_errors(detached), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        raise BenchmarkIntegrationError(f"{_path(first)}: {first.message}") from first
    _semantic_validate(detached)
    return detached


def canonical_integration_bytes(document: Mapping[str, Any]) -> bytes:
    validated = validate_integration(document)
    return (
        json.dumps(validated, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def integration_digest(document: Mapping[str, Any]) -> str:
    """SHA-256 of the validated canonical descriptor representation."""

    return hashlib.sha256(canonical_integration_bytes(document)).hexdigest()


def load_integration(path: str | Path) -> dict[str, Any]:
    """Load and validate one descriptor file without executing anything it names."""

    location = Path(path)
    try:
        document = json.loads(location.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkIntegrationError(f"unable to load benchmark integration {location}: {exc}") from exc
    if not isinstance(document, dict):
        raise BenchmarkIntegrationError("benchmark integration root must be a JSON object")
    return validate_integration(document)


def resolve_native_path(native: Mapping[str, Any], path: str) -> tuple[bool, Any]:
    """Resolve a dotted path inside a native report.

    Returns ``(present, value)``. List indexes are plain integers. A missing segment makes
    the observation absent; absence is never converted into a value.
    """

    current: Any = native
    for segment in path.split("."):
        if isinstance(current, Mapping) and segment in current:
            current = current[segment]
            continue
        if isinstance(current, list) and segment.isdigit() and int(segment) < len(current):
            current = current[int(segment)]
            continue
        return False, None
    return True, current


def mapped_metric_observations(
    descriptor: Mapping[str, Any],
    native: Mapping[str, Any],
    *,
    dimension: str,
    denominator: float | int | None = None,
    unit: str | None = None,
    population: str | None = None,
) -> list[dict[str, Any]]:
    """Build common metric observations strictly from declared mappings and native evidence.

    A mapping whose ``native_evidence`` path is absent from the native report, or resolves
    to something that is not a scalar, yields a ``not_measured`` observation with a note.
    It never yields a value and never yields zero. The mapping therefore cannot manufacture
    a measurement the benchmark did not produce.
    """

    if dimension not in DIMENSIONS:
        raise BenchmarkIntegrationError(f"unsupported dimension: {dimension}")
    observations: list[dict[str, Any]] = []
    for mapping in descriptor["normalization"]["mappings"]:
        if mapping["dimension"] != dimension:
            continue
        direction = mapping.get("direction", "descriptive")
        present, value = resolve_native_path(native, mapping["native_evidence"])
        scalar = isinstance(value, (int, float, str, bool)) and not (
            isinstance(value, float) and value != value
        )
        if not present or not scalar:
            observations.append(
                metric_observation(
                    mapping["metric_id"],
                    state="not_measured",
                    direction=direction,
                    note=(
                        f"native evidence absent at {mapping['native_evidence']}; "
                        "a mapping cannot manufacture a measurement"
                    ),
                )
            )
            continue
        observations.append(
            metric_observation(
                mapping["metric_id"],
                value=value,
                direction=direction,
                denominator=denominator,
                unit=unit,
                population=population,
                note=mapping["semantics"],
            )
        )
    return observations


_WILDCARD = re.compile(r"<[A-Za-z_][A-Za-z0-9_]*>")


def mapping_pattern(metric_id: str) -> "re.Pattern[str]":
    """Compile a declared metric id (with ``<placeholder>`` segments) into a matcher."""

    parts = _WILDCARD.split(metric_id)
    return re.compile("^" + "[A-Za-z0-9_.@-]+".join(re.escape(part) for part in parts) + "$")


def declared_mapping(descriptor: Mapping[str, Any], dimension: str, metric_id: str) -> dict[str, Any] | None:
    """Return the descriptor mapping that declares ``metric_id`` in ``dimension``, if any.

    Used to refuse a normalizer that emits a measured common metric the descriptor never
    declared: a metric with no declared native evidence is undeclared evidence.
    """

    for mapping in descriptor["normalization"]["mappings"]:
        if mapping["dimension"] != dimension:
            continue
        if mapping["metric_id"] == metric_id or mapping_pattern(mapping["metric_id"]).match(metric_id):
            return mapping
    return None


def check_profile_binding(profile: Mapping[str, Any], descriptor: Mapping[str, Any]) -> dict[str, Any]:
    """Check one Gauntlet profile against the descriptor it claims to bind.

    Registration may never change evidence class: the profile's ``kind`` must equal the
    descriptor's ``provenance_class``. A profile that declares a stronger class than the
    benchmark it executes is a provenance upgrade and is refused; a weaker class is a
    silent relabeling and is refused as well. The binding must also be mutual.
    """

    validated = validate_integration(descriptor)
    profile_id = profile.get("profile_id")
    kind = profile.get("kind")
    provenance = validated["benchmark"]["provenance_class"]
    if kind not in PROVENANCE_STRENGTH:
        raise BenchmarkIntegrationError(f"Gauntlet profile {profile_id} declares unknown kind {kind!r}")
    if profile.get("benchmark_integration") != validated["integration_id"]:
        raise BenchmarkIntegrationError(
            f"Gauntlet profile {profile_id} does not declare benchmark_integration={validated['integration_id']}"
        )
    gauntlet = validated["gauntlet"]
    if gauntlet["relationship"] != "bound_profile" or gauntlet["profile_id"] != profile_id:
        raise BenchmarkIntegrationError(
            f"benchmark integration {validated['integration_id']} is not bound to Gauntlet profile {profile_id}"
        )
    if kind != provenance:
        direction = (
            "upgrade" if PROVENANCE_STRENGTH[kind] < PROVENANCE_STRENGTH[provenance] else "relabel"
        )
        raise BenchmarkIntegrationError(
            f"Gauntlet profile {profile_id} would {direction} benchmark provenance "
            f"{provenance} to {kind}; registration cannot change evidence class"
        )
    runner = validated["native_protocol"]["runner"]
    if profile.get("runner") != runner["entry_point"]:
        raise BenchmarkIntegrationError(
            f"Gauntlet profile {profile_id} runner {profile.get('runner')!r} differs from the "
            f"integration runner {runner['entry_point']!r}"
        )
    return {
        "profile_id": profile_id,
        "integration_id": validated["integration_id"],
        "provenance_class": provenance,
        "profile_kind": kind,
        "status": "bound",
    }


__all__ = [
    "CONTRACT_FAMILY",
    "CONTRACT_VERSION",
    "PROVENANCE_CLASSES",
    "PROVENANCE_STRENGTH",
    "GAUNTLET_RELATIONSHIPS",
    "BenchmarkIntegrationError",
    "contract_version_compatible",
    "is_placeholder_sha256",
    "validate_integration",
    "canonical_integration_bytes",
    "integration_digest",
    "load_integration",
    "resolve_native_path",
    "mapped_metric_observations",
    "mapping_pattern",
    "declared_mapping",
    "check_profile_binding",
]
