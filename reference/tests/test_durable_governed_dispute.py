"""#582: dispute is one governed durable transition, not an in-memory side effect."""

from __future__ import annotations

import tempfile
import unittest
from unittest import mock

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm

TENANT = "tenant:dispute"
SCOPE = "project:dispute"
NOW = "2026-09-27T12:00:00Z"


def _open(root: str) -> AgentMemory:
    return AgentMemory.open(
        root,
        tenant=TENANT,
        actor_id="agent:dispute",
        scope=SCOPE,
        purpose="durable dispute tests",
    )


def _evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:dispute-review",
        version=1,
        purpose="qualify a dispute transition",
        scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE),
        required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the dispute against its source evidence.",
        provenance_refs=("evidence:dispute-source",),
    )
    return pm.evidence_for(skill)


class DurableGovernedDisputeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = self.temp.name

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _state_change(self, memory: AgentMemory) -> tuple[str, str]:
        old = memory.remember(
            "memory:city",
            "Kevin lives in Denver.",
            valid_from="2020-01-01",
        )["fact_uuid"]
        changed = memory.correct(
            "memory:city",
            "Kevin lives in Boston.",
            evidence=_evidence(),
            risk_class="low",
            replacement_kind="state_change",
            valid_from="2024-06-01",
        )
        self.assertTrue(changed["committed"], changed)
        return old, changed["fact_uuid"]

    def _historical(self, memory: AgentMemory) -> dict:
        return memory.recall(
            "Where does Kevin live?",
            temporal_intent={"mode": "historical"},
            reference_time=NOW,
        )

    def _as_of_old(self, memory: AgentMemory) -> dict:
        return memory.recall(
            "Where does Kevin live?",
            temporal_intent={
                "mode": "as_of",
                "target_start": "2022-01-01",
                "target_end": "2022-01-02",
            },
        )

    def test_dispute_without_qualified_evidence_does_not_commit(self):
        with _open(self.root) as memory:
            fact = memory.remember("memory:status", "Deployment is healthy.")["fact_uuid"]
            before = memory.history("memory:status")["history"]["state_version"]
            result = memory.dispute("memory:status", fact_uuid=fact)
            self.assertFalse(result["committed"], result)
            self.assertEqual(result["outcome"], "require_review")
            self.assertEqual(memory.history("memory:status")["history"]["state_version"], before)
            recalled = memory.recall("Deployment healthy")
            self.assertIn(fact, recalled["admitted"])

    def test_dispute_is_durable_without_any_intervening_operation(self):
        memory = _open(self.root)
        old, new = self._state_change(memory)
        before = memory.history("memory:city")["history"]["state_version"]
        result = memory.dispute(
            "memory:city",
            fact_uuid=old,
            evidence=_evidence(),
            risk_class="low",
            evidence_refs=("evidence:city-dispute",),
        )
        self.assertTrue(result["committed"], result)
        self.assertEqual(result["fact_uuid"], old)
        self.assertEqual(result["receipt"]["requested_action"], "other")
        self.assertEqual(result["receipt"]["before_state"], f"v{before}")
        self.assertEqual(result["receipt"]["after_state"], f"v{before + 1}")
        history = memory.history("memory:city")["history"]
        dispute_events = [event for event in history["events"] if event["event_type"] == "memory.dispute"]
        self.assertEqual(len(dispute_events), 1)
        event = dispute_events[0]
        self.assertEqual(event["payload"]["fact_uuid"], old)
        self.assertTrue(event["payload"]["committed"])
        self.assertEqual(event["payload"]["operation_classification"], "other")
        self.assertIn("evidence:city-dispute", event["payload"]["evidence_refs"])

        # Critical regression boundary: close immediately. No recall/write is allowed
        # to accidentally publish the dispute on our behalf.
        memory.close()
        memory = _open(self.root)
        try:
            historical = self._historical(memory)
            self.assertNotIn(old, historical["admitted"])
            self.assertEqual(historical["admissions"][old]["refusal"], "disputed")
            as_of = self._as_of_old(memory)
            self.assertNotIn(old, as_of["admitted"])
            self.assertEqual(as_of["admissions"][old]["refusal"], "disputed")
            current = memory.recall("Where does Kevin currently live?", reference_time=NOW)
            self.assertEqual(current["admitted"], [new])
        finally:
            memory.close()

    def test_disputed_current_fact_is_refused_after_restart(self):
        memory = _open(self.root)
        fact = memory.remember("memory:status", "Deployment is healthy.")["fact_uuid"]
        result = memory.dispute("memory:status", fact_uuid=fact, evidence=_evidence(), risk_class="low")
        self.assertTrue(result["committed"], result)
        memory.close()

        with _open(self.root) as reopened:
            recalled = reopened.recall("Deployment healthy")
            self.assertNotIn(fact, recalled["admitted"])
            self.assertEqual(recalled["admissions"][fact]["refusal"], "disputed")
            self.assertEqual(reopened.history("memory:status")["history"]["current_fact_uuid"], fact)

    def test_dispute_preserves_fact_content_and_history(self):
        memory = _open(self.root)
        old, _new = self._state_change(memory)
        before = memory.runtime.adapter._substrate.get_fact(old)
        self.assertIsNotNone(before)
        result = memory.dispute("memory:city", fact_uuid=old, evidence=_evidence(), risk_class="low")
        self.assertTrue(result["committed"], result)
        memory.close()

        with _open(self.root) as reopened:
            after = reopened.runtime.adapter._substrate.get_fact(old)
            self.assertIsNotNone(after)
            self.assertEqual(after.fact_text, before.fact_text)
            replacement = reopened.runtime.adapter.replacement_record(old)
            self.assertIsNotNone(replacement)
            self.assertEqual(replacement["kind"], "state_change")

    def test_direct_durable_mark_disputed_bypass_is_rejected(self):
        with _open(self.root) as memory:
            fact = memory.remember("memory:status", "Deployment is healthy.")["fact_uuid"]
            with self.assertRaisesRegex(RuntimeError, "governed_dispute"):
                memory.runtime.adapter.mark_disputed(fact)
            recalled = memory.recall("Deployment healthy")
            self.assertIn(fact, recalled["admitted"])

    def test_failed_generation_rolls_back_dispute_and_evidence(self):
        memory = _open(self.root)
        old, _new = self._state_change(memory)
        base = memory.runtime.durable_runtime.base
        history_before = memory.history("memory:city")["history"]
        with mock.patch.object(
            base.substrate,
            "append_runtime_journal",
            side_effect=RuntimeError("simulated publication failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "publication failure"):
                memory.dispute("memory:city", fact_uuid=old, evidence=_evidence(), risk_class="low")

        # Rollback restores the in-memory adapter immediately, not merely after reopen.
        historical = self._historical(memory)
        self.assertIn(old, historical["admitted"])
        self.assertNotEqual(historical["admissions"][old].get("refusal"), "disputed")
        history_after = memory.history("memory:city")["history"]
        self.assertEqual(history_after["state_version"], history_before["state_version"])
        self.assertFalse([event for event in history_after["events"] if event["event_type"] == "memory.dispute"])
        memory.close()

        with _open(self.root) as reopened:
            historical = self._historical(reopened)
            self.assertIn(old, historical["admitted"])
            self.assertNotEqual(historical["admissions"][old].get("refusal"), "disputed")

    def test_duplicate_and_wrong_binding_do_not_mutate(self):
        with _open(self.root) as memory:
            a = memory.remember("memory:a", "Alpha state.")["fact_uuid"]
            b = memory.remember("memory:b", "Beta state.")["fact_uuid"]
            wrong = memory.dispute("memory:a", fact_uuid=b, evidence=_evidence(), risk_class="low")
            self.assertFalse(wrong["committed"], wrong)
            self.assertEqual(wrong["refusal"], "target_binding_mismatch")
            first = memory.dispute("memory:a", fact_uuid=a, evidence=_evidence(), risk_class="low")
            self.assertTrue(first["committed"], first)
            version = memory.history("memory:a")["history"]["state_version"]
            duplicate = memory.dispute("memory:a", fact_uuid=a, evidence=_evidence(), risk_class="low")
            self.assertFalse(duplicate["committed"], duplicate)
            self.assertEqual(duplicate["refusal"], "already_disputed")
            self.assertEqual(memory.history("memory:a")["history"]["state_version"], version)


if __name__ == "__main__":
    unittest.main()
