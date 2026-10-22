"""#809 legacy upgrade on the in-memory substrate (unit coverage beside the preregistered
facade/SQLite module ``test_809_legacy_upgrade``): the classifier and the rewrite primitive on
``InMemoryTemporalGraph``, with legacy rows produced by removing the record."""
from __future__ import annotations

import unittest

from agentmem_ref.runtime.adapter import (
    DERIVATION_KEY, LEGACY_UPGRADE_KEY, RECONSTRUCTED_POLICY, Clock, GovernedMemoryAdapter, RecallContext)
from agentmem_ref.substrate import InMemoryTemporalGraph
from tests.test_786_cross_scope_write_authority import TENANT, _proposal


def _strip(substrate: InMemoryTemporalGraph, uuid: str) -> None:
    fact = substrate.get_fact(uuid)
    attributes = dict(fact.attributes or {})
    attributes.pop(DERIVATION_KEY, None)
    substrate.rewrite_fact_attributes(uuid, attributes)


class InMemoryLegacyUpgrade(unittest.TestCase):
    def setUp(self):
        self.substrate = InMemoryTemporalGraph()
        self.adapter = GovernedMemoryAdapter(self.substrate, tenant=TENANT, clock=Clock())

    def _write(self, pid, actor, domains, target, refs=("evidence:seed",), project="", task=""):
        out = self.adapter.commit_proposal(
            _proposal(proposal_id=pid, actor_id=actor, scope=domains[0], isolation_domain_refs=tuple(domains),
                      project_ref=project, task_ref=task, target_reference=target, evidence_refs=tuple(refs)),
            f"legacy window {pid}")
        self.assertTrue(out.committed, out.refusal)
        return out.fact_uuid

    def test_every_class_from_durable_state_and_the_rewrite_is_in_place(self):
        self.adapter.set_shared_domain_members("shared:x", ("agent:a", "agent:b"))
        a1 = self._write("a1", "agent:a", ("project:a",), "mem:a")
        own = self._write("own", "agent:a", ("project:a",), "mem:own", refs=(a1, "evidence:ticket"))
        foreign = self._write("foreign", "agent:b", ("project:b",), "mem:b", refs=(a1,))
        s1 = self._write("s1", "agent:a", ("shared:x",), "mem:s")
        member = self._write("member", "agent:b", ("shared:x",), "mem:sb", refs=(s1,))
        forward = self._write("forward", "agent:a", ("project:a",), "mem:fwd", refs=("ref-0999",))
        for uuid in (a1, own, foreign, s1, member, forward):
            _strip(self.substrate, uuid)
        self.assertEqual(self.adapter.legacy_upgrade_status()["status"], "legacy_pending")
        report = self.adapter.upgrade_canonical_derivation()
        self.assertEqual(report["status"], "legacy_unqualified")
        self.assertEqual(report["facts_rewritten"], 6)
        rec = lambda u: (self.substrate.get_fact(u).attributes or {})[DERIVATION_KEY]  # noqa: E731
        self.assertEqual(rec(own)["classification"], {a1: "eligible", "evidence:ticket": "unknown_reference"})
        self.assertEqual(rec(own)["bound"], [a1])
        self.assertEqual(rec(foreign)["classification"], {a1: "ineligible_scope"})
        self.assertEqual(rec(member)["classification"], {s1: "membership_undecidable"})
        self.assertEqual(rec(member)["bound"], [s1])
        self.assertEqual(rec(forward)["classification"], {"ref-0999": "unknown_reference"})  # never governed here
        self.assertEqual(report["quarantined"], {member: [s1]})
        self.assertEqual(rec(own)["policy"], RECONSTRUCTED_POLICY)
        self.assertIn(LEGACY_UPGRADE_KEY, self.adapter.extension_state)
        # the record now drives taint: the foreign citer is admitted after a1's deletion, own is not
        out = self.adapter.governed_delete(
            _proposal(proposal_id="d1", operation="pruning", proposed_strength="archived", scope="project:a",
                      isolation_domain_refs=("project:a",), target_reference="mem:a"), a1)
        self.assertTrue(out.committed, out.refusal)
        result = self.adapter.governed_recall("legacy window", RecallContext(target_domain_refs=("project:b",), principal_ref="agent:b"))
        self.assertIsNone(result.refusals.get(foreign))
        result = self.adapter.governed_recall("legacy window", RecallContext(target_domain_refs=("project:a",), principal_ref="agent:a"))
        self.assertIn(result.refusals.get(own), {"derived_from_tombstoned_source", "derived_from_deleted_logical_memory"})
        again = self.adapter.upgrade_canonical_derivation()
        self.assertEqual((again["facts_rewritten"], again["runs"]), (0, 2))

    def _forward_scenario(self, future: str) -> tuple[str, str]:
        a1 = self._write("a1", "agent:a", ("project:a",), "mem:a")
        fwd = self._write("fwd", "agent:a", ("project:a",), "mem:fwd", refs=(future,))
        late = self._write("late", "agent:a", ("project:a",), "mem:late", refs=(a1,))
        return fwd, late

    def test_forward_reference_class_when_the_cited_fact_exists_later(self):
        _, late_id = self._forward_scenario("external:placeholder")  # discovery pass: deterministic ids
        self.setUp()
        fwd, late = self._forward_scenario(late_id)
        self.assertEqual(late, late_id)
        _strip(self.substrate, fwd)
        report = self.adapter.upgrade_canonical_derivation()
        self.assertEqual(report["edges"]["forward_reference"], 1)
        self.assertEqual((self.substrate.get_fact(fwd).attributes or {})[DERIVATION_KEY]["bound"], [])


if __name__ == "__main__":
    unittest.main()
