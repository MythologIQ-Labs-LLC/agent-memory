"""#809 (F-R3-2), preregistered: a reference the writer cannot read is an unknown reference.

Owner decision (PR #805 review 5527079673, issue #809): option (b) of
``reports/validation/805-at-head/f-r3-2-disposition.md``. Only a reference that names a fact
of this tenant **the writer is eligible to read** (the #786 writer gates: tenant, isolation
domains, shared membership, project, task) may become a canonical derivation link that
carries deletion taint. A reference to a fact outside the writer's scope behaves exactly
like an identifier nobody wrote: it commits, it is admitted, it leaves the same receipt,
history, recall payload and write semantics, and it never withholds anything later.

These expectations were authored and committed BEFORE the runtime change, executed once on
the unmodified integration candidate ``28f257c9`` (protected tree ``ef8b6cb2``) to record the
fail-first baseline (``reports/validation/809-at-head/preregistration-baseline.log``), and
compared by a separate reviewer before their first execution on the changed runtime. A
failure after the change is a finding to investigate, never permission to weaken a line.

What is expected to be RED on the unmodified tree (the oracle and its side channels):
``FourReferencesIndistinguishable`` (all four), ``CanaryAndReCreation`` (both),
``CrossScopeChains`` (both), ``LateBinding``, ``RecordedDerivation``, and in
``SharedDomainAndRestrictions`` every case but ``test_revocation_after_binding_keeps_the_dependency``
(each of the others asserts that a stranger, a later member, another task or another project
binds nothing). Recorded on ``28f257c9``: 29 failed, 9 passed.
What is expected to be GREEN before and after (positive controls, deletion completeness):
``OwnScopeDeletionCompleteness`` (all three), ``test_revocation_after_binding_keeps_the_dependency``,
``LegacyFacts``.

Existing tests this change is declared to alter (listed here so the reviewer sees them):
``test_776_transitive_traversal_review.py::TransitiveTraversal::test_decision_does_not_depend_on_query_order``
(a forward citation of an id that does not exist at commit time never binds: fail-closed at
commit; the memo-stability property it also asserts is kept), and the from-scratch oracle of
``test_776_deletion_decision_properties.py`` (provenance is the fact's bound canonical
derivation, not every string in ``episode_uuids``). ``EvidenceReferenceOracle`` in
``test_786_cross_scope_write_authority.py`` keeps its body as the pre-repair proof and is
marked ``expectedFailure``: an unexpected success there means the oracle has reopened.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory, policy
from agentmem_ref.runtime.adapter import Clock, GovernedMemoryAdapter, RecallContext
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests.test_644_combined_independent import _evidence, _prop
from tests.test_786_cross_scope_write_authority import ACTOR, QUERY, TENANT, _TwoProjects, _proposal

HIST = {"mode": "historical"}
FOUR = ["memory.propose", "memory.authorize", "memory.commit", "memory.receipt"]
GUESS = "fact-guess-" + "9" * 12
REFERENCE = Path(__file__).resolve().parents[1]


def _fold(text: str) -> str:
    text = re.sub(r"ref-\d+", "ref-X", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", "T", text)
    text = re.sub(r"facade:[0-9a-f]{64}", "facade:H", text)
    text = re.sub(r"content:sha256:[0-9a-f]{64}", "content:H", text)
    text = re.sub(r"\"elapsed_ms\": [0-9.e-]+", "\"elapsed_ms\": E", text)
    return text


def _shape(value, *, self_uuid: str | None, ref: str | None, label: str) -> str:
    """One public payload with the citer's own identifiers, the cited string and the case
    label replaced by placeholders: two cases are indistinguishable iff their shapes are equal."""
    text = json.dumps(value, sort_keys=True, default=str)
    if self_uuid:
        text = text.replace(self_uuid, "<self>")
    if ref:
        text = text.replace(ref, "<ref>")
    return _fold(text).replace(label, "<label>")


def _attestation(memory: AgentMemory, target: str) -> policy.ExternalVerification:
    proposal = memory._proposal(target_reference=target, operation="permanent_deletion", current_strength="reinforced",
                                proposed_strength="not_applicable", reversibility="irreversible", risk_class="high")
    return policy.ExternalVerification(bound_proposal_id=str(proposal["proposal_id"]),
                                       verifier_principal_id="human:809-reviewer",
                                       authority_kind=policy.HUMAN_CONFIRMATION, max_risk_class="critical")


class _Citer(_TwoProjects):
    """Project A owns ``memory:a`` (``a1``) and ``memory:a2`` (``a2``); project B cites."""

    def fresh(self, scope="project:a"):
        self.memory.close()
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name + "/m"
        self.memory = self.open(scope)

    def forget_a(self, memory="memory:a", *, permanent: bool):
        if permanent:
            out = self.memory.forget(memory, permanent=True, risk_class="high", attestation=_attestation(self.memory, memory))
        else:
            out = self.memory.forget(memory)
        self.assertTrue(out["committed"], out)
        return out

    def seed_a(self, *, permanent: bool) -> tuple[str, str]:
        a1 = self.seed()
        a2 = self.memory.remember("memory:a2", f"{QUERY} is Bergen", proposition=_prop("Bergen"))["fact_uuid"]
        self.forget_a(permanent=permanent)
        return a1, a2

    def cite(self, label: str, ref: str | None) -> dict:
        memory = f"memory:b-{label}"
        kw = {"evidence_refs": (ref,)} if ref else {}
        out = self.memory.remember(memory, f"{QUERY} digest {label}", **kw)
        return {"memory": memory, "ref": ref, "label": label, "out": out, "uuid": out.get("fact_uuid")}

    def observe(self, cited: dict) -> dict:
        m, uuid, label, ref = cited["memory"], cited["uuid"], cited["label"], cited["ref"]
        by_ref = self.memory.recall(f"{QUERY} digest {label}", logical_memory_refs=(m,))
        historical = self.memory.recall(f"{QUERY} digest", temporal_intent=HIST)
        history = self.memory.history(m)
        semantics = self.memory.write_semantics(uuid) if uuid else None
        return {
            "committed": cited["out"]["committed"],
            "admitted": by_ref["admitted"].count(uuid),
            "admitted_historical": uuid in historical["admitted"],
            "events": [e["event_type"] for e in history["history"]["events"]],
            "write_semantics": semantics is not None,
            "shape": {
                "remember": _shape(cited["out"], self_uuid=uuid, ref=ref, label=label),
                "recall": _shape(by_ref, self_uuid=uuid, ref=ref, label=label),
                "history": _shape(history, self_uuid=uuid, ref=ref, label=label),
                "write_semantics": _shape(semantics, self_uuid=uuid, ref=ref, label=label),
            },
        }

    def four(self, *, permanent: bool) -> dict:
        a1, a2 = self.seed_a(permanent=permanent)
        self.reopen("project:b")
        cited = {"deleted": self.cite("deleted", a1), "live_foreign": self.cite("live", a2),
                 "unknown": self.cite("unknown", GUESS), "none": self.cite("none", None)}
        return cited


class FourReferencesIndistinguishable(_Citer):
    """Foreign-deleted, foreign-live, unknown and absent references are externally
    indistinguishable at write and at every public read of the citer (issue #809, item 2)."""

    def _assert_indistinguishable(self, cited: dict, views: dict):
        for label, view in views.items():
            with self.subTest(label=label):
                self.assertTrue(view["committed"], label)
                self.assertEqual(view["admitted"], 1, (label, view["events"]))
                self.assertTrue(view["admitted_historical"], label)
                self.assertEqual(view["events"], FOUR, label)
                self.assertTrue(view["write_semantics"], label)
        for channel in ("remember", "recall", "history", "write_semantics"):
            with self.subTest(channel=channel):
                self.assertEqual(views["deleted"]["shape"][channel], views["unknown"]["shape"][channel], channel)
                self.assertEqual(views["live_foreign"]["shape"][channel], views["unknown"]["shape"][channel], channel)

    def test_after_pruning_and_after_attested_permanent_deletion(self):
        for permanent in (False, True):
            with self.subTest(permanent=permanent):
                self.fresh()
                cited = self.four(permanent=permanent)
                self._assert_indistinguishable(cited, {k: self.observe(v) for k, v in cited.items()})

    def test_the_same_after_an_in_process_reopen(self):
        for permanent in (False, True):
            with self.subTest(permanent=permanent):
                self.fresh()
                cited = self.four(permanent=permanent)
                self.reopen("project:b")
                self._assert_indistinguishable(cited, {k: self.observe(v) for k, v in cited.items()})

    def test_the_same_in_a_genuine_process_restart(self):
        self.fresh()
        cited = self.four(permanent=True)
        self.memory.close()
        refs = {v["memory"]: v["uuid"] for v in cited.values()}
        child = subprocess.run(
            [sys.executable, "-c", _CHILD, str(REFERENCE), self.root, TENANT, ACTOR, "project:b", QUERY, json.dumps(refs)],
            capture_output=True, text=True, check=True)
        views = json.loads(child.stdout)
        for label, memory in ((k, v["memory"]) for k, v in cited.items()):
            with self.subTest(label=label):
                self.assertEqual(views[memory], {"admitted": 1, "events": FOUR, "write_semantics": True}, label)
        self.memory = self.open("project:b")

    def test_a_dispute_citing_a_foreign_deleted_reference_is_indistinguishable_in_the_citers_history(self):
        self.fresh()
        a1, _ = self.seed_a(permanent=False)
        self.reopen("project:b")
        shapes = {}
        for label, ref in (("deleted", a1), ("unknown", "fact-guess-" + "8" * 12)):
            memory = f"memory:d-{label}"
            own = self.memory.remember(memory, f"{QUERY} digest {label}")
            disputed = self.memory.dispute(memory, evidence=_evidence("project:b", TENANT), risk_class="low", evidence_refs=(ref,))
            self.assertTrue(disputed["committed"], disputed)
            history = self.memory.history(memory)
            events = [e["event_type"] for e in history["history"]["events"]]
            self.assertIn("memory.dispute", events, label)
            shapes[label] = (_shape(disputed, self_uuid=own["fact_uuid"], ref=ref, label=label),
                             _shape(history, self_uuid=own["fact_uuid"], ref=ref, label=label))
        self.assertEqual(shapes["deleted"], shapes["unknown"])


_CHILD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from agentmem_ref import AgentMemory
root, tenant, actor, scope, query, refs = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], json.loads(sys.argv[7])
m = AgentMemory.open(root, tenant=tenant, actor_id=actor, scope=scope, purpose="c786")
out = {}
for memory, uuid in refs.items():
    label = memory.split("-", 1)[1]
    rec = m.recall(f"{query} digest {label}", logical_memory_refs=(memory,))
    hist = m.history(memory)["history"]
    out[memory] = {"admitted": rec["admitted"].count(uuid), "events": [e["event_type"] for e in hist["events"]],
                   "write_semantics": m.write_semantics(uuid) is not None}
m.close()
print(json.dumps(out))
'''


class CanaryAndReCreation(_Citer):
    def test_a_canary_citing_a_live_foreign_fact_does_not_vanish_when_that_fact_is_deleted(self):
        for permanent in (False, True):
            with self.subTest(permanent=permanent):
                self.fresh()
                a3 = self.memory.remember("memory:a3", f"{QUERY} is Narvik", proposition=_prop("Narvik"))["fact_uuid"]
                self.reopen("project:b")
                canary = self.cite("canary", a3)
                before = self.observe(canary)
                self.reopen("project:a")
                self.forget_a("memory:a3", permanent=permanent)
                self.reopen("project:b")
                after = self.observe(canary)
                self.assertEqual((before["admitted"], after["admitted"]), (1, 1))
                self.assertEqual(before["events"], after["events"])
                self.assertEqual(before["shape"], after["shape"])

    def test_the_citing_scope_may_re_create_the_deleted_id_and_its_own_derivations_follow_its_own_deletions(self):
        self.fresh()
        a1, _ = self.seed_a(permanent=False)
        self.reopen("project:b")
        foreign = self.cite("foreign", a1)
        again = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.assertTrue(again["committed"], again)
        own = self.cite("own", again["fact_uuid"])
        self.assertEqual((self.observe(foreign)["admitted"], self.observe(own)["admitted"]), (1, 1))
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        # B's own derivation of B's own deleted generation is withheld; the foreign citation never bound
        self.assertEqual((self.observe(foreign)["admitted"], self.observe(own)["admitted"]), (1, 0))
        self.reopen("project:b")
        self.assertEqual((self.observe(foreign)["admitted"], self.observe(own)["admitted"]), (1, 0))


class CrossScopeChains(_Citer):
    def test_a_purged_foreign_identifier_binds_nothing(self):
        self.fresh()
        a1 = self.seed()
        self.forget_a(permanent=True)
        self.assertIsNone(self.fact(a1))
        self.reopen("project:b")
        self.assertEqual(self.observe(self.cite("purged", a1))["admitted"], 1)

    def test_a_chain_rooted_in_a_foreign_deleted_reference_is_not_tainted(self):
        self.fresh()
        a1, _ = self.seed_a(permanent=True)
        self.reopen("project:b")
        first = self.cite("first", a1)
        second = self.cite("second", first["uuid"])
        third = self.cite("third", second["uuid"])
        self.assertEqual([self.observe(c)["admitted"] for c in (first, second, third)], [1, 1, 1])


class OwnScopeDeletionCompleteness(_Citer):
    """Positive controls: within the writer's own scope the #776/#777 rule is unchanged."""

    def _chain(self):
        a1 = self.seed()
        d1 = self.memory.remember("memory:d1", f"{QUERY} digest one", evidence_refs=(a1, "evidence:ticket-7"))["fact_uuid"]
        d2 = self.memory.remember("memory:d2", f"{QUERY} digest two", evidence_refs=(d1,))["fact_uuid"]
        ctl = self.memory.remember("memory:ctl", f"{QUERY} digest control", evidence_refs=("evidence:ticket-7",))["fact_uuid"]
        return a1, d1, d2, ctl

    def _admitted(self):
        return set(self.memory.recall(f"{QUERY} digest", temporal_intent=HIST)["admitted"])

    def test_direct_and_transitive_derivations_are_withheld_after_pruning_and_after_permanent_deletion(self):
        for permanent in (False, True):
            with self.subTest(permanent=permanent):
                self.fresh()
                a1, d1, d2, ctl = self._chain()
                self.assertEqual(self._admitted() & {d1, d2, ctl}, {d1, d2, ctl})
                self.forget_a(permanent=permanent)
                self.assertEqual(self._admitted() & {d1, d2, ctl}, {ctl})
                self.reopen("project:a")
                self.assertEqual(self._admitted() & {d1, d2, ctl}, {ctl})
                if permanent:
                    # the source payload is gone; the deletion dependency is not
                    self.assertIsNone(self.fact(a1))
                    self.assertEqual(self._admitted() & {d1, d2}, set())

    def test_a_derivation_written_after_its_own_source_was_purged_is_still_withheld(self):
        self.fresh()
        a1 = self.seed()
        self.forget_a(permanent=True)
        self.assertIsNone(self.fact(a1))
        late = self.memory.remember("memory:late", f"{QUERY} digest late", evidence_refs=(a1,))
        self.assertTrue(late["committed"], late)
        self.assertNotIn(late["fact_uuid"], self._admitted())
        self.reopen("project:a")
        self.assertNotIn(late["fact_uuid"], self._admitted())

    def test_external_evidence_identifiers_are_preserved_as_evidence_and_carry_no_deletion_state(self):
        self.fresh()
        a1, d1, d2, ctl = self._chain()
        substrate = self.adapter._substrate
        self.assertEqual(tuple(substrate.get_fact(d1).episode_uuids), (a1, "evidence:ticket-7"))
        self.assertEqual(tuple(substrate.get_fact(ctl).episode_uuids), ("evidence:ticket-7",))
        neighbours = {fact.uuid: shared for fact, shared, _ in substrate.evidence_neighbors(ctl)}
        self.assertEqual(neighbours.get(d1), ("evidence:ticket-7",))
        self.forget_a(permanent=False)
        self.assertIn(ctl, self._admitted())


class LateBinding(_Citer):
    def _scenario(self, root: str, future: str) -> tuple[str, str, bool, bool]:
        m = AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a", purpose="c786")
        old = m.remember("memory:a", f"{QUERY} is Oslo", proposition=_prop("Oslo"))["fact_uuid"]
        self.assertTrue(m.forget("memory:a")["committed"])
        fwd = m.remember("memory:fwd", f"{QUERY} digest forward", evidence_refs=(future,))["fact_uuid"]
        late = m.remember("memory:late", f"{QUERY} digest late", evidence_refs=(old,))["fact_uuid"]
        got = set(m.recall(f"{QUERY} digest", temporal_intent=HIST)["admitted"])
        m.close()
        m = AgentMemory.open(root, tenant=TENANT, actor_id=ACTOR, scope="project:a", purpose="c786")
        again = set(m.recall(f"{QUERY} digest", temporal_intent=HIST)["admitted"])
        m.close()
        return late, fwd, fwd in got and fwd in again, late in got or late in again

    def test_a_reference_that_names_no_fact_at_commit_never_binds_later(self):
        """Fail-closed at commit (issue #809, item 4): authorization is evaluated when the
        derivation is written. An id that exists only later cannot have carried content.
        Deterministic ids: a discovery pass learns the late fact's id; the replay cites it
        before it exists (the construction of test_776_transitive_traversal_review)."""
        with tempfile.TemporaryDirectory() as d1:
            late_id, *_ = self._scenario(d1 + "/m", "external:placeholder")
        with tempfile.TemporaryDirectory() as d2:
            late, fwd, fwd_admitted, late_admitted = self._scenario(d2 + "/m", late_id)
        self.assertEqual(late, late_id)
        self.assertFalse(late_admitted, "the late derivation of a deleted source is withheld")
        self.assertTrue(fwd_admitted, "a reference that named no fact at commit never binds")


class RecordedDerivation(_Citer):
    def test_the_canonical_derivation_is_recorded_apart_from_the_caller_supplied_evidence(self):
        from agentmem_ref.runtime import adapter as adapter_module

        key = getattr(adapter_module, "DERIVATION_KEY", None)
        self.assertIsNotNone(key, "the adapter records a canonical derivation set distinct from episode_uuids")
        self.fresh()
        a1 = self.seed()
        own = self.memory.remember("memory:own", f"{QUERY} digest own", evidence_refs=(a1, "evidence:ticket-7"))["fact_uuid"]
        self.reopen("project:b")
        foreign = self.cite("foreign", a1)["uuid"]
        unknown = self.cite("unknown", GUESS)["uuid"]
        facts = {n: self.adapter._substrate.get_fact(u) for n, u in (("own", own), ("foreign", foreign), ("unknown", unknown))}
        self.assertEqual(tuple(facts["own"].episode_uuids), (a1, "evidence:ticket-7"))
        self.assertEqual(tuple(facts["foreign"].episode_uuids), (a1,))
        self.assertEqual(list((facts["own"].attributes or {})[key]["bound"]), [a1])
        self.assertEqual(list((facts["foreign"].attributes or {})[key]["bound"]), [])
        self.assertEqual(list((facts["unknown"].attributes or {})[key]["bound"]), [])


def _ctx(domains, principal="agent:a", project="", task=""):
    return RecallContext(target_domain_refs=tuple(domains), principal_ref=principal, project_ref=project, task_ref=task)


class SharedDomainAndRestrictions(unittest.TestCase):
    """Adapter level: the same gates recall applies decide what binds, evaluated at commit."""

    def setUp(self):
        self.substrate = InMemoryTemporalGraph()
        self.adapter = GovernedMemoryAdapter(self.substrate, tenant=TENANT, clock=Clock())

    def _digest(self, pid, actor, domains, ref, *, target, project="", task=""):
        out = self.adapter.commit_proposal(
            _proposal(proposal_id=pid, actor_id=actor, scope=domains[0], isolation_domain_refs=tuple(domains),
                      project_ref=project, task_ref=task, target_reference=target, evidence_refs=(ref,)),
            f"shared window digest {pid}")
        self.assertTrue(out.committed, out.refusal)
        return out.fact_uuid

    def _refused(self, uuid, context) -> str | None:
        result = self.adapter.governed_recall("shared window digest", context)
        self.assertIn(uuid, result.candidates, (uuid, result.refusals))
        return result.refusals.get(uuid)

    def _delete_shared(self, s1):
        out = self.adapter.governed_delete(
            _proposal(proposal_id="d1", operation="pruning", proposed_strength="archived"), s1)
        self.assertTrue(out.committed, out.refusal)

    def test_a_member_binds_a_stranger_does_not(self):
        self.adapter.set_shared_domain_members("shared:x", ("agent:a", "agent:b"))
        s1 = self.adapter.commit_proposal(_proposal(), "shared window is Thursday").fact_uuid
        member = self._digest("pb", "agent:b", ("project:b", "shared:x"), s1, target="mem:b")
        stranger = self._digest("pc", "agent:c", ("project:c", "shared:x"), s1, target="mem:c")
        self._delete_shared(s1)
        self.assertIsNotNone(self._refused(member, _ctx(("project:b", "shared:x"), "agent:b")))
        self.assertIsNone(self._refused(stranger, _ctx(("project:c", "shared:x"), "agent:c")))

    def test_revocation_after_binding_keeps_the_dependency(self):
        self.adapter.set_shared_domain_members("shared:x", ("agent:a", "agent:b"))
        s1 = self.adapter.commit_proposal(_proposal(), "shared window is Thursday").fact_uuid
        member = self._digest("pb", "agent:b", ("project:b", "shared:x"), s1, target="mem:b")
        self.adapter.set_shared_domain_members("shared:x", ("agent:a",))
        self._delete_shared(s1)
        self.assertIsNotNone(self._refused(member, _ctx(("project:b", "shared:x"), "agent:b")))

    def test_membership_granted_later_gives_no_retroactive_binding(self):
        self.adapter.set_shared_domain_members("shared:x", ("agent:a",))
        s1 = self.adapter.commit_proposal(_proposal(), "shared window is Thursday").fact_uuid
        later = self._digest("pb", "agent:b", ("project:b", "shared:x"), s1, target="mem:b")
        self.adapter.set_shared_domain_members("shared:x", ("agent:a", "agent:b"))
        self._delete_shared(s1)
        self.assertIsNone(self._refused(later, _ctx(("project:b", "shared:x"), "agent:b")))

    def test_project_and_task_restrictions_decide_what_binds(self):
        t1 = self.adapter.commit_proposal(
            _proposal(scope=TENANT, isolation_domain_refs=(TENANT,), project_ref="project:p", task_ref="task:1",
                      target_reference="mem:t"), "shared window is Monday").fact_uuid
        same = self._digest("p1", "agent:a", (TENANT,), t1, target="mem:same", project="project:p", task="task:1")
        other_task = self._digest("p2", "agent:a", (TENANT,), t1, target="mem:task", project="project:p", task="task:2")
        other_project = self._digest("p3", "agent:a", (TENANT,), t1, target="mem:proj", project="project:q", task="task:1")
        out = self.adapter.governed_delete(
            _proposal(proposal_id="d1", operation="pruning", proposed_strength="archived", scope=TENANT,
                      isolation_domain_refs=(TENANT,), project_ref="project:p", task_ref="task:1", target_reference="mem:t"), t1)
        self.assertTrue(out.committed, out.refusal)
        self.assertIsNotNone(self._refused(same, _ctx((TENANT,), project="project:p", task="task:1")))
        self.assertIsNone(self._refused(other_task, _ctx((TENANT,), project="project:p", task="task:2")))
        self.assertIsNone(self._refused(other_project, _ctx((TENANT,), project="project:q", task="task:1")))

    def test_a_foreign_unknown_reference_binds_nothing_at_the_adapter(self):
        a1 = self.adapter.commit_proposal(
            _proposal(scope="project:a", isolation_domain_refs=("project:a",), target_reference="mem:a"), "shared window is Tuesday").fact_uuid
        foreign = self._digest("pb", "agent:b", ("project:b",), a1, target="mem:b")
        out = self.adapter.governed_delete(
            _proposal(proposal_id="d1", operation="pruning", proposed_strength="archived", scope="project:a",
                      isolation_domain_refs=("project:a",), target_reference="mem:a"), a1)
        self.assertTrue(out.committed, out.refusal)
        self.assertIsNone(self._refused(foreign, _ctx(("project:b",), "agent:b")))


class LegacyFacts(unittest.TestCase):
    """A fact persisted before #809 carries no recorded derivation: its ``episode_uuids`` keep
    binding as before (no silent weakening of deletion completeness for existing data)."""

    def test_a_fact_without_a_recorded_derivation_keeps_its_episode_provenance_as_the_dependency(self):
        from agentmem_ref.runtime import adapter as adapter_module

        substrate = InMemoryTemporalGraph()
        adapter = GovernedMemoryAdapter(substrate, tenant=TENANT, clock=Clock())
        a1 = adapter.commit_proposal(
            _proposal(scope="project:a", isolation_domain_refs=("project:a",), target_reference="mem:a"), "legacy window is Tuesday").fact_uuid
        d = adapter.commit_proposal(
            _proposal(proposal_id="pd", scope="project:a", isolation_domain_refs=("project:a",), target_reference="mem:d",
                      evidence_refs=(a1,)), "legacy window digest").fact_uuid
        fact = substrate.get_fact(d)
        key = getattr(adapter_module, "DERIVATION_KEY", None)
        if key is not None and fact.attributes:
            fact.attributes.pop(key, None)
        adapter._derived_taint_memo = None
        out = adapter.governed_delete(
            _proposal(proposal_id="d1", operation="pruning", proposed_strength="archived", scope="project:a",
                      isolation_domain_refs=("project:a",), target_reference="mem:a"), a1)
        self.assertTrue(out.committed, out.refusal)
        result = adapter.governed_recall("legacy window digest", _ctx(("project:a",)))
        self.assertIsNotNone(result.refusals.get(d), result.refusals)


if __name__ == "__main__":
    unittest.main()
