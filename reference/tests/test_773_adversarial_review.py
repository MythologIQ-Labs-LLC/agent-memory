"""#773 independent adversarial review of the opt-in current-context selector.

Authored by the cloud reviewer against 9c9bf4de493c76fec44b5d9c21af89849a2a9f73.
``ReferenceInstantDefects`` failed before repair. ``SelectorControls`` held on
the candidate and pin behaviour outside the authored fixtures.
"""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from agentmem_ref.runtime_composition import ConfiguredCompositionRuntime
from tests.qualified_fixtures import corpus_for, registry_for, rule
from tests.test_runtime_composition import _context, _plan, _proposal, TENANT, PROJECT

NOW = "2026-10-12T12:00:00Z"


class _Store:
    def __init__(self, testcase, rules=()):
        tmp = tempfile.TemporaryDirectory()
        testcase.addCleanup(tmp.cleanup)
        self.corpus = corpus_for(*rules)
        self.runtime = ConfiguredCompositionRuntime.create(
            Path(tmp.name), tenant=TENANT, plan=_plan(), verifier_registry=registry_for(self.corpus))
        self.t = testcase

    def proposal(self, memory, *, project=PROJECT, **kw):
        base = replace(_proposal("proposal:773r:" + memory + ":" + kw.pop("tag", "w"), operation="promotion"),
                       target_reference="memory:773r:" + memory)
        if project != PROJECT:
            base = replace(base, project_ref=project, isolation_domain_refs=(TENANT, project),
                           required_isolation_domain_refs=(project,))
        return replace(base, **kw)

    def retain(self, memory, text, *, project=PROJECT, validity=None):
        out = self.runtime.retain(self.proposal(memory, project=project), text, temporal=validity)
        self.t.assertTrue(out.committed)
        return out.fact_uuid

    def replace_value(self, memory, before, after, *, kind, project=PROJECT):
        proposal = self.proposal(memory, project=project, tag="c", operation="correction",
                                 state_snapshot="v1", review_satisfied=True,
                                 approval_refs=("approval:memory-owner",))
        out = self.runtime.correct(
            proposal, after, replacement_kind=kind,
            evidence=self.corpus.evidence_for(target_reference="memory:773r:" + memory,
                                              criterion="value-correction", pre_state=before,
                                              proposed_value=after))
        self.t.assertTrue(out.committed, out)
        return out.fact_uuid

    def select(self, query, reference_time, *, project=PROJECT, budget=5):
        return self.runtime.current_served_context(query, _context(project), budget=budget,
                                                   reference_time=reference_time)


def _rules(memory, before, after):
    return (rule(rule_id="rule:773r:" + memory, target="memory:773r:" + memory,
                 criterion="value-correction", from_state=before, to_values=(after,)),)


OLD, NEW = "The ledger database runs PostgreSQL 15.", "The ledger database runs PostgreSQL 16."
QUERY = "Which PostgreSQL version does the ledger database run?"


class ReferenceInstantDefects(unittest.TestCase):
    """D773-1: a reference instant earlier than a governed state change."""

    def test_instant_before_a_state_change_is_refused_not_served_with_the_later_value(self):
        store = _Store(self, _rules("pg", OLD, NEW))
        store.retain("pg", OLD)
        later = store.replace_value("pg", OLD, NEW, kind="state_change")
        # The store's governed clock places this change in 2026. At 2025-11-25
        # PostgreSQL 15 was current, but current-state admission has already
        # refused it as superseded, so any "current" context for that instant
        # would serve PostgreSQL 16 (or nothing) as if it applied then.
        with self.assertRaisesRegex(ValueError, "precedes a governed state change"):
            store.select(QUERY, "2025-11-25T00:00:00Z")
        # Control: an instant after the change is unaffected.
        self.assertIn(later, store.select(QUERY, NOW).served_refs)


class SelectorControls(unittest.TestCase):
    def test_error_correction_after_the_instant_does_not_refuse(self):
        # An error correction declares the old value never held, so the
        # corrected value is the best current evidence for any instant.
        store = _Store(self, _rules("pg", OLD, NEW))
        store.retain("pg", OLD)
        fixed = store.replace_value("pg", OLD, NEW, kind="error_correction")
        self.assertIn(fixed, store.select(QUERY, "2025-11-25T00:00:00Z").served_refs)

    def test_out_of_scope_superseded_candidate_neither_refuses_nor_leaks(self):
        store = _Store(self, _rules("pg-beta", OLD, NEW))
        store.retain("pg-beta", OLD, project="project-beta")
        store.replace_value("pg-beta", OLD, NEW, kind="state_change", project="project-beta")
        home = store.retain("pg-home", "The ledger database replica runs PostgreSQL 16.")
        selected = store.select(QUERY, "2025-11-25T00:00:00Z")
        self.assertEqual(selected.served_refs, (home,))
        self.assertEqual(selected.known_inapplicable_count, 0)

    def test_offset_boundaries_match_their_utc_instant(self):
        store = _Store(self)
        freeze = store.retain("freeze", "Ledger deploys are frozen for the holiday window.",
                              validity={"valid_from": "2025-11-20T00:00:00Z",
                                        "valid_until": "2025-12-01T00:00:00Z"})
        cases = (("2025-11-30T23:59:59Z", True), ("2025-12-01T01:00:00+01:00", False),
                 ("2025-11-30T23:30:00-01:00", False), ("2025-12-01T00:59:59+01:00", True),
                 ("2025-11-20T05:30:00+05:30", True), ("2025-11-20T05:29:59+05:30", False))
        for instant, served in cases:
            with self.subTest(instant=instant):
                self.assertEqual(freeze in store.select("Are ledger deploys frozen?", instant).served_refs, served)

    def test_hidden_project_memories_never_change_selection_or_counts(self):
        plain, noisy = _Store(self), _Store(self)
        for store in (plain, noisy):
            store.retain("days", "Ledger deploys happen on Tuesdays.")
            store.retain("freeze", "Ledger deploys are frozen for the holiday window.",
                         validity={"valid_from": "2025-11-20T00:00:00Z", "valid_until": "2025-12-01T00:00:00Z"})
        noisy.retain("hidden-freeze", "Ledger deploys are frozen during the beta window.", project="project-beta",
                     validity={"valid_from": "2025-11-20T00:00:00Z", "valid_until": "2025-12-01T00:00:00Z"})
        noisy.retain("hidden-days", "Ledger deploys happen on Fridays.", project="project-beta")
        a, b = plain.select("When do ledger deploys happen?", NOW), noisy.select("When do ledger deploys happen?", NOW)
        self.assertEqual(len(a.served_refs), len(b.served_refs))
        self.assertEqual((a.known_inapplicable_count, a.unknown_applicability_count),
                         (b.known_inapplicable_count, b.unknown_applicability_count))

    def test_selection_is_a_prefix_preserving_subsequence_of_governed_ranking(self):
        store = _Store(self)
        for i in range(6):
            store.retain(f"m{i}", f"Ledger deploy note {i} mentions deploys.",
                         validity=({"valid_from": "2025-11-20T00:00:00Z", "valid_until": "2025-12-01T00:00:00Z"}
                                   if i % 2 else None))
        ranked = store.runtime.multi_route_recall("ledger deploys", _context(),
                                                  temporal_intent={"mode": "current", "reference_time": NOW})
        selected = store.select("ledger deploys", NOW, budget=2)
        eligible = [r for r in ranked.ranked_admitted
                    if ranked.ranking_evidence[r]["temporal_applicability"] in ("applicable", "unknown_temporal_basis")]
        self.assertEqual(list(selected.served_refs), eligible[:2])
        self.assertTrue(set(selected.served_refs) <= set(ranked.admitted))

    def test_never_attests_completeness_authority_or_abstention(self):
        store = _Store(self)
        selected = store.select("anything at all", NOW)
        self.assertEqual(selected.served_refs, ())
        self.assertFalse(selected.complete_evidence_attested)
        self.assertEqual(selected.authority_effect, "none")
        self.assertFalse(any("abstain" in name or "stop" in name for name in vars(selected)))
        for field, value in (("complete_evidence_attested", True), ("authority_effect", "stop")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(selected, **{field: value})


if __name__ == "__main__":
    unittest.main()
