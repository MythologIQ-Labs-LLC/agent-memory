"""Example embedding-host boundary for an operational Agent Memory store.

This does not authenticate callers. The host must bind tenant, actor and scope to
an authenticated principal before calling this wrapper. Legacy migration is a
separate privileged administrative operation; never expose its raw handle as a
normal consumer session.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from agentmem_ref import AgentMemory


class UnqualifiedLegacyStoreError(RuntimeError):
    """A store has not completed a provably safe #809 lineage migration."""


@contextmanager
def open_qualified_memory(path: str | Path, **host_bound_identity) -> Iterator[AgentMemory]:
    """Yield a facade only after validating its canonical derivation readiness.

    The runtime's legacy_upgrade_status is reporting, not an activation gate.
    This gate is enforced by the embedding host before any operational method
    becomes available. Older stores must be upgraded through a separate, trusted
    maintenance path that does not serve application recall or write requests.
    """
    memory = AgentMemory.open(path, **host_bound_identity)
    try:
        posture = memory.legacy_upgrade_status()
        if posture.get("status") not in ("fresh", "legacy_qualified"):
            raise UnqualifiedLegacyStoreError(
                "Agent Memory activation refused: legacy derivation state is not qualified"
            )
        yield memory
    finally:
        memory.close()
