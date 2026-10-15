"""Lifecycle closure in return selection (#819 C3 slice 3, selection policy 2.2.0).

The weakness under test: the runtime's cross-fact stage (#671, typed slot, guards G1-G13) marks a
remembered state as ``limited_by_cross_fact_state_change`` by a later admitted fact, but
relevance selection (C2 onward) judged each fact by word overlap alone. "Where do I live now?"
returned "I live in Boston." and withheld "I moved to Denver.", which shares no topical word with
the question: the stale state was returned as if current. The pre-C2 ranked prefix returned both.

Closure: a selected fact that the ranking stage records as limited by another *admitted* fact
brings that fact into the set (``lifecycle_successor``), transitively. The relation comes only
from the runtime's own governed lifecycle evidence, never from memory text, and only admitted
facts can join, so scope, forgetting and correction are unchanged.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.memory import procedural_memory as pm

TENANT = "tenant:lifecycle"
SCOPE = "project:lifecycle"


def _evidence():
    skill = pm.SkillArtifact(
        skill_id="skill:lifecycle-closure", version=1, purpose="lifecycle test", scope=SCOPE,
        isolation_domain_refs=(TENANT, SCOPE), required_isolation_domain_refs=(TENANT, SCOPE),
        procedure_markdown="# verify\nConfirm the lifecycle change.", provenance_refs=("evidence:test",),
    )
    return pm.evidence_for(skill)


def _residence(value, *, change=False, replaces=None):
    proposition = {"subject": "user", "attribute": "residence", "value": value,
                   "assertion": "change" if change else "state", "cardinality": "single"}
    if replaces:
        proposition["replaces_value"] = replaces
    return proposition


class _Facade(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        self.memory = self.open(SCOPE)

    def tearDown(self):
        self.memory.close()
        self._dir.cleanup()

    def open(self, scope):
        return AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:t", scope=scope, purpose="lifecycle test")

    def put(self, ref, text, observed_at, proposition=None):
        kwargs = {"proposition": proposition} if proposition else {}
        outcome = self.memory.remember(ref, text, source_ref="user:u", observed_at=observed_at, **kwargs)
        self.assertTrue(outcome["committed"])
        return outcome["fact_uuid"]


class LifecycleClosure(_Facade):
    def test_limited_state_brings_its_later_state(self):
        boston = self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        denver = self.put("memory:home2", "I moved to Denver last month.", "2025-06-01",
                          _residence("Denver", change=True, replaces="Boston"))
        result = self.memory.recall("Where do I live now?")
        self.assertIn(boston, result["returned"])
        self.assertIn(denver, result["returned"])
        self.assertLess(result["returned"].index(denver), result["returned"].index(boston))  # ranked order kept
        self.assertEqual(result["admissions"][denver]["return_selection"]["basis"], "lifecycle_successor")
        self.assertEqual(result["return_policy"]["lifecycle_successor_count"], 1)

    def test_closure_is_transitive(self):
        boston = self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        denver = self.put("memory:home2", "I moved to Denver.", "2025-06-01",
                          _residence("Denver", change=True, replaces="Boston"))
        austin = self.put("memory:home3", "I moved again, to Austin.", "2025-09-01",
                          _residence("Austin", change=True, replaces="Denver"))
        result = self.memory.recall("Where do I live now?")
        self.assertEqual(set(result["returned"]), {boston, denver, austin})
        self.assertLess(result["returned"].index(austin), result["returned"].index(boston))
        self.assertEqual(result["admissions"][austin]["return_selection"]["basis"], "lifecycle_successor")

    def test_closure_never_reaches_beyond_admitted_facts(self):
        # A successor no route discovered is not admitted, so closure cannot add it (known gap:
        # same-slot discovery is not part of this slice).
        boston = self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        austin = self.put("memory:home3", "Relocated to Austin for the new job.", "2025-09-01",
                          _residence("Austin", change=True, replaces="Boston"))
        result = self.memory.recall("Where do I live now?")
        self.assertNotIn(austin, result["admitted"])
        self.assertEqual(result["returned"], [boston])

    def test_no_relation_means_no_closure(self):
        # Without governed lifecycle evidence (no typed proposition) nothing is inferred from text.
        boston = self.put("memory:home1", "I live in Boston.", "2025-01-01")
        moved = self.put("memory:home2", "This supersedes memory:home1. I moved to Denver.", "2025-06-01")
        result = self.memory.recall("Where do I live now?")
        self.assertEqual(result["returned"], [boston])
        self.assertNotEqual(result["admissions"][moved]["return_selection"]["basis"], "lifecycle_successor")

    def test_closure_does_not_need_a_current_cue(self):
        # Closure decides no currentness, so the #671 explicit-current gate (G1) does not apply.
        priya = self.put("memory:mgr1", "My manager is Priya.", "2025-01-01",
                         {"subject": "user", "attribute": "manager", "value": "Priya", "assertion": "state",
                          "cardinality": "single"})
        daniel = self.put("memory:mgr2", "Priya left; my team now reports to Daniel.", "2025-06-01",
                          {"subject": "user", "attribute": "manager", "value": "Daniel", "assertion": "change",
                           "cardinality": "single", "replaces_value": "Priya"})
        result = self.memory.recall("Who is my manager?")
        self.assertEqual(set(result["returned"]), {priya, daniel})
        ranking = result["admissions"][priya]["ranking_evidence"]
        self.assertNotIn("cross_fact_limitation", ranking)  # no applicability decision was made

    def test_hedged_change_does_not_close(self):
        boston = self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        hedged = dict(_residence("Denver", change=True, replaces="Boston"), flags={"hedged": True})
        maybe = self.put("memory:home2", "I might move to Denver.", "2025-06-01", hedged)
        result = self.memory.recall("Where do I live now?")
        self.assertEqual(result["returned"], [boston])
        self.assertNotEqual(result["admissions"][maybe]["return_selection"]["basis"], "lifecycle_successor")

    def test_change_from_another_source_does_not_close(self):
        boston = self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        other = self.memory.remember("memory:home2", "I moved to Denver.", source_ref="tool:web-search",
                                     observed_at="2025-06-01",
                                     proposition=_residence("Denver", change=True, replaces="Boston"))["fact_uuid"]
        result = self.memory.recall("Where do I live now?")
        self.assertEqual(result["returned"], [boston])
        self.assertNotEqual(result["admissions"][other]["return_selection"]["basis"], "lifecycle_successor")

    def test_ranked_prefix_is_unchanged(self):
        self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        self.put("memory:home2", "I moved to Denver.", "2025-06-01", _residence("Denver", change=True, replaces="Boston"))
        result = self.memory.recall("Where do I live now?", return_selection="ranked_prefix")
        self.assertEqual(result["returned"], result["admitted"])


class GovernanceUnchanged(_Facade):
    def test_forgotten_successor_is_never_added(self):
        boston = self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        denver = self.put("memory:home2", "I moved to Denver.", "2025-06-01",
                          _residence("Denver", change=True, replaces="Boston"))
        self.assertTrue(self.memory.forget("memory:home2", evidence=_evidence())["committed"])
        result = self.memory.recall("Where do I live now?")
        self.assertEqual(result["returned"], [boston])
        self.assertNotIn(denver, result["admitted"])

    def test_corrected_successor_returns_only_its_current_version(self):
        boston = self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        old = self.put("memory:home2", "I moved to Denver.", "2025-06-01",
                       _residence("Denver", change=True, replaces="Boston"))
        corrected = self.memory.correct("memory:home2", "I moved to Denver in May, not June.", evidence=_evidence())
        self.assertTrue(corrected["committed"])
        result = self.memory.recall("Where do I live now?")
        self.assertNotIn(old, result["returned"])
        self.assertNotIn(old, result["admitted"])
        self.assertIn(boston, result["returned"])

    def test_other_scope_successor_is_never_added(self):
        boston = self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        self.memory.close()  # one handle at a time on a store
        other = self.open("project:other")
        hidden = other.remember("memory:home2", "I moved to Denver.", source_ref="user:u", observed_at="2025-06-01",
                                proposition=_residence("Denver", change=True, replaces="Boston"))["fact_uuid"]
        other.close()
        self.memory = self.open(SCOPE)
        result = self.memory.recall("Where do I live now?")
        self.assertEqual(result["returned"], [boston])
        self.assertNotIn(hidden, result["admitted"])

    def test_selection_is_deterministic_across_reopen(self):
        self.put("memory:home1", "I live in Boston.", "2025-01-01", _residence("Boston"))
        self.put("memory:home2", "I moved to Denver.", "2025-06-01", _residence("Denver", change=True, replaces="Boston"))
        first = self.memory.recall("Where do I live now?")
        self.memory.close()
        self.memory = self.open(SCOPE)
        second = self.memory.recall("Where do I live now?")
        self.assertEqual(first["returned"], second["returned"])


if __name__ == "__main__":
    unittest.main()
