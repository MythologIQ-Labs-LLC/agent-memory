"""#809 legacy upgrade, amendment 1: a legacy self-reference never binds (preregistered).

The record is ``reports/validation/809-legacy-upgrade/AMENDMENT-1-self-reference.PREREGISTERED.md``.
Amended rule 2: a cited reference minted after the citing fact, or equal to it
(``seq(r) >= seq(F)``), is ``forward_reference`` and never binds. A self-reference cannot
have named a previously committed fact.

The store under ``reference/fixtures/809-legacy-self-reference`` was written by the published v7
runtime (``16a248b1``) and is byte-frozen with its own manifest. The frozen
``809-legacy-stores`` fixtures are untouched. Every test copies the store before opening it.

Expected RED on the unmodified head ``e88bced2``:
- ``Upgrade.test_self_references_are_forward_and_unbound_the_prior_dependency_stays``;
- ``IdempotentAndDurable.test_a_second_run_rewrites_nothing_and_restart_reads_the_same``;
- ``NoFabricationSelfReference``;
- ``ResidueAudit.test_after_the_upgrade_a_self_citer_is_not_its_own_residue`` (addendum, section 9).

Every other test is a control that is GREEN before and after the repair. A failure after the
repair is a finding to investigate, never permission to weaken a line.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agentmem_ref import AgentMemory
# #786 store identity profiles: this module drives several projects through one tenant-wide store to
# exercise the canonical adapter gates; AgentMemory.open admits that only as scope_distinct_v1, so the
# test-only tenant-wide fixture reproduces the pre-profile store (tests/_tenant_wide_fixture.py).
from tests._tenant_wide_fixture import open_tenant_wide
from tests import test_809_legacy_upgrade as legacy
from tests.test_809_legacy_upgrade import KEY, POLICY, QUERY, ROOT, TENANT

FIXTURES = ROOT / "reference/fixtures/809-legacy-self-reference"
SELF_EDGE_CLASSES = {"unknown_reference": 3, "eligible": 2, "forward_reference": 3}


def _nonzero(edges: dict) -> dict:
    return {k: v for k, v in edges.items() if v}


class _SelfStore(legacy._Store):
    fixtures = FIXTURES
    store = "self-reference"

    def interest(self, handle: AgentMemory) -> set[str]:
        names = ("a1", "prior", "self", "mixed", "fwd", "next", "other")
        return self.admitted(handle) & {self.ids[n] for n in names}

    def expect_admitted_a(self) -> set[str]:
        return {self.ids["self"], self.ids["fwd"], self.ids["next"]}


class SelfReferenceFixture(unittest.TestCase):
    def test_the_store_and_script_are_byte_frozen_and_v7_produced(self):
        manifest = json.loads((FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "frozen")
        self.assertEqual(manifest["produced_by"]["revision"], "16a248b1e28f455fbf19217114175f0c20df2a01")
        for store, entry in manifest["stores"].items():
            for name, digest in entry["files"].items():
                with self.subTest(store=store, file=name):
                    self.assertEqual(hashlib.sha256((FIXTURES / store / name).read_bytes()).hexdigest(), digest)
        for name, digest in manifest["scripts"].items():
            self.assertEqual(hashlib.sha256((FIXTURES / "produce" / name).read_bytes()).hexdigest(), digest)

    def test_the_v7_rows_really_cite_themselves_and_carry_no_derivation_record(self):
        import sqlite3

        ids = json.loads((FIXTURES / "self-reference/ids.json").read_text(encoding="utf-8"))
        db = FIXTURES / "self-reference/agent-memory.sqlite3"
        with sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True) as c:
            rows = {u: (json.loads(e), json.loads(a or "{}")) for u, e, a in
                    c.execute("SELECT uuid, episode_uuids_json, attributes_json FROM facts")}
        self.assertEqual(rows[ids["self"]][0], [ids["self"]])
        self.assertEqual(rows[ids["mixed"]][0], [ids["a1"], ids["mixed"]])
        self.assertEqual(rows[ids["prior"]][0], [ids["a1"]])
        self.assertEqual(rows[ids["fwd"]][0], [ids["next"]])
        self.assertTrue(all(KEY not in attrs for _, attrs in rows.values()))


class BeforeUpgrade(_SelfStore):
    def test_pending_status_and_the_legacy_dependency_of_the_deleted_source(self):
        a = self.open("project:a")
        self.assertEqual(a.legacy_upgrade_status()["status"], "legacy_pending")
        self.assertEqual(self.interest(a), self.expect_admitted_a())
        a.close()
        b = self.open("project:b", "agent:other")
        self.assertEqual(self.interest(b), {self.ids["other"]})


class Upgrade(_SelfStore):
    def test_self_references_are_forward_and_unbound_the_prior_dependency_stays(self):  # FAIL-FIRST
        a = self.open("project:a")
        report = a.upgrade_canonical_derivation()
        i = self.ids
        self.assertEqual(self.record(a, i["self"])["classification"], {i["self"]: "forward_reference"})
        self.assertEqual(self.record(a, i["self"])["bound"], [])
        self.assertEqual(self.record(a, i["mixed"])["classification"], {i["a1"]: "eligible", i["mixed"]: "forward_reference"})
        self.assertEqual(self.record(a, i["mixed"])["bound"], [i["a1"]])
        self.assertEqual(self.record(a, i["prior"])["classification"], {i["a1"]: "eligible"})
        self.assertEqual(self.record(a, i["prior"])["bound"], [i["a1"]])
        self.assertEqual(self.record(a, i["fwd"])["classification"], {i["next"]: "forward_reference"})
        self.assertEqual(self.record(a, i["fwd"])["bound"], [])
        for name in ("a1", "next", "other"):
            rec = self.record(a, i[name])
            self.assertEqual(set(rec["classification"].values()), {"unknown_reference"}, name)
            self.assertEqual(rec["bound"], [], name)
        self.assertEqual(self.record(a, i["self"])["policy"], POLICY)
        self.assertEqual(_nonzero(report["edges"]), SELF_EDGE_CLASSES)
        self.assertEqual((report["status"], report["quarantined"]), ("legacy_qualified", {}))

    def test_recall_after_the_upgrade_keeps_the_deleted_source_dependency(self):  # control
        a = self.open("project:a")
        a.upgrade_canonical_derivation()
        self.assertEqual(self.interest(a), self.expect_admitted_a())


class DerivedDeletion(_SelfStore):
    def test_forgetting_a_self_citing_fact_after_the_upgrade_is_an_ordinary_deletion(self):  # control
        a = self.open("project:a")
        a.upgrade_canonical_derivation()
        self.assertTrue(a.forget("memory:self")["committed"])
        self.assertEqual(self.interest(a), {self.ids["fwd"], self.ids["next"]})
        a.close()
        reopened = self.open("project:a")  # recovery verifies the published digests
        self.assertEqual(self.interest(reopened), {self.ids["fwd"], self.ids["next"]})


class DerivedDeletionBeforeUpgrade(_SelfStore):
    def test_forgetting_self_citers_on_a_pending_store_terminates_and_recovers(self):  # control (addendum, review F2)
        a = self.open("project:a")
        self.assertTrue(a.forget("memory:self")["committed"])
        self.assertTrue(a.forget("memory:mixed")["committed"])
        self.assertEqual(self.interest(a), {self.ids["fwd"], self.ids["next"]})
        a.close()
        reopened = self.open("project:a")
        self.assertEqual(reopened.legacy_upgrade_status()["status"], "legacy_pending")
        self.assertEqual(self.interest(reopened), {self.ids["fwd"], self.ids["next"]})


class ResidueAudit(_SelfStore):
    """Addendum (review F1): the deletion residue audit lists every fact whose derivation refs name
    the deleted fact. A self-citing legacy row names itself."""

    def residue(self, handle: AgentMemory) -> dict:
        adapter = handle.runtime.adapter
        return {name: adapter.undeclared_residue(self.ids[name]) for name in ("self", "mixed")}

    def test_on_a_pending_store_a_self_citer_is_its_own_residue(self):  # control: accepted legacy-fallback residual
        a = self.open("project:a")
        a.forget("memory:self"); a.forget("memory:mixed")
        self.assertEqual(self.residue(a), {"self": [self.ids["self"]], "mixed": [self.ids["mixed"]]})

    def test_after_the_upgrade_a_self_citer_is_not_its_own_residue(self):  # FAIL-FIRST (addendum)
        a = self.open("project:a")
        a.upgrade_canonical_derivation()
        a.forget("memory:self"); a.forget("memory:mixed")
        self.assertEqual(self.residue(a), {"self": [], "mixed": []})
        a.close()
        self.assertEqual(self.residue(self.open("project:a")), {"self": [], "mixed": []})


class IdempotentAndDurable(_SelfStore):
    def test_a_second_run_rewrites_nothing_and_restart_reads_the_same(self):  # FAIL-FIRST
        a = self.open("project:a")
        first = a.upgrade_canonical_derivation()
        second = a.upgrade_canonical_derivation()
        self.assertEqual(second["facts_rewritten"], 0)
        self.assertEqual(_nonzero(second["edges"]), SELF_EDGE_CLASSES)
        self.assertEqual(second["status"], first["status"])
        self.assertEqual(self.record(a, self.ids["self"])["bound"], [])
        a.close()
        reopened = self.open("project:a")
        self.assertEqual(reopened.legacy_upgrade_status()["status"], "legacy_qualified")
        self.assertEqual(self.record(reopened, self.ids["mixed"])["bound"], [self.ids["a1"]])
        self.assertEqual(self.interest(reopened), self.expect_admitted_a())  # addendum (review F5)
        reopened.close()
        restarted = self.restart_status("project:a")
        self.assertEqual(restarted["status"]["status"], "legacy_qualified")
        self.assertEqual(set(restarted["admitted"]) & {self.ids[n] for n in self.ids}, self.expect_admitted_a())


class ScopeIsolation(_SelfStore):
    def test_project_b_sees_only_its_own_fact_before_and_after(self):  # control
        a = self.open("project:a")
        a.upgrade_canonical_derivation()
        a.close()
        b = self.open("project:b", "agent:other")
        self.assertEqual(self.interest(b), {self.ids["other"]})


class NoFabricationSelfReference(legacy.NoFabrication):  # FAIL-FIRST
    fixtures = FIXTURES
    store = "self-reference"  # unittest runs setUp before _check: the default store must exist here

    def test_no_edge_is_fabricated_or_dropped_without_a_durable_reason(self):
        self._check("self-reference", "project:a", "agent:legacy")


class NewWriteControl(unittest.TestCase):
    def test_a_new_write_citing_its_own_predicted_id_binds_nothing(self):  # control
        with tempfile.TemporaryDirectory() as tmp:
            def scenario(root, self_id):
                m = open_tenant_wide(root, tenant=TENANT, actor_id="agent:legacy", scope="project:a", purpose="legacy")
                try:
                    a1 = m.remember("memory:a", f"{QUERY} is Oslo")["fact_uuid"]
                    out = m.remember("memory:self", f"{QUERY} digest self", evidence_refs=(a1, self_id))["fact_uuid"]
                    rec = dict((m.runtime.adapter._substrate.get_fact(out).attributes or {}).get(KEY) or {})
                    return a1, out, rec
                finally:
                    m.close()
            _, predicted, _ = scenario(tmp + "/discover", "external:placeholder")
            a1, uuid, rec = scenario(tmp + "/m", predicted)
            self.assertEqual(uuid, predicted)
            self.assertEqual(rec["bound"], [a1])


if __name__ == "__main__":
    unittest.main()
