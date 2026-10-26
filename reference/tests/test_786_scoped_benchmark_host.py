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
    def __init__(self, scope, closed):
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
        self.host = SerializedScopedBenchmarkHost(opener)

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
        self.host = SerializedScopedBenchmarkHost(opener)
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
