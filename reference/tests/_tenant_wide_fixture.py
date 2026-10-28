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
from agentmem_ref.api import surface
from agentmem_ref.api.surface import STORE_PROFILE_FILE, STORE_PROFILE_LEGACY
from agentmem_ref.runtime import doctor
from agentmem_ref.runtime.runtime_behavior import validate_runtime_behavior_contract
from agentmem_ref.runtime.sqlite_composition import SQLiteConfiguredCompositionRuntime

_DATABASE = "agent-memory.sqlite3"


class HostDeclaredScopeMemory(AgentMemory):
    """A facade whose proposal ``overrides`` are the host declaring scope (contract 1.8.0, replay W4).

    Test-only. The production facade binds a handle's identity to its store (store-open 1.0.0)
    and refuses an override that changes it. The canonical adapter still judges any scope a host
    declares at the envelope layer, and the #786/#809 review suites exercise those canonical
    gates through facade overrides. This subclass restores exactly the contract 1.8.0 facade
    check (protected fields, then the malformed-scope refusal), so those suites keep testing
    the canonical adapter unchanged. ``tests/test_786_store_open_contract.py`` asserts that the
    production facade refuses the same overrides.
    """

    def _check_overrides(self, overrides):
        if not overrides:
            return
        protected = {"contract_version", "proposal_id", "actor_id", "charter_version", "state_snapshot"}
        attempted = protected.intersection(overrides)
        if attempted:
            raise ValueError(f"facade proposal overrides may not replace protected fields: {sorted(attempted)}")
        domains = overrides.get("isolation_domain_refs", self._domain_refs())
        required = overrides.get("required_isolation_domain_refs", self._domain_refs())
        if not set(required or ()).issubset(set(domains or ())):
            raise ValueError("required isolation domains must also be bound isolation domains")
_CONFIG = "runtime-config.json"


def open_tenant_wide(
    root,
    *,
    tenant: str = "tenant:local",
    actor_id: str = "agent:local",
    scope: str = "project:local",
    purpose: str = "local memory",
    charter_version: str = "charter:local-v1",
    task_ref: str = "",
    verifier_registry=None,
    recall_control: str = surface.RECALL_CONTROL_DEFAULT,
    proposition_extractor=None,
    semantic_retrieval: str = surface.SEMANTIC_RETRIEVAL_DEFAULT,
    representation_dir=None,
    config_path=None,
    qualification_path=None,
    host_declared_overrides: bool = False,
) -> AgentMemory:
    """Open ``scope``'s handle on a tenant-wide multi-project store (test-only)."""
    root = Path(root)
    if not (root / _DATABASE).exists():
        if (root / surface._WITNESS_NAME).exists():
            # #821: exactly as AgentMemory.open, a store that lost its database is never re-created.
            raise surface.RuntimeRecoveryError(
                "incomplete durable state: generation witness exists without SQLite runtime database")
        AgentMemory.open(root, tenant=tenant, actor_id=actor_id, scope=scope, purpose=purpose,
                         charter_version=charter_version, verifier_registry=verifier_registry,
                         config_path=config_path, qualification_path=qualification_path).close()
        (root / STORE_PROFILE_FILE).unlink()  # a store written before profiles existed
    config = Path(config_path) if config_path is not None else root / _CONFIG
    qualification = Path(qualification_path) if qualification_path is not None else None
    value = doctor.load_configuration_value(config)
    plan = validate_runtime_behavior_contract(value, qualification_bindings=doctor.load_qualification_bindings(qualification))
    semantic = surface._semantic_route(root, semantic_retrieval, representation_dir)
    runtime = SQLiteConfiguredCompositionRuntime.recover(
        root, plan=plan, verifier_registry=verifier_registry, vector_retriever=semantic["retriever"],
    )
    if runtime.adapter.checkpoint_tenant() != tenant:
        runtime.close()
        raise AssertionError("fixture tenant does not match the store")
    # #802: exactly as AgentMemory.open, interrupted sidecar cleanup is retried on recovery.
    try:
        reconciliation = AgentMemory._reconcile_cached_representations(root, runtime)
    except Exception as exc:  # the report, not the exception, carries it (as in AgentMemory.open)
        reconciliation = {"status": "incomplete", "stores_checked": 0, "rows_purged": 0, "stores_discarded": [],
                          "foreign": [], "unsafe": [], "failed": [[str(root / "derived"), f"{type(exc).__name__}: {exc}"]]}
    reconciliation["pending"] = []
    handle = (HostDeclaredScopeMemory if host_declared_overrides else AgentMemory)(
        root=root,
        config_path=config,
        qualification_path=qualification,
        tenant=tenant,
        actor_id=actor_id,
        charter_version=charter_version,
        scope=scope,
        purpose=purpose,
        runtime=runtime,
        task_ref=task_ref,
        semantic=semantic,
        recall_control=recall_control,
        proposition_extractor=proposition_extractor,
        store_profile=STORE_PROFILE_LEGACY,
    )
    handle._derived_reconciliation = reconciliation
    return handle


class FrozenRunnerOpener:
    """``AgentMemory`` as a frozen replay runner sees it: ``open`` reaches the tenant-wide store.

    The frozen #786/#809/#644 replay runners open several projects in one root; their bytes are
    pinned by committed manifests, so the store opener is the one name substituted. The frozen
    fixtures then execute unmodified against the canonical runtime they were written for."""

    @staticmethod
    def open(path, **kwargs):
        return open_tenant_wide(path, host_declared_overrides=True, **kwargs)


def frozen_runner_store(*runner_modules):
    """``(setUpModule, tearDownModule)`` that route each frozen runner's ``AgentMemory`` to the fixture."""
    from unittest import mock

    patchers = [mock.patch.object(module, "AgentMemory", FrozenRunnerOpener) for module in runner_modules]

    def set_up_module():
        for patcher in patchers:
            patcher.start()

    def tear_down_module():
        for patcher in reversed(patchers):
            patcher.stop()

    return set_up_module, tear_down_module
