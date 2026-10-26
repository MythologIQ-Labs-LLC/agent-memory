"""#786 REAL SQLite scope-distinct collision/roundtrip candidate replay.

Must execute against exact branch SHA and installed runtime dependencies.
No release authority or benchmark score is granted by this test alone.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref.api.scoped_identity import ScopeDistinctMemory

TENANT = "tenant:scoped-786"
ACTOR = "agent:scoped-786"
KEY = "memory:gateway-region"


class ScopeDistinctSQLiteTests(unittest.TestCase):
    def test_colliding_public_keys_are_isolated_and_survive_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with ScopeDistinctMemory.open(
                root, tenant=TENANT, actor_id=ACTOR, scope="project:a",
            ) as owner:
                first = owner.remember(KEY, "Orrin gateway is in Oslo")
                self.assertTrue(first["committed"], first)
                first_ref = first["fact_ref"]
                self.assertEqual(owner.history(KEY)["current_fact_ref"], first_ref)
            with ScopeDistinctMemory.open(
                root, tenant=TENANT, actor_id=ACTOR, scope="project:b",
            ) as other:
                second = other.remember(KEY, "Orrin gateway is in Turku")
                self.assertTrue(second["committed"], second)
                second_ref = second["fact_ref"]
                self.assertNotEqual(first_ref, second_ref)
                self.assertEqual(other.history(KEY)["current_fact_ref"], second_ref)
            with ScopeDistinctMemory.open(
                root, tenant=TENANT, actor_id=ACTOR, scope="project:a",
            ) as recovered_owner:
                self.assertEqual(recovered_owner.history(KEY)["current_fact_ref"], first_ref)
            with ScopeDistinctMemory.open(
                root, tenant=TENANT, actor_id=ACTOR, scope="project:b",
            ) as recovered_other:
                self.assertEqual(recovered_other.history(KEY)["current_fact_ref"], second_ref)

    def test_two_keys_inside_same_scope_do_not_collide(self):
        with tempfile.TemporaryDirectory() as temp:
            with ScopeDistinctMemory.open(
                Path(temp), tenant=TENANT, actor_id=ACTOR, scope="project:a",
            ) as memory:
                one = memory.remember("memory:first", "Alpha state")
                two = memory.remember("memory:second", "Beta state")
                self.assertTrue(one["committed"], one)
                self.assertTrue(two["committed"], two)
                self.assertNotEqual(one["fact_ref"], two["fact_ref"])

    def test_distinct_project_cannot_read_other_scoped_key(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with ScopeDistinctMemory.open(
                root, tenant=TENANT, actor_id=ACTOR, scope="project:a",
            ) as owner:
                written = owner.remember(KEY, "Orrin gateway is in Oslo")
                self.assertTrue(written["committed"], written)
            with ScopeDistinctMemory.open(
                root, tenant=TENANT, actor_id=ACTOR, scope="project:b",
            ) as other:
                self.assertIsNone(other.history(KEY)["current_fact_ref"])
                self.assertEqual(other.history(KEY)["state_version"], 0)


if __name__ == "__main__":
    unittest.main()
