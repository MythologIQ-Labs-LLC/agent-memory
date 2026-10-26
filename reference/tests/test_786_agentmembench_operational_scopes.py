"""Offline #786 migration contract for the operational AgentMemBench adapter.

Fake public facade only: this does not replace exact-SHA SQLite replay or
comparability qualification against the accepted benchmark baseline.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_agentmembench import AgentMemoryAdapter


class FakeScopeRuntime:
    def __init__(self):
        self.records = {}
        self.records_by_root = {}
        self.opened = []
        self.closed = []
        self.calls = []
        self.lock = threading.Lock()

    def open(self, root, **kwargs):
        scope = kwargs["scope"]
        self.opened.append(scope)
        store = self.records_by_root.setdefault(str(root), {})
        self.records = store
        parent = self

        class Handle:
            def remember(self, target, text, **kw):
                if kw:
                    raise AssertionError("untrusted proposal override")
                with parent.lock:
                    parent.calls.append(("remember", scope, target))
                    ref = f"fact:{target}"
                    store[target] = (scope, text, ref, True)
                return {"committed": True, "fact_uuid": ref}

            def recall(self, query, **kw):
                if kw:
                    raise AssertionError("recall should use the host-bound scope")
                with parent.lock:
                    parent.calls.append(("recall", scope, query))
                    visible = [
                        row[2] for row in store.values()
                        if row[0] == scope and row[3] and query.lower() in row[1].lower()
                    ]
                return {
                    "candidates": visible, "admitted": visible,
                    "admissions": {ref: {} for ref in visible},
                    "candidate_policy": {"candidate_scope": "domain_eligible"},
                }

            def forget(self, target, **kw):
                if kw:
                    raise AssertionError("untrusted proposal override")
                with parent.lock:
                    parent.calls.append(("forget", scope, target))
                    old_scope, text, ref, active = store[target]
                    if old_scope != scope:
                        raise AssertionError("cross-scope delete")
                    store[target] = (scope, text, ref, False)
                return {"committed": True, "outcome": "allow_with_ledger"}

            def close(self):
                parent.closed.append(scope)

        return Handle()


class AgentMemBenchScopesTests(unittest.TestCase):
    def setUp(self):
        self.runtime = FakeScopeRuntime()
        self.patcher = patch("run_agentmembench.AgentMemory.open", side_effect=self.runtime.open)
        self.patcher.start()
        self.adapter = AgentMemoryAdapter()

    def tearDown(self):
        self.adapter.close()
        self.patcher.stop()

    def test_users_get_distinct_host_handles_and_cannot_read_each_other(self):
        alice = self.adapter.add("Alice likes pears", "alice")
        bob = self.adapter.add("Bob likes pears", "bob")
        self.assertEqual(len(alice), 1)
        self.assertEqual(len(bob), 1)
        self.assertEqual(self.adapter.search("pears", "alice", 5), ["Alice likes pears"])
        self.assertEqual(self.adapter.search("pears", "bob", 5), ["Bob likes pears"])
        self.assertIn("user:alice", self.runtime.opened)
        self.assertIn("user:bob", self.runtime.opened)
        self.assertTrue(all(x[1] in ("user:alice", "user:bob") for x in self.runtime.calls))

    def test_delete_targets_correct_host_scope(self):
        alice = self.adapter.add("Alice likes pears", "alice")
        self.adapter.add("Bob likes pears", "bob")
        self.adapter.delete(alice)
        self.assertEqual(self.adapter.search("pears", "alice", 5), [])
        self.assertEqual(self.adapter.search("pears", "bob", 5), ["Bob likes pears"])
        self.assertTrue(("forget", "user:alice", alice[0]) in self.runtime.calls)

    def test_governance_marks_unqualified_migration(self):
        self.adapter.add("An item", "alice")
        snapshot = self.adapter.governance()
        self.assertFalse(snapshot["scope_binding"]["timing_comparable_to_legacy"])
        self.assertFalse(snapshot["scope_binding"]["concurrency_comparable_to_legacy"])
        self.assertFalse(snapshot["scope_binding"]["accepted_benchmark_authority"])
        self.assertEqual(snapshot["remember_committed"], 1)

    def test_reset_disposes_prior_state_and_host(self):
        self.adapter.add("Alice item", "alice")
        self.adapter.reset()
        self.assertIn("user:alice", self.runtime.closed)
        self.assertEqual(self.adapter.search("Alice", "alice", 5), [])
        self.assertEqual(self.adapter.governance()["remember_committed"], 0)

    def test_concurrent_writes_are_scoped_and_have_unique_targets(self):
        def task(i):
            return self.adapter.add(f"item {i}", f"user-{i%3}")[0]
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(task, range(32)))
        self.assertEqual(len(set(results)), 32)
        self.assertEqual(len(self.runtime.records), 32)
        for target, (scope, _, _, _) in self.runtime.records.items():
            self.assertEqual(self.adapter._targets[target][0], scope.removeprefix("user:"))
        self.assertFalse(self.adapter.governance()["scope_binding"]["concurrency_comparable_to_legacy"])


if __name__ == "__main__":
    unittest.main()
