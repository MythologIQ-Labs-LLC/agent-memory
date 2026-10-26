"""#786 formal adapter migration tests, not an accepted frozen benchmark run."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_agentmembench_formal import (
    AgentMemoryFormalAdapter, load_freeze, verify_self,
)


class FakeFormalStore:
    def __init__(self):
        self.roots = {}
        self.operations = []
        self.closed = []
        self.lock = threading.Lock()

    def open(self, root, **kwargs):
        scope = kwargs["scope"]
        records = self.roots.setdefault(str(root), {})
        parent = self

        class FakeHandle:
            def remember(self, target, text, **kwargs):
                if kwargs:
                    raise AssertionError("fabricated identity override")
                with parent.lock:
                    ref = f"ref:{target}"
                    records[target] = (scope, text, ref, True)
                    parent.operations.append(("write", scope, target))
                    return {"committed": True, "fact_uuid": ref}

            def recall(self, query, **kwargs):
                if set(kwargs) != {"budget"}:
                    raise AssertionError(f"unexpected recall arguments {kwargs}")
                limit = kwargs["budget"]
                with parent.lock:
                    matched = [
                        ref for owner, text, ref, live in records.values()
                        if live and owner == scope and query.lower() in text.lower()
                    ]
                    parent.operations.append(("read", scope, query))
                return {
                    "candidates": matched, "admitted": matched,
                    "returned": matched[:limit],
                    "admissions": {ref: {} for ref in matched},
                }

            def forget(self, target, **kwargs):
                if kwargs:
                    raise AssertionError("fabricated identity override")
                with parent.lock:
                    owner, text, ref, _ = records[target]
                    if owner != scope:
                        raise AssertionError("foreign deletion")
                    records[target] = (owner, text, ref, False)
                    parent.operations.append(("delete", scope, target))
                    return {"committed": True}

            def write_semantics(self, ref):
                for owner, text, current, _ in records.values():
                    if current == ref:
                        return {"scope": owner, "visible": owner == scope}
                return None

            def close(self):
                parent.closed.append(scope)

        return FakeHandle()


class FormalScopeMigrationTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeFormalStore()
        self.patcher = patch("run_agentmembench_formal.AgentMemory.open", side_effect=self.fake.open)
        self.patcher.start()
        self.adapter = AgentMemoryFormalAdapter()

    def tearDown(self):
        self.adapter.close()
        self.patcher.stop()

    def test_each_user_is_written_and_recalled_through_a_real_scope(self):
        alice = self.adapter.add("Alice's favorite is pears", "alice")
        bob = self.adapter.add("Bob's favorite is pears", "bob")
        self.assertEqual(len(alice), 1)
        self.assertEqual(len(bob), 1)
        self.assertEqual(self.adapter.search("pears", "alice", 5), ["Alice's favorite is pears"])
        self.assertEqual(self.adapter.search("pears", "bob", 5), ["Bob's favorite is pears"])
        self.assertTrue(all(entry[1] in ("user:alice", "user:bob") for entry in self.fake.operations))

    def test_delete_uses_target_owners_scope(self):
        alice = self.adapter.add("Alice's favorite is pears", "alice")
        self.adapter.add("Bob's favorite is pears", "bob")
        self.adapter.delete(alice)
        self.assertEqual(self.adapter.search("pears", "alice", 5), [])
        self.assertEqual(self.adapter.search("pears", "bob", 5), ["Bob's favorite is pears"])
        self.assertIn(("delete", "user:alice", alice[0]), self.fake.operations)

    def test_traced_writes_snapshot_through_public_scope_at_reset(self):
        self.adapter.phase_label = "conflict"
        self.adapter.add("Older role is analyst", "conflict_alice")
        self.adapter.add("New role is engineer", "conflict_alice")
        self.adapter.search("role", "conflict_alice", 1)
        self.adapter.reset()
        self.assertEqual(len(self.adapter.traces["conflict"]), 1)
        self.assertEqual(len(self.adapter.write_semantics), 2)
        for semantics in self.adapter.write_semantics.values():
            self.assertEqual(semantics["scope"], "user:conflict_alice")
            self.assertTrue(semantics["visible"])

    def test_concurrent_calls_remain_serialized_and_distinct(self):
        def add(i):
            return self.adapter.add(f"entry {i}", f"worker_{i % 4}")[0]
        with ThreadPoolExecutor(max_workers=8) as executor:
            targets = list(executor.map(add, range(24)))
        self.assertEqual(len(set(targets)), 24)
        self.assertFalse(self.adapter._host.posture()["concurrency_comparable_to_legacy"])

    def test_changed_formal_runner_cannot_claim_existing_freeze(self):
        with self.assertRaisesRegex(SystemExit, "new protocol identity"):
            verify_self(load_freeze())


if __name__ == "__main__":
    unittest.main()
