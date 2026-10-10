"""#597: mixed utterances persist a bounded assertion, never the follow-up request.

These are synthetic, preregistered runtime-integration cases, not #594 gold.
"""
from __future__ import annotations

import tempfile
import unittest

from agentmem_ref import AgentMemory
from agentmem_ref.runtime import proposition_semantics as semantics


class PersistedRequestBoundaryTests(unittest.TestCase):
    def test_followup_request_does_not_bleed_into_persisted_value_on_reopen(self):
        with tempfile.TemporaryDirectory() as root:
            def open_memory():
                return AgentMemory.open(
                    root, tenant="tenant:synthetic-boundary",
                    actor_id="agent:synthetic-boundary", scope="project:synthetic-boundary",
                    purpose="synthetic proposition request boundary replay",
                )

            memory = open_memory()
            try:
                out = memory.remember(
                    "memory:preference:green-tea",
                    "I prefer green tea, can you recommend a book?",
                )
                fact_uuid = out["fact_uuid"]
                before = memory.write_semantics(fact_uuid)
                self.assertEqual(before["proposition"]["status"], "known")
                self.assertEqual(before["proposition"]["value"], "green tea")
                self.assertEqual(before["interpreter"]["version"], "1.2.0")
                self.assertEqual(before["authority_effect"], "none")
                self.assertFalse(any(
                    "recommend" in str(value) or "book" in str(value)
                    for value in before["proposition"].values()
                ))
            finally:
                memory.close()

            memory = open_memory()
            try:
                after = memory.write_semantics(fact_uuid)
                self.assertEqual(after, before)
                self.assertEqual(after["proposition"]["value"], "green tea")
                self.assertEqual(after["interpreter"]["version"], "1.2.0")
            finally:
                memory.close()

    def test_legacy_write_decoding_does_not_reinterpret_old_values(self):
        old = {
            "version": "1.1.0/1.0.0",
            "proposition": {
                "status": "known", "entity": "speaker", "property": "prefer",
                "value": "green tea, can you recommend a book?", "reason": None,
            },
        }
        expanded = semantics.expanded_form(old)
        self.assertEqual(expanded["interpreter"]["version"], "1.1.0")
        self.assertEqual(expanded["proposition"]["value"],
                         "green tea, can you recommend a book?")
        self.assertEqual(expanded["authority_effect"], "none")


if __name__ == "__main__":
    unittest.main()
