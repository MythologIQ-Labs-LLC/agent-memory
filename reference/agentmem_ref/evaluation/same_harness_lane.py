"""Same-harness lane freeze contract (#640 / #601).

A lane freeze fixes, before any score exists, everything that makes a cross-system
comparison fair: the exact external harness revision, the frozen input and its digest,
the query selection, the retrieval/context budget, the gold-identity and leakage rules,
the evaluator and its (absence of) models, execution semantics, and the exact source,
adapter, configuration, inference posture, and capability posture of every system that
will enter. Changing any of those after results are visible requires a new lane id.

A lane carries no scores. It is validated structurally against
``schemas/same-harness-lane.schema.json`` and semantically here, and it is cross-checked
against the benchmark integration registry so a lane cannot claim a harness, revision,
or input the registered integration does not describe. Lane metadata has no authority.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from .._paths import PACKAGE_NAME, REPO_ROOT
from .benchmark_integration import EXTERNAL_PROVENANCE, BenchmarkIntegrationError, is_placeholder_sha256

CONTRACT_FAMILY = "agent-memory-same-harness-lane"
CONTRACT_VERSION = "1.0.0"
SCHEMA_NAME = "same-harness-lane.schema.json"
LANES_RESOURCE = "lanes"
SUPPORTED_MAJOR = 1
SUPPORTED_MINOR = 0

# Row statuses a lane may carry while its own status is still ``frozen``.
_PRE_EXECUTION_ROW_STATUSES = {"frozen", "deferred", "blocked"}
_POSTURE_REQUIRES_CREDENTIALS = {"reflective_llm_extraction": {"provider_dependent"}}


class SameHarnessLaneError(BenchmarkIntegrationError):
    """Raised when a same-harness lane freeze violates the contract."""


def _schema_document() -> dict[str, Any]:
    source = REPO_ROOT / "schemas" / SCHEMA_NAME
    if source.is_file():
        return json.loads(source.read_text(encoding="utf-8"))
    try:
        resource = importlib.resources.files(PACKAGE_NAME) / "_schemas" / SCHEMA_NAME
        return json.loads(resource.read_text(encoding="utf-8"))
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise SameHarnessLaneError(f"same-harness lane schema unavailable: {SCHEMA_NAME}") from exc


def _path(error: ValidationError) -> str:
    if not error.absolute_path:
        return "$"
    return "$" + "".join(f"[{item!r}]" if isinstance(item, int) else f".{item}" for item in error.absolute_path)


def contract_version_compatible(version: str) -> bool:
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return False
    major, minor, _patch = (int(part) for part in parts)
    return major == SUPPORTED_MAJOR and minor <= SUPPORTED_MINOR


def _refuse(message: str) -> None:
    raise SameHarnessLaneError(message)


def _semantic_validate(lane: Mapping[str, Any]) -> None:
    version = lane["contract_version"]
    if not contract_version_compatible(version):
        _refuse(f"unsupported same-harness lane contract version {version}")

    dataset = lane["dataset"]
    if is_placeholder_sha256(dataset["input_sha256"]):
        _refuse("dataset.input_sha256 is a placeholder, not a frozen input identity")
    names: set[str] = set()
    for fixture in dataset["fixtures"]:
        if fixture["name"] in names:
            _refuse(f"duplicate fixture name: {fixture['name']}")
        names.add(fixture["name"])
        if is_placeholder_sha256(fixture["sha256"]):
            _refuse(f"fixture {fixture['name']} carries a placeholder digest")
    partition = dataset.get("query_partition")
    if partition and sum(partition.values()) != dataset["query_count"]:
        _refuse("dataset.query_partition must sum to dataset.query_count")

    selection = lane["selection"]
    if selection["query_limit"] is not None and selection["query_limit"] > dataset["query_count"]:
        _refuse("selection.query_limit exceeds dataset.query_count")

    evaluator = lane["evaluator"]
    if evaluator["llm_calls"]:
        if not evaluator["answer_model"] and not evaluator["judge_model"]:
            _refuse("an evaluator with llm_calls=true must bind an answer or judge model identity")
    elif evaluator["answer_model"] is not None or evaluator["judge_model"] is not None:
        _refuse("an evaluator with llm_calls=false may not name an answer or judge model")

    status = lane["status"]
    row_ids: set[str] = set()
    provider_keys: set[str] = set()
    roles: dict[str, int] = {}
    for system in lane["systems"]:
        row_id = system["row_id"]
        if row_id in row_ids:
            _refuse(f"duplicate system row_id: {row_id}")
        row_ids.add(row_id)
        if system["provider_key"] in provider_keys:
            _refuse(f"duplicate provider_key: {system['provider_key']}")
        provider_keys.add(system["provider_key"])
        roles[system["role"]] = roles.get(system["role"], 0) + 1
        row_status = system["status"]
        if status == "frozen" and row_status not in _PRE_EXECUTION_ROW_STATUSES:
            _refuse(f"a frozen lane may not carry an {row_status} row: {row_id}")
        if row_status in {"deferred", "blocked"} and not system.get("status_reason"):
            _refuse(f"{row_status} row {row_id} requires a status_reason")
        if row_status == "frozen":
            for field in ("inference_posture", "credentials"):
                if field not in system:
                    _refuse(f"frozen row {row_id} must declare {field}")
            posture = system["inference_posture"]
            allowed = _POSTURE_REQUIRES_CREDENTIALS.get(posture)
            if allowed and system["credentials"] not in allowed:
                _refuse(f"row {row_id}: inference_posture {posture} requires credentials in {sorted(allowed)}")
            if posture == "explicit_memory_no_inference" and system["credentials"] == "provider_dependent":
                _refuse(f"row {row_id}: explicit-memory posture contradicts provider_dependent credentials")
            if not system["capability_posture"]:
                _refuse(f"frozen row {row_id} must declare a capability_posture")
        source = system["source"]
        if source["kind"] == "python_package" and row_status == "frozen":
            if not system.get("dependency_pins"):
                _refuse(f"frozen python_package row {row_id} must carry exact dependency_pins")
            if source["revision"] == "unbound":
                _refuse(f"frozen python_package row {row_id} must bind an exact source revision")
    if roles.get("comparator", 0) < 1:
        _refuse("a lane needs at least one comparator row")
    if roles.get("control", 0) + roles.get("baseline", 0) < 1:
        _refuse("a lane needs at least one control or baseline row")


def validate_lane(document: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a detached lane freeze. Nothing it names is executed."""

    detached = json.loads(json.dumps(document))
    validator = Draft202012Validator(_schema_document(), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(detached), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        raise SameHarnessLaneError(f"{_path(first)}: {first.message}") from first
    _semantic_validate(detached)
    return detached


def canonical_lane_bytes(document: Mapping[str, Any]) -> bytes:
    validated = validate_lane(document)
    return (json.dumps(validated, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def lane_digest(document: Mapping[str, Any]) -> str:
    """SHA-256 of the validated canonical lane; the freeze identity recorded on the issue."""

    return hashlib.sha256(canonical_lane_bytes(document)).hexdigest()


def load_lane(path: str | Path) -> dict[str, Any]:
    location = Path(path)
    try:
        document = json.loads(location.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SameHarnessLaneError(f"unable to load same-harness lane {location}: {exc}") from exc
    if not isinstance(document, dict):
        raise SameHarnessLaneError("same-harness lane root must be a JSON object")
    return validate_lane(document)


def _lanes_root() -> Path:
    resource = importlib.resources.files(f"{PACKAGE_NAME}.evaluation") / LANES_RESOURCE
    root = Path(str(resource))
    if not root.is_dir():
        raise SameHarnessLaneError(f"same-harness lane directory unavailable: {root}")
    return root


def lane_paths() -> list[Path]:
    return sorted(_lanes_root().glob("*.json"))


def list_lanes() -> list[dict[str, Any]]:
    lanes = [load_lane(path) for path in lane_paths()]
    seen: set[str] = set()
    for lane in lanes:
        if lane["lane_id"] in seen:
            raise SameHarnessLaneError(f"duplicate lane id: {lane['lane_id']}")
        seen.add(lane["lane_id"])
    return sorted(lanes, key=lambda item: item["lane_id"])


def get_lane(lane_id: str) -> dict[str, Any]:
    for lane in list_lanes():
        if lane["lane_id"] == lane_id:
            return lane
    raise KeyError(lane_id)


def resolve_lane(lane: Mapping[str, Any]) -> dict[str, Any]:
    """Cross-check a lane against its registered benchmark integration.

    The lane may not claim a harness revision, input digest, or evidence class that the
    integration descriptor does not describe. A lane over a non-external integration is
    refused: same-harness evidence is only meaningful against an external harness.
    """

    from .registry import get_integration

    validated = validate_lane(lane)
    try:
        integration = get_integration(validated["benchmark_integration"])
    except KeyError:
        raise SameHarnessLaneError(
            f"lane {validated['lane_id']} binds unknown benchmark integration {validated['benchmark_integration']}"
        ) from None
    benchmark = integration["benchmark"]
    if benchmark["provenance_class"] not in EXTERNAL_PROVENANCE:
        _refuse(
            f"lane {validated['lane_id']}: benchmark integration {integration['integration_id']} is "
            f"{benchmark['provenance_class']}, not an external harness"
        )
    if benchmark["source_revision"] != validated["harness"]["revision"]:
        _refuse(
            f"lane {validated['lane_id']}: harness revision {validated['harness']['revision']} differs from "
            f"the integration's source_revision {benchmark['source_revision']}"
        )
    known = integration["input_contract"].get("known_input_sha256")
    if known is not None and known != validated["dataset"]["input_sha256"]:
        _refuse(
            f"lane {validated['lane_id']}: dataset.input_sha256 differs from the integration's known_input_sha256"
        )
    return {
        "lane_id": validated["lane_id"],
        "integration_id": integration["integration_id"],
        "provenance_class": benchmark["provenance_class"],
        "harness_revision": validated["harness"]["revision"],
        "input_sha256": validated["dataset"]["input_sha256"],
        "status": validated["status"],
        "lane_digest_sha256": lane_digest(validated),
        "rows": [
            {"row_id": row["row_id"], "system_id": row["system_id"], "role": row["role"], "status": row["status"]}
            for row in validated["systems"]
        ],
        "authority_effect": "none",
    }


__all__ = [
    "CONTRACT_FAMILY",
    "CONTRACT_VERSION",
    "SameHarnessLaneError",
    "contract_version_compatible",
    "validate_lane",
    "canonical_lane_bytes",
    "lane_digest",
    "load_lane",
    "lane_paths",
    "list_lanes",
    "get_lane",
    "resolve_lane",
]
