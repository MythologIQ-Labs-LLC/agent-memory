"""Execution/orchestration shell for Agent Memory Gauntlet (#558).

The orchestrator coordinates capability negotiation, transport invocation, evidence
persistence, and common Memory Evaluation normalization. It never grants memory authority
and does not import the Agent Memory runtime.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .contract import DIMENSIONS, dimension_report, metric_observation, validate_run, write_run
from .gauntlet_contract import (
    GauntletContractError,
    manifest_digest,
    negotiate_capabilities,
    validate_manifest,
)
from .gauntlet_probe import FIXTURE_SHA256
from .gauntlet_profiles import get_gauntlet_profile
from .gauntlet_transport import AdapterSession, GauntletExecutionError

QUALIFICATION_VERSION = "0.1.0"
_ALLOWED_COMMON_KINDS = {"no_memory", "lexical", "vector", "agent_memory", "external_memory", "other"}


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _write_json(path: Path, value: Mapping[str, Any]) -> str:
    payload = _canonical_json_bytes(value)
    digest = hashlib.sha256(payload).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
    return digest


def _load_json(path: str | Path) -> dict[str, Any]:
    location = Path(path)
    try:
        value = json.loads(location.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GauntletContractError(f"unable to load adapter manifest {location}: {exc}") from exc
    if not isinstance(value, dict):
        raise GauntletContractError("adapter manifest root must be a JSON object")
    return validate_manifest(value)


def _load_profile_runner(path: str):
    module_name, separator, attribute = path.partition(":")
    if not separator:
        raise GauntletExecutionError("benchmark_adapter", "invalid_runner", f"invalid profile runner: {path}")
    try:
        module = importlib.import_module(module_name)
        runner = getattr(module, attribute)
    except (ImportError, AttributeError) as exc:
        raise GauntletExecutionError(
            "benchmark_adapter", "runner_unavailable", f"unable to load profile runner {path}: {exc}"
        ) from exc
    if not callable(runner):
        raise GauntletExecutionError(
            "benchmark_adapter", "runner_not_callable", f"profile runner is not callable: {path}"
        )
    return runner


def load_adapter_manifest(path: str | Path) -> dict[str, Any]:
    """Load and validate one adapter manifest without executing it."""

    return _load_json(path)


def _common_system(manifest: Mapping[str, Any]) -> dict[str, Any]:
    system = manifest["system"]
    kind = str(system["kind"])
    common_kind = kind if kind in _ALLOWED_COMMON_KINDS else "external_memory"
    result: dict[str, Any] = {
        "id": system["id"],
        "kind": common_kind,
        "revision": system["revision"],
        "adapter_id": manifest["adapter"]["id"],
        "adapter_revision": manifest["adapter"]["revision"],
    }
    configuration_digest = system.get("configuration_digest")
    if isinstance(configuration_digest, str):
        result["configuration_digest"] = configuration_digest.removeprefix("sha256:")
    return result


def _dimensions_for_success(native: Mapping[str, Any], manifest_sha: str) -> dict[str, Any]:
    dimensions = {dimension: dimension_report("not_applicable") for dimension in DIMENSIONS}
    dimensions["retrieval"] = dimension_report(
        "measured",
        [
            metric_observation(
                "exact_top1",
                value=float(native["exact_top1"]),
                direction="higher_better",
                denominator=int(native["sample_count"]),
                unit="fraction",
                population="gauntlet orchestration probe queries",
                note="baseline_or_probe metric; not independent efficacy evidence",
            )
        ],
    )
    dimensions["governance"] = dimension_report(
        "not_measured",
        notes=["This orchestration probe does not exercise governance claims."],
    )
    dimensions["efficiency"] = dimension_report(
        "measured",
        [
            metric_observation(
                "run_elapsed_ms",
                value=float(native["elapsed_ms"]),
                direction="lower_better",
                unit="ms",
                population="one orchestration probe run",
            ),
            metric_observation(
                "operation_elapsed_ms_p50",
                value=float(native["operation_elapsed_ms_p50"]),
                direction="lower_better",
                unit="ms",
                population="adapter-reported operation timings",
            ),
        ],
    )
    dimensions["evaluator_integrity"] = dimension_report(
        "measured",
        [
            metric_observation(
                "operation_contract_valid_rate",
                value=1.0,
                direction="higher_better",
                denominator=int(native["operation_count"]),
                unit="fraction",
                population="operation responses",
                note="every response crossed the operation-envelope validator",
            )
        ],
    )
    dimensions["reproducibility"] = dimension_report(
        "measured",
        [
            metric_observation(
                "fixture_sha256",
                value=FIXTURE_SHA256,
                direction="descriptive",
                population="probe fixture",
            ),
            metric_observation(
                "adapter_manifest_sha256",
                value=manifest_sha,
                direction="descriptive",
                population="validated adapter manifest",
            ),
        ],
    )
    return dimensions


def _dimensions_for_blocked(manifest_sha: str) -> dict[str, Any]:
    dimensions = {dimension: dimension_report("blocked") for dimension in DIMENSIONS}
    dimensions["reproducibility"] = dimension_report(
        "measured",
        [
            metric_observation(
                "fixture_sha256",
                value=FIXTURE_SHA256,
                direction="descriptive",
                population="probe fixture",
            ),
            metric_observation(
                "adapter_manifest_sha256",
                value=manifest_sha,
                direction="descriptive",
                population="validated adapter manifest",
            ),
        ],
        notes=["Execution was blocked, but frozen input and manifest identity remain reconstructable."],
    )
    return dimensions


def _normalized_run(
    *,
    run_id: str,
    manifest: Mapping[str, Any],
    manifest_sha: str,
    profile_id: str,
    started_at: str,
    elapsed_ms: float,
    native_results: Mapping[str, Any],
    native_artifact: Mapping[str, Any] | None,
    status: str,
    failure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if status == "complete":
        dimensions = _dimensions_for_success(native_results, manifest_sha)
        limitations = [
            "This is baseline_or_probe evidence for Gauntlet orchestration, not an independent memory-quality benchmark.",
            "Only three deterministic retrieval queries are exercised.",
        ]
    else:
        dimensions = _dimensions_for_blocked(manifest_sha)
        limitations = [
            "Execution did not complete; blocked evidence must not be treated as a zero score.",
        ]
    if failure:
        limitations.append(
            f"Failure attribution: {failure.get('source')} / {failure.get('code')}: {failure.get('message')}"
        )

    artifacts = []
    if native_artifact is not None:
        artifacts.append(dict(native_artifact))

    document = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "status": status,
        "benchmark": {
            "id": "agent-memory-gauntlet-orchestration-probe",
            "source_revision": "1.0.0",
            "dataset_id": "gauntlet-orchestration-probe-fixture",
            "dataset_revision": "1.0.0",
            "input_sha256": FIXTURE_SHA256,
            "task_profile": profile_id,
        },
        "system": _common_system(manifest),
        "execution": {
            "selection_id": f"all:{FIXTURE_SHA256[:16]}",
            "selection_method": "full deterministic fixture",
            "sample_count": 3,
            "started_at": started_at,
            "elapsed_ms": elapsed_ms,
            "environment": {
                "python": platform.python_version(),
                "platform": sys.platform,
            },
            "seed": "none",
        },
        "dimensions": dimensions,
        "native_results": dict(native_results),
        "limitations": limitations,
        "artifacts": artifacts,
        "authority_effect": "none",
    }
    return validate_run(document)


def _qualification_base(
    *,
    run_id: str,
    profile: Mapping[str, Any],
    manifest: Mapping[str, Any],
    manifest_sha: str,
    negotiation: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": QUALIFICATION_VERSION,
        "run_id": run_id,
        "profile": {
            "profile_id": profile["profile_id"],
            "kind": profile["kind"],
            "description": profile["description"],
        },
        "system": {
            "id": manifest["system"]["id"],
            "kind": manifest["system"]["kind"],
            "revision": manifest["system"]["revision"],
        },
        "adapter": {
            "id": manifest["adapter"]["id"],
            "version": manifest["adapter"]["version"],
            "revision": manifest["adapter"]["revision"],
            "transport": manifest["transport"]["kind"],
        },
        "manifest_digest_sha256": manifest_sha,
        "negotiation": dict(negotiation),
        "authority_effect": "none",
    }


def run_gauntlet(
    manifest_path: str | Path,
    profile_id: str,
    *,
    output_dir: str | Path,
    allow_external_process: bool = False,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Run one qualified Gauntlet profile and persist reconstructable evidence."""

    manifest = load_adapter_manifest(manifest_path)
    profile = get_gauntlet_profile(profile_id)
    negotiation = negotiate_capabilities(manifest, profile["requirements"])
    manifest_sha = manifest_digest(manifest)
    run_id = f"gauntlet-{profile_id}-{manifest['system']['id']}-{uuid.uuid4().hex[:12]}"
    run_root = Path(output_dir) / run_id
    qualification = _qualification_base(
        run_id=run_id,
        profile=profile,
        manifest=manifest,
        manifest_sha=manifest_sha,
        negotiation=negotiation,
    )

    manifest_path_out = run_root / "adapter-manifest.json"
    manifest_artifact_sha = _write_json(manifest_path_out, manifest)

    qualification["artifacts"] = {
        "adapter_manifest": {
            "path": str(manifest_path_out),
            "sha256": manifest_artifact_sha,
        }
    }

    if negotiation["outcome"] not in {"eligible", "eligible_with_limitations"}:
        qualification["status"] = negotiation["outcome"]
        qualification["coverage"] = {
            dimension: ("unsupported" if negotiation["outcome"] == "unsupported" else "blocked")
            for dimension in profile["dimensions"]
        }
        qualification_path = run_root / "qualification.json"
        qualification_sha = _write_json(qualification_path, qualification)
        qualification["artifacts"]["qualification"] = {
            "path": str(qualification_path),
            "sha256": qualification_sha,
        }
        return qualification

    isolation = manifest.get("benchmark_isolation")
    if not isinstance(isolation, Mapping) or isolation.get("strategy") != "disposable_instance":
        failure = {
            "source": "orchestrator",
            "code": "unproven_destructive_isolation",
            "message": (
                "this alpha profile invokes reset and therefore requires "
                "benchmark_isolation.strategy=disposable_instance"
            ),
        }
        qualification["status"] = "blocked"
        qualification["failure"] = failure
        qualification["coverage"] = {dimension: "blocked" for dimension in profile["dimensions"]}
        qualification_path = run_root / "qualification.json"
        qualification_sha = _write_json(qualification_path, qualification)
        qualification["artifacts"]["qualification"] = {
            "path": str(qualification_path),
            "sha256": qualification_sha,
        }
        return qualification

    started_wall = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    started = time.perf_counter()
    native: dict[str, Any]
    failure: dict[str, Any] | None = None
    normalized_status = "complete"

    try:
        runner = _load_profile_runner(profile["runner"])
        with AdapterSession(
            manifest,
            allow_external_process=allow_external_process,
            timeout_seconds=timeout_seconds,
        ) as session:
            try:
                native = runner(session, run_id=run_id, namespace=run_id)
            except GauntletExecutionError:
                raise
            except Exception as exc:
                raise GauntletExecutionError(
                    "benchmark_adapter",
                    "runner_exception",
                    f"profile runner raised {type(exc).__name__}: {exc}",
                ) from exc
    except GauntletExecutionError as exc:
        normalized_status = "blocked"
        failure = {"source": exc.source, "code": exc.code, "message": str(exc)}
        native = {
            "profile_kind": profile["kind"],
            "fixture_sha256": FIXTURE_SHA256,
            "failure": failure,
            "authority_effect": "none",
        }

    elapsed_ms = max(0.0, (time.perf_counter() - started) * 1000.0)
    native_path = run_root / "native-results.json"
    native_sha = _write_json(native_path, native)
    native_artifact = {
        "artifact_id": "gauntlet-native-results",
        "kind": "benchmark_native_results",
        "uri": str(native_path),
        "sha256": native_sha,
    }

    normalized = _normalized_run(
        run_id=run_id,
        manifest=manifest,
        manifest_sha=manifest_sha,
        profile_id=profile_id,
        started_at=started_wall,
        elapsed_ms=elapsed_ms,
        native_results=native,
        native_artifact=native_artifact,
        status=normalized_status,
        failure=failure,
    )
    normalized_path = run_root / "normalized-run.json"
    normalized_sha = write_run(normalized_path, normalized)

    qualification["status"] = "complete" if normalized_status == "complete" else "blocked"
    qualification["coverage"] = {
        dimension: normalized["dimensions"][dimension]["status"] for dimension in DIMENSIONS
    }
    if failure:
        qualification["failure"] = failure
    qualification["artifacts"].update(
        {
            "native_results": {"path": str(native_path), "sha256": native_sha},
            "normalized_run": {"path": str(normalized_path), "sha256": normalized_sha},
        }
    )
    qualification_path = run_root / "qualification.json"
    qualification_sha = _write_json(qualification_path, qualification)
    qualification["artifacts"]["qualification"] = {
        "path": str(qualification_path),
        "sha256": qualification_sha,
    }
    return qualification


__all__ = ["QUALIFICATION_VERSION", "load_adapter_manifest", "run_gauntlet"]
