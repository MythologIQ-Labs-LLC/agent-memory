"""#786 security oracle v2: foreign occupancy under the supported store-profile contract.

Successor of ``test_786_legacy_collision_oracle.py`` (v1), which stays unchanged as a
historical probe of the retired tenant-wide multi-project interface. Like v1 this is a
standalone falsifier outside ordinary discovery; qualification runs it explicitly:

    PYTHONPATH=reference python reference/security_falsifiers/test_786_store_profile_oracle_v2.py -v

Method: matched controls. In the *occupied* store project A writes the probed public key;
in the *control* store A writes a different key with identical activity, so store-wide
counters and the deterministic clock advance identically. Every externally visible output
project B can obtain (results, refusals, receipts, identifiers, exceptions) must then be
byte-identical between the two. Any difference is a foreign-occupancy signal.

Supported surface under test: the ``AgentMemory`` facade method surface and
``ScopeDistinctMemory``. The canonical adapter and ``AgentMemory.runtime`` are host
objects; in-process Python offers no capability isolation, so a host must never hand them
to an untrusted caller. Their canonical gate is exercised here as defense in depth.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from agentmem_ref import AgentMemory
from agentmem_ref.api import surface
from agentmem_ref.api.scoped_identity import ScopeDistinctMemory, scope_distinct_key
from agentmem_ref.api.surface import (
    STORE_PROFILE_FILE,
    STORE_PROFILE_SCOPE_DISTINCT,
    STORE_PROFILE_SINGLE_PROJECT,
    StoreIdentityError,
)
from agentmem_ref.runtime.restart_runtime import RuntimeCheckpointConflict

ORACLE_ID = "agent-memory-786-store-profile-oracle-v2"
TENANT = "tenant:786-oracle-v2"
ACTOR = "agent:786-oracle-v2"
A, B = "project:a", "project:b"
KEY = "memory:public-collision-probe"
CONTROL_KEY = "memory:unrelated-control-key"
PROBED_IDS = tuple(f"ref-{n:04d}" for n in range(1, 41))
DATABASE = "agent-memory.sqlite3"


def _open(root, scope, **kwargs) -> AgentMemory:
    return AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope=scope, **kwargs)


def _seed(root, key: str | None, profile: str | None) -> None:
    with _open(root, A, store_profile=profile) as owner:
        if key is not None:
            assert owner.remember(key, "Project A private gateway is Oslo")["committed"]


def _outcome(call) -> object:
    """Everything a caller observes from one call: its full result or its exception."""
    try:
        return {"result": call()}
    except Exception as exc:  # noqa: BLE001 - the exception itself is the observable
        return {"raised": type(exc).__name__, "message": str(exc)}


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _probe_b(memory: AgentMemory) -> dict:
    """Project B's full observable surface against the probed public key."""
    observed = {
        "history_before": _outcome(lambda: memory.history(KEY)),
        "recall_seeded": _outcome(lambda: memory.recall("private gateway Oslo", logical_memory_refs=[KEY])),
        "recall_plain": _outcome(lambda: memory.recall("private gateway Oslo")),
        "remember": _outcome(lambda: memory.remember(KEY, "Project B gateway is Turku")),
        "correct": _outcome(lambda: memory.correct(KEY, "Project B gateway is Bergen")),
        "dispute_key": _outcome(lambda: memory.dispute(KEY)),
        "history_mid": _outcome(lambda: memory.history(KEY, fact_text="Project A private gateway is Oslo")),
    }
    # Identifier probing: sequential fact ids name facts of every project in the store.
    observed["dispute_by_id"] = {ref: _outcome(lambda ref=ref: memory.dispute(KEY, fact_uuid=ref))
                                 for ref in PROBED_IDS}
    observed["write_semantics_by_id"] = {ref: _outcome(lambda ref=ref: memory.write_semantics(ref))
                                         for ref in PROBED_IDS}
    observed["forget"] = _outcome(lambda: memory.forget(KEY))
    observed["forget_permanent"] = _outcome(lambda: memory.forget(KEY, permanent=True))
    observed["history_after"] = _outcome(lambda: memory.history(KEY))
    return observed


class _Matched(unittest.TestCase):
    profile = STORE_PROFILE_SCOPE_DISTINCT

    def matched(self, run) -> tuple[str, str]:
        """Run ``run(root)`` against an occupied and a control store; return both views."""
        views = []
        for key in (KEY, CONTROL_KEY):
            with tempfile.TemporaryDirectory() as temp:
                _seed(temp, key, self.profile)
                views.append(_canonical(run(temp)))
        return views[0], views[1]

    def assert_indistinguishable(self, run, label: str) -> None:
        occupied, control = self.matched(run)
        self.assertEqual(
            hashlib.sha256(occupied.encode()).hexdigest(), hashlib.sha256(control.encode()).hexdigest(),
            f"{label}: project B can distinguish project A's occupancy of the public key",
        )


class SingleProjectOracle(_Matched):
    profile = None  # the default for a new store: single_project_v1

    def test_second_project_open_refusal_is_occupancy_independent(self):
        refusals = []
        for key in (KEY, CONTROL_KEY, None):
            with tempfile.TemporaryDirectory() as temp:
                _seed(temp, key, None)
                refusals.append(_canonical(_outcome(lambda temp=temp: _open(temp, B))))
        self.assertEqual(len(set(refusals)), 1, refusals)
        self.assertIn(StoreIdentityError.__name__, refusals[0])

    def test_refusal_survives_restart_and_owner_activity(self):
        def run(temp):
            seen = [_outcome(lambda: _open(temp, B))]
            with _open(temp, A) as owner:
                owner.remember("memory:later", "later owner write")
            seen.append(_outcome(lambda: _open(temp, B)))
            return seen
        self.assert_indistinguishable(run, "single-project refusal after restart")


class ScopeDistinctOracle(_Matched):
    def test_full_b_surface_is_occupancy_independent(self):
        def run(temp):
            with _open(temp, B) as foreign:
                return _probe_b(foreign)
        self.assert_indistinguishable(run, "scope_distinct_v1 project B surface")

    def test_guarantee_holds_after_restart(self):
        def run(temp):
            with _open(temp, B) as foreign:
                first = _probe_b(foreign)
            with _open(temp, B) as reopened:
                return {"first": first, "after_restart": {
                    "history": _outcome(lambda: reopened.history(KEY)),
                    "recall": _outcome(lambda: reopened.recall("private gateway Oslo", logical_memory_refs=[KEY])),
                }}
        self.assert_indistinguishable(run, "scope_distinct_v1 after restart")

    def test_stale_concurrent_handles_fail_identically(self):
        def run(temp):
            first = _open(temp, A)
            second = _open(temp, B)
            try:
                first.remember("memory:a-concurrent", "owner concurrent write")
                stale = _outcome(lambda: second.remember(KEY, "Project B gateway is Turku"))
            finally:
                second.close()
                first.close()
            with _open(temp, B) as fresh:
                return {"stale": stale, "fresh": _probe_b(fresh)}
        occupied, control = self.matched(run)
        self.assertEqual(occupied, control)
        self.assertIn(RuntimeCheckpointConflict.__name__, occupied)

    def test_scope_distinct_wrapper_surface_is_occupancy_independent(self):
        def run(temp):
            parent = Path(temp) / "host"
            parent.mkdir()
            with ScopeDistinctMemory.open(parent, tenant=TENANT, actor_id=ACTOR, scope=A) as owner:
                owner.remember(KEY if Path(temp, "occupied").exists() else CONTROL_KEY, "A private")
            with ScopeDistinctMemory.open(parent, tenant=TENANT, actor_id=ACTOR, scope=B) as foreign:
                return [_outcome(lambda: foreign.history(KEY)), _outcome(lambda: foreign.remember(KEY, "B")),
                        _outcome(lambda: foreign.correct(KEY, "B2")), _outcome(lambda: foreign.forget(KEY))]
        views = []
        for occupied in (True, False):
            with tempfile.TemporaryDirectory() as temp:
                if occupied:
                    Path(temp, "occupied").touch()
                views.append(_canonical(run(temp)))
        self.assertEqual(views[0], views[1])


class FailSafeOracle(unittest.TestCase):
    """Tampering, missing metadata, interrupted creation and races fail safely."""

    def _digest(self, temp) -> str:
        return hashlib.sha256((Path(temp) / DATABASE).read_bytes()).hexdigest()

    def _record(self, temp) -> Path:
        return Path(temp) / STORE_PROFILE_FILE

    def _two_project_scope_distinct(self, temp) -> None:
        _seed(temp, KEY, STORE_PROFILE_SCOPE_DISTINCT)
        with _open(temp, B) as foreign:
            assert foreign.remember(KEY, "B value")["committed"]

    def assert_refused_everywhere(self, temp, scopes=(A, B, "project:c")) -> None:
        before = self._digest(temp)
        for scope in scopes:
            with self.subTest(scope=scope), self.assertRaises(StoreIdentityError):
                _open(temp, scope)
        self.assertEqual(self._digest(temp), before, "a refused open mutated the store")

    def test_truncated_or_malformed_record_is_refused(self):
        for corrupt in ('{"schema": "agent-memory-store-identity", "version"', "[]",
                        json.dumps({"schema": "agent-memory-store-identity", "version": 2,
                                    "profile": STORE_PROFILE_SINGLE_PROJECT, "tenant": TENANT, "bound_project": A})):
            with self.subTest(corrupt=corrupt[:30]), tempfile.TemporaryDirectory() as temp:
                _seed(temp, KEY, None)
                self._record(temp).write_text(corrupt, encoding="utf-8")
                self.assert_refused_everywhere(temp)

    def test_rebinding_a_single_project_record_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            _seed(temp, KEY, None)
            record = json.loads(self._record(temp).read_text())
            record["bound_project"] = B
            self._record(temp).write_text(json.dumps(record), encoding="utf-8")
            self.assert_refused_everywhere(temp)

    def test_downgrading_scope_distinct_to_single_project_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            self._two_project_scope_distinct(temp)
            self._record(temp).write_text(json.dumps({
                "schema": "agent-memory-store-identity", "version": 1, "profile": STORE_PROFILE_SINGLE_PROJECT,
                "tenant": TENANT, "bound_project": B}), encoding="utf-8")
            self.assert_refused_everywhere(temp)

    def test_upgrading_single_project_to_scope_distinct_discloses_nothing(self):
        # A tampered upgrade re-binds every caller key into its project namespace, so
        # the owner's tenant-wide keys become unreachable rather than observable.
        def run(temp):
            record = json.loads(self._record(temp).read_text())
            record.update(profile=STORE_PROFILE_SCOPE_DISTINCT, bound_project=None)
            self._record(temp).write_text(json.dumps(record), encoding="utf-8")
            with _open(temp, B) as foreign:
                return _probe_b(foreign)
        views = []
        for key in (KEY, CONTROL_KEY):
            with tempfile.TemporaryDirectory() as temp:
                _seed(temp, key, None)
                views.append(_canonical(run(temp)))
        self.assertEqual(views[0], views[1])

    def test_missing_record_falls_back_to_restricted_legacy(self):
        with tempfile.TemporaryDirectory() as temp:
            self._two_project_scope_distinct(temp)
            self._record(temp).unlink()
            self.assert_refused_everywhere(temp)
            self.assertFalse(self._record(temp).exists(), "a refused open must not rewrite metadata")
        with tempfile.TemporaryDirectory() as temp:
            _seed(temp, KEY, None)
            self._record(temp).unlink()
            self.assert_refused_everywhere(temp, scopes=(B,))
            with _open(temp, A) as owner:
                self.assertIsNotNone(owner.history(KEY)["history"]["current_fact_uuid"])
            self.assertFalse(self._record(temp).exists())

    def test_interrupted_creation_leaves_root_claimed_by_its_creator(self):
        from agentmem_ref.runtime.sqlite_composition import SQLiteConfiguredCompositionRuntime

        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(SQLiteConfiguredCompositionRuntime, "create", side_effect=OSError("power loss")):
                with self.assertRaises(OSError):
                    _open(temp, A)
            self.assertTrue(self._record(temp).exists())
            self.assertFalse((Path(temp) / DATABASE).exists())
            with self.assertRaises(StoreIdentityError):
                _open(temp, B)
            with self.assertRaises(StoreIdentityError):
                _open(temp, A, store_profile=STORE_PROFILE_SCOPE_DISTINCT)
            with _open(temp, A) as owner:
                self.assertTrue(owner.remember(KEY, "completed creation")["committed"])

    def test_interrupted_first_checkpoint_does_not_brick_a_claimed_root(self):
        import sqlite3
        from agentmem_ref.runtime.sqlite_runtime import SQLiteRestartSafeRuntime

        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(SQLiteRestartSafeRuntime, "checkpoint",
                                   side_effect=sqlite3.OperationalError("database is locked")):
                with self.assertRaises(sqlite3.OperationalError):
                    _open(temp, A)
            self.assertTrue((Path(temp) / DATABASE).exists(), "the database file was left behind")
            with self.assertRaises(StoreIdentityError):
                _open(temp, B)
            with _open(temp, A) as owner:
                self.assertTrue(owner.remember(KEY, "completed creation")["committed"])
            with _open(temp, A) as owner:
                self.assertIsNotNone(owner.history(KEY)["history"]["current_fact_uuid"])
        with tempfile.TemporaryDirectory() as temp:
            # An unclaimed (pre-profile) root in the same state keeps failing closed.
            with mock.patch.object(SQLiteRestartSafeRuntime, "checkpoint",
                                   side_effect=sqlite3.OperationalError("database is locked")):
                with self.assertRaises(sqlite3.OperationalError):
                    _open(temp, A)
            self._record(temp).unlink()
            from agentmem_ref.runtime.restart_runtime import RuntimeRecoveryError

            with self.assertRaises(RuntimeRecoveryError):
                _open(temp, A)

    def test_identity_claim_is_exclusive_first_writer_wins(self):
        # Deterministic complement to the race below: a later claimant always receives the
        # first claimant's record and is then refused by the ordinary identity check.
        with tempfile.TemporaryDirectory() as temp:
            path = self._record(temp)
            first = {"schema": "agent-memory-store-identity", "version": 1, "profile": STORE_PROFILE_SINGLE_PROJECT,
                     "tenant": TENANT, "bound_project": A}
            second = dict(first, bound_project=B)
            self.assertEqual(surface._claim_store_identity(path, first), first)
            self.assertEqual(surface._claim_store_identity(path, second), first)
            self.assertEqual(json.loads(path.read_text()), first)
            self.assertEqual(sorted(p.name for p in Path(temp).iterdir()), [STORE_PROFILE_FILE])
            with self.assertRaises(StoreIdentityError):
                _open(temp, B)

    def test_concurrent_first_opens_bind_exactly_one_identity(self):
        contenders = [(A, None), (B, None), ("project:c", None), ("project:d", STORE_PROFILE_SCOPE_DISTINCT)]
        for trial in range(15):
            with self.subTest(trial=trial), tempfile.TemporaryDirectory() as temp:
                barrier = threading.Barrier(len(contenders))
                outcomes: dict[str, str] = {}

                def contend(scope, profile):
                    barrier.wait()
                    try:
                        handle = _open(temp, scope, store_profile=profile)
                    except Exception as exc:  # noqa: BLE001
                        outcomes[scope] = type(exc).__name__
                        return
                    try:
                        handle.remember(f"memory:{scope}", f"{scope} first write")
                        outcomes[scope] = "opened"
                    except Exception as exc:  # noqa: BLE001
                        outcomes[scope] = "opened:" + type(exc).__name__
                    finally:
                        handle.close()

                threads = [threading.Thread(target=contend, args=c) for c in contenders]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
                record = json.loads(self._record(temp).read_text())
                opened = {scope for scope, outcome in outcomes.items() if outcome.startswith("opened")}
                # Every loser fails closed: an identity refusal, or a concurrent-recovery
                # / stale-generation refusal from the durable runtime. Never a crash.
                # ``OperationalError`` is SQLite's transient "database is locked" while another
                # contender creates the store; the reopen below proves no root is left unusable.
                fail_closed = {"StoreIdentityError", "RuntimeRecoveryError", "RuntimeCheckpointConflict",
                               "OperationalError"}
                for scope, outcome in outcomes.items():
                    self.assertIn(outcome.removeprefix("opened:") if outcome != "opened" else "opened",
                                  fail_closed | {"opened"}, outcomes)
                if record["profile"] == STORE_PROFILE_SINGLE_PROJECT:
                    # Exactly one project may ever open a single-project store.
                    self.assertEqual(opened, {record["bound_project"]}, outcomes)
                    for scope in set(outcomes) - opened:
                        self.assertEqual(outcomes[scope], "StoreIdentityError", outcomes)
                else:
                    self.assertIn("project:d", outcomes)
                    self.assertNotEqual(outcomes["project:d"], "StoreIdentityError", outcomes)
                # Afterwards the bound identity reopens a consistent store.
                bound = record["bound_project"] or "project:d"
                with _open(temp, bound) as reopened:
                    self.assertEqual(reopened.store_profile, record["profile"])


class BypassOracle(unittest.TestCase):
    """No supported caller input reaches another project's identity or canonical key."""

    def test_identity_bearing_inputs_are_refused_identically(self):
        attempts = {
            "canonical_key": lambda m: m.remember(scope_distinct_key(TENANT, A, KEY), "alias"),
            "reserved_prefix": lambda m: m.history("scope-key-v1:" + "0" * 64),
            "override_target": lambda m: m.remember("memory:x", "x", overrides={"target_reference": KEY}),
            "override_project": lambda m: m.remember("memory:x", "x", overrides={"project_ref": A, "scope": A}),
            "override_domains": lambda m: m.forget(KEY, overrides={"isolation_domain_refs": [TENANT, A]}),
            "recall_project": lambda m: m.recall("gateway", project_ref=A),
            "recall_domains": lambda m: m.recall("gateway", target_domain_refs=[TENANT, A]),
            "recall_principal": lambda m: m.recall("gateway", principal_ref="agent:someone-else"),
            "seed_canonical": lambda m: m.recall("gateway", logical_memory_refs=[scope_distinct_key(TENANT, A, KEY)]),
        }
        views = []
        for key in (KEY, CONTROL_KEY):
            with tempfile.TemporaryDirectory() as temp:
                _seed(temp, key, STORE_PROFILE_SCOPE_DISTINCT)
                with _open(temp, B) as foreign:
                    observed = {name: _outcome(lambda a=attempt: a(foreign)) for name, attempt in attempts.items()}
                for name, value in observed.items():
                    self.assertIn("raised", value, f"{name} was accepted: {value}")
                views.append(_canonical(observed))
        self.assertEqual(views[0], views[1])

    def test_wrapper_exposes_no_runtime_or_adapter(self):
        public = {name for name in dir(ScopeDistinctMemory) if not name.startswith("_")}
        self.assertEqual(public, {"open", "close", "remember", "history", "correct", "forget"})

    def test_canonical_gate_answers_foreign_ids_like_absent_ids(self):
        # Defense in depth below the facade: even a host-built proposal for project B
        # learns nothing from A's fact id that it would not learn from an unused id.
        with tempfile.TemporaryDirectory() as temp:
            _seed(temp, KEY, STORE_PROFILE_SCOPE_DISTINCT)
            with _open(temp, A) as owner:
                owner_fact = owner.history(KEY)["history"]["current_fact_uuid"]
            with _open(temp, B) as foreign:
                adapter = foreign.runtime.adapter
                envelope = foreign._proposal(target_reference=scope_distinct_key(TENANT, B, KEY), operation="pruning",
                                             current_strength="reinforced", proposed_strength="archived")
                from agentmem_ref.api import contract

                proposal = contract.proposal_from_envelope(envelope)
                # #816 (v7 integration): a governed act runs inside a runtime generation; outside one
                # both ids would raise the same UngovernedDurableWrite and the comparison would be vacuous.
                governed = foreign.runtime.durable_runtime.run_governed_read
                views = [_canonical(_outcome(lambda ref=ref: (lambda r: (r.committed, r.refusal, r.decision.outcome,
                                                                         r.receipt["before_state"]))(
                    governed(lambda: adapter.governed_delete(proposal, ref))))) for ref in (owner_fact, "ref-9999")]
        self.assertNotIn("raised", views[0])
        self.assertEqual(views[0], views[1])


if __name__ == "__main__":
    unittest.main()
