"""#636 integration probe against the real governed SQLite public facade.

No route is disabled or rewritten here; this is observed provenance only.
These tests require a complete repository environment.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.evaluation.route_attribution import attribute_returned_routes


class ObservedRouteAttributionIntegrationTests(unittest.TestCase):
    def test_public_sqlite_facade_retains_nonlexical_identity_contribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            with AgentMemory.open(
                Path(tmp), tenant="tenant:636", actor_id="agent:636",
                scope="project:636", purpose="representation attribution",
            ) as memory:
                deploy = memory.remember("memory:deploy", "deployment window Thursday")
                backup = memory.remember("memory:backup", "database backups run nightly")
                self.assertTrue(deploy["committed"])
                self.assertTrue(backup["committed"])

                result = memory.recall(
                    "deployment window",
                    logical_memory_refs=("memory:backup",),
                )
                refs = {deploy["fact_uuid"], backup["fact_uuid"]}
                self.assertTrue(refs <= set(result["returned"]))
                report = attribute_returned_routes(
                    result,
                    required_refs=frozenset((deploy["fact_uuid"],)),
                    forbidden_refs=frozenset((backup["fact_uuid"],)),
                )
                self.assertEqual(report.required_returned, 1)
                self.assertEqual(report.forbidden_returned, 1)
                routes = {item.route_id: item for item in report.routes}
                self.assertGreaterEqual(routes["lexical"].required, 1)
                self.assertGreaterEqual(routes["exact_logical_identity"].forbidden, 1)
                self.assertEqual(report.authority_effect, "none")

    def test_return_budget_does_not_count_unreturned_admitted_memories(self):
        with tempfile.TemporaryDirectory() as tmp:
            with AgentMemory.open(
                Path(tmp), tenant="tenant:636", actor_id="agent:636",
                scope="project:636", purpose="representation attribution",
            ) as memory:
                first = memory.remember("memory:first", "shared project milestone one")
                second = memory.remember("memory:second", "shared project milestone two")
                self.assertTrue(first["committed"])
                self.assertTrue(second["committed"])
                recall = memory.recall("shared project milestone", budget=1)
                self.assertEqual(len(recall["returned"]), 1)
                self.assertEqual(len(recall["admitted"]), 2)
                expected = frozenset((first["fact_uuid"], second["fact_uuid"]))
                report = attribute_returned_routes(
                    recall, required_refs=expected, forbidden_refs=frozenset()
                )
                self.assertEqual(report.returned, 1)
                self.assertEqual(report.required_missing, 1)
                self.assertEqual(sum(r.uniquely_required for r in report.routes) <= 1, True)


if __name__ == "__main__":
    unittest.main()
