"""Public contract 2.0.0 candidate (#786): unaccepted, isolated from the qualified runtime.

This module is deliberately outside ``reference/agentmem_ref`` (the protected runtime
surface) and nothing in the runtime imports it. ``agentmem_ref.api.contract.CONTRACT_VERSION``
stays ``1.6.0`` until an owner explicitly approves promotion; promotion would then be a
Runtime Baseline identity delta (``identity.public_contract_version`` 1.6.0 -> 2.0.0) and an
amendment of the open v7 declaration.

Why a major version: under #786 store identity profiles a new store binds to one project and
opening it for another project is refused; multi-project use must create a
``scope_distinct_v1`` store, whose canonical keys differ from the public keys. A 1.x
consumer that opened one root for several projects now fails at open. That is a breaking
change to the facade's open contract even though no envelope schema changed.

ADR-030 consequence (measured in the tests): every 1.x envelope is ``incompatible`` against
2.0.0, not only the open-time default. That is the cost the owner decision must weigh.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

CANDIDATE_VERSION = "2.0.0"
PREDECESSOR_VERSION = "1.6.0"
STATUS = (
    "unaccepted candidate: not wired into agentmem_ref.api.contract; promotion requires explicit owner "
    "approval, a v7 identity delta and a migration window decision"
)
RECORD = Path(__file__).with_name("public_contract_v2_candidate.json")

CURRENT = "current"
MIGRATION_REQUIRED = "migration_required"
INCOMPATIBLE = "incompatible"
UNKNOWN = "unknown"


def compatibility(envelope: Mapping[str, Any]) -> str:
    """ADR-030's four states for an envelope against the 2.0.0 candidate."""
    raw = envelope.get("contract_version") if isinstance(envelope, Mapping) else None
    try:
        major, minor, _patch = (int(part) for part in str(raw).split("."))
    except (ValueError, AttributeError, TypeError):
        return UNKNOWN
    ours = tuple(int(part) for part in CANDIDATE_VERSION.split("."))
    if major != ours[0]:
        return INCOMPATIBLE
    if minor > ours[1]:
        return MIGRATION_REQUIRED
    return CURRENT


def classify_existing_store(record: Mapping[str, Any] | None, canonical_projects: set[str]) -> str:
    """How an existing store opens under 2.0.0. Never a migration; a classification only."""
    if record is not None:
        return str(record["profile"])
    if len(canonical_projects) <= 1:
        return "legacy_unprofiled_single_project_restricted"
    return "legacy_unprofiled_multi_project_requires_governed_migration"


def load_record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8"))
