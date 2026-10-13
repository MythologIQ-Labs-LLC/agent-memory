"""#774: governed historical predecessor targeting (preregistered before implementation).

Generic histories authored for this slice; none reuse Halcyon or Cedarline
wording. The selector must use recorded state-change lineage and canonical
historical admission, never lexical guesses or chronological reversal.
"""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agentmem_ref import policy
from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime
from tests.qualified_fixtures import corpus_for, rule
from tests.test_runtime_composition import _context, _plan, _proposal, PROJECT, TENANT


class _History:
    """A store whose host adjudicates exactly the declared transitions."""

    def __init__(self, testcase, chains):
        # chains: {memory: [(text, kind_into_this_value or None), ...]}
        self.t = testcase
        tmp = tempfile.TemporaryDirectory()
        testcase.addCleanup(tmp.cleanup)
        # One single-rule corpus per transition (a corpus holds one rule per
        # target and criterion), behind one host-configured verifier.
        self.corpora = {}
        self._verifiers = []
        from agentmem_ref.verification import TRANSITION_VERIFIER, VerifierRegistry
        registry = VerifierRegistry()
        registry.register(TRANSITION_VERIFIER, lambda item: any(v(item) for v in self._verifiers))
        self._chains = chains
        self.runtime = ConfiguredCompositionRuntime.create(Path(tmp.name), tenant=TENANT, plan=_plan(),
                                                           verifier_registry=registry)
        self.ids: dict[str, list[str]] = {}
        for memory, versions in chains.items():
            self.write_chain(memory, versions)

    def _adjudicate(self, memory, i, before, after):
        corpus = corpus_for(rule(rule_id=f"rule:774:{memory}:{i}", target=f"memory:774:{memory}",
                                 criterion="value-correction", from_state=before, to_values=(after,)))
        self._verifiers.append(corpus.verifier())
        return corpus

    def _proposal(self, memory, n, *, project=PROJECT, op="promotion", **kw):
        base = replace(_proposal(f"proposal:774:{memory}:{n}", operation=op), target_reference=f"memory:774:{memory}")
        if project != PROJECT:
            base = replace(base, project_ref=project, isolation_domain_refs=(TENANT, project),
                           required_isolation_domain_refs=(project,))
        return replace(base, **kw)

    def write_chain(self, memory, versions, *, project=PROJECT):
        ids = []
        first = self.runtime.retain(self._proposal(memory, 0, project=project), versions[0][0])
        self.t.assertTrue(first.committed)
        ids.append(first.fact_uuid)
        for i, (text, kind) in enumerate(versions[1:], start=1):
            out = self.runtime.correct(
                self._proposal(memory, i, project=project, op="correction", state_snapshot=f"v{i}",
                               review_satisfied=True, approval_refs=("approval:774",)),
                text, replacement_kind=kind,
                evidence=self._adjudicate(memory, i, versions[i - 1][0], text).evidence_for(
                    target_reference=f"memory:774:{memory}", criterion="value-correction",
                    pre_state=versions[i - 1][0], proposed_value=text))
            self.t.assertTrue(out.committed, out)
            ids.append(out.fact_uuid)
        self.ids[memory] = ids
        return ids

    def delete(self, memory):
        out = self.runtime.delete_current(replace(
            self._proposal(memory, 99, op="pruning"), target_class=policy.M1, proposed_strength="tentative",
            review_satisfied=True, approval_refs=("approval:774",)))
        self.t.assertTrue(out.committed, out)

    def select(self, query, *, budget=3, successor_ref=None, project=PROJECT, as_of_target=None):
        return self.runtime.historical_predecessor_context(query, _context(project), budget=budget,
                                                            successor_ref=successor_ref, as_of_target=as_of_target)

    def recall(self, query, mode):
        return self.runtime.multi_route_recall(query, _context(), temporal_intent={"mode": mode})


S, E = "state_change", "error_correction"
KILN = [("The kiln firing schedule uses cone 6 glaze.", None),
        ("The kiln firing schedule uses cone 10 glaze.", S)]
TRAM = [("Route 4 trams run every 20 minutes.", None), ("Route 4 trams run every 15 minutes.", S),
        ("Route 4 trams run every 10 minutes.", S)]
LIB = [(f"The archive catalogue runs on catalogue engine version {n}.", None if n == 1 else S) for n in range(1, 6)]


class PredecessorSelection(unittest.TestCase):
    def test_two_revisions_serves_the_predecessor_at_rank_one(self):
        h = _History(self, {"kiln": KILN})
        old, new = h.ids["kiln"]
        out = h.select("What glaze did the kiln firing schedule use before cone 10?", successor_ref=new)  # strict 0.2.0
        self.assertEqual(out.served_refs[:2], (old, new))
        self.assertEqual((out.predecessor_ref, out.successor_ref), (old, new))
        self.assertEqual(out.relation, "immediate_state_change_predecessor")

    def test_three_revisions_selects_the_immediate_not_the_oldest(self):
        h = _History(self, {"tram": TRAM})
        v1, v2, v3 = h.ids["tram"]
        out = h.select("How often did Route 4 trams run before the current timetable?", successor_ref=v3)  # strict 0.2.0
        self.assertEqual(out.predecessor_ref, v2)
        self.assertEqual(out.served_refs[0], v2)
        declared = h.select("How often did Route 4 trams run?", successor_ref=v2)
        self.assertEqual(declared.predecessor_ref, v1)

    def test_five_revisions_walks_one_step_from_the_declared_successor(self):
        h = _History(self, {"lib": LIB})
        ids = h.ids["lib"]
        for k in range(1, 5):
            with self.subTest(successor=k):
                self.assertEqual(h.select("Which catalogue engine version?", successor_ref=ids[k],
                                          budget=5).predecessor_ref, ids[k - 1])
        self.assertIsNone(h.select("Which catalogue engine version?", successor_ref=ids[0]).predecessor_ref)

    def test_error_corrected_values_are_never_predecessors(self):
        # v1 -state-> v2 (wrong) -correct-> v3: v2 never held, so v3's predecessor is v1.
        h = _History(self, {"dose": [("The sensor sample rate is 5 hertz.", None),
                                     ("The sensor sample rate is 50 hertz.", S),
                                     ("The sensor sample rate is 20 hertz.", E)]})
        v1, v2, v3 = h.ids["dose"]
        out = h.select("What was the sensor sample rate before?", successor_ref=v3)  # strict 0.2.0
        self.assertEqual(out.predecessor_ref, v1)
        self.assertNotIn(v2, out.served_refs)
        # v1 -correct-> v2: v1 never held, so there is no valid predecessor.
        h2 = _History(self, {"fee": [("The late fee is 9 dollars.", None), ("The late fee is 6 dollars.", E)]})
        out2 = h2.select("What was the late fee before?", successor_ref=h2.ids["fee"][1])  # strict 0.2.0
        self.assertIsNone(out2.predecessor_ref)
        self.assertNotIn(h2.ids["fee"][0], out2.served_refs)

    def test_deleted_memory_history_is_never_targeted(self):
        h = _History(self, {"kiln": KILN})
        old, new = h.ids["kiln"]
        h.delete("kiln")
        out = h.select("What glaze did the kiln firing schedule use before cone 10?")
        self.assertIsNone(out.predecessor_ref)
        self.assertNotIn(old, out.served_refs)

    def test_other_project_lineage_is_neither_targeted_nor_revealed(self):
        h = _History(self, {})
        h.write_chain("kiln-b", KILN, project="project-beta")
        out = h.select("What glaze did the kiln firing schedule use before cone 10?")
        self.assertEqual((out.served_refs, out.predecessor_ref), ((), None))
        with self.assertRaises(ValueError):
            h.select("What glaze?", successor_ref=h.ids["kiln-b"][1])
        with self.assertRaises(ValueError):
            h.select("What glaze?", successor_ref="ref-does-not-exist")

    def test_only_one_lineage_predecessor_moves_and_other_order_is_preserved(self):
        h = _History(self, {"kiln": KILN, "tram": TRAM})
        h.runtime.retain(h._proposal("note", 0), "The kiln room schedule is posted by the door.")
        query = "What glaze did the kiln firing schedule use before cone 10?"
        base = list(h.recall(query, "historical").ranked_admitted)
        out = h.select(query, budget=10, successor_ref=h.ids["kiln"][1])  # strict 0.2.0
        moved = out.predecessor_ref
        self.assertEqual([r for r in out.served_refs if r != moved],
                         [r for r in base if r != moved][:9])
        older_others = set(h.ids["tram"][:-1])
        for ref in older_others & set(out.served_refs):
            self.assertGreater(out.served_refs.index(ref), 0)

    def test_predecessor_with_no_word_overlap_is_found_through_lineage(self):
        h = _History(self, {"host": [("Builds ran on Jenkins agents.", None),
                                     ("Continuous integration now runs on hosted runners.", S)]})
        old, new = h.ids["host"]
        out = h.select("Which continuous integration did we use before hosted runners?", successor_ref=new)  # strict 0.2.0
        self.assertEqual(out.served_refs[0], old)

    def test_no_lineage_leaves_historical_ranking_unchanged(self):
        h = _History(self, {})
        h.runtime.retain(h._proposal("solo", 0), "The kiln firing schedule is weekly.")
        query = "What was the kiln firing schedule?"
        base = list(h.recall(query, "historical").ranked_admitted)
        out = h.select(query)
        self.assertIsNone(out.predecessor_ref)
        self.assertEqual(list(out.served_refs), base[:3])

    def test_default_current_and_historical_recall_are_unchanged(self):
        h = _History(self, {"tram": TRAM})
        q = "How often do Route 4 trams run?"
        before = [list(h.recall(q, m).ranked_admitted) for m in ("current", "historical")]
        h.select(q)
        after = [list(h.recall(q, m).ranked_admitted) for m in ("current", "historical")]
        self.assertEqual(before, after)
        self.assertEqual(before[0], [h.ids["tram"][-1]])

    def test_no_causal_or_authority_claims_and_budget_respected(self):
        h = _History(self, {"kiln": KILN})
        out = h.select("What glaze did the kiln firing schedule use before cone 10?", budget=1,
                       successor_ref=h.ids["kiln"][1])  # strict 0.2.0
        self.assertEqual(out.served_refs, (h.ids["kiln"][0],))
        self.assertFalse(out.complete_evidence_attested)
        self.assertEqual(out.authority_effect, "none")
        self.assertFalse(any(k in vars(out) for k in ("reason", "because", "cause", "explanation", "rationale")))
        for field, value in (("complete_evidence_attested", True), ("authority_effect", "stop"),
                             ("relation", "caused_by")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(out, **{field: value})
        with self.assertRaises(ValueError):
            h.select("x", budget=0)


class PreExistingDeletionLeak(unittest.TestCase):
    @unittest.expectedFailure
    def test_plain_historical_recall_does_not_serve_a_deleted_memorys_history(self):
        # Pre-existing v7 behaviour, NOT changed by #774: governed deletion
        # tombstones only the current fact, so earlier versions remain
        # admissible to historical recall. Needs its own slice.
        h = _History(self, {"kiln": KILN})
        old, _ = h.ids["kiln"]
        h.delete("kiln")
        self.assertNotIn(old, h.recall("What glaze did the kiln firing schedule use?", "historical").admitted)


if __name__ == "__main__":
    unittest.main()
