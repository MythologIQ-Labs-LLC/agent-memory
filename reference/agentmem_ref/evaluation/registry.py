"""Registry of repository-owned benchmark integrations.

The registry is backed by committed benchmark integration descriptors
(``evaluation/integrations/*.json``) validated against
``schemas/memory-benchmark-integration.schema.json``. It does not duplicate benchmark
identities in Python. Registry metadata is descriptive only: it does not establish that
an external run has occurred, that a score is comparable, or that any benchmark result
has memory authority.

The registry also makes the relationship between benchmark integrations and Gauntlet
execution profiles explicit and mechanically checkable. The two registries describe
different things (a benchmark integration versus a system-neutral qualification
workload) and deliberately remain separate structures; this module only verifies that
their cross-references are mutual and that registration never changes evidence class.
"""

from __future__ import annotations

import importlib.resources
from copy import deepcopy
from pathlib import Path
from typing import Any

from .._paths import PACKAGE_NAME
from .benchmark_integration import (
    PROVENANCE_STRENGTH,
    BenchmarkIntegrationError,
    check_profile_binding,
    load_integration,
    resolve_native_path,
)

INTEGRATIONS_RESOURCE = "integrations"
# Gauntlet profiles that bind no benchmark integration must declare one of these kinds:
# Gauntlet-native suites and probes are never independent external evidence.
GAUNTLET_NATIVE_KINDS = {"baseline_or_probe", "gauntlet_native_gap", "agent_memory_conformance"}


def _integrations_root() -> Path:
    resource = importlib.resources.files(f"{PACKAGE_NAME}.evaluation") / INTEGRATIONS_RESOURCE
    root = Path(str(resource))
    if not root.is_dir():
        raise BenchmarkIntegrationError(f"benchmark integration directory unavailable: {root}")
    return root


def integration_paths() -> list[Path]:
    """Committed descriptor files, sorted by file name."""

    return sorted(_integrations_root().glob("*.json"))


def list_integrations() -> list[dict[str, Any]]:
    """Return every committed, validated benchmark integration descriptor."""

    descriptors = [load_integration(path) for path in integration_paths()]
    seen: set[str] = set()
    for descriptor in descriptors:
        integration_id = descriptor["integration_id"]
        if integration_id in seen:
            raise BenchmarkIntegrationError(f"duplicate benchmark integration id: {integration_id}")
        seen.add(integration_id)
    return sorted(descriptors, key=lambda item: item["integration_id"])


def get_integration(integration_id: str) -> dict[str, Any]:
    """Return one committed descriptor or raise ``KeyError``."""

    for descriptor in list_integrations():
        if descriptor["integration_id"] == integration_id:
            return descriptor
    raise KeyError(integration_id)


def _evidence_status(descriptor: dict[str, Any]) -> str:
    counts: dict[str, int] = {}
    for item in descriptor["evidence_history"]:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    if not counts:
        return "no_evidence_recorded"
    return ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))


def profile_view(descriptor: dict[str, Any]) -> dict[str, Any]:
    """Project one descriptor into the compact profile shape used by ``benchmark list``.

    The projection carries only descriptor facts. It adds nothing and upgrades nothing.
    """

    runner = descriptor["native_protocol"]["runner"]
    return {
        "profile_id": descriptor["integration_id"],
        "benchmark_id": descriptor["benchmark"]["id"],
        "provenance_class": descriptor["benchmark"]["provenance_class"],
        "admission_state": descriptor["admission_state"],
        "owning_issue": descriptor["owning_issue"],
        "runner": runner["entry_point"],
        "runner_kind": runner["kind"],
        "supporting_runners": list(runner.get("supporting_entry_points", [])),
        "invocation_surface": descriptor["system_requirements"]["invocation_surface"],
        "external_system_entry": descriptor["system_requirements"]["external_system_entry"],
        "credentials": descriptor["provider_requirements"]["credentials"],
        "external_evidence_status": _evidence_status(descriptor),
        "external_evidence": deepcopy(descriptor["evidence_history"]),
        "product_findings": deepcopy(descriptor.get("product_findings", [])),
        "dimensions": list(descriptor.get("dimensions", [])),
        "gauntlet": deepcopy(descriptor["gauntlet"]),
        "description": descriptor["description"],
        "authority_effect": "none",
    }


def list_profiles() -> list[dict[str, Any]]:
    """Return stable profile metadata sorted by profile id (descriptor projection)."""

    return [profile_view(descriptor) for descriptor in list_integrations()]


def get_profile(profile_id: str) -> dict[str, Any]:
    """Return one registered profile projection or raise ``KeyError``."""

    return profile_view(get_integration(profile_id))


def resolve_gauntlet_relationship(descriptor: dict[str, Any]) -> dict[str, Any]:
    """Resolve a descriptor's declared Gauntlet relationship against the profile registry."""

    from .gauntlet_profiles import get_gauntlet_profile

    gauntlet = descriptor["gauntlet"]
    result: dict[str, Any] = {
        "relationship": gauntlet["relationship"],
        "profile_id": gauntlet["profile_id"],
        "reason": gauntlet["reason"],
    }
    if gauntlet["relationship"] != "bound_profile":
        result["status"] = gauntlet["relationship"]
        return result
    try:
        profile = get_gauntlet_profile(gauntlet["profile_id"])
    except KeyError:
        result["status"] = "profile_missing"
        return result
    try:
        binding = check_profile_binding(profile, descriptor)
    except BenchmarkIntegrationError as exc:
        result["status"] = "binding_invalid"
        result["error"] = str(exc)
        return result
    result["status"] = "bound"
    result["profile_kind"] = binding["profile_kind"]
    return result


def validate_registry_relationships() -> dict[str, Any]:
    """Mechanically verify benchmark-integration <-> Gauntlet-profile cross-references.

    Rules:

    * a descriptor bound to a profile must name an existing profile that binds it back
      with an identical evidence class and the same runner;
    * a Gauntlet profile that binds a benchmark integration must pass the same check;
    * a Gauntlet profile that binds nothing must declare a Gauntlet-native kind; it can
      never present itself as external evidence by registration alone;
    * every profile kind must be a known provenance class.
    """

    from .gauntlet_profiles import list_gauntlet_profiles

    descriptors = {item["integration_id"]: item for item in list_integrations()}
    profiles = {item["profile_id"]: item for item in list_gauntlet_profiles()}
    bindings: list[dict[str, Any]] = []
    for descriptor in descriptors.values():
        relationship = resolve_gauntlet_relationship(descriptor)
        if relationship["status"] in {"profile_missing", "binding_invalid"}:
            raise BenchmarkIntegrationError(
                f"benchmark integration {descriptor['integration_id']}: "
                f"{relationship['status']}: {relationship.get('error', relationship['profile_id'])}"
            )
        if relationship["status"] == "bound":
            bindings.append(
                {
                    "integration_id": descriptor["integration_id"],
                    "profile_id": relationship["profile_id"],
                    "provenance_class": descriptor["benchmark"]["provenance_class"],
                }
            )
    for profile in profiles.values():
        kind = profile["kind"]
        if kind not in PROVENANCE_STRENGTH:
            raise BenchmarkIntegrationError(f"Gauntlet profile {profile['profile_id']} declares unknown kind {kind!r}")
        bound = profile.get("benchmark_integration")
        if bound is None:
            if kind not in GAUNTLET_NATIVE_KINDS:
                raise BenchmarkIntegrationError(
                    f"Gauntlet profile {profile['profile_id']} declares {kind} without a bound "
                    "benchmark integration; registration cannot create external evidence"
                )
            continue
        descriptor = descriptors.get(bound)
        if descriptor is None:
            raise BenchmarkIntegrationError(
                f"Gauntlet profile {profile['profile_id']} binds unknown benchmark integration {bound}"
            )
        check_profile_binding(profile, descriptor)
    return {
        "integration_count": len(descriptors),
        "gauntlet_profile_count": len(profiles),
        "bindings": sorted(bindings, key=lambda item: item["integration_id"]),
        "authority_effect": "none",
    }


def check_evidence_binding(descriptor: dict[str, Any], *, repo_root: Path) -> list[dict[str, Any]]:
    """Check that each executed evidence row is bound to a committed report by exact identity."""

    rows: list[dict[str, Any]] = []
    for item in descriptor["evidence_history"]:
        if item["status"] not in {"complete", "partial"}:
            continue
        path = repo_root / item["report"]
        row = {"variant": item["variant"], "report": item["report"], "bound": False}
        if not path.is_file():
            row["error"] = "report missing"
            rows.append(row)
            continue
        import json

        report = json.loads(path.read_text(encoding="utf-8"))
        binding = item["report_binding"]
        present_sha, sha = resolve_native_path(report, binding["input_sha256_path"])
        present_rev, revision = resolve_native_path(report, binding["system_revision_path"])
        if not present_sha or sha != item["input_sha256"]:
            row["error"] = f"report input digest {sha!r} != {item['input_sha256']!r}"
        elif not present_rev or revision != item["system_revision"]:
            row["error"] = f"report system revision {revision!r} != {item['system_revision']!r}"
        else:
            row["bound"] = True
        rows.append(row)
    return rows


__all__ = [
    "GAUNTLET_NATIVE_KINDS",
    "integration_paths",
    "list_integrations",
    "get_integration",
    "profile_view",
    "list_profiles",
    "get_profile",
    "resolve_gauntlet_relationship",
    "validate_registry_relationships",
    "check_evidence_binding",
]
