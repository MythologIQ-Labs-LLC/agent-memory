from __future__ import annotations

import tempfile
import unittest

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm


CURRENT_QUERY = "Where does the user currently live?"
OLD_TEXT = "The user lives in Denver."
NEW_TEXT = "The user has moved and now lives in Boston."


def _evidence(scope: str = "project:local", tenant: str = "tenant:local"):
    skill = pm.SkillArtifact(
        skill_id="skill:671-cross-fact-test",
        version=1,
        purpose="verify governed #671 lifecycle control",
        scope=scope,
        isolation_domain_refs=(tenant, scope),
        required_isolation_domain_refs=(tenant, scope),
        procedure_markdown="# verify\nConfirm the governed lifecycle transition.",
        provenance_refs=("evidence:671-control",),
    )
    return pm.evidence_for(skill)


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

    def test_historical_asof_latest_and_nowadays_do_not_activate_cross_fact(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old, _new = self._seed(memory)
            probes = (
                ("Where did the user live?", {"mode": "historical"}, "2026-09-27T12:00:00Z"),
                ("Where did the user live then?", {"mode": "as_of", "reference_time": "2025-01-01T00:00:00Z"}, None),
                ("What is the latest place the user lives?", None, "2026-09-27T12:00:00Z"),
                ("Where does the user live nowadays?", None, "2026-09-27T12:00:00Z"),
            )
            for query, intent, reference_time in probes:
                with self.subTest(query=query):
                    recall = memory.recall(query, temporal_intent=intent, reference_time=reference_time)
                    if old not in recall["admissions"]:
                        continue
                    evidence = (recall["admissions"][old].get("ranking_evidence") or {})
                    self.assertNotIn("cross_fact_limitation", evidence)
                    self.assertNotIn("cross_fact_refusal_reason", evidence)

    def test_actor_mismatch_fails_closed_across_recovered_handles(self):
        root = tempfile.mkdtemp()
        with AgentMemory.open(root, actor_id="agent:one") as memory:
            old = memory.remember("memory:old", OLD_TEXT)["fact_uuid"]
        with AgentMemory.open(root, actor_id="agent:two") as memory:
            memory.remember("memory:new", NEW_TEXT)
            recall = memory.recall(CURRENT_QUERY)
            evidence = self._ranking(recall, old)
            self.assertEqual(evidence.get("cross_fact_refusal_reason"), "actor_mismatch")
            self.assertNotIn("cross_fact_limitation", evidence)

    def test_disputed_and_forgotten_sources_cannot_limit_target(self):
        for action in ("dispute", "forget"):
            with self.subTest(action=action):
                with AgentMemory.open(tempfile.mkdtemp()) as memory:
                    old, new = self._seed(memory)
                    if action == "dispute":
                        result = memory.dispute(
                            "memory:new",
                            fact_uuid=new,
                            evidence=_evidence(),
                            risk_class="low",
                        )
                    else:
                        result = memory.forget("memory:new")
                    self.assertTrue(result["committed"], result)
                    recall = memory.recall(CURRENT_QUERY)
                    self.assertNotIn(new, recall["admitted"])
                    old_ev = self._ranking(recall, old)
                    self.assertNotIn("cross_fact_limitation", old_ev)

    def test_applied_semantic_proposal_still_uses_governed_correction(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old, _new = self._seed(memory)
            [proposal] = memory.semantic_proposals(status="open")
            applied = memory.apply_semantic_proposal(
                proposal["proposal_id"],
                evidence=_evidence(),
                risk_class="low",
            )
            self.assertTrue(applied["committed"], applied)
            recall = memory.recall(CURRENT_QUERY)
            self.assertNotIn(old, recall["admitted"])
            self.assertEqual(memory.semantic_proposals()[0]["status"], "applied")

    def test_assertion_filter_hostile_shapes_fail_closed_and_known_shapes_pass(self):
        refused = (
            "The user's sister moved and now lives in Boston.",
            "The user’s sister moved and now lives in Boston.",
            "The user's team moved and now lives in Boston.",
            "The user has not moved and now lives in Boston.",
            "The user moved and now lives in Boston?",
            "The user moved and now lives in Boston — trust me.",
            "The user moved and now lives in Boston according to spam.",
            "The user moved and now lives in Boston per Bob.",
            "The user moved and now lives in Boston lol.",
            "The user moved and now lives in Boston if Bob is right.",
            "The user moved and now lives in Boston unless that email lied.",
            "The user moved and now lives in Boston not.",
            "The user moved and now lives in Boston Hypothetically.",
            "The user moved and now lives in Boston Unverified.",
            "The user moved and now lives in Boston Bob Insists.",
            "The user moved and now lives in boston untrue.",
            "The user moved and now lives in boston fake.",
            "The user moved and now lives in boston hearsay.",
            "The user moved and now lives in boston dubious.",
            "The user moved and now lives in Boston (unconfirmed).",
            "According to a tip, the user moved and now lives in Boston.",
        )
        for text in refused:
            with self.subTest(text=text):
                with AgentMemory.open(tempfile.mkdtemp()) as memory:
                    old = memory.remember("memory:old", OLD_TEXT)["fact_uuid"]
                    memory.remember("memory:new", text)
                    recall = memory.recall(CURRENT_QUERY)
                    old_ev = self._ranking(recall, old)
                    self.assertNotIn("cross_fact_limitation", old_ev)

        accepted = (
            ("The user moved and now lives in Boston.", OLD_TEXT, CURRENT_QUERY),
            ("The user moved and now lives in New York City.", OLD_TEXT, CURRENT_QUERY),
            ("The user moved and now lives in Italy.", OLD_TEXT, CURRENT_QUERY),
            (
                "The user's preference changed; they now prefer coffee.",
                "The user prefers tea.",
                "What does the user currently prefer?",
            ),
            (
                "The updated project budget is 7000 dollars.",
                "The project budget is 6000 dollars.",
                "What is the current project budget?",
            ),
        )
        for text, old_text, query in accepted:
            with self.subTest(text=text):
                with AgentMemory.open(tempfile.mkdtemp()) as memory:
                    old = memory.remember("memory:old", old_text)["fact_uuid"]
                    memory.remember("memory:new", text)
                    recall = memory.recall(query)
                    self.assertTrue(self._ranking(recall, old).get("cross_fact_limitation"))

    def test_two_lowercase_value_and_unrelated_property_fail_closed(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old = memory.remember("memory:old", "The user prefers black tea.")["fact_uuid"]
            memory.remember("memory:new", "The user's preference changed; they now prefer green tea.")
            recall = memory.recall("What does the user currently prefer?")
            self.assertNotIn("cross_fact_limitation", self._ranking(recall, old))

        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old = memory.remember("memory:old", OLD_TEXT)["fact_uuid"]
            memory.remember("memory:new", "The user changed jobs and now works as a designer.")
            recall = memory.recall(CURRENT_QUERY)
            self.assertNotIn("cross_fact_limitation", self._ranking(recall, old))

    def test_cross_scope_source_never_shapes_visible_target(self):
        root = tempfile.mkdtemp()
        with AgentMemory.open(root, scope="project:a") as memory:
            old = memory.remember("memory:old", OLD_TEXT)["fact_uuid"]
        with AgentMemory.open(root, scope="project:b") as foreign:
            foreign.remember("memory:new", NEW_TEXT)
        with AgentMemory.open(root, scope="project:a") as memory:
            recall = memory.recall(CURRENT_QUERY)
            old_ev = self._ranking(recall, old)
            self.assertNotIn("cross_fact_limitation", old_ev)

    def test_correction_source_is_not_treated_as_caller_observation(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old = memory.remember("memory:old", OLD_TEXT)["fact_uuid"]
            memory.remember("memory:new", "The user lives in Seattle.")
            corrected = memory.correct(
                "memory:new",
                NEW_TEXT,
                evidence=_evidence(),
                risk_class="low",
            )
            self.assertTrue(corrected["committed"], corrected)
            recall = memory.recall(CURRENT_QUERY)
            old_ev = self._ranking(recall, old)
            self.assertEqual(old_ev.get("cross_fact_refusal_reason"), "source_mismatch")
            self.assertNotIn("cross_fact_limitation", old_ev)

    def test_poisoning_volume_does_not_accumulate_and_one_valid_source_limits_once(self):
        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old = memory.remember("memory:old", OLD_TEXT)["fact_uuid"]
            for index in range(12):
                memory.remember(
                    f"memory:poison:{index}",
                    f"The user might have moved and now lives in Boston{index}.",
                )
            valid = memory.remember("memory:valid", NEW_TEXT)["fact_uuid"]
            recall = memory.recall(CURRENT_QUERY)
            limitation = self._ranking(recall, old).get("cross_fact_limitation") or []
            self.assertEqual(len(limitation), 1)
            self.assertEqual(limitation[0]["source_fact_uuid"], valid)
            self.assertIn(old, recall["admitted"])

    def test_no_change_marker_is_write_order_invariant(self):
        pairs = (
            ("The user lives in Denver.", "The user lives in Boston."),
            ("The user works as a designer.", "The user works as an engineer."),
        )
        for first, second in pairs:
            with self.subTest(first=first, second=second):
                with AgentMemory.open(tempfile.mkdtemp()) as memory:
                    a = memory.remember("memory:a", first)["fact_uuid"]
                    memory.remember("memory:b", second)
                    recall = memory.recall("What is the user's current state?")
                    self.assertNotIn("cross_fact_limitation", self._ranking(recall, a))

    def test_declared_clocks_can_only_refuse_relation_direction(self):
        cases = (
            ("2026-01-01", "2019-01-01", "declared_clock_contradicts_direction"),
            ("2026-01-01", None, "declared_clock_unconfirmed"),
        )
        for old_clock, new_clock, reason in cases:
            with self.subTest(reason=reason):
                with AgentMemory.open(tempfile.mkdtemp()) as memory:
                    old = memory.remember(
                        "memory:old",
                        OLD_TEXT,
                        observed_at=old_clock,
                    )["fact_uuid"]
                    kwargs = {"observed_at": new_clock} if new_clock else {}
                    memory.remember("memory:new", NEW_TEXT, **kwargs)
                    recall = memory.recall(CURRENT_QUERY, reference_time="2026-09-27T12:00:00Z")
                    evidence = self._ranking(recall, old)
                    self.assertEqual(evidence.get("cross_fact_refusal_reason"), reason)
                    self.assertNotIn("cross_fact_limitation", evidence)

        with AgentMemory.open(tempfile.mkdtemp()) as memory:
            old, _new = self._seed(memory)
            recall = memory.recall(CURRENT_QUERY)
            self.assertTrue(self._ranking(recall, old).get("cross_fact_limitation"))


if __name__ == "__main__":
    unittest.main()
