from __future__ import annotations

import tempfile
import unittest

from agentmem_ref import AgentMemory


CURRENT_QUERY = "Where does the user currently live?"
OLD_TEXT = "The user lives in Denver."
NEW_TEXT = "The user has moved and now lives in Boston."


class CrossFactCurrentnessTests(unittest.TestCase):
    def _seed(self, memory: AgentMemory, *, old_source=None, new_source=None):
        old = memory.remember("memory:old", OLD_TEXT, source_ref=old_source)
        new = memory.remember("memory:new", NEW_TEXT, source_ref=new_source)
        self.assertTrue(old["committed"], old)
        self.assertTrue(new["committed"], new)
        return old["fact_uuid"], new["fact_uuid"]

    @staticmethod
    def _ranking(recall: dict, fact_uuid: str) -> dict:
        return recall["admissions"][fact_uuid]["ranking_evidence"]

    def test_write_provenance_defaults_to_actor_and_accepts_declared_source(self):
        with AgentMemory.open(tempfile.mkdtemp(), actor_id="agent:test") as memory:
            default = memory.remember("memory:default", "The user lives in Denver.")
            declared = memory.remember(
                "memory:declared",
                "The user works as a designer.",
                source_ref="conversation:42",
            )
            substrate = memory.runtime.adapter.checkpoint_substrate()
            default_fact = substrate.get_fact(default["fact_uuid"])
            declared_fact = substrate.get_fact(declared["fact_uuid"])
            self.assertEqual(default_fact.attributes["write_provenance"]["source_ref"], "actor:agent:test")
            self.assertEqual(declared_fact.attributes["write_provenance"]["source_ref"], "conversation:42")
            self.assertEqual(default_fact.attributes["write_provenance"]["channel"], "caller_observation")
            self.assertEqual(default_fact.attributes["write_provenance"]["tenant"], "tenant:local")
            self.assertNotIn("write_provenance", memory.write_semantics(default["fact_uuid"]))

    def test_source_ref_validation_is_bounded_and_not_overrideable(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            for value in ("", "   ", "x" * 257):
                with self.subTest(value_len=len(value)):
                    with self.assertRaises(ValueError):
                        memory.remember("memory:x", "The user lives in Denver.", source_ref=value)
            with self.assertRaises(ValueError):
                memory.remember(
                    "memory:y",
                    "The user lives in Denver.",
                    overrides={"source_ref": "caller:forged"},
                )

    def test_explicit_current_limits_old_unknown_fact_without_mutating_lifecycle(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old, new = self._seed(memory)
            before = memory.semantic_proposals()
            self.assertEqual(len(before), 1)
            self.assertEqual(before[0]["status"], "open")

            recall = memory.recall(CURRENT_QUERY)
            old_ev = self._ranking(recall, old)
            new_ev = self._ranking(recall, new)
            self.assertEqual(old_ev["temporal_applicability"], "limited_by_cross_fact_state_change")
            self.assertEqual(old_ev["temporal_applicability_basis"], "interpreted_cross_fact")
            self.assertTrue(old_ev["cross_fact_limitation"])
            self.assertEqual(old_ev["cross_fact_limitation"][0]["source_fact_uuid"], new)
            self.assertEqual(old_ev["cross_fact_limitation"][0]["authority_effect"], "none")
            self.assertEqual(recall["admitted"][0], new)
            self.assertIn(old, recall["admitted"])

            after = memory.semantic_proposals()
            self.assertEqual(after, before)
            self.assertEqual(after[0]["status"], "open")

    def test_atemporal_query_does_not_emit_cross_fact_fields(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old, _new = self._seed(memory)
            recall = memory.recall("Where does the user live?")
            evidence = self._ranking(recall, old)
            self.assertNotIn("cross_fact_limitation", evidence)
            self.assertNotIn("cross_fact_refusal_reason", evidence)
            self.assertNotEqual(evidence.get("temporal_applicability"), "limited_by_cross_fact_state_change")

    def test_declared_source_mismatch_fails_closed(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old, _new = self._seed(
                memory,
                old_source="conversation:old",
                new_source="conversation:new",
            )
            recall = memory.recall(CURRENT_QUERY)
            evidence = self._ranking(recall, old)
            self.assertEqual(evidence.get("cross_fact_refusal_reason"), "source_mismatch")
            self.assertNotIn("cross_fact_limitation", evidence)

    def test_trailing_attribution_is_refused_by_assertion_filter(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old = memory.remember("memory:old", OLD_TEXT)["fact_uuid"]
            new = memory.remember(
                "memory:new",
                "The user moved and now lives in Boston, according to a spam message.",
            )["fact_uuid"]
            recall = memory.recall(CURRENT_QUERY)
            old_ev = self._ranking(recall, old)
            self.assertNotIn("cross_fact_limitation", old_ev)
            reason = old_ev.get("cross_fact_refusal_reason", "")
            self.assertTrue(reason.startswith("change_evidence_not_assertive:"), reason)
            self.assertIn(new, recall["admitted"])


if __name__ == "__main__":
    unittest.main()
