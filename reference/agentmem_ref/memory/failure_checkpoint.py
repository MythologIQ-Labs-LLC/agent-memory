"""Restart-safe owner checkpoint for native governed failure memory.

The generic ``FailureMemory`` runtime keeps its revision index process-local.
This module provides the bounded restart-safe specialization used when a host
explicitly composes failure memory through ``ComposedRestartSafeRuntime``.

The checkpoint is owner state, not a second persistence system. Governed facts,
tombstones, receipts, and substrate state remain owned by the existing runtime
checkpoint. This owner snapshot binds only the failure-memory lineage and the
fact-to-logical-object mapping required to interpret that durable state after
recovery.
"""

from __future__ import annotations

from typing import Mapping

from .failure_memory import (
    FailureMemory,
    FailureMemoryError,
    FailureRevision,
    FailureScope,
)


FAILURE_CHECKPOINT_SCHEMA_VERSION = "1.0.0"
FAILURE_AUXILIARY_COMPONENT_ID = "negative_failure_memory"


class FailureCheckpointError(FailureMemoryError):
    """Persisted failure-memory owner state cannot be reconstructed safely."""


def _scope_to_dict(scope: FailureScope) -> dict:
    return {
        "scope": scope.scope,
        "isolation_domain_refs": list(scope.isolation_domain_refs),
        "required_isolation_domain_refs": list(scope.required_isolation_domain_refs),
        "project_ref": scope.project_ref,
        "task_ref": scope.task_ref,
        "purpose": scope.purpose,
    }


def _scope_from_dict(value: object) -> FailureScope:
    if not isinstance(value, Mapping):
        raise FailureCheckpointError("failure checkpoint scope must be a mapping")
    expected = {
        "scope",
        "isolation_domain_refs",
        "required_isolation_domain_refs",
        "project_ref",
        "task_ref",
        "purpose",
    }
    if set(value) != expected:
        raise FailureCheckpointError("failure checkpoint scope shape changed")
    return FailureScope(
        scope=_required_str(value, "scope"),
        isolation_domain_refs=_string_tuple(value, "isolation_domain_refs"),
        required_isolation_domain_refs=_string_tuple(
            value, "required_isolation_domain_refs"
        ),
        project_ref=_optional_str(value, "project_ref"),
        task_ref=_optional_str(value, "task_ref"),
        purpose=_required_str(value, "purpose"),
    )


def _revision_to_dict(revision: FailureRevision) -> dict:
    return {
        "failure_ref": revision.failure_ref,
        "revision_ref": revision.revision_ref,
        "action_class": revision.action_class,
        "summary": revision.summary,
        "category": revision.category,
        "causal_status": revision.causal_status,
        "scope": _scope_to_dict(revision.scope),
        "source_component": revision.source_component,
        "observed_at": revision.observed_at,
        "expected_outcome": revision.expected_outcome,
        "actual_outcome": revision.actual_outcome,
        "severity_label": revision.severity_label,
        "impact_score": revision.impact_score,
        "root_cause_candidates": list(revision.root_cause_candidates),
        "mitigation": revision.mitigation,
        "verification_evidence_refs": list(revision.verification_evidence_refs),
        "applicability_conditions": list(revision.applicability_conditions),
        "source_evidence_refs": list(revision.source_evidence_refs),
        "recurrence_evidence_refs": list(revision.recurrence_evidence_refs),
        "similarity_score": revision.similarity_score,
        "prior_revision_ref": revision.prior_revision_ref,
        "revision_reason": revision.revision_reason,
        "memory_status": revision.memory_status,
        "estimator_ref": revision.estimator_ref,
        "estimator_version": revision.estimator_version,
    }


def _revision_from_dict(value: object) -> FailureRevision:
    if not isinstance(value, Mapping):
        raise FailureCheckpointError("failure checkpoint revision must be a mapping")
    expected = {
        "failure_ref",
        "revision_ref",
        "action_class",
        "summary",
        "category",
        "causal_status",
        "scope",
        "source_component",
        "observed_at",
        "expected_outcome",
        "actual_outcome",
        "severity_label",
        "impact_score",
        "root_cause_candidates",
        "mitigation",
        "verification_evidence_refs",
        "applicability_conditions",
        "source_evidence_refs",
        "recurrence_evidence_refs",
        "similarity_score",
        "prior_revision_ref",
        "revision_reason",
        "memory_status",
        "estimator_ref",
        "estimator_version",
    }
    if set(value) != expected:
        raise FailureCheckpointError("failure checkpoint revision shape changed")
    return FailureRevision(
        failure_ref=_required_str(value, "failure_ref"),
        revision_ref=_required_str(value, "revision_ref"),
        action_class=_required_str(value, "action_class"),
        summary=_optional_str(value, "summary"),
        category=_required_str(value, "category"),
        causal_status=_required_str(value, "causal_status"),
        scope=_scope_from_dict(value["scope"]),
        source_component=_required_str(value, "source_component"),
        observed_at=_required_str(value, "observed_at"),
        expected_outcome=_optional_str(value, "expected_outcome"),
        actual_outcome=_optional_str(value, "actual_outcome"),
        severity_label=_required_str(value, "severity_label"),
        impact_score=_optional_score(value, "impact_score"),
        root_cause_candidates=_string_tuple(value, "root_cause_candidates"),
        mitigation=_optional_str(value, "mitigation"),
        verification_evidence_refs=_string_tuple(
            value, "verification_evidence_refs"
        ),
        applicability_conditions=_string_tuple(value, "applicability_conditions"),
        source_evidence_refs=_string_tuple(value, "source_evidence_refs"),
        recurrence_evidence_refs=_string_tuple(value, "recurrence_evidence_refs"),
        similarity_score=_optional_score(value, "similarity_score"),
        prior_revision_ref=_optional_str(value, "prior_revision_ref"),
        revision_reason=_optional_str(value, "revision_reason"),
        memory_status=_required_str(value, "memory_status"),
        estimator_ref=_optional_str(value, "estimator_ref"),
        estimator_version=_optional_str(value, "estimator_version"),
    )


def _required_str(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise FailureCheckpointError(f"failure checkpoint {key} must be non-empty text")
    return item


def _optional_str(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str):
        raise FailureCheckpointError(f"failure checkpoint {key} must be text")
    return item


def _string_tuple(value: Mapping[str, object], key: str) -> tuple[str, ...]:
    item = value.get(key)
    if not isinstance(item, list) or any(not isinstance(part, str) for part in item):
        raise FailureCheckpointError(
            f"failure checkpoint {key} must be a list of strings"
        )
    return tuple(item)


def _optional_score(value: Mapping[str, object], key: str) -> float | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, (int, float)):
        raise FailureCheckpointError(
            f"failure checkpoint {key} must be null or numeric"
        )
    return float(item)


class CheckpointedFailureMemory(FailureMemory):
    """Failure memory with explicit owner snapshot and fail-closed recovery."""

    def export_checkpoint_state(self) -> dict:
        if self.recall_policy is not None:
            raise FailureCheckpointError(
                "checkpointed failure reference currently supports only the default recall policy"
            )
        return {
            "schema_version": FAILURE_CHECKPOINT_SCHEMA_VERSION,
            "history": {
                failure_ref: [_revision_to_dict(item) for item in revisions]
                for failure_ref, revisions in sorted(self._history.items())
            },
            "fact_by_revision": dict(sorted(self._fact_by_revision.items())),
            "object_by_fact": dict(sorted(self._mesh._object_by_fact.items())),
        }

    def restore_checkpoint_state(self, snapshot: Mapping[str, object]) -> None:
        expected = {
            "schema_version",
            "history",
            "fact_by_revision",
            "object_by_fact",
        }
        if not isinstance(snapshot, Mapping) or set(snapshot) != expected:
            raise FailureCheckpointError("failure checkpoint envelope shape changed")
        if snapshot.get("schema_version") != FAILURE_CHECKPOINT_SCHEMA_VERSION:
            raise FailureCheckpointError("unsupported failure checkpoint schema")

        raw_history = snapshot.get("history")
        raw_fact_by_revision = snapshot.get("fact_by_revision")
        raw_object_by_fact = snapshot.get("object_by_fact")
        if not isinstance(raw_history, Mapping):
            raise FailureCheckpointError("failure checkpoint history must be a mapping")
        if not isinstance(raw_fact_by_revision, Mapping):
            raise FailureCheckpointError(
                "failure checkpoint fact_by_revision must be a mapping"
            )
        if not isinstance(raw_object_by_fact, Mapping):
            raise FailureCheckpointError(
                "failure checkpoint object_by_fact must be a mapping"
            )

        rebuilt_history: dict[str, list[FailureRevision]] = {}
        known_revisions: dict[str, FailureRevision] = {}
        for failure_ref in sorted(raw_history):
            if not isinstance(failure_ref, str) or not failure_ref:
                raise FailureCheckpointError("failure checkpoint has invalid failure_ref")
            rows = raw_history[failure_ref]
            if not isinstance(rows, list) or not rows:
                raise FailureCheckpointError(
                    "failure checkpoint history rows must be non-empty lists"
                )
            revisions: list[FailureRevision] = []
            previous_ref = ""
            base_scope = None
            base_action_class = ""
            for index, row in enumerate(rows):
                revision = _revision_from_dict(row)
                if revision.failure_ref != failure_ref:
                    raise FailureCheckpointError(
                        "failure checkpoint history key does not match revision identity"
                    )
                if revision.revision_ref in known_revisions:
                    raise FailureCheckpointError(
                        "failure checkpoint contains duplicate revision identity"
                    )
                if index == 0:
                    if revision.prior_revision_ref:
                        raise FailureCheckpointError(
                            "initial restored failure revision names a prior revision"
                        )
                    base_scope = revision.scope
                    base_action_class = revision.action_class
                else:
                    if revision.prior_revision_ref != previous_ref:
                        raise FailureCheckpointError(
                            "restored failure lineage is not append-only"
                        )
                    if revision.scope != base_scope:
                        raise FailureCheckpointError(
                            "restored failure lineage changes governed scope"
                        )
                    if revision.action_class != base_action_class:
                        raise FailureCheckpointError(
                            "restored failure lineage changes action-class identity"
                        )
                known_revisions[revision.revision_ref] = revision
                revisions.append(revision)
                previous_ref = revision.revision_ref
            rebuilt_history[failure_ref] = revisions

        rebuilt_fact_by_revision: dict[str, str] = {}
        for revision_ref, fact_uuid in raw_fact_by_revision.items():
            if not isinstance(revision_ref, str) or revision_ref not in known_revisions:
                raise FailureCheckpointError(
                    "failure checkpoint fact mapping names an unknown revision"
                )
            if not isinstance(fact_uuid, str) or not fact_uuid:
                raise FailureCheckpointError(
                    "failure checkpoint fact mapping has invalid fact UUID"
                )
            if known_revisions[revision_ref].memory_status == "retracted":
                raise FailureCheckpointError(
                    "retracted failure revision cannot own a replacement fact"
                )
            if self.adapter._substrate.get_fact(fact_uuid) is None:
                raise FailureCheckpointError(
                    "failure checkpoint references a fact absent from durable substrate"
                )
            rebuilt_fact_by_revision[revision_ref] = fact_uuid

        expected_fact_revisions = {
            revision.revision_ref
            for revisions in rebuilt_history.values()
            for revision in revisions
            if revision.memory_status != "retracted"
        }
        if set(rebuilt_fact_by_revision) != expected_fact_revisions:
            raise FailureCheckpointError(
                "failure checkpoint fact mappings do not cover every committed non-retracted revision"
            )

        rebuilt_object_by_fact: dict[str, str] = {}
        fact_values = set(rebuilt_fact_by_revision.values())
        for fact_uuid, failure_ref in raw_object_by_fact.items():
            if not isinstance(fact_uuid, str) or fact_uuid not in fact_values:
                raise FailureCheckpointError(
                    "failure checkpoint object map names an unknown owned fact"
                )
            if not isinstance(failure_ref, str) or failure_ref not in rebuilt_history:
                raise FailureCheckpointError(
                    "failure checkpoint object map names an unknown failure"
                )
            revision_refs = [
                revision.revision_ref
                for revision in rebuilt_history[failure_ref]
                if revision.memory_status != "retracted"
            ]
            owned_facts = {
                rebuilt_fact_by_revision[revision_ref]
                for revision_ref in revision_refs
            }
            if fact_uuid not in owned_facts:
                raise FailureCheckpointError(
                    "failure checkpoint object map crosses logical failure identity"
                )
            rebuilt_object_by_fact[fact_uuid] = failure_ref

        if set(rebuilt_object_by_fact) != fact_values:
            raise FailureCheckpointError(
                "failure checkpoint object map does not cover every owned fact"
            )

        self._history = rebuilt_history
        self._fact_by_revision = rebuilt_fact_by_revision
        self._mesh._object_by_fact = rebuilt_object_by_fact
