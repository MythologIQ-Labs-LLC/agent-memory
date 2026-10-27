"""#786 preregistered adversarial tests: versioned store identity profiles (REAL SQLite).

Proposed contract (pending owner approval before promotion or release):

* ``scope_distinct_v1``: the only multi-project store profile. Every public logical
  key is bound to (tenant, project, key) by the facade itself, so identical public
  keys in different projects are different canonical memories and one project's
  occupancy is not observable from another.
* ``single_project_v1``: the default for a NEW store. Tenant-wide keys exactly as
  before, but the store is bound to the project that created it; any other project
  is refused at open, independently of which keys exist.
* An existing store without a profile record (pre-profile legacy) is never migrated
  or rewritten. It opens only for the single project its canonical scope metadata
  already contains; a legacy store holding several projects is refused.

The unchanged legacy collision oracle
(reference/security_falsifiers/test_786_legacy_collision_oracle.py) runs separately.
"""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
from agentmem_ref.api import contract
from agentmem_ref.api.scoped_identity import scope_distinct_key
from agentmem_ref.api.surface import (
    STORE_PROFILE_LEGACY,
    STORE_PROFILE_SCOPE_DISTINCT,
    STORE_PROFILE_SINGLE_PROJECT,
    STORE_PROFILE_FILE,
    StoreIdentityError,
)
from agentmem_ref.runtime.restart_runtime import RuntimeCheckpointConflict

TENANT = "tenant:786-profile"
ACTOR = "agent:786-profile"
KEY = "memory:shared-public-key"
A, B = "project:a", "project:b"


def _open(root, scope, **kwargs) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, **kwargs)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _observable(result: dict) -> tuple:
    """What a caller can learn from a mutation: commitment, outcome, refusal."""
    return (result.get("committed"), result.get("outcome"), result.get("refusal"))


def _history(memory: AgentMemory, key: str) -> dict:
    state = dict(memory.history(key)["history"])
    # Fact identifiers are store-local counters; occupancy is what must not leak.
    state["current_fact_uuid"] = state.get("current_fact_uuid") is not None
    state["events"] = len(state.get("events", []))
    return state


class SingleProjectDefaultTests(unittest.TestCase):
    def test_new_store_defaults_to_single_project_and_refuses_other_projects(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp, A) as owner:
                self.assertEqual(owner.store_profile, STORE_PROFILE_SINGLE_PROJECT)
                written = owner.remember(KEY, "Project A gateway is Oslo")
                self.assertTrue(written["committed"], written)
            with self.assertRaises(StoreIdentityError):
                _open(temp, B)
            with _open(temp, A) as owner:
                self.assertEqual(owner.history(KEY)["history"]["current_fact_uuid"], written["fact_uuid"])

    def test_refusal_is_independent_of_key_occupancy(self):
        # The oracle's attack: B probes whether A holds KEY. In a single-project store B
        # is refused at open whether A wrote KEY, a different key, or nothing at all.
        for seeded in (KEY, "memory:unrelated", None):
            with self.subTest(seeded=seeded), tempfile.TemporaryDirectory() as temp:
                with _open(temp, A) as owner:
                    if seeded:
                        self.assertTrue(owner.remember(seeded, "Project A value")["committed"])
                with self.assertRaises(StoreIdentityError) as refused:
                    _open(temp, B)
                self.assertNotIn(KEY, str(refused.exception))

    def test_other_tasks_of_the_bound_project_still_open(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp, A) as owner:
                self.assertTrue(owner.remember(KEY, "Project A value")["committed"])
            with _open(temp, A, task_ref="task:7") as task_handle:
                self.assertEqual(task_handle.store_profile, STORE_PROFILE_SINGLE_PROJECT)

    def test_profile_conflicts_are_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp, A):
                pass
            with self.assertRaises(StoreIdentityError):
                _open(temp, A, store_profile=STORE_PROFILE_SCOPE_DISTINCT)
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                _open(temp, A, store_profile="tenant_wide_multi_project")


class ScopeDistinctTests(unittest.TestCase):
    def _store(self, temp: str) -> None:
        with _open(temp, A, store_profile=STORE_PROFILE_SCOPE_DISTINCT) as owner:
            self.owner_fact = owner.remember(KEY, "Project A gateway is Oslo")["fact_uuid"]

    def test_identical_public_keys_commit_independently_and_indistinguishably(self):
        with tempfile.TemporaryDirectory() as occupied, tempfile.TemporaryDirectory() as vacant:
            self._store(occupied)
            with _open(occupied, B) as foreign:
                self.assertEqual(foreign.store_profile, STORE_PROFILE_SCOPE_DISTINCT)
                occupied_write = foreign.remember(KEY, "Project B gateway is Turku")
            with _open(vacant, B, store_profile=STORE_PROFILE_SCOPE_DISTINCT) as alone:
                vacant_write = alone.remember(KEY, "Project B gateway is Turku")
            self.assertTrue(occupied_write["committed"], occupied_write)
            self.assertEqual(_observable(occupied_write), _observable(vacant_write))
            with _open(occupied, A) as owner:
                self.assertEqual(owner.history(KEY)["history"]["current_fact_uuid"], self.owner_fact)
            with _open(occupied, B) as foreign:
                self.assertEqual(foreign.history(KEY)["history"]["current_fact_uuid"], occupied_write["fact_uuid"])

    def test_foreign_occupancy_is_not_observable_through_reads_or_mutations(self):
        with tempfile.TemporaryDirectory() as occupied, tempfile.TemporaryDirectory() as vacant:
            self._store(occupied)
            views = {}
            for label, root in (("occupied", occupied), ("vacant", vacant)):
                with _open(root, B, store_profile=STORE_PROFILE_SCOPE_DISTINCT) as probe:
                    views[label] = {
                        "history": _history(probe, KEY),
                        "recall": (lambda r: (r["candidates"], r["admitted"]))(
                            probe.recall("gateway Oslo", logical_memory_refs=[KEY])),
                        "correct": _observable(probe.correct(KEY, "Project B gateway is Bergen")),
                        "forget": _observable(probe.forget(KEY)),
                        "forget_permanent": _observable(probe.forget(KEY, permanent=True)),
                        "dispute": _observable(probe.dispute(KEY)),
                    }
            self.assertEqual(views["occupied"], views["vacant"])
            with _open(occupied, A) as owner:
                history = owner.history(KEY)["history"]
                self.assertEqual(history["current_fact_uuid"], self.owner_fact)
                self.assertFalse(history["tombstoned"])
                self.assertEqual(owner.recall("gateway Oslo")["admitted"], [self.owner_fact])

    def test_deletion_is_confined_to_the_deleting_project(self):
        with tempfile.TemporaryDirectory() as temp:
            self._store(temp)
            with _open(temp, B) as foreign:
                own = foreign.remember(KEY, "Project B gateway is Turku")["fact_uuid"]
                self.assertTrue(foreign.forget(KEY)["committed"])
                self.assertTrue(foreign.history(KEY)["history"]["tombstoned"])
                self.assertNotIn(own, foreign.recall("gateway Turku")["admitted"])
            with _open(temp, A) as owner:
                history = owner.history(KEY)["history"]
                self.assertFalse(history["tombstoned"])
                self.assertEqual(history["current_fact_uuid"], self.owner_fact)

    def test_profile_and_isolation_survive_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            self._store(temp)
            with _open(temp, B) as foreign:
                second = foreign.remember(KEY, "Project B gateway is Turku")["fact_uuid"]
            for scope, expected in ((A, self.owner_fact), (B, second), (A, self.owner_fact)):
                with _open(temp, scope) as reopened:
                    self.assertEqual(reopened.store_profile, STORE_PROFILE_SCOPE_DISTINCT)
                    self.assertEqual(reopened.history(KEY)["history"]["current_fact_uuid"], expected)

    def test_stale_cross_project_handle_fails_closed_without_loss(self):
        with tempfile.TemporaryDirectory() as temp:
            self._store(temp)
            first = _open(temp, A)
            second = _open(temp, B)
            try:
                written = second.remember(KEY, "Project B gateway is Turku")
                self.assertTrue(written["committed"])
                with self.assertRaises(RuntimeCheckpointConflict):
                    first.remember("memory:late", "stale handle write")
            finally:
                second.close()
                first.close()
            with _open(temp, A) as owner:
                self.assertEqual(owner.history(KEY)["history"]["current_fact_uuid"], self.owner_fact)
                self.assertIsNone(owner.history("memory:late")["history"]["current_fact_uuid"])
            with _open(temp, B) as foreign:
                self.assertEqual(foreign.history(KEY)["history"]["current_fact_uuid"], written["fact_uuid"])


class DirectInterfaceBypassTests(unittest.TestCase):
    def test_canonical_keys_are_namespaced_and_raw_keys_are_never_stored(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp, A, store_profile=STORE_PROFILE_SCOPE_DISTINCT) as owner:
                owner.remember(KEY, "Project A gateway is Oslo")
                adapter = owner.runtime.adapter
                self.assertIsNone(adapter.current_fact_uuid(KEY))
                self.assertIsNotNone(adapter.current_fact_uuid(scope_distinct_key(TENANT, A, KEY)))

    def test_reserved_and_foreign_canonical_keys_cannot_alias(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp, A, store_profile=STORE_PROFILE_SCOPE_DISTINCT) as owner:
                owner.remember(KEY, "Project A gateway is Oslo")
            foreign_canonical = scope_distinct_key(TENANT, A, KEY)
            with _open(temp, B) as foreign:
                for attempt in (foreign_canonical, "scope-key-v1:anything"):
                    with self.subTest(attempt=attempt):
                        for call in (lambda: foreign.remember(attempt, "alias"),
                                     lambda: foreign.history(attempt),
                                     lambda: foreign.forget(attempt),
                                     lambda: foreign.correct(attempt, "alias"),
                                     lambda: foreign.recall("gateway", logical_memory_refs=[attempt])):
                            with self.assertRaises(ValueError):
                                call()
            with _open(temp, A) as owner:
                self.assertEqual(owner.history(KEY)["history"]["state_version"], 1)

    def test_foreign_fact_uuid_cannot_be_disputed_by_another_project(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp, A, store_profile=STORE_PROFILE_SCOPE_DISTINCT) as owner:
                owner_fact = owner.remember(KEY, "Project A gateway is Oslo")["fact_uuid"]
            with _open(temp, B) as foreign:
                foreign.remember(KEY, "Project B gateway is Turku")
                aimed = foreign.dispute(KEY, fact_uuid=owner_fact)
                missing = foreign.dispute(KEY, fact_uuid="ref-does-not-exist")
                self.assertFalse(aimed["committed"])
                self.assertEqual(_observable(aimed), _observable(missing))
            with _open(temp, A) as owner:
                events = owner.history(KEY)["history"]["events"]
                self.assertFalse([e for e in events if "dispute" in str(e.get("event_type", ""))])

    def test_scope_distinct_store_cannot_be_reopened_with_tenant_wide_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp, A, store_profile=STORE_PROFILE_SCOPE_DISTINCT):
                pass
            with self.assertRaises(StoreIdentityError):
                _open(temp, A, store_profile=STORE_PROFILE_SINGLE_PROJECT)
            with _open(temp, B) as default_open:
                self.assertEqual(default_open.store_profile, STORE_PROFILE_SCOPE_DISTINCT)

    def test_overrides_cannot_reach_the_canonical_target(self):
        with tempfile.TemporaryDirectory() as temp:
            with _open(temp, A, store_profile=STORE_PROFILE_SCOPE_DISTINCT) as owner:
                owner.remember(KEY, "Project A gateway is Oslo")
            with _open(temp, B) as foreign:
                with self.assertRaises(ValueError):
                    foreign.remember("memory:other", "alias",
                                     overrides={"target_reference": scope_distinct_key(TENANT, A, KEY)})


class LegacyContainmentTests(unittest.TestCase):
    """Pre-profile stores: preserved, never migrated, restricted to one project."""

    def _legacy(self, temp: str, projects: tuple[str, ...]) -> None:
        with _open(temp, projects[0]) as owner:
            self.assertTrue(owner.remember(KEY, f"{projects[0]} value")["committed"])
            # Legacy multi-project data could only have been written before this
            # contract; reproduce it through the trusted host proposal layer.
            for project in projects[1:]:
                envelope = owner._proposal(target_reference=f"memory:{project}", operation="promotion",
                                           fact_text=f"{project} value")
                domains = [TENANT, project]
                envelope.update({"scope": project, "project_ref": project, "isolation_domain_refs": domains,
                                 "required_isolation_domain_refs": domains})
                outcome = owner.runtime.retain(contract.proposal_from_envelope(envelope), f"{project} value")
                self.assertTrue(outcome.committed)
        (Path(temp) / STORE_PROFILE_FILE).unlink()  # a store written before profiles existed

    def test_single_project_legacy_store_opens_for_its_project_without_migration(self):
        with tempfile.TemporaryDirectory() as temp:
            self._legacy(temp, (A,))
            with _open(temp, A) as owner:
                self.assertEqual(owner.store_profile, STORE_PROFILE_LEGACY)
                self.assertIsNotNone(owner.history(KEY)["history"]["current_fact_uuid"])
            self.assertFalse((Path(temp) / STORE_PROFILE_FILE).exists())
            with self.assertRaises(StoreIdentityError):
                _open(temp, B)

    def test_multi_project_legacy_store_is_refused_and_left_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            self._legacy(temp, (A, B))
            database = Path(temp) / "agent-memory.sqlite3"
            before = _digest(database)
            for scope in (A, B, "project:c"):
                with self.subTest(scope=scope), self.assertRaises(StoreIdentityError):
                    _open(temp, scope)
            self.assertEqual(_digest(database), before)
            self.assertFalse((Path(temp) / STORE_PROFILE_FILE).exists())

    def test_legacy_store_is_not_silently_promoted_to_scope_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            self._legacy(temp, (A,))
            with self.assertRaises(StoreIdentityError):
                _open(temp, A, store_profile=STORE_PROFILE_SCOPE_DISTINCT)
            self.assertFalse((Path(temp) / STORE_PROFILE_FILE).exists())


if __name__ == "__main__":
    unittest.main()
