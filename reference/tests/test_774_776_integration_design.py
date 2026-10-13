"""Design verification (#774 x #776): no predecessor traversal may cross a deleted generation.

Adversarial cases beyond the four preregistered contract tests. Executed against a
DISPOSABLE combination only; this is evidence for a design, not a candidate.
"""
from __future__ import annotations

import unittest
from dataclasses import replace

from agentmem_ref import policy
from agentmem_ref.runtime.configured_restart import ConfigBoundRestartRuntime
from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime
from tests.qualified_fixtures import corpus_for, rule
from tests.test_774_governed_predecessor import KILN, S, E, _History
from tests.test_runtime_composition import _context, _plan

Q = "What glaze did the kiln firing schedule use before?"


def _recreate(h, memory, texts, start):
    """Re-create ``memory`` with a governed promotion, then state changes."""
    first = h.runtime.retain(h._proposal(memory, start), texts[0])
    assert first.committed, first
    ids = [first.fact_uuid]
    for i, text in enumerate(texts[1:], start=start + 1):
        prior = texts[i - start - 1]
        corpus = corpus_for(rule(rule_id=f"rule:design:{memory}:{i}", target=f"memory:774:{memory}",
                                 criterion="value-correction", from_state=prior, to_values=(text,)))
        h._verifiers.append(corpus.verifier())
        out = h.runtime.correct(
            h._proposal(memory, i, op="correction",
                        state_snapshot=f"v{h.runtime.adapter.state_version(f'memory:774:{memory}')}", review_satisfied=True,
                        approval_refs=("approval:design",)),
            text, replacement_kind=S,
            evidence=corpus.evidence_for(target_reference=f"memory:774:{memory}", criterion="value-correction",
                                         pre_state=prior, proposed_value=text))
        assert out.committed, out
        ids.append(out.fact_uuid)
    return ids


def _purge(h, memory, fact=None):
    corpus = corpus_for(rule(rule_id=f"rule:design:purge:{memory}:{fact}", target=f"memory:774:{memory}",
                             criterion="permanent-deletion", from_state="current", to_values=("deleted",)))
    h._verifiers.append(corpus.verifier())
    proposal = replace(h._proposal(memory, 98, op="permanent_deletion"), reversibility="irreversible",
                       review_satisfied=True, approval_refs=("approval:dpo",))
    evidence = corpus.evidence_for(target_reference=f"memory:774:{memory}", criterion="permanent-deletion",
                                   pre_state="current", proposed_value="deleted")
    out = (h.runtime.delete_current(proposal, evidence=evidence) if fact is None else
           h.runtime.durable_runtime.governed_delete(proposal, fact, evidence=evidence))
    assert out.committed, out


class GenerationBoundary(unittest.TestCase):
    def test_erased_old_generation_does_not_block_the_new_generations_history(self):
        h = _History(self, {"kiln": KILN})
        _purge(h, "kiln")
        n1, n2 = _recreate(h, "kiln", ["The kiln firing schedule uses cone 4 glaze.",
                                       "The kiln firing schedule uses cone 5 glaze."], 80)
        self.assertEqual(h.runtime.adapter.governed_state_change_predecessor(n2, _context()), n1)
        self.assertIsNone(h.runtime.adapter.governed_state_change_predecessor(n1, _context()))

    def test_erased_superseded_version_is_not_skipped_to_an_older_one(self):
        h = _History(self, {"tram": [("Route 4 trams run every 20 minutes.", None),
                                     ("Route 4 trams run every 15 minutes.", S),
                                     ("Route 4 trams run every 10 minutes.", S)]})
        v1, v2, v3 = h.ids["tram"]
        _purge(h, "tram", v2)
        self.assertIsNone(h.runtime.adapter._substrate.get_fact(v2))
        self.assertIsNone(h.runtime.adapter.governed_state_change_predecessor(v3, _context()))

    def test_second_generation_history_is_its_own(self):
        h = _History(self, {"kiln": KILN})
        old = set(h.ids["kiln"])
        h.delete("kiln")
        n1, n2 = _recreate(h, "kiln", ["The kiln firing schedule uses cone 4 glaze.",
                                       "The kiln firing schedule uses cone 5 glaze."], 50)
        ad = h.runtime.adapter
        self.assertEqual(ad.governed_state_change_predecessor(n2, _context()), n1)
        self.assertIsNone(ad.governed_state_change_predecessor(n1, _context()))  # never crosses into old
        out = h.select(Q, budget=5)
        self.assertEqual((out.predecessor_ref, out.successor_ref), (n1, n2))
        self.assertFalse(old & set(out.served_refs))
        self.assertFalse(old & set(h.recall(Q, "historical").admitted))

    def test_deleted_superseded_version_is_not_skipped_to_an_older_one(self):
        h = _History(self, {"tram": [("Route 4 trams run every 20 minutes.", None),
                                     ("Route 4 trams run every 15 minutes.", S),
                                     ("Route 4 trams run every 10 minutes.", S)]})
        v1, v2, v3 = h.ids["tram"]
        out = h.runtime.adapter.governed_delete(replace(
            h._proposal("tram", 77, op="pruning"), target_class=policy.M1, proposed_strength="tentative",
            review_satisfied=True, approval_refs=("approval:design",)), v2)
        self.assertTrue(out.committed, out)
        ad = h.runtime.adapter
        self.assertFalse(ad.memory_deleted(v3))
        self.assertIsNone(ad.governed_state_change_predecessor(v3, _context()))  # not v1
        self.assertEqual(ad.lineage_head(v1, _context()), v3)
        self.assertIsNone(ad.lineage_head(v2, _context()))
        sel = h.select("How often did Route 4 trams run before?", budget=5)
        self.assertNotIn(v2, sel.served_refs)
        self.assertIsNone(sel.predecessor_ref)

    def test_declared_deleted_successor_is_refused_like_an_unknown_one(self):
        h = _History(self, {"kiln": KILN})
        old, head = h.ids["kiln"]
        h.delete("kiln")
        for ref in (head, old, "ref-does-not-exist"):
            with self.subTest(ref=ref), self.assertRaises(ValueError) as caught:
                h.select(Q, successor_ref=ref)
            self.assertEqual(str(caught.exception), "declared successor is not visible to this reader")

    def test_error_correction_inside_new_generation_is_skipped_but_boundary_holds(self):
        h = _History(self, {"kiln": KILN})
        h.delete("kiln")
        n1 = h.runtime.retain(h._proposal("kiln", 60), "The kiln firing schedule uses cone 4 glaze.").fact_uuid
        corpus = corpus_for(rule(rule_id="rule:design:ec", target="memory:774:kiln", criterion="value-correction",
                                 from_state="The kiln firing schedule uses cone 4 glaze.",
                                 to_values=("The kiln firing schedule uses cone 3 glaze.",)))
        h._verifiers.append(corpus.verifier())
        n2 = h.runtime.correct(
            h._proposal("kiln", 61, op="correction", state_snapshot=f"v{h.runtime.adapter.state_version('memory:774:kiln')}", review_satisfied=True,
                        approval_refs=("approval:design",)), "The kiln firing schedule uses cone 3 glaze.",
            replacement_kind=E, evidence=corpus.evidence_for(
                target_reference="memory:774:kiln", criterion="value-correction",
                pre_state="The kiln firing schedule uses cone 4 glaze.",
                proposed_value="The kiln firing schedule uses cone 3 glaze.")).fact_uuid
        # n1 never held (error-corrected); behind it is the deleted generation: nothing.
        self.assertIsNone(h.runtime.adapter.governed_state_change_predecessor(n2, _context()))

    def test_boundary_survives_restart(self):
        h = _History(self, {"kiln": KILN})
        old = set(h.ids["kiln"])
        h.delete("kiln")
        n1, n2 = _recreate(h, "kiln", ["The kiln firing schedule uses cone 4 glaze.",
                                       "The kiln firing schedule uses cone 5 glaze."], 70)
        root = h.runtime.durable_runtime.base.store.root
        rec = ConfiguredCompositionRuntime(durable_runtime=ConfigBoundRestartRuntime.recover(root, plan=_plan()),
                                           plan=_plan())
        ad = rec.adapter
        self.assertTrue(all(ad.memory_deleted(r) for r in old))
        self.assertFalse(ad.memory_deleted(n2))
        self.assertEqual(ad.lineage_head(n1, _context()), n2)
        self.assertEqual(ad.governed_state_change_predecessor(n2, _context()), n1)
        self.assertIsNone(ad.governed_state_change_predecessor(n1, _context()))
        out = rec.historical_predecessor_context(Q, _context(), budget=5)
        self.assertFalse(old & set(out.served_refs))


if __name__ == "__main__":
    unittest.main()
