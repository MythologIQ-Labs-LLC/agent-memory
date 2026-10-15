"""#809, legacy-upgrade threat and migration decision: preregistered expectations.

Owner checkpoint on PR #815 (review 5527842455): the #809 repair binds canonical derivation at
commit for NEW writes; a fact persisted before the repair carries no record and keeps every
``episode_uuids`` entry as a deletion dependency, so for a pre-upgrade citer the F-R3-2 oracle
persists. Before security acceptance the owner requires a separate, preregistered decision:
old persisted foreign citers demonstrated on a real recoverable v7-origin store; what durable
state is available for secure reconstruction; no cross-scope public oracle after upgrade;
preservation or explicit governed quarantine of legitimately derived deletion dependencies;
never drop legacy edges without evidence, never fabricate historical read authority; if an
upgrade cannot be proven sound, label the store ``legacy_unqualified`` and block activation.

The decision these expectations pin is ``reports/validation/809-legacy-upgrade/decision.PREREGISTERED.md``.
The stores under ``reference/fixtures/809-legacy-stores`` were written by the published v7
runtime (revision ``16a248b1``, the v7 Gauntlet adapter's FROZEN_RUNTIME_REVISION) and are
byte-frozen; every test copies a store before opening it.

The operation under test does not exist on the current head: ``AgentMemory.upgrade_canonical_derivation()``
and ``AgentMemory.legacy_upgrade_status()``. Expected RED on the head these expectations are
committed on (``0808cb61``): every test of ``StatusBeforeUpgrade``, ``CrossScopeStore``,
``SharedMembershipStore``, ``ForwardReferenceStore``, ``FreshStore`` and ``NoFabrication``.
Expected GREEN before and after: ``Fixtures`` (byte identity) and ``LegacyOracleDemonstrated``
(the threat on the unmodified store, which an upgrade must not be allowed to hide: the test
observes the store BEFORE any upgrade). A failure after the implementation is a finding to
investigate, never permission to weaken a line.

Classification vocabulary (one class per cited reference of a legacy fact):
``unknown_reference`` (names no fact this store governed), ``forward_reference`` (names a fact
minted after the citing fact: never binds, the owner's non-retroactive ruling),
``ineligible_scope`` (the citing writer's reconstructed context fails an isolation, required-
domain, project or task gate against the cited fact's scope record: provably unreadable),
``eligible`` (passes every gate and the shared-membership gate does not apply),
``membership_undecidable`` (every matching isolation domain is a governed shared space, so the
decision depends on membership at write time, which the v7 runtime did not record: kept bound,
quarantined, reported), ``order_undecidable`` (ids not comparable: kept bound, quarantined).
Bound after upgrade = eligible + the two undecidable classes. Store status: ``fresh`` (no legacy
fact), ``legacy_pending`` (legacy facts, no record), ``legacy_qualified`` (upgraded, nothing
quarantined), ``legacy_unqualified`` (upgraded, at least one quarantined edge; activation over
the store is blocked by the decision record's rule).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import agentmem_ref
from agentmem_ref import AgentMemory
from tests.test_809_evidence_reference_authorization import _shape

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "reference/fixtures/809-legacy-stores"
REFERENCE = ROOT / "reference"
TENANT, QUERY, HIST = "tenant:legacy", "Quillon ferry berth", {"mode": "historical"}
KEY, POLICY = "canonical_derivation", "writer-eligible-reconstructed/1"
CLASSES = {"unknown_reference", "forward_reference", "ineligible_scope", "eligible", "membership_undecidable", "order_undecidable"}
UNDECIDABLE = {"membership_undecidable", "order_undecidable"}


def _manifest() -> dict:
    return json.loads((FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))


class _Store(unittest.TestCase):
    """A fresh copy of one frozen v7-origin store per test; handles opened on demand."""

    store = "cross-scope"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = str(Path(tmp.name) / "store")
        shutil.copytree(FIXTURES / self.store, self.root)
        self.ids = json.loads((FIXTURES / self.store / "ids.json").read_text(encoding="utf-8"))
        self.handles: list[AgentMemory] = []
        self.addCleanup(lambda: [h.close() for h in self.handles if not h.closed])

    def open(self, scope: str, actor: str = "agent:legacy") -> AgentMemory:
        handle = AgentMemory.open(self.root, tenant=TENANT, actor_id=actor, scope=scope, purpose="legacy")
        self.handles.append(handle)
        return handle

    def admitted(self, handle: AgentMemory) -> set[str]:
        return set(handle.recall(f"{QUERY} digest", temporal_intent=HIST)["admitted"])

    def fact(self, handle: AgentMemory, uuid: str):
        return handle.runtime.adapter._substrate.get_fact(uuid)

    def record(self, handle: AgentMemory, uuid: str) -> dict:
        return dict((self.fact(handle, uuid).attributes or {}).get(KEY) or {})

    def restart_status(self, scope: str, actor: str = "agent:legacy") -> dict:
        """The status as read by a genuine new process (durability of the upgrade)."""
        child = subprocess.run([sys.executable, "-c", _CHILD, str(REFERENCE), self.root, TENANT, actor, scope],
                               capture_output=True, text=True, check=True)
        out = json.loads(child.stdout)
        self.assertEqual(Path(out.pop("package")).resolve().parents[1], Path(agentmem_ref.__file__).resolve().parents[1])
        return out


_CHILD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import agentmem_ref
from agentmem_ref import AgentMemory
root, tenant, actor, scope = sys.argv[2:6]
m = AgentMemory.open(root, tenant=tenant, actor_id=actor, scope=scope, purpose="legacy")
out = {"package": agentmem_ref.__file__, "status": m.legacy_upgrade_status(),
       "admitted": sorted(m.recall("Quillon ferry berth digest", temporal_intent={"mode": "historical"})["admitted"])}
m.close()
print(json.dumps(out))
'''


class Fixtures(unittest.TestCase):
    def test_stores_and_scripts_are_byte_frozen_and_v7_produced(self):
        manifest = _manifest()
        self.assertEqual(manifest["status"], "frozen")
        self.assertEqual(manifest["produced_by"]["revision"], "16a248b1e28f455fbf19217114175f0c20df2a01")
        for store, entry in manifest["stores"].items():
            for name, digest in entry["files"].items():
                with self.subTest(store=store, file=name):
                    self.assertEqual(hashlib.sha256((FIXTURES / store / name).read_bytes()).hexdigest(), digest)
        for name, digest in manifest["scripts"].items():
            self.assertEqual(hashlib.sha256((FIXTURES / "produce" / name).read_bytes()).hexdigest(), digest)

    def test_the_v7_gauntlet_adapter_pins_the_same_revision(self):
        text = (ROOT / "examples/gauntlet/agent_memory_runtime_baseline_v7_stdio.py").read_text(encoding="utf-8")
        self.assertIn('FROZEN_RUNTIME_REVISION = "16a248b1e28f455fbf19217114175f0c20df2a01"', text)


class LegacyOracleDemonstrated(_Store):
    """The threat, observed on the unmodified v7-origin store under the current runtime, before
    any upgrade: the pre-#809 foreign citer is withheld on every channel; the owner's own
    derivation stays withheld; the legacy rows carry no derivation record."""

    def test_old_foreign_citer_is_withheld_and_own_dependency_preserved(self):
        b = self.open("project:b")
        admitted = self.admitted(b)
        self.assertNotIn(self.ids["bd"], admitted)
        self.assertIn(self.ids["bl"], admitted)
        self.assertIn(self.ids["bu"], admitted)
        self.assertEqual(b.history("memory:bd")["history"]["events"], [])
        self.assertIsNone(b.write_semantics(self.ids["bd"]))
        self.assertNotIn(KEY, self.fact(b, self.ids["bd"]).attributes or {})
        self.assertEqual(list(self.fact(b, self.ids["bd"]).episode_uuids), [self.ids["a1"]])
        a = self.open("project:a")
        self.assertEqual(self.admitted(a) & {self.ids["d1"], self.ids["ctl"]}, {self.ids["ctl"]})
        self.assertIn(self.ids["a1"], a.runtime.adapter._fact_scope)


class StatusBeforeUpgrade(_Store):
    def test_a_legacy_store_reads_legacy_pending_with_its_legacy_fact_count(self):
        a = self.open("project:a")
        status = a.legacy_upgrade_status()
        self.assertEqual(status["status"], "legacy_pending")
        self.assertEqual(status["legacy_facts"], 7)  # a1, a2, d1, ctl, bd, bl, bu
        self.assertIsNone(status["record"])


class CrossScopeStore(_Store):
    """Cross-project citations are provably unreadable from the durable scope records: they are
    unbound by the upgrade; the owner's own derivation stays bound; external ids and guesses
    are unknown references. The store becomes legacy_qualified."""

    def _expect_after(self, b: AgentMemory, a: AgentMemory):
        admitted = self.admitted(b)
        for k in ("bd", "bl", "bu"):
            self.assertIn(self.ids[k], admitted, k)
        shapes = {}
        for k, ref, memory, token in (("bd", self.ids["a1"], "memory:bd", "digest foreign deleted"),
                                      ("bl", self.ids["a2"], "memory:bl", "digest foreign live"),
                                      ("bu", "fact-guess-999999999999", "memory:bu", "digest unknown")):
            uuid = self.ids[k]
            views = {"recall": b.recall(f"{QUERY} {token}", logical_memory_refs=(memory,)),
                     "history": b.history(memory), "write_semantics": b.write_semantics(uuid)}
            shapes[k] = {ch: _shape(v, self_uuid=uuid, ref=ref, label="x").replace(memory, "memory:<m>").replace(token, "digest <t>")
                         for ch, v in views.items()}
        for ch in ("recall", "history", "write_semantics"):
            with self.subTest(channel=ch):
                self.assertEqual(shapes["bd"][ch], shapes["bu"][ch])
                self.assertEqual(shapes["bl"][ch], shapes["bu"][ch])
        self.assertEqual(self.admitted(a) & {self.ids["d1"], self.ids["ctl"]}, {self.ids["ctl"]})

    def test_upgrade_classifies_rewrites_and_closes_the_oracle_without_releasing_own_dependencies(self):
        a = self.open("project:a")
        report = a.upgrade_canonical_derivation()
        self.assertEqual(report["policy"], POLICY)
        self.assertEqual(report["status"], "legacy_qualified")
        self.assertEqual(report["facts_legacy"], 7)
        self.assertEqual(report["facts_rewritten"], 7)
        self.assertEqual(report["quarantined"], {})
        self.assertEqual(report["edges"], {"eligible": 1, "ineligible_scope": 2, "unknown_reference": 2,
                                           "forward_reference": 0, "membership_undecidable": 0, "order_undecidable": 0})
        expected = {"bd": ({self.ids["a1"]: "ineligible_scope"}, []), "bl": ({self.ids["a2"]: "ineligible_scope"}, []),
                    "bu": ({"fact-guess-999999999999": "unknown_reference"}, []),
                    "d1": ({self.ids["a1"]: "eligible"}, [self.ids["a1"]]), "ctl": ({"evidence:ticket-7": "unknown_reference"}, [])}
        for k, (classes, bound) in expected.items():
            with self.subTest(fact=k):
                rec = self.record(a, self.ids[k])
                self.assertEqual(rec["policy"], POLICY)
                self.assertEqual(rec["classification"], classes)
                self.assertEqual(list(rec["bound"]), bound)
                self.assertEqual(list(self.fact(a, self.ids[k]).episode_uuids), list(classes))  # verbatim, nothing dropped
        self.assertEqual(a.legacy_upgrade_status()["status"], "legacy_qualified")
        self._expect_after(self.open("project:b"), a)

    def test_upgrade_is_idempotent_and_durable_across_reopen_and_a_genuine_restart(self):
        a = self.open("project:a")
        first = a.upgrade_canonical_derivation()
        again = a.upgrade_canonical_derivation()
        self.assertEqual(again["facts_rewritten"], 0)
        self.assertEqual(again["status"], "legacy_qualified")
        self.assertEqual({k: v for k, v in again.items() if k not in ("runs", "completed_at")},
                         {k: v for k, v in first.items() if k not in ("runs", "runs", "completed_at", "facts_rewritten")} | {"facts_rewritten": 0})
        a.close()
        a = self.open("project:a")
        self.assertEqual(a.legacy_upgrade_status()["status"], "legacy_qualified")
        self.assertEqual(self.record(a, self.ids["d1"])["bound"], [self.ids["a1"]])
        a.close()
        child = self.restart_status("project:b")
        self.assertEqual(child["status"]["status"], "legacy_qualified")
        self.assertTrue({self.ids["bd"], self.ids["bl"], self.ids["bu"]} <= set(child["admitted"]))
        self.assertEqual(self.restart_status("project:a")["admitted"].count(self.ids["d1"]), 0)


class SharedMembershipStore(_Store):
    """Every matching isolation domain of these citations is a governed shared space, so the
    decision depends on membership at write time, which the v7 runtime did not record. The
    upgrade must not fabricate it: the edges are kept bound and quarantined, the store is
    legacy_unqualified, and the owner's deletion still withholds the member's digest. The
    oracle for the later-granted citer therefore persists and is reported, not hidden."""

    store = "shared-membership"

    def test_membership_dependent_edges_are_quarantined_and_the_store_is_unqualified(self):
        o = self.open("shared:x", "agent:o")
        report = o.upgrade_canonical_derivation()
        self.assertEqual(report["status"], "legacy_unqualified")
        self.assertEqual(report["edges"]["membership_undecidable"], 3)
        self.assertEqual(report["edges"]["eligible"], 0)
        self.assertEqual(set(report["quarantined"]), {self.ids["sm"], self.ids["sc"], self.ids["sl"]})
        for k in ("sm", "sc", "sl"):
            with self.subTest(fact=k):
                rec = self.record(o, self.ids[k])
                self.assertEqual(rec["classification"], {self.ids["s1"]: "membership_undecidable"})
                self.assertEqual(list(rec["bound"]), [self.ids["s1"]])
        self.assertEqual(o.legacy_upgrade_status()["status"], "legacy_unqualified")
        # deletion completeness preserved for the member; the quarantined oracle still reported
        for actor, k in (("agent:m", "sm"), ("agent:l", "sl")):
            h = self.open("shared:x", actor)
            self.assertNotIn(self.ids[k], self.admitted(h), k)
        o.close()
        self.assertEqual(self.restart_status("shared:x", "agent:o")["status"]["status"], "legacy_unqualified")


class ForwardReferenceStore(_Store):
    """A legacy citation of an id minted after the citing fact never binds (the owner's
    non-retroactive ruling); the late derivation of the deleted source stays bound."""

    store = "forward-reference"

    def test_forward_reference_is_unbound_and_the_late_derivation_stays_withheld(self):
        a = self.open("project:a")
        self.assertEqual(self.admitted(a) & {self.ids["fwd"], self.ids["late"]}, set())  # v7 late binding, before upgrade
        report = a.upgrade_canonical_derivation()
        self.assertEqual(report["status"], "legacy_qualified")
        self.assertEqual(report["edges"]["forward_reference"], 1)
        self.assertEqual(self.record(a, self.ids["fwd"])["classification"], {self.ids["late"]: "forward_reference"})
        self.assertEqual(self.record(a, self.ids["fwd"])["bound"], [])
        self.assertEqual(self.record(a, self.ids["late"])["bound"], [self.ids["a1"]])
        self.assertEqual(self.admitted(a) & {self.ids["fwd"], self.ids["late"]}, {self.ids["fwd"]})
        a.close()
        self.assertEqual(self.restart_status("project:a")["admitted"].count(self.ids["fwd"]), 1)


class FreshStore(unittest.TestCase):
    def test_a_store_written_by_this_runtime_is_fresh_and_the_upgrade_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = AgentMemory.open(tmp + "/m", tenant=TENANT, actor_id="agent:legacy", scope="project:a", purpose="legacy")
            try:
                a1 = m.remember("memory:a", f"{QUERY} is Oslo")["fact_uuid"]
                m.remember("memory:d", f"{QUERY} digest own", evidence_refs=(a1,))
                self.assertEqual(m.legacy_upgrade_status(), {"status": "fresh", "legacy_facts": 0, "record": None})
                report = m.upgrade_canonical_derivation()
                self.assertEqual((report["status"], report["facts_legacy"], report["facts_rewritten"]), ("fresh", 0, 0))
                self.assertEqual(m.legacy_upgrade_status()["status"], "fresh")
            finally:
                m.close()


class NoFabrication(_Store):
    """Across the three stores: an edge is marked eligible only when the reconstructed writer
    context passes every gate and the membership gate did not apply; an undecidable edge is
    never marked eligible and never dropped; the classification covers every cited reference;
    scope records of cited facts are never created or altered by the upgrade."""

    def _check(self, store: str, scope: str, actor: str):
        self.store = store
        self.setUp()
        h = self.open(scope, actor)
        adapter = h.runtime.adapter
        scopes_before = {k: dict(v) for k, v in adapter._fact_scope.items()}
        report = h.upgrade_canonical_derivation()
        self.assertEqual({k: dict(v) for k, v in adapter._fact_scope.items()}, scopes_before)
        total = 0
        for fact in adapter._substrate.all_facts():
            rec = (fact.attributes or {}).get(KEY)
            self.assertIsNotNone(rec, fact.uuid)
            if rec["policy"] != POLICY:
                continue
            classes = rec["classification"]
            self.assertEqual(set(classes), set(fact.episode_uuids))
            self.assertTrue(set(classes.values()) <= CLASSES)
            for ref, cls in classes.items():
                total += 1
                if cls in UNDECIDABLE or cls == "eligible":
                    self.assertIn(ref, rec["bound"], (fact.uuid, ref, cls))
                    self.assertIn(ref, adapter._fact_scope)
                else:
                    self.assertNotIn(ref, rec["bound"], (fact.uuid, ref, cls))
                if cls == "eligible":
                    scope_r = adapter._fact_scope[ref]
                    matching = set(scope_r["domain_refs"]) & set(adapter._fact_scope[fact.uuid]["domain_refs"])
                    self.assertTrue(matching)
                    self.assertFalse(matching and all(d in adapter._shared_domain_members for d in matching),
                                     "an eligible edge never depends on the membership gate")
        self.assertEqual(total, sum(report["edges"].values()))
        self.assertEqual(report["status"] == "legacy_unqualified", bool(report["quarantined"]))
        h.close()

    def test_no_edge_is_fabricated_or_dropped_without_a_durable_reason(self):
        for store, scope, actor in (("cross-scope", "project:a", "agent:legacy"),
                                    ("shared-membership", "shared:x", "agent:o"),
                                    ("forward-reference", "project:a", "agent:legacy")):
            with self.subTest(store=store):
                self._check(store, scope, actor)


if __name__ == "__main__":
    unittest.main()
