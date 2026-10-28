"""#816: durable writes on a runtime-owned SQLite store happen only inside a runtime generation.

Issue #816 reported that ``m.runtime.adapter.governed_recall(...)`` on a facade-owned SQLite
handle, followed by ``close()``, left a store whose next ``open`` failed with
``SQLite canonical substrate digest mismatch``. The adapter's identifier sequence lives in the
SQLite metadata table and is part of the canonical substrate digest; the direct call advanced it
in autocommit, outside ``SQLiteRestartSafeRuntime._transactional_operation``, so the digest the
last generation published no longer matched. A later facade operation hid the defect only because
its generation re-published whatever the live state had become.

The repair binds the store's identifier sequence to its transactional runtime: outside a
generation every governed act refuses with ``UngovernedDurableWrite`` before the clock,
the identifier sequence or any governance state moves, and the configuration binding follows
every base generation. The supported paths (the facade, and the runtime's own governed operations)
are unchanged.

The tests marked FAIL-FIRST fail on the unmodified #815 head ``77c472e6``; the record of that
run is ``reports/validation/816-runtime-owned-writes/``. Every byte-level assertion reads the
SQLite files through independent connections, never through the governed read path.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentmem_ref import AgentMemory  # noqa: E402
from agentmem_ref.api import contract  # noqa: E402
from agentmem_ref.memory import procedural_memory as pm  # noqa: E402
from agentmem_ref.runtime.restart_runtime import RuntimeCheckpointConflict, RuntimeRecoveryError  # noqa: E402
from agentmem_ref.state import sqlite_substrate  # noqa: E402
from agentmem_ref.state.sqlite_substrate import UNGOVERNED_WRITE_MESSAGE, UngovernedDurableWrite  # noqa: E402
# #786 store identity profiles: this module drives several projects through one tenant-wide store to
# exercise the canonical adapter gates; AgentMemory.open admits that only as scope_distinct_v1, so the
# test-only tenant-wide fixture reproduces the pre-profile store (tests/_tenant_wide_fixture.py).
from tests._tenant_wide_fixture import open_tenant_wide

TENANT = "tenant:816"
SCOPE = "project:816"
REFERENCE = Path(__file__).resolve().parents[1]


def _evidence(scope: str = SCOPE):
    skill = pm.SkillArtifact(
        skill_id="skill:816-correction",
        version=1,
        purpose="correct retained test memory",
        scope=scope,
        isolation_domain_refs=(TENANT, scope),
        required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# verify\nConfirm the correction against the current source.",
        provenance_refs=("evidence:816-source",),
    )
    return pm.evidence_for(skill)


def _db(root: Path) -> Path:
    return Path(root) / "agent-memory.sqlite3"


def _rows(root: Path) -> dict[str, list]:
    """Every row of every table, through an independent read-only connection."""

    uri = f"file:{_db(root)}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {table: sorted(map(tuple, connection.execute(f"SELECT * FROM {table}").fetchall()), key=repr) for table in tables}


def _governance(memory: AgentMemory) -> str:
    state = memory.runtime.adapter.export_checkpoint_state()
    return hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()


def _generation(memory: AgentMemory) -> int:
    return memory.runtime.durable_runtime.base._observed_generation


class _Store(unittest.TestCase):
    def setUp(self) -> None:
        self._folder = tempfile.TemporaryDirectory()
        self.root = Path(self._folder.name)

    def tearDown(self) -> None:
        self._folder.cleanup()

    def open(self, scope: str = SCOPE, actor: str = "agent:a", *, tenant_wide: bool = False) -> AgentMemory:
        # #786: a test that drives two projects through one store uses the test-only tenant-wide fixture.
        opener = open_tenant_wide if tenant_wide else AgentMemory.open
        memory = opener(self.root, tenant=TENANT, actor_id=actor, scope=scope, purpose="816 qualification")
        self.addCleanup(memory.close)
        return memory

    def proposal(self, memory: AgentMemory, ref: str, operation: str, text: str = ""):
        return contract.proposal_from_envelope(memory._proposal(target_reference=ref, operation=operation, fact_text=text))


class IssueReproduction(_Store):
    def test_direct_adapter_recall_then_close_leaves_the_store_reopenable(self):  # FAIL-FIRST
        memory = self.open()
        self.assertTrue(memory.remember("memory:x", "The deploy window is Thursday.")["committed"])
        with self.assertRaises(UngovernedDurableWrite):
            memory.runtime.adapter.governed_recall("deploy window", memory._handle_recall_context())
        memory.close()
        reopened = self.open()
        self.assertTrue(reopened.recall("deploy window")["returned"])

    def test_controls_from_the_issue_still_hold(self):
        for between in (lambda m: None, lambda m: m.recall("deploy window")):
            with self.subTest(between=between):
                self.tearDown()
                self.setUp()
                memory = self.open()
                memory.remember("memory:x", "The deploy window is Thursday.")
                between(memory)
                memory.close()
                self.open().close()


class RefusalIsExplicitAndChangesNothing(_Store):
    """Every governed act on the adapter is refused outside a generation, before anything moves."""

    def acts(self, memory: AgentMemory):
        adapter = memory.runtime.adapter
        context = memory._handle_recall_context()
        return {
            "governed_recall": lambda: adapter.governed_recall("deploy window", context),
            "commit_proposal": lambda: adapter.commit_proposal(
                self.proposal(memory, "memory:y", "promotion", "Lunch is at noon."), "Lunch is at noon."),
            "governed_delete": lambda: adapter.governed_delete(
                self.proposal(memory, "memory:x", "pruning"), self.fact),
            "governed_dispute": lambda: adapter.governed_dispute(self.proposal(memory, "memory:x", "other"), self.fact),
            "mint_id": adapter.mint_id,
            "now": adapter.now,
            "record_event": lambda: adapter.record_event("probe.event", "memory:x", "ref-probe"),
            "upgrade_canonical_derivation": adapter.upgrade_canonical_derivation,
        }

    def test_each_act_is_refused_and_leaves_rows_governance_and_generation_unchanged(self):  # FAIL-FIRST
        memory = self.open()
        written = memory.remember("memory:x", "The deploy window is Thursday.")
        self.fact = written["fact_uuid"]
        for name, act in self.acts(memory).items():
            with self.subTest(act=name):
                rows, governance, generation = _rows(self.root), _governance(memory), _generation(memory)
                with self.assertRaises(UngovernedDurableWrite) as raised:
                    act()
                self.assertEqual(str(raised.exception), UNGOVERNED_WRITE_MESSAGE)
                self.assertEqual(_rows(self.root), rows)
                self.assertEqual(_governance(memory), governance)
                self.assertEqual(_generation(memory), generation)
        memory.close()
        self.assertTrue(self.open().recall("deploy window")["returned"])

    def test_a_store_that_saw_refused_acts_is_identical_to_one_that_did_not(self):  # FAIL-FIRST
        def session(root: Path, interfere: bool) -> dict:
            memory = AgentMemory.open(root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="816 qualification")
            try:
                self.fact = memory.remember("memory:x", "The deploy window is Thursday.")["fact_uuid"]
                if interfere:
                    for act in self.acts(memory).values():
                        with self.assertRaises(UngovernedDurableWrite):
                            act()
                memory.recall("deploy window")
                memory.correct("memory:x", "The deploy window is Friday.", evidence=_evidence())
                memory.forget("memory:x", evidence=_evidence())
                memory.recall("deploy window")
            finally:
                memory.close()
            AgentMemory.open(root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="816 qualification").close()
            return _rows(root)

        with tempfile.TemporaryDirectory() as control, tempfile.TemporaryDirectory() as treated:
            self.assertEqual(session(Path(treated), True), session(Path(control), False))

    def test_storage_level_writes_stay_privileged_and_are_never_bound_by_close(self):
        """The substrate's storage methods are a privileged, ungoverned layer (fixtures and the
        migration tooling publish through them with an explicit checkpoint). #816 does not
        govern them; it guarantees close() never binds them and recovery still refuses them."""

        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        substrate = memory.runtime.adapter.checkpoint_substrate()
        with self.assertRaises(UngovernedDurableWrite):  # the governed identifier sequence is
            substrate._ids.next()
        substrate._connection.execute("UPDATE facts SET fact_text = 'The deploy window is never.'")
        rows = _rows(self.root)
        memory.close()
        self.assertEqual(_rows(self.root), rows, "close() publishes nothing")
        with self.assertRaisesRegex(RuntimeRecoveryError, "canonical substrate digest mismatch"):
            self.open()

    def test_the_refusal_discloses_nothing(self):
        memory = self.open()
        written = memory.remember("memory:secret", "The vault code is 4242.")
        with self.assertRaises(UngovernedDurableWrite) as raised:
            memory.runtime.adapter.governed_recall("vault code", memory._handle_recall_context())
        message = str(raised.exception)
        for leaked in ("4242", "vault", written["fact_uuid"], "memory:secret", TENANT, SCOPE):
            self.assertNotIn(leaked, message)
        self.assertEqual(raised.exception.args, (UNGOVERNED_WRITE_MESSAGE,))
        self.assertIsNone(raised.exception.__cause__)


class SupportedPathsStillWork(_Store):
    def test_facade_lifecycle_across_restarts(self):
        memory = self.open()
        self.assertTrue(memory.remember("memory:car", "Our car is a blue Honda Civic.")["committed"])
        self.assertTrue(memory.remember("memory:pet", "The cat is called Miso.")["committed"])
        memory.close()
        memory = self.open()
        corrected = memory.correct("memory:car", "Our car is a red Toyota Corolla.", evidence=_evidence())
        self.assertTrue(corrected["committed"], corrected)
        self.assertTrue(memory.forget("memory:pet", evidence=_evidence())["committed"])
        memory.close()
        memory = self.open()
        returned = memory.recall("car")["returned"]
        self.assertEqual(returned, [corrected["fact_uuid"]])
        self.assertEqual(memory.recall("cat Miso")["returned"], [])
        memory.close()

    def test_the_runtime_governed_operations_publish_and_reopen(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        before = _generation(memory)
        result = memory.runtime.recall("deploy window", memory._handle_recall_context())
        self.assertTrue(result.admitted)
        self.assertEqual(_generation(memory), before + 1)
        base = memory.runtime.durable_runtime.base
        base.governed_recall("deploy window", memory._handle_recall_context())
        self.assertEqual(_generation(memory), before + 2)
        memory.close()
        self.open().close()

    def test_the_facade_legacy_upgrade_still_runs_inside_its_generation(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        before = _generation(memory)
        memory.upgrade_canonical_derivation()
        self.assertEqual(_generation(memory), before + 1)
        memory.close()
        self.open().close()


class CloseAndFailureInjection(_Store):
    def test_repeated_close_and_close_after_a_refusal(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        with self.assertRaises(UngovernedDurableWrite):
            memory.runtime.adapter.mint_id()
        rows = _rows(self.root)
        memory.close()
        memory.close()
        self.assertEqual(_rows(self.root), rows, "close() publishes nothing")
        self.open().close()

    def test_a_handle_abandoned_without_close_reopens(self):
        memory = AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:a", scope=SCOPE, purpose="816 qualification")
        memory.remember("memory:x", "The deploy window is Thursday.")
        with self.assertRaises(UngovernedDurableWrite):
            memory.runtime.adapter.governed_recall("deploy window", memory._handle_recall_context())
        # no close(): the process "dies" holding the handle
        reopened = AgentMemory.open(self.root, tenant=TENANT, actor_id="agent:b", scope=SCOPE, purpose="816 qualification")
        self.assertTrue(reopened.recall("deploy window")["returned"])
        reopened.close()
        memory.close()

    def test_a_failed_publication_rolls_back_and_the_guard_still_holds(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        rows, governance = _rows(self.root), _governance(memory)
        with mock.patch.object(sqlite_substrate.SQLiteTemporalGraph, "append_runtime_journal",
                               side_effect=sqlite3.OperationalError("injected journal failure")):
            with self.assertRaises(sqlite3.OperationalError):
                memory.remember("memory:y", "Lunch is at noon.")
        self.assertEqual(_rows(self.root), rows)
        self.assertEqual(_governance(memory), governance)
        with self.assertRaises(UngovernedDurableWrite):
            memory.runtime.adapter.mint_id()
        self.assertTrue(memory.remember("memory:y", "Lunch is at noon.")["committed"])
        memory.close()
        self.assertEqual(len(self.open().recall("lunch noon")["returned"]), 1)


class ReviewFindings(_Store):
    """Independent review of 51452b88 (``reports/validation/816-runtime-owned-writes/REVIEW-816.md``)."""

    def test_f1_planner_and_preselected_admission_refuse_before_the_clock_ticks(self):
        from agentmem_ref.runtime.contextual_recall_adapter import admit_preselected_candidates

        memory = self.open()
        written = memory.remember("memory:x", "The deploy window is Thursday.")
        context = memory._handle_recall_context()
        for name, act in (
            ("admit_preselected_candidates", lambda: admit_preselected_candidates(
                memory.runtime.adapter, [written["fact_uuid"]], context, query_label="probe")),
            ("recall_planner.recall", lambda: memory.runtime.recall_planner.recall("deploy window", context)),
        ):
            with self.subTest(act=name):
                governance, rows = _governance(memory), _rows(self.root)
                with self.assertRaises(UngovernedDurableWrite):
                    act()
                self.assertEqual(_governance(memory), governance)
                self.assertEqual(_rows(self.root), rows)

    def test_f3_a_binding_failure_after_commit_keeps_the_committed_visibility_snapshot(self):
        # #821 moved the durable binding inside the generation (a failure there rolls everything
        # back: test_821 M6). What still runs after COMMIT is the owner's in-memory evidence update;
        # a failure there must likewise keep what the generation committed.
        from agentmem_ref.runtime import sqlite_runtime

        memory = self.open()
        durable = memory.runtime.durable_runtime
        snapshot = {"operation": {"required_projection_ids": []}}
        with mock.patch.object(sqlite_runtime, "checkpoint_evidence",
                               side_effect=OSError("injected binding failure")):
            with self.assertRaises(OSError):
                durable.persist_visibility_snapshot("op:816", snapshot)
        self.assertIn("op:816", durable.base.visibility_snapshots)  # SQLite committed it
        memory.recall("anything")  # the next generation re-binds and keeps it
        memory.close()
        self.assertIn("op:816", self.open().runtime.durable_runtime.base.visibility_snapshots)

    def test_f4_an_open_transaction_is_not_a_generation(self):
        import threading

        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        substrate = memory.runtime.adapter.checkpoint_substrate()
        # a bare substrate transaction the runtime never publishes
        with self.assertRaises(UngovernedDurableWrite):
            with substrate.transaction():
                memory.runtime.adapter.mint_id()
        # another thread, not holding the lock, while a generation is open
        inside, release, seen = threading.Event(), threading.Event(), {}

        def hold():
            inside.set()
            release.wait(5)
            return "held"

        holder = threading.Thread(target=lambda: seen.setdefault("a", memory.runtime.durable_runtime.run_governed_read(hold)))
        holder.start()
        inside.wait(5)
        try:
            memory.runtime.adapter.governed_recall("deploy window", memory._handle_recall_context())
            seen["b"] = "not refused"
        except UngovernedDurableWrite:
            seen["b"] = "refused"
        release.set()
        holder.join()
        self.assertEqual(seen, {"a": "held", "b": "refused"})
        memory.close()
        self.open().close()

    def test_f4_an_interrupt_inside_a_generation_rolls_back(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        rows, governance = _rows(self.root), _governance(memory)

        def interrupted():
            memory.runtime.adapter.mint_id()
            raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            memory.runtime.durable_runtime.run_governed_read(interrupted)
        substrate = memory.runtime.adapter.checkpoint_substrate()
        self.assertFalse(substrate._connection.in_transaction)
        self.assertEqual((_rows(self.root), _governance(memory)), (rows, governance))
        with self.assertRaises(UngovernedDurableWrite):
            memory.runtime.adapter.mint_id()
        self.assertTrue(memory.recall("deploy window")["returned"])
        memory.close()
        self.open().close()


    def test_n1_a_holder_of_the_substrate_cannot_declare_its_own_generation(self):
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        substrate = memory.runtime.adapter.checkpoint_substrate()
        for capability in (None, object()):
            with self.subTest(capability=capability):
                with self.assertRaises(UngovernedDurableWrite):
                    with substrate.transaction(), substrate.generation_opened(capability):
                        memory.runtime.adapter.governed_recall("deploy window", memory._handle_recall_context())
        nested = {}

        def inside():
            try:
                with substrate.generation_opened(memory.runtime.durable_runtime.base._generation_capability):
                    pass
            except RuntimeError as exc:
                nested["refused"] = str(exc)
            return memory.runtime.adapter.mint_id()  # the outer generation still holds its token

        self.assertTrue(memory.runtime.durable_runtime.run_governed_read(inside))
        self.assertIn("already open", nested["refused"])
        memory.close()
        self.open().close()

    def test_n2_an_interrupted_visibility_snapshot_is_not_kept(self):
        memory = self.open()
        durable = memory.runtime.durable_runtime
        with mock.patch.object(sqlite_substrate.SQLiteTemporalGraph, "append_runtime_journal", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                durable.persist_visibility_snapshot("op:interrupted", {"operation": {"required_projection_ids": []}})
        self.assertNotIn("op:interrupted", durable.base.visibility_snapshots)
        memory.recall("anything")
        memory.close()
        self.assertNotIn("op:interrupted", self.open().runtime.durable_runtime.base.visibility_snapshots)

_OTHER_PROCESS = textwrap.dedent(
    """
    import sys
    sys.path.insert(0, sys.argv[1])
    from agentmem_ref import AgentMemory
    m = AgentMemory.open(sys.argv[2], tenant=sys.argv[3], actor_id="agent:b", scope=sys.argv[4], purpose="816 qualification")
    assert m.remember("memory:y", "Lunch is at noon.")["committed"]
    m.close()
    """
)


class CrossProcessStaleHandle(_Store):
    def test_a_stale_handle_cannot_corrupt_another_process_generation(self):  # FAIL-FIRST
        stale = self.open()
        stale.remember("memory:x", "The deploy window is Thursday.")
        subprocess.run([sys.executable, "-c", _OTHER_PROCESS, str(REFERENCE), str(self.root), TENANT, SCOPE], check=True)
        published = _rows(self.root)
        with self.assertRaises(UngovernedDurableWrite):
            stale.runtime.adapter.governed_recall("lunch", stale._handle_recall_context())
        with self.assertRaises(RuntimeCheckpointConflict):  # the supported path's CAS, unchanged
            stale.recall("lunch")
        self.assertEqual(_rows(self.root), published)
        stale.close()
        fresh = self.open(actor="agent:c")
        self.assertEqual(len(fresh.recall("lunch noon")["returned"]), 1)


class IntegrityChecksAreNotRelaxed(_Store):
    def tamper(self, sql: str) -> None:
        with sqlite3.connect(_db(self.root)) as connection:
            connection.execute(sql)

    def seeded(self) -> None:
        memory = self.open()
        memory.remember("memory:x", "The deploy window is Thursday.")
        memory.close()

    def test_tampered_fact_text_fails_recovery(self):
        self.seeded()
        self.tamper("UPDATE facts SET fact_text = 'The deploy window is never.'")
        with self.assertRaisesRegex(RuntimeRecoveryError, "canonical substrate digest mismatch"):
            self.open()

    def test_an_identifier_sequence_advanced_out_of_band_fails_recovery(self):
        self.seeded()
        self.tamper("UPDATE agent_memory_meta SET value = CAST(value AS INTEGER) + 3 WHERE key = 'id_counter'")
        with self.assertRaisesRegex(RuntimeRecoveryError, "canonical substrate digest mismatch"):
            self.open()

    def test_tampered_governance_fails_recovery(self):
        self.seeded()
        self.tamper("UPDATE governance_log SET value_json = '{}' WHERE seq = (SELECT MAX(seq) FROM governance_log)")
        with self.assertRaises(RuntimeRecoveryError):
            self.open()


class SecurityRegressions(_Store):
    def test_cross_scope_correction_is_still_refused(self):
        owner = self.open(tenant_wide=True)
        written = owner.remember("memory:x", "The deploy window is Thursday.")
        owner.close()
        other = self.open(scope="project:other", actor="agent:b", tenant_wide=True)
        attempt = other.correct("memory:x", "The deploy window is never.", evidence=_evidence("project:other"))
        self.assertFalse(attempt["committed"], attempt)
        other.close()
        self.assertEqual(self.open(tenant_wide=True).recall("deploy window")["returned"], [written["fact_uuid"]])

    def test_deleted_lineage_stays_deleted_and_a_refused_direct_delete_changes_no_tombstone(self):
        memory = self.open()
        written = memory.remember("memory:x", "The deploy window is Thursday.")
        self.assertTrue(memory.forget("memory:x", evidence=_evidence())["committed"])
        tombstones = dict(memory.runtime.adapter._tombstones)
        with self.assertRaises(UngovernedDurableWrite):
            memory.runtime.adapter.governed_delete(self.proposal(memory, "memory:x", "pruning"), written["fact_uuid"])
        self.assertEqual(dict(memory.runtime.adapter._tombstones), tombstones)
        memory.close()
        reopened = self.open()
        recalled = reopened.recall("deploy window")
        self.assertEqual(recalled["returned"], [])
        self.assertNotIn(written["fact_uuid"], json.dumps(recalled, default=str))


class SemanticCacheReconciliation(unittest.TestCase):
    """#802 sidecar erasure holds with the guard in place, including after a refused direct act."""

    def test_permanent_forget_after_a_refused_direct_act_reconciles_the_sidecar_across_reopen(self):
        try:
            from tests import test_802_semantic_cache_deletion as t802
        except ImportError:  # run from inside reference/tests
            import test_802_semantic_cache_deletion as t802

        with tempfile.TemporaryDirectory() as folder, t802._provider():
            root = Path(folder)
            with t802._open(root) as memory:
                deleted, kept, cache = t802._seed_cached_facts(memory)
                with self.assertRaises(UngovernedDurableWrite):
                    memory.runtime.adapter.governed_recall("dog", memory._handle_recall_context())
                t802._authorized_permanent_forget(memory)
                self.assertEqual(t802._stored_fact_refs(cache), {kept})
            with t802._open(root) as memory:
                self.assertEqual(t802._stored_fact_refs(cache), {kept})
                self.assertNotIn(deleted, t802._canonical_fact_refs(root))
                verified = memory.verify_semantic_store()
                self.assertEqual((verified["mismatched"], verified["orphans"]), ([], []), verified)


if __name__ == "__main__":
    unittest.main()
