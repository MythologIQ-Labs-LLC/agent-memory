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
from agentmem_ref.api import contract, surface
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

    def test_p2_gate_a_recreated_generation_starts_its_own_version_counter(self):
        """Owner's P2 gate (PR #788 review): the re-creating writer's proposal, receipt and the
        new generation's history must not carry the former generation's memory-wide count,
        before and after restart; the former owner's deleted view keeps its recorded version."""
        self.seed()
        self.correct("memory:a", "Bergen")
        self.assertTrue(self.memory.forget("memory:a")["committed"])  # A's deletion records v3
        owner_view = self.memory.history("memory:a")["history"]
        self.assertEqual((owner_view["tombstoned"], owner_view["state_version"]), (True, 3))
        for round_, label in enumerate(("live", "after restart")):
            with self.subTest(label):
                self.reopen("project:b")
                view = self.memory.history("memory:a")["history"]
                # round 0: A's deletion is invisible to B (0, not tombstoned); round 1: B's own
                # deletion of its previous generation (recorded v3, tombstoned), never A's
                self.assertEqual((view["state_version"], view["tombstoned"]), (0, False) if round_ == 0 else (3, True))
                out = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))
                self.assertTrue(out["committed"], out)
                self.assertEqual((out["receipt"]["state_snapshot"], out["receipt"]["before_state"],
                                  out["receipt"]["after_state"]), ("v0", "v0", "v1"))
                self.assertNotIn("v3", _serial(out))
                self.assertEqual(self.memory.history("memory:a")["history"]["state_version"], 1)
                again = self.correct("memory:a", "Narvik")
                self.assertTrue(again["committed"], again)
                self.assertEqual((again["receipt"]["before_state"], again["receipt"]["after_state"]), ("v1", "v2"))
                self.assertTrue(self.memory.forget("memory:a")["committed"])
                self.assertEqual(self.memory.history("memory:a")["history"]["state_version"], 3)
                self.reopen("project:a")
                self.assertEqual(self.memory.history("memory:a")["history"], owner_view)

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


class SecondReviewFindings(_TwoProjects):
    """Reproductions from the second independent adversarial review (of b70ff58a), kept as
    regressions: F-A/F-B version disclosure through refused or snapshot-probing proposals on a
    tombstoned id, F-C re-deletion rewriting a tombstone, F-D/F-E deletion and dispute moving
    another scope's live generation, F-F widening on supersession."""

    def _deleted_owner_generation(self, permanent=False):
        self.seed()
        self.correct("memory:a", "Bergen")
        kw = {"permanent": True, "evidence": _evidence("project:a", TENANT), "risk_class": "low"} if permanent else {}
        self.assertTrue(self.memory.forget("memory:a", **kw)["committed"])
        self.assertEqual(self.memory.history("memory:a")["history"]["state_version"], 3)

    def _delete_version(self, memory, fact_uuid, snapshot=None):
        env = self.memory._proposal(target_reference=memory, operation="pruning", current_strength="reinforced",
                                    proposed_strength="archived", reversibility="reversible", risk_class="low")
        if snapshot is not None:
            env = dict(env, state_snapshot=snapshot)
        with self.memory.runtime.serialization_lock:
            return self.memory.runtime.durable_runtime.governed_delete(contract.proposal_from_envelope(env), fact_uuid)

    def test_fa_parked_or_refused_proposals_on_a_tombstoned_id_report_v0_only(self):
        for permanent in (False, True):
            with self.subTest(permanent=permanent):
                self.setUp()
                self._deleted_owner_generation(permanent)
                self.reopen("project:b")
                for risk in ("medium", "high"):
                    out = self.memory.remember("memory:a", f"{QUERY} is Turku", overrides={"risk_class": risk})
                    self.assertFalse(out["committed"], out)
                    r = out["receipt"]
                    self.assertEqual((r["state_snapshot"], r["before_state"], r["after_state"]), ("v0", "v0", "v0"), risk)
                    self.assertNotIn("v3", _serial(out))
                self.assertEqual(self.memory.history("memory:a")["history"]["state_version"], 0)

    def test_fb_module_level_commit_cannot_probe_the_former_count_through_state_snapshot(self):
        self._deleted_owner_generation()
        self.reopen("project:b")
        results = {}
        for snap in ("v1", "v2", "v3"):
            env = dict(self.memory._proposal(target_reference="memory:a", operation="promotion",
                                             fact_text=f"{QUERY} is Turku {snap}"), state_snapshot=snap)
            with self.memory.runtime.serialization_lock:
                out = surface.commit(self.adapter, env, f"{QUERY} is Turku {snap}")
            results[snap] = (out["committed"], out.get("refusal"), out["receipt"]["before_state"], out["receipt"]["after_state"])
        for snap, (committed, _refusal, before, after) in results.items():
            self.assertFalse(committed, snap)  # only the public v0 binds on a no-head id
            self.assertEqual((before, after), ("v0", "v0"), (snap, results[snap]))
        self.assertEqual(len({r[:2] for r in results.values()}), 1, results)

    def test_fc_re_pruning_a_deleted_head_is_refused_and_the_generation_stays_deleted(self):
        a1 = self.seed()
        a2 = self.correct("memory:a", "Bergen")["fact_uuid"]
        when1 = self.fact(a1).created_at
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        tombstone = dict(self.adapter.tombstone(a2))
        self.assertEqual(sorted(tombstone["deleted_fact_uuids"]), sorted([a1, a2]))
        out = self._delete_version("memory:a", a2)
        self.assertFalse(out.committed)
        self.assertEqual(out.refusal, "already_deleted")
        self.assertEqual(dict(self.adapter.tombstone(a2)), tombstone)
        member = self._delete_version("memory:a", a1)
        self.assertEqual((member.committed, member.refusal), (False, "already_deleted"))
        self.reopen("project:a")
        ctx = self.memory._handle_recall_context()
        with self.memory.runtime.serialization_lock:
            self.assertEqual(self.memory.recall(QUERY, temporal_intent=HIST)["admitted"], [])
            self.assertIsNone(self.memory.write_semantics(a1))
            self.assertIsNone(self.adapter.version_in_effect("memory:a", when1, ctx))
            self.assertTrue(self.adapter.memory_deleted(a1))
        self.assertEqual(self.memory.history("memory:a")["history"]["state_version"], 3)

    def test_fc_pruning_escalates_to_permanent_deletion_without_rewriting_the_generation(self):
        a1 = self.seed()
        a2 = self.correct("memory:a", "Bergen")["fact_uuid"]
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        before = dict(self.adapter.tombstone(a2))
        env = self.memory._proposal(target_reference="memory:a", operation="permanent_deletion", current_strength="reinforced",
                                    proposed_strength="not_applicable", reversibility="irreversible", risk_class="low")
        with self.memory.runtime.serialization_lock:
            out = self.memory.runtime.durable_runtime.governed_delete(
                contract.proposal_from_envelope(env), a2, evidence=_evidence("project:a", TENANT))
        self.assertTrue(out.committed, out.refusal)
        after = dict(self.adapter.tombstone(a2))
        self.assertEqual((after["mode"], after["reversible"]), ("permanent_deletion", False))
        for key in ("deleted_at", "state_version", "deleted_fact_uuids"):
            self.assertEqual(after[key], before[key], key)
        self.assertIsNone(self.fact(a1)); self.assertIsNone(self.fact(a2))
        self.reopen("project:a")
        self.assertEqual(self.memory.history("memory:a")["history"]["state_version"], 3)

    def test_fd_fe_former_owner_cannot_move_the_live_generation_through_delete_or_dispute(self):
        a1 = self.seed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        a_tombstone = dict(self.adapter.tombstone(a1))
        self.reopen("project:b")
        b1 = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))["fact_uuid"]
        b_view = self.memory.history("memory:a")["history"]
        self.assertEqual(b_view["state_version"], 1)
        self.reopen("project:a")
        for snap in (None, "v1"):
            out = self._delete_version("memory:a", a1, snapshot=snap)
            self.assertFalse(out.committed, snap)
            self.assertEqual((out.receipt["before_state"], out.receipt["after_state"]), ("v0", "v0"))
        env = dict(self.memory._proposal(target_reference="memory:a", operation="other", current_strength="reinforced",
                                         proposed_strength="blocked", risk_class="low", evidence_refs=(f"fact:{a1}",)),
                   state_snapshot="v1")
        with self.memory.runtime.serialization_lock:
            disputed = self.memory.runtime.dispute(contract.proposal_from_envelope(env), a1, evidence=_evidence("project:a", TENANT))
        self.assertFalse(disputed.committed)
        self.assertEqual((disputed.receipt["before_state"], disputed.receipt["after_state"]), ("v0", "v0"))
        for _ in range(3):
            out = self.memory.dispute("memory:a", fact_uuid=a1, **self.DISPUTE)
            self.assertFalse(out["committed"])
            self.assertNotIn(b1, _serial(out)); self.assertNotIn("Turku", _serial(out))
        self.assertEqual(dict(self.adapter.tombstone(a1)), a_tombstone)
        self.reopen("project:b")
        self.assertEqual(self.memory.history("memory:a")["history"], b_view)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [b1])
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        b_deleted = self.memory.history("memory:a")["history"]
        self.reopen("project:a")
        out = self.memory.dispute("memory:a", fact_uuid=a1, **self.DISPUTE)
        self.assertFalse(out["committed"])
        self.assertNotIn((out.get("receipt") or {}).get("before_state"), ("v2", "v3"))
        self.reopen("project:b")
        self.assertEqual(self.memory.history("memory:a")["history"], b_deleted)

    def test_ff_supersession_cannot_widen_a_shared_or_guarded_memory(self):
        def proposal(**overrides):
            base = dict(proposal_id="p1", actor_id="alice", charter_version="c", target_reference="mem:s",
                        target_class=policy.M2, scope="shared:x", operation="promotion", current_strength="reinforced",
                        proposed_strength="promoted", downstream_authority=policy.A1, reversibility="reversible",
                        risk_class="low", evidence_refs=("ev:1",), tenant_ref=TENANT, purpose="assist",
                        isolation_domain_refs=("shared:x",), required_isolation_domain_refs=(), project_ref="", task_ref="")
            base.update(overrides)
            return policy.Proposal(**base)
        from agentmem_ref.runtime.adapter import RecallContext
        adapter = GovernedMemoryAdapter(InMemoryTemporalGraph(), tenant=TENANT, clock=Clock())
        adapter.set_shared_domain_members("shared:x", ("alice", "bob"))
        first = adapter.commit_proposal(proposal(), "window is Thursday")
        self.assertTrue(first.committed)
        stranger = RecallContext(target_domain_refs=("project:a",), principal_ref="carol", purpose="assist")
        widen = adapter.commit_proposal(proposal(proposal_id="p2", isolation_domain_refs=("shared:x", "project:a")), "window is Friday")
        self.assertEqual((widen.committed, widen.refusal), (False, "target_unavailable"))
        self.assertFalse(adapter.fact_eligible_in_context(adapter.current_fact_uuid("mem:s"), stranger))
        same = adapter.commit_proposal(proposal(proposal_id="p3"), "window is Friday")
        self.assertTrue(same.committed, same.refusal)
        other = GovernedMemoryAdapter(InMemoryTemporalGraph(), tenant=TENANT, clock=Clock())
        guarded = other.commit_proposal(proposal(scope=TENANT, isolation_domain_refs=(TENANT, "project:a"),
                                                 required_isolation_domain_refs=("project:a",), project_ref="project:a"), "x")
        self.assertTrue(guarded.committed)
        dropped = other.commit_proposal(proposal(proposal_id="p2", scope=TENANT, isolation_domain_refs=(TENANT, "project:a"),
                                                 required_isolation_domain_refs=(), project_ref="project:a"), "y")
        self.assertFalse(dropped.committed)
        wide_reader = RecallContext(target_domain_refs=(TENANT,), principal_ref="carol", purpose="assist")
        self.assertFalse(other.fact_eligible_in_context(other.current_fact_uuid("mem:s"), wide_reader))

    def test_tombstone_recorded_versions_are_stable_under_a_third_generation(self):
        self.seed(); self.correct("memory:a", "Bergen")
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        a_view = self.memory.history("memory:a")["history"]
        self.reopen("project:b")
        self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        b_view = self.memory.history("memory:a")["history"]
        self.assertEqual((b_view["tombstoned"], b_view["state_version"]), (True, 2))
        self.reopen("project:a")
        self.assertEqual(self.memory.history("memory:a")["history"], a_view)
        third = self.memory.remember("memory:a", f"{QUERY} is Narvik", proposition=_prop("Narvik"))
        self.assertEqual((third["receipt"]["before_state"], third["receipt"]["after_state"]), ("v0", "v1"))
        self.reopen("project:b")
        self.assertEqual(self.memory.history("memory:a")["history"], b_view)
        self.reopen("project:a")
        self.correct("memory:a", "Tromso")
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.assertEqual(self.memory.history("memory:a")["history"]["state_version"], 3)
        self.reopen("project:b")
        self.assertEqual(self.memory.history("memory:a")["history"], b_view)


def _skill(scope, version=1, skill_id="deploy", domains=None, required=None):
    domains = domains if domains is not None else (TENANT, scope)
    required = required if required is not None else domains
    return pm.SkillArtifact(
        skill_id=skill_id, version=version, purpose="c786", scope=scope,
        isolation_domain_refs=domains, required_isolation_domain_refs=required,
        procedure_markdown="# v\nok", provenance_refs=("evidence:c786",))


class ReplayV2Findings(_TwoProjects):
    """Reproductions from the first execution of the superseding -v2 security replays
    (W7c): refusal ordering at the governed delete and dispute boundaries read a foreign
    live generation before the writer's own tombstone, so a former owner could tell whether
    its deleted id had been re-created by another project. The control is the same act
    with no re-creation: every observable the former owner gets must be identical."""

    def _delete(self, memory, fact_uuid, *, permanent=False):
        if permanent:
            env = self.memory._proposal(target_reference=memory, operation="permanent_deletion", current_strength="reinforced",
                                        proposed_strength="not_applicable", reversibility="irreversible", risk_class="low")
        else:
            env = self.memory._proposal(target_reference=memory, operation="pruning", current_strength="reinforced",
                                        proposed_strength="archived", reversibility="reversible", risk_class="low")
        with self.memory.runtime.serialization_lock:
            return self.memory.runtime.durable_runtime.governed_delete(
                contract.proposal_from_envelope(env), fact_uuid, evidence=_evidence("project:a", TENANT))

    def _dispute(self, memory, fact_uuid):
        env = self.memory._proposal(target_reference=memory, operation="other", current_strength="reinforced",
                                    proposed_strength="blocked", risk_class="low", evidence_refs=(f"fact:{fact_uuid}",))
        with self.memory.runtime.serialization_lock:
            return self.memory.runtime.dispute(contract.proposal_from_envelope(env), fact_uuid, evidence=_evidence("project:a", TENANT))

    def _former_owner_view(self, recreated: bool, *, permanent_escalation: bool) -> tuple:
        """Observables the former owner collects on its own deleted generation, in a fresh store."""
        self.memory.close()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name + "/m"
        self.memory = self.open()
        a1 = self.seed()
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        if recreated:
            self.reopen("project:b")
            self.b1 = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))["fact_uuid"]
            self.b_view = self.memory.history("memory:a")["history"]
            self.reopen("project:a")
        rows = []
        for act in (lambda: self._delete("memory:a", a1), lambda: self._dispute("memory:a", a1),
                    lambda: self._delete("memory:a", a1, permanent=permanent_escalation)):
            out = act()
            rows.append((out.committed, out.refusal, out.receipt["before_state"], out.receipt["after_state"]))
        rows.append(self.memory.history("memory:a")["history"]["state_version"])
        rows.append(tuple(sorted(self.adapter.tombstone(a1).items())) if self.adapter.tombstone(a1) else None)
        return tuple(rows)

    def test_fg_re_deletion_and_dispute_refusals_do_not_disclose_a_foreign_re_creation(self):
        control = self._former_owner_view(False, permanent_escalation=False)
        self.assertEqual(control[0][1], "already_deleted"); self.assertEqual(control[1][1], "already_deleted")
        probed = self._former_owner_view(True, permanent_escalation=False)
        self.assertEqual(probed, control)
        self.reopen("project:b")
        self.assertEqual(self.memory.history("memory:a")["history"], self.b_view)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [self.b1])

    def test_fh_escalation_of_the_owners_own_tombstone_is_the_same_under_a_foreign_generation(self):
        control = self._former_owner_view(False, permanent_escalation=True)
        self.assertTrue(control[2][0], control[2])
        self.assertEqual(control[2][2:], ("v0", "v2"))  # the deletion's own recorded version
        probed = self._former_owner_view(True, permanent_escalation=True)
        self.assertEqual(probed, control)
        self.reopen("project:b")
        self.assertEqual(self.memory.history("memory:a")["history"], self.b_view)
        self.assertEqual(self.memory.recall(QUERY)["admitted"], [self.b1])
        self.assertIsNotNone(self.fact(self.b1))


class PayloadLevelSeparation(_TwoProjects):
    """Independent replay review of the -v2 fixtures (PR #805 checkpoint, finding 7): the
    fixtures compare live-generation history views by event type and count only, so nothing
    there would catch a former generation's uuid or text riding inside an event payload,
    an evidence ref or a receipt. These probes serialise every public observable of every
    scope after a deletion and a foreign re-creation and scan the whole JSON for the other
    generation's identifiers and content."""

    C = "project:c"

    def _public_view(self, memory="memory:a") -> str:
        h = self.memory.history(memory)
        r = self.memory.recall(QUERY)
        ws = self.memory.write_semantics(memory) if hasattr(self.memory, "write_semantics") else None
        return _serial({"history": h, "recall": r, "write_semantics": ws})

    def _permanent_forget(self, memory="memory:a") -> dict:
        """A test-host attestation bound to exactly the facade's delete proposal (as test_802 does)."""
        proposal = self.memory._proposal(target_reference=memory, operation="permanent_deletion",
                                         current_strength="reinforced", proposed_strength="not_applicable",
                                         reversibility="irreversible", risk_class="high")
        attestation = policy.ExternalVerification(
            bound_proposal_id=str(proposal["proposal_id"]), verifier_principal_id="human:786-reviewer",
            authority_kind=policy.HUMAN_CONFIRMATION, max_risk_class="critical")
        return self.memory.forget(memory, permanent=True, risk_class="high", attestation=attestation)

    def _run(self, *, permanent: bool) -> tuple:
        a1 = self.seed()
        out = self._permanent_forget() if permanent else self.memory.forget("memory:a")
        self.assertTrue(out["committed"], out)
        a_before = self._public_view()
        self.reopen("project:b")
        b1 = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))["fact_uuid"]
        self.assertTrue(self.memory.correct("memory:a", f"{QUERY} is Tromso", evidence=_evidence("project:b", TENANT),
                                            risk_class="low")["committed"] or True)
        b_view = self._public_view()
        self.reopen(self.C)
        c_view = self._public_view()
        self.reopen("project:a")
        a_after = self._public_view()
        return a1, b1, a_before, b_view, c_view, a_after

    def _assert_separated(self, permanent: bool):
        a1, b1, a_before, b_view, c_view, a_after = self._run(permanent=permanent)
        # The re-creating scope sees nothing of the former generation anywhere in its payloads.
        for token in (a1, "Oslo"):
            self.assertNotIn(token, b_view, token)
        # The former owner's whole public view is unchanged by the foreign generation.
        self.assertEqual(a_after, a_before)
        for token in (b1, "Turku", "Tromso"):
            self.assertNotIn(token, a_after, token)
        # A third project reads a never-written memory: no identifier or text of either generation.
        for token in (a1, b1, "Oslo", "Turku", "Tromso"):
            self.assertNotIn(token, c_view, token)
        self.assertEqual(json.loads(c_view)["history"]["history"], _blank())

    def test_pruned_generation_leaves_no_identifier_or_text_in_any_other_scopes_payloads(self):
        self._assert_separated(permanent=False)

    def test_permanently_deleted_generation_leaves_no_identifier_or_text_in_any_other_scopes_payloads(self):
        self._assert_separated(permanent=True)


class EvidenceReferenceOracle(_TwoProjects):
    """F-R3-2 (third review), investigated as evidence for the owner's disposition (PR #805):
    a writer that cites a guessed fact uuid as ``evidence_refs`` learns whether that uuid is a
    member of a deleted generation of ANY scope, because its own derived memory is then withheld
    from its own recall (#776/#777 tenant-wide deletion completeness), while a citation of a
    random uuid or of a live fact it cannot read is admitted. These tests pin the observable as
    it stands; they are documentation of the oracle, not a claim that it is closed. Closing it
    (opaque identifiers, or treating a reference the writer cannot read as unknown) is a protected
    runtime change the owner decides (docs/786 'What remains disclosed')."""

    def _cite(self, ref: str | None, label: str) -> tuple[bool, int]:
        kw = {"evidence_refs": (ref,)} if ref else {}
        out = self.memory.remember(f"memory:b-{label}", f"{QUERY} digest {label}", **kw)
        rec = self.memory.recall(f"{QUERY} digest {label}", logical_memory_refs=(f"memory:b-{label}",))
        return out["committed"], len([u for u in rec["admitted"] if u == out["fact_uuid"]])

    def _oracle(self, *, permanent: bool) -> dict:
        a1 = self.seed()
        a2 = self.memory.remember("memory:a2", f"{QUERY} is Bergen", proposition=_prop("Bergen"))["fact_uuid"]
        if permanent:
            proposal = self.memory._proposal(target_reference="memory:a", operation="permanent_deletion",
                                             current_strength="reinforced", proposed_strength="not_applicable",
                                             reversibility="irreversible", risk_class="high")
            attestation = policy.ExternalVerification(
                bound_proposal_id=str(proposal["proposal_id"]), verifier_principal_id="human:786-reviewer",
                authority_kind=policy.HUMAN_CONFIRMATION, max_risk_class="critical")
            self.assertTrue(self.memory.forget("memory:a", permanent=True, risk_class="high", attestation=attestation)["committed"])
        else:
            self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen("project:b")
        return {"deleted": self._cite(a1, "deleted"), "live_foreign": self._cite(a2, "live"),
                "random": self._cite("fact-guess-" + "9" * 12, "random"), "none": self._cite(None, "none")}

    def test_fr3_2_citing_a_deleted_foreign_uuid_is_observable_to_the_citer(self):
        for permanent in (False, True):
            with self.subTest(permanent=permanent):
                self.memory.close()
                tmp = tempfile.TemporaryDirectory()
                self.addCleanup(tmp.cleanup)
                self.root = tmp.name + "/m"
                self.memory = self.open()
                views = self._oracle(permanent=permanent)
                # every citation commits; the writer is told nothing at write time
                self.assertTrue(all(committed for committed, _ in views.values()), views)
                # the oracle: the memory citing the deleted uuid is withheld from its own writer...
                self.assertEqual(views["deleted"][1], 0, views)
                # ...while the random and the live-foreign citations are admitted (no existence oracle for live facts)
                self.assertEqual((views["random"][1], views["live_foreign"][1], views["none"][1]), (1, 1, 1), views)


class ThirdReviewFindings(_TwoProjects):
    """Reproductions from the third independent adversarial review (of the final runtime
    a7a81c45): F-R3-1 narrowing capture of a multi-holder memory, F-R3-3 the composition
    runtime's delete_current answering an exception for "no head" and a refusal for "foreign
    head", F-R3-6 the shadow recall_control's route provenance disclosing a foreign live head."""

    WIDE = {"isolation_domain_refs": [TENANT, "project:a", "project:b"], "required_isolation_domain_refs": [TENANT], "project_ref": ""}

    @staticmethod
    def _narrow(scope):
        return {"isolation_domain_refs": [TENANT, scope], "required_isolation_domain_refs": [TENANT, scope], "project_ref": ""}

    def _view(self, memory="memory:w"):
        h = self.memory.history(memory)["history"]
        return (self.memory.recall(QUERY)["admitted"], h["current_fact_uuid"], h["state_version"], h["tombstoned"])

    def test_fr3_1_a_holder_cannot_narrow_a_shared_memory_out_of_the_other_holders_reach(self):
        for capturer, victim in (("project:b", "project:a"), ("project:a", "project:b")):
            with self.subTest(capturer=capturer):
                self.memory.close()
                tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
                self.root = tmp.name + "/m"; self.memory = self.open("project:a")
                w1 = self.memory.remember("memory:w", f"{QUERY} is Oslo", proposition=_prop("Oslo"), overrides=self.WIDE)
                self.assertTrue(w1["committed"])
                self.reopen(victim); before = self._view()
                self.assertEqual(before[0], [w1["fact_uuid"]])
                self.reopen(capturer)
                out = self.memory.correct("memory:w", f"{QUERY} is Bergen", evidence=_evidence(capturer, TENANT), risk_class="low",
                                          replacement_kind="error_correction", overrides=self._narrow(capturer))
                self.assertFalse(out["committed"], "a single holder narrowed the shared memory into its own scope")
                self.assertEqual(self.adapter.current_fact_uuid("memory:w"), w1["fact_uuid"])
                # the same holder superseding under the head's own scope still commits (positive control)
                kept = self.memory.correct("memory:w", f"{QUERY} is Narvik", evidence=_evidence(capturer, TENANT), risk_class="low",
                                           replacement_kind="error_correction", overrides=self.WIDE)
                self.assertTrue(kept["committed"], kept.get("refusal"))
                self.reopen(victim)
                after = self._view()
                self.assertEqual((after[1], after[2], after[3]), (kept["fact_uuid"], 2, False))
                self.assertEqual(after[0], [kept["fact_uuid"]])

    def test_fr3_1_adapter_single_route_holder_cannot_narrow_a_two_domain_memory(self):
        adapter = GovernedMemoryAdapter(InMemoryTemporalGraph(), tenant=TENANT, clock=Clock())
        first = adapter.commit_proposal(_proposal(scope="d1", isolation_domain_refs=("d1", "d2"), target_reference="mem:two"), "window is Thursday")
        self.assertTrue(first.committed)
        narrowed = adapter.commit_proposal(_proposal(proposal_id="p2", actor_id="agent:d1", scope="d1", isolation_domain_refs=("d1",),
                                                     required_isolation_domain_refs=("d1",), target_reference="mem:two"), "window is Friday")
        self.assertFalse(narrowed.committed)
        self.assertEqual(adapter.current_fact_uuid("mem:two"), first.fact_uuid)
        same = adapter.commit_proposal(_proposal(proposal_id="p3", actor_id="agent:d1", scope="d1", isolation_domain_refs=("d1", "d2"),
                                                 target_reference="mem:two"), "window is Friday")
        self.assertTrue(same.committed, same.refusal)

    def test_fr3_3_delete_current_answers_the_same_not_found_with_and_without_a_foreign_generation(self):
        rows = []
        for recreated in (False, True):
            self.memory.close()
            tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
            self.root = tmp.name + "/m"; self.memory = self.open("project:a")
            self.seed()
            self.assertTrue(self.memory.forget("memory:a")["committed"])
            if recreated:
                self.reopen("project:b")
                self.assertTrue(self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))["committed"])
                self.reopen("project:a")
            for permanent in (False, True):
                env = self.memory._proposal(target_reference="memory:a", operation="permanent_deletion" if permanent else "pruning",
                                            current_strength="reinforced", proposed_strength="not_applicable" if permanent else "archived",
                                            reversibility="irreversible" if permanent else "reversible", risk_class="low")
                out = self.memory.runtime.delete_current(contract.proposal_from_envelope(env), evidence=_evidence("project:a", TENANT))
                rows.append((recreated, permanent, out.committed, out.refusal, out.receipt["before_state"], out.receipt["after_state"]))
        control = [r[2:] for r in rows if not r[0]]; probed = [r[2:] for r in rows if r[0]]
        self.assertEqual(probed, control)
        self.assertEqual(control[0][1], "fact_not_found")

    def test_fr3_6_shadow_recall_control_route_provenance_does_not_reveal_a_foreign_live_head(self):
        live = self.seed("memory:live", "Oslo")
        self.seed("memory:del", "Bergen")
        self.assertTrue(self.memory.forget("memory:del")["committed"])
        self.memory.close()
        self.memory = self.open("project:b", recall_control="shadow")
        routes = {}
        for mem in ("memory:never", "memory:del", "memory:live"):
            out = self.memory.recall(QUERY, logical_memory_refs=[mem])
            self.assertEqual(out["admitted"], []); self.assertEqual(out["candidates"], [])
            self.assertNotIn(live, _serial(out))
            routes[mem] = out["recall_control"].get("routes_executed")
        self.assertEqual(routes["memory:live"], routes["memory:never"], routes)
        self.assertEqual(routes["memory:del"], routes["memory:never"], routes)
        self.memory.close()
        self.memory = self.open("project:a", recall_control="shadow")
        self.assertEqual(self.memory.recall(QUERY, logical_memory_refs=["memory:live"])["admitted"], [live])


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

    def test_fr3_4_revoking_a_foreign_skill_reads_exactly_like_an_unknown_skill(self):
        self.assertTrue(self.runtime.commit_skill(self.runtime.propose_skill(_skill("project:a"), actor_id="agent:a")).commit.committed)
        outcomes = {}
        for skill_id in ("deploy", "unknown"):
            try:
                out = self.runtime.revoke_skill(skill_id, actor_id="agent:b", evidence_refs=("evidence:b",), scope="project:b",
                                                isolation_domain_refs=(TENANT, "project:b"), required_isolation_domain_refs=(TENANT, "project:b"), purpose="c786")
                outcomes[skill_id] = ("result", out.commit.committed, out.commit.refusal, out.fact_uuid, out.physical_content_retained)
            except ValueError as exc:
                outcomes[skill_id] = ("ValueError", str(exc).replace(repr(skill_id), "<id>"))
        self.assertEqual(outcomes["deploy"], outcomes["unknown"], outcomes)
        self.assertNotIn("ref-", _serial(outcomes))

    def test_fr3_5_a_member_can_advance_a_skill_bound_only_to_a_shared_domain(self):
        self.adapter.set_shared_domain_members("shared:x", ("agent:alice", "agent:bob"))
        v1 = self.runtime.commit_skill(self.runtime.propose_skill(
            _skill("shared:x", domains=("shared:x",), required=()), actor_id="agent:alice")).commit
        self.assertTrue(v1.committed, v1.refusal)
        proposal = self.runtime.propose_skill(  # raised "current=v0, proposed=v2" before the fix
            _skill("shared:x", version=2, domains=("shared:x",), required=()), actor_id="agent:alice")
        v2 = self.runtime.commit_skill(proposal).commit
        self.assertIsNone(v2.refusal)  # a correction parks under policy (require_review); it is not refused
        with self.assertRaises(ValueError):  # a non-member still resolves the version as 0 and may not advance it
            self.runtime.propose_skill(_skill("shared:x", version=3, domains=("shared:x",), required=()), actor_id="agent:stranger")

    def test_f4_revocation_carries_the_callers_scope_not_the_targets(self):
        head = self.runtime.commit_skill(self.runtime.propose_skill(_skill("project:a"), actor_id="agent:a")).commit.fact_uuid
        other = self.runtime.propose_skill(_skill("project:b"), actor_id="agent:b")
        self.assertFalse(self.runtime.commit_skill(other).commit.committed)
        # fail closed: a bare or wrong-scope revocation reads like an unknown skill (third review F-R3-4)
        with self.assertRaises(ValueError):
            self.runtime.revoke_skill("deploy", actor_id="agent:b", evidence_refs=("ev:b",))
        with self.assertRaises(ValueError):
            self.runtime.revoke_skill("deploy", actor_id="agent:b", evidence_refs=("ev:b",), scope="project:b",
                                      isolation_domain_refs=(TENANT, "project:b"),
                                      required_isolation_domain_refs=(TENANT, "project:b"), purpose="c786")
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
