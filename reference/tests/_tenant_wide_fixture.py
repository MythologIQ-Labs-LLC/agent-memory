"""Canonical-gate fixture: one tenant-wide store driven by several projects (#786).

No public opener can produce this configuration any more. ``AgentMemory.open`` binds a
new store to one project (``single_project_v1``) unless it is ``scope_distinct_v1``,
and a pre-profile store opens only for the single project it already contains.

The canonical adapter still guards writes, corrections, deletion, disputes and recall
against foreign projects as defense in depth, because hosts and runtimes below the
facade (the trusted proposal layer, procedural memory, direct adapter consumers) do
not pass through store profiles. Tests that must keep executable evidence for those
canonical guards use this fixture: it reproduces a pre-profile tenant-wide store and
constructs per-project facade handles directly, exactly as a host would have to do
deliberately. It is a test construction, not a supported deployment.
"""
from __future__ import annotations

from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.api.surface import STORE_PROFILE_FILE, STORE_PROFILE_LEGACY
from agentmem_ref.runtime import doctor
from agentmem_ref.runtime.runtime_behavior import validate_runtime_behavior_contract
from agentmem_ref.runtime.sqlite_composition import SQLiteConfiguredCompositionRuntime

_DATABASE = "agent-memory.sqlite3"
_CONFIG = "runtime-config.json"


def open_tenant_wide(
    root,
    *,
    tenant: str,
    actor_id: str,
    scope: str,
    purpose: str = "local memory",
    charter_version: str = "charter:local-v1",
    task_ref: str = "",
    verifier_registry=None,
) -> AgentMemory:
    """Open ``scope``'s handle on a tenant-wide multi-project store (test-only)."""
    root = Path(root)
    if not (root / _DATABASE).exists():
        AgentMemory.open(root, tenant=tenant, actor_id=actor_id, scope=scope, purpose=purpose,
                         charter_version=charter_version, verifier_registry=verifier_registry).close()
        (root / STORE_PROFILE_FILE).unlink()  # a store written before profiles existed
    value = doctor.load_configuration_value(root / _CONFIG)
    plan = validate_runtime_behavior_contract(value, qualification_bindings=doctor.load_qualification_bindings(None))
    runtime = SQLiteConfiguredCompositionRuntime.recover(root, plan=plan, verifier_registry=verifier_registry)
    if runtime.adapter.checkpoint_tenant() != tenant:
        runtime.close()
        raise AssertionError("fixture tenant does not match the store")
    return AgentMemory(
        root=root,
        config_path=root / _CONFIG,
        qualification_path=None,
        tenant=tenant,
        actor_id=actor_id,
        charter_version=charter_version,
        scope=scope,
        purpose=purpose,
        runtime=runtime,
        task_ref=task_ref,
        store_profile=STORE_PROFILE_LEGACY,
    )
