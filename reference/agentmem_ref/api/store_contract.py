"""The store-open contract (#786): versioned separately from the public envelope contract.

``agentmem_ref.api.contract.CONTRACT_VERSION`` versions the envelopes the surface
exchanges (proposal, recall context, result, target, posture, action, observation).
Store identity profiles change what ``AgentMemory.open`` admits -- a new store binds to
one project unless it is ``scope_distinct_v1``, and a pre-profile store opens only for
the single project it already contains -- but no envelope changes. Folding that open-time
change into the envelope contract would force a major version that makes every 1.x
envelope ``incompatible`` under ADR-030 (the measured cost recorded by the isolated
2.0.0 candidate). The owner decision is instead to version the open contract on its own:

* ``STORE_OPEN_CONTRACT_VERSION`` versions store identity records, the profiles they
  name, and the open-time admission rules. It never changes an envelope's compatibility.
* ``CONTRACT_VERSION`` stays ``1.6.0``; ``1.0.0``-``1.6.0`` envelopes remain ``current``
  on every store this runtime opens.

Compatibility uses ADR-030's four states against this contract's own version. Anything
other than ``current`` refuses the open: a host or a record from a newer store-open
contract may rely on admission rules (for example a governed migration) this runtime
does not implement, so it is never opened, rewritten or silently downgraded.
"""

from __future__ import annotations

from typing import Any

STORE_OPEN_CONTRACT_ID = "agent-memory-store-open"
#: 1.0.0 (#786): identity records version 1; profiles ``single_project_v1`` (default for a
#: new store) and ``scope_distinct_v1``; unrecorded stores open as restricted
#: ``legacy_unprofiled`` stores and are never migrated implicitly.
STORE_OPEN_CONTRACT_VERSION = "1.0.0"

#: The identity-record ``version`` each store-open contract minor writes and reads.
RECORD_VERSION = 1

CURRENT = "current"
MIGRATION_REQUIRED = "migration_required"
INCOMPATIBLE = "incompatible"
UNKNOWN = "unknown"


def _parts(version: Any) -> tuple[int, int, int] | None:
    if not isinstance(version, str):
        return None
    try:
        major, minor, patch = (int(part) for part in version.split("."))
    except ValueError:
        return None
    if min(major, minor, patch) < 0:
        return None
    return major, minor, patch


def compatibility(version: Any) -> str:
    """ADR-030's four states for a declared store-open contract version."""
    parts = _parts(version)
    if parts is None:
        return UNKNOWN
    ours = _parts(STORE_OPEN_CONTRACT_VERSION)
    if parts[0] != ours[0]:
        return INCOMPATIBLE
    if parts[1] > ours[1]:
        return MIGRATION_REQUIRED
    return CURRENT


def record_compatibility(record_version: Any) -> str:
    """The state of an identity record's ``version`` field against this contract."""
    if isinstance(record_version, bool) or not isinstance(record_version, int) or record_version < 1:
        return UNKNOWN
    if record_version > RECORD_VERSION:
        return MIGRATION_REQUIRED
    return CURRENT


def describe(store_profile: str, envelope_contract_version: str) -> dict:
    """What a handle reports about the contract it was opened under; read-only, never authority."""
    return {
        "contract_id": STORE_OPEN_CONTRACT_ID,
        "contract_version": STORE_OPEN_CONTRACT_VERSION,
        "record_version": RECORD_VERSION,
        "store_profile": store_profile,
        "envelope_contract_version": envelope_contract_version,
    }
