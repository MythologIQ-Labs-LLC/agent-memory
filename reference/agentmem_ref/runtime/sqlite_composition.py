"""Configured Agent Memory composition over the transactional SQLite profile."""

from __future__ import annotations

from pathlib import Path

from .runtime_composition import ConfiguredCompositionRuntime, RETRIEVAL_CAPABILITY
from .runtime_config import RuntimeConfigurationPlan
from .sqlite_runtime import SQLiteConfigBoundRestartRuntime


class SQLiteConfiguredCompositionRuntime(ConfiguredCompositionRuntime):
    """RC composition using SQLite as the durable canonical substrate."""

    @classmethod
    def create(
        cls,
        root: str | Path,
        *,
        tenant: str,
        plan: RuntimeConfigurationPlan,
        verifier_registry=None,
    ) -> "SQLiteConfiguredCompositionRuntime":
        durable = SQLiteConfigBoundRestartRuntime.create(
            root,
            tenant=tenant,
            plan=plan,
            verifier_registry=verifier_registry,
        )
        return cls(durable_runtime=durable, plan=plan)

    @classmethod
    def recover(
        cls,
        root: str | Path,
        *,
        plan: RuntimeConfigurationPlan,
        provider_failures=(),
        verifier_registry=None,
    ) -> "SQLiteConfiguredCompositionRuntime":
        durable = SQLiteConfigBoundRestartRuntime.recover(
            root,
            plan=plan,
            provider_failures=provider_failures,
            verifier_registry=verifier_registry,
        )
        return cls(durable_runtime=durable, plan=plan)

    def recall(self, query: str, context):
        """Persist recall decisions/audit evidence in the SQLite generation."""
        self._route_for(RETRIEVAL_CAPABILITY)
        return self.durable_runtime.run_governed_read(
            lambda: self.adapter.governed_recall(query, context)
        )

    def multi_route_recall(
        self,
        query: str,
        context,
        *,
        logical_memory_refs: tuple[str, ...] = (),
    ):
        """Persist preselected-admission decisions and audit evidence atomically."""
        self._route_for(RETRIEVAL_CAPABILITY)
        return self.durable_runtime.run_governed_read(
            lambda: self.recall_planner.recall(
                query,
                context,
                logical_memory_refs=logical_memory_refs,
            )
        )

    def close(self) -> None:
        self.durable_runtime.base.close()
