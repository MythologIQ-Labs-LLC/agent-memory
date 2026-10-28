"""Candidate-only tests for serialized host-owned per-user scope switching."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoped_benchmark_host import SerializedScopedBenchmarkHost


class FakeFacade:
    def __init__(self, scope, closed, tenant="tenant:bench", actor_id="agent:bench"):
        self.tenant = tenant
        self.actor_id = actor_id
        self.scope = scope
        self.closed = closed
        self.is_closed = False

    def remember(self, text):
        if self.is_closed:
            raise RuntimeError("handle already closed")
        return (self.scope, text)

    def close(self):
        if self.is_closed:
            raise AssertionError("closed twice")
        self.is_closed = True
        self.closed.append(self.scope)


class ScopedHostTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        self.closed = []
        def opener(scope):
            self.created.append(scope)
            return FakeFacade(scope, self.closed)
        self.host = SerializedScopedBenchmarkHost(opener, tenant="tenant:bench", actor_id="agent:bench")

    def tearDown(self):
        self.host.close()

    def test_one_scope_reuses_same_handle(self):
        with self.host.use("alice") as first:
            self.assertEqual(first.remember("alpha"), ("user:alice", "alpha"))
        with self.host.use("alice") as again:
            self.assertIs(first, again)
        self.assertEqual(self.created, ["user:alice"])
        self.assertEqual(self.closed, [])

    def test_switch_closes_old_before_new_scope_is_opened(self):
        with self.host.use("alice") as first:
            pass
        with self.host.use("bob") as second:
            self.assertTrue(first.is_closed)
            self.assertEqual(second.scope, "user:bob")
        self.assertEqual(self.created, ["user:alice", "user:bob"])
        self.assertEqual(self.closed, ["user:alice"])
        self.assertEqual(self.host.posture()["scope_switches"], 1)

    def test_misbound_facade_is_closed_and_never_issued(self):
        wrong = FakeFacade("user:bob", self.closed)
        self.host.close()
        self.host = SerializedScopedBenchmarkHost(lambda requested: wrong, tenant="tenant:bench", actor_id="agent:bench")
        with self.assertRaisesRegex(RuntimeError, "identity does not match"):
            with self.host.use("alice"):
                self.fail("a misbound handle escaped to its caller")
        self.assertTrue(wrong.is_closed)
        self.assertEqual(self.host.posture()["opens"], 0)

    def test_missing_runtime_scope_is_refused_even_if_open_succeeds(self):
        class Unbound:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        unbound = Unbound()
        self.host.close()
        self.host = SerializedScopedBenchmarkHost(lambda requested: unbound, tenant="tenant:bench", actor_id="agent:bench")
        with self.assertRaisesRegex(RuntimeError, "identity does not match"):
            with self.host.use("alice"):
                pass
        self.assertTrue(unbound.closed)
        self.assertEqual(self.host.posture()["opens"], 0)

    def test_wrong_tenant_or_actor_is_closed_before_use(self):
        for overrides in ({"tenant": "tenant:foreign"}, {"actor_id": "agent:foreign"}):
            with self.subTest(overrides=overrides):
                self.host.close()
                fake = FakeFacade("user:alice", self.closed, **overrides)
                self.host = SerializedScopedBenchmarkHost(
                    lambda requested: fake, tenant="tenant:bench", actor_id="agent:bench"
                )
                with self.assertRaisesRegex(RuntimeError, "identity does not match"):
                    with self.host.use("alice"):
                        self.fail("misbound tenant or actor escaped to caller")
                self.assertTrue(fake.is_closed)
                self.assertEqual(self.host.posture()["opens"], 0)

    def test_missing_host_identity_is_refused_at_construction(self):
        for tenant, actor in (("", "agent:bench"), ("tenant:bench", "")):
            with self.assertRaisesRegex(ValueError, "must be nonempty"):
                SerializedScopedBenchmarkHost(lambda scope: None, tenant=tenant, actor_id=actor)

    def test_cached_scope_identity_change_cannot_borrow_prior_authorization(self):
        with self.host.use("alice") as facade:
            pass
        facade.scope = "user:bob"
        with self.assertRaisesRegex(RuntimeError, "cached runtime identity"):
            with self.host.use("alice"):
                self.fail("a tampered cached handle escaped")
        self.assertTrue(facade.is_closed)
        with self.host.use("alice") as reopened:
            self.assertIsNot(reopened, facade)
            self.assertEqual(reopened.scope, "user:alice")

    def test_cached_actor_identity_change_is_refused(self):
        with self.host.use("alice") as facade:
            pass
        facade.actor_id = "agent:foreign"
        with self.assertRaisesRegex(RuntimeError, "cached runtime identity"):
            with self.host.use("alice"):
                self.fail("a mutated actor escaped")
        self.assertTrue(facade.is_closed)

    def test_identity_property_raising_during_open_closes_handle(self):
        class FailingScope(FakeFacade):
            @property
            def scope(self):
                raise RuntimeError("sensitive property failure")

            @scope.setter
            def scope(self, value):
                pass

            def close(self):
                self.is_closed = True
                self.closed.append("unreadable-scope")

        self.host.close()
        handle = FailingScope("user:alice", self.closed)
        self.host = SerializedScopedBenchmarkHost(
            lambda requested: handle, tenant="tenant:bench", actor_id="agent:bench"
        )
        with self.assertRaisesRegex(RuntimeError, "identity does not match"):
            with self.host.use("alice"):
                self.fail("identity descriptor error must never release a handle")
        self.assertTrue(handle.is_closed)
        self.assertEqual(self.host.posture()["opens"], 0)

    def test_cached_identity_descriptor_failure_closes_handle(self):
        with self.host.use("alice") as handle:
            pass
        class FailingActor:
            def __get__(self, obj, owner):
                raise RuntimeError("sensitive cached identity failure")

            def __set__(self, obj, value):
                raise RuntimeError("actor identity is read-only")
        # An existing public facade can become misconfigured after first open.
        # This simulates a descriptor that raises during every later check.
        original_class = handle.__class__
        class BrokenFacade(original_class):
            actor_id = FailingActor()
        handle.__class__ = BrokenFacade
        with self.assertRaisesRegex(RuntimeError, "cached runtime identity"):
            with self.host.use("alice"):
                self.fail("cached identity failure must not release a handle")
        self.assertTrue(handle.is_closed)
        self.assertEqual(self.host.posture()["opens"], 1)

    def test_scope_is_host_owned_not_tool_overridable(self):
        with self.host.use("alice") as handle:
            self.assertEqual(handle.scope, "user:alice")
            self.assertFalse(hasattr(handle, "overrides"))

    def test_bad_user_refused_before_any_runtime_open(self):
        for bad in ("", " ", None, 7):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                with self.host.use(bad):
                    pass
        self.assertEqual(self.created, [])

    def test_close_is_idempotent_and_blocks_reuse(self):
        with self.host.use("alice"):
            pass
        self.host.close()
        self.host.close()
        self.assertEqual(self.closed, ["user:alice"])
        with self.assertRaises(RuntimeError):
            with self.host.use("alice"):
                pass

    def test_failed_open_does_not_leave_old_scope_active(self):
        failed = {"bob"}
        def opener(scope):
            if scope == "user:bob":
                raise RuntimeError("open denied")
            return FakeFacade(scope, self.closed)
        self.host.close()
        self.host = SerializedScopedBenchmarkHost(opener, tenant="tenant:bench", actor_id="agent:bench")
        with self.host.use("alice") as old:
            pass
        with self.assertRaisesRegex(RuntimeError, "open denied"):
            with self.host.use("bob"):
                pass
        self.assertTrue(old.is_closed)
        with self.host.use("alice") as renewed:
            self.assertIsNot(renewed, old)

    def test_threaded_scope_switches_are_serialized(self):
        active = 0
        maximum_active = 0
        lock = threading.Lock()
        def execute(index):
            nonlocal active, maximum_active
            with self.host.use("alice" if index % 2 else "bob") as handle:
                with lock:
                    active += 1
                    maximum_active = max(maximum_active, active)
                self.assertEqual(handle.remember(index)[0], handle.scope)
                time.sleep(0.001)
                with lock:
                    active -= 1
        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(execute, range(40)))
        self.assertEqual(maximum_active, 1)
        self.assertFalse(self.host.posture()["concurrency_comparable_to_legacy"])


if __name__ == "__main__":
    unittest.main()
