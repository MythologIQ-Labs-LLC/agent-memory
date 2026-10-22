"""#776 P0: deletion must govern *all* fact versions of a logical memory.

Frozen before implementation. All writes, corrections and deletion pass the
normal governed composition path, not direct private substrate mutation.
"""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agentmem_ref import policy
from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime
from agentmem_ref.verification import TRANSITION_VERIFIER, VerifierRegistry
from tests.qualified_fixtures import corpus_for, rule
from tests.test_runtime_composition import _context, _plan, _proposal, TENANT, PROJECT


class _HistoricalDeletionStore:
    def __init__(self, case):
        self.case = case
        tmp = tempfile.TemporaryDirectory()
        case.addCleanup(tmp.cleanup)
        self.verifiers = []
        registry = VerifierRegistry()
        registry.register(TRANSITION_VERIFIER,
                          lambda item: any(verify(item) for verify in self.verifiers))
        self.runtime = ConfiguredCompositionRuntime.create(
            Path(tmp.name), tenant=TENANT, plan=_plan(), verifier_registry=registry,
        )
        self.ids = {}

    def proposal(self, memory, step, operation="promotion", project=PROJECT, **kwargs):
        item = replace(
            _proposal("proposal:776:" + memory + ":" + str(step),
                      operation=operation, project_ref=project),
            target_reference="memory:776:" + memory,
        )
        if project != PROJECT:
            item = replace(
                item, project_ref=project, isolation_domain_refs=(TENANT, project),
                required_isolation_domain_refs=(project,),
            )
        return replace(item, **kwargs)

    def chain(self, memory, texts, *, project=PROJECT, kinds=None):
        if kinds is None:
            kinds = ("state_change",) * (len(texts) - 1)
        self.case.assertEqual(len(kinds), len(texts) - 1)
        first = self.runtime.retain(self.proposal(memory, 0, project=project), texts[0])
        self.case.assertTrue(first.committed, first)
        refs = [first.fact_uuid]
        for n, (new, kind) in enumerate(zip(texts[1:], kinds), start=1):
            before = texts[n-1]
            corpus = corpus_for(rule(
                rule_id=f"rule:776:{memory}:{n}",
                target=f"memory:776:{memory}", criterion="value-correction",
                from_state=before, to_values=(new,),
            ))
            self.verifiers.append(corpus.verifier())
            changed = self.runtime.correct(
                self.proposal(memory, n, "correction", project=project,
                              state_snapshot=f"v{n}", review_satisfied=True,
                              approval_refs=("approval:776",)),
                new, replacement_kind=kind,
                evidence=corpus.evidence_for(
                    target_reference=f"memory:776:{memory}",
                    criterion="value-correction", pre_state=before, proposed_value=new,
                ),
            )
            self.case.assertTrue(changed.committed, changed)
            refs.append(changed.fact_uuid)
        self.ids[memory] = refs
        return refs

    def prune(self, memory, *, project=PROJECT):
        deleted = self.runtime.delete_current(replace(
            self.proposal(memory, 99, "pruning", project=project,
                          review_satisfied=True, approval_refs=("approval:776",)),
            target_class=policy.M1, proposed_strength="tentative",
        ))
        self.case.assertTrue(deleted.committed, deleted)

    def recall(self, text, *, mode="historical"):
        return self.runtime.multi_route_recall(
            text, _context(), temporal_intent={"mode":mode},
        )


class LogicalDeletionAdmissionTests(unittest.TestCase):
    def test_two_versions_prune_refuses_earlier_history(self):
        store = _HistoricalDeletionStore(self)
        old, new = store.chain("gearbox", [
            "The gearbox service interval was 10 days.",
            "The gearbox service interval became 20 days.",
        ])
        before = store.recall("gearbox service interval")
        self.assertIn(old, before.admitted)
        store.prune("gearbox")
        after = store.recall("gearbox service interval")
        self.assertNotIn(old, after.admitted)
        self.assertNotIn(new, after.admitted)
        self.assertNotIn(old, after.ranked_admitted)
        self.assertEqual(after.refusals.get(old), "logical_memory_deleted")

    def test_three_versions_prune_refuses_entire_history(self):
        store = _HistoricalDeletionStore(self)
        versions = store.chain("crane", [
            "The crane inspection checklist used form A.",
            "The crane inspection checklist used form B.",
            "The crane inspection checklist used form C.",
        ])
        store.prune("crane")
        for mode in ("historical", "current"):
            with self.subTest(mode=mode):
                result = store.recall("crane inspection checklist", mode=mode)
                self.assertFalse(set(versions) & set(result.admitted))

    def test_deleting_one_memory_does_not_suppress_another(self):
        store = _HistoricalDeletionStore(self)
        deleted = store.chain("gearbox", [
            "The gearbox service interval was 10 days.",
            "The gearbox service interval became 20 days.",
        ])
        retained = store.chain("pump", [
            "The water pump service interval was 7 days.",
            "The water pump service interval became 14 days.",
        ])
        store.prune("gearbox")
        result = store.recall("service interval")
        self.assertTrue(set(retained) & set(result.admitted))
        self.assertFalse(set(deleted) & set(result.admitted))

    def test_error_correction_remains_refused_and_other_history_visible(self):
        store = _HistoricalDeletionStore(self)
        erased = store.chain("rpm", [
            "The test rotor nominal speed was 900 RPM.",
            "The test rotor nominal speed was 1200 RPM.",
        ], kinds=("error_correction",))
        unrelated = store.chain("gearbox", [
            "The gearbox nominal speed was 500 RPM.",
            "The gearbox nominal speed became 700 RPM.",
        ])
        store.prune("gearbox")
        history = store.recall("nominal speed")
        self.assertNotIn(erased[0], history.admitted)
        self.assertIn(erased[1], history.admitted)
        self.assertFalse(set(unrelated) & set(history.admitted))

    def test_deletion_refusal_does_not_launder_cross_project_history(self):
        store = _HistoricalDeletionStore(self)
        foreign = store.chain("secret-gear", [
            "The private gearbox service interval was 2 days.",
            "The private gearbox service interval became 3 days.",
        ], project="project-beta")
        local = store.chain("local-gear", [
            "The local gearbox service interval was 5 days.",
            "The local gearbox service interval became 6 days.",
        ])
        store.prune("local-gear")
        result = store.recall("gearbox service interval")
        self.assertFalse(set(foreign) & set(result.admitted))
        self.assertFalse(set(local) & set(result.admitted))
        # No source text or deleted ID is included in admitted context.
        self.assertFalse(result.admitted)


if __name__ == "__main__":
    unittest.main()
