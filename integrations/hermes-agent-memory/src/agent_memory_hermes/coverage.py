"""Coverage and doctor semantics for the pinned Hermes integration profile."""

from __future__ import annotations

from typing import Any

from . import (
    HERMES_COMMIT,
    HERMES_REPOSITORY,
    INTEGRATION_PROFILE,
    INTEGRATION_VERSION,
    MUTATION_SURFACES,
    STRICT_BLOCKERS,
)
from .config import IntegrationConfig


_INTERCEPTABLE = {
    "foreground_builtin_memory_tool",
    "foreground_skill_manage",
    "background_review_memory",
    "background_review_skill_manage",
    "curator_llm_consolidation",
}
_OBSERVED_PROVIDER = {"external_memory_provider_mirror"}


def _surface_status(surface: str, mode: str) -> str:
    if surface in _INTERCEPTABLE:
        return "intercepted" if mode in {"govern", "strict"} else "observed"
    if surface in _OBSERVED_PROVIDER:
        return "observed"
    return "uncovered"


def build_coverage_report(
    config: IntegrationConfig,
    *,
    observed_hermes_revision: str,
) -> dict[str, Any]:
    current = observed_hermes_revision == config.expected_hermes_revision == HERMES_COMMIT
    surfaces = []
    for surface in MUTATION_SURFACES:
        notes: list[str] = []
        if surface in {"background_review_memory", "background_review_skill_manage"}:
            notes.append(
                "mechanically routed through the same model tool hook, but the pinned pre_tool_call metadata does not expose Hermes _memory_write_origin"
            )
        if surface == "external_memory_provider_mirror":
            notes.append("post-commit observation only; provider callback is not built-in admission authority")
        if surface in STRICT_BLOCKERS:
            notes.append("does not traverse the normal tool executor at the pinned Hermes profile")
        surfaces.append(
            {
                "surface_id": surface,
                "status": _surface_status(surface, config.mode),
                "origin_precision": (
                    "mechanical_path_only"
                    if surface in {"background_review_memory", "background_review_skill_manage"}
                    else "surface_specific"
                ),
                "notes": notes,
            }
        )

    reasons: list[str] = []
    if config.mode == "strict":
        reasons.append("strict mode is unsupported at the pinned Hermes profile")
    if config.require_exact_profile and not current:
        reasons.append(
            "exact Hermes profile is not current: "
            f"observed={observed_hermes_revision} expected={config.expected_hermes_revision}"
        )
    if config.mode == "govern" and config.governor_required and not config.governor_command:
        reasons.append("govern mode requires a configured governor_command")

    ready = not reasons
    return {
        "schema_version": "1.0.0",
        "hermes": {
            "repository": HERMES_REPOSITORY,
            "observed_revision": observed_hermes_revision,
            "expected_revision": config.expected_hermes_revision,
            "research_pin": HERMES_COMMIT,
            "profile_current": current,
        },
        "integration": {
            "profile": INTEGRATION_PROFILE,
            "version": INTEGRATION_VERSION,
            "mode": config.mode,
            "ready": ready,
            "governor_required": config.governor_required,
            "governor_configured": bool(config.governor_command),
            "record_payloads": config.record_payloads,
        },
        "surfaces": surfaces,
        "strict": {
            "supported": False,
            "blocking_surfaces": list(STRICT_BLOCKERS),
            "reason": "six consequential durable mutation families remain outside plugin/provider interception",
        },
        "limitations": [
            "external MemoryProvider observation is post-commit and incomplete for background/approval/curator/Journey/direct-file mutation paths",
            "pre_tool_call cannot distinguish foreground from background_review origin at the pinned profile without additional Hermes metadata",
            "Agent Memory stage cannot be represented as a native staged durable mutation through the generic pre_tool_call hook",
        ],
        "reasons_not_ready": reasons,
        "authority_effect": "none",
    }
