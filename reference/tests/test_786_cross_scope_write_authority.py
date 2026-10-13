"""#786 preregistered tests: a governed write that targets an existing live logical memory
must be authorized for that memory's current canonical scope.

Authored before the repair and pinned on the unrepaired head (060e7cd): the negative cases
fail there, the positive controls pass there, and both must pass on the repaired head.

Independent identities throughout: tenant ``tenant:c786``, projects ``project:a`` (owner)
and ``project:b`` (other), actor ``agent:c786``. ``memory:never`` is an id nobody ever wrote;
the other project's refusals must be indistinguishable from it.

What a passing negative case proves (a changed refusal string alone is insufficient):
the owner's canonical head is preserved byte-for-byte, the owner's recall still admits it,
the other project gains no admitted or candidate access, no tombstone/dispute/rejected value
is recorded, and no persistence (fact, episode, generation) is left behind by the refusal.
"""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory, policy
from agentmem_ref.memory import procedural_memory as pm
from agentmem_ref.api import contract
from agentmem_ref.runtime.adapter import Clock, GovernedMemoryAdapter
from agentmem_ref.runtime.restart_runtime import RuntimeCheckpointConflict, RuntimeRecoveryError
from agentmem_ref.substrate import Episode, InMemoryTemporalGraph
import re
from tests.test_644_combined_independent import _evidence, _prop

TENANT = "tenant:c786"
ACTOR = "agent:c786"
QUERY = "Orrin gateway region"
HIST = {"mode": "historical"}
NEVER = "memory:never"


def _serial(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _blank() -> dict:
    return {"current_fact_uuid": None, "state_version": 0, "tombstoned": False, "events": []}


class _TwoProjects(unittest.TestCase):
    """One SQLite root; handles opened as ``project:a`` (owner) or ``project:b`` (other)."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name + "/m"
        self.memory = self.open()
        self.addCleanup(lambda: self.memory.closed or self.memory.close())

    def open(self, scope="project:a", **kwargs):
        return AgentMemory.open(self.root, tenant=TENANT, actor_id=ACTOR, scope=scope, purpose="c786", **kwargs)

    def reopen(self, scope="project:a"):
        self.memory.close()
        self.memory = self.open(scope)

    # -- fixtures -------------------------------------------------------------------------

    def seed(self, memory="memory:a", value="Oslo") -> str:
        out = self.memory.remember(memory, f"{QUERY} is {value}", proposition=_prop(value))
        self.assertTrue(out["committed"], out)
        return out["fact_uuid"]

    DISPUTE = {"evidence": _evidence("project:a", TENANT), "risk_class": "low"}

    def correct(self, memory, value, **kwargs) -> dict:
        kind = kwargs.pop("replacement_kind", "state_change")
        return self.memory.correct(memory, f"{QUERY} is {value}", evidence=_evidence("project:a", TENANT),
                                   risk_class="low", replacement_kind=kind, **kwargs)

    @property
    def adapter(self):
        return self.memory.runtime.adapter

    def fact(self, uuid):
        return self.adapter._substrate.get_fact(uuid)

    def canonical_head(self, memory="memory:a"):
        return self.memory._canonical_history(memory)["history"]["current_fact_uuid"]

    def snapshot(self, memory="memory:a") -> dict:
        """Everything the owner's canonical state consists of for one memory."""
        head = self.canonical_head(memory)
        fact = self.fact(head) if head else None
        return {
            "head": head,
            "fact": None if fact is None else _serial(fact.__dict__),
            "version": self.adapter.state_version(memory),
            "tombstoned": memory in self.adapter.tombstoned_ids(),
            "disputed": sorted(self.adapter._disputed),
            "rejected": _serial(self.adapter.rejected_value_history(memory, f"{QUERY} is Oslo")),
        }

    def assert_refused_like_unknown(self, outcome: dict, unknown: dict, *, forbidden: tuple[str, ...]):
        """The other project's result must be indistinguishable from targeting ``memory:never``."""
        self.assertFalse(outcome["committed"], outcome)
        self.assertIsNone(outcome.get("fact_uuid"))
        a, b = _serial(outcome).replace("memory:a", NEVER), _serial(unknown)
        self.assertEqual(a, b)
        for token in forbidden:
            self.assertNotIn(token, _serial(outcome), token)


# ====================================================================== positive controls

class OwnerWrites(_TwoProjects):
    def test_owner_writes_and_corrects_its_own_live_memory(self):
        first = self.seed()
        out = self.correct("memory:a", "Bergen")
        self.assertTrue(out["committed"], out)
        self.assertEqual(self.canonical_head(), out["fact_uuid"])
        self.assertIsNotNone(self.fact(first).invalid_at)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [out["fact_uuid"]])
        again = self.memory.remember("memory:a", f"{QUERY} is Bergen North", proposition=_prop("Bergen North"))
        self.assertTrue(again["committed"], again)
        self.assertEqual(self.canonical_head(), again["fact_uuid"])

    def test_owner_forgets_and_disputes_its_own_memory(self):
        first = self.seed()
        self.assertTrue(self.memory.dispute("memory:a", **self.DISPUTE)["committed"])
        self.assertIn(first, self.adapter._disputed)
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.assertTrue(self.memory.history("memory:a")["history"]["tombstoned"])

    def test_same_text_in_unrelated_memories_of_two_projects_stays_independent(self):
        first = self.seed("memory:a")
        self.reopen("project:b")
        other = self.memory.remember("memory:b", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        self.assertTrue(other["committed"], other)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [other["fact_uuid"]])
        self.assertEqual(self.canonical_head("memory:a"), first)
        self.reopen("project:a")
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [first])
        self.assertEqual(self.memory.history("memory:b")["history"], _blank())

    def test_other_project_creates_a_fresh_id_normally(self):
        self.reopen("project:b")
        out = self.memory.remember("memory:fresh", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.assertTrue(out["committed"], out)
        self.assertEqual(out["receipt"]["before_state"], "v0")
        self.assertEqual(out["receipt"]["after_state"], "v1")


# ====================================================================== the #786 failure class

class OtherProjectCannotWriteOverLiveHead(_TwoProjects):
    FORBIDDEN = ("project:a", "Oslo", "ref-0004", "scope", "project_scope", "isolation")

    def test_remember_onto_the_owners_live_head_is_refused_and_leaves_the_head_intact(self):
        first = self.seed()
        before = self.snapshot()
        self.reopen("project:b")
        out = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.assertFalse(out["committed"], out)
        self.assertIsNone(out.get("fact_uuid"))
        self.assertIsInstance(out.get("refusal"), str)
        # the refusal discloses nothing about the memory it protected
        self.assertEqual(out["receipt"]["before_state"], "v0")
        self.assertEqual(out["receipt"]["after_state"], "v0")
        for token in self.FORBIDDEN:
            self.assertNotIn(token, _serial(out), token)
        self.assertEqual(self.memory.history("memory:a")["history"], _blank())
        self.assertEqual(self.memory.recall(QUERY)["candidates"], [])
        # nothing of B's was persisted anywhere
        self.assertEqual(self.canonical_head(), first)
        self.reopen("project:a")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.memory.history("memory:a")["history"]["current_fact_uuid"], first)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [first])
        self.assertNotIn("Turku", _serial(self.memory.recall("Turku", temporal_intent=HIST)))

    def test_correct_onto_the_owners_live_head_reads_as_fact_not_found(self):
        first = self.seed()
        before = self.snapshot()
        self.reopen("project:b")
        out = self.correct("memory:a", "Turku")
        unknown = self.correct(NEVER, "Turku")
        self.assert_refused_like_unknown(out, unknown, forbidden=self.FORBIDDEN)
        self.reopen("project:a")
        self.assertEqual(self.snapshot(), before)
        self.assertIsNone(self.fact(first).invalid_at)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [first])

    def test_forget_and_permanent_forget_of_the_owners_memory_read_as_fact_not_found(self):
        first = self.seed()
        before = self.snapshot()
        self.reopen("project:b")
        for permanent in (False, True):
            with self.subTest(permanent=permanent):
                out = self.memory.forget("memory:a", permanent=permanent)
                unknown = self.memory.forget(NEVER, permanent=permanent)
                self.assert_refused_like_unknown(out, unknown, forbidden=self.FORBIDDEN)
        self.assertEqual(self.adapter.tombstoned_ids(), set())
        self.reopen("project:a")
        self.assertEqual(self.snapshot(), before)
        self.assertIsNotNone(self.fact(first))
        self.assertFalse(self.memory.history("memory:a")["history"]["tombstoned"])

    def test_dispute_of_the_owners_memory_reads_as_fact_not_found(self):
        first = self.seed()
        before = self.snapshot()
        self.reopen("project:b")
        out = self.memory.dispute("memory:a", **self.DISPUTE)
        unknown = self.memory.dispute(NEVER, **self.DISPUTE)
        self.assert_refused_like_unknown(out, unknown, forbidden=self.FORBIDDEN)
        # naming the owner's fact uuid directly grants nothing either
        by_uuid = self.memory.dispute("memory:a", fact_uuid=first, **self.DISPUTE)
        self.assertFalse(by_uuid["committed"], by_uuid)
        self.assertEqual(by_uuid.get("refusal"), unknown.get("refusal"))
        self.assertEqual(self.adapter._disputed, set())
        self.reopen("project:a")
        self.assertEqual(self.snapshot(), before)

    def test_refused_writes_leave_no_audit_trace_the_owner_can_see_and_no_generation(self):
        self.seed()
        self.reopen("project:b")
        self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.correct("memory:a", "Turku")
        self.memory.forget("memory:a")
        self.reopen("project:a")
        events = self.memory.history("memory:a")["history"]["events"]
        # refusal receipts are audit records; no commit, deletion or content reaches the owner
        self.assertEqual({e["event_type"] for e in events} & {"memory.delete", "memory.readmission_blocked"}, set())
        self.assertEqual(sum(e["event_type"] == "memory.commit" for e in events), 1)
        self.assertNotIn("Turku", _serial(events))
        self.assertEqual(self.memory.history("memory:a")["history"]["state_version"], 1)

    def test_wrong_scope_correction_after_restart_is_still_refused(self):
        first = self.seed()
        self.correct("memory:a", "Bergen")
        before = self.snapshot()
        for _ in range(2):  # the scope binding must survive every restart, not just the first
            self.reopen("project:b")
            out = self.correct("memory:a", "Turku")
            self.assertFalse(out["committed"], out)
            self.assertFalse(self.memory.remember("memory:a", f"{QUERY} is Turku")["committed"])
            self.reopen("project:a")
            self.assertEqual(self.snapshot(), before)
        self.assertIsNotNone(self.fact(first).invalid_at)  # the owner's own correction still stands
        self.assertTrue(self.correct("memory:a", "Narvik")["committed"])


# ====================================================================== forged scope metadata

class ForgedScopeMetadata(_TwoProjects):
    def test_protected_fields_cannot_be_overridden(self):
        self.reopen("project:b")
        for field in ("actor_id", "proposal_id", "state_snapshot", "charter_version"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.memory.remember("memory:a", "x", overrides={field: "forged"})

    def test_claiming_the_owners_project_ref_without_its_domain_is_refused(self):
        first = self.seed()
        self.reopen("project:b")
        out = self.memory.remember("memory:a", f"{QUERY} is Turku", overrides={"project_ref": "project:a"})
        self.assertFalse(out["committed"], out)
        with self.assertRaises(ValueError):  # the handle's required domains no longer bound: malformed
            self.memory.remember("memory:a", f"{QUERY} is Turku", overrides={"isolation_domain_refs": [TENANT, "project:a"]})
        out = self.memory.remember("memory:a", f"{QUERY} is Turku", overrides={"tenant_ref": "tenant:other"})
        self.assertFalse(out["committed"], out)
        self.assertEqual(self.canonical_head(), first)

    def test_full_redeclaration_of_the_owner_scope_is_the_host_declaring_that_scope(self):
        """DISPOSITION (documented, not a repair): ``overrides`` re-declares the proposal's scope
        exactly as ``AgentMemory.open(scope=...)`` would. The facade is not an authentication
        boundary -- whoever can pass overrides can open an owner handle -- so a complete
        re-declaration commits as the owner would. Partial forgeries (above) are refused."""
        self.seed()
        self.reopen("project:b")
        domains = [TENANT, "project:a"]
        out = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"),
                                   overrides={"scope": "project:a", "project_ref": "project:a",
                                              "isolation_domain_refs": domains,
                                              "required_isolation_domain_refs": domains})
        self.assertTrue(out["committed"], out)


# ====================================================================== deleted-id re-creation

class DeletedIdReuse(_TwoProjects):
    def test_other_project_recreates_a_deleted_id_as_an_isolated_generation(self):
        v1 = self.seed()
        v2 = self.correct("memory:a", "Bergen")["fact_uuid"]
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        owner_view = _serial(self.memory.history("memory:a"))
        self.reopen("project:b")
        again = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.assertTrue(again["committed"], again)
        # B's generation sees nothing of A's
        self.assertEqual(self.memory.history("memory:a")["history"]["current_fact_uuid"], again["fact_uuid"])
        historical = _serial(self.memory.recall(QUERY, temporal_intent=HIST))
        for token in (v1, v2, "Oslo", "Bergen"):
            self.assertNotIn(token, historical)
        # A's tombstoned view is unchanged and A can neither read nor write B's generation
        self.reopen("project:a")
        self.assertEqual(_serial(self.memory.history("memory:a")), owner_view)
        self.assertNotIn(again["fact_uuid"], _serial(self.memory.recall(QUERY, temporal_intent=HIST)))
        self.assertFalse(self.memory.remember("memory:a", f"{QUERY} is Narvik")["committed"])
        self.assertFalse(self.correct("memory:a", "Narvik")["committed"])
        self.assertFalse(self.memory.forget("memory:a")["committed"])
        self.reopen("project:b")
        self.assertEqual(self.canonical_head(), again["fact_uuid"])
        self.assertTrue(self.memory.forget("memory:a")["committed"])  # B governs its own generation

    def test_three_generations_keep_their_deletion_barriers(self):
        ctx_a = self.memory._handle_recall_context()
        a1 = self.seed()
        a2 = self.correct("memory:a", "Bergen")["fact_uuid"]
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen("project:b")
        ctx_b = self.memory._handle_recall_context()
        b1 = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))["fact_uuid"]
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen("project:a")
        a3 = self.seed(value="Narvik")
        when = {u: self.fact(u).created_at for u in (a1, a2, b1, a3)}
        adapter = self.adapter
        # the live generation resolves only for its owner, only from its own start
        self.assertEqual(adapter.version_in_effect("memory:a", when[a3], ctx_a), a3)
        self.assertIsNone(adapter.version_in_effect("memory:a", when[a3], ctx_b))
        # every deleted generation is a barrier for everyone
        for instant in (when[a1], when[a2], when[b1]):
            self.assertIsNone(adapter.version_in_effect("memory:a", instant, ctx_a), instant)
            self.assertIsNone(adapter.version_in_effect("memory:a", instant, ctx_b), instant)
        self.assertEqual(self.canonical_head(), a3)
        self.reopen("project:b")
        self.assertFalse(self.memory.remember("memory:a", f"{QUERY} is Tromso")["committed"])
        # B's view is its own deletion (DUR-DEL-001 owner-visible tombstone), never A's live generation
        view = self.memory.history("memory:a")["history"]
        self.assertEqual((view["current_fact_uuid"], view["tombstoned"], view["events"]), (None, True, []))
        self.assertNotIn(a3, _serial(self.memory.recall(QUERY, temporal_intent=HIST)))


# ====================================================================== concurrency

class CompetingWriters(_TwoProjects):
    def test_other_project_handle_open_at_the_same_time_cannot_replace_the_head(self):
        first = self.seed()
        other = self.open("project:b")
        try:
            out = other.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))
            self.assertFalse(out["committed"], out)
            fresh = other.remember("memory:b-own", f"{QUERY} is Turku", proposition=_prop("Turku"))
            self.assertTrue(fresh["committed"], fresh)
        finally:
            other.close()
        self.reopen("project:a")
        self.assertEqual(self.canonical_head(), first)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [first])

    def test_threads_racing_as_both_projects_never_move_the_owners_head(self):
        first = self.seed()
        self.memory.close()
        errors: list[BaseException] = []
        conflicts: list[BaseException] = []
        open_races: list[BaseException] = []
        committed_by_b: list[dict] = []

        def run(scope, n):
            try:
                try:
                    handle = self.open(scope)
                except RuntimeRecoveryError as exc:
                    # pre-existing SQLite-profile behaviour, outside #786: a recovery that reads
                    # while another handle publishes a checkpoint fails closed (digest mismatch)
                    # instead of opening on a torn view; it never admits or commits anything
                    open_races.append(exc)
                    return
                try:
                    for i in range(n):
                        try:
                            out = handle.remember("memory:a", f"{QUERY} is {scope}-{i}")
                        except RuntimeCheckpointConflict as exc:
                            conflicts.append(exc)  # designed outcome for a handle behind the generation
                            continue
                        if scope == "project:b" and out["committed"]:
                            committed_by_b.append(out)
                finally:
                    handle.close()
            except BaseException as exc:  # noqa: BLE001 - collected for the assertion
                errors.append(exc)

        threads = [threading.Thread(target=run, args=("project:b", 5)) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(committed_by_b, [])
        self.assertEqual(errors, [])
        self.memory = self.open()
        self.assertEqual(self.canonical_head(), first)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [first])


# ====================================================================== episode hypothesis

class DeniedProposalWithEpisode(_TwoProjects):
    """Hypothesis to falsify (issue #786 review comment): ``commit_proposal`` adds the optional
    episode to the substrate before policy evaluation and target admission."""

    def _proposal(self, operation="promotion", **kwargs):
        env = self.memory._proposal(target_reference="memory:a", operation=operation,
                                    fact_text=f"{QUERY} is Turku", **kwargs)
        return contract.proposal_from_envelope(env)

    def _commit_with_episode(self, proposal, uuid="episode:786"):
        episode = Episode(uuid=uuid, content=f"{QUERY} is Turku (raw)", source_description="chat",
                          valid_at="2026-01-01T00:00:00Z", group_id="project:b")
        with self.memory.runtime.serialization_lock:
            return self.memory.runtime.durable_runtime.commit_proposal(proposal, f"{QUERY} is Turku", episode)

    def test_cross_project_denial_persists_no_episode(self):
        first = self.seed()
        self.reopen("project:b")
        out = self._commit_with_episode(self._proposal())
        self.assertFalse(out.committed, out.refusal)
        self.assertIsNone(self.adapter._substrate.get_episode("episode:786"))
        self.assertNotIn(("add_episode", "episode:786"), list(getattr(self.adapter._substrate, "write_log", [])))
        self.reopen("project:b")
        self.assertIsNone(self.adapter._substrate.get_episode("episode:786"))
        self.assertNotIn("Turku", _serial(self.memory.recall("Turku raw", temporal_intent=HIST)))
        self.reopen("project:a")
        self.assertEqual(self.canonical_head(), first)
        self.assertNotIn("Turku", _serial(self.memory.recall("Turku raw", temporal_intent=HIST)))

    def test_policy_denial_in_own_scope_persists_no_episode(self):
        """A same-scope proposal parked by PAMA (``require_review``) must not retain its episode
        either: refusal receipts are the audit record, episodic content is not."""
        out = self._commit_with_episode(self._proposal(risk_class="high"), uuid="episode:parked")
        self.assertFalse(out.committed, out.decision.outcome)
        self.assertNotEqual(out.decision.outcome, policy.ALLOW_WITH_LEDGER)
        self.assertIsNone(self.adapter._substrate.get_episode("episode:parked"))
        self.reopen("project:a")
        self.assertIsNone(self.adapter._substrate.get_episode("episode:parked"))

    def test_committed_proposal_retains_its_episode(self):
        out = self._commit_with_episode(self._proposal(), uuid="episode:kept")
        self.assertTrue(out.committed, out.refusal)
        self.assertIsNotNone(self.adapter._substrate.get_episode("episode:kept"))
        self.reopen("project:a")
        self.assertIsNotNone(self.adapter._substrate.get_episode("episode:kept"))


# ====================================================================== independent review findings (36a6ef4d)

def _normalised(value, *, memory: str = "memory:a") -> str:
    """Byte comparison after folding volatile identifiers and the target id."""
    text = _serial(value).replace(memory, NEVER)
    text = re.sub(r"ref-\d+", "ref-X", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "T", text)
    return re.sub(r"facade:[0-9a-f]{64}", "facade:H", text)


class ReviewFindings(_TwoProjects):
    """Reproductions from the independent adversarial review of 36a6ef4d, kept as regressions."""

    PARTIAL = {"isolation_domain_refs": [TENANT, "project:a"], "project_ref": "project:a"}
    SUPERSET = {"isolation_domain_refs": [TENANT, "project:a", "project:b"], "project_ref": "project:a"}

    def test_f1_deleted_generations_rejected_values_neither_block_nor_reach_a_new_generation(self):
        self.seed()
        self.assertTrue(self.correct("memory:a", "Bergen", replacement_kind="error_correction")["committed"])
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen("project:b")
        again = self.memory.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        self.assertTrue(again["committed"], again)  # A's rejection of "Oslo" belongs to A's deleted generation
        view = self.memory.history("memory:a", fact_text=f"{QUERY} is Oslo")["history"]
        self.assertEqual(view["rejected_values"], [])
        self.assertNotIn("project:a", _serial(view))
        # the owner's own rejections still govern the owner's live generation
        self.reopen("project:a")
        self.seed("memory:c", "Oslo")
        self.assertTrue(self.correct("memory:c", "Bergen", replacement_kind="error_correction")["committed"])
        blocked = self.memory.remember("memory:c", f"{QUERY} is Oslo", proposition=_prop("Oslo"))
        self.assertEqual(blocked.get("refusal"), "rejected_value_requires_reconciliation")

    def test_f2_superset_domain_override_cannot_move_the_head_out_of_its_holders_reach(self):
        first = self.seed()
        before = self.snapshot()
        self.reopen("project:b")
        out = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"), overrides=self.SUPERSET)
        self.assertFalse(out["committed"], out)
        self.assertEqual((out["receipt"]["before_state"], out["receipt"]["after_state"]), ("v0", "v0"))
        self.assertFalse(self.correct("memory:a", "Turku", overrides=self.SUPERSET)["committed"])
        self.reopen("project:a")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.memory.history("memory:a")["history"]["current_fact_uuid"], first)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [first])
        self.assertTrue(self.correct("memory:a", "Bergen")["committed"])
        # DISPOSITION: a writer whose declared domains include the owner's project and whose
        # project_ref is the owner's is an eligible reader of the head; a deletion or dispute
        # stores no new scope, so it is admitted exactly as the owner's would be. Only writes
        # that would store a scope the holder cannot read (remember, correct) are refused.
        self.reopen("project:b")
        self.assertTrue(self.memory.dispute("memory:a", overrides=self.SUPERSET, **self.DISPUTE)["committed"])

    def test_f2_a_project_writer_cannot_capture_a_tenant_wide_memory(self):
        """Adapter level: a fact every project may read (domains (tenant,), no project) stays
        that way. A writer that would store it under one project is refused; a writer that
        keeps the tenant-wide scope supersedes it in place."""
        adapter = GovernedMemoryAdapter(InMemoryTemporalGraph(), tenant=TENANT, clock=Clock())
        wide = dict(scope=TENANT, isolation_domain_refs=(TENANT,), required_isolation_domain_refs=(), project_ref="")
        first = adapter.commit_proposal(_proposal(target_reference="mem:w", **wide), "window is Thursday")
        self.assertTrue(first.committed)
        capture = adapter.commit_proposal(_proposal(proposal_id="p2", target_reference="mem:w", scope=TENANT,
                                                    isolation_domain_refs=(TENANT, "project:b"),
                                                    required_isolation_domain_refs=(TENANT, "project:b"),
                                                    project_ref="project:b"), "window is Friday")
        self.assertFalse(capture.committed)
        self.assertEqual(capture.refusal, "target_unavailable")
        kept = adapter.commit_proposal(_proposal(proposal_id="p3", target_reference="mem:w", **wide), "window is Friday")
        self.assertTrue(kept.committed, kept.refusal)
        self.assertEqual(adapter.current_fact_uuid("mem:w"), kept.fact_uuid)

    def test_f3_inconsistent_partial_override_is_malformed_before_any_target_is_resolved(self):
        self.seed()
        self.correct("memory:a", "Bergen")
        self.reopen("project:b")
        for target in ("memory:a", NEVER):
            for op in (lambda m: self.memory.remember(m, f"{QUERY} is Turku", overrides=self.PARTIAL),
                       lambda m: self.correct(m, "Turku", overrides=self.PARTIAL),
                       lambda m: self.memory.forget(m, overrides=self.PARTIAL),
                       lambda m: self.memory.dispute(m, overrides=self.PARTIAL, **self.DISPUTE)):
                with self.subTest(target=target), self.assertRaises(ValueError) as caught:
                    op(target)
                self.assertNotIn("v2", str(caught.exception))

    def test_f7_another_scopes_refused_attempts_never_reach_the_live_generations_history(self):
        self.seed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen("project:b")
        self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.reopen("project:a")
        self.assertFalse(self.memory.remember("memory:a", f"{QUERY} is Narvik")["committed"])
        self.reopen("project:b")
        events = self.memory.history("memory:a")["history"]["events"]
        self.assertEqual([e["event_type"] for e in events],
                         ["memory.propose", "memory.authorize", "memory.commit", "memory.receipt"])
        # the owner of a live memory likewise sees no trace of another scope's attempt
        self.reopen("project:a")
        self.seed("memory:c")
        self.reopen("project:b")
        self.memory.remember("memory:c", f"{QUERY} is Turku")
        self.reopen("project:a")
        self.assertEqual(len(self.memory.history("memory:c")["history"]["events"]), 4)

    def test_f6_disposition_a_handle_behind_the_generation_reads_an_unknown_id(self):
        """DISPOSITION (pre-existing, unchanged): a second owner handle opened before another
        handle's write has no in-memory view of that memory; its correct/forget/dispute read
        ``fact_not_found`` exactly as before #786, while a write that reaches the checkpoint
        raises ``RuntimeCheckpointConflict``. Nothing commits."""
        self.memory.close()
        h1, h2 = self.open(), self.open()
        try:
            self.assertTrue(h1.remember("memory:a", f"{QUERY} is Oslo")["committed"])
            self.assertEqual(h2.correct("memory:a", f"{QUERY} is Bergen", evidence=_evidence("project:a", TENANT),
                                        risk_class="low").get("refusal"), "fact_not_found")
            with self.assertRaises(RuntimeCheckpointConflict):
                h2.remember("memory:a", f"{QUERY} is Bergen")
        finally:
            h1.close(); h2.close()
        self.memory = self.open()
        self.assertEqual(self.fact(self.canonical_head()).fact_text, f"{QUERY} is Oslo")


def _skill(scope, version=1, skill_id="deploy"):
    return pm.SkillArtifact(
        skill_id=skill_id, version=version, purpose="c786", scope=scope,
        isolation_domain_refs=(TENANT, scope), required_isolation_domain_refs=(TENANT, scope),
        procedure_markdown="# v\nok", provenance_refs=("evidence:c786",))


class ProceduralReviewFindings(unittest.TestCase):
    def setUp(self):
        from agentmem_ref.capabilities import ComponentRegistry
        self.substrate = InMemoryTemporalGraph()
        self.adapter = GovernedMemoryAdapter(self.substrate, tenant=TENANT, clock=Clock())
        registry = ComponentRegistry()
        registry.register(pm.reference_procedural_component())
        self.runtime = pm.ProceduralMemoryRuntime(adapter=self.adapter, substrate=self.substrate, registry=registry)

    def test_f5_propose_skill_does_not_disclose_another_scopes_version(self):
        self.assertTrue(self.runtime.commit_skill(self.runtime.propose_skill(_skill("project:a"), actor_id="agent:a")).commit.committed)
        with self.assertRaises(ValueError) as a:
            self.runtime.propose_skill(_skill("project:b", version=3), actor_id="agent:b")
        with self.assertRaises(ValueError) as b:
            self.runtime.propose_skill(_skill("project:b", version=3, skill_id="fresh"), actor_id="agent:b")
        self.assertEqual(str(a.exception), str(b.exception))

    def test_f4_revocation_carries_the_callers_scope_not_the_targets(self):
        head = self.runtime.commit_skill(self.runtime.propose_skill(_skill("project:a"), actor_id="agent:a")).commit.fact_uuid
        other = self.runtime.propose_skill(_skill("project:b"), actor_id="agent:b")
        self.assertFalse(self.runtime.commit_skill(other).commit.committed)
        bare = self.runtime.revoke_skill("deploy", actor_id="agent:b", evidence_refs=("ev:b",))
        self.assertFalse(bare.commit.committed)
        wrong = self.runtime.revoke_skill("deploy", actor_id="agent:b", evidence_refs=("ev:b",), scope="project:b",
                                          isolation_domain_refs=(TENANT, "project:b"),
                                          required_isolation_domain_refs=(TENANT, "project:b"), purpose="c786")
        self.assertFalse(wrong.commit.committed)
        self.assertEqual(wrong.commit.refusal, "fact_not_found")
        self.assertEqual(self.adapter.current_fact_uuid("skill:deploy"), head)
        owner = self.runtime.revoke_skill("deploy", actor_id="agent:a", evidence_refs=("ev:a",), scope="project:a",
                                          isolation_domain_refs=(TENANT, "project:a"),
                                          required_isolation_domain_refs=(TENANT, "project:a"), purpose="c786")
        self.assertTrue(owner.commit.committed, owner.commit.refusal)


# ====================================================================== adapter boundary

def _proposal(**overrides) -> policy.Proposal:
    base = dict(
        proposal_id="prop-786", actor_id="agent:a", charter_version="charter-1", target_reference="mem:shared",
        target_class=policy.M2, scope="shared:x", operation="promotion", current_strength="reinforced",
        proposed_strength="promoted", downstream_authority=policy.A1, reversibility="reversible",
        risk_class="low", evidence_refs=("ev:1",), tenant_ref=TENANT, purpose="assistance",
        isolation_domain_refs=("shared:x",), project_ref="", task_ref="",
    )
    base.update(overrides)
    return policy.Proposal(**base)


class AdapterBoundary(unittest.TestCase):
    """The check lives in the adapter: it governs every composition, not only the facade."""

    def setUp(self):
        self.substrate = InMemoryTemporalGraph()
        self.adapter = GovernedMemoryAdapter(self.substrate, tenant=TENANT, clock=Clock())

    def test_shared_domain_member_may_write_over_the_head_and_a_non_member_may_not(self):
        self.adapter.set_shared_domain_members("shared:x", ("agent:a", "agent:member"))
        first = self.adapter.commit_proposal(_proposal(), "window is Thursday")
        self.assertTrue(first.committed)
        member = self.adapter.commit_proposal(_proposal(proposal_id="p2", actor_id="agent:member"), "window is Friday")
        self.assertTrue(member.committed, member.refusal)
        stranger = self.adapter.commit_proposal(_proposal(proposal_id="p3", actor_id="agent:stranger"), "window is Monday")
        self.assertFalse(stranger.committed)
        self.assertEqual(self.adapter.current_fact_uuid("mem:shared"), member.fact_uuid)
        self.assertEqual(stranger.receipt["before_state"], "v0")
        self.assertEqual(stranger.receipt["after_state"], "v0")

    def test_task_scoped_head_requires_the_same_task(self):
        first = self.adapter.commit_proposal(
            _proposal(scope=TENANT, isolation_domain_refs=(TENANT,), project_ref="project:p", task_ref="task:1"), "x")
        self.assertTrue(first.committed)
        other_task = self.adapter.commit_proposal(
            _proposal(proposal_id="p2", scope=TENANT, isolation_domain_refs=(TENANT,), project_ref="project:p",
                      task_ref="task:2"), "y")
        self.assertFalse(other_task.committed)
        same_task = self.adapter.commit_proposal(
            _proposal(proposal_id="p3", scope=TENANT, isolation_domain_refs=(TENANT,), project_ref="project:p",
                      task_ref="task:1"), "z")
        self.assertTrue(same_task.committed, same_task.refusal)

    def test_delete_and_dispute_by_a_non_member_are_refused_as_not_found(self):
        self.adapter.set_shared_domain_members("shared:x", ("agent:a",))
        first = self.adapter.commit_proposal(_proposal(), "window is Thursday")
        stranger_delete = self.adapter.governed_delete(
            _proposal(proposal_id="d1", actor_id="agent:stranger", operation="pruning", proposed_strength="archived"),
            first.fact_uuid)
        missing_delete = self.adapter.governed_delete(
            _proposal(proposal_id="d2", actor_id="agent:stranger", operation="pruning", proposed_strength="archived"),
            "ref-missing")
        self.assertFalse(stranger_delete.committed)
        self.assertEqual(stranger_delete.refusal, missing_delete.refusal)
        stranger_dispute = self.adapter.governed_dispute(
            _proposal(proposal_id="x1", actor_id="agent:stranger", operation="other", proposed_strength="blocked"),
            first.fact_uuid)
        missing_dispute = self.adapter.governed_dispute(
            _proposal(proposal_id="x2", actor_id="agent:stranger", operation="other", proposed_strength="blocked"),
            "ref-missing")
        self.assertFalse(stranger_dispute.committed)
        self.assertEqual(stranger_dispute.refusal, missing_dispute.refusal)
        self.assertEqual(self.adapter.current_fact_uuid("mem:shared"), first.fact_uuid)
        self.assertEqual(self.adapter.tombstoned_ids(), set())
        self.assertEqual(self.adapter._disputed, set())


if __name__ == "__main__":
    unittest.main()
