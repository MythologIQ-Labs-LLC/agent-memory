"""Experimental host-owned scope-distinct logical memory interface (#786).

This is an explicit NEW-STORE candidate, not the default public facade
contract or an in-place legacy state migration. The host exclusively exposes
this surface to untrusted callers; arbitrary access to AgentMemory.open or
direct adapter proposals bypasses the boundary.

No new PAMA authority: write, correction and deletion still use AgentMemory.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

from .surface import AgentMemory

_NAMESPACE = "scope-key-v1:"
_MAX_KEY_LENGTH = 512


def scope_distinct_key(tenant: str, scope: str, public_key: str) -> str:
    """Stable tenant/project/key tuple identity without raw key disclosure.

    Collision protection derives from tuple separation plus SHA256, not from a
    secret or access token. It does NOT authorize reads or writes by itself.
    """
    for label, value in (
        ("tenant", tenant), ("scope", scope), ("public_key", public_key),
    ):
        if (
            not isinstance(value, str) or not value or value != value.strip()
            or unicodedata.normalize("NFC", value) != value
        ):
            raise ValueError(f"{label} must be a nonempty NFC canonical string")
    if len(public_key) > _MAX_KEY_LENGTH:
        raise ValueError("public_key is too long")
    if public_key.startswith(_NAMESPACE):
        raise ValueError("public_key uses a reserved internal prefix")
    encoded = json.dumps(
        [tenant, scope, public_key], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return _NAMESPACE + hashlib.sha256(encoded).hexdigest()


class ScopeDistinctMemory:
    """Bounded current-head consumer for a host-owned project scope.

    New dedicated store only. Do not mix it with legacy direct-key consumers.
    Key allocation is not security isolation if raw AgentMemory handles are
    exposed to the same untrusted principal.
    """

    def __init__(self, memory: AgentMemory, *, tenant: str, scope: str, actor_id: str):
        if (
            getattr(memory, "tenant", None) != tenant
            or getattr(memory, "scope", None) != scope
            or getattr(memory, "actor_id", None) != actor_id
        ):
            raise ValueError("backing memory identity does not match trusted host binding")
        self._memory = memory
        self._tenant = tenant
        self._scope = scope
        self._actor_id = actor_id

    @classmethod
    def open(
        cls, path, *, tenant: str, actor_id: str, scope: str, purpose: str = "scope-bound memory"
    ) -> "ScopeDistinctMemory":
        # The caller running this constructor is the trusted host. The model
        # must not select tenant/scope/actor per memory operation.
        memory = AgentMemory.open(
            path, tenant=tenant, actor_id=actor_id, scope=scope, purpose=purpose
        )
        try:
            return cls(memory, tenant=tenant, scope=scope, actor_id=actor_id)
        except BaseException:
            memory.close()
            raise

    def __enter__(self) -> "ScopeDistinctMemory":
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def close(self) -> None:
        self._memory.close()

    def _key(self, public_key: str) -> str:
        if (
            getattr(self._memory, "closed", False)
            or getattr(self._memory, "tenant", None) != self._tenant
            or getattr(self._memory, "scope", None) != self._scope
            or getattr(self._memory, "actor_id", None) != self._actor_id
        ):
            raise RuntimeError("host-bound memory is closed or identity changed")
        return scope_distinct_key(self._tenant, self._scope, public_key)

    @staticmethod
    def _outcome(result: dict) -> dict:
        committed = result.get("committed") is True
        status = result.get("outcome")
        return {
            "committed": committed,
            "fact_ref": result.get("fact_uuid") if committed else None,
            "status": status if isinstance(status, str) else "not_committed",
            "review_required": status in ("require_review", "require_external_verification")
            if not committed else False,
            "authoritative_answer": False,
        }

    def remember(self, public_key: str, text: str) -> dict:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be nonempty")
        return self._outcome(self._memory.remember(self._key(public_key), text))

    def history(self, public_key: str) -> dict:
        state = self._memory.history(self._key(public_key)).get("history", {})
        if not isinstance(state, dict):
            raise RuntimeError("invalid governed history result")
        # Projected public answer, never expose the internal canonical target,
        # audit events, raw graph paths, or other scopes' diagnostics.
        return {
            "public_key": public_key,
            "current_fact_ref": state.get("current_fact_uuid"),
            "state_version": state.get("state_version"),
            "tombstoned": state.get("tombstoned"),
            "authoritative_answer": False,
        }

    def correct(self, public_key: str, text: str, *, evidence=(),
                replacement_kind: str = "error_correction") -> dict:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text must be nonempty")
        return self._outcome(self._memory.correct(
            self._key(public_key), text,
            evidence=evidence, replacement_kind=replacement_kind,
        ))

    def forget(self, public_key: str, *, evidence=(), permanent: bool = False) -> dict:
        if type(permanent) is not bool:
            raise ValueError("permanent must be a boolean")
        return self._outcome(self._memory.forget(
            self._key(public_key), evidence=evidence, permanent=permanent,
        ))
