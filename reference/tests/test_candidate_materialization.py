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


class MaterializationTests(_Store):
    """#591: facts that cannot become candidates are not materialized."""

    def _populate(self, users: int = 60, items: int = 5) -> None:
        for user in range(users):
            for item in range(items):
                self.write(f"u{user}:{item}", f"The user prefers tool {item} for project {user}.", _scope(f"u{user:02d}"))

    def test_only_surviving_candidates_are_materialized(self):
        self._populate()
        substrate = self.adapter._substrate
        context = _context("u07")
        search = substrate.search
        calls = []
        original = type(substrate)._fact_from_row

        def counting(row):
            calls.append(row["uuid"])
            return original(row)

        with mock.patch.object(type(substrate), "_fact_from_row", staticmethod(counting)):
            results = search("which tool does the user prefer", group_ids=[TENANT],
                             eligible=lambda fact: self.adapter.domain_eligible(fact, context),
                             eligible_identity=lambda uuid, group: self.adapter.domain_eligible_identity(uuid, group, context))
        self.assertEqual(len(results), 5)
        self.assertEqual(sorted(calls), sorted(fact.uuid for fact, _ in results))  # 5 of 300, not 300

    def test_identity_path_equals_full_materialization_path(self):
        self._populate(users=30)
        substrate = self.adapter._substrate
        for user in ("u00", "u07", "u29", "nobody"):
            context = _context(user)
            for query in ("which tool does the user prefer", "project 7", "tool 3", "unrelated words"):
                eligible = lambda fact, context=context: self.adapter.domain_eligible(fact, context)
                identity = lambda uuid, group, context=context: self.adapter.domain_eligible_identity(uuid, group, context)
                full = substrate.search(query, group_ids=[TENANT], eligible=eligible)
                fast = substrate.search(query, group_ids=[TENANT], eligible=eligible, eligible_identity=identity)
                self.assertEqual([(f.uuid, s, f) for f, s in fast], [(f.uuid, s, f) for f, s in full], (user, query))

    def test_identity_predicate_is_exactly_the_fact_predicate(self):
        self.write("a:1", "The deploy key rotates.", _scope("a"))
        self.write("a:task", "The deploy checklist.", _scope("a", task_ref="task:7"))
        self.write("b:1", "The deploy key rotates.", _scope("b"))
        self.adapter.set_shared_domain_members("space:s", ("agent:591",))
        self.write("s:1", "The deploy runbook.", {"scope": "space:s", "isolation_domain_refs": ["space:s"],
                                                  "required_isolation_domain_refs": ["space:s"], "project_ref": ""})
        contexts = [_context("a"), _context("b"), _context("a", task_ref="task:7"),
                    _context("a", target_domain_refs=("space:s",), project_ref=""),
                    _context("a", target_domain_refs=("space:s",), project_ref="", principal_ref="agent:other"),
                    _context("a", target_domain_refs=())]
        for fact in self.adapter._substrate.all_facts():
            for context in contexts:
                self.assertEqual(self.adapter.domain_eligible_identity(fact.uuid, fact.group_id, context),
                                 self.adapter.domain_eligible(fact, context))
        self.assertFalse(self.adapter.domain_eligible_identity("unknown-uuid", TENANT, _context("a")))  # unknown scope fails closed
        self.assertFalse(self.adapter.domain_eligible_identity(next(iter(self.adapter._fact_scope)), "tenant:other", _context("a")))

    def test_materialized_facts_are_still_checked_by_the_fact_predicate(self):
        uuid = self.write("a:1", "The deploy key rotates.", _scope("a"))
        results = self.adapter._substrate.search("deploy key", group_ids=[TENANT], eligible=lambda fact: False,
                                                 eligible_identity=lambda uuid, group: True)
        self.assertEqual(results, [])  # an over-permissive identity predicate cannot widen visibility
        self.assertEqual(self.adapter._substrate.search("deploy key", group_ids=[TENANT], eligible=None,
                                                        eligible_identity=lambda uuid, group: True)[0][0].uuid, uuid)


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
