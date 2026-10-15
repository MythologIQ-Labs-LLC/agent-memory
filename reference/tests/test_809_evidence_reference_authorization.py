"""#809 (F-R3-2), preregistered: a reference the writer cannot read is an unknown reference.

Owner decision (PR #805 review 5527079673, issue #809): option (b) of
``reports/validation/805-at-head/f-r3-2-disposition.md``. Only a reference that names a fact
of this tenant **the writer is eligible to read** (the #786 writer gates: tenant, isolation
domains, shared membership, project, task) may become a canonical derivation link that
carries deletion taint. A reference to a fact outside the writer's scope behaves exactly
like an identifier nobody wrote: it commits, it is admitted, it leaves the same receipt,
history, recall payload and write semantics, and it never withholds anything later.

These expectations were authored and committed BEFORE the runtime change and executed on
the unmodified integration candidate ``28f257c9`` (protected tree ``ef8b6cb2``) to record the
fail-first baseline. Two baselines exist and both are kept: the first
(``reports/validation/809-at-head/preregistration-baseline.log``, commit ``10a0d70e``) and,
after the independent pre-execution review found that the first version of ``_shape`` folded
the bare case label and so rewrote runtime vocabulary (``deleted_lineage``, ``"status":
"unknown"``) on one side of each comparison, the second
(``reports/validation/809-at-head/preregistration-baseline-2.log``), run on the same runtime
with this corrected module. The review record is
``reports/validation/809-at-head/independent-preregistration-review.md``; this revision
answers its SF-1..SF-7 items. A failure after the change is a finding to investigate, never
permission to weaken a line.

What is expected to be RED on the unmodified tree (the oracle and its side channels):
``FourReferencesIndistinguishable`` (all four), ``CanaryAndReCreation`` (all three),
``CrossScopeChains`` (both), ``LateBinding``, ``RecordedDerivation``, ``ProvenanceAudit``,
``SharedDomainDurable``, and in ``SharedDomainAndRestrictions`` every case but
``test_revocation_after_binding_keeps_the_dependency`` (each of the others asserts that a
stranger, a later member, another task or another project binds nothing). Of the two
declared 776 changes, the traversal test is RED (the forward note is refused pre-#809) and
the property test is RED for the seeds in which a forward citation materialises (seed 4:
the independent fail-closed oracle disagrees with the late-binding runtime). Recorded on
the unmodified runtime with this module: 36 failed, 14 passed, 82 subtests passed; the 14
are the 8 positive-control test bodies plus the 6 bodies whose failures are subtest-level.
In the ``FourReferences`` family only the ``deleted`` case fails before the repair, and only
on ``recall``, ``history`` and ``write_semantics``: ``remember`` (receipt) and every
``live_foreign`` comparison already hold, which is the pre-repair oracle exactly.
What is expected to be GREEN before and after (positive controls, deletion completeness):
``OwnScopeDeletionCompleteness`` (all four, including the genuine-process-restart case),
``DirectProbes`` (a foreign deleted id and a guess already read identically when addressed
directly), ``test_revocation_after_binding_keeps_the_dependency``, ``LegacyFacts`` and
``LegacyFactsDurable``. The ``none`` control is compared on admission, events and write
semantics only: its receipt carries a content hash where the others carry a citation, so it
cannot be byte-equal and is not claimed to be.

Existing tests this change is declared to alter (listed here so the reviewer sees them;
both edits are committed with this module, before the runtime change, and run in the
baseline): ``test_776_transitive_traversal_review.py::TransitiveTraversal::
test_decision_does_not_depend_on_query_order`` (a forward citation of an id that does not
exist at commit time never binds: fail-closed at commit; the memo-stability property it also
asserts is kept; this withdraws the pre-#809 guarantee that such a forward note became
refused once the id materialised, a behavioural change presented for the owner's explicit
acceptance in the #809 handoff), and the from-scratch oracle of
``test_776_deletion_decision_properties.py`` (dependencies are recomputed independently of the
runtime, from ``episode_uuids``, the governed-fact scope record and id order, never from the
runtime's own recorded derivation). ``EvidenceReferenceOracle`` in
``test_786_cross_scope_write_authority.py`` keeps its body as the pre-repair proof and is
marked ``expectedFailure``: that decorator is the one edit to the proof file (issue item 1
asked for the proof to be kept, and a permanently red proof would be worse); an unexpected
success there means the oracle has reopened.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import agentmem_ref
from agentmem_ref import AgentMemory, policy
from agentmem_ref.runtime.adapter import Clock, GovernedMemoryAdapter, RecallContext
from agentmem_ref.state.sqlite_substrate import _canonical_bytes
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests.test_644_combined_independent import _evidence, _prop
from tests.test_786_cross_scope_write_authority import ACTOR, QUERY, TENANT, _TwoProjects, _proposal

HIST = {"mode": "historical"}
FOUR = ["memory.propose", "memory.authorize", "memory.commit", "memory.receipt"]
GUESS = "fact-guess-" + "9" * 12
REFERENCE = Path(__file__).resolve().parents[1]
DELETION_FAMILY = {"derived_from_tombstoned_source", "derived_from_deleted_logical_memory"}


UUID = re.compile(r"^ref-\d+$")


def _fold(text: str) -> str:
    text = re.sub(r"ref-\d+", "ref-X", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z", "T", text)
    text = re.sub(r"facade:[0-9a-f]{64}", "facade:H", text)
    text = re.sub(r"content:sha256:[0-9a-f]{64}", "content:H", text)
    text = re.sub(r"\"elapsed_ms\": [0-9.e-]+", "\"elapsed_ms\": E", text)
    # transaction clocks are wall time; relevance scores differ in the last binary digits
    # with the query's token lengths (the label is part of the query), so compare at 1e-6
    text = re.sub(r"\"seconds\": [0-9.e+-]+", "\"seconds\": S", text)
    text = re.sub(r"(\"[a-z_]*score[a-z_]*\": )(-?[0-9]+\.[0-9]+(?:e-?[0-9]+)?)",
                  lambda m: m.group(1) + format(round(float(m.group(2)), 6), ".6f"), text)
    return text


def _shape(value, *, self_uuid: str | None, ref: str | None, label: str) -> str:
    """One public payload with the citer's own identifiers, the cited string and the case
    label replaced by placeholders: two cases are indistinguishable iff their shapes are equal.

    Only the exact tokens the harness itself derived from the label are folded (the memory
    ids ``memory:b-<label>`` / ``memory:d-<label>`` and the text ``digest <label>``), never the
    bare label: the runtime's own vocabulary contains the words ``deleted`` (public
    projection ``deleted_lineage``) and ``unknown`` (write-semantics ``"status": "unknown"``),
    and folding those on one side only made the first version of this comparison
    unsatisfiable (review SF-1). Maps keyed by fact uuid and lists of fact uuids (recall's
    ``admissions``, ``candidates``, ``admitted``, ``returned``) are compared without regard
    to order: the citer's other memories are candidates of every recall and their rank
    relative to the citer's own fact follows the query text, which carries the label. What
    is compared is therefore the set of candidate records and the citer's own record, with
    nothing dropped."""

    def fold(text: str) -> str:
        if self_uuid:
            text = text.replace(self_uuid, "<self>")
        if ref:
            text = text.replace(ref, "<ref>")
        for needle, placeholder in ((f"memory:b-{label}", "memory:b-<label>"),
                                    (f"memory:d-{label}", "memory:d-<label>"),
                                    (f"digest {label}", "digest <label>")):
            text = text.replace(needle, placeholder)
        return _fold(text)

    def canonical(item):
        if isinstance(item, dict):
            if item and all(isinstance(k, str) and UUID.match(k) for k in item):
                pairs = [[k, canonical(v)] for k, v in item.items()]
                return sorted(pairs, key=lambda kv: fold(json.dumps(kv, sort_keys=True, default=str)))
            return {k: canonical(v) for k, v in item.items()}
        if isinstance(item, list):
            items = [canonical(v) for v in item]
            if items and all(isinstance(v, str) and UUID.match(v) for v in items):
                return sorted(items, key=fold)
            return items
        return item

    return fold(json.dumps(canonical(value), sort_keys=True, default=str))


def _attestation(memory: AgentMemory, target: str) -> policy.ExternalVerification:
    proposal = memory._proposal(target_reference=target, operation="permanent_deletion", current_strength="reinforced",
                                proposed_strength="not_applicable", reversibility="irreversible", risk_class="high")
    return policy.ExternalVerification(bound_proposal_id=str(proposal["proposal_id"]),
                                       verifier_principal_id="human:809-reviewer",
                                       authority_kind=policy.HUMAN_CONFIRMATION, max_risk_class="critical")


def _package_root(file: str) -> str:
    return str(Path(file).resolve().parents[1])


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

    def admitted_historical(self) -> set[str]:
        return set(self.memory.recall(f"{QUERY} digest", temporal_intent=HIST)["admitted"])

    def restart(self, script: str, scope: str, *args: str) -> dict:
        """Run ``script`` in a fresh interpreter against this root (a genuine process restart)
        and check that it imported the same ``agentmem_ref`` package as this process."""
        child = subprocess.run([sys.executable, "-c", script, str(REFERENCE), self.root, TENANT, ACTOR, scope, QUERY, *args],
                               capture_output=True, text=True, check=True)
        out = json.loads(child.stdout)
        self.assertEqual(_package_root(out.pop("package")), _package_root(agentmem_ref.__file__))
        return out


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
            for case in ("deleted", "live_foreign"):
                with self.subTest(channel=channel, case=case):
                    self.assertEqual(views[case]["shape"][channel], views["unknown"]["shape"][channel], (channel, case))

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
        views = self.restart(_CHILD, "project:b", json.dumps(refs))
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
            with self.subTest(label=label):
                self.assertIn("memory.dispute", events, label)
            shapes[label] = {"dispute": _shape(disputed, self_uuid=own["fact_uuid"], ref=ref, label=label),
                             "history": _shape(history, self_uuid=own["fact_uuid"], ref=ref, label=label)}
        for channel in ("dispute", "history"):
            with self.subTest(channel=channel):
                self.assertEqual(shapes["deleted"][channel], shapes["unknown"][channel], channel)


_CHILD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import agentmem_ref
from agentmem_ref import AgentMemory
root, tenant, actor, scope, query, refs = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], json.loads(sys.argv[7])
m = AgentMemory.open(root, tenant=tenant, actor_id=actor, scope=scope, purpose="c786")
out = {"package": agentmem_ref.__file__}
for memory, uuid in refs.items():
    label = memory.split("-", 1)[1]
    rec = m.recall(f"{query} digest {label}", logical_memory_refs=(memory,))
    hist = m.history(memory)["history"]
    out[memory] = {"admitted": rec["admitted"].count(uuid), "events": [e["event_type"] for e in hist["events"]],
                   "write_semantics": m.write_semantics(uuid) is not None}
m.close()
print(json.dumps(out))
'''

_CHILD_ADMITTED = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import agentmem_ref
from agentmem_ref import AgentMemory
root, tenant, actor, scope, query = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
m = AgentMemory.open(root, tenant=tenant, actor_id=actor, scope=scope, purpose="c786")
out = {"package": agentmem_ref.__file__,
       "admitted": sorted(m.recall(f"{query} digest", temporal_intent={"mode": "historical"})["admitted"])}
m.close()
print(json.dumps(out))
'''


class DirectProbes(_Citer):
    """Positive control (review SF-7b): a foreign deleted identifier addressed directly, as
    a dispute target or a write-semantics lookup, already reads exactly like a guess."""

    def test_a_dispute_by_uuid_and_a_write_semantics_lookup_read_like_a_guess(self):
        self.fresh()
        a1, _ = self.seed_a(permanent=False)
        self.reopen("project:b")
        own = self.memory.remember("memory:b-probe", f"{QUERY} digest probe")
        shapes = {}
        for label, ref in (("deleted", a1), ("unknown", GUESS)):
            disputed = self.memory.dispute("memory:b-probe", fact_uuid=ref, evidence=_evidence("project:b", TENANT), risk_class="low")
            self.assertFalse(disputed["committed"], disputed)
            shapes[label] = {"dispute": _shape(disputed, self_uuid=own["fact_uuid"], ref=ref, label="probe"),
                             "write_semantics": self.memory.write_semantics(ref)}
        self.assertEqual(shapes["deleted"], shapes["unknown"])
        self.assertIsNone(shapes["unknown"]["write_semantics"])
        self.assertEqual(self.memory.history("memory:b-probe")["history"]["events"][-1]["event_type"], "memory.receipt")


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

    def test_the_owners_view_after_the_other_scope_re_creates_and_deletes_the_id(self):
        """Review SF-7d: A's old derivation stays withheld through B's re-creation of the id,
        and A's citation of B's generation never binds (it is foreign to A), so B's later
        deletion changes nothing A can see."""
        self.fresh()
        a1 = self.seed()
        d1 = self.memory.remember("memory:d1", f"{QUERY} digest one", evidence_refs=(a1,))["fact_uuid"]
        self.forget_a(permanent=False)
        self.assertNotIn(d1, self.admitted_historical())
        self.reopen("project:b")
        again = self.memory.remember("memory:a", f"{QUERY} is Turku", proposition=_prop("Turku"))
        self.assertTrue(again["committed"], again)
        self.reopen("project:a")
        x = self.memory.remember("memory:x", f"{QUERY} digest x", evidence_refs=(again["fact_uuid"],))
        self.assertTrue(x["committed"], x)
        self.assertEqual(self.admitted_historical() & {d1, x["fact_uuid"]}, {x["fact_uuid"]})
        self.reopen("project:b")
        self.assertTrue(self.memory.forget("memory:a")["committed"])
        self.reopen("project:a")
        self.assertEqual(self.admitted_historical() & {d1, x["fact_uuid"]}, {x["fact_uuid"]})
        self.reopen("project:a")
        self.assertEqual(self.admitted_historical() & {d1, x["fact_uuid"]}, {x["fact_uuid"]})


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


class ProvenanceAudit(_Citer):
    """Review SF-7c: the owner's revocation audit (``undeclared_residue``) follows the bound
    derivation. A foreign citation of the owner's deleted fact never bound, so it is not a
    remnant of the owner's deletion (and the owner no longer learns a foreign fact uuid
    through it); the owner's own undeclared derivation still is one, or was declared."""

    def test_a_foreign_citation_is_not_residue_of_the_owners_deletion(self):
        self.fresh()
        a1 = self.seed()
        d1 = self.memory.remember("memory:d1", f"{QUERY} digest one", evidence_refs=(a1,))["fact_uuid"]
        self.reopen("project:b")
        foreign = self.cite("foreign", a1)["uuid"]
        self.reopen("project:a")
        self.forget_a(permanent=False)
        for _ in range(2):
            residue = set(self.adapter.undeclared_residue(a1))
            declared = set(self.adapter.tombstone(a1)["declared_derived_refs"])
            self.assertNotIn(foreign, residue | declared)
            self.assertIn(d1, residue | declared)
            self.reopen("project:a")


class OwnScopeDeletionCompleteness(_Citer):
    """Positive controls: within the writer's own scope the #776/#777 rule is unchanged."""

    def _chain(self):
        a1 = self.seed()
        d1 = self.memory.remember("memory:d1", f"{QUERY} digest one", evidence_refs=(a1, "evidence:ticket-7"))["fact_uuid"]
        d2 = self.memory.remember("memory:d2", f"{QUERY} digest two", evidence_refs=(d1,))["fact_uuid"]
        ctl = self.memory.remember("memory:ctl", f"{QUERY} digest control", evidence_refs=("evidence:ticket-7",))["fact_uuid"]
        return a1, d1, d2, ctl

    def _admitted(self):
        return self.admitted_historical()

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

    def test_own_scope_dependencies_survive_a_genuine_process_restart_before_and_after_the_deletion(self):
        """Review SF-7a: a genuine restart between the citation and the deletion, and another
        after the deletion (pruning, and attested permanent deletion that purges the payload),
        keeps the dependency: the derivations are withheld, the external-only control is not."""
        for permanent in (False, True):
            with self.subTest(permanent=permanent):
                self.fresh()
                a1, d1, d2, ctl = self._chain()
                self.memory.close()
                first = set(self.restart(_CHILD_ADMITTED, "project:a")["admitted"])
                self.assertEqual(first & {d1, d2, ctl}, {d1, d2, ctl})
                self.memory = self.open("project:a")
                self.forget_a(permanent=permanent)
                if permanent:
                    self.assertIsNone(self.fact(a1))
                self.memory.close()
                second = set(self.restart(_CHILD_ADMITTED, "project:a")["admitted"])
                self.assertEqual(second & {d1, d2, ctl}, {ctl})
                self.memory = self.open("project:a")

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
        before it exists (the construction of test_776_transitive_traversal_review).

        Declared behavioural change (review SF-4): before #809 the forward note became
        refused once the cited id materialised as a derivation of a deleted source
        (``test_776_transitive_traversal_review::test_decision_does_not_depend_on_query_order``
        asserted ``assertFalse(fresh)``). That guarantee is withdrawn here: provenance is
        caller-declared and a writer who cites nothing already escapes it, so a pre-citation
        gives the writer no power it did not have by omission, and a late-bound link would
        have to be judged under a context the runtime no longer holds. The owner's explicit
        acceptance of this change is requested in the #809 handoff; it is not a consequence
        of the repair that the owner has already approved."""
        with tempfile.TemporaryDirectory() as d1:
            late_id, *_ = self._scenario(d1 + "/m", "external:placeholder")
        with tempfile.TemporaryDirectory() as d2:
            late, fwd, fwd_admitted, late_admitted = self._scenario(d2 + "/m", late_id)
        self.assertEqual(late, late_id)
        self.assertFalse(late_admitted, "the late derivation of a deleted source is withheld")
        self.assertTrue(fwd_admitted, "a reference that named no fact at commit never binds")


class RecordedDerivation(_Citer):
    """Pins the implementation shape (review A.13: a deviation from the disposition's option
    (b) sketch, which filtered ``episode_uuids``; filtering would itself distinguish a dropped
    foreign reference from a kept guess at the substrate, so the caller's references are kept
    verbatim and the bound set is recorded apart from them)."""

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
        self.assertIn(self._refused(member, _ctx(("project:b", "shared:x"), "agent:b")), DELETION_FAMILY)
        self.assertIsNone(self._refused(stranger, _ctx(("project:c", "shared:x"), "agent:c")))

    def test_revocation_after_binding_keeps_the_dependency(self):
        self.adapter.set_shared_domain_members("shared:x", ("agent:a", "agent:b"))
        s1 = self.adapter.commit_proposal(_proposal(), "shared window is Thursday").fact_uuid
        member = self._digest("pb", "agent:b", ("project:b", "shared:x"), s1, target="mem:b")
        self.adapter.set_shared_domain_members("shared:x", ("agent:a",))
        self._delete_shared(s1)
        self.assertIn(self._refused(member, _ctx(("project:b", "shared:x"), "agent:b")), DELETION_FAMILY)

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
        self.assertIn(self._refused(same, _ctx((TENANT,), project="project:p", task="task:1")), DELETION_FAMILY)
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


class SharedDomainDurable(_Citer):
    """Review SF-7e, facade over SQLite: a member's binding survives revocation of its
    membership, handle reopens and the source's deletion; a stranger granted membership
    only after its citation never binds, also after reopens. Facts are written into the
    shared domain alone (host-supplied scope override) so that membership is the gate."""

    SHARED = {"isolation_domain_refs": ["shared:x"], "required_isolation_domain_refs": ["shared:x"]}

    def handle(self, actor: str, scope: str = "shared:x") -> AgentMemory:
        return AgentMemory.open(self.root, tenant=TENANT, actor_id=actor, scope=scope, purpose="c786")

    def test_binding_survives_revocation_and_reopen_and_a_later_grant_binds_nothing(self):
        self.fresh()
        self.memory.close()
        owner = self.handle("agent:a")
        owner.runtime.adapter.set_shared_domain_members("shared:x", ("agent:a", "agent:b"))
        s1 = owner.remember("memory:s", f"{QUERY} is Thursday", proposition=_prop("Thursday"), overrides=self.SHARED)
        self.assertTrue(s1["committed"], s1)
        owner.close()
        member = self.handle("agent:b")
        bound = member.remember("memory:sb", f"{QUERY} digest member", evidence_refs=(s1["fact_uuid"],), overrides=self.SHARED)
        self.assertTrue(bound["committed"], bound)
        member.close()
        stranger = self.handle("agent:c", "project:c")
        unbound = stranger.remember("memory:sc", f"{QUERY} digest stranger", evidence_refs=(s1["fact_uuid"],),
                                    overrides={"isolation_domain_refs": ["project:c", "shared:x"],
                                               "required_isolation_domain_refs": ["project:c"]})
        self.assertTrue(unbound["committed"], unbound)
        stranger.close()
        owner = self.handle("agent:a")
        owner.runtime.adapter.set_shared_domain_members("shared:x", ("agent:a", "agent:c"))  # revoke b, grant c
        owner.close()
        owner = self.handle("agent:a")
        self.assertEqual(owner.runtime.adapter._shared_domain_members["shared:x"], {"agent:a", "agent:c"})
        self.assertTrue(owner.forget("memory:s")["committed"])
        owner.close()
        for _ in range(2):
            owner = self.handle("agent:a")
            result = owner.runtime.adapter.governed_recall(f"{QUERY} digest", owner._handle_recall_context())
            self.assertIn(bound["fact_uuid"], result.candidates, result.refusals)
            self.assertIn(result.refusals.get(bound["fact_uuid"]), DELETION_FAMILY)
            owner.close()
            stranger = self.handle("agent:c", "project:c")
            self.assertIn(unbound["fact_uuid"], stranger.recall(f"{QUERY} digest", temporal_intent=HIST)["admitted"])
            stranger.close()
        self.memory = self.open("project:a")


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
            self.assertNotIn(key, substrate.get_fact(d).attributes or {})
        # every adapter-side memo of the deletion decision (review SF-5): the fallback must be
        # read from the fact at evaluation time, not from a cache filled before the pop
        adapter._derived_taint_memo = None
        adapter._deleted_lineage_cache = None
        out = adapter.governed_delete(
            _proposal(proposal_id="d1", operation="pruning", proposed_strength="archived", scope="project:a",
                      isolation_domain_refs=("project:a",), target_reference="mem:a"), a1)
        self.assertTrue(out.committed, out.refusal)
        result = adapter.governed_recall("legacy window digest", _ctx(("project:a",)))
        self.assertIn(d, result.candidates, result.refusals)
        self.assertIn(result.refusals.get(d), DELETION_FAMILY)


class LegacyFactsDurable(_Citer):
    """Review SF-5: the same on durable data. A legacy row (its recorded derivation removed
    through the SQLite substrate) is reopened from disk and still follows its source's
    deletion. The row is rewritten on every runtime, so the baseline exercises the rewrite."""

    def test_a_legacy_row_keeps_binding_across_reopens(self):
        from agentmem_ref.runtime import adapter as adapter_module

        self.fresh()
        a1 = self.seed()
        d = self.memory.remember("memory:d", f"{QUERY} digest legacy", evidence_refs=(a1,))["fact_uuid"]
        key = getattr(adapter_module, "DERIVATION_KEY", None)
        attributes = dict(self.fact(d).attributes or {})
        if key is not None:
            attributes.pop(key, None)
        self.adapter._substrate._connection.execute(
            "UPDATE facts SET attributes_json = ? WHERE uuid = ?", (_canonical_bytes(attributes).decode("utf-8"), d))
        self.reopen("project:a")
        if key is not None:
            self.assertNotIn(key, self.fact(d).attributes or {})
        self.assertIn(d, self.admitted_historical())
        self.forget_a(permanent=False)
        self.assertNotIn(d, self.admitted_historical())
        self.reopen("project:a")
        self.assertNotIn(d, self.admitted_historical())


if __name__ == "__main__":
    unittest.main()
