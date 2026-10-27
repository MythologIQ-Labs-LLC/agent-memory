"""#786 security falsifier: legacy tenant-wide IDs disclose collision occupancy.

This test is deliberately RED against a vulnerable legacy facade. It must stay
a NO-GO until the multi-project host/storage identity contract is accepted and
the implementation passes a real SQLite replay. Suppressing or xfail-marking
it is not remediation.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory


TENANT = "tenant:786-collision-oracle"
ACTOR = "agent:786-collision-oracle"
KEY = "memory:public-collision-probe"


class LegacyCollisionOracleTests(unittest.TestCase):
    def test_project_b_cannot_observe_project_a_key_occupancy_via_write(self):
        # Two independent scratch roots isolate only the existence of A's key.
        # To B, the authorization identity and requested operation are identical.
        with tempfile.TemporaryDirectory() as occupied, tempfile.TemporaryDirectory() as free:
            occupied_root = Path(occupied)
            free_root = Path(free)
            with AgentMemory.open(
                occupied_root, tenant=TENANT, actor_id=ACTOR, scope="project:a"
            ) as a:
                first = a.remember(KEY, "Private gateway is Oslo")
                self.assertTrue(first["committed"], first)

            with AgentMemory.open(
                occupied_root, tenant=TENANT, actor_id=ACTOR, scope="project:b"
            ) as b:
                foreign = b.remember(KEY, "Project B gateway is Turku")

            with AgentMemory.open(
                free_root, tenant=TENANT, actor_id=ACTOR, scope="project:b"
            ) as b:
                vacant = b.remember(KEY, "Project B gateway is Turku")

            # This fails while tenant-wide collisions are observable.
            # Merely changing the refusal reason is insufficient: an attacker
            # observes whether B's independent write committed.
            self.assertEqual(
                (foreign["committed"], foreign.get("outcome")),
                (vacant["committed"], vacant.get("outcome")),
                "Legacy project B can distinguish occupancy of project A's logical key",
            )


if __name__ == "__main__":
    unittest.main()
