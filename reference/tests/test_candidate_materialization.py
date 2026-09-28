"""#591: candidate formation must not depend on how facts are materialized.

These tests pin current candidate semantics (#548) independently of the SQLite
materialization strategy:

    raw discovery -> domain-eligible candidate formation -> canonical admission on
    every candidate -> ranking

The oracle below restates the pre-#591 path: materialize every tenant fact, apply the
adapter's own ``domain_eligible`` predicate, score lexical overlap, and sort by
(score desc, uuid). Every scenario compares the live runtime against it and pins
candidate identities, candidate order, refusals, and admitted order, not just recall
text. Candidate filtering is minimization, never authority: admission still evaluates
every candidate.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference"))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.runtime.adapter import RecallContext  # noqa: E402
from agentmem_ref.state import sqlite_substrate  # noqa: E402

TENANT = "tenant:591"


def _open(root: str) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id="agent:591", scope="user:a", purpose="591 tests")


def _scope(user: str, **extra) -> dict:
    scope = f"user:{user}"
    return {"scope": scope, "isolation_domain_refs": [TENANT, scope], "required_isolation_domain_refs": [TENANT, scope],
            "project_ref": scope, **extra}


def _context(user: str, **extra) -> RecallContext:
    scope = f"user:{user}"
    values = {"target_domain_refs": (TENANT, scope), "principal_ref": "agent:591", "project_ref": scope}
    values.update(extra)
    return RecallContext(**values)


class _Store(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = self._temp.name
        self.memory = _open(self.root)

    def tearDown(self) -> None:
        self.memory.close()
        self._temp.cleanup()

    @property
    def adapter(self):
        return self.memory.runtime.adapter

    def write(self, target: str, text: str, overrides: dict, **kwargs) -> str:
        result = self.memory.remember(f"memory:{target}", text, overrides=overrides, **kwargs)
        self.assertTrue(result["committed"], result)
        return result["fact_uuid"]

    def oracle(self, query: str, context: RecallContext) -> list[str]:
        """Pre-#591 semantics restated: full materialization, adapter predicate, overlap."""
        terms = sqlite_substrate._tokens(query)
        scored = []
        for fact in self.adapter._substrate.all_facts():
            if fact.group_id != TENANT or not self.adapter.domain_eligible(fact, context):
                continue
            overlap = terms & sqlite_substrate._tokens(fact.fact_text)
            if overlap:
                scored.append((-(len(overlap) / max(len(terms), 1)), fact.uuid))
        return [uuid for _, uuid in sorted(scored)]

    def recall(self, query: str, context: RecallContext) -> dict:
        return self.memory.recall(query, target_domain_refs=list(context.target_domain_refs),
                                  principal_ref=context.principal_ref, project_ref=context.project_ref,
                                  task_ref=context.task_ref or None)

    def pinned(self, query: str, context: RecallContext) -> dict:
        recalled = self.recall(query, context)
        refusals = {uuid: decision.get("refusal") for uuid, decision in recalled["admissions"].items()
                    if uuid not in recalled["admitted"]}
        return {"candidates": list(recalled["candidates"]), "admitted": list(recalled["admitted"]), "refusals": refusals,
                "ranking": {uuid: {k: v for k, v in (recalled["admissions"][uuid].get("ranking_evidence") or {}).items()}
                            for uuid in recalled["admitted"]}}

    def assert_matches_oracle(self, query: str, context: RecallContext) -> dict:
        state = self.pinned(query, context)
        self.assertEqual(state["candidates"], self.oracle(query, context))
        return state


class CandidateFormationTests(_Store):
    def test_scope_domain_project_task_and_shared_space(self):
        a1 = self.write("a:1", "The deploy key rotates on Mondays.", _scope("a"))
        a2 = self.write("a:2", "The deploy window opens on Mondays at noon.", _scope("a"))
        b1 = self.write("b:1", "The deploy key rotates on Fridays.", _scope("b"))
        task = self.write("a:task", "The deploy checklist lives in the task tracker.", _scope("a", task_ref="task:7"))
        required = self.write("a:req", "The deploy vault needs the compartment.",
                              {**_scope("a"), "isolation_domain_refs": [TENANT, "user:a", "compartment:x"],
                               "required_isolation_domain_refs": [TENANT, "user:a", "compartment:x"]})
        self.adapter.set_shared_domain_members("space:s", ("agent:591",))
        shared = self.write("s:1", "The deploy runbook is shared.",
                            {"scope": "space:s", "isolation_domain_refs": ["space:s"],
                             "required_isolation_domain_refs": ["space:s"], "project_ref": ""})

        state = self.assert_matches_oracle("deploy key Mondays", _context("a"))
        self.assertEqual(set(state["candidates"]), {a1, a2})               # b: wrong domain; task/required: excluded
        self.assertEqual(state["candidates"][0], a1)                         # higher overlap first
        with_task = self.assert_matches_oracle("deploy checklist", _context("a", task_ref="task:7"))
        self.assertIn(task, with_task["candidates"])
        self.assertNotIn(task, self.assert_matches_oracle("deploy checklist", _context("a"))["candidates"])
        self.assertNotIn(required, self.assert_matches_oracle("deploy vault", _context("a"))["candidates"])
        self.assertIn(required, self.assert_matches_oracle(
            "deploy vault", _context("a", target_domain_refs=(TENANT, "user:a", "compartment:x")))["candidates"])
        member = _context("a", target_domain_refs=("space:s",), project_ref="")
        self.assertEqual(self.assert_matches_oracle("deploy runbook", member)["candidates"], [shared])
        stranger = _context("a", target_domain_refs=("space:s",), project_ref="", principal_ref="agent:other")
        self.assertEqual(self.assert_matches_oracle("deploy runbook", stranger)["candidates"], [])
        self.assertNotIn(b1, state["candidates"])

    def test_tombstoned_and_derived_residue_stay_candidates_refused_by_admission(self):
        source = self.write("a:src", "The escrow code is 4417.", _scope("a"))
        derived = self.write("a:derived", "The escrow code summary says 4417.", _scope("a"), evidence_refs=[source])
        self.assertTrue(self.memory.forget("memory:a:src", overrides=_scope("a"))["committed"])
        state = self.assert_matches_oracle("escrow code", _context("a"))
        self.assertEqual(set(state["candidates"]), {source, derived})
        self.assertEqual(state["refusals"], {source: "tombstoned", derived: "derived_from_tombstoned_source"})
        self.assertEqual(state["admitted"], [])

    def test_write_semantics_and_pre_550_facts_are_both_candidates(self):
        modern = self.write("a:modern", "The user lives in Denver.", _scope("a"))
        legacy = self.write("a:legacy", "The user lived near Denver before.", _scope("a"))
        connection = self.adapter._substrate._connection
        row = connection.execute("SELECT attributes_json FROM facts WHERE uuid = ?", (legacy,)).fetchone()
        attributes = json.loads(row[0])
        attributes.pop("write_semantics")
        connection.execute("UPDATE facts SET attributes_json = ? WHERE uuid = ?", (json.dumps(attributes), legacy))
        self.assertIsNone(self.memory.write_semantics(legacy))
        state = self.assert_matches_oracle("user Denver", _context("a"))
        self.assertEqual(set(state["candidates"]), {modern, legacy})
        self.assertEqual(set(state["admitted"]), {modern, legacy})

    def test_large_tenant_small_scope(self):
        for user in range(60):
            for item in range(5):
                self.write(f"u{user}:{item}", f"The user prefers tool {item} for project {user}.", _scope(f"u{user:02d}"))
        state = self.assert_matches_oracle("which tool does the user prefer", _context("u07"))
        self.assertEqual(len(state["candidates"]), 5)
        self.assertEqual(len(state["admitted"]), 5)


class DurabilityTests(_Store):
    def _populate(self) -> None:
        for user in ("a", "b"):
            for item in range(4):
                self.write(f"{user}:{item}", f"The {user} team deploys service {item} on day {item}.", _scope(user))

    def test_restart_reproduces_candidates_admission_and_ranking(self):
        self._populate()
        before = self.pinned("team deploys service", _context("a"))
        self.memory.close()
        self.memory = _open(self.root)
        self.assertEqual(self.assert_matches_oracle("team deploys service", _context("a")), before)

    def test_rolled_back_write_leaves_candidates_unchanged(self):
        self._populate()
        before = self.pinned("team deploys service", _context("a"))
        runtime = self.memory.runtime.durable_runtime.base
        with mock.patch.object(type(runtime), "_persist_unlocked", side_effect=RuntimeError("injected")):
            with self.assertRaises(RuntimeError):
                self.memory.remember("memory:a:ghost", "The a team deploys service ghost.", overrides=_scope("a"))
        self.assertEqual(self.assert_matches_oracle("team deploys service", _context("a")), before)


if __name__ == "__main__":
    unittest.main()
