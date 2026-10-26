"""Candidate-only host-scoped AgentMemBench facade switching (#786).

One active facade handle, one shared durable store, serialized operations.
Unlike forged per-call proposal overrides, this binds each upstream user to an
actual host-created scope. It is a COMPATIBILITY CANDIDATE, not a qualification
of latency, concurrency or a frozen benchmark lane.
"""
from __future__ import annotations

from contextlib import contextmanager
import threading
from typing import Callable, Iterator, TypeVar

T = TypeVar("T")


class SerializedScopedBenchmarkHost:
    """Own the only active runtime handle and its identity transition."""

    def __init__(self, open_scope: Callable[[str], T], *, tenant: str, actor_id: str):
        if not isinstance(tenant, str) or not tenant.strip():
            raise ValueError("host tenant must be nonempty")
        if not isinstance(actor_id, str) or not actor_id.strip():
            raise ValueError("host actor_id must be nonempty")
        self._tenant = tenant
        self._actor_id = actor_id
        self._open_scope = open_scope
        self._lock = threading.RLock()
        self._active_scope: str | None = None
        self._handle: T | None = None
        self._closed = False
        self.opens = 0
        self.switches = 0

    def _matches_binding(self, handle: T | None, scope: str) -> bool:
        return (
            handle is not None
            and getattr(handle, "scope", None) == scope
            and getattr(handle, "tenant", None) == self._tenant
            and getattr(handle, "actor_id", None) == self._actor_id
        )

    @contextmanager
    def use(self, user_id: str) -> Iterator[T]:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("benchmark user_id must be nonempty")
        requested_scope = f"user:{user_id}"
        with self._lock:
            if self._closed:
                raise RuntimeError("scoped benchmark host is closed")
            if self._active_scope != requested_scope:
                previous = self._handle
                self._handle = None
                self._active_scope = None
                if previous is not None:
                    previous.close()
                    self.switches += 1
                # Failed opens leave no prior handle/caller scope eligible.
                opened = self._open_scope(requested_scope)
                # A host callback is not proof that the returned runtime is
                # bound to the requested principal/project. A wrongly bound
                # facade must never be handed to a benchmark operation.
                if not self._matches_binding(opened, requested_scope):
                    if opened is not None:
                        opened.close()
                    raise RuntimeError("opened runtime identity does not match host binding")
                self._handle = opened
                self._active_scope = requested_scope
                self.opens += 1
            # Runtime identity is checked on *every* use, not just open.
            # A tampered cached facade cannot borrow the earlier authorization.
            if not self._matches_binding(self._handle, requested_scope):
                compromised = self._handle
                self._handle = None
                self._active_scope = None
                if compromised is not None:
                    compromised.close()
                raise RuntimeError("cached runtime identity no longer matches host binding")
            assert self._handle is not None
            yield self._handle

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            old = self._handle
            self._handle = None
            self._active_scope = None
            if old is not None:
                old.close()

    def posture(self) -> dict:
        with self._lock:
            return {
                "mode": "serialized-host-bound-scope-candidate-v1",
                "opens": self.opens,
                "scope_switches": self.switches,
                "timing_comparable_to_legacy": False,
                "concurrency_comparable_to_legacy": False,
                "accepted_benchmark_authority": False,
            }
